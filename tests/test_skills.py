"""Frontmatter, sección de aprendizajes y evals de todas las skills (derivado de RDEWAI)."""

from __future__ import annotations

import pytest
import yaml
from conftest import ROOT
from registry import load_registry, ready_plugins

SKILLS = [
    (plugin, path.parent.name, path)
    for plugin in ready_plugins()
    for path in sorted((ROOT / plugin / "skills").glob("*/SKILL.md"))
]
IDS = [f"{p}/{s}" for p, s, _ in SKILLS]
CORE = [(p, s, path) for p, s, path in SKILLS if s != "apply-learnings"]
CORE_IDS = [f"{p}/{s}" for p, s, _ in CORE]
FORK_PREFIXES = ("create-", "update-")
NO_EVALS = ("apply-learnings", "approve-")

VALID_EXPECTED_TYPES = {
    "validation_pass",
    "validation_fail",
    "section_present",
    "content_contains",
    "no_vague_language",
    "asks_question",
    "asks_confirmation",
    "no_output_generated",
    "file_created",
    "exit_code",
    "yaml_valid",
    "status_is",
    "command_denied",
    "command_handed_to_user",
    "stops_with_message",
}


def _parse(path):
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---"), f"{path} debe empezar con frontmatter YAML"
    _, fm, body = content.split("---", 2)
    return yaml.safe_load(fm), body


@pytest.mark.parametrize("plugin,skill,path", SKILLS, ids=IDS)
def test_frontmatter(plugin, skill, path):
    fm, _ = _parse(path)
    assert fm["name"] == skill
    assert "úsala cuando" in fm["description"].lower(), "la descripción necesita 'Úsala cuando'"
    assert fm.get("allowed-tools")


@pytest.mark.parametrize("plugin,skill,path", SKILLS, ids=IDS)
def test_fork_context(plugin, skill, path):
    fm, _ = _parse(path)
    if skill.startswith(FORK_PREFIXES):
        assert fm.get("context") == "fork"
    elif skill.startswith("validate-"):
        assert fm.get("context") != "fork"


@pytest.mark.parametrize("plugin,skill,path", CORE, ids=CORE_IDS)
def test_learnings_section(plugin, skill, path):
    _, body = _parse(path)
    assert "## Aprendizajes y correcciones" in body
    assert "Meta-reglas" in body
    assert "### Aprendizajes activos" in body


@pytest.mark.parametrize("plugin,skill,path", CORE, ids=CORE_IDS)
def test_no_cross_plugin_paths(plugin, skill, path):
    """Las skills se invocan con /plugin:skill, nunca leyendo ficheros de otro plugin."""
    _, body = _parse(path)
    for other in load_registry():
        if other != plugin:
            assert f"{other}/skills/" not in body


EVALS = [(p, s, path) for p, s, path in SKILLS if not s.startswith(NO_EVALS)]
EVAL_IDS = [f"{p}/{s}" for p, s, _ in EVALS]


@pytest.mark.parametrize("plugin,skill,path", EVALS, ids=EVAL_IDS)
def test_evals(plugin, skill, path):
    eval_file = path.parent / "evals" / "eval-cases.yaml"
    assert eval_file.exists(), f"falta {eval_file}"
    data = yaml.safe_load(eval_file.read_text(encoding="utf-8"))
    assert data["skill"] == skill
    assert "version" in data
    cases = data["cases"]
    assert len(cases) >= 3, "mínimo 3 casos"
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    for case in cases:
        missing = {"id", "name", "expected", "success_criteria"} - set(case)
        assert not missing, f"{case.get('id')}: faltan {missing}"
        for exp in case["expected"]:
            assert exp["type"] in VALID_EXPECTED_TYPES, f"{case['id']}: tipo {exp['type']}"
