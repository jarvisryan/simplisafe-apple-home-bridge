from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_LIVEKIT_CAMERAS = 16
LIVEKIT_DEFAULT_BASE_PORT = 8099


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64)
    location_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    camera_id: str = Field(pattern=r"^[A-Fa-f0-9]{32}$")
    homekit_pin: str = Field(pattern=r"^[1-9]\d{7}$")  # noqa: S105
    transport: Literal["livekit", "kinesis"] = "livekit"
    preload: bool = False
    # Explicit stream port for LiveKit cameras. When omitted, the bridge
    # allocates the lowest free port, which changes if cameras are reordered:
    # pin this for stable installations.
    port: int | None = Field(default=None, ge=1024, le=65535)

    @field_validator("name")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("camera names cannot contain control characters")
        return value

    @field_validator("homekit_pin")
    @classmethod
    def reject_weak_homekit_pin(cls, value: str) -> str:
        if len(set(value)) == 1 or value in {"12345678", "87654321"}:
            raise ValueError("choose a non-trivial HomeKit PIN")
        return value


class BridgeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cameras: list[CameraConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_cameras(self) -> BridgeConfig:
        identifiers = [(camera.location_id, camera.camera_id) for camera in self.cameras]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("each camera can appear only once")
        ports = [camera.port for camera in self.cameras if camera.port is not None]
        if len(ports) != len(set(ports)):
            raise ValueError("each stream port can be used by one camera only")
        return self

    @classmethod
    def load(cls, path: Path) -> BridgeConfig:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)


def assign_livekit_ports(
    config: BridgeConfig,
    base_port: int = LIVEKIT_DEFAULT_BASE_PORT,
) -> dict[tuple[str, str], int]:
    """Map each LiveKit camera to its TCP stream port.

    Explicit ``port`` settings win. The remaining cameras take the lowest
    free port in ``[base_port, base_port + MAX_LIVEKIT_CAMERAS)``. Both the
    go2rtc renderer and the LiveKit bridge call this, so they always agree
    even when cameras are added, removed or reordered.
    """
    ports: dict[tuple[str, str], int] = {}
    taken: set[int] = set()
    livekit_cameras = [camera for camera in config.cameras if camera.transport == "livekit"]
    for camera in livekit_cameras:
        if camera.port is None:
            continue
        ports[(camera.location_id, camera.camera_id)] = camera.port
        taken.add(camera.port)
    for camera in livekit_cameras:
        key = (camera.location_id, camera.camera_id)
        if key in ports:
            continue
        port = next(
            (
                candidate
                for candidate in range(base_port, base_port + MAX_LIVEKIT_CAMERAS)
                if candidate not in taken
            ),
            None,
        )
        if port is None:
            raise ValueError(
                f"no free stream port for '{camera.name}'; set an explicit port "
                f"or keep at most {MAX_LIVEKIT_CAMERAS} LiveKit cameras"
            )
        ports[key] = port
        taken.add(port)
    return ports


@dataclass(frozen=True, slots=True)
class DiscoveredCamera:
    location_id: str
    location_name: str
    camera_id: str
    camera_name: str
    provider: str | None
    model: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "location_id": self.location_id,
            "location_name": self.location_name,
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "provider": self.provider,
            "model": self.model,
        }


@dataclass(frozen=True, slots=True)
class LiveView:
    signed_channel_endpoint: str
    client_id: str
    ice_servers: list[dict[str, Any]]
