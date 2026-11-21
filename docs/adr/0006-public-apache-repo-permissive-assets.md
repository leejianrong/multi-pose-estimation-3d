# ADR-0006: Public Apache-2.0 repo, permissive assets only, licence recorded per asset

- Status: Accepted
- Date: 2026-11-22
- Deciders: Jian, Claude

## Context

The project is personal, but the repo will be public under Apache-2.0. Common avatar and mocap sources have restrictions (Mixamo: no redistribution of raw assets; SMPL/SMPL-X: non-commercial; Ultralytics YOLO: AGPL).

## Decision

- Code is Apache-2.0. Dependencies must be Apache-2.0, MIT, BSD or equivalent. AGPL/GPL and non-commercial licences are excluded from the repo and from required runtime.
- Every committed or fetched asset (avatar, animation, sample, model weights) has an entry in `ASSETS.md` with source, licence, and URL. V1 includes a verification step before any asset is committed.
- Preferred sources: CC0 characters (e.g. Quaternius, MakeHuman exports), CMU motion capture (free for any use, retargeted in Blender), self-generated parametric objects. Large files fetched by a script with checksums, or Git LFS, rather than inline.
- The user's own recordings are the user's to licence; default suggestion CC0 or CC-BY, to be stated in `ASSETS.md`.
- Pose model weights must be redistributable or downloaded on first run from the upstream URL.

## Alternatives considered

| Option | Why not |
|---|---|
| Mixamo avatars/animations | Cannot be redistributed in a public repo. |
| SMPL body model | Non-commercial licence conflicts with Apache-2.0 use. |
| Ultralytics YOLO | AGPL. |

## Consequences

- Constrains avatar choice; realism and rig quality must be checked in V1.
- Licence claims in this repo were not independently verified when planned (upstream licences assumed from public knowledge). V1 must confirm each before commit.
