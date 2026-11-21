# ADR-0005: A shared conductor drives per-object personalities; voices are synth or sample

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

Several people interact with several objects at once, and the result must sound cohesive, not like random notes. The user will pre-record chords and short phrases on piano and wants real instrument samples (piano, violin, etc.) alongside synthesis.

## Decision

- **Conductor** owns a global clock (tempo, meter), key/mode and a looping chord progression. All audio onsets are quantised to a grid (default 1/16 note). All pitched material is constrained to the current chord/scale.
- **Personality** = a parameter set per object (JSON): voice (synth patch or sampler), register, scale degrees preferred, response curve to proximity, which gestures it answers and how (note / arpeggio / chord / phrase / texture), reaction latency, density, mood drift with repeated interaction, stereo position.
- **Voices**: Synth (Tone.js synths) and Sampler (Tone.js `Sampler`, plus phrase clips). Both are selected per personality, and can be layered.
- **Sample library**: one manifest (`samples/manifest.json`) tags each file: instrument, kind (`note|chord|phrase`), key/mode, chord function, tempo (if rhythmic), bars, mood tags, licence/author. Selection is by tags matching the conductor's current state. Phrases are only played when key matches; no pitch-shifting by more than ±2 semitones.
- Initial recording convention: all recorded chords and phrases in **C major / A minor**, I–vi–IV–V progression, 80–100 BPM. More keys can be added to the manifest later.
- Until the user's recordings exist, generated placeholder phrases (synthesised from the same manifest schema) stand in.
- Polyphony: per-object cap 4 voices, per (person, object, gesture) cooldown 1.5 s, master limiter.
- Output: true stereo; pan by object x-position, gain by proximity.
- Library: Tone.js (MIT) over raw Web Audio.

## Alternatives considered

| Option | Why not |
|---|---|
| Each object plays independently | Drifting tempo and keys produce noise; cohesion is the stated requirement. |
| Pitch-shift one recorded key to everything | Audible artefacts on piano and strings. |
| Live generative MIDI to an external synth | Extra install, no browser-only path. |
| Raw Web Audio | Re-implements transport, quantisation and samplers. |

## Consequences

- Cohesion is checkable: every scheduled note belongs to the current chord/scale; onsets fall on the grid.
- Quantisation adds up to one grid step of delay (~167 ms at 90 BPM, 1/16). The latency target accounts for it (PLAN R6).
- The artistic result depends on the user's recordings; engine and manifest must be ready before they exist.
- Third-party instrument samples need redistributable licences (ADR-0006).
