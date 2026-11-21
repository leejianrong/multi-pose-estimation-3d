"""Frame sources feed a camera-node (ADR-0003). SimSource receives frames pushed by the sim."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from .messages import unpack_frame


@dataclass
class Frame:
    camera_id: str
    frame_id: int
    t_capture: float
    image: np.ndarray  # BGR uint8
    decode_ms: float = 0.0


class FrameSource(Protocol):
    def frames(self) -> AsyncIterator[Frame]: ...


class SimSource:
    """Latest frame wins: if inference lags the sim, old frames are dropped, not queued."""

    def __init__(self) -> None:
        self._latest: Frame | None = None
        self._event = asyncio.Event()
        self.dropped = 0

    def push(self, data: bytes) -> None:
        t0 = time.perf_counter()
        header, jpeg = unpack_frame(data)
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("undecodable JPEG")
        if self._latest is not None:
            self.dropped += 1
        self._latest = Frame(
            header["camera_id"],
            int(header["frame_id"]),
            float(header["t_capture"]),
            image,
            (time.perf_counter() - t0) * 1000,
        )
        self._event.set()

    async def frames(self) -> AsyncIterator[Frame]:
        while True:
            await self._event.wait()
            self._event.clear()
            frame, self._latest = self._latest, None
            if frame is not None:
                yield frame
