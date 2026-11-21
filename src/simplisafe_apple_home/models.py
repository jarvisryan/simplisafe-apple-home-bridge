from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DECODER_PORT_MIN = 8099
DECODER_PORT_MAX = 8114
MAX_DECODERS = DECODER_PORT_MAX - DECODER_PORT_MIN + 1


class CameraConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64)
    location_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    camera_id: str = Field(pattern=r"^[A-Fa-f0-9]{32}$")
    homekit_pin: str = Field(pattern=r"^[1-9]\d{7}$")  # noqa: S105
    transport: Literal["livekit", "kinesis"] = "livekit"
    preload: bool = False
    # Explicit decoder port. 0 (the default) means "derive a stable port from
    # the camera's identity"; see BridgeConfig.resolve_decoder_ports. Ports are
    # identity-keyed rather than order-keyed, so reordering or inserting
    # cameras in bridge.yaml can never repoint a stream that an existing
    # go2rtc HomeKit pairing still references.
    port: int = Field(default=0, ge=0, le=DECODER_PORT_MAX)

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

    @model_validator(mode="after")
    def resolve_decoder_ports(self) -> BridgeConfig:
        """Give every livekit camera a unique decoder port.

        Ports marked 0 are derived by hashing the camera's identity into the
        8099-8114 range and resolving collisions with quadratic probing. The
        result depends only on the set of cameras, never on their order in
        bridge.yaml, so the mapping is stable across config edits and
        re-renders and each camera keeps its stream and preserved pairing.

        The result is built with model_construct (bypassing re-validation) so
        the assigned ports survive; mutating self.cameras inside a
        mode=after validator is silently discarded by pydantic.
        """
        livekit_cameras = [camera for camera in self.cameras if camera.transport == "livekit"]
        if len(livekit_cameras) > MAX_DECODERS:
            raise ValueError(f"at most {MAX_DECODERS} livekit cameras are supported")

        explicit = {camera.port for camera in livekit_cameras if camera.port != 0}
        if len(explicit) != sum(1 for camera in livekit_cameras if camera.port != 0):
            raise ValueError("each livekit camera needs a unique port")

        taken = set(explicit)
        updated: list[CameraConfig] = []
        for camera in self.cameras:
            if camera.transport == "livekit" and camera.port == 0:
                digest = int.from_bytes(
                    hashlib.blake2b(
                        f"{camera.location_id}|{camera.camera_id}".encode("utf-8"),
                        digest_size=4,
                    ).digest(),
                    "big",
                )
                span = DECODER_PORT_MAX - DECODER_PORT_MIN + 1
                for probe in range(span):
                    port = DECODER_PORT_MIN + (digest + probe * probe) % span
                    if port not in taken:
                        taken.add(port)
                        camera = camera.model_copy(update={"port": port})
                        break
                else:
                    raise ValueError(
                        f"no free decoder port for camera {camera.name}; "
                        "assign explicit ports in bridge.yaml"
                    )
            updated.append(camera)

        return BridgeConfig.model_construct(cameras=updated)

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
