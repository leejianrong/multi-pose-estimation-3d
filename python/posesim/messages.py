"""Wire contracts (ADR-0002). JSON, versioned."""

from __future__ import annotations

import json
import struct

from pydantic import BaseModel, field_validator

VERSION = 1
N_JOINTS = 17


class Person2D(BaseModel):
    bbox: list[float]  # x1, y1, x2, y2
    score: float
    keypoints: list[list[float]]  # 17 x [x, y, conf], distorted image pixels

    @field_validator("keypoints")
    @classmethod
    def _17(cls, v: list[list[float]]) -> list[list[float]]:
        if len(v) != N_JOINTS or any(len(k) != 3 for k in v):
            raise ValueError("keypoints must be 17 x [x, y, conf]")
        return v


class Pose2D(BaseModel):
    version: int = VERSION
    camera_id: str
    frame_id: int
    t_capture: float  # seconds, sim clock
    people: list[Person2D]
    timings_ms: dict[str, float] = {}


class Person3D(BaseModel):
    track_id: int
    joints: list[list[float] | None]  # 17 x [x, y, z, conf] in metres, room frame, or None
    partial: bool = False
    views: list[str] = []

    @field_validator("joints")
    @classmethod
    def _17(cls, v: list[list[float] | None]) -> list[list[float] | None]:
        if len(v) != N_JOINTS or any(j is not None and len(j) != 4 for j in v):
            raise ValueError("joints must be 17 x ([x, y, z, conf] | null)")
        return v


class Skeleton3D(BaseModel):
    version: int = VERSION
    frame_id: int
    t_capture: float
    t_fused: float
    people: list[Person3D]
    cameras_used: list[str]
    cameras_down: list[str] = []
    timings_ms: dict[str, float] = {}


def pack_frame(header: dict, jpeg: bytes) -> bytes:
    """Sim -> camera-node binary frame: 4-byte big-endian header length, JSON header, JPEG."""
    h = json.dumps(header).encode()
    return struct.pack(">I", len(h)) + h + jpeg


def unpack_frame(data: bytes) -> tuple[dict, bytes]:
    (n,) = struct.unpack(">I", data[:4])
    if n > len(data) - 4:
        raise ValueError("truncated frame header")
    return json.loads(data[4 : 4 + n]), data[4 + n :]
