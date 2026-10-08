#!/usr/bin/env python3
"""Valida un Informe de mantenimiento (MNT) del NAS.

Comprueba la lista de tareas del periodo (guía §13.3), que el semáforo no oculte fallos y, sobre
todo, que un disco que se degrada (atributos 5/197/198 distintos de 0 o que crecen) tenga una
acción hacia el experto en discos (storage-plugin).

Uso: python validate_mnt.py <MNT.md> | --all <carpeta> | --format json <MNT.md>
Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 error de fichero.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doc_validation import (  # noqa: E402
    ValidationReport,
    ValidationResult,
    base_report,
    cell,
    check_no_empty_sections,
    check_required_sections,
    check_upstream_reference,
    common_checks,
    critical,
    find_section,
    find_table,
    parse_metadata,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Resumen",
    "Checklist",
    "Salud de discos",
    "Temperatura y energía",
    "Espacio",
    "Backups",
    "Acciones",
    "Historial de versiones",
]
CONTENT_SECTIONS = ["Resumen", "Temperatura y energía", "Espacio"]

PERIODS = ("Semanal", "Mensual", "Semestral")
LIGHTS = ("Verde", "Ámbar", "Rojo")
TASK_RESULTS = ("OK", "Aviso", "Fallo", "No aplica")
TASKS = {
    "Semanal": {"informe de SnapRAID": "snapraid", "backup de AIO": "aio"},
    "Mensual": {
        "informe de SnapRAID": "snapraid",
        "backup de AIO": "aio",
        "backup restic": "restic",
        "filtro de polvo": "filtro",
        "actualizaciones": "actualizaci",
        "revisión SMART": "smart",
    },
    "Semestral": {
        "restauración de prueba": "restaur",
        "prueba del SAI": "sai",
        "copia fuera de casa": "fuera de casa",
    },
}
INVENTORY = re.compile(r"state/inventory/\d{4}-\d{2}-\d{2}\.yaml")
TEMP_WARN, TEMP_CRIT = 40, 45


def _int(value: str) -> int | None:
    digits = re.sub(r"[\s.]", "", value)
    return int(digits) if digits.isdigit() else None


def check_header(content: str) -> list[ValidationResult]:
    meta = parse_metadata(content)
    results = []
    if meta.get("Periodo") not in PERIODS:
        results.append(critical("Metadatos", "Periodo no válido", f"Usa {', '.join(PERIODS)}"))
    if meta.get("Semáforo") not in LIGHTS:
        results.append(critical("Metadatos", "Semáforo no válido", f"Usa {', '.join(LIGHTS)}"))
    if not INVENTORY.search(meta.get("Inventario", "")):
        results.append(
            critical("Metadatos", "Sin inventario", "Cita state/inventory/AAAA-MM-DD.yaml")
        )
    return results


def check_checklist(content: str, sections: dict[str, str]) -> list[ValidationResult]:
    section = "Checklist"
    rows = find_table(find_section(sections, section) or "", "tarea", "resultado")
    if not rows:
        return [critical(section, "Sin tareas", "Añade la lista del periodo (guía §13.3)")]
    results = [
        critical(section, f"'{cell(r, 'tarea')}': resultado no válido", f"Usa {TASK_RESULTS}")
        for r in rows
        if cell(r, "resultado") not in TASK_RESULTS
    ]
    period = parse_metadata(content).get("Periodo", "")
    text = " ".join(cell(r, "tarea") for r in rows).lower()
    for name, keyword in TASKS.get(period, {}).items():
        if keyword not in text:
            results.append(warning(section, f"Falta la tarea: {name}", "Ver guía §13.3"))
    light = parse_metadata(content).get("Semáforo")
    if light == "Verde" and any(cell(r, "resultado") == "Fallo" for r in rows):
        results.append(
            critical("Metadatos", "Semáforo Verde con tareas en Fallo", "Usa Ámbar o Rojo")
        )
    return results


def check_disks(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Salud de discos"
    rows = find_table(find_section(sections, section) or "", "disco", "tendencia")
    if not rows:
        return [critical(section, "Sin tabla de salud de discos", "Usa la plantilla")]
    actions = find_table(find_section(sections, "Acciones") or "", "acción", "skill") or []
    storage_action = any("storage-plugin" in cell(a, "skill") for a in actions)
    cooling_action = any(
        re.search(r"aire|ventila|temperatura", cell(a, "acción"), re.IGNORECASE) for a in actions
    )
    results = []
    for r in rows:
        name = f"{cell(r, 'disco')} ({cell(r, 'rol')})"
        values = [_int(r.get(attr, "")) for attr in ("5", "197", "198")]
        degrading = any(v for v in values if v) or "crece" in cell(r, "tendencia").lower()
        if degrading and not storage_action:
            results.append(
                critical(
                    section,
                    f"{name} se degrada y no hay acción hacia el experto en discos",
                    "Añade una acción con /storage-plugin:diagnose-disk",
                )
            )
        temp = _int(cell(r, "temp").split(",")[0])
        if temp is not None and temp > TEMP_CRIT and not actions:
            results.append(critical(section, f"{name} a {temp} °C sin acción", "Añade una acción"))
        elif temp is not None and temp > TEMP_WARN and not cooling_action:
            results.append(
                warning(section, f"{name} a {temp} °C (> {TEMP_WARN})", "Revisa el aire")
            )
    return results


def check_actions(sections: dict[str, str]) -> list[ValidationResult]:
    rows = find_table(find_section(sections, "Acciones") or "", "acción", "responsable") or []
    return [
        warning("Acciones", f"'{cell(r, 'acción')}' sin responsable o fecha", "Complétalo")
        for r in rows
        if not cell(r, "responsable") or not re.search(r"\d{4}-\d{2}-\d{2}", cell(r, "fecha"))
    ]


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_upstream_reference(content, "hld")
    report.results += check_header(content)
    report.results += check_checklist(content, sections)
    report.results += check_disks(sections)
    report.results += check_actions(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Informe de mantenimiento (MNT) del NAS"))
