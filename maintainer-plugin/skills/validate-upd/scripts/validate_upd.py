#!/usr/bin/env python3
"""Valida un Plan de actualización (UPD) del NAS.

Además de la completitud y las reglas por paso comunes con los runbooks, exige inventario de
referencia, precondiciones de SnapRAID y backup, vuelta atrás escrita y, si cambia el kernel o el
firmware, comprobar después los discos (`lsblk`) y el enlace PCIe (`LnkSta` 8GT/s).

Uso: python validate_upd.py <UPD.md> | --all <carpeta> | --format json <UPD.md>
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
    check_steps,
    check_upstream_reference,
    common_checks,
    critical,
    find_section,
    find_table,
    has_content,
    max_risk_check,
    parse_metadata,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Resumen",
    "Cambios disponibles",
    "Impacto en el diseño",
    "Decisión",
    "Precondiciones",
    "Pasos",
    "Verificación posterior",
    "Vuelta atrás",
    "Historial de versiones",
]
CONTENT_SECTIONS = ["Resumen", "Impacto en el diseño", "Decisión"]

INVENTORY = re.compile(r"state/inventory/\d{4}-\d{2}-\d{2}\.yaml")
KERNEL = re.compile(r"linux-image|kernel|firmware|eeprom", re.IGNORECASE)
DECISIONS = ("Aplicar", "Posponer", "Descartar", "No aplica")


def check_inventory(content: str) -> list[ValidationResult]:
    if not INVENTORY.search(parse_metadata(content).get("Inventario", "")):
        return [
            critical(
                "Metadatos",
                "Sin inventario de referencia",
                "Ejecuta /maintainer-plugin:inventory y cita state/inventory/AAAA-MM-DD.yaml",
            )
        ]
    return []


def check_changes(sections: dict[str, str]) -> tuple[list[ValidationResult], bool]:
    section = "Cambios disponibles"
    rows = find_table(find_section(sections, section) or "", "componente", "versión nueva")
    if not rows:
        return [
            critical(section, "No hay cambios listados", "Sin cambios no hace falta UPD")
        ], False
    results = [
        warning(section, f"'{cell(r, 'componente')}' sin fuente", "Cita notas de versión")
        for r in rows
        if not cell(r, "fuente")
    ]
    touches_kernel = any(KERNEL.search(cell(r, "componente")) for r in rows)
    return results, touches_kernel


def check_post_verification(
    sections: dict[str, str], touches_kernel: bool
) -> list[ValidationResult]:
    section = "Verificación posterior"
    body = find_section(sections, section) or ""
    if not find_table(body, "comprobación", "esperado"):
        return [critical(section, "Sin verificación posterior", "| Comprobación | Comando | …")]
    if touches_kernel and not ("lsblk" in body and re.search(r"LnkSta|8GT/s", body)):
        return [
            critical(
                section,
                "Cambia el kernel o el firmware y no se comprueban discos y enlace PCIe",
                "Añade `lsblk` (tres discos SATA) y `lspci … | grep LnkSta` (8GT/s)",
            )
        ]
    return []


def check_preconditions(sections: dict[str, str]) -> list[ValidationResult]:
    body = (find_section(sections, "Precondiciones") or "").lower()
    missing = [w for w in ("snapraid", "backup") if w not in body]
    if missing:
        return [
            critical(
                "Precondiciones",
                f"Faltan precondiciones: {', '.join(missing)}",
                "SnapRAID sin errores y backups al día antes de actualizar",
            )
        ]
    return []


def check_rollback(sections: dict[str, str]) -> list[ValidationResult]:
    if not has_content(find_section(sections, "Vuelta atrás") or ""):
        return [critical("Vuelta atrás", "Sin vuelta atrás", "Qué hacer si algo sale mal")]
    return []


def check_decisions(sections: dict[str, str]) -> list[ValidationResult]:
    rows = find_table(find_section(sections, "Decisión") or "", "componente", "decisión") or []
    return [
        warning("Decisión", f"Decisión '{cell(r, 'decisión')}' no válida", f"Usa {DECISIONS}")
        for r in rows
        if cell(r, "decisión") not in DECISIONS
    ]


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_upstream_reference(content, "hld")
    report.results += check_inventory(content)
    change_results, touches_kernel = check_changes(sections)
    report.results += change_results
    report.results += check_decisions(sections)
    report.results += check_preconditions(sections)
    step_results, risks = check_steps(sections)
    report.results += step_results
    report.results += max_risk_check(content, risks)
    report.results += check_post_verification(sections, touches_kernel)
    report.results += check_rollback(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Plan de actualización (UPD) del NAS"))
