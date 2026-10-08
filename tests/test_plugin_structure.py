"""Convenciones que debe cumplir cada plugin de registry.yaml."""

from __future__ import annotations

import json

import pytest
from conftest import ROOT, load_module
from jinja2 import Environment
from registry import deliverables, ready_plugins

PLUGINS = list(ready_plugins())
DELIVERABLES = deliverables(ready_only=True)
ALL_DELIVERABLES = deliverables()
CORE_SKILLS = ("create", "update", "validate", "approve")


def _hooks(plugin: str) -> dict:
    return json.loads((ROOT / plugin / "hooks" / "hooks.json").read_text(encoding="utf-8"))


def _commands(plugin: str, event: str) -> list[str]:
    return [
        h["command"]
        for group in _hooks(plugin)["hooks"].get(event, [])
        for h in group.get("hooks", [])
    ]


def test_marketplace_matches_registry():
    data = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    listed = {p["name"]: p["source"] for p in data["plugins"]}
    assert set(listed) == set(PLUGINS)
    for name, source in listed.items():
        assert source == f"./{name}"


@pytest.mark.parametrize("plugin", PLUGINS)
def test_plugin_manifest(plugin):
    manifest = json.loads(
        (ROOT / plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == plugin
    assert manifest.get("description")
    assert (ROOT / plugin / "README.md").exists()
    assert (ROOT / plugin / "skills" / "apply-learnings" / "SKILL.md").exists()


@pytest.mark.parametrize("plugin", PLUGINS)
def test_plugin_hooks(plugin):
    pre = _commands(plugin, "PreToolUse")
    post = _commands(plugin, "PostToolUse")
    assert any("ssh_guard.py" in c for c in pre), "falta el guard SSH en PreToolUse"
    assert any("secrets_guard.py" in c for c in post), "falta el guard de secretos"
    assert any("check_learnings_queue.py" in c for c in post)
    for abbr, d in DELIVERABLES.items():
        if d["plugin"] != plugin:
            continue
        validator = f"skills/validate-{abbr}/scripts/validate_{abbr}.py"
        assert any(f"validate_output_hook.py {abbr} {validator}" in c for c in post)
        assert (ROOT / plugin / validator).exists()


@pytest.mark.parametrize("abbr", list(DELIVERABLES))
def test_deliverable_layout(abbr):
    d = DELIVERABLES[abbr]
    plugin = ROOT / d["plugin"]
    for kind in CORE_SKILLS:
        assert (plugin / "skills" / f"{kind}-{abbr}" / "SKILL.md").exists()
    assert (plugin / "skills" / f"create-{abbr}" / f"{d['prefix']}_template.j2").exists()
    assert list((plugin / "skills" / f"create-{abbr}" / "examples").glob("*.md"))
    assert (ROOT / "memory" / abbr / "learnings-queue.jsonl").exists()
    assert (ROOT / "outputs" / abbr / "v1").is_dir()
    for up in d.get("upstream", []):
        assert up in ALL_DELIVERABLES, f"{abbr}: entregable previo desconocido {up}"


def _validator(abbr: str):
    d = DELIVERABLES[abbr]
    path = ROOT / d["plugin"] / "skills" / f"validate-{abbr}" / "scripts" / f"validate_{abbr}.py"
    return load_module(path)


@pytest.mark.parametrize("abbr", list(DELIVERABLES))
def test_template_has_required_sections(abbr):
    d = DELIVERABLES[abbr]
    template = ROOT / d["plugin"] / "skills" / f"create-{abbr}" / f"{d['prefix']}_template.j2"
    source = template.read_text(encoding="utf-8")
    Environment().parse(source)
    for section in _validator(abbr).REQUIRED_SECTIONS:
        assert section in source, f"la plantilla no contiene la sección '{section}'"


@pytest.mark.parametrize("abbr", list(DELIVERABLES))
def test_examples_pass_validation(abbr):
    d = DELIVERABLES[abbr]
    validator = _validator(abbr)
    examples = ROOT / d["plugin"] / "skills" / f"create-{abbr}" / "examples"
    for example in examples.glob("*.md"):
        report = validator.validate(example)
        problems = [f"{r.level.value} {r.section}: {r.message}" for r in report.results]
        assert report.passed, f"{example.name}: {problems}"
