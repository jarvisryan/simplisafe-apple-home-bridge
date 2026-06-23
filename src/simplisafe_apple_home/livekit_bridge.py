from __future__ import annotations

import asyncio
import contextlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aiohttp import ClientSession

from .errors import http_status, safe_error_message
from .models import BridgeConfig, CameraConfig
from .storage import TokenStore

WEBRTC_URL_BASE = "https://app-hub.prd.aser.simplisafe.com/v2"


def _log(message: str) -> None:
    print(f"[livekit] {message}", flush=True)


def livekit_credentials(payload: object) -> tuple[str, str] | None:
    if not isinstance(payload, dict):
        return None
    details = payload.get("liveKitDetails")
    if not isinstance(details, dict):
        return None
    url = details.get("liveKitURL")
    token = details.get("userToken")
    if not isinstance(url, str) or not url.startswith(("ws://", "wss://")):
        return None
    if not isinstance(token, str) or not token:
        return None
    return url, token


class LiveViewProvider:
    def __init__(self, api: Any) -> None:
        self._api = api
        self._request_lock = asyncio.Lock()

    @classmethod
    async def create(cls, token_path: Path, session: ClientSession) -> LiveViewProvider:
        from simplipy import API  # type: ignore[import-untyped]

        store = TokenStore(token_path)
        api = await API.async_from_refresh_token(store.load(), session=session)

        async def save_refreshed_token(refresh_token: str) -> None:
            await asyncio.to_thread(store.save, refresh_token)

        api.add_refresh_token_callback(save_refreshed_token)
        return cls(api)

    async def request(self, camera: CameraConfig) -> dict[str, Any]:
        async with self._request_lock:
            response = await self._api.async_request(
                "get",
                f"cameras/{camera.camera_id}/{camera.location_id}/live-view",
                url_base=WEBRTC_URL_BASE,
            )
        if not isinstance(response, dict):
            raise RuntimeError("SimpliSafe returned an invalid live-view response")
        return response

    async def credentials(self, camera: CameraConfig) -> tuple[str, str]:
        for attempt in range(30):
            try:
                response = await self.request(camera)
            except Exception as error:  # noqa: BLE001
                if http_status(error) not in {400, 409}:
                    raise
                _log(
                    f"{camera.name}: wake attempt {attempt + 1}, "
                    f"HTTP {http_status(error)}"
                )
                await asyncio.sleep(2)
                continue
            credentials = livekit_credentials(response)
            if credentials is not None:
                return credentials
            status = response.get("cameraStatus", "unknown")
            _log(f"{camera.name}: wake attempt {attempt + 1}, status={status}")
            await asyncio.sleep(2)
        raise RuntimeError(f"{camera.name}: camera did not provide LiveKit credentials")


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    target_fps: int = 10
    threads: int = 2
    preset: str = "ultrafast"
    enable_audio: bool = True
    audio_rate: int = 16000
    warm_interval: int = 0

    @classmethod
    def from_environment(cls) -> RuntimeSettings:
        return cls(
            target_fps=int(os.environ.get("SSAH_TARGET_FPS", "10")),
            threads=int(os.environ.get("SSAH_THREADS", "2")),
            preset=os.environ.get("SSAH_PRESET", "ultrafast"),
            enable_audio=(
                os.environ.get("SSAH_ENABLE_AUDIO", "1").lower()
                not in {"0", "false", "no"}
            ),
            audio_rate=int(os.environ.get("SSAH_AUDIO_RATE", "16000")),
            warm_interval=int(os.environ.get("SSAH_WARM_INTERVAL", "0")),
        )


class CameraServer:
    def __init__(
        self,
        camera: CameraConfig,
        port: int,
        provider: LiveViewProvider,
        settings: RuntimeSettings,
    ) -> None:
        self.camera = camera
        self.port = port
        self.provider = provider
        self.settings = settings
        self._active: asyncio.Task[None] | None = None

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if self._active is not None and not self._active.done():
            self._active.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._active
        task = asyncio.create_task(self._run_session(reader, writer))
        self._active = task
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as error:  # noqa: BLE001
            _log(f"{self.camera.name}: session failed: {safe_error_message(error)}")
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def keep_warm(self) -> None:
        while True:
            try:
                response = await self.provider.request(self.camera)
                status = response.get("cameraStatus", "unknown")
                _log(f"{self.camera.name}: keep-warm status={status}")
            except Exception as error:  # noqa: BLE001
                _log(f"{self.camera.name}: keep-warm failed: {safe_error_message(error)}")
            await asyncio.sleep(self.settings.warm_interval)

    async def _run_session(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        from livekit import rtc  # type: ignore[import-not-found]

        _log(f"{self.camera.name}: viewer connected")
        room: Any = None
        video_stream: Any = None
        audio_stream: Any = None
        process: asyncio.subprocess.Process | None = None
        audio_write_fd: int | None = None
        tasks: list[asyncio.Task[None]] = []
        try:
            url, token = await self.provider.credentials(self.camera)
            room = rtc.Room()
            tracks: dict[str, Any] = {}
            video_ready = asyncio.Event()

            @room.on("track_subscribed")
            def track_subscribed(track: Any, _publication: Any, _participant: Any) -> None:
                if track.kind == rtc.TrackKind.KIND_VIDEO and "video" not in tracks:
                    tracks["video"] = track
                    video_ready.set()
                elif track.kind == rtc.TrackKind.KIND_AUDIO and "audio" not in tracks:
                    tracks["audio"] = track

            @room.on("disconnected")
            def disconnected(*_args: object) -> None:
                video_ready.set()

            await room.connect(url, token)
            await asyncio.wait_for(video_ready.wait(), timeout=60)
            if "video" not in tracks:
                raise RuntimeError("LiveKit room disconnected before sending video")
            await asyncio.sleep(0.5)

            video_stream = rtc.VideoStream(tracks["video"])
            first_event = await video_stream.__anext__()
            first_frame = first_event.frame.convert(rtc.VideoBufferType.I420)
            width, height = first_frame.width, first_frame.height
            have_audio = self.settings.enable_audio and "audio" in tracks

            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-thread_queue_size",
                "512",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "yuv420p",
                "-s",
                f"{width}x{height}",
                "-r",
                str(self.settings.target_fps),
                "-i",
                "pipe:0",
            ]
            pass_fds: tuple[int, ...] = ()
            audio_read_fd: int | None = None
            if have_audio:
                audio_read_fd, audio_write_fd = os.pipe()
                pass_fds = (audio_read_fd,)
                command.extend(
                    [
                        "-thread_queue_size",
                        "512",
                        "-f",
                        "s16le",
                        "-ar",
                        str(self.settings.audio_rate),
                        "-ac",
                        "1",
                        "-i",
                        f"pipe:{audio_read_fd}",
                    ]
                )
            command.extend(["-map", "0:v"])
            if have_audio:
                command.extend(["-map", "1:a"])
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    self.settings.preset,
                    "-tune",
                    "zerolatency",
                    "-threads",
                    str(self.settings.threads),
                    "-g",
                    str(self.settings.target_fps * 2),
                    "-bf",
                    "0",
                    "-pix_fmt",
                    "yuv420p",
                ]
            )
            if have_audio:
                command.extend(
                    [
                        "-c:a",
                        "aac",
                        "-b:a",
                        "48k",
                        "-ar",
                        str(self.settings.audio_rate),
                        "-ac",
                        "1",
                    ]
                )
            command.extend(["-f", "mpegts", "pipe:1"])

            process = await asyncio.create_subprocess_exec(  # noqa: S603
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                pass_fds=pass_fds,
            )
            if audio_read_fd is not None:
                os.close(audio_read_fd)
            ffmpeg = process
            _log(
                f"{self.camera.name}: streaming {width}x{height}@"
                f"{self.settings.target_fps}fps audio={'on' if have_audio else 'off'}"
            )

            stop = asyncio.Event()
            interval = 1.0 / self.settings.target_fps

            async def feed_video() -> None:
                if ffmpeg.stdin is None:
                    raise RuntimeError("FFmpeg video input is unavailable")
                last_frame = 0.0
                try:
                    ffmpeg.stdin.write(first_frame.data.tobytes())
                    await ffmpeg.stdin.drain()
                    last_frame = time.monotonic()
                    async for event in video_stream:
                        if stop.is_set():
                            break
                        now = time.monotonic()
                        if now - last_frame < interval:
                            continue
                        last_frame = now
                        frame = event.frame.convert(rtc.VideoBufferType.I420)
                        ffmpeg.stdin.write(frame.data.tobytes())
                        await ffmpeg.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    stop.set()
                    ffmpeg.stdin.close()

            async def feed_audio() -> None:
                nonlocal audio_stream
                if audio_write_fd is None:
                    raise RuntimeError("FFmpeg audio input is unavailable")
                write_fd = audio_write_fd
                try:
                    audio_stream = rtc.AudioStream(
                        tracks["audio"],
                        sample_rate=self.settings.audio_rate,
                        num_channels=1,
                    )
                    async for event in audio_stream:
                        if stop.is_set():
                            break
                        await asyncio.to_thread(
                            os.write, write_fd, bytes(event.frame.data)
                        )
                except (BrokenPipeError, OSError):
                    pass
                finally:
                    with contextlib.suppress(OSError):
                        os.close(write_fd)

            async def relay() -> None:
                if ffmpeg.stdout is None:
                    raise RuntimeError("FFmpeg stream output is unavailable")
                try:
                    while chunk := await ffmpeg.stdout.read(65536):
                        writer.write(chunk)
                        await writer.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    stop.set()

            async def watch_disconnect() -> None:
                try:
                    while await reader.read(4096):
                        pass
                finally:
                    stop.set()

            tasks = [
                asyncio.create_task(feed_video()),
                asyncio.create_task(relay()),
                asyncio.create_task(watch_disconnect()),
            ]
            if have_audio:
                tasks.append(asyncio.create_task(feed_audio()))
            await stop.wait()
        finally:
            _log(f"{self.camera.name}: viewer disconnected")
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if audio_write_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(audio_write_fd)
            if process is not None:
                with contextlib.suppress(ProcessLookupError):
                    process.terminate()
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(process.wait(), timeout=5)
            if video_stream is not None:
                with contextlib.suppress(Exception):
                    await video_stream.aclose()
            if audio_stream is not None:
                with contextlib.suppress(Exception):
                    await audio_stream.aclose()
            if room is not None:
                with contextlib.suppress(Exception):
                    await room.disconnect()


async def run() -> None:
    config_path = Path(os.environ.get("SSAH_CONFIG", "/config/bridge.yaml"))
    token_path = Path(os.environ.get("SSAH_TOKEN", "/data/simplisafe-token.json"))
    bind = os.environ.get("SSAH_BIND", "0.0.0.0")  # noqa: S104
    base_port = int(os.environ.get("SSAH_BASE_PORT", "8099"))
    settings = RuntimeSettings.from_environment()
    config = BridgeConfig.load(config_path)
    cameras = [
        (index, camera)
        for index, camera in enumerate(config.cameras)
        if camera.transport == "livekit"
    ]
    if not cameras:
        raise RuntimeError("bridge.yaml contains no LiveKit cameras")
    if len(config.cameras) > 16:
        raise RuntimeError("at most 16 configured cameras are supported")

    async with ClientSession() as session:
        provider = await LiveViewProvider.create(token_path, session)
        camera_servers = [
            CameraServer(camera, base_port + index, provider, settings)
            for index, camera in cameras
        ]
        servers = [
            await asyncio.start_server(server.handle, bind, server.port)
            for server in camera_servers
        ]
        warm_tasks: list[asyncio.Task[None]] = []
        for server in camera_servers:
            _log(f"{server.camera.name}: listening on {bind}:{server.port}")
            if settings.warm_interval > 0:
                warm_tasks.append(asyncio.create_task(server.keep_warm()))
        await asyncio.gather(
            *(server.serve_forever() for server in servers),
            *warm_tasks,
        )


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
