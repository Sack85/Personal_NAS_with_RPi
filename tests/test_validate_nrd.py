from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import ROOT, load_module

PLUGIN = ROOT / "requirements-plugin"
VALIDATOR = PLUGIN / "skills" / "validate-nrd" / "scripts" / "validate_nrd.py"
SAMPLE = (PLUGIN / "skills" / "create-nrd" / "examples" / "sample-nrd.md").read_text(
    encoding="utf-8"
)

nrd = load_module(VALIDATOR)


def _report(tmp_path, text):
    path = tmp_path / "NRD-2026-10-08-test.md"
    path.write_text(text, encoding="utf-8")
    return nrd.validate(path)


def _messages(report, level):
    return [r.message for r in report.results if r.level.value == level]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_missing_section_is_critical(tmp_path):
    text = SAMPLE.replace("## 5. Protección de datos", "## 5. Otra cosa")
    assert any("Protección de datos" in m for m in _messages(_report(tmp_path, text), "CRITICAL"))


def test_invalid_criticality_is_critical(tmp_path):
    text = SAMPLE.replace("| 5 | Irreemplazable |", "| 5 | Importante |")
    assert any("criticidad" in m for m in _messages(_report(tmp_path, text), "CRITICAL"))


def test_unmeasured_irreplaceable_data_warns(tmp_path):
    text = SAMPLE.replace("| Medido con `du -sh` el 2026-10-08 |", "| Estimado |", 1)
    assert any("no está medido" in m for m in _messages(_report(tmp_path, text), "WARNING"))


def test_missing_scenario_warns(tmp_path):
    lines = [ln for ln in SAMPLE.split("\n") if not ln.startswith("| Ransomware")]
    report = _report(tmp_path, "\n".join(lines))
    assert any("ransomware" in m for m in _messages(report, "WARNING"))


def test_protection_without_rpo_is_critical(tmp_path):
    text = SAMPLE.replace("| Escenario | Datos afectados | RPO | RTO |", "| Escenario | Datos |")
    assert any("RPO" in m for m in _messages(_report(tmp_path, text), "CRITICAL"))


def test_objective_without_number_warns(tmp_path):
    text = SAMPLE.replace(
        "| 0 ficheros perdidos en la prueba semestral de restauración |", "| Que no se pierda |"
    )
    assert any("medida numérica" in m for m in _messages(_report(tmp_path, text), "WARNING"))


def test_open_question_without_date_warns(tmp_path):
    text = SAMPLE.replace("| Adulto 1 | 2026-11-15 |", "| Adulto 1 | pronto |")
    assert any(
        "sin responsable o fecha" in m for m in _messages(_report(tmp_path, text), "WARNING")
    )


def test_exposure_rule_missing_warns(tmp_path):
    text = SAMPLE.replace("- Nunca se exponen a Internet", "- Se exponen a Internet")
    assert any("no se expone" in m for m in _messages(_report(tmp_path, text), "WARNING"))


@pytest.mark.parametrize(
    "secret", ["password: Hunter2Hunter2", "Router con IP pública 81.56.120.33"]
)
def test_secrets_are_critical(tmp_path, secret):
    text = SAMPLE.replace("## 7. Seguridad y acceso\n", f"## 7. Seguridad y acceso\n\n{secret}\n")
    assert any("sensible" in m for m in _messages(_report(tmp_path, text), "CRITICAL"))


def test_bad_status_is_critical(tmp_path):
    text = SAMPLE.replace("| **Estado** | Borrador |", "| **Estado** | Hecho |")
    assert any("Estado" in m for m in _messages(_report(tmp_path, text), "CRITICAL"))


def test_cli_exit_codes(tmp_path):
    good = tmp_path / "ok.md"
    good.write_text(SAMPLE, encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("# vacío", encoding="utf-8")
    run = [sys.executable, str(VALIDATOR)]
    assert subprocess.run(run + [str(good)], capture_output=True).returncode == 0
    assert subprocess.run(run + [str(bad)], capture_output=True).returncode == 1
    assert subprocess.run(run + [str(tmp_path / "x.md")], capture_output=True).returncode == 3
    assert subprocess.run(run + ["--all", str(tmp_path)], capture_output=True).returncode == 1
