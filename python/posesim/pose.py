"""2D person detection + pose on CPU (ADR-0007). Heavy imports are deferred."""

from __future__ import annotations

import time
from typing import Protocol

import numpy as np

from .messages import Person2D

DET_URL = (
    "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/"
    "yolox_tiny_8xb8-300e_humanart-6f3252f9.zip"
)
POSE_URL = (
    "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/"
    "rtmpose-s_simcc-body7_pt-body7_420e-256x192-acd4a1ef_20230504.zip"
)


class PoseEstimator(Protocol):
    def __call__(self, image: np.ndarray) -> tuple[list[Person2D], dict[str, float]]: ...


def _bbox_from_keypoints(kp: np.ndarray, sc: np.ndarray, shape: tuple[int, ...]) -> list[float]:
    ok = sc > 0.3
    pts = kp[ok] if ok.sum() >= 4 else kp
    x1, y1 = pts.min(axis=0)
    x2, y2 = pts.max(axis=0)
    w, h = (x2 - x1) * 1.25, (y2 - y1) * 1.25
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return [
        float(max(0, cx - w / 2)),
        float(max(0, cy - h / 2)),
        float(min(shape[1], cx + w / 2)),
        float(min(shape[0], cy + h / 2)),
    ]


class RtmPoseEstimator:
    """YOLOX-tiny every `det_interval` frames, RTMPose-s on every box every frame.

    Between detections the boxes are propagated from the previous frame's keypoints.
    """

    def __init__(self, det_interval: int = 1, device: str = "cpu", backend: str = "onnxruntime"):
        from rtmlib import YOLOX, RTMPose

        self.det = YOLOX(DET_URL, model_input_size=(416, 416), backend=backend, device=device)
        self.pose = RTMPose(POSE_URL, model_input_size=(192, 256), backend=backend, device=device)
        self.det_interval = max(1, det_interval)
        self._n = 0
        self._boxes: list[list[float]] = []

    def __call__(self, image: np.ndarray) -> tuple[list[Person2D], dict[str, float]]:
        t: dict[str, float] = {}
        t0 = time.perf_counter()
        if self._n % self.det_interval == 0 or not self._boxes:
            self._boxes = [list(map(float, b[:4])) for b in self.det(image)]
        self._n += 1
        t["det_ms"] = (time.perf_counter() - t0) * 1000
        if not self._boxes:
            return [], t
        t1 = time.perf_counter()
        kps, scs = self.pose(image, bboxes=self._boxes)
        t["pose_ms"] = (time.perf_counter() - t1) * 1000
        people, next_boxes = [], []
        for box, kp, sc in zip(self._boxes, kps, scs, strict=True):
            people.append(
                Person2D(
                    bbox=box,
                    score=float(np.mean(sc)),
                    keypoints=np.hstack([kp, sc[:, None]]).astype(float).tolist(),
                )
            )
            next_boxes.append(_bbox_from_keypoints(kp, sc, image.shape))
        self._boxes = next_boxes
        return people, t
