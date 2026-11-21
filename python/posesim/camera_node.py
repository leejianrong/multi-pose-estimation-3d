"""camera-node: frames in, Pose2D out (ADR-0002). One process per camera.

WebSocket endpoints on one port: /frames (sim pushes frames), /poses (fusion subscribes).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import time

from websockets.asyncio.server import ServerConnection, serve

from .calibration import load
from .frame_source import FrameSource, SimSource
from .messages import Pose2D
from .pose import PoseEstimator, RtmPoseEstimator

log = logging.getLogger("camera_node")


class CameraNode:
    def __init__(self, camera_id: str, source: FrameSource, estimator: PoseEstimator):
        self.camera_id = camera_id
        self.source = source
        self.estimator = estimator
        self.subscribers: set[ServerConnection] = set()
        self.processed = 0
        self._t_start = time.perf_counter()

    @property
    def fps(self) -> float:
        return self.processed / max(1e-6, time.perf_counter() - self._t_start)

    async def publish(self, msg: Pose2D) -> None:
        data = msg.model_dump_json()
        for ws in list(self.subscribers):
            try:
                await ws.send(data)
            except Exception:
                self.subscribers.discard(ws)

    async def run(self) -> None:
        async for frame in self.source.frames():
            t0 = time.perf_counter()
            people, timings = await asyncio.to_thread(self.estimator, frame.image)
            timings["decode_ms"] = frame.decode_ms
            timings["node_total_ms"] = (time.perf_counter() - t0) * 1000 + frame.decode_ms
            self.processed += 1
            await self.publish(
                Pose2D(
                    camera_id=self.camera_id,
                    frame_id=frame.frame_id,
                    t_capture=frame.t_capture,
                    people=people,
                    timings_ms=timings,
                )
            )


async def serve_node(node: CameraNode, source: SimSource, host: str, port: int) -> None:
    async def handler(ws: ServerConnection) -> None:
        path = ws.request.path if ws.request else ""
        if path.endswith("/poses"):
            node.subscribers.add(ws)
            try:
                await ws.wait_closed()
            finally:
                node.subscribers.discard(ws)
        elif path.endswith("/frames"):
            async for data in ws:
                if isinstance(data, bytes):
                    try:
                        source.push(data)
                    except ValueError as e:
                        log.warning("bad frame dropped: %s", e)
        elif path.endswith("/status"):
            await ws.send(json.dumps({"camera_id": node.camera_id, "fps": node.fps}))
        else:
            await ws.close(code=1008, reason="unknown path")

    async with serve(handler, host, port, max_size=8 * 1024 * 1024):
        log.info("%s listening on ws://%s:%d (/frames, /poses)", node.camera_id, host, port)
        task = asyncio.create_task(node.run())
        try:
            await asyncio.Future()
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def main() -> None:
    ap = argparse.ArgumentParser(prog="camera-node")
    ap.add_argument("--camera", required=True)
    ap.add_argument("--calibration", required=True, help="calibration JSON for this camera")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--det-interval", type=int, default=1)
    ap.add_argument("--threads", type=int, default=4, help="ONNX Runtime threads for this node")
    ap.add_argument("--det-score", type=float, default=0.4)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    calib = load(args.calibration)
    if calib.id != args.camera:
        raise SystemExit(f"calibration id {calib.id!r} does not match --camera {args.camera!r}")
    source = SimSource()
    node = CameraNode(
        args.camera,
        source,
        RtmPoseEstimator(
            det_interval=args.det_interval, threads=args.threads, det_score_thr=args.det_score
        ),
    )
    asyncio.run(serve_node(node, source, args.host, args.port))


if __name__ == "__main__":
    main()
