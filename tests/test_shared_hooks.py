from __future__ import annotations

import json
import shutil

from conftest import SHARED, run_hook

VALIDATOR = """import sys
text = open(sys.argv[1]).read()
if "CRIT" in text:
    print("[CRITICAL] fallo"); sys.exit(1)
if "WARN" in text:
    print("[WARNING] aviso"); sys.exit(2)
sys.exit(0)
"""


def _plugin(tmp_path):
    plugin = tmp_path / "x-plugin"
    (plugin / "scripts").mkdir(parents=True)
    shutil.copy(SHARED / "hooks" / "validate_output_hook.py", plugin / "scripts")
    (plugin / "validator.py").write_text(VALIDATOR, encoding="utf-8")
    return plugin / "scripts" / "validate_output_hook.py"


def _write(tmp_path, text):
    out = tmp_path / "repo" / "outputs" / "nrd" / "v1" / "NRD-2026-10-08-x.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return {"tool_input": {"file_path": str(out)}}


def test_validate_hook_blocks_on_critical(tmp_path):
    result = run_hook(_plugin(tmp_path), _write(tmp_path, "CRIT"), "nrd", "validator.py")
    assert result.returncode == 2
    assert "fallo" in result.stderr


def test_validate_hook_warns_without_blocking(tmp_path):
    result = run_hook(_plugin(tmp_path), _write(tmp_path, "WARN"), "nrd", "validator.py")
    assert result.returncode == 0
    assert "aviso" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_validate_hook_ignores_other_deliverables(tmp_path):
    result = run_hook(_plugin(tmp_path), _write(tmp_path, "CRIT"), "hld", "validator.py")
    assert result.returncode == 0 and result.stdout == ""


def test_learnings_queue_reminder(tmp_path):
    payload = _write(tmp_path, "ok")
    queue = tmp_path / "repo" / "memory" / "nrd" / "learnings-queue.jsonl"
    queue.parent.mkdir(parents=True)
    queue.write_text(
        '{"skill":"create-nrd","status":"pending"}\n{"skill":"x","status":"applied"}\n',
        encoding="utf-8",
    )
    script = SHARED / "hooks" / "check_learnings_queue.py"
    result = run_hook(script, payload, "requirements-plugin", "nrd")
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "1 corrección" in context
    assert "/requirements-plugin:apply-learnings" in context


def test_learnings_queue_silent_when_empty(tmp_path):
    script = SHARED / "hooks" / "check_learnings_queue.py"
    result = run_hook(script, _write(tmp_path, "ok"), "requirements-plugin", "nrd")
    assert result.stdout == ""
