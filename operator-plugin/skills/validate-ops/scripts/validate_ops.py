#!/usr/bin/env python3
"""Valida un Registro de ejecución (OPS) del NAS.

Comprueba que la ejecución parte de un documento aprobado (RBK, UPD o DCP), que ningún paso
destructivo lo ejecutó el agente, que el resultado global es coherente con los pasos y que los
fallos tienen incidencia registrada.

Uso: python validate_ops.py <OPS.md> | --all <carpeta> | --format json <OPS.md>
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
    common_checks,
    critical,
    find_section,
    find_table,
    info,
    parse_metadata,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Alcance",
    "Estado inicial",
    "Registro de pasos",
    "Evidencias",
    "Incidencias",
    "Estado final",
    "Cambios en la configuración",
    "Historial de versiones",
]
CONTENT_SECTIONS = ["Alcance", "Estado inicial", "Cambios en la configuración"]

SOURCE = re.compile(r"\b(RBK|UPD|DCP)\s+v\d+\s*\([\d.]+,\s*Aprobado\)")
OUTCOMES = ("En curso", "Completado", "Parcial", "Abortado")
STEP_RESULTS = ("OK", "Fallo", "Omitido", "Pendiente")
RUNNERS = ("Agente", "Usuario")


def check_source(content: str) -> list[ValidationResult]:
    if not SOURCE.search(parse_metadata(content).get("Entregable previo", "")):
        return [
            critical(
                "Metadatos",
                "No se ejecuta un documento aprobado",
                "Entregable previo: 'RBK|UPD|DCP vN (X.Y, Aprobado) — fichero'",
            )
        ]
    return []


def check_steps(content: str, sections: dict[str, str]) -> list[ValidationResult]:
    section = "Registro de pasos"
    rows = find_table(find_section(sections, section) or "", "paso", "resultado", "ejecutó")
    outcome = parse_metadata(content).get("Resultado", "")
    results: list[ValidationResult] = []
    if outcome not in OUTCOMES:
        results.append(
            critical("Metadatos", f"Resultado '{outcome}' no válido", f"Usa {', '.join(OUTCOMES)}")
        )
    if not rows:
        results.append(
            critical(section, "Sin tabla de pasos", "| Paso | Riesgo | Ejecutó | Hora | …")
        )
        return results

    failed = []
    for r in rows:
        step, result, runner = cell(r, "paso"), cell(r, "resultado"), cell(r, "ejecutó")
        if result not in STEP_RESULTS:
            results.append(critical(section, f"'{step}': resultado '{result}' no válido", "OK…"))
        if runner not in RUNNERS:
            results.append(critical(section, f"'{step}': ejecutó '{runner}'", "Agente o Usuario"))
        if cell(r, "riesgo").lower().startswith("destructivo") and runner == "Agente":
            results.append(
                critical(
                    section,
                    f"'{step}' es destructivo y figura ejecutado por el agente",
                    "Los pasos destructivos los ejecuta siempre el usuario",
                )
            )
        if result == "OK" and not cell(r, "evidencia"):
            results.append(warning(section, f"'{step}' sin evidencia", "Referencia E<n>"))
        if result in ("Fallo", "Pendiente"):
            failed.append(step)

    if outcome == "Completado" and failed:
        results.append(
            critical(
                section,
                f"Resultado Completado con pasos en Fallo/Pendiente: {', '.join(failed)}",
                "Usa Parcial o Abortado, o completa los pasos",
            )
        )
    incidents = [
        r
        for r in find_table(find_section(sections, "Incidencias") or "", "paso", "acción") or []
        if cell(r, "paso") not in ("", "—", "-")
    ]
    if any(cell(r, "resultado") == "Fallo" for r in rows) and not incidents:
        results.append(
            critical("Incidencias", "Hay pasos en Fallo sin incidencia", "Registra qué pasó")
        )
    if outcome in ("Parcial", "Abortado") and not incidents:
        results.append(
            critical("Incidencias", f"Resultado {outcome} sin incidencia", "Explica por qué")
        )
    if outcome == "En curso":
        results.append(info("Metadatos", "Ejecución en curso", "Reanúdala con update-ops"))
    return results


def check_final_state(content: str, sections: dict[str, str]) -> list[ValidationResult]:
    outcome = parse_metadata(content).get("Resultado", "")
    if outcome != "Completado":
        return []
    rows = find_table(find_section(sections, "Estado final") or "", "comprobación", "ok")
    if not rows:
        return [
            critical(
                "Estado final",
                "Completado sin verificación final",
                "Ejecuta la verificación final del documento y anótala",
            )
        ]
    bad = [cell(r, "comprobación") for r in rows if not cell(r, "ok").lower().startswith("s")]
    if bad:
        return [
            critical(
                "Estado final",
                f"Verificación final no superada: {', '.join(bad)}",
                "Usa Resultado Parcial y registra la incidencia",
            )
        ]
    return []


def check_end_time(content: str) -> list[ValidationResult]:
    meta = parse_metadata(content)
    if meta.get("Resultado") in ("Completado", "Parcial", "Abortado") and not meta.get("Fin"):
        return [warning("Metadatos", "Ejecución terminada sin hora de fin", "Rellena **Fin**")]
    return []


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_source(content)
    report.results += check_steps(content, sections)
    report.results += check_final_state(content, sections)
    report.results += check_end_time(content)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Registro de ejecución (OPS) del NAS"))
