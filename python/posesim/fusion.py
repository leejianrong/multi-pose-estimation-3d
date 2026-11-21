"""fusion: Pose2D from N camera-nodes -> Skeleton3D (ADR-0002, ADR-0007).

V1 handles one person: per view the highest-scoring detection is used. Multi-person association
and tracking arrive in V2.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import time
from pathlib import Path

import numpy as np
from websockets.asyncio.client import connect
from websockets.asyncio.server import ServerConnection, serve

from .calibration import Calibration, load
from .messages import Person3D, Pose2D, Skeleton3D
from .triangulate import triangulate_skeleton

log = logging.getLogger("fusion")


def fuse_frame(calibs: dict[str, Calibration], poses: dict[str, Pose2D]) -> Skeleton3D:
    """Pure function: poses for one frame_id -> Skeleton3D. No person if seen in <2 views."""
    views = []
    for cam_id, pose in poses.items():
        if cam_id in calibs and pose.people:
            best = max(pose.people, key=lambda p: p.score)
            views.append((cam_id, np.array(best.keypoints, dtype=np.float64)))
    any_pose = next(iter(poses.values()))
    people: list[Person3D] = []
    if len(views) >= 2:
        res = triangulate_skeleton([calibs[c] for c, _ in views], [k for _, k in views])
        joints: list[list[float] | None] = [
            None if r is None else [*map(float, r.point), r.confidence] for r in res
        ]
        if sum(j is not None for j in joints) >= 4:
            people.append(
                Person3D(
                    track_id=0,
                    joints=joints,
                    partial=any(j is None for j in joints),
                    views=[c for c, _ in views],
                )
            )
    return Skeleton3D(
        frame_id=any_pose.frame_id,
        t_capture=any_pose.t_capture,
        t_fused=time.time(),
        people=people,
        cameras_used=[c for c, _ in views],
        cameras_down=sorted(set(calibs) - set(poses)),
    )


class Fusion:
    def __init__(self, calibs: dict[str, Calibration], window_s: float = 0.15):
        self.calibs = calibs
        self.window_s = window_s
        self.pending: dict[int, tuple[float, dict[str, Pose2D]]] = {}
        self.last_emitted = -1
        self.subscribers: set[ServerConnection] = set()
        self.last_seen: dict[str, float] = {}

    def add(self, pose: Pose2D) -> None:
        self.last_seen[pose.camera_id] = time.monotonic()
        if pose.frame_id <= self.last_emitted:
            return  # late result for a frame already emitted
        _, group = self.pending.setdefault(pose.frame_id, (time.monotonic(), {}))
        group[pose.camera_id] = pose

    def ready(self, now: float) -> list[Skeleton3D]:
        out = []
        for fid in sorted(self.pending):
            t0, group = self.pending[fid]
            if len(group) == len(self.calibs) or now - t0 > self.window_s:
                skel = fuse_frame(self.calibs, group)
                skel.cameras_down = sorted(
                    c for c in self.calibs if now - self.last_seen.get(c, -1e9) > 1.0
                )
                skel.timings_ms["fuse_wait_ms"] = (now - t0) * 1000
                out.append(skel)
                self.last_emitted = fid
                del self.pending[fid]
        for fid in [f for f in self.pending if f < self.last_emitted]:
            del self.pending[fid]
        return out

    async def publish(self, skel: Skeleton3D) -> None:
        data = skel.model_dump_json()
        for ws in list(self.subscribers):
            try:
                await ws.send(data)
            except Exception:
                self.subscribers.discard(ws)

    async def pump(self) -> None:
        while True:
            for skel in self.ready(time.monotonic()):
                await self.publish(skel)
            await asyncio.sleep(0.01)

    async def read_node(self, url: str) -> None:
        while True:
            try:
                async with connect(url) as ws:
                    log.info("connected to %s", url)
                    async for data in ws:
                        self.add(Pose2D.model_validate_json(data))
            except Exception as e:
                log.warning("node %s unavailable: %s", url, e)
                await asyncio.sleep(1.0)


async def run(fusion: Fusion, node_urls: list[str], host: str, port: int) -> None:
    async def handler(ws: ServerConnection) -> None:
        fusion.subscribers.add(ws)
        try:
            await ws.wait_closed()
        finally:
            fusion.subscribers.discard(ws)

    async with serve(handler, host, port):
        log.info("fusion publishing Skeleton3D on ws://%s:%d", host, port)
        tasks = [asyncio.create_task(fusion.pump())] + [
            asyncio.create_task(fusion.read_node(u)) for u in node_urls
        ]
        try:
            await asyncio.Future()
        finally:
            for t in tasks:
                t.cancel()
            for t in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await t


def main() -> None:
    ap = argparse.ArgumentParser(prog="fusion")
    ap.add_argument("--calibration-dir", default="calibration")
    ap.add_argument("--nodes", nargs="+", required=True, help="ws://host:port/poses per camera")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9100)
    ap.add_argument("--window-ms", type=float, default=150)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    calibs = {c.id: c for c in map(load, sorted(Path(args.calibration_dir).glob("cam*.json")))}
    asyncio.run(run(Fusion(calibs, args.window_ms / 1000), args.nodes, args.host, args.port))


if __name__ == "__main__":
    main()
