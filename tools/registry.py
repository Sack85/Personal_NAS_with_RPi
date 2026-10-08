"""Lectura de registry.yaml y utilidades de versionado de entregables."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_registry() -> dict:
    data = yaml.safe_load((ROOT / "registry.yaml").read_text(encoding="utf-8")) or {}
    return data.get("plugins") or {}


def ready_plugins() -> dict:
    """Plugins terminados (sin `wip: true`): los únicos que se exigen en tests y marketplace."""
    return {name: spec for name, spec in load_registry().items() if not spec.get("wip")}


def deliverables(ready_only: bool = False) -> dict[str, dict]:
    """{abbr: {..., 'plugin': nombre}}."""
    out: dict[str, dict] = {}
    plugins = ready_plugins() if ready_only else load_registry()
    for plugin, spec in plugins.items():
        for abbr, d in (spec.get("deliverables") or {}).items():
            out[abbr] = {**d, "plugin": plugin}
    return out


def latest_version_dir(abbr: str, base: str = "outputs") -> Path | None:
    dirs = [p for p in (ROOT / base / abbr).glob("v*") if re.fullmatch(r"v\d+", p.name)]
    return max(dirs, key=lambda p: int(p.name[1:]), default=None)


def validator_path(abbr: str) -> Path:
    plugin = deliverables()[abbr]["plugin"]
    return ROOT / plugin / "skills" / f"validate-{abbr}" / "scripts" / f"validate_{abbr}.py"
