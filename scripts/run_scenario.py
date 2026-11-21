"""Run the V1 scenario headless: start nodes + fusion + Vite, drive the sim, check targets.

Exit code 0 only if every target is met. Report goes to runs/<timestamp>/report.json.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = {"mpjpe_median_mm_max": 80.0, "person_frame_ratio_min": 0.95, "node_fps_min": 10.0}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.3)
    raise TimeoutError(f"port {port} did not open")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=20, help="sim seconds")
    ap.add_argument("--fps", type=float, default=10)
    ap.add_argument("--timeout", type=float, default=240)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dump-frames", action="store_true", help="keep received JPEGs in the run dir")
    args = ap.parse_args()

    room = json.loads((ROOT / "config" / "room.json").read_text())
    nodes = room["services"]["nodes"]
    fusion_port = room["services"]["fusion"]
    run_dir = ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    procs: list[subprocess.Popen] = []

    env = {**os.environ}
    if args.dump_frames:
        env["POSESIM_DUMP_DIR"] = str(run_dir / "frames")

    def spawn(cmd: list[str], name: str, cwd: Path = ROOT) -> None:
        log = open(run_dir / f"{name}.log", "w")  # noqa: SIM115
        procs.append(subprocess.Popen(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT))

    try:
        for cam, port in nodes.items():
            spawn(
                [
                    "uv",
                    "run",
                    "camera-node",
                    "--camera",
                    cam,
                    "--calibration",
                    f"calibration/{cam}.json",
                    "--port",
                    str(port),
                ],
                cam,
            )
        spawn(
            [
                "uv",
                "run",
                "fusion",
                "--port",
                str(fusion_port),
                "--nodes",
                *[f"ws://127.0.0.1:{p}/poses" for p in nodes.values()],
            ],
            "fusion",
        )
        vite_port = free_port()
        spawn(["npx", "vite", "--port", str(vite_port), "--strictPort"], "vite", ROOT / "app")
        for p in [*nodes.values(), fusion_port, vite_port]:
            wait_port(p, 120)
        url = f"http://127.0.0.1:{vite_port}/?scenario=v1&duration={args.duration}&fps={args.fps}"
        out = subprocess.run(
            ["node", "scripts/scenario.mjs", url, str(run_dir / "room.png"), str(args.timeout)],
            cwd=ROOT / "app",
            capture_output=True,
            text=True,
            timeout=args.timeout + 60,
        )
        sys.stderr.write(out.stderr)
        report = json.loads(out.stdout.strip().splitlines()[-1])
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()

    checks: dict[str, bool] = {}
    if "error" not in report:
        ratio = report["frames_with_person"] / max(1, report["frames_sent"])
        report["person_frame_ratio"] = ratio
        checks["mpjpe_median"] = (
            report["mpjpe_median_mm"] is not None
            and report["mpjpe_median_mm"] <= TARGETS["mpjpe_median_mm_max"]
        )
        checks["person_frame_ratio"] = ratio >= TARGETS["person_frame_ratio_min"]
        checks["node_fps"] = bool(report["node_fps"]) and all(
            v >= TARGETS["node_fps_min"] for v in report["node_fps"].values()
        )
    report["targets"] = TARGETS
    report["checks"] = checks
    report["passed"] = bool(checks) and all(checks.values())
    (run_dir / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report) if args.json else json.dumps(report, indent=2))
    print(f"run dir: {run_dir}", file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
