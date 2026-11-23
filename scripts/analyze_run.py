"""Offline analysis of a run made with --dump-frames: per-joint error, with and without L/R swap.

usage: analyze_run.py runs/<id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

from posesim.calibration import load
from posesim.fusion import fuse_frame
from posesim.messages import Pose2D
from posesim.pose import RtmPoseEstimator

EVAL = list(range(5, 17))
SWAP = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]


def main() -> None:
    run = Path(sys.argv[1])
    report = json.loads((run / "report.json").read_text())
    gt_all = report["gt_by_frame"]
    calibs = {c.id: c for c in map(load, sorted(Path("calibration").glob("cam*.json")))}
    est = {c: RtmPoseEstimator(threads=8, det_score_thr=0.3) for c in calibs}
    errs, errs_sw = [], []
    per_joint = np.zeros(17)
    n = 0
    for fid in sorted(map(int, gt_all)):
        poses = {}
        for cam in calibs:
            f = run / "frames" / f"{cam}_{fid:05d}.jpg"
            img = cv2.imread(str(f))
            if img is None:
                continue
            people, _ = est[cam](img)
            poses[cam] = Pose2D(camera_id=cam, frame_id=fid, t_capture=0, people=people)
        if len(poses) < 2:
            continue
        skel = fuse_frame(calibs, poses)
        if not skel.people:
            continue
        j = skel.people[0].joints
        gt = gt_all[str(fid)]
        for variant, store in ((list(range(17)), errs), (SWAP, errs_sw)):
            d = [
                np.linalg.norm(np.array(gt[i]) - np.array(j[variant[i]][:3]))
                for i in EVAL
                if gt[i] is not None and j[variant[i]] is not None
            ]
            if len(d) >= 6:
                store.append(float(np.mean(d)))
        for i in EVAL:
            if gt[i] is not None and j[i] is not None:
                per_joint[i] += np.linalg.norm(np.array(gt[i]) - np.array(j[i][:3]))
        n += 1
    print(f"frames with 3D: {n}")
    as_is, swapped = np.median(errs) * 1000, np.median(errs_sw) * 1000
    print(f"median MPJPE mm  as-is: {as_is:.0f}   L/R swapped: {swapped:.0f}")
    print("per-joint mean mm (as-is):", {i: round(per_joint[i] / max(n, 1) * 1000) for i in EVAL})


if __name__ == "__main__":
    main()
