from typing import Any

import pytest

from simplisafe_apple_home.client import SimpliSafeClient
from simplisafe_apple_home.storage import TokenStore


class FakeSession:
    async def close(self) -> None:
        return None


class FakeCamera:
    name = "Back Garden"
    model = "Outdoor Camera"
    camera_supported_features = {"providers": {"webrtc": "kvs"}}


class FakeSystem:
    address = "Home"
    cameras = {"camera-1": FakeCamera()}


class FakeApi:
    async def async_get_systems(self) -> dict[str, FakeSystem]:
        return {"location-1": FakeSystem()}

    async def async_request(self, *_args: object, **_kwargs: object) -> dict[str, Any]:
        return {
            "signedChannelEndpoint": "wss://example.test/kvs",
            "clientId": "client-1",
            "iceServers": [{"urls": ["stun:example.test"]}],
        }


@pytest.mark.asyncio
async def test_discovery_normalises_camera_data(tmp_path: Any) -> None:
    client = SimpliSafeClient(  # type: ignore[arg-type]
        FakeApi(), FakeSession(), TokenStore(tmp_path / "token")
    )
    result = await client.discover()
    assert result[0].camera_name == "Back Garden"
    assert result[0].location_id == "location-1"
    assert result[0].provider == "kvs"


@pytest.mark.asyncio
async def test_live_view_validates_transport(tmp_path: Any) -> None:
    client = SimpliSafeClient(  # type: ignore[arg-type]
        FakeApi(), FakeSession(), TokenStore(tmp_path / "token")
    )
    result = await client.get_live_view("location-1", "camera-1")
    assert result.client_id == "client-1"
