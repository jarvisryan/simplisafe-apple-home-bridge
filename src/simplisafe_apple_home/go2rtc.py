from __future__ import annotations

import hashlib
import json
import re
import shlex
import secrets
from pathlib import Path
from urllib.parse import quote

import yaml

from .models import BridgeConfig, CameraConfig, LiveView

LIVEKIT_BASE_PORT = 8099
PAIRING_KEYS = ("device_id", "device_private", "pairings")


def live_view_uri(live_view: LiveView) -> str:
    ice_servers = quote(
        json.dumps(live_view.ice_servers, separators=(",", ":")), safe=""
    )
    return (
        f"webrtc:{live_view.signed_channel_endpoint}"
        f"#format=kinesis#client_id={quote(live_view.client_id, safe='')}"
        f"#ice_servers={ice_servers}"
    )


def stream_slug(name: str, camera_id: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
    suffix = hashlib.blake2s(camera_id.encode("utf-8"), digest_size=4).hexdigest()
    return f"{cleaned or 'camera'}_{suffix}"


def decoder_port(camera: CameraConfig) -> int:
    """Return the resolved decoder port for a livekit camera."""
    if camera.port is None:
        raise RuntimeError(
            f"{camera.name}: no decoder port assigned; reload BridgeConfig to allocate ports"
        )
    return camera.port


def render_go2rtc_config(
    config: BridgeConfig,
    token_path: Path,
    kinesis_command: str = "ssah",
    api_password: str | None = None,
) -> dict[str, object]:
    streams: dict[str, list[str]] = {}
    homekit: dict[str, dict[str, object]] = {}
    preload: dict[str, None] = {}

    for camera in config.cameras:
        slug = stream_slug(camera.name, camera.camera_id)
        if camera.transport == "livekit":
            streams[slug] = [f"tcp://127.0.0.1:{decoder_port(camera)}"]
        else:
            command = (
                f"echo:{kinesis_command} --token {shlex.quote(str(token_path))} stream"
                f" --location {camera.location_id} --camera {camera.camera_id}"
            )
            streams[slug] = [command, f"ffmpeg:{slug}#audio=opus/16000"]
        homekit[slug] = {
            "pin": camera.homekit_pin,
            "name": camera.name,
        }
        if camera.preload:
            preload[slug] = None

    api: dict[str, object] = {"listen": ":1984"}
    if api_password is not None:
        api["password"] = api_password

    rendered: dict[str, object] = {
        "api": api,
        "rtsp": {"listen": "127.0.0.1:8554"},
        "webrtc": {"listen": ":8555"},
        "streams": streams,
        "homekit": homekit,
        "log": {"format": "text", "level": "info"},
    }
    if preload:
        rendered["preload"] = preload
    return rendered


def write_go2rtc_config(
    config: BridgeConfig,
    output: Path,
    token_path: Path,
    kinesis_command: str = "ssah",
) -> str:
    """Render go2rtc.yaml and return the generated API password, if any."""
    output.parent.mkdir(parents=True, exist_ok=True)
    api_password = secrets.token_urlsafe(16)
    rendered = render_go2rtc_config(
        config, token_path, kinesis_command, api_password=api_password
    )
    _preserve_pairings(output, rendered)
    # go2rtc's YAML reader does not fold wrapped command scalars reliably.
    output.write_text(
        yaml.safe_dump(rendered, sort_keys=False, width=4096),
        encoding="utf-8",
    )
    return api_password


def _preserve_pairings(output: Path, rendered: dict[str, object]) -> None:
    if not output.exists():
        return
    existing = yaml.safe_load(output.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        return
    old_homekit = existing.get("homekit")
    new_homekit = rendered.get("homekit")
    if not isinstance(old_homekit, dict) or not isinstance(new_homekit, dict):
        return
    for slug, settings in new_homekit.items():
        old_settings = old_homekit.get(slug)
        if not isinstance(settings, dict) or not isinstance(old_settings, dict):
            continue
        for key in PAIRING_KEYS:
            if key in old_settings:
                settings[key] = old_settings[key]
