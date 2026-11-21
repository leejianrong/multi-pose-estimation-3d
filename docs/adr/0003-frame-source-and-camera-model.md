# ADR-0003: Cameras are described by an OpenCV calibration model behind a frame-source interface

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

The sim must eventually approximate real cameras, including lens distortion, noise and exposure, and the same pipeline must later ingest real camera streams. three.js renders ideal pinhole images.

## Decision

- Each camera has a calibration record (JSON): `{id, width, height, K (3×3), dist (OpenCV k1,k2,p1,p2,k3), R, t (room frame, metres)}`. Same schema for virtual and real cameras.
- `FrameSource` interface, consumed by `camera-node`: yields `(camera_id, t_capture, image)`. Implementations: `SimSource` (frames pushed from the browser), later `VideoFileSource` and `RtspSource`.
- Realism is applied **on the Python side**, between the raw render and the pose model: `cv2` distort (using the camera's `dist`), optional blur, noise, exposure. The browser always renders ideal pinhole. The pose model therefore sees the same kind of image a real camera would give.
- `fusion` undistorts 2D keypoints with `cv2.undistortPoints` using the same calibration before triangulating, so the correction path is identical in sim and reality.
- Initial virtual cameras: distortion zero (pinhole), identity of the schema established from V1; non-zero distortion and degradations arrive in V7.

## Alternatives considered

| Option | Why not |
|---|---|
| Distort in a three.js shader | Duplicates the realism logic in a second language; real-camera path would not use it. |
| Render with Blender Cycles for true lens effects | Offline only; revisit as an extra `FrameSource`. |
| Ignore distortion until real hardware | The user explicitly wants to rehearse this; late discovery is costly. |

## Consequences

- Buys: sim → real is a `FrameSource` swap plus a calibration file; the degradation of accuracy with distortion is measurable.
- Costs: the distortion step adds per-frame CPU on each node (a `cv2.remap` with a cached map is cheap).
- Costs: virtual intrinsics are perfect, so sim accuracy is an upper bound on real accuracy. Real-camera calibration tooling is deferred.
