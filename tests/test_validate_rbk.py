from __future__ import annotations

from conftest import ROOT, load_module

PLUGIN = ROOT / "runbook-plugin"
rbk = load_module(PLUGIN / "skills" / "validate-rbk" / "scripts" / "validate_rbk.py")
SAMPLE = (PLUGIN / "skills" / "create-rbk" / "examples" / "sample-rbk.md").read_text(
    encoding="utf-8"
)
STEP7_RUNNER = (
    "| **Riesgo** | Destructivo |\n| **Ejecuta** | Usuario |\n| **Dónde** | NAS por SSH |"
)


def _report(tmp_path, text):
    path = tmp_path / "RBK-2026-10-12-05-discos.md"
    path.write_text(text, encoding="utf-8")
    return rbk.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def _warning(report):
    return [r.message for r in report.results if r.level.value == "WARNING"]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_commands_in_unwraps_ssh_loops_and_chains():
    text = (
        "```bash\nssh nas 'for d in /dev/sda; do sudo smartctl -t long \"$d\"; done'\n"
        "ssh nas 'lsblk && sudo wipefs -a /dev/sdb'\n```"
    )
    cmds = rbk.commands_in(text)
    assert 'sudo smartctl -t long "$d"' in cmds
    assert "sudo wipefs -a /dev/sdb" in cmds


def test_destructive_command_in_change_step_is_critical(tmp_path):
    text = SAMPLE.replace(STEP7_RUNNER, STEP7_RUNNER.replace("Destructivo", "Cambio"))
    assert any("Comando destructivo" in m for m in _critical(_report(tmp_path, text)))


def test_destructive_step_by_agent_is_critical(tmp_path):
    text = SAMPLE.replace(STEP7_RUNNER, STEP7_RUNNER.replace("Usuario", "Agente"))
    assert any("ejecutado por el agente" in m for m in _critical(_report(tmp_path, text)))


def test_hidden_destructive_command_over_ssh_is_critical(tmp_path):
    text = SAMPLE.replace(
        "ssh nas 'findmnt -rn -o SOURCE,TARGET",
        "ssh nas 'sudo mkfs.ext4 /dev/sdb1; findmnt -rn -o SOURCE,TARGET",
    )
    critical = _critical(_report(tmp_path, text))
    assert any("Paso 6" in r.section for r in _report(tmp_path, text).results)
    assert any("formatear" in m for m in critical)


def test_destructive_without_precheck_is_critical(tmp_path):
    start = SAMPLE.index("### Paso 7")
    step7 = SAMPLE[start:]
    without = step7.replace("Comprobación previa:", "Antes:", 1)
    text = SAMPLE[:start] + without
    assert any("sin comprobación previa" in m for m in _critical(_report(tmp_path, text)))


def test_invalid_risk_is_critical(tmp_path):
    text = SAMPLE.replace("| **Riesgo** | Lectura |", "| **Riesgo** | Bajo |", 1)
    assert any("Riesgo 'Bajo'" in m for m in _critical(_report(tmp_path, text)))


def test_change_step_without_rollback_warns(tmp_path):
    start = SAMPLE.index("### Paso 3")
    end = SAMPLE.index("### Paso 4")
    step3 = SAMPLE[start:end].replace("Si falla:", "Nota:")
    text = SAMPLE[:start] + step3 + SAMPLE[end:]
    assert any("sin 'Si falla'" in m for m in _warning(_report(tmp_path, text)))


def test_max_risk_mismatch_warns(tmp_path):
    text = SAMPLE.replace("| **Riesgo máximo** | Destructivo |", "| **Riesgo máximo** | Cambio |")
    assert any("Riesgo máximo" in m for m in _warning(_report(tmp_path, text)))


def test_missing_phase_is_critical(tmp_path):
    text = SAMPLE.replace("| **Fase** | 05 — Discos: revisión SMART y formateo |\n", "")
    assert any("fase" in m for m in _critical(_report(tmp_path, text)))


def test_missing_hld_reference_is_critical(tmp_path):
    text = SAMPLE.replace("HLD v1 (1.0, Aprobado)", "la guía")
    assert any("HLD" in m for m in _critical(_report(tmp_path, text)))


def test_no_steps_is_critical(tmp_path):
    start = SAMPLE.index("### Paso 1")
    end = SAMPLE.index("## Verificación final")
    text = SAMPLE[:start] + SAMPLE[end:]
    assert any("No hay pasos" in m for m in _critical(_report(tmp_path, text)))
