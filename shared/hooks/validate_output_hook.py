#!/usr/bin/env python3
"""PostToolUse (Write|Edit): valida un entregable al escribirlo en outputs/<entregable>/.

Derivado de validate-drd-hook.py de RDEWAI (modificado). Fuente única: shared/hooks/.

Uso en hooks.json:
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_output_hook.py <entregable> <validador>
<validador> es relativo a la raíz del plugin. CRITICAL -> exit 2 (bloquea y devuelve el
informe a Claude); WARNING -> contexto adicional no bloqueante.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        return 0
    deliverable, validator_rel = sys.argv[1], sys.argv[2]
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if f"/outputs/{deliverable}/" not in file_path or not file_path.endswith(".md"):
        return 0

    plugin_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    validator = os.path.join(plugin_root, validator_rel)
    if not os.path.exists(validator):
        return 0

    try:
        result = subprocess.run(
            [sys.executable, validator, file_path], capture_output=True, text=True, timeout=25
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0

    if result.returncode == 1:
        print(result.stdout, file=sys.stderr)
        return 2
    if result.returncode == 2:
        context = f"Avisos de validación de {os.path.basename(file_path)}:\n{result.stdout}"
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": context,
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
