# ADR-0002: Three camera-node processes send 2D keypoints to one fusion service

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

The real installation is three cameras, each wired to its own mini PC (Intel integrated graphics, CPU inference), connected by Ethernet to a central laptop that shows a dashboard. The sim runs on one laptop for now. Splitting later is expensive if the first version is a monolith that passes images in memory.

## Decision

- **`camera-node`** (Python process, one per camera): receives frames for its camera ID from a frame source (ADR-0003), runs person detection + 2D pose (ADR-0007), emits `Pose2D` messages: `{camera_id, t_capture, frame_id, people: [{bbox, keypoints[17]: x,y,conf}]}`. No cross-camera knowledge.
- **`fusion`** (Python process): consumes `Pose2D` from N nodes, associates people across views, triangulates, tracks, emits `Skeleton3D` messages.
- **`app`** (browser): sim, dashboard, gesture engine, audio. Consumes `Skeleton3D`.
- Transport: WebSocket (JSON for poses; binary JPEG only for frames going sim→node). Images never reach `fusion` or `app` on the wire, matching what the real network would carry.
- In the sim, all processes run on localhost. Each node is configured with a host/port so it can run on another machine unchanged.
- Messages carry capture timestamps; fusion groups by timestamp window, not arrival order.

## Alternatives considered

| Option | Why not |
|---|---|
| One Python process doing everything | Cannot validate the real topology or per-node CPU budget; rewrite on deployment. |
| Ship all frames to the laptop and infer centrally | Not the planned hardware, and 3×720p streams are wasteful on Ethernet. |
| Pose inference in the browser (ONNX Runtime Web / MediaPipe JS) | Cannot mirror mini-PC deployment; weaker model options. |

## Consequences

- Buys: the real deployment is a config change; per-node CPU cost is measurable in isolation; edge/central bandwidth is realistic (kilobytes of keypoints).
- Costs: on one laptop, 3 nodes + fusion + browser compete for CPU, so the single-laptop FPS is a pessimistic proxy.
- Costs: time sync is only trivial on localhost. Real deployment needs NTP/PTP, deferred (QUESTIONS Q31).
- Forecloses: 3D pose lifting models that need all views' images at once.
