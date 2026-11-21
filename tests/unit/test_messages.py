import pytest

from posesim.messages import Person2D, Pose2D, Skeleton3D, pack_frame, unpack_frame


def test_frame_round_trip():
    h, j = unpack_frame(
        pack_frame({"camera_id": "cam0", "frame_id": 3, "t_capture": 0.1}, b"\xff\xd8x")
    )
    assert h["frame_id"] == 3 and j == b"\xff\xd8x"


def test_truncated_frame_is_rejected():
    with pytest.raises(ValueError):
        unpack_frame(b"\x00\x00\x00\xffabc")


def test_pose2d_requires_17_keypoints():
    with pytest.raises(ValueError):
        Person2D(bbox=[0, 0, 1, 1], score=1, keypoints=[[0, 0, 1]] * 16)
    Pose2D(camera_id="c", frame_id=1, t_capture=0.0, people=[])


def test_skeleton3d_schema_exports():
    assert "people" in Skeleton3D.model_json_schema()["properties"]
