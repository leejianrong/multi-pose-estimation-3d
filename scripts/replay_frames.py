"""Run the pose estimator over dumped frames (run_scenario --dump-frames) and report detections.

Fast offline loop for tuning the model, thresholds and avatar without the sim.
usage: replay_frames.py <frames_dir> [--out overlay_dir] [--det-score 0.4]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from posesim.pose import RtmPoseEstimator


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--det-score", type=float, default=0.4)
    ap.add_argument("--step", type=int, default=1)
    args = ap.parse_args()
    est = RtmPoseEstimator(threads=8, det_score_thr=args.det_score)
    files = sorted(args.frames_dir.glob("*.jpg"))[:: args.step]
    stats: dict[str, list[int]] = {}
    for f in files:
        img = cv2.imread(str(f))
        if img is None:
            continue
        people, _ = est(img)
        cam = f.name.split("_")[0]
        stats.setdefault(cam, []).append(len(people))
        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            for p in people:
                for x, y, c in p.keypoints:
                    if c > 0.3:
                        cv2.circle(img, (int(x), int(y)), 3, (0, 255, 255), -1)
                x1, y1, x2, y2 = map(int, p.bbox)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 0), 1)
            cv2.imwrite(str(args.out / f.name), img)
    for cam, n in sorted(stats.items()):
        print(f"{cam}: detected in {np.mean(np.array(n) > 0):.0%} of {len(n)} frames")


if __name__ == "__main__":
    main()
