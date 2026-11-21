# Questions

Statuses: `DECIDED` (user answered) · `ASSUMED` (default taken, correct it if wrong) · `FORK` (waiting on the user) · `DEFERRED` (not needed this milestone).

Env seen at planning time: WSL2, Python 3.13, Node 24, no GPU visible, no Blender installed.

## Open forks

None. Round 1 closed.

## Register

| ID | Question | Status | Answer or default | Landed |
|----|----------|--------|-------------------|--------|
| Q1 | Platform: three.js, Blender, Godot? | DECIDED | three.js runtime; Blender for rig/animation authoring; Godot rejected | ADR-0001 |
| Q2 | Vision fidelity | DECIDED | Full loop: render → 2D pose → multi-view triangulation. GT skeleton is oracle + fallback | ADR-0002, 0007 |
| Q3 | Real-time on CPU; real topology | DECIDED | CPU real-time is mandatory. Real: 3 mini PCs (Intel iGPU) → Ethernet → laptop dashboard. Sim: one laptop | ADR-0002 |
| Q4 | Gestures | DECIDED | 6 rule-based: approach/leave, arms raised, reach/touch, sit, crouch, wave | ADR-0004 |
| Q5 | Licence | DECIDED | Personal, public repo, Apache-2.0 | ADR-0006 |
| Q6 | Sound | DECIDED | Hybrid synth + real samples; user pre-records piano chords/phrases; output must be cohesive | ADR-0005 |
| Q7 | Testbed vs real cameras | DECIDED | Testbed, real-camera-ready; target realism incl. lens distortion | ADR-0003 |
| Q8 | MVP scale | DECIDED | 3–5 people, 2–3 objects | PLAN §Scope |
| Q9 | Learned action classifier | DEFERRED | Future. MVP logs labelled windows and keeps the detector interface swappable | ADR-0004 |
| Q10 | Primary user | ASSUMED | The artist/builder. No agent-facing surface beyond a JSON CLI | PLAN §Users |
| Q11 | Scope boundary | ASSUMED | See PLAN §Scope | PLAN §Scope |
| Q12 | Data model and identity | ASSUMED | COCO-17 joints, metres, room frame, Z up. `track_id` stable within a run, not across runs. Objects/cameras have string IDs in config | PLAN §Implementation |
| Q13 | State and storage | ASSUMED | JSON configs in git; per-run JSONL logs + metrics under `runs/` (gitignored). No DB | PLAN §Implementation |
| Q14 | Concurrency | ASSUMED | Sim is the authoritative clock; messages timestamped; late results applied by timestamp. One writer per stream | ADR-0002 |
| Q15 | Interfaces | ASSUMED | Browser app, Python `camera-node` + `fusion` services over WebSocket, CLI with `--json` and non-zero exit on failed metrics | PLAN §Shape |
| Q16 | Failure behaviour | ASSUMED | <2 views → no 3D, flagged, no trigger; node down → banner, GT-fallback mode; never silent | PLAN §Implementation |
| Q17 | Dependencies and licences | ASSUMED | three.js, Tone.js (MIT); rtmlib, RTMPose/YOLOX (Apache-2.0 assumed), onnxruntime, OpenCV. **Weights/licences verified in V1** | ADR-0006, 0007 |
| Q18 | Runtime | ASSUMED | Local only: `npm run dev` + `uv run` services on localhost | PLAN §Implementation |
| Q19 | Success metrics | ASSUMED | Median MPJPE ≤ 80 mm (≤ 120 mm with distortion/noise); 0 ID switches on the scripted scenario; ≥10 FPS per node at 5 people; gesture P/R ≥ 0.9 on scripted clips; motion→scheduled ≤ 300 ms p95, audible ≤ 500 ms p95 | PLAN §Requirements |
| Q20 | Security | ASSUMED | Nothing sensitive; servers bound to 127.0.0.1; no real people's video committed | PLAN §Implementation |
| Q21 | Versioning | DEFERRED | Config files carry `version`; no migration tooling | PLAN §Implementation |
| Q22 | Camera layout | ASSUMED | 3 cameras ~2.8 m high, room corners/edges aimed at centre, 640×480 to nodes, pinhole at V1 | PLAN §Implementation |
| Q23 | Room | ASSUMED | 8 × 6 × 3 m; speakers on front wall (+Y); stereo L/R | PLAN §Implementation |
| Q24 | Objects | ASSUMED | Seeded procedural meshes (sine-warped, noise-displaced superellipsoids ~1.8×0.9×0.8 m), clearcoat PBR for the resin look | PLAN §Shape |
| Q25 | Proximity | ASSUMED | Horizontal distance from pelvis to object footprint; zones far >2.0, near 1.0–2.0, close 0.3–1.0, touch <0.3 m; hysteresis | PLAN §Shape |
| Q26 | Multi-person association | ASSUMED | Epipolar Hungarian matching, weighted DLT, constant-velocity tracker | ADR-0007 |
| Q27 | Audio spatialisation | ASSUMED | Stereo pan by object x, gain by proximity, no HRTF | ADR-0005 |
| Q28 | Polyphony | ASSUMED | 4 voices/object, 1.5 s cooldown per (person, object, gesture), master limiter | ADR-0005 |
| Q29 | Object visual feedback | ASSUMED | Emissive pulse synced to object amplitude | PLAN §Shape |
| Q30 | Human motion source | ASSUMED | Looping glTF clips on scripted waypoint paths; keyboard-controlled debug avatar | PLAN §Shape |
| Q31 | Clock sync across real mini PCs | DEFERRED | Trivial on localhost; real deployment needs NTP/PTP | ADR-0002 |
| Q32 | Real-camera calibration tooling | DEFERRED | Schema is ready; tooling after sim works | ADR-0003 |
| Q33 | Recording convention | ASSUMED | C major / A minor, I–vi–IV–V, 80–100 BPM, WAV/OGG, tagged in manifest | ADR-0005 |
| Q34 | Latency definition | ASSUMED | Quantisation (1/16 note) adds ≤ ~170 ms, so budget is 300 ms to schedule plus quantisation = ≤ 500 ms audible | PLAN R6 |

## Coverage

| Category | Covered by |
|----------|-----------|
| Primary user and actors | Q10 |
| Scope boundary | Q8, Q11 |
| Data model and identity | Q12 |
| State and storage | Q13 |
| Concurrency and conflict | Q14 |
| Interfaces and contracts | Q15 |
| Failure behaviour | Q16 |
| External dependencies | Q1, Q17, Q5 |
| Runtime and deployment | Q3, Q18 |
| Measurable success | Q19, Q34 |
| Security and secrets | Q20 |
| Versioning and migration | Q21 |
| Domain: cameras, room, objects, proximity, association, audio | Q22–Q33 |
