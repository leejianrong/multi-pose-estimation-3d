# Avatar handoff (MP3D-9): continue on a machine with Blender

State at handoff: the V1 pipeline runs end to end on branch `v1` (PR #5, draft). The placeholder
avatar (CesiumMan, cartoon robot) limits the measurement: YOLOX misses it in a fraction of frames and
MPJPE is about 100 mm offline against an 80 mm target. A human-like avatar should fix most of this.

## What to do

1. Get the CC0 packs from Quaternius (manual itch.io click-through, glTF versions):
   - Universal Base Characters: https://quaternius.com/packs/universalbasecharacters.html
   - Universal Animation Library: https://quaternius.com/packs/universalanimationlibrary.html
2. In Blender: import one character and the walk (or jog) clip, bind them (the packs share a
   humanoid rig), and export a single `.glb` with the animation embedded.
   Prefer a realistic-proportion adult with a face and clothing that contrasts with the floor.
3. Save as `assets/avatars/<name>.glb`, add a row to `ASSETS.md` (source, CC0, URL, date), and run
   `make check-assets`.
4. Point `config/room.json` `avatar.path` at it.
5. Make `app/src/sim.ts` work with the new rig. Everything avatar-specific is in two places:
   - `BONES` (joint node names for shoulders, elbows, wrists, hips, knees, ankles, toes), and
   - `resolveSides()` (which named side is anatomical left, and which way the avatar faces).
   Set `avatar.shoulder_to_ankle_m` to about 1.4, or remove the rescale if the model is already 1.7 m.
   The ground-truth left/right check below is how you know it is right.

## How to check it

```bash
make setup
uv run python scripts/run_scenario.py --duration 8 --timeout 300 --dump-frames
uv run python scripts/analyze_run.py runs/<latest>
```

`analyze_run.py` prints median MPJPE both as-is and with left/right swapped. **As-is must be the
smaller number.** If the swapped one is smaller, the ground-truth side or facing in `sim.ts` is
wrong (this happened with CesiumMan: swapped 96 mm, as-is 549 mm, until `fwd` was negated).
`scripts/replay_frames.py <runs/.../frames> --out <dir>` draws the detections on every frame.

Known facts worth keeping:
- Ground truth exists only for COCO joints 5 to 16 (no face joints), so MPJPE covers those.
- First run downloads the ONNX models to `~/.cache/rtmlib`. `RtmPoseEstimator` takes a file lock
  because rtmlib's downloader is not safe for three processes at once.
- Headless Chromium uses SwiftShader (software GL), so FPS in headless runs is pessimistic. Run
  `make dev` and open the app in a normal browser for the interactive view (start the three nodes
  and fusion first: see `scripts/run_scenario.py` for the exact commands).

## Done when (MP3D-9)

- Detector finds the person in at least 95% of frames per camera (`replay_frames.py`).
- Median MPJPE at most 80 mm and at least 95% of frames with a 3D person (`run_scenario.py` exits 0).
- `ASSETS.md` updated. Then finish MP3D-5, 7 and 8 and mark the PR ready.
