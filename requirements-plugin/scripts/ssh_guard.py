#!/usr/bin/env python3
"""PreToolUse (Bash): guard de 3 niveles para comandos que tocan el NAS o sus discos.

Derivado de enforce-readonly-queries.py de RDEWAI (modificado). Fuente única: shared/hooks/.

- deny:  destructivo para discos o backups (mkfs, wipefs, dd of=, snapraid fix, restic forget...)
         -> el agente debe entregar el comando al usuario para que lo ejecute él.
- ask:   cambia el estado del NAS (apt, systemctl, reboot, snapraid sync, docker compose up...)
- allow: lecturas por SSH de una lista blanca (lsblk, smartctl -a, snapraid status...)
Los comandos locales que no tocan dispositivos de bloque no se evalúan.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

DEVICE = r"/dev/(sd[a-z]|nvme\d|mmcblk\d|disk/)"

DENY: list[tuple[str, str]] = [
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
DENY_ANYWHERE = [(r">\s*" + DEVICE, "redirigir a un dispositivo de bloque")]

ASK: list[tuple[str, str]] = [
    (
        r"^(apt|apt-get)\s+(install|remove|purge|upgrade|full-upgrade|dist-upgrade|autoremove)\b",
        "instalar o actualizar paquetes",
    ),
    (r"^systemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask)\b", "servicios"),
    (r"^(reboot|poweroff|shutdown|halt)\b", "reinicio o apagado"),
    (r"^snapraid\b.*\b(sync|scrub|touch)\b", "escribir paridad"),
    (r"^docker\b.*\b(up|down|rm|stop|restart|pull|run|start|kill)\b", "contenedores"),
    (r"^restic\b.*\b(backup|init|restore)\b", "restic"),
    (r"^(mount|umount)\s+\S", "montajes"),
    (r"^smartctl\b.*\s-(t|s|o)\b", "tests o ajustes SMART"),
    (r"^hdparm\b.*\s-[BSyY]\b", "energía de discos"),
]

READONLY = re.compile(
    r"^("
    r"lsblk|blkid|lspci|lsusb|lscpu|df|du|free|uptime|uname|hostname|hostnamectl|timedatectl|"
    r"cat|head|tail|grep|egrep|zgrep|ls|stat|wc|sort|uniq|cut|tr|column|which|id|whoami|date|"
    r"findmnt|ip|ss|ps|top\s+-bn1|vmstat|iostat|sensors|journalctl|dmesg|readlink|realpath|"
    r"sha256sum|md5sum|true|echo|printf|test|vcgencmd|upsc|"
    r"smartctl\s+(-[aAiHlxc]|--all|--info|--health|--xall|--attributes)|"
    r"hdparm\s+-[CI]|tune2fs\s+-l|dumpe2fs\s+-h|"
    r"systemctl\s+(status|is-active|is-enabled|is-failed|list-units|list-timers|show|cat)|"
    r"snapraid\b.*\b(status|diff|list|smart|devices)\b|"
    r"restic\b.*\b(snapshots|stats|ls|check|cat\s+config)\b|"
    r"docker\s+(ps|images|logs|inspect|version|info|compose\s+(ps|ls|logs|config|images))|"
    r"apt\s+(list|show|policy|changelog)|apt-cache|dpkg\s+(-l|-s|--status|--list)|"
    r"dpkg-query|rpi-eeprom-update$|rpi-eeprom-config$|omv-confdbadm\s+read|"
    r"find\b(?!.*-(delete|exec|execdir|ok)\b)"
    r")"
)

SSH_OPTS_WITH_ARG = set("bcDEeFIiJLlmOopQRSWw")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2\s*(?=\n|$)", re.DOTALL)


def _extract_heredocs(command: str) -> tuple[str, list[str]]:
    bodies: list[str] = []

    def repl(m: re.Match[str]) -> str:
        bodies.append(m.group(3))
        return f"__HEREDOC{len(bodies) - 1}__"

    return HEREDOC.sub(repl, command), bodies


def _split_unquoted(command: str) -> list[str]:
    """Parte por ; | || && y saltos de línea fuera de comillas y de $( )."""
    parts: list[str] = []
    buf: list[str] = []
    quote = ""
    depth = 0
    i = 0
    while i < len(command):
        c = command[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(command):
                buf.append(command[i : i + 2])
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
        elif command.startswith("$(", i):
            depth += 1
        elif c == ")" and depth:
            depth -= 1
        elif depth == 0 and c in ";|&\n":
            parts.append("".join(buf))
            buf = []
            i += 2 if command[i : i + 2] in ("||", "&&") else 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _strip_prefixes(seg: str) -> str:
    seg = seg.strip()
    while True:
        new = re.sub(r"^(sudo(\s+-\S+)*|env|nice|ionice|timeout\s+\S+|time)\s+", "", seg)
        new = re.sub(r"^\w+=\S*\s+", "", new)
        if new == seg:
            return seg
        seg = new


def _segments(command: str) -> list[str]:
    return [s for s in (_strip_prefixes(x) for x in _split_unquoted(command)) if s]


def _remote_command(segment: str) -> str | None:
    """`ssh [opciones] host [comando]` -> comando remoto ("" = sesión); None si no es ssh."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    if not tokens or tokens[0] != "ssh":
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        opt = tokens[i]
        i += 2 if len(opt) == 2 and opt[1] in SSH_OPTS_WITH_ARG else 1
    return " ".join(tokens[i + 1 :])


def _unwrap_shell(segment: str) -> str | None:
    m = re.match(r"^(bash|sh)\s+-c\s+(.+)$", segment, re.DOTALL)
    if not m:
        return None
    try:
        return " ".join(shlex.split(m.group(2)))
    except ValueError:
        return m.group(2)


def _match(rules: list[tuple[str, str]], segment: str) -> str | None:
    for pattern, reason in rules:
        if re.search(pattern, segment):
            return reason
    return None


def classify_remote(remote: str) -> tuple[str, str]:
    if not remote.strip():
        return "ask", "sesión SSH interactiva"
    decision, reason = "allow", "lectura"
    for seg in _segments(remote):
        inner = _unwrap_shell(seg)
        if inner is not None:
            d, r = classify_remote(inner)
        elif hit := _match(DENY, seg) or _match(DENY_ANYWHERE, seg):
            d, r = "deny", hit
        elif hit := _match(ASK, seg):
            d, r = "ask", hit
        elif READONLY.match(seg):
            d, r = "allow", "lectura"
        else:
            d, r = "ask", f"comando no reconocido como lectura: {seg.split()[0]}"
        if d == "deny":
            return d, r
        if d == "ask" and decision == "allow":
            decision, reason = d, r
    return decision, reason


def classify(command: str) -> tuple[str | None, str]:
    """Devuelve (decisión, motivo). decisión None = no es asunto de este guard."""
    decision: str | None = None
    reason = ""
    command, heredocs = _extract_heredocs(command)
    for seg in _segments(command):
        remote = _remote_command(seg)
        if remote is not None:
            for idx, body in enumerate(heredocs):
                marker = f"__HEREDOC{idx}__"
                if marker in remote:
                    remote = remote.replace(marker, "").strip()
                    remote = re.sub(r"^(sudo\s+)?(bash|sh)(\s+-\S+)*\s*(-s)?\s*$", "", remote)
                    remote = (remote + "\n" + body).strip()
            d, r = classify_remote(remote)
        elif re.match(r"^(scp|rsync)\b", seg) and re.search(r"\S+:\S*\s*$", seg):
            d, r = "ask", "copiar ficheros hacia el NAS"
        elif hit := _match(DENY_ANYWHERE, seg) or (re.search(DEVICE, seg) and _match(DENY, seg)):
            d, r = "deny", hit
        elif _match(DENY[:6], seg):
            d, r = "deny", _match(DENY[:6], seg) or ""
        else:
            continue
        if d == "deny":
            return d, r
        if decision is None or (decision == "allow" and d == "ask"):
            decision, reason = d, r
    return decision, reason


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    decision, reason = classify(command)
    if decision is None:
        return 0
    messages = {
        "deny": f"Bloqueado ({reason}). Es destructivo: da el comando exacto al usuario para que "
        "lo ejecute él por SSH tras revisarlo, y registra el resultado en el OPS.",
        "ask": f"Cambia el estado del NAS ({reason}). Confirma solo si está en un RBK/UPD/DCP "
        "aprobado.",
        "allow": "Lectura en el NAS permitida por el guard.",
    }
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": messages[decision],
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
