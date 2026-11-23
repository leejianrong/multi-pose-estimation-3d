"""Camera calibration records (ADR-0003). Same schema for virtual and real cameras."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel, field_validator, model_validator

Matrix3 = list[list[float]]


class Calibration(BaseModel):
    version: int = 1
    id: str
    width: int
    height: int
    K: Matrix3
    dist: list[float]
    R: Matrix3  # world -> camera (OpenCV: x right, y down, z forward)
    t: list[float]  # world -> camera translation, metres

    @field_validator("K", "R")
    @classmethod
    def _3x3(cls, v: Matrix3) -> Matrix3:
        if len(v) != 3 or any(len(r) != 3 for r in v):
            raise ValueError("must be 3x3")
        return v

    @field_validator("t")
    @classmethod
    def _len3(cls, v: list[float]) -> list[float]:
        if len(v) != 3:
            raise ValueError("t must have 3 elements")
        return v

    @field_validator("dist")
    @classmethod
    def _dist(cls, v: list[float]) -> list[float]:
        if len(v) not in (4, 5, 8):
            raise ValueError("dist must have 4, 5 or 8 coefficients")
        return v

    @model_validator(mode="after")
    def _rotation(self) -> Calibration:
        R = np.array(self.R)
        if not np.allclose(R @ R.T, np.eye(3), atol=1e-6) or np.linalg.det(R) < 0:
            raise ValueError("R is not a proper rotation matrix")
        return self

    @property
    def K_np(self) -> np.ndarray:
        return np.array(self.K, dtype=np.float64)

    @property
    def dist_np(self) -> np.ndarray:
        return np.array(self.dist, dtype=np.float64)

    @property
    def R_np(self) -> np.ndarray:
        return np.array(self.R, dtype=np.float64)

    @property
    def t_np(self) -> np.ndarray:
        return np.array(self.t, dtype=np.float64)

    @property
    def center(self) -> np.ndarray:
        """Camera centre in the room frame."""
        return -self.R_np.T @ self.t_np

    @property
    def P(self) -> np.ndarray:
        """3x4 projection matrix for undistorted pixel coordinates."""
        return self.K_np @ np.hstack([self.R_np, self.t_np.reshape(3, 1)])

    def project(self, X: np.ndarray) -> np.ndarray:
        """Project Nx3 room points to undistorted pixels (Nx2)."""
        X = np.atleast_2d(X)
        h = (self.P @ np.hstack([X, np.ones((len(X), 1))]).T).T
        return h[:, :2] / h[:, 2:3]

    def undistort(self, xy: np.ndarray) -> np.ndarray:
        """Distorted pixels (Nx2) -> undistorted pixels (Nx2) in the same K."""
        xy = np.asarray(xy, dtype=np.float64).reshape(-1, 1, 2)
        out = cv2.undistortPoints(xy, self.K_np, self.dist_np, P=self.K_np)
        return out.reshape(-1, 2)


def look_at(
    cam_id: str,
    position: tuple[float, float, float],
    target: tuple[float, float, float],
    vfov_deg: float,
    width: int = 640,
    height: int = 480,
    dist: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0),
) -> Calibration:
    """Build a calibration for a camera at `position` looking at `target` (room frame, Z up)."""
    C = np.array(position, dtype=np.float64)
    f = np.array(target, dtype=np.float64) - C
    f /= np.linalg.norm(f)
    right = np.cross(f, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(f, right)
    R = np.vstack([right, down, f])
    t = -R @ C
    fy = (height / 2) / np.tan(np.radians(vfov_deg) / 2)
    K = [[fy, 0.0, width / 2], [0.0, fy, height / 2], [0.0, 0.0, 1.0]]
    return Calibration(
        id=cam_id, width=width, height=height, K=K, dist=list(dist), R=R.tolist(), t=t.tolist()
    )


def load(path: Path | str) -> Calibration:
    return Calibration.model_validate(json.loads(Path(path).read_text()))


def save(calib: Calibration, path: Path | str) -> None:
    Path(path).write_text(json.dumps(calib.model_dump(), indent=2) + "\n")
