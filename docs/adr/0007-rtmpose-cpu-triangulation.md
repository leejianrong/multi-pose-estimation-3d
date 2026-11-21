# ADR-0007: Top-down 2D pose with RTMPose on CPU, 3D by multi-view triangulation

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

Each camera node must run in real time on a CPU or Intel integrated graphics, for 3–5 people. Calibration is known (virtual cameras now, real later). Skeleton format is COCO-17.

## Decision

- Per node: person detector (YOLOX-tiny or nano) every N frames with box propagation between, then RTMPose (tiny/small) per box, via `rtmlib` with ONNX Runtime (CPU execution provider; OpenVINO provider is an option for the real mini PCs). Input resolution 640×480.
- Fusion: match 2D skeletons across views by epipolar distance (Hungarian assignment on pairwise cost), triangulate each joint with weighted DLT using ≥2 confident views, reject outliers by reprojection error, smooth with a constant-velocity filter, assign stable `track_id` with Hungarian matching on 3D distance.
- A person visible in fewer than 2 views yields no 3D skeleton for that frame; the track coasts for up to 0.5 s.
- No learned 3D lifting model.

## Alternatives considered

| Option | Why not |
|---|---|
| MediaPipe Pose | Single-person model; multi-person needs external detector crops. Kept as a fallback if RTMPose is too slow. |
| Ultralytics YOLO-pose | AGPL (ADR-0006). |
| OpenPose | Restrictive non-commercial licence, heavy. |
| Monocular 3D lifting | Less accurate than 3 calibrated views; scale ambiguity. |

## Consequences

- Latency/accuracy are tunable via model size, detector interval, input resolution.
- Models are trained on real photos; synthetic avatars may degrade detections. V1 measures this and may drive avatar choices.
- Top-down cost grows with person count; 5 people is the MVP ceiling.
- Licences of `rtmlib` and the RTMPose/YOLOX ONNX weights are assumed Apache-2.0 and must be checked in V1.
