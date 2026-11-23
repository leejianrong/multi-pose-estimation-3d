import numpy as np
import pytest

from posesim.calibration import Calibration, look_at
from posesim.triangulate import triangulate_point, triangulate_skeleton

CAMS = [
    look_at("cam0", (-3.5, -2.5, 2.8), (0, 0, 1.0), 60),
    look_at("cam1", (3.5, -2.5, 2.8), (0, 0, 1.0), 60),
    look_at("cam2", (0.0, 3.0, 2.8), (0, 0, 1.0), 60),
]


def proj(X):
    return [c.project(X)[0] for c in CAMS]


def test_recovers_known_point_within_1mm():
    X = np.array([0.4, -0.3, 1.2])
    res = triangulate_point([c.P for c in CAMS], proj(X), [1, 1, 1])
    assert res is not None
    assert np.linalg.norm(res.point - X) < 1e-3


def test_rejects_grossly_wrong_view():
    X = np.array([0.4, -0.3, 1.2])
    pts = proj(X)
    pts[2] = pts[2] + np.array([120.0, -80.0])
    res = triangulate_point([c.P for c in CAMS], pts, [1, 1, 1], max_error_px=5)
    assert res is not None
    assert res.used == [0, 1]
    assert np.linalg.norm(res.point - X) < 1e-3


def test_two_inconsistent_views_return_none():
    X = np.array([0.4, -0.3, 1.2])
    pts = proj(X)
    pts[1] = pts[1] + np.array([150.0, 0.0])
    assert triangulate_point([CAMS[0].P, CAMS[1].P], pts[:2], [1, 1], max_error_px=5) is None


def test_skeleton_needs_two_confident_views_per_joint():
    X = np.random.default_rng(0).uniform([-1, -1, 0.2], [1, 1, 1.8], (17, 3))
    kps = []
    for c in CAMS:
        k = np.hstack([c.project(X), np.ones((17, 1))])
        kps.append(k)
    kps[0][5, 2] = 0.0
    kps[1][5, 2] = 0.0  # joint 5 only seen by one view
    out = triangulate_skeleton(CAMS, kps)
    assert out[5] is None
    assert all(o is not None for i, o in enumerate(out) if i != 5)
    assert np.linalg.norm(out[0].point - X[0]) < 1e-3  # type: ignore[union-attr]


def test_undistort_recovers_projection():
    c = look_at("d", (-3, -3, 2.5), (0, 0, 1), 60, dist=(-0.2, 0.05, 0.001, -0.001, 0.0))
    X = np.array([[0.5, 0.2, 1.0]])
    ideal = c.project(X)
    # distort the ideal pixel with the same model
    import cv2

    xn = np.linalg.inv(c.K_np) @ np.append(ideal[0], 1.0)
    obj = np.array([[xn[0], xn[1], 1.0]])
    d, _ = cv2.projectPoints(obj, np.zeros(3), np.zeros(3), c.K_np, c.dist_np)
    back = c.undistort(d.reshape(-1, 2))
    assert np.linalg.norm(back - ideal) < 0.5


def test_calibration_round_trips_and_rejects_bad_rotation(tmp_path):
    from posesim.calibration import load, save

    save(CAMS[0], tmp_path / "c.json")
    assert load(tmp_path / "c.json") == CAMS[0]
    bad = CAMS[0].model_dump()
    bad["R"] = [[2, 0, 0], [0, 1, 0], [0, 0, 1]]
    with pytest.raises(ValueError):
        Calibration.model_validate(bad)


def test_camera_looks_at_target():
    c = CAMS[0]
    p = c.project(np.array([[0.0, 0.0, 1.0]]))[0]
    assert np.allclose(p, [320, 240], atol=1e-6)
