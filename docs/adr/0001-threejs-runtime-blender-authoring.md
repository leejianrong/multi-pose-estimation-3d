# ADR-0001: three.js is the runtime, Blender is the authoring tool, Godot is not used

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

The user wants skeletons, rigging and animation (Blender's strength), a live interactive sim, three virtual camera streams, and CPU-only real-time operation on a laptop. Audio needs tight scheduling and synthesis. Blender's real-time viewport (Eevee) is GPU-bound and is not designed to emit three synchronised camera streams plus drive a live audio engine. The final deliverable is a public Apache-2.0 repo, so a low-friction `git clone && run` matters.

## Decision

- **Blender (authoring, offline):** rig/retarget avatars, build animation clips, optionally author or export the wavy objects. Output is glTF 2.0 (`.glb`) with skeletal animations, committed or fetched by script. Blender is not required to run the sim.
- **three.js (runtime):** loads `.glb` avatars, plays `AnimationMixer` clips, renders the room, renders three offscreen camera views, hosts the dashboard and the audio engine.
- **Godot:** not adopted.
- Blender Python (`bpy`) may later be used for an offline high-quality render path behind the same frame-source interface (ADR-0003). Not in the MVP.

## Alternatives considered

| Option | Why not |
|---|---|
| Blender as the live runtime | Real-time output needs a GPU; poor fit for multi-stream live capture plus Web Audio-grade scheduling; heavy dependency for every cloner. |
| Godot | Good engine, but adds a third runtime and language (GDScript/C#) beside Python and TS, has no browser dashboard story, and its audio is weaker than Web Audio/Tone.js for synthesis and quantised scheduling. Gains nothing we need. Revisit only if three.js rendering performance becomes the bottleneck. |
| Unity/Unreal | Licensing, size, and incompatible with a lean public Apache-2.0 repo. |
| Pure Blender offline (render video + mix audio) | Loses live "step in and it responds" feel, which is the point of the piece. |

## Consequences

- Buys: one browser app for sim, dashboard and audio; glTF is the open interchange format; Blender stays optional.
- Costs: avatar realism is limited by three.js PBR rather than Cycles, which may hurt pose-estimator accuracy; mitigated by V1 measuring this first.
- Costs: two toolchains (Node and Python) must coexist.
- Rendering three 640×480 views in-browser has a CPU/GPU cost on the laptop; the sim must be able to throttle camera render rate independently of the display.
