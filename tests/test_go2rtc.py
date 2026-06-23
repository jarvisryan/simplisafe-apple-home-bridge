from pathlib import Path

import pytest
from pydantic import ValidationError

from simplisafe_apple_home.go2rtc import live_view_uri, render_go2rtc_config, stream_slug
from simplisafe_apple_home.models import BridgeConfig, CameraConfig, LiveView


def test_live_view_uri_is_go2rtc_kinesis_source() -> None:
    view = LiveView(
        signed_channel_endpoint="wss://example.kinesisvideo.eu-west-2.amazonaws.com/path?X=1",
        client_id="camera client",
        ice_servers=[{"urls": ["stun:example.test:443"]}],
    )
    uri = live_view_uri(view)
    assert uri.startswith("webrtc:wss://example.kinesisvideo")
    assert "#format=kinesis" in uri
    assert "client_id=camera%20client" in uri
    assert 'ice_servers=[{"urls":["stun:example.test:443"]}]' in uri


def test_render_creates_stable_stream_and_homekit_accessory() -> None:
    config = BridgeConfig(
        cameras=[
            CameraConfig(
                name="Back Garden",
                location_id="location-1",
                camera_id="ABCDEF12345678",
                homekit_pin="48276135",
            )
        ]
    )
    rendered = render_go2rtc_config(config, Path("/data/token.json"))
    slug = stream_slug("Back Garden", "ABCDEF12345678")
    assert slug in rendered["streams"]
    assert rendered["homekit"][slug]["pin"] == 48276135
    assert "/data/token.json" in rendered["streams"][slug][0]


def test_slug_removes_shell_metacharacters() -> None:
    assert stream_slug("Front; rm -rf /", "ABC-12345678").startswith("front_rm_rf_")


def test_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        BridgeConfig.model_validate(
            {
                "cameras": [
                    {
                        "name": "Garden",
                        "location_id": "1",
                        "camera_id": "2",
                        "unexpected": True,
                    }
                ]
            }
        )


@pytest.mark.parametrize("pin", ["11111111", "22222222", "12345678", "87654321"])
def test_config_rejects_weak_homekit_pins(pin: str) -> None:
    with pytest.raises(ValidationError, match="non-trivial"):
        CameraConfig(name="Garden", location_id="1", camera_id="2", homekit_pin=pin)


def test_config_rejects_duplicate_camera() -> None:
    camera = CameraConfig(name="Garden", location_id="1", camera_id="2")
    with pytest.raises(ValidationError, match="only once"):
        BridgeConfig(cameras=[camera, camera])
