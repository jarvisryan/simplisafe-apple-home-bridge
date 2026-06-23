from __future__ import annotations

import hashlib
import json
import re
import shlex
from pathlib import Path
from urllib.parse import quote

import yaml

from .models import BridgeConfig, LiveView


def live_view_uri(live_view: LiveView) -> str:
    ice_servers = json.dumps(live_view.ice_servers, separators=(",", ":"))
    return (
        f"webrtc:{live_view.signed_channel_endpoint}"
        f"#format=kinesis#client_id={quote(live_view.client_id, safe='')}"
        f"#ice_servers={ice_servers}"
    )


def stream_slug(name: str, camera_id: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
    suffix = hashlib.blake2s(camera_id.encode("utf-8"), digest_size=4).hexdigest()
    return f"{cleaned or 'camera'}_{suffix}"


def render_go2rtc_config(config: BridgeConfig, token_path: Path) -> dict[str, object]:
    streams: dict[str, list[str]] = {}
    homekit: dict[str, dict[str, object]] = {}
    preload: dict[str, None] = {}

    for camera in config.cameras:
        slug = stream_slug(camera.name, camera.camera_id)
        command = (
            f"echo:ssah --token {shlex.quote(str(token_path))} stream"
            f" --location {camera.location_id} --camera {camera.camera_id}"
        )
        streams[slug] = [command, f"ffmpeg:{slug}#audio=opus/16000"]
        homekit[slug] = {
            "pin": int(camera.homekit_pin),
            "name": camera.name,
        }
        if camera.preload:
            preload[slug] = None

    rendered: dict[str, object] = {
        "api": {"listen": "127.0.0.1:1984"},
        "rtsp": {"listen": "127.0.0.1:8554"},
        "webrtc": {"listen": ":8555"},
        "streams": streams,
        "homekit": homekit,
        "log": {"format": "text", "level": "info"},
    }
    if preload:
        rendered["preload"] = preload
    return rendered


def write_go2rtc_config(config: BridgeConfig, output: Path, token_path: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_go2rtc_config(config, token_path)
    output.write_text(yaml.safe_dump(rendered, sort_keys=False), encoding="utf-8")
