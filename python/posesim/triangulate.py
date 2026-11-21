"""Weighted DLT triangulation with reprojection-based outlier rejection (ADR-0007)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .calibration import Calibration

N_JOINTS = 17


@dataclass
class Triangulated:
    point: np.ndarray  # (3,)
    errors: list[float]  # reprojection error in px, per used view
    used: list[int]  # indices into the input views
    confidence: float


def dlt(Ps: list[np.ndarray], xys: list[np.ndarray], weights: list[float]) -> np.ndarray:
    rows = []
    for P, xy, w in zip(Ps, xys, weights, strict=True):
        rows.append(w * (xy[0] * P[2] - P[0]))
        rows.append(w * (xy[1] * P[2] - P[1]))
    _, _, vt = np.linalg.svd(np.array(rows))
    X = vt[-1]
    return X[:3] / X[3]


def _errors(X: np.ndarray, Ps: list[np.ndarray], xys: list[np.ndarray]) -> list[float]:
    out = []
    for P, xy in zip(Ps, xys, strict=True):
        h = P @ np.append(X, 1.0)
        out.append(float(np.linalg.norm(h[:2] / h[2] - xy)))
    return out


def triangulate_point(
    Ps: list[np.ndarray],
    xys: list[np.ndarray],
    weights: list[float],
    max_error_px: float = 8.0,
) -> Triangulated | None:
    """Triangulate from >=2 views, using the largest view subset that passes the reprojection gate.

    Subsets are tried largest first; among passing subsets of equal size the lowest worst-case
    reprojection error wins. (Dropping the single worst view of a fit is unreliable, because a
    corrupt view drags the fit toward itself.)
    """
    n = len(Ps)
    for size in range(n, 1, -1):
        best: Triangulated | None = None
        best_worst = np.inf
        for subset in combinations(range(n), size):
            sel = list(subset)
            X = dlt([Ps[i] for i in sel], [xys[i] for i in sel], [weights[i] for i in sel])
            errs = _errors(X, [Ps[i] for i in sel], [xys[i] for i in sel])
            worst = max(errs)
            if worst <= max_error_px and worst < best_worst:
                conf = float(np.mean([weights[i] for i in sel]))
                best, best_worst = Triangulated(X, errs, sel, conf), worst
        if best is not None:
            return best
    return None


def triangulate_skeleton(
    calibs: list[Calibration],
    keypoints: list[np.ndarray],  # per view: (17, 3) distorted x, y, conf
    min_conf: float = 0.3,
    max_error_px: float = 8.0,
) -> list[Triangulated | None]:
    """One skeleton seen by several cameras -> 17 joints (None where not recoverable)."""
    undist = [c.undistort(k[:, :2]) for c, k in zip(calibs, keypoints, strict=True)]
    joints: list[Triangulated | None] = []
    for j in range(N_JOINTS):
        views = [i for i, k in enumerate(keypoints) if k[j, 2] >= min_conf]
        if len(views) < 2:
            joints.append(None)
            continue
        res = triangulate_point(
            [calibs[i].P for i in views],
            [undist[i][j] for i in views],
            [float(keypoints[i][j, 2]) for i in views],
            max_error_px,
        )
        if res is not None:
            res.used = [views[u] for u in res.used]
        joints.append(res)
    return joints
