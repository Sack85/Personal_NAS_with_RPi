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
import shlex
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doc_validation import (  # noqa: E402
    ValidationReport,
    ValidationResult,
    base_report,
    check_no_empty_sections,
    check_required_sections,
    check_upstream_reference,
    common_checks,
    critical,
    destructive_reason,
    find_section,
    find_table,
    parse_metadata,
    parse_sections,
    run_cli,
    warning,
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

RISKS = ("Lectura", "Cambio", "Destructivo")
RUNNERS = ("Agente", "Usuario")
STEP = re.compile(r"^Paso\s+(\d+)\s*:")
CODE = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)
SSH_OPTS_WITH_ARG = set("bcDEeFIiJLlmOopQRSWw")


def _remote(line: str) -> str:
    """Si la línea es `ssh [opciones] host comando`, devuelve el comando remoto."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        return line
    if not tokens or tokens[0] != "ssh":
        return line
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if len(tokens[i]) == 2 and tokens[i][1] in SSH_OPTS_WITH_ARG else 1
    return " ".join(tokens[i + 1 :])


def commands_in(text: str) -> list[str]:
    """Comandos simples de todos los bloques de código (deshace ssh, bucles y encadenados)."""
    out: list[str] = []
    for block in CODE.findall(text):
        for line in block.split("\n"):
            line = line.split(" #")[0].strip()
            if not line or line.startswith("#"):
                continue
            for part in re.split(r"&&|\|\||;|\|", _remote(line)):
                part = re.sub(r"^(do|then|else)\s+", "", part.strip())
                if part and not part.startswith(("for ", "done", "fi", "if ")):
                    out.append(part)
    return out


def _between(text: str, start: str, *ends: str) -> str:
    """Texto desde `start` hasta el primero de `ends` (o el final)."""
    i = text.find(start)
    if i < 0:
        return ""
    rest = text[i + len(start) :]
    cut = min((rest.find(e) for e in ends if rest.find(e) >= 0), default=len(rest))
    return rest[:cut]


def check_steps(sections: dict[str, str]) -> tuple[list[ValidationResult], list[str]]:
    body = find_section(sections, "Pasos") or ""
    steps = {h: b for h, b in parse_sections(body, level=3).items() if STEP.match(h)}
    if not steps:
        return [critical("Pasos", "No hay pasos (### Paso N: …)", "Añade al menos un paso")], []
    results: list[ValidationResult] = []
    risks: list[str] = []
    expected_n = 1
    for heading, text in steps.items():
        n = int(STEP.match(heading).group(1))
        where = f"Paso {n}"
        if n != expected_n:
            results.append(
                warning(where, f"Numeración: se esperaba el paso {expected_n}", "Renumera")
            )
        expected_n = n + 1

        meta = parse_metadata(text)
        risk, runner, place = meta.get("Riesgo", ""), meta.get("Ejecuta", ""), meta.get("Dónde", "")
        if risk not in RISKS:
            results.append(
                critical(where, f"Riesgo '{risk}' no válido", f"Usa uno de {', '.join(RISKS)}")
            )
        if runner not in RUNNERS:
            results.append(critical(where, f"Ejecuta '{runner}' no válido", "Agente o Usuario"))
        if not place:
            results.append(critical(where, "Falta 'Dónde'", "PC, NAS por SSH, Web de OMV…"))
        risks.append(risk)

        command_text = _between(text, "Comando:", "Esperado:", "Si falla:") or (
            text if "Comprobación previa:" not in text else ""
        )
        destructive = [r for c in commands_in(command_text) if (r := destructive_reason(c))]
        if destructive and risk != "Destructivo":
            results.append(
                critical(
                    where,
                    f"Comando destructivo ({destructive[0]}) en un paso de riesgo '{risk}'",
                    "Marca el paso como Destructivo y que lo ejecute el usuario",
                )
            )
        if risk == "Destructivo" or destructive:
            if runner != "Usuario":
                results.append(
                    critical(
                        where,
                        "Paso destructivo ejecutado por el agente",
                        "Ejecuta: Usuario. El guard SSH lo bloquearía igualmente",
                    )
                )
            if "Comprobación previa:" not in text:
                results.append(
                    critical(
                        where,
                        "Paso destructivo sin comprobación previa",
                        "Identifica el disco (lsblk con modelo y serie) antes de tocarlo",
                    )
                )
            if "Si falla:" not in text:
                results.append(critical(where, "Paso destructivo sin 'Si falla'", "Añádelo"))
        elif risk == "Cambio" and "Si falla:" not in text:
            results.append(warning(where, "Paso de cambio sin 'Si falla'", "Cómo deshacerlo"))
        if "Esperado:" not in text:
            results.append(warning(where, "Falta 'Esperado'", "Qué salida confirma el paso"))
    return results, risks


def check_header(content: str, risks: list[str]) -> list[ValidationResult]:
    meta = parse_metadata(content)
    results = []
    if not re.match(r"^\d{2}\b", meta.get("Fase", "")):
        results.append(
            critical("Metadatos", "Falta la fase (NN — nombre)", "Añade | **Fase** | 05 — … |")
        )
    known = [r for r in risks if r in RISKS]
    if known:
        worst = max(known, key=RISKS.index)
        if meta.get("Riesgo máximo") != worst:
            results.append(
                warning(
                    "Metadatos",
                    f"Riesgo máximo '{meta.get('Riesgo máximo', '')}' no coincide con '{worst}'",
                    f"Pon | **Riesgo máximo** | {worst} |",
                )
            )
    return results


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
