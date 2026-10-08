#!/usr/bin/env python3
"""PostToolUse (Write|Edit): recuerda las correcciones pendientes de la cola de learnings.

Derivado de check-learnings-queue.py de RDEWAI (modificado). Fuente única: shared/hooks/.

Uso: python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_learnings_queue.py <plugin> <entregable>...
La raíz del proyecto se deduce de la ruta escrita (…/outputs/<entregable>/…), porque el
plugin instalado vive en la caché de Claude Code, no en el repo.
"""

from __future__ import annotations

import json
import os
import sys


def pending_count(queue_file: str) -> int:
    count = 0
    try:
        with open(queue_file, encoding="utf-8") as fh:
            for line in fh:
                try:
                    if json.loads(line).get("status") == "pending":
                        count += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        return 0
    return count


def main() -> int:
    if len(sys.argv) < 3:
        return 0
    plugin, deliverables = sys.argv[1], sys.argv[2:]
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path", "")

    for d in deliverables:
        marker = f"/outputs/{d}/"
        if marker not in file_path:
            continue
        root = file_path.split(marker)[0]
        queue = os.path.join(root, "memory", d, "learnings-queue.jsonl")
        count = pending_count(queue)
        if count:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": (
                                f"COLA DE LEARNINGS: {count} corrección(es) pendiente(s) en "
                                f"memory/{d}/learnings-queue.jsonl. Al terminar la skill actual, "
                                f"ejecuta /{plugin}:apply-learnings."
                            ),
                        }
                    },
                    ensure_ascii=False,
                )
            )
        break
    return 0


if __name__ == "__main__":
    sys.exit(main())
