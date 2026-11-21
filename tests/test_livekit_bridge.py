import asyncio
from typing import Any

import pytest

from simplisafe_apple_home.livekit_bridge import (
    LiveViewProvider,
    RuntimeSettings,
    livekit_credentials,
)
from simplisafe_apple_home.models import CameraConfig


def make_camera() -> CameraConfig:
    return CameraConfig(
        name="Back Garden",
        location_id="location-1",
        camera_id="a" * 32,
        homekit_pin="48276135",
    )


def test_livekit_credentials_reads_valid_response() -> None:
    payload = {
        "cameraStatus": "online",
        "liveKitDetails": {
            "liveKitURL": "wss://livekit.example.test",
            "userToken": "signed-token",
        },
    }

    assert livekit_credentials(payload) == (
        "wss://livekit.example.test",
        "signed-token",
    )


def test_livekit_credentials_rejects_kinesis_response() -> None:
    assert livekit_credentials({"signedChannelEndpoint": "wss://kinesis.test"}) is None


def test_runtime_settings_disable_audio(monkeypatch: Any) -> None:
    monkeypatch.setenv("SSAH_ENABLE_AUDIO", "false")

    assert RuntimeSettings.from_environment().enable_audio is False


async def test_live_view_requests_run_concurrently_across_cameras() -> None:
    """A slow request for one camera must not delay the others."""

    class SlowApi:
        async def async_request(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
            await asyncio.sleep(0.05)
            return {}

    provider = LiveViewProvider(SlowApi())
    garden = make_camera()
    drive = CameraConfig(
        name="Drive",
        location_id="location-1",
        camera_id="b" * 32,
        homekit_pin="13572468",
    )

    async def request(camera: CameraConfig) -> None:
        with pytest.raises(RuntimeError, match="invalid live-view"):
            await provider.request(camera)

    await asyncio.gather(request(garden), request(drive))


async def test_request_lock_is_per_camera(monkeypatch: Any) -> None:
    seen: list[str] = []

    class RecordingApi:
        async def async_request(self, _method: str, path: str, **_kwargs: object) -> dict[str, Any]:
            camera_id = path.split("/")[0]
            seen.append(camera_id)
            # Interleave: yield control so the other camera's request starts.
            await asyncio.sleep(0)
            return {}

    provider = LiveViewProvider(RecordingApi())

    async def request(camera: CameraConfig) -> None:
        with pytest.raises(RuntimeError, match="invalid live-view"):
            await provider.request(camera)

    garden = make_camera()
    drive = CameraConfig(
        name="Drive",
        location_id="location-1",
        camera_id="b" * 32,
        homekit_pin="13572468",
    )
    await asyncio.gather(request(garden), request(drive))

    assert seen == [garden.camera_id, drive.camera_id]
