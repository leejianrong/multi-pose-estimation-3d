# Multi-person 3D pose → interactive sound sculpture sim: Plan

Status: draft · Milestone: MVP

## Problem

An interactive art installation is planned: a room with several sculptural, resin-coated fibreglass objects, visitors moving among them, three cameras estimating everyone's 3D pose, and stereo speakers playing sound that responds to where people are and what they do. Building that physically before knowing whether the sensing and sound design work is expensive. Camera placement, CPU budget on the mini PCs, and how multi-person occlusion affects pose accuracy are all unknown.

The sound must also hold together. Several people triggering several objects at once should read as music, not noise.

## Solution

A simulated room in the browser with 3–5 animated humans and 2–3 wavy, resin-looking objects. Three virtual cameras render the room; the frames go through the same pipeline as real cameras would: per-camera 2D pose on CPU, fusion into 3D skeletons, then proximity and gesture detection. Each object has a "personality" and plays its part in a shared musical key, tempo and chord progression, mixing synthesised voices with the user's recorded piano phrases and instrument samples. A dashboard shows the room, the estimated skeletons against ground truth, zones, gestures, timings and accuracy. Later the virtual cameras gain real-lens distortion and noise, and can be swapped for real cameras.

## Users and actors

- **Primary: the artist/builder (Jian)**, tuning the room, personalities, thresholds and recordings, and checking whether the plan is viable.
- Simulated visitors (3–5), objects (2–3), three cameras, two speakers.
- Future: a learned action classifier and real cameras on mini PCs.
- When actors conflict: ground truth from the sim is authoritative for scoring only; the pipeline output is authoritative for triggering sound.

## Scope

**In this milestone.**
- Browser three.js room, parametric wavy objects, rigged animated avatars (3–5).
- 3 virtual cameras, calibration schema, frame-source interface, pose pipeline on CPU split into 3 camera nodes + fusion.
- Multi-person tracking, proximity zones, 6 rule-based gestures.
- Conductor + personalities + synth and sample voices, stereo output.
- Dashboard, JSONL logs, accuracy and latency metrics, scripted scenarios, headless runner.
- Lens distortion, noise and exposure degradations.
- Public repo, Apache-2.0, asset licence log.

**Out.**
- Physical fabrication, resin/fibreglass simulation, structural or acoustic modelling.
- Real-camera calibration tooling and clock sync (schema ready; Q31, Q32).
- Learned action classifier training (hooks only; Q9).
- More than 5 people or 3 objects; VR; multi-user networking.
- Blender-rendered offline path (possible later `FrameSource`).
- Mini-PC hardware deployment.

## Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| R0 | 3–5 simulated people in a room are tracked in 3D from 3 CPU-only camera pipelines in real time, and their proximity and gestures near objects produce cohesive stereo music | Core goal |
| R1 | Room with rigged, animated humans (3–5) and 2–3 parametric wavy objects the size of a 1–2 seat sofa | Must-have |
| R2 | Cameras described by an OpenCV calibration; pipeline reads frames via a source interface so real cameras can replace virtual ones; sim can apply lens distortion, noise and exposure | Must-have |
| R3 | Multi-person 3D pose: median MPJPE ≤ 80 mm (pinhole), ≤ 120 mm (degraded); 0 identity switches on the scripted scenario; ≥ 10 FPS per camera node at 5 people on CPU | Must-have |
| R4 | Per-person, per-object proximity zones with hysteresis | Must-have |
| R5 | Six gestures detected with precision and recall ≥ 0.9 on scripted clips | Must-have |
| R6 | Each object has a personality; all sound follows one conductor (clock, key, progression); every scheduled pitched note belongs to the current chord/scale; motion → scheduled ≤ 300 ms p95, audible ≤ 500 ms p95 | Must-have |
| R7 | Voices can be synthesised or sample-based, with a tagged manifest for user recordings | Must-have |
| R8 | Dashboard and CLI report accuracy, FPS, latency, gestures, zones; runs are reproducible from a seed | Must-have |
| R9 | Repo is public, Apache-2.0, every asset licence logged | Must-have |
| R10 | Labelled skeleton-window logs for a future learned classifier | Nice-to-have |

## Shape

| Part | Mechanism | ADR |
|------|-----------|-----|
| S1 | **Sim app** (three.js + TS): loads `.glb` avatars, plays clips along scripted paths, renders room and objects, renders 3 offscreen camera views at 640×480 | 0001 |
| S2 | **Authoring**: Blender retargets CC0 avatars and CMU mocap to `.glb`; documented, optional to run | 0001, 0006 |
| S3 | **Frame transport**: sim → JPEG over WebSocket → `camera-node` for that camera, stamped with `t_capture`, `frame_id` | 0002, 0003 |
| S4 | **camera-node**: `FrameSource` → realism filter (distort/noise) → detector + RTMPose → `Pose2D` out | 0002, 0003, 0007 |
| S5 | **fusion**: undistort → epipolar association → triangulate → track → `Skeleton3D` out | 0002, 0007 |
| S6 | **Scene sensing** (in app): per-person pelvis → object footprint distance → zones with hysteresis; emits zone events | |
| S7 | **Gesture engine** (in app): six `GestureDetector`s over a sliding window; `GestureEvent` stream; optional labelled-window logging | 0004 |
| S8 | **Music engine** (in app, Tone.js): conductor, personalities, synth + sampler voices, sample manifest, stereo pan/gain | 0005 |
| S9 | **Dashboard** (in app): room view with GT vs estimated skeletons, camera previews with 2D overlays, zone/gesture timeline, FPS/latency/MPJPE panel | |
| S10 | **Scenario runner + metrics** (CLI): seeded scripted scenarios, headless run, JSON report, non-zero exit on missed targets | |
| S11 | **Object visual feedback**: emissive pulse driven by each object's audio amplitude | |

## Affordances

**UI.**

| Affordance | Place | Wires to |
|------------|-------|----------|
| Room view (orbit camera), GT and estimated skeletons | Dashboard | S1, S5 |
| Camera tiles with 2D keypoint overlay and per-node FPS | Dashboard | S4 |
| Zone and gesture timeline per person/object | Dashboard | S6, S7 |
| Metrics panel (MPJPE, ID switches, FPS, latency) | Dashboard | S10 |
| Conductor panel (tempo, key, chord, mute/solo per object) | Dashboard | S8 |
| Mode banner (pose service up / GT fallback) | Dashboard | S5 |
| Keyboard-controlled debug avatar | Room view | S1 |

**Non-UI.**

| Affordance | Kind | Wires to |
|------------|------|----------|
| `camera-node --camera cam0 --source sim --port 9001` | Service CLI | S4 |
| `fusion --nodes ws://…` | Service CLI | S5 |
| `scenario run <name> --json` | CLI | S10 |
| `calibration/*.json` | Config | S3, S4, S5 |
| `config/room.json`, `objects.json`, `personalities/*.json`, `gestures.json` | Config | S1, S6–S8 |
| `samples/manifest.json` | Config | S8 |
| `runs/<id>/*.jsonl` | Store | S10 |

## Implementation decisions

- **Contracts** (JSON, versioned): `Pose2D` and `Skeleton3D` (ADR-0002), `GestureEvent` (ADR-0004), `ZoneEvent {person_id, object_id, zone, t}`, calibration record (ADR-0003), personality and sample manifest (ADR-0005).
- **Coordinates**: room frame, metres, Z up, +Y front (speakers). Skeleton COCO-17.
- **Room**: 8 × 6 × 3 m; speakers at front wall L/R.
- **Cameras**: 3 at ~2.8 m, corners/edges aimed at room centre; pinhole until V7.
- **Objects**: seeded procedural meshes, ~1.8 × 0.9 × 0.8 m, clearcoat physical material; each has a `footprint` polygon for proximity.
- **Proximity**: pelvis (mean of hip joints) to footprint; zones far >2.0, near 1.0–2.0, close 0.3–1.0, touch <0.3 m; 0.15 m hysteresis.
- **Failure**: person in <2 views → no `Skeleton3D`, track coasts ≤0.5 s, no triggers; node/fusion down → dashboard banner, sim switches to GT-skeleton mode so audio can still be developed; no silent degradation.
- **Storage**: configs in git; run logs in `runs/` (gitignored); no database.
- **Security**: services bind to 127.0.0.1; no real video committed; nothing sensitive.
- **Versioning**: every config and message has a `version`; migrations deferred.
- **Process model**: three `camera-node`s + `fusion` as Python processes (managed with `uv`), the app via Vite dev server; one command starts all for the sim.
- **Assets**: logged in `ASSETS.md`; fetched by script with checksums (ADR-0006).

## Testing approach

Test at the highest seams that don't need a human: (1) the scenario runner, which drives the whole pipeline against seeded scripts and checks metrics against ground truth; (2) message-contract tests between services; (3) pure-function unit tests for triangulation, association, gesture detectors, proximity and conductor note selection, using synthetic skeletons and a mock clock. Audio is tested by asserting the scheduled event list (note, time, voice) rather than rendered sound; listening checks are manual and listed per slice. Per-slice plans are in `SLICES.md`.

## Assumed defaults

| ID | Assumed | Cost if wrong |
|----|---------|---------------|
| Q17 | RTMPose/YOLOX weights and rtmlib are Apache-2.0 | Swap model; V1 catches it |
| Q19 | Metric thresholds (80/120 mm, 10 FPS, 0.9 P/R, 300/500 ms) | Retune; they are config-level |
| Q22 | Camera height/positions | Rerun V1/V2 geometry; only config |
| Q25 | Zone distances | Config only |
| Q33 | Recordings in C major/A minor, I–vi–IV–V | Re-record or extend the manifest to more keys |
| Q34 | 1/16 quantisation acceptable for latency | Use 1/32 or free onset for some personalities |

## Open risks

- **Pose estimators on synthetic avatars** may fail or jitter. Earliest signal: V1.
- **Occlusion with 5 people from 3 cameras** may break association/tracking. V2.
- **Single-laptop CPU contention** (3 nodes + fusion + browser rendering 3 views) may miss 10 FPS. V1 measures, V2 confirms.
- **Rule-based `sit`/`crouch` confusion** at camera height. V4.
- **Cohesion is partly taste**: engine guarantees harmonic correctness, not beauty; needs the user's ears from V5.
- **Asset licences** were not verified at planning time. V1.
