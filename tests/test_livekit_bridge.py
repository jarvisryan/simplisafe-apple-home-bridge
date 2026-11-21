import asyncio
import time
from typing import Any

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
    started: dict[str, float] = {}

    class SlowApi:
        async def async_request(self, _method: str, path: str, **_kwargs: object) -> dict[str, Any]:
            camera_id = path.split("/")[1]
            started[camera_id] = time.monotonic()
            await asyncio.sleep(0.2)
            return {"cameraStatus": "offline"}

    provider = LiveViewProvider(SlowApi())
    garden = make_camera()
    drive = CameraConfig(
        name="Drive",
        location_id="location-1",
        camera_id="b" * 32,
        homekit_pin="13572468",
    )

    begin = time.monotonic()
    await asyncio.gather(provider.request(garden), provider.request(drive))
    total = time.monotonic() - begin

    # With a single shared lock, the two 200 ms requests would serialise to
    # roughly 400 ms; per-camera locks should finish near 200 ms.
    assert total < 0.35, f"requests appear serialised across cameras: {total:.2f}s"
    assert set(started) == {garden.camera_id, drive.camera_id}


async def test_repeat_requests_for_one_camera_are_serialised() -> None:
    """Concurrent requests for the SAME camera take turns, not overlap."""
    active = 0
    max_active = 0

    class CountingApi:
        async def async_request(self, _method: str, path: str, **_kwargs: object) -> dict[str, Any]:
            nonlocal active, max_active
            camera_id = path.split("/")[1]
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            active -= 1
            return {"cameraStatus": "offline", "cameraId": camera_id}

    provider = LiveViewProvider(CountingApi())
    garden = make_camera()

    await asyncio.gather(*[provider.request(garden) for _ in range(3)])

    assert max_active == 1, f"per-camera lock did not serialise: {max_active} overlapping"
