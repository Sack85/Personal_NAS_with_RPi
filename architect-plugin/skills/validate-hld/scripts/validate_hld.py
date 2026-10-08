#!/usr/bin/env python3
"""Valida el Diseño de Alto Nivel (HLD) del NAS.

Derivado de validate_hld.py de RDEWAI (modificado). Además de la completitud, bloquea los
diseños inseguros: paridad menor que un disco de datos o dentro del pool, pocos ficheros
content, paneles expuestos a Internet y HAT PCIe sin el overlay de 32 bits.

Uso: python validate_hld.py <HLD.md> | --all <carpeta> | --format json <HLD.md>
Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 error de fichero.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doc_validation import (  # noqa: E402
    YES,
    ValidationReport,
    ValidationResult,
    base_report,
    cell,
    check_disk_layout,
    check_no_empty_sections,
    check_required_sections,
    check_upstream_reference,
    common_checks,
    critical,
    find_section,
    find_table,
    run_cli,
    warning,
)

REQUIRED_SECTIONS = [
    "Resumen",
    "Requisitos cubiertos",
    "Hardware y montaje",
    "Sistema y arranque",
    "Red y puertos",
    "Almacenamiento",
    "Servicios y carpetas",
    "Protección de datos y backups",
    "Seguridad",
    "Energía y temperatura",
    "Actualizaciones y mantenimiento",
    "Decisiones de arquitectura (ADR)",
    "Riesgos",
    "Historial de versiones",
]
CONTENT_SECTIONS = REQUIRED_SECTIONS[:-1]

NEVER_EXPOSED = {"22": "SSH", "8000": "panel de OMV", "8080": "panel de AIO"}


def check_storage(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Almacenamiento"
    body = find_section(sections, section) or ""
    results = check_disk_layout(body, section)
    if not re.search(r"umbral", body, re.IGNORECASE):
        results.append(
            warning(
                section,
                "SnapRAID sin umbral de borrados",
                "Añade 'Umbral de borrados': no sincronizar si hay más de N borrados",
            )
        )
    if not re.search(r"espacio libre m[ií]nimo", body, re.IGNORECASE):
        results.append(warning(section, "MergerFS sin espacio libre mínimo", "Añade p. ej. 20G"))
    return results


def check_ports(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Red y puertos"
    body = find_section(sections, section) or ""
    rows = find_table(body, "puerto", "expuesto")
    if not rows:
        return [
            critical(
                section,
                "No hay tabla de puertos con 'Expuesto a Internet'",
                "Añade | Puerto | Servicio | Expuesto a Internet |",
            )
        ]
    results = []
    for r in rows:
        ports = set(re.findall(r"\d+", cell(r, "puerto")))
        for port, name in NEVER_EXPOSED.items():
            if port in ports and YES.match(cell(r, "expuesto")):
                results.append(
                    critical(
                        section,
                        f"El {name} ({port}) está expuesto a Internet",
                        "Nunca: usa Tailscale o publica solo Nextcloud",
                    )
                )
    return results


def check_boot_config(content: str, sections: dict[str, str]) -> list[ValidationResult]:
    if not re.search(r"penta|jmb585", content, re.IGNORECASE):
        return []
    body = find_section(sections, "Sistema y arranque") or ""
    results = []
    for line, why in (
        ("dtparam=pciex1", "activa el conector PCIe del HAT"),
        ("dtoverlay=pcie-32bit-dma-pi5", "sin él los discos desaparecen tras actualizar el kernel"),
    ):
        if line not in body:
            results.append(
                critical(
                    "Sistema y arranque",
                    f"Falta `{line}` en config.txt",
                    f"Añádelo: {why}",
                )
            )
    return results


def check_traceability(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Requisitos cubiertos"
    rows = find_table(find_section(sections, section) or "", "requisito", "sección")
    if not rows:
        return [
            critical(
                section,
                "No hay trazabilidad NRD → HLD",
                "Añade | Requisito (NRD) | Cómo se cubre | Sección del HLD |",
            )
        ]
    return [
        warning(section, f"Requisito sin referencia al NRD: '{cell(r, 'requisito')}'", "Usa §N")
        for r in rows
        if "§" not in cell(r, "requisito")
    ]


def check_adrs(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Decisiones de arquitectura (ADR)"
    rows = find_table(find_section(sections, section) or "", "decisión", "motivo")
    if not rows:
        return [critical(section, "No hay decisiones registradas", "Añade al menos un ADR")]
    results = []
    for r in rows:
        if not cell(r, "requisito"):
            results.append(warning(section, f"{cell(r, 'id')} sin requisito", "Cita el NRD §N"))
        if not cell(r, "alternativas"):
            results.append(
                warning(section, f"{cell(r, 'id')} sin alternativas", "Indica qué se descartó")
            )
    return results


def check_protection(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Protección de datos y backups"
    rows = find_table(find_section(sections, section) or "", "escenario", "mecanismo")
    if not rows:
        return [
            critical(section, "No se asigna mecanismo a cada escenario", "Tabla de la plantilla")
        ]
    text = " ".join(cell(r, "mecanismo") for r in rows).lower()
    if "restic" not in text and "backup" not in text:
        return [
            critical(
                section,
                "Ningún escenario se cubre con un backup",
                "SnapRAID no es un backup: añade restic o equivalente",
            )
        ]
    return []


def check_updates(sections: dict[str, str]) -> list[ValidationResult]:
    section = "Actualizaciones y mantenimiento"
    rows = find_table(find_section(sections, section) or "", "componente", "comprobar")
    if not rows:
        return [
            warning(
                section,
                "Sin tabla de componentes y comprobaciones tras actualizar",
                "La usa el mantenedor para sus planes de actualización",
            )
        ]
    return []


def check_risks(sections: dict[str, str]) -> list[ValidationResult]:
    if not find_table(find_section(sections, "Riesgos") or "", "riesgo", "mitigación"):
        return [warning("Riesgos", "Sin riesgos con mitigación", "Añade la tabla de riesgos")]
    return []


def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += check_no_empty_sections(sections, CONTENT_SECTIONS)
    report.results += common_checks(content, sections)
    report.results += check_upstream_reference(content, "nrd")
    report.results += check_boot_config(content, sections)
    for check in (
        check_traceability,
        check_ports,
        check_storage,
        check_protection,
        check_updates,
        check_adrs,
        check_risks,
    ):
        report.results += check(sections)
    return report


if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida el Diseño de Alto Nivel (HLD) del NAS"))
