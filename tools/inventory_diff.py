#!/usr/bin/env python3
"""Compara dos inventarios del NAS (state/inventory/*.yaml) o revisa uno solo.

    uv run python tools/inventory_diff.py <anterior.yaml> <actual.yaml> [--format json]
    uv run python tools/inventory_diff.py <actual.yaml>

Informa de versiones que cambian, actualizaciones pendientes y alertas de salud: atributos SMART
5/197/198/199 que crecen o no son 0, cabezales (193) que aparcan más de 100 veces al día,
temperaturas, enlace PCIe distinto de 8GT/s, throttling, errores de SnapRAID y pool lleno.
Salida: 0 sin alertas CRITICAL, 1 con alguna.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import yaml

FAILURE_ATTRS = (5, 197, 198)
CABLE_ATTR = 199
LOAD_CYCLE_ATTR = 193
LOAD_CYCLES_PER_DAY = 100
TEMP_WARN, TEMP_CRIT = 40, 45
POOL_WARN, POOL_CRIT = 85, 95


@dataclass
class Finding:
    level: str
    area: str
    message: str


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _versions(inv: dict) -> dict[str, str]:
    sistema = inv.get("sistema") or {}
    out = {
        "kernel": sistema.get("kernel"),
        "firmware_eeprom": sistema.get("firmware_eeprom"),
        "os": sistema.get("os"),
    }
    out.update({f"paquete {k}": v for k, v in (inv.get("paquetes") or {}).items()})
    out.update({f"contenedor {k}": v for k, v in (inv.get("contenedores") or {}).items()})
    return {k: str(v) for k, v in out.items() if v is not None}


def version_changes(old: dict, new: dict) -> list[Finding]:
    before, after = _versions(old), _versions(new)
    found = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a != b:
            level = "WARNING" if key in ("kernel", "firmware_eeprom") else "INFO"
            found.append(Finding(level, "versiones", f"{key}: {a or '—'} → {b or '—'}"))
    return found


def pending(new: dict) -> list[Finding]:
    found = []
    for p in new.get("pendientes") or []:
        name = p.get("paquete", "?")
        level = "WARNING" if "linux-image" in name or "firmware" in name else "INFO"
        found.append(Finding(level, "pendientes", f"{name}: {p.get('actual')} → {p.get('nueva')}"))
    return found


def _days_between(old: dict, new: dict) -> int:
    try:
        d = date.fromisoformat(str(new["fecha"])) - date.fromisoformat(str(old["fecha"]))
        return max(d.days, 1)
    except (KeyError, ValueError):
        return 1


def disk_health(new: dict, old: dict | None = None) -> list[Finding]:
    found = []
    previous = {d.get("serie"): d for d in ((old or {}).get("salud") or {}).get("discos") or []}
    days = _days_between(old, new) if old else 1
    for disk in (new.get("salud") or {}).get("discos") or []:
        name = f"{disk.get('rol', '?')} ({disk.get('modelo', '?')}, {disk.get('serie', '?')})"
        smart = {int(k): v for k, v in (disk.get("smart") or {}).items()}
        prev = {
            int(k): v
            for k, v in ((previous.get(disk.get("serie")) or {}).get("smart") or {}).items()
        }
        for attr in FAILURE_ATTRS:
            value = smart.get(attr)
            if value is None:
                continue
            if prev.get(attr) is not None and value > prev[attr]:
                found.append(
                    Finding(
                        "CRITICAL",
                        "discos",
                        f"{name}: atributo {attr} crece {prev[attr]} → {value}",
                    )
                )
            elif value:
                found.append(Finding("WARNING", "discos", f"{name}: atributo {attr} = {value}"))
        if prev.get(CABLE_ATTR) is not None and (smart.get(CABLE_ATTR) or 0) > prev[CABLE_ATTR]:
            found.append(
                Finding(
                    "WARNING", "discos", f"{name}: errores CRC (199) crecen: revisar FFC y bahía"
                )
            )
        if prev.get(LOAD_CYCLE_ATTR) is not None and smart.get(LOAD_CYCLE_ATTR) is not None:
            per_day = (smart[LOAD_CYCLE_ATTR] - prev[LOAD_CYCLE_ATTR]) / days
            if per_day > LOAD_CYCLES_PER_DAY:
                found.append(
                    Finding(
                        "WARNING",
                        "discos",
                        f"{name}: 193 sube {per_day:.0f}/día (> {LOAD_CYCLES_PER_DAY}): APM 254",
                    )
                )
        temp = disk.get("temp_c")
        if temp is not None and temp > TEMP_CRIT:
            found.append(Finding("CRITICAL", "temperatura", f"{name}: {temp} °C > {TEMP_CRIT}"))
        elif temp is not None and temp > TEMP_WARN:
            found.append(Finding("WARNING", "temperatura", f"{name}: {temp} °C > {TEMP_WARN}"))
    return found


def system_health(new: dict) -> list[Finding]:
    salud = new.get("salud") or {}
    found = []
    link = salud.get("pcie_enlace")
    if link and link != "8GT/s":
        found.append(Finding("CRITICAL", "pcie", f"Enlace PCIe {link} (esperado 8GT/s)"))
    if str(salud.get("throttled", "0x0")) != "0x0":
        found.append(Finding("WARNING", "energía", f"throttled = {salud.get('throttled')}"))
    errors = (salud.get("snapraid") or {}).get("errores") or 0
    if errors:
        found.append(Finding("CRITICAL", "snapraid", f"{errors} errores en snapraid status"))
    usage = salud.get("pool_uso_pct")
    if usage is not None and usage >= POOL_CRIT:
        found.append(Finding("CRITICAL", "espacio", f"Pool al {usage} %"))
    elif usage is not None and usage >= POOL_WARN:
        found.append(Finding("WARNING", "espacio", f"Pool al {usage} %"))
    return found


def compare(old: dict | None, new: dict) -> list[Finding]:
    found = []
    if old:
        found += version_changes(old, new)
    found += pending(new)
    found += disk_health(new, old)
    found += system_health(new)
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    return sorted(found, key=lambda f: order[f.level])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if len(args.files) > 2:
        parser.error("uno o dos inventarios")
    old = load(args.files[0]) if len(args.files) == 2 else None
    new = load(args.files[-1])
    findings = compare(old, new)
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"[{f.level}] {f.area}: {f.message}")
        if not findings:
            print("Sin cambios ni alertas")
    return 1 if any(f.level == "CRITICAL" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
