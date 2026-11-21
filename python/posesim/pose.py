"""2D person detection + pose on CPU (ADR-0007). Heavy imports are deferred."""

from __future__ import annotations

import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path
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


@contextlib.contextmanager
def _download_lock() -> Iterator[None]:
    """rtmlib's first-run download is not safe for concurrent processes; serialise it."""
    try:
        import fcntl
    except ImportError:  # non-POSIX: no lock
        yield
        return
    lock = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "posesim-model.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _limit_ort_threads(threads: int) -> None:
    """rtmlib builds its ONNX sessions without options; cap threads so 3 nodes can share a CPU."""
    import onnxruntime as ort

    original = ort.InferenceSession
    if getattr(original, "_posesim_patched", False):
        return

    def patched(*args, **kwargs):
        opts = kwargs.pop("sess_options", None) or ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        return original(*args, sess_options=opts, **kwargs)

    patched._posesim_patched = True  # type: ignore[attr-defined]
    ort.InferenceSession = patched  # type: ignore[misc,assignment]


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

    def __init__(
        self,
        det_interval: int = 1,
        device: str = "cpu",
        backend: str = "onnxruntime",
        threads: int = 4,
        det_score_thr: float = 0.4,
    ):
        from rtmlib import YOLOX, RTMPose

        _limit_ort_threads(threads)

        with _download_lock():
            self.det = YOLOX(
                DET_URL,
                model_input_size=(416, 416),
                score_thr=det_score_thr,
                backend=backend,
                device=device,
            )
            self.pose = RTMPose(
                POSE_URL, model_input_size=(192, 256), backend=backend, device=device
            )
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
