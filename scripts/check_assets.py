"""Fail if any file under assets/ lacks a row in ASSETS.md (ADR-0006)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = {".gitkeep", "README.md"}


def missing_assets(root: Path) -> list[str]:
    ledger = (root / "ASSETS.md").read_text() if (root / "ASSETS.md").exists() else ""
    assets = root / "assets"
    files = [p for p in assets.rglob("*") if p.is_file() and p.name not in IGNORE]
    files = [p for p in files if "_cache" not in p.parts]
    return sorted(str(p.relative_to(root)) for p in files if str(p.relative_to(root)) not in ledger)


def main() -> int:
    missing = missing_assets(ROOT)
    for m in missing:
        print(f"missing licence entry in ASSETS.md: {m}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
