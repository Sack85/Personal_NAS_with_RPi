#!/usr/bin/env python3
"""Copia shared/ a cada plugin del registro.

Los plugins instalados se copian a la caché de Claude Code, así que cada uno debe llevar sus
propios scripts. Este script mantiene una única fuente:
  shared/hooks/*.py + shared/doc_validation.py  ->  <plugin>/scripts/
  shared/doc_validation.py                       ->  <plugin>/skills/validate-*/scripts/
Con --check no copia: sale con 1 si alguna copia falta o ha divergido.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from registry import ROOT, load_registry  # noqa: E402

SHARED = ROOT / "shared"


def targets() -> list[tuple[Path, Path]]:
    core = SHARED / "doc_validation.py"
    pairs: list[tuple[Path, Path]] = []
    for plugin in load_registry():
        plugin_dir = ROOT / plugin
        for src in sorted((SHARED / "hooks").glob("*.py")) + [core]:
            pairs.append((src, plugin_dir / "scripts" / src.name))
        for validator_dir in sorted(plugin_dir.glob("skills/validate-*/scripts")):
            pairs.append((core, validator_dir / core.name))
    return pairs


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for src, dst in targets():
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            continue
        if check:
            stale.append(dst)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        dst.chmod(0o755)
        print(f"copiado {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    if stale:
        print("Copias desactualizadas (ejecuta `make sync`):", file=sys.stderr)
        for p in stale:
            print(f"  {p.relative_to(ROOT)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
