# posesim

Simulated interactive sound sculpture: 3 virtual cameras → CPU 2D pose per camera → fusion to 3D → proximity/gestures → cohesive stereo music. Public, Apache-2.0.

## Status
Scaffold only. Trust the code over the docs. Plan: `PLAN.md`, `SLICES.md`, ADRs in `docs/adr/`, decision register `QUESTIONS.md`. Work is tracked on Pandan board MP3D (`pandan board use 50`).

## Layout
- `app/` three.js + TS (sim, dashboard, gestures, audio). `python/posesim/` camera-node, fusion, contracts. `tests/unit` fast, `tests/integration` heavy (`@pytest.mark.integration`).
- Room frame: metres, Z up, +Y front. Skeleton COCO-17.

## Commands
- `make help` lists targets. `make setup`, `make dev`, `make check` (lint + fast tests + asset licence check; the pre-push hook runs this), `make hooks` once per clone.

## Conventions
- Branch per slice/card off fresh `main`, PR only, CI green before merge. Reference cards as `MP3D-N`.
- Fast tests must need no models, network or Docker. Heavy ones carry the `integration` marker.
- Every bug gets a failing test first. Tests assert observable behaviour.
- New asset or model: add a row to `ASSETS.md` with licence. AGPL/GPL/non-commercial is excluded (ADR-0006).
- Thresholds and geometry live in `config/`, not in code.
