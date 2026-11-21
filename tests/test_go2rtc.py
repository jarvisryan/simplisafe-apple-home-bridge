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
OTHER_CAMERA_ID = "b" * 32


def make_camera(**overrides: object) -> CameraConfig:
    fields: dict[str, object] = {
        "name": "Back Garden",
        "location_id": "location-1",
        "camera_id": CAMERA_ID,
        "homekit_pin": "48276135",
    }
    fields.update(overrides)
    return CameraConfig(**fields)  # type: ignore[arg-type]


def make_config(**overrides: object) -> BridgeConfig:
    fields: dict[str, object] = {"cameras": [make_camera(**overrides)]}
    return BridgeConfig(**fields)  # type: ignore[arg-type]


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
    assert "ice_servers=%5B%7B%22urls%22%3A%5B%22stun%3Aexample.test%3A443%22%5D%7D%5D" in uri


def test_live_view_uri_encodes_fragment_metacharacters() -> None:
    view = LiveView(
        signed_channel_endpoint="wss://kinesis.example.test/channel",
        client_id="client#id",
        ice_servers=[{"urls": ["stun:example.test:443"], "username": "u#1"}],
    )
    uri = live_view_uri(view)
    assert "#" not in uri.split("format=kinesis#", 1)[0]
    assert uri.count("#") == 3  # format, client_id, ice_servers separators only


def test_render_creates_stable_stream_and_homekit_accessory() -> None:
    rendered = render_go2rtc_config(make_config(), Path("/data/token.json"))
    slug = stream_slug("Back Garden", CAMERA_ID)
    assert slug in rendered["streams"]
    assert rendered["homekit"][slug]["pin"] == "48276135"
    assert rendered["streams"][slug] == ["tcp://127.0.0.1:8099"]


def test_render_creates_kinesis_command_when_selected() -> None:
    config = BridgeConfig(
        cameras=[
            make_camera(
                name="Older Camera",
                transport="kinesis",
            )
        ]
    )

    rendered = render_go2rtc_config(config, Path("/data/token.json"))
    slug = stream_slug("Older Camera", CAMERA_ID)

    assert "/data/token.json" in rendered["streams"][slug][0]


def test_render_sets_api_password() -> None:
    rendered = render_go2rtc_config(
        make_config(), Path("/data/token.json"), api_password="s3cret-pass"
    )
    assert rendered["api"]["password"] == "s3cret-pass"  # type: ignore[union-attr]


def test_render_without_password_keeps_plain_api() -> None:
    rendered = render_go2rtc_config(make_config(), Path("/data/token.json"))
    assert rendered["api"] == {"listen": ":1984"}


def test_ports_survive_reordering_and_insertion() -> None:
    """A camera's decoder port must follow its identity, not its file order."""
    garden = make_camera(camera_id=CAMERA_ID)
    drive = make_camera(name="Drive", camera_id=OTHER_CAMERA_ID, homekit_pin="13572468")

    original = BridgeConfig(cameras=[garden, drive])
    reordered = BridgeConfig(cameras=[drive, garden])
    inserted = BridgeConfig(
        cameras=[
            make_camera(name="Kitchen", camera_id="c" * 32, homekit_pin="19283746"),
            garden,
            drive,
        ]
    )

    original_ports = {
        camera.camera_id: camera.port for camera in original.cameras if camera.transport == "livekit"
    }
    for later in (reordered, inserted):
        later_ports = {
            camera.camera_id: camera.port
            for camera in later.cameras
            if camera.transport == "livekit"
        }
        for camera_id, port in original_ports.items():
            assert later_ports[camera_id] == port


def test_explicit_ports_honoured_and_validated() -> None:
    config = BridgeConfig(
        cameras=[
            make_camera(name="Garden", port=8110),
            make_camera(name="Drive", camera_id=OTHER_CAMERA_ID, homekit_pin="13572468", port=8099),
        ]
    )
    ports = [camera.port for camera in config.cameras]
    assert sorted(port for port in ports if port is not None) == [8099, 8110]

    with pytest.raises(ValidationError, match="greater than or equal to 8099"):
        make_camera(port=8115)
    with pytest.raises(ValidationError, match="unique port"):
        BridgeConfig(
            cameras=[
                make_camera(name="Garden", port=8100),
                make_camera(name="Drive", camera_id=OTHER_CAMERA_ID, homekit_pin="13572468", port=8100),
            ]
        )


def test_write_does_not_wrap_long_camera_command(tmp_path: Path) -> None:
    kinesis_command = (
        "docker compose -f /Users/example/"
        + ("long-directory/" * 20)
        + "compose.yaml run --rm -T camera-bridge ssah"
    )
    config = BridgeConfig(
        cameras=[
            make_camera(
                name="Back Garden",
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


def test_write_returns_api_password_and_persists_it(tmp_path: Path) -> None:
    output = tmp_path / "go2rtc.yaml"

    password = write_go2rtc_config(make_config(), output, Path("/data/token.json"))

    assert password
    written = output.read_text(encoding="utf-8")
    assert f"password: {password}" in written


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
    slug = stream_slug("Back Garden", CAMERA_ID)
    existing = output.read_text(encoding="utf-8").replace("back_garden_bcbbe1b7", slug)
    output.write_text(existing, encoding="utf-8")

    write_go2rtc_config(make_config(), output, Path("/data/token.json"))

    assert "paired-client" in output.read_text(encoding="utf-8")


def test_slug_removes_shell_metacharacters() -> None:
    assert stream_slug("Front; rm -rf /", CAMERA_ID).startswith("front_rm_rf_")


def test_config_requires_homekit_pin() -> None:
    with pytest.raises(ValidationError, match="homekit_pin"):
        make_camera(homekit_pin=None)  # type: ignore[arg-type]


def test_config_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        BridgeConfig.model_validate(
            {
                "cameras": [
                    {
                        "name": "Garden",
                        "location_id": "1",
                        "camera_id": CAMERA_ID,
                        "homekit_pin": "48276135",
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
    camera = make_camera()
    with pytest.raises(ValidationError, match="only once"):
        BridgeConfig(cameras=[camera, camera])


def test_config_rejects_truncated_camera_id() -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        CameraConfig(
            name="Garden",
            location_id="1",
            camera_id="a" * 31,
            homekit_pin="48276135",
        )
