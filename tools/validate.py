#!/usr/bin/env python3
"""Valida la última versión de un entregable: python tools/validate.py <abbr> | --all"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from registry import deliverables, latest_version_dir, validator_path  # noqa: E402


def validate(abbr: str) -> int:
    latest = latest_version_dir(abbr)
    if latest is None or not any(latest.glob("*.md")):
        print(f"{abbr}: no hay entregables todavía")
        return 0
    return subprocess.run(
        [sys.executable, str(validator_path(abbr)), "--all", str(latest)], check=False
    ).returncode


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 3
    known = deliverables()
    names = list(known) if sys.argv[1] == "--all" else [sys.argv[1]]
    unknown = [n for n in names if n not in known]
    if unknown:
        print(f"Entregable desconocido: {unknown}. Conocidos: {list(known)}")
        return 3
    return max((validate(n) for n in names), default=0)


if __name__ == "__main__":
    sys.exit(main())
