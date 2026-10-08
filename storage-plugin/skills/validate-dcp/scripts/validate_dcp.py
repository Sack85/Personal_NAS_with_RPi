#!/usr/bin/env python3
"""Valida un Plan de cambio de discos (DCP) del NAS.

Reglas de seguridad por escenario sobre SnapRAID + MergerFS:
- la disposición final cumple paridad ≥ mayor disco de datos, paridad fuera del pool y
  content ≥ paridades + 1 (misma regla que el HLD);
- precondiciones con backup y con el sync programado desactivado;
- fallo de disco de datos: hay `snapraid -d dN … fix` y ningún `sync` antes del `fix`;
- fallo de paridad: hay un `sync` que recrea la paridad;
- reglas por paso comunes con los runbooks.

Uso: python validate_dcp.py <DCP.md> | --all <carpeta> | --format json <DCP.md>
Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 error de fichero.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doc_validation import (  # noqa: E402
    STEP,
    ValidationReport,
    ValidationResult,
    base_report,
    check_disk_layout,
    check_no_empty_sections,
    check_required_sections,
    check_steps,
    check_upstream_reference,
    commands_in,
    common_checks,
    critical,
    find_section,
    find_table,
    max_risk_check,
    parse_metadata,
    parse_sections,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Resumen",
    "Diagnóstico",
    "Situación de partida",
    "Situación final",
    "Precondiciones",
    "Pasos",
    "Verificación final",
    "Vuelta atrás",
    "Cambios en el diseño",
    "Historial de versiones",
]
CONTENT_SECTIONS = ["Resumen", "Diagnóstico", "Vuelta atrás", "Cambios en el diseño"]

SCENARIOS = (
    "Fallo de disco de datos",
    "Fallo de paridad",
    "Sustitución preventiva",
    "Ampliación",
    "Retirada",
)
SYNC_DISABLED = re.compile(
    r"(desactiv|paus|deten|parar)\w*[^\n]*\bsync\b|\bsync\b[^\n]*(desactiv|pausad|detenid)",
    re.IGNORECASE,
)
FIX = re.compile(r"\bsnapraid\b.*\s-d\s+\S+.*\bfix\b")
SYNC = re.compile(r"\bsnapraid\b.*\bsync\b")
CHECK = re.compile(r"\bsnapraid\b.*\bcheck\b")
DESIGN_ITEMS = ("HLD", "SnapRAID", "MergerFS", "hd-idle", "SMART")


def check_header(content: str) -> tuple[list[ValidationResult], str]:
    meta = parse_metadata(content)
    scenario = meta.get("Escenario", "")
    results = []
    if scenario not in SCENARIOS:
        results.append(
            critical(
                "Metadatos", f"Escenario '{scenario}' no válido", f"Usa {', '.join(SCENARIOS)}"
            )
        )
    if not meta.get("Disco afectado"):
        results.append(critical("Metadatos", "Falta el disco afectado", "Rol, modelo y serie"))
    if not re.search(r"state/inventory/\d{4}-\d{2}-\d{2}\.yaml", meta.get("Inventario", "")):
        results.append(
            warning("Metadatos", "Sin inventario de referencia", "/maintainer-plugin:inventory")
        )
    return results, scenario


def check_preconditions(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Precondiciones") or ""
    results = []
    if not re.search(r"backup|restic", body, re.IGNORECASE):
        results.append(
            critical(
                "Precondiciones",
                "No se exige comprobar el backup antes de tocar discos",
                "Añade la fecha del último backup restic (y hacerlo si es antiguo)",
            )
        )
    if not SYNC_DISABLED.search(body):
        results.append(
            critical(
                "Precondiciones",
                "No se desactiva el sync programado de SnapRAID",
                "Un sync automático a mitad del cambio puede destruir la paridad: desactívalo",
            )
        )
    return results


def _step_commands(sections: dict[str, str]) -> list[tuple[int, list[str]]]:
    body = find_section(sections, "Pasos") or ""
    steps = []
    for heading, text in parse_sections(body, level=3).items():
        m = STEP.match(heading)
        if m:
            steps.append((int(m.group(1)), commands_in(text)))
    return sorted(steps)


def _first(steps: list[tuple[int, list[str]]], pattern: re.Pattern[str]) -> int | None:
    for n, cmds in steps:
        if any(pattern.search(c) for c in cmds):
            return n
    return None


def check_scenario(scenario: str, sections: dict[str, str]) -> list[ValidationResult]:
    steps = _step_commands(sections)
    fix, sync, check = _first(steps, FIX), _first(steps, SYNC), _first(steps, CHECK)
    results = []
    if scenario == "Fallo de disco de datos":
        if fix is None:
            results.append(
                critical(
                    "Pasos",
                    "Fallo de disco de datos sin `snapraid -d dN … fix`",
                    "Reconstruye el disco con fix sobre el disco nuevo con el mismo nombre",
                )
            )
        elif sync is not None and sync < fix:
            results.append(
                critical(
                    "Pasos",
                    f"Hay un sync (paso {sync}) antes del fix (paso {fix})",
                    "Nunca sincronices antes de reconstruir: perderías los datos del disco muerto",
                )
            )
        if fix is not None and (check is None or check < fix):
            results.append(
                warning("Pasos", "Sin `-d dN -a check` tras el fix", "Verifica lo reconstruido")
            )
        if fix is not None and sync is None:
            results.append(warning("Pasos", "Sin sync final tras reconstruir", "Añádelo al final"))
    if scenario == "Fallo de paridad" and sync is None:
        results.append(
            critical("Pasos", "Fallo de paridad sin sync que la recree", "Añade el sync completo")
        )
    return results


def check_final_layout(sections: dict[str, str]) -> list[ValidationResult]:
    return check_disk_layout(find_section(sections, "Situación final") or "", "Situación final")


def check_design_changes(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Cambios en el diseño") or ""
    return [
        warning("Cambios en el diseño", f"No se menciona {item}", f"Indica qué cambia en {item}")
        for item in DESIGN_ITEMS
        if item.lower() not in body.lower()
    ]


def check_final_verification(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Verificación final") or ""
    if not find_table(body, "comprobación", "esperado"):
        return [critical("Verificación final", "Sin verificación final", "Tabla de la plantilla")]
    if "snapraid" not in body.lower():
        return [
            warning("Verificación final", "No se comprueba SnapRAID", "Añade `snapraid status`")
        ]
    return []


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_upstream_reference(content, "hld")
    header_results, scenario = check_header(content)
    report.results += header_results
    report.results += check_final_layout(sections)
    report.results += check_preconditions(sections)
    step_results, risks = check_steps(sections)
    report.results += step_results
    report.results += max_risk_check(content, risks)
    report.results += check_scenario(scenario, sections)
    report.results += check_final_verification(sections)
    report.results += check_design_changes(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Plan de cambio de discos (DCP) del NAS"))
