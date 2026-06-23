from pathlib import Path

import pytest
from pydantic import ValidationError

from simplisafe_apple_home.go2rtc import (
    live_view_uri,
    render_go2rtc_config,
    stream_slug,
    write_go2rtc_config,
)
from simplisafe_apple_home.models import BridgeConfig, CameraConfig, LiveView

CAMERA_ID = "a" * 32


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
                camera_id=CAMERA_ID,
                homekit_pin="48276135",
            )
        ]
    )
    rendered = render_go2rtc_config(config, Path("/data/token.json"))
    slug = stream_slug("Back Garden", CAMERA_ID)
    assert slug in rendered["streams"]
    assert rendered["homekit"][slug]["pin"] == "48276135"
    assert rendered["streams"][slug] == ["tcp://127.0.0.1:8099"]


def test_render_creates_kinesis_command_when_selected() -> None:
    config = BridgeConfig(
        cameras=[
            CameraConfig(
                name="Older Camera",
                location_id="location-1",
                camera_id=CAMERA_ID,
                homekit_pin="48276135",
                transport="kinesis",
            )
        ]
    )

    rendered = render_go2rtc_config(config, Path("/data/token.json"))
    slug = stream_slug("Older Camera", CAMERA_ID)

    assert "/data/token.json" in rendered["streams"][slug][0]


def test_write_does_not_wrap_long_camera_command(tmp_path: Path) -> None:
    kinesis_command = (
        "docker compose -f /Users/example/"
        + ("long-directory/" * 20)
        + "compose.yaml run --rm -T camera-bridge ssah"
    )
    config = BridgeConfig(
        cameras=[
            CameraConfig(
                name="Back Garden",
                location_id="location-1",
                camera_id=CAMERA_ID,
                homekit_pin="48276135",
                transport="kinesis",
            )
        ]
    )
    output = tmp_path / "go2rtc.yaml"

    write_go2rtc_config(
        config,
        output,
        Path("/data/token.json"),
        kinesis_command,
    )

    command_line = next(line for line in output.read_text().splitlines() if "echo:ssah" in line)
    assert f"--camera {CAMERA_ID}" in command_line
    assert kinesis_command in command_line


def test_write_preserves_homekit_pairings(tmp_path: Path) -> None:
    output = tmp_path / "go2rtc.yaml"
    output.write_text(
        "homekit:\n"
        "  back_garden_bcbbe1b7:\n"
        "    pin: '48276135'\n"
        "    pairings:\n"
        "      - paired-client\n",
        encoding="utf-8",
    )
    config = BridgeConfig(
        cameras=[
            CameraConfig(
                name="Back Garden",
                location_id="location-1",
                camera_id=CAMERA_ID,
                homekit_pin="48276135",
            )
        ]
    )
    slug = stream_slug("Back Garden", CAMERA_ID)
    existing = output.read_text(encoding="utf-8").replace("back_garden_bcbbe1b7", slug)
    output.write_text(existing, encoding="utf-8")

    write_go2rtc_config(config, output, Path("/data/token.json"))

    assert "paired-client" in output.read_text(encoding="utf-8")


def test_slug_removes_shell_metacharacters() -> None:
    assert stream_slug("Front; rm -rf /", CAMERA_ID).startswith("front_rm_rf_")


def test_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        BridgeConfig.model_validate(
            {
                "cameras": [
                    {
                        "name": "Garden",
                        "location_id": "1",
                        "camera_id": CAMERA_ID,
                        "unexpected": True,
                    }
                ]
            }
        )


@pytest.mark.parametrize("pin", ["11111111", "22222222", "12345678", "87654321"])
def test_config_rejects_weak_homekit_pins(pin: str) -> None:
    with pytest.raises(ValidationError, match="non-trivial"):
        CameraConfig(name="Garden", location_id="1", camera_id=CAMERA_ID, homekit_pin=pin)


def test_config_rejects_duplicate_camera() -> None:
    camera = CameraConfig(name="Garden", location_id="1", camera_id=CAMERA_ID)
    with pytest.raises(ValidationError, match="only once"):
        BridgeConfig(cameras=[camera, camera])


def test_config_rejects_truncated_camera_id() -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        CameraConfig(name="Garden", location_id="1", camera_id="a" * 31)
