#!/usr/bin/env python3
"""Valida un Documento de Requisitos del NAS (NRD).

Derivado de validate_drd.py de RDEWAI (modificado).

Uso:
    python validate_nrd.py <NRD.md>
    python validate_nrd.py --all <carpeta>
    python validate_nrd.py --format json <NRD.md>

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
    parse_metadata,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Resumen",
    "Contexto y objetivos",
    "Usuarios y dispositivos",
    "Datos y capacidad",
    "Servicios",
    "Protección de datos",
    "Entorno y restricciones",
    "Seguridad y acceso",
    "Operación y mantenimiento",
    "Supuestos y preguntas abiertas",
    "Historial de versiones",
]
CONTENT_SECTIONS = REQUIRED_SECTIONS[:-1]

CRITICALITY = ("irreemplazable", "reemplazable", "mixta")
SCENARIOS = {
    "fallo de un disco": r"disco",
    "borrado accidental": r"borrad",
    "ransomware o cifrado": r"ransomware|cifrad",
    "desastre en casa (rayo, robo, inundación)": r"rayo|robo|incendio|inundaci",
}
NUMBER = re.compile(r"^\s*~?\d[\d\s.,]*\s*$")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def check_objectives(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Contexto y objetivos") or ""
    rows = find_table(body, "objetivo", "medida")
    if not rows:
        return [
            critical(
                "Contexto y objetivos",
                "No hay tabla de objetivos con su medida de éxito",
                "Añade | Objetivo | Medida de éxito |",
            )
        ]
    return [
        warning(
            "Contexto y objetivos",
            f"Objetivo sin medida numérica: '{cell(r, 'objetivo')}'",
            "Expresa la medida con un número, plazo o umbral",
        )
        for r in rows
        if not re.search(r"\d", cell(r, "medida"))
    ]


def check_users(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Usuarios y dispositivos") or ""
    if not find_table(body, "usuario", "dispositivos"):
        return [
            critical(
                "Usuarios y dispositivos",
                "No hay usuarios identificados",
                "Añade | Usuario | Dispositivos | Uso principal | Acceso desde fuera |",
            )
        ]
    return []


def check_data(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Datos y capacidad"
    body = find_section(sections, section) or ""
    rows = find_table(body, "carpeta", "volumen", "criticidad")
    if not rows:
        return [
            critical(
                section,
                "No hay inventario de datos por carpeta",
                "Añade | Carpeta | Contenido | Volumen actual (GB) | Crecimiento anual (GB) | "
                "Criticidad | Fuente del dato |",
            )
        ]
    results: list[ValidationResult] = []
    for r in rows:
        name = cell(r, "carpeta")
        crit = cell(r, "criticidad").lower()
        if not crit.startswith(CRITICALITY):
            results.append(
                critical(
                    section,
                    f"'{name}': criticidad '{cell(r, 'criticidad')}' no válida",
                    "Usa Irreemplazable, Reemplazable o Mixta (y explica qué parte)",
                )
            )
        for col in ("volumen", "crecimiento"):
            value = cell(r, col)
            if value and not NUMBER.match(value) and "pendiente" not in value.lower():
                results.append(
                    warning(section, f"'{name}': {col} '{value}' no es un número", "Cifra en GB")
                )
        source = cell(r, "fuente").lower()
        if crit.startswith("irreemplazable") and "medido" not in source:
            results.append(
                warning(
                    section,
                    f"'{name}' es irreemplazable y su volumen no está medido",
                    "Mide con `du -sh <carpeta>` o el Explorador e indica la fecha",
                )
            )
    if not re.search(r"capacidad necesaria a \d+ años?:\s*[\d\s.,]+\s*GB", body, re.IGNORECASE):
        results.append(
            warning(
                section,
                "No se calcula la capacidad necesaria",
                "Añade 'Capacidad necesaria a N años: X GB' con el cálculo",
            )
        )
    return results


def check_services(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Servicios") or ""
    if not find_table(body, "servicio"):
        return [critical("Servicios", "No hay servicios definidos", "Añade la tabla de servicios")]
    return []


def check_protection(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Protección de datos"
    body = find_section(sections, section) or ""
    rows = find_table(body, "escenario", "rpo", "rto")
    if not rows:
        return [
            critical(
                section,
                "No hay tabla de escenarios con RPO y RTO",
                "Añade | Escenario | Datos afectados | RPO | RTO | Cómo se cubre |",
            )
        ]
    text = " ".join(cell(r, "escenario") for r in rows).lower()
    return [
        warning(section, f"No se cubre el escenario: {name}", "Añade una fila con RPO y RTO")
        for name, pattern in SCENARIOS.items()
        if not re.search(pattern, text)
    ]


def check_environment(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Entorno y restricciones"
    body = find_section(sections, section) or ""
    results = []
    if "°C" not in body or "%" not in body:
        results.append(
            warning(
                section,
                "Falta el clima (temperatura en °C y humedad en %)",
                "Añade la fila Clima con rango de temperatura y humedad",
            )
        )
    if not find_table(body, "pieza", "modelo"):
        results.append(
            warning(section, "Falta el hardware disponible", "Añade ### Hardware disponible")
        )
    return results


def check_security(sections: dict[str, str]) -> list[ValidationResult]:
    raw = (find_section(sections, "Seguridad y acceso") or "").lower()
    body = re.sub(r"\s+", " ", raw)
    rules = re.split(r"\n\s*(?:[-*]|\d+\.)\s+", "\n" + raw)
    results = []
    if not any("nunca" in r and "ssh" in r and "omv" in r for r in rules):
        results.append(
            warning(
                "Seguridad y acceso",
                "No se dice qué no se expone nunca a Internet",
                "Indica que el panel de OMV, el de AIO y SSH nunca se exponen",
            )
        )
    if "gestor de contraseñas" not in body:
        results.append(
            warning(
                "Seguridad y acceso",
                "No se indica dónde se guardan los secretos",
                "Contraseñas y frases de acceso en el gestor de contraseñas, nunca en el repo",
            )
        )
    return results


def check_operation(sections: dict[str, str]) -> list[ValidationResult]:
    body = (find_section(sections, "Operación y mantenimiento") or "").lower()
    if "actualizaci" not in body:
        return [
            warning(
                "Operación y mantenimiento",
                "No se define cómo se actualiza el NAS",
                "Frecuencia, plan aprobado y comprobaciones tras actualizar",
            )
        ]
    return []


def check_open_questions(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, "Supuestos y preguntas abiertas") or ""
    rows = find_table(body, "pregunta", "responsable") or []
    return [
        warning(
            "Supuestos y preguntas abiertas",
            f"Pregunta sin responsable o fecha: '{cell(r, 'pregunta')}'",
            "Asigna responsable y fecha AAAA-MM-DD",
        )
        for r in rows
        if not cell(r, "responsable") or not DATE.search(cell(r, "fecha"))
    ]


def check_sources(content: str) -> list[ValidationResult]:
    if not parse_metadata(content).get("Fuentes"):
        return [
            warning(
                "Metadatos", "No se citan las fuentes", "Añade | **Fuentes** | inputs/nrd/vN/…|"
            )
        ]
    return []


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_sources(content)
    for check in (
        check_objectives,
        check_users,
        check_data,
        check_services,
        check_protection,
        check_environment,
        check_security,
        check_operation,
        check_open_questions,
    ):
        report.results += check(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un Documento de Requisitos del NAS (NRD)"))
