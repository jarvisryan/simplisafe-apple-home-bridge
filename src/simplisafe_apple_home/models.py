from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64)
    location_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    camera_id: str = Field(pattern=r"^[A-Fa-f0-9]{32}$")
    homekit_pin: str = Field(default="19550224", pattern=r"^[1-9]\d{7}$")  # noqa: S105
    transport: Literal["livekit", "kinesis"] = "livekit"
    preload: bool = False

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
        return self

    @classmethod
    def load(cls, path: Path) -> BridgeConfig:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)


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
