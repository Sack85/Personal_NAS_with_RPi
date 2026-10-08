#!/usr/bin/env python3
"""Valida un Runbook (RBK) de una fase de la instalación o el mantenimiento del NAS.

Cada paso (### Paso N: …) debe declarar Riesgo, Ejecuta y Dónde. Los comandos destructivos se
detectan con la misma lista que usa el guard SSH (doc_validation.DESTRUCTIVE): un paso que los
contiene debe ser Destructivo, ejecutarlo el usuario y llevar comprobación previa y "Si falla".

Uso: python validate_rbk.py <RBK.md> | --all <carpeta> | --format json <RBK.md>
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
    check_no_empty_sections,
    check_required_sections,
    check_steps,
    check_upstream_reference,
    common_checks,
    critical,
    find_section,
    find_table,
    max_risk_check,
    parse_metadata,
    run_cli,
)

REQUIRED_SECTIONS = [
    "Objetivo",
    "Prerrequisitos",
    "Pasos",
    "Verificación final",
    "Vuelta atrás",
    "Evidencias",
    "Historial de versiones",
]
CONTENT_SECTIONS = ["Objetivo", "Prerrequisitos", "Vuelta atrás", "Evidencias"]


def check_header(content: str, risks: list[str]) -> list[ValidationResult]:
    results = []
    if not re.match(r"^\d{2}\b", parse_metadata(content).get("Fase", "")):
        results.append(
            critical("Metadatos", "Falta la fase (NN — nombre)", "Añade | **Fase** | 05 — … |")
        )
    return results + max_risk_check(content, risks)


def check_final_verification(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Verificación final") or ""
    if not find_table(body, "comprobación", "esperado"):
        return [
            critical(
                "Verificación final",
                "Sin tabla de verificación final",
                "Añade | Comprobación | Comando | Esperado |",
            )
        ]
    return []


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_upstream_reference(content, "hld")
    step_results, risks = check_steps(sections)
    report.results += step_results
    report.results += check_header(content, risks)
    report.results += check_final_verification(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Runbook (RBK) del NAS"))
