#!/usr/bin/env python3
"""PostToolUse (Write|Edit): bloquea secretos en ficheros que se versionan en GitHub.

Revisa outputs/, state/, inputs/ y memory/. Si encuentra una contraseña, token, clave
privada o IP pública, sale con 2: Claude recibe el aviso y debe quitar el dato.
Fuente única: shared/hooks/.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.dirname(_HERE)]  # copia en plugin / fuente en shared/

from doc_validation import find_secrets  # noqa: E402

WATCHED = re.compile(r"/(outputs|state|inputs|memory)/")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not WATCHED.search(file_path) or not os.path.isfile(file_path):
        return 0
    try:
        with open(file_path, encoding="utf-8") as fh:
            hits = find_secrets(fh.read())
    except (OSError, UnicodeDecodeError):
        return 0
    if not hits:
        return 0
    lines = "\n".join(f"  línea {n}: {kind}" for n, kind in hits)
    print(
        f"{file_path} contiene datos que no deben llegar a GitHub:\n{lines}\n"
        "Sustitúyelos por una referencia (p. ej. 'en el gestor de contraseñas') o por "
        "una IP privada/ejemplo.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
