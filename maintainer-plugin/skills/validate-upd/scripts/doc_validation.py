#!/usr/bin/env python3
"""Núcleo común de validación de entregables (derivado de validate_drd.py de RDEWAI, modificado).

Fuente única: shared/doc_validation.py. `make sync` lo copia a cada plugin; no editar las copias.

Uso directo (pre-commit): python doc_validation.py --secrets-only <ficheros...>

Códigos de salida de los validadores: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 error de fichero.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shlex
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ValidationLevel(Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationResult:
    level: ValidationLevel
    section: str
    message: str
    suggestion: str


@dataclass
class ValidationReport:
    file_path: str
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for r in self.results if r.level == ValidationLevel.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.level == ValidationLevel.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for r in self.results if r.level == ValidationLevel.INFO)

    @property
    def passed(self) -> bool:
        return self.critical_count == 0 and self.warning_count == 0

    @property
    def exit_code(self) -> int:
        if self.critical_count:
            return 1
        if self.warning_count:
            return 2
        return 0


STATUSES = ("Borrador", "En revisión", "Aprobado")
REQUIRED_METADATA = ("Documento", "Versión", "Estado", "Última modificación", "Autor")
VERSION_HISTORY = "Historial de versiones"


def critical(section: str, message: str, suggestion: str) -> ValidationResult:
    return ValidationResult(ValidationLevel.CRITICAL, section, message, suggestion)


def warning(section: str, message: str, suggestion: str) -> ValidationResult:
    return ValidationResult(ValidationLevel.WARNING, section, message, suggestion)


def info(section: str, message: str, suggestion: str) -> ValidationResult:
    return ValidationResult(ValidationLevel.INFO, section, message, suggestion)


# --- Parsing -----------------------------------------------------------------


def parse_sections(content: str, level: int = 2) -> dict[str, str]:
    """Devuelve {título de sección: contenido} para los encabezados del nivel dado."""
    marker = "#" * level + " "
    sections: dict[str, str] = {}
    heading = ""
    lines: list[str] = []
    in_code = False
    for line in content.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith(marker):
            if heading:
                sections[heading] = "\n".join(lines).strip()
            heading = line[len(marker) :].strip()
            lines = []
        else:
            lines.append(line)
    if heading:
        sections[heading] = "\n".join(lines).strip()
    return sections


def find_section(sections: dict[str, str], name: str) -> str | None:
    """Busca una sección por nombre, ignorando la numeración inicial ("3. Red" == "Red")."""
    target = _normalize_heading(name)
    for heading, body in sections.items():
        if _normalize_heading(heading) == target:
            return body
    return None


def _normalize_heading(heading: str) -> str:
    return re.sub(r"^[\d.]+\s*", "", heading).strip().lower()


def table_rows(content: str) -> list[list[str]]:
    """Filas de datos de las tablas markdown (sin cabecera ni separador)."""
    rows: list[list[str]] = []
    header_seen = False
    for line in content.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            header_seen = False
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not header_seen:
            header_seen = True
            continue
        rows.append(cells)
    return rows


def has_table_rows(content: str) -> bool:
    return bool(table_rows(content))


def parse_tables(content: str) -> list[list[dict[str, str]]]:
    """Cada tabla markdown como lista de filas {cabecera en minúsculas: celda}."""
    tables: list[list[dict[str, str]]] = []
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in content.split("\n") + [""]:
        s = line.strip()
        if not s.startswith("|"):
            if header is not None:
                tables.append(rows)
            header, rows = None, []
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        else:
            rows.append(dict(zip(header, cells)))
    return tables


def find_table(content: str, *columns: str) -> list[dict[str, str]] | None:
    """Primera tabla cuyas cabeceras contienen todas las columnas indicadas."""
    wanted = [c.lower() for c in columns]
    for rows in parse_tables(content):
        if rows and all(any(w in h for h in rows[0]) for w in wanted):
            return rows
    return None


def cell(row: dict[str, str], column: str) -> str:
    """Valor de la primera columna cuya cabecera contiene `column`."""
    column = column.lower()
    return next((v for h, v in row.items() if column in h), "")


def has_content(content: str) -> bool:
    return any(
        s and not s.startswith("#") and not s.startswith("---")
        for s in (ln.strip() for ln in content.split("\n"))
    )


def parse_metadata(content: str) -> dict[str, str]:
    """Lee las filas `| **Clave** | Valor |` de la tabla de metadatos."""
    meta: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.*?)\s*\|\s*$", content, re.MULTILINE):
        meta.setdefault(m.group(1).strip(), m.group(2).strip())
    return meta


# --- Checks comunes ----------------------------------------------------------


def check_required_sections(
    sections: dict[str, str], required: list[str]
) -> list[ValidationResult]:
    return [
        critical(name, f"Falta la sección obligatoria '{name}'", f"Añade '## {name}'")
        for name in required
        if find_section(sections, name) is None
    ]


def check_metadata(content: str) -> list[ValidationResult]:
    meta = parse_metadata(content)
    results = [
        critical("Metadatos", f"Falta el campo '{key}'", f"Añade `| **{key}** | ... |`")
        for key in REQUIRED_METADATA
        if not meta.get(key)
    ]
    status = meta.get("Estado")
    if status and status not in STATUSES:
        results.append(
            critical("Metadatos", f"Estado '{status}' no válido", f"Usa uno de {STATUSES}")
        )
    version = meta.get("Versión")
    if version and not re.fullmatch(r"\d+\.\d+", version):
        results.append(critical("Metadatos", f"Versión '{version}' no válida", "Formato N.M"))
    return results


def check_version_history(sections: dict[str, str]) -> list[ValidationResult]:
    body = find_section(sections, VERSION_HISTORY)
    if body is not None and not has_table_rows(body):
        return [
            critical(
                VERSION_HISTORY,
                "El historial de versiones no tiene filas",
                "Añade | versión | fecha | autor | cambio |",
            )
        ]
    return []


def check_no_empty_sections(
    sections: dict[str, str], content_sections: list[str]
) -> list[ValidationResult]:
    results = []
    for name in content_sections:
        body = find_section(sections, name)
        if body is not None and not has_content(body):
            results.append(warning(name, "Sección vacía", "Complétala o explica por qué no aplica"))
    return results


def check_upstream_reference(content: str, abbr: str) -> list[ValidationResult]:
    """El entregable debe citar la versión aprobada del entregable previo."""
    meta = parse_metadata(content)
    ref = meta.get("Entregable previo", "")
    if abbr.upper() not in ref.upper() or not re.search(r"v\d+", ref):
        return [
            critical(
                "Metadatos",
                f"No se indica qué versión del {abbr.upper()} se ha usado",
                f"Añade `| **Entregable previo** | {abbr.upper()} vN (X.Y, Aprobado) |`",
            )
        ]
    return []


VAGUE_TERMS = [
    "etc.",
    "según sea necesario",
    "si hace falta",
    "si es necesario",
    "más o menos",
    "aproximadamente",
    "lo antes posible",
    "adecuado",
    "apropiado",
    "suficiente",
    "algunos",
    "varios",
    "normalmente",
    "en principio",
    "debería funcionar",
]


def check_vague_language(content: str) -> list[ValidationResult]:
    text = _strip_code(content).lower()
    found = [t for t in VAGUE_TERMS if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text)]
    if not found:
        return []
    return [
        warning(
            "Redacción",
            f"Lenguaje vago: {', '.join(found)}",
            "Sustituye por valores, umbrales o comandos concretos",
        )
    ]


def check_placeholders(content: str) -> list[ValidationResult]:
    results = []
    for n, line in enumerate(content.split("\n"), 1):
        if re.search(r"\[(TBD|PENDIENTE|TODO)\b", line, re.IGNORECASE) and not re.search(
            r"(responsable|fecha)\s*:", line, re.IGNORECASE
        ):
            results.append(
                info(
                    f"línea {n}",
                    "Marcador pendiente sin responsable ni fecha",
                    "Formato: [PENDIENTE: qué — responsable: X, fecha: AAAA-MM-DD]",
                )
            )
    return results


# --- Comandos destructivos (fuente única para ssh_guard.py y los validadores) ---

DEVICE = r"/dev/(sd[a-z]|nvme\d|mmcblk\d|disk/)"

DESTRUCTIVE: list[tuple[str, str]] = [
    (r"^mkfs(\.\w+)?\b|^mke2fs\b|^mkswap\b", "formatear"),
    (r"^wipefs\b", "borrar firmas de disco"),
    (r"^(sgdisk|gdisk|cfdisk|sfdisk)\b", "particionar"),
    (r"^parted\b(?!.*\s(-l|--list|print)\b)", "particionar"),
    (r"^fdisk\b(?!\s+-l)", "particionar"),
    (r"^dd\b.*\bof=", "escribir con dd"),
    (r"^(shred|blkdiscard)\b", "borrado irrecuperable"),
    (r"^tune2fs\b.*\s-[a-zA-Z]*m", "cambiar bloques reservados"),
    (r"^snapraid\b.*\bfix\b", "snapraid fix"),
    (r"^restic\b.*\b(forget|prune|key\s+remove)\b", "borrar snapshots de restic"),
    (r"^rpi-eeprom-(config|update)\b.*(\s-e\b|--edit|--apply|\s-a\b|\s-d\b)", "EEPROM"),
    (r"^mdadm\b.*--(create|zero-superblock|remove|fail)\b", "RAID"),
    (r"^(lvremove|vgremove|pvremove)\b", "LVM"),
    (r"^rm\b.*\s-[a-zA-Z]*[rR]", "borrado recursivo en el NAS"),
]


def strip_command_prefixes(command: str) -> str:
    """Quita sudo, env, timeout... para que las reglas se apliquen al comando real."""
    command = command.strip()
    while True:
        new = re.sub(r"^(sudo(\s+-\S+)*|env|nice|ionice|timeout\s+\S+|time)\s+", "", command)
        new = re.sub(r"^\w+=\S*\s+", "", new)
        if new == command:
            return command
        command = new


def destructive_reason(command: str) -> str | None:
    """Motivo si el comando (una línea) es destructivo para discos o backups."""
    cmd = strip_command_prefixes(command)
    for pattern, reason in DESTRUCTIVE:
        if re.search(pattern, cmd):
            return reason
    if re.search(r">\s*" + DEVICE, cmd):
        return "redirigir a un dispositivo de bloque"
    return None


# --- Pasos (RBK, UPD, DCP) -----------------------------------------------------

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


def check_steps(
    sections: dict[str, str], section: str = "Pasos"
) -> tuple[list[ValidationResult], list[str]]:
    """Reglas por paso (### Paso N:) comunes a RBK, UPD y DCP. Devuelve (hallazgos, riesgos)."""
    body = find_section(sections, section) or ""
    steps = {h: b for h, b in parse_sections(body, level=3).items() if STEP.match(h)}
    if not steps:
        return [critical(section, "No hay pasos (### Paso N: …)", "Añade al menos un paso")], []
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


def max_risk_check(content: str, risks: list[str]) -> list[ValidationResult]:
    """El metadato Riesgo máximo debe coincidir con el peor paso."""
    known = [r for r in risks if r in RISKS]
    if not known:
        return []
    worst = max(known, key=RISKS.index)
    declared = parse_metadata(content).get("Riesgo máximo", "")
    if declared != worst:
        return [
            warning(
                "Metadatos",
                f"Riesgo máximo '{declared}' no coincide con '{worst}'",
                f"Pon | **Riesgo máximo** | {worst} |",
            )
        ]
    return []


# --- Secretos ----------------------------------------------------------------

_PLACEHOLDER = re.compile(
    r"(x{3,}|\*{3,}|redact|cambiar|change|tu_|your_|ejemplo|example|<|\$\{|\$\(|\.\.\.)",
    re.IGNORECASE,
)
_KEYWORD_SECRET = re.compile(
    r"(?i)\b(password|passwd|pwd|contrase(?:ñ|n)a|passphrase|frase de acceso|api[_ -]?key|"
    r"token|secret|clave)\b\s*[:=]\s*[\"'`]?([^\s\"'`|]{6,})"
)
_TOKEN_PATTERNS = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "clave privada"),
    (re.compile(r"\btskey-[A-Za-z0-9-]{10,}"), "clave de Tailscale"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "token de GitHub"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "clave de API"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "clave de AWS"),
]
_APP_PASSWORD = re.compile(
    r"(?i)(aplicaci[oó]n|app[ _-]?password)[^:=\n]{0,30}[:=]\s*[\"'`]?(?:[a-z]{4}\s?){3}[a-z]{4}\b"
)
_IPV4 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])")
_ALLOWED_PUBLIC_IPS = {"1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"}
_DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def _is_public_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        return False
    if raw in _ALLOWED_PUBLIC_IPS or raw.startswith("255."):
        return False
    if any(ip in net for net in _DOC_NETS) or ip in _CGNAT:
        return False
    return ip.is_global and not ip.is_multicast


def find_secrets(content: str) -> list[tuple[int, str]]:
    """Devuelve [(línea, tipo)] de posibles secretos o datos que no deben publicarse."""
    hits: list[tuple[int, str]] = []
    for n, line in enumerate(content.split("\n"), 1):
        m = _KEYWORD_SECRET.search(line)
        if m and not _PLACEHOLDER.search(m.group(2)):
            hits.append((n, f"posible {m.group(1).lower()} en claro"))
        for pattern, kind in _TOKEN_PATTERNS:
            if pattern.search(line):
                hits.append((n, kind))
        if _APP_PASSWORD.search(line):
            hits.append((n, "posible contraseña de aplicación"))
        for raw in _IPV4.findall(line):
            if _is_public_ip(raw):
                hits.append((n, f"IP pública {raw}"))
    return hits


def check_secrets(content: str) -> list[ValidationResult]:
    return [
        critical(
            f"línea {n}",
            f"Dato sensible: {kind}",
            "Quítalo del repo: guárdalo fuera del NAS (gestor de contraseñas)",
        )
        for n, kind in find_secrets(content)
    ]


def common_checks(content: str, sections: dict[str, str]) -> list[ValidationResult]:
    return (
        check_metadata(content)
        + check_version_history(sections)
        + check_secrets(content)
        + check_vague_language(content)
        + check_placeholders(content)
    )


def _strip_code(content: str) -> str:
    return re.sub(r"```.*?```", "", content, flags=re.DOTALL)


# --- Salida y CLI ------------------------------------------------------------


def print_report(report: ValidationReport) -> None:
    print(f"\n=== {report.file_path} ===")
    for level in ValidationLevel:
        for r in (x for x in report.results if x.level == level):
            print(f"[{level.value}] {r.section}: {r.message}\n    → {r.suggestion}")
    print(
        f"Resultado: {report.critical_count} CRITICAL, {report.warning_count} WARNING, "
        f"{report.info_count} INFO — {'OK' if report.passed else 'REVISAR'}"
    )


def report_to_json(report: ValidationReport) -> str:
    return json.dumps(
        {
            "file": report.file_path,
            "passed": report.passed,
            "critical": report.critical_count,
            "warning": report.warning_count,
            "info": report.info_count,
            "results": [
                {
                    "level": r.level.value,
                    "section": r.section,
                    "message": r.message,
                    "suggestion": r.suggestion,
                }
                for r in report.results
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def run_cli(validate: Callable[[Path], ValidationReport], description: str) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("path", type=Path, help="Fichero o carpeta (con --all)")
    parser.add_argument("--all", action="store_true", help="Valida todos los .md de la carpeta")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.all:
        if not args.path.is_dir():
            print(f"Error: {args.path} no es una carpeta", file=sys.stderr)
            return 3
        files = sorted(args.path.glob("*.md"))
        if not files:
            print(f"No hay .md en {args.path}", file=sys.stderr)
            return 3
    else:
        if not args.path.is_file():
            print(f"Error: {args.path} no es un fichero", file=sys.stderr)
            return 3
        files = [args.path]

    worst = 0
    for path in files:
        report = validate(path)
        if args.format == "json":
            print(report_to_json(report))
        else:
            print_report(report)
        worst = max(worst, report.exit_code)
    return worst


def base_report(path: Path) -> tuple[ValidationReport, str, dict[str, str]]:
    content = path.read_text(encoding="utf-8")
    return ValidationReport(str(path)), content, parse_sections(content)


def _secrets_only(paths: list[str]) -> int:
    worst = 0
    for p in paths:
        try:
            text = Path(p).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, kind in find_secrets(text):
            print(f"{p}:{n}: {kind}", file=sys.stderr)
            worst = 1
    return worst


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--secrets-only":
        sys.exit(_secrets_only(sys.argv[2:]))
    print(__doc__)
