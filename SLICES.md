# Multi-person 3D pose → interactive sound sculpture sim: Slices

Vertical increments. Each ends in something you can demonstrate. Slice 1 confronts the riskiest unknown: whether a real pose model, run on CPU on rendered avatars, triangulates to usable 3D.

## V1: One avatar, three views, 3D skeleton

**Delivers:** R0 (partial), R1 (partial), R2 (partial), R3 (single person), R9 (partial)

**Build plan**

1. Repo skeleton: Apache-2.0 `LICENSE`, `ASSETS.md`, `uv` Python project, Vite + TS app. One start command.
2. Choose one CC0 realistic rigged avatar and a walk/idle/wave clip (CMU mocap retargeted in Blender, or CC0 pack). Verify and log licences before committing.
3. three.js room, avatar playing a clip, 3 virtual cameras at calibration-schema poses; export `calibration/*.json`.
4. Offscreen render per camera at 640×480, JPEG over WebSocket with `t_capture`, `frame_id`.
5. `camera-node`: `SimSource`, detector + RTMPose via `rtmlib`/ONNX CPU, emit `Pose2D`. Verify model and `rtmlib` licences.
6. `fusion`: undistort (identity), triangulate (weighted DLT, reprojection rejection), emit `Skeleton3D`.
7. Dashboard: room view showing GT skeleton vs estimated skeleton; camera tiles with 2D overlay; MPJPE, per-node FPS.
8. Record per-stage timings (render, encode, detect, pose, fuse).

**Demo:** run the start command, watch the avatar walk and wave. The estimated skeleton follows the ground-truth skeleton in the room view. MPJPE and per-node FPS shown live.

**Rests on assumptions:** Q17 (model licences and quality on avatars), Q22 (camera layout). If the pose model fails on avatars, V1 reveals it and drives an avatar change (more realistic skin/clothing) or a different model.

### Test plan

#### End-to-end

- Scripted 20 s single-avatar scenario: median MPJPE ≤ 80 mm over frames with ≥2 views.
- Same scenario: per-node FPS ≥ 10 sustained on this machine, reported in the metrics file.
- ≥ 95 % of frames yield a `Skeleton3D`.
- `ASSETS.md` lists source and licence for every committed asset, and the check script fails when one is missing.

#### Integration

- Sim → node → fusion with a recorded set of frames reproduces identical `Skeleton3D` JSON (determinism with a seed).
- `Pose2D` and `Skeleton3D` messages validate against their JSON schemas.
- Killing a node: fusion keeps running with 2 views and flags the camera down.

#### Unit

- Triangulation recovers a known 3D point from three synthetic projections within 1 mm.
- Triangulation rejects a point with one grossly wrong view.
- Calibration loader round-trips `K`, `dist`, `R`, `t` and rejects malformed records.

## V2: 3–5 people, tracked

**Delivers:** R0 (partial), R1, R3

**Build plan**

1. Multiple avatars on scripted waypoint paths with seeded randomisation; crossing and occlusion segments included.
2. Detector with interval + box propagation to bound cost with person count.
3. Fusion: epipolar Hungarian association across views, per-person triangulation, constant-velocity tracker with stable `track_id`, coast ≤ 0.5 s.
4. Dashboard: track IDs, colours, ID-switch counter, per-node FPS vs person count.
5. Scenario runner (CLI) with `--json` output and non-zero exit on missed targets.

**Demo:** run the 5-person crossing scenario; each person keeps a stable colour/ID in the room view, and the report prints MPJPE, ID switches, FPS.

**Rests on assumptions:** Q26 (epipolar matching suffices), Q19 (≥10 FPS at 5 people on one laptop). If FPS misses, drop to 4 people or smaller models before changing architecture.

### Test plan

#### End-to-end

- 5-person scenario: median MPJPE ≤ 80 mm, 0 ID switches, ≥ 10 FPS per node.
- 3-person scenario with two people crossing: identities preserved after crossing.
- Scenario runner exits non-zero if any target is missed, 0 otherwise, and writes a JSON report.

#### Integration

- Fusion given scripted `Pose2D` streams (no vision) with two people crossing keeps IDs.
- A person seen by only one camera yields no `Skeleton3D` and is flagged `partial`.

#### Unit

- Epipolar cost is lower for correct cross-view pairs than for wrong ones on synthetic data.
- Hungarian assignment is stable under a swapped input order.
- Tracker coasts for 0.5 s and then drops the track.

## V3: Objects, proximity, first sound

**Delivers:** R1 (complete), R4, R6 (partial), R8 (partial)

**Build plan**

1. Seeded procedural wavy objects (2–3), clearcoat material, footprint polygons, placed from `config/objects.json`.
2. Proximity zones with hysteresis from `Skeleton3D`; `ZoneEvent` stream; timeline in dashboard.
3. Emissive pulse on object when a person is `close`.
4. Minimal Tone.js output: a per-object test tone, stereo-panned by object x, gain by proximity. Clock/key not yet cohesive.

**Demo:** walk an avatar toward an object, the dashboard shows far → near → close → touch, the object pulses, and its tone rises in level, panned toward that object's side.

**Rests on assumptions:** Q24 (procedural shape reads as sculpture), Q25 (zone distances), Q27 (stereo pan by object x).

### Test plan

#### End-to-end

- Scenario with one avatar walking to each object: zone event sequence for each object is exactly far→near→close→touch→(leaving)→far with no flicker (≤1 transition per zone boundary crossing).
- Same seed gives identical object meshes (vertex hash equal).
- Two objects at left/right produce left-/right-weighted stereo gain (checked on the audio graph, not by ear).

#### Integration

- `Skeleton3D` stream → `ZoneEvent` stream with a mock clock.
- Object footprints match mesh bounds within 5 cm.

#### Unit

- Distance from point to polygon is correct inside, outside, and on edges.
- Hysteresis suppresses flicker for a signal jittering ±0.1 m around a boundary.

## V4: Six gestures

**Delivers:** R5, R10

**Build plan**

1. Animation clips for each gesture (arms raised, reach, sit, crouch, wave, walk in/out).
2. Six `GestureDetector`s over a ~1 s window; thresholds in `config/gestures.json`.
3. `GestureEvent` stream, dashboard timeline, gesture log.
4. Labelled-window JSONL logging (sim knows the clip) for a future classifier.
5. Evaluation script: precision/recall per gesture on the scripted clips.

**Demo:** run the gesture scenario; each action by each avatar appears on the timeline with the right label near an object; a table shows P/R.

**Rests on assumptions:** Q4 (six gestures are separable from COCO-17), Q22 (camera height does not confuse sit/crouch). If sit/crouch is poor, tune heights or add the knee-angle rule before changing cameras.

### Test plan

#### End-to-end

- Scripted gesture scenario: precision and recall ≥ 0.9 for each of the six, through the full vision pipeline.
- Same scenario in GT-fallback mode: ≥ 0.98, isolating vision from rule errors.
- Label log contains one labelled window per scripted gesture instance.

#### Integration

- Gesture engine consumes `Skeleton3D` JSONL replay and emits identical events twice.
- `reach_touch` carries the correct `object_id`.

#### Unit

- Each detector fires on a synthetic positive window and not on negatives (standing, walking).
- Minimum-duration and cooldown logic drop sub-threshold blips.
- Detectors are insensitive to room-frame translation.

## V5: Conductor and personalities (synth only)

**Delivers:** R6, R7 (synth voices)

**Build plan**

1. Conductor: tempo, meter, key/mode, looping chord progression, 1/16 grid scheduling, conductor panel.
2. Personality JSON schema, four archetypes (e.g. shy, bold, playful, brooding), each with voice, register, degrees, gesture→action map, density, mood drift.
3. Note selection constrained to the current chord/scale; arpeggio/chord/texture actions.
4. Polyphony caps, cooldowns, master limiter, per-object mute/solo.
5. Latency instrumentation: gesture time → schedule time → audible time.

**Demo:** 3–5 avatars wander among 3 objects with the full pipeline running. Different objects respond with different characters but in the same key, pulse, and chords. Listen and judge whether it is cohesive.

**Rests on assumptions:** Q34 (1/16 quantisation acceptable), Q28 (polyphony caps), Q27. The artistic quality needs the user's ear; the harmonic correctness is checkable.

### Test plan

#### End-to-end

- 10-minute simulated run: 100 % of scheduled pitched notes belong to the current chord/scale at their onset.
- All onsets lie on the 1/16 grid within ±10 ms (scheduled time).
- p95 gesture→scheduled ≤ 300 ms and gesture→audible ≤ 500 ms from the latency log.
- Voice count per object never exceeds the cap; no `(person, object, gesture)` retrigger within the cooldown.
- Manual: user listens to the demo and records a pass/fail note on cohesion in the PR.

#### Integration

- Gesture events + mock clock → deterministic scheduled event list for a fixed seed.
- Muting an object removes its events from the schedule.

#### Unit

- Note picker only returns scale/chord tones for every mode and chord.
- Quantiser maps arbitrary onsets to the next grid slot.
- Personality schema validation rejects missing/unknown fields.
- Mood drift stays within bounds.

## V6: Samples and the user's recordings

**Delivers:** R7 (complete)

**Build plan**

1. `samples/manifest.json` schema and validator (instrument, kind, key/mode, chord function, tempo, bars, mood, licence, author).
2. Tone.js `Sampler` for notes; phrase/chord clip player quantised to the conductor.
3. Tag-based selection by conductor state; ±2 semitone pitch limit.
4. Recording guide in docs for the user (key, tempo, count-in, trimming, naming) plus a script that validates and normalises WAV/OGG.
5. Placeholder generated phrases until the user's recordings land; at least one third-party instrument set (piano, violin) with a verified redistributable licence or a fetch script.
6. Hybrid personalities: layer synth + sample; update archetype JSONs.

**Demo:** the same scenario now plays the user's piano chords and phrases and real instrument notes, in time with the conductor, with different personalities choosing different samples.

**Rests on assumptions:** Q33 (C major/A minor, I–vi–IV–V, 80–100 BPM recordings). If the user records in other keys, add them to the manifest; engine is unchanged.

### Test plan

#### End-to-end

- Run of 10 minutes: every played sample's tagged key/chord matches the conductor state at its onset.
- Missing/invalid samples are reported by the validator and the engine falls back to synth voices with a dashboard warning, never silence.
- Manual: user plays back the run and judges cohesion.

#### Integration

- Manifest + conductor state → selection returns the expected clip for a table of states.
- `ASSETS.md` check includes samples and fails when licence is missing.

#### Unit

- Manifest validator rejects malformed entries.
- Pitch-shift limiter refuses >2 semitones.
- Phrase scheduling aligns clip start to the next bar boundary.

## V7: Real-camera realism

**Delivers:** R2 (complete), R3 (degraded targets)

**Build plan**

1. Python realism stage in `camera-node`: OpenCV distortion from `dist`, blur, sensor noise, exposure, rolling-shutter-free; cached remap.
2. Calibration files for distorted virtual cameras; fusion undistorts with `undistortPoints` (already present, now non-identity).
3. `VideoFileSource` (prerecorded multi-camera clips) as a second `FrameSource`; stub `RtspSource` documented.
4. Degradation sweep script: MPJPE and FPS vs distortion strength, noise, exposure.
5. Docs on how to calibrate real cameras (deferred tooling, Q32).

**Demo:** same 5-person scenario with a wide-angle, noisy configuration. The dashboard shows distorted camera tiles and the report shows how much accuracy drops.

**Rests on assumptions:** Q19 degraded target (≤120 mm). If it fails, adjust models or camera count and record the finding in an ADR.

### Test plan

#### End-to-end

- 5-person scenario with moderate distortion and noise: median MPJPE ≤ 120 mm, 0 ID switches.
- Degradation sweep writes a report and fails if the baseline (zero degradation) is above the pinhole target.
- `VideoFileSource` replays a recorded clip through node and fusion with the same results as live sim frames.

#### Integration

- Distort then undistort a synthetic grid recovers point positions within 0.5 px.
- Calibration with `dist` ≠ 0 is accepted by node and fusion; mismatched calibrations produce a clear error.

#### Unit

- Distortion maps cached once per calibration and reused.
- Noise/exposure stage is deterministic for a seed.

## V8: Distributed run and CI gate

**Delivers:** R8 (complete), R9 (complete), R0 (complete)

**Build plan**

1. Run `camera-node`s on separate hosts/containers with configured addresses; measure bandwidth and latency; document the mini-PC deployment (Intel iGPU/OpenVINO option).
2. Timestamp-window fusion verified under added network jitter (injected delay).
3. CI: lint, unit, integration, and a short headless scenario gate; asset licence check; docs.
4. README with demo GIF, quick start, architecture figure.

**Demo:** run two nodes in separate containers with injected delay; metrics still pass and the README quick start works from a clean clone.

**Rests on assumptions:** Q31 (time sync deferred; localhost and containers share a clock). Real mini-PC clock skew is not covered.

### Test plan

#### End-to-end

- Clean clone → documented quick start → V2 scenario passes its metric gate.
- With 100 ms ± 30 ms injected network delay, MPJPE stays within 10 % of baseline and ID switches stay 0.
- CI is green on a headless short scenario.

#### Integration

- Node reconnects after fusion restart and resumes without manual steps.
- Bandwidth per node is below 1 Mbit/s of keypoints.

#### Unit

- Timestamp-window grouping selects the right frame set for out-of-order arrivals.
