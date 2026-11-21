# ADR-0004: Gestures are rule-based detectors on 3D keypoints behind a swappable interface

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

The MVP needs six actions to trigger sound. The user wants to explore a learned action classifier later.

## Decision

- Six detectors, each a pure function over a short sliding window of `Skeleton3D` (≈1 s) plus object geometry: `approach/leave`, `arms_raised`, `reach_touch`, `sit`, `crouch`, `wave`.
- Interface: `GestureDetector.update(person_window, scene) -> GestureEvent[]`, with `GestureEvent {name, person_id, object_id|null, t, confidence}`. A learned classifier later implements the same interface.
- Thresholds live in a config file, not in code.
- Every run can log labelled-by-the-sim skeleton windows (the sim knows which clip is playing) as JSONL, forming a free training set for the future classifier. Logging only; training is out of scope.
- Skeleton coordinates are normalised to the room frame, Z up, metres; detectors use joint heights and distances, not image coordinates.

## Alternatives considered

| Option | Why not |
|---|---|
| Learned classifier now (e.g. ST-GCN) | Needs data and training; not needed to prove the loop. |
| Gesture logic inside the 2D nodes | Cannot use 3D geometry or object proximity. |

## Consequences

- Testable with synthetic skeleton windows, no vision required.
- Rules are brittle to pose-estimator noise; hysteresis and minimum durations are required and tuned against the scripted clips.
- `sit` and `crouch` are confusable at low camera heights; accuracy is measured, not assumed.
