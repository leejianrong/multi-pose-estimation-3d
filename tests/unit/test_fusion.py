import numpy as np

from posesim.calibration import look_at
from posesim.fusion import Fusion, fuse_frame
from posesim.messages import Person2D, Pose2D

CALIBS = {
    c.id: c
    for c in [
        look_at("cam0", (-3.6, -2.6, 2.8), (0, 0, 1.0), 60),
        look_at("cam1", (3.6, -2.6, 2.8), (0, 0, 1.0), 60),
        look_at("cam2", (0.0, 2.8, 2.8), (0, 0, 1.0), 60),
    ]
}
X = np.random.default_rng(1).uniform([-0.5, -0.5, 0.1], [0.5, 0.5, 1.8], (17, 3))


def pose(cam: str, frame_id: int = 1, visible: bool = True) -> Pose2D:
    if not visible:
        return Pose2D(camera_id=cam, frame_id=frame_id, t_capture=0.1, people=[])
    kp = np.hstack([CALIBS[cam].project(X), np.full((17, 1), 0.9)])
    return Pose2D(
        camera_id=cam,
        frame_id=frame_id,
        t_capture=0.1,
        people=[Person2D(bbox=[0, 0, 640, 480], score=0.9, keypoints=kp.tolist())],
    )


def test_three_views_recover_skeleton_within_1mm():
    skel = fuse_frame(CALIBS, {c: pose(c) for c in CALIBS})
    assert len(skel.people) == 1
    est = np.array([j[:3] for j in skel.people[0].joints])  # type: ignore[index]
    assert np.abs(est - X).max() < 1e-3
    assert not skel.people[0].partial


def test_two_views_still_work_and_flag_down_camera():
    skel = fuse_frame(CALIBS, {"cam0": pose("cam0"), "cam1": pose("cam1")})
    assert len(skel.people) == 1
    assert skel.cameras_down == ["cam2"]


def test_single_view_yields_no_skeleton():
    skel = fuse_frame(
        CALIBS,
        {
            "cam0": pose("cam0"),
            "cam1": pose("cam1", visible=False),
            "cam2": pose("cam2", visible=False),
        },
    )
    assert skel.people == []


def test_fusion_emits_when_all_cameras_arrive_without_waiting():
    f = Fusion(CALIBS)
    for c in CALIBS:
        f.add(pose(c, 5))
    out = f.ready(now=0.0)
    assert [s.frame_id for s in out] == [5]


def test_fusion_waits_for_window_then_emits_with_two_views():
    f = Fusion(CALIBS, window_s=0.15)
    f.add(pose("cam0", 7))
    f.add(pose("cam1", 7))
    import time

    t0 = time.monotonic()
    assert f.ready(t0) == []
    out = f.ready(t0 + 0.2)
    assert len(out) == 1 and len(out[0].people) == 1


def test_late_result_for_emitted_frame_is_ignored():
    f = Fusion(CALIBS)
    for c in CALIBS:
        f.add(pose(c, 9))
    f.ready(0.0)
    f.add(pose("cam0", 8))
    assert f.pending == {}
