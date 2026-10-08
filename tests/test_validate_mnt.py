from __future__ import annotations

from conftest import ROOT, load_module

PLUGIN = ROOT / "maintainer-plugin"
mnt = load_module(PLUGIN / "skills" / "validate-mnt" / "scripts" / "validate_mnt.py")
SAMPLE = (PLUGIN / "skills" / "create-mnt" / "examples" / "sample-mnt.md").read_text(
    encoding="utf-8"
)
STORAGE_ACTION = (
    "| Diagnosticar D1 y preparar su sustitución | Alta | Adulto 1 | 2026-12-05 | "
    "`/storage-plugin:diagnose-disk` |\n"
)


def _report(tmp_path, text):
    path = tmp_path / "MNT-2026-12-01-mensual.md"
    path.write_text(text, encoding="utf-8")
    return mnt.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def _warning(report):
    return [r.message for r in report.results if r.level.value == "WARNING"]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_degrading_disk_without_storage_action_is_critical(tmp_path):
    text = SAMPLE.replace(STORAGE_ACTION, "").replace(
        "`/storage-plugin:create-dcp`", "`/maintainer-plugin:create-upd`"
    )
    assert any("experto en discos" in m for m in _critical(_report(tmp_path, text)))


def test_green_light_with_failure_is_critical(tmp_path):
    text = SAMPLE.replace("| **Semáforo** | Rojo |", "| **Semáforo** | Verde |")
    assert any("Verde con tareas en Fallo" in m for m in _critical(_report(tmp_path, text)))


def test_missing_monthly_task_warns(tmp_path):
    text = SAMPLE.replace(
        "| Limpiar el filtro de polvo | Mensual | OK | Confirmado por el usuario |\n", ""
    )
    assert any("filtro de polvo" in m for m in _warning(_report(tmp_path, text)))


def test_invalid_period_is_critical(tmp_path):
    text = SAMPLE.replace("| **Periodo** | Mensual |", "| **Periodo** | Anual |")
    assert any("Periodo" in m for m in _critical(_report(tmp_path, text)))


def test_hot_disk_without_cooling_action_warns(tmp_path):
    text = SAMPLE.replace(
        "| Revisar el aire de la bahía de D1 (41 °C) y limpiar el filtro | Media | Adulto 1 | "
        "2026-12-03 | — |\n",
        "",
    )
    assert any("41 °C" in m for m in _warning(_report(tmp_path, text)))


def test_action_without_date_warns(tmp_path):
    text = SAMPLE.replace("| Adulto 1 | 2027-01-10 |", "| Adulto 1 | pronto |")
    assert any("sin responsable o fecha" in m for m in _warning(_report(tmp_path, text)))
