"""Write calibration/cam{0,1,2}.json from config/room.json (ADR-0003)."""

from __future__ import annotations

import json
from pathlib import Path

from posesim.calibration import look_at, save

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cfg = json.loads((ROOT / "config" / "room.json").read_text())
    for cam in cfg["cameras"]:
        calib = look_at(
            cam["id"],
            tuple(cam["position"]),
            tuple(cam["target"]),
            cam["vfov_deg"],
            cfg["camera_width"],
            cfg["camera_height"],
            tuple(cam.get("dist", (0, 0, 0, 0, 0))),
        )
        save(calib, ROOT / "calibration" / f"{cam['id']}.json")
        print("wrote", cam["id"])


if __name__ == "__main__":
    main()
