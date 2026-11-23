"""Sim-style frames -> camera-node (fake estimator) -> fusion -> Skeleton3D over real WebSockets."""

import asyncio

import cv2
import numpy as np
import pytest
from websockets.asyncio.client import connect

from posesim.calibration import look_at
from posesim.camera_node import CameraNode, serve_node
from posesim.frame_source import SimSource
from posesim.fusion import Fusion, run
from posesim.messages import Person2D, Skeleton3D, pack_frame

pytestmark = pytest.mark.integration
X = np.random.default_rng(2).uniform([-0.5, -0.5, 0.1], [0.5, 0.5, 1.8], (17, 3))


def jpeg() -> bytes:
    ok, buf = cv2.imencode(".jpg", np.zeros((480, 640, 3), np.uint8))
    assert ok
    return buf.tobytes()


@pytest.mark.asyncio
async def test_frames_to_skeleton_over_websockets():
    calibs = {
        "cam0": look_at("cam0", (-3.6, -2.6, 2.8), (0, 0, 1.0), 60),
        "cam1": look_at("cam1", (3.6, -2.6, 2.8), (0, 0, 1.0), 60),
    }

    def make_estimator(cam):
        def est(_img):
            kp = np.hstack([calibs[cam].project(X), np.full((17, 1), 0.9)])
            return [Person2D(bbox=[0, 0, 1, 1], score=0.9, keypoints=kp.tolist())], {}

        return est

    ports = {"cam0": 19101, "cam1": 19102}
    tasks = []
    for cam, port in ports.items():
        src = SimSource()
        node = CameraNode(cam, src, make_estimator(cam))
        tasks.append(asyncio.create_task(serve_node(node, src, "127.0.0.1", port)))
    fusion = Fusion(calibs)
    tasks.append(
        asyncio.create_task(
            run(fusion, [f"ws://127.0.0.1:{p}/poses" for p in ports.values()], "127.0.0.1", 19100)
        )
    )
    try:
        await asyncio.sleep(0.5)
        async with connect("ws://127.0.0.1:19100") as out:
            senders = [await connect(f"ws://127.0.0.1:{p}/frames") for p in ports.values()]
            await asyncio.sleep(0.3)
            for s, cam in zip(senders, ports, strict=True):
                await s.send(
                    pack_frame({"camera_id": cam, "frame_id": 1, "t_capture": 0.0}, jpeg())
                )
            skel = Skeleton3D.model_validate_json(await asyncio.wait_for(out.recv(), 5))
            est = np.array([j[:3] for j in skel.people[0].joints])  # type: ignore[index]
            assert skel.frame_id == 1 and np.abs(est - X).max() < 1e-3
            for s in senders:
                await s.close()
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
