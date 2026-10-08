from __future__ import annotations

from conftest import ROOT, load_module

PLUGIN = ROOT / "operator-plugin"
ops = load_module(PLUGIN / "skills" / "validate-ops" / "scripts" / "validate_ops.py")
SAMPLE = (PLUGIN / "skills" / "create-ops" / "examples" / "sample-ops.md").read_text(
    encoding="utf-8"
)
STEP4 = "| 4. Borrar los discos | Destructivo | Usuario | 12:30 | OK | E4 |"


def _report(tmp_path, text):
    path = tmp_path / "OPS-2026-10-13-rbk05-discos.md"
    path.write_text(text, encoding="utf-8")
    return ops.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_unapproved_source_is_critical(tmp_path):
    text = SAMPLE.replace("RBK v1 (1.0, Aprobado)", "RBK v1 (1.0, Borrador)")
    assert any("documento aprobado" in m for m in _critical(_report(tmp_path, text)))


def test_upd_and_dcp_sources_are_accepted(tmp_path):
    for doc in ("UPD v3 (1.0, Aprobado)", "DCP v1 (1.2, Aprobado)"):
        text = SAMPLE.replace("RBK v1 (1.0, Aprobado)", doc)
        assert not any("documento aprobado" in m for m in _critical(_report(tmp_path, text)))


def test_destructive_step_by_agent_is_critical(tmp_path):
    text = SAMPLE.replace(STEP4, STEP4.replace("Usuario", "Agente"))
    assert any("ejecutado por el agente" in m for m in _critical(_report(tmp_path, text)))


def test_completed_with_failed_step_is_critical(tmp_path):
    text = SAMPLE.replace(STEP4, STEP4.replace("| OK |", "| Fallo |"))
    critical = _critical(_report(tmp_path, text))
    assert any("Completado con pasos" in m for m in critical)


def test_failed_step_without_incident_is_critical(tmp_path):
    text = SAMPLE.replace(STEP4, STEP4.replace("| OK |", "| Fallo |"))
    text = text.replace("| 2 | Atributo 193", "| — | Atributo 193")
    text = text.replace("| **Resultado** | Completado |", "| **Resultado** | Parcial |")
    assert any("sin incidencia" in m for m in _critical(_report(tmp_path, text)))


def test_failed_final_check_is_critical(tmp_path):
    text = SAMPLE.replace("| Paridad sin reserva | 0 | Sí |", "| Paridad sin reserva | 5 % | No |")
    assert any("no superada" in m for m in _critical(_report(tmp_path, text)))


def test_in_progress_is_info_only(tmp_path):
    text = SAMPLE.replace("| **Resultado** | Completado |", "| **Resultado** | En curso |")
    report = _report(tmp_path, text)
    assert not _critical(report)
    assert any(r.level.value == "INFO" for r in report.results)


def test_invalid_outcome_is_critical(tmp_path):
    text = SAMPLE.replace("| **Resultado** | Completado |", "| **Resultado** | Bien |")
    assert any("Resultado 'Bien'" in m for m in _critical(_report(tmp_path, text)))


def test_secret_in_evidence_is_critical(tmp_path):
    text = SAMPLE.replace(
        "Reserved block count:     0", "Reserved block count:     0\npassword: Hunter2Hunter2"
    )
    assert any("sensible" in m for m in _critical(_report(tmp_path, text)))
