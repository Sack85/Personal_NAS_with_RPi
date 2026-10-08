from __future__ import annotations

import pytest
from conftest import ROOT, load_module

PLUGIN = ROOT / "architect-plugin"
hld = load_module(PLUGIN / "skills" / "validate-hld" / "scripts" / "validate_hld.py")
SAMPLE = (PLUGIN / "skills" / "create-hld" / "examples" / "sample-hld.md").read_text(
    encoding="utf-8"
)
PARITY_ROW = "| Paridad | WD Blue | 1 TB | SATA bahía 1 | ext4 (0 % reservado) |"


def _report(tmp_path, text):
    path = tmp_path / "HLD-2026-10-10-test.md"
    path.write_text(text, encoding="utf-8")
    return hld.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def _warning(report):
    return [r.message for r in report.results if r.level.value == "WARNING"]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_parity_smaller_than_data_is_critical(tmp_path):
    text = SAMPLE.replace(PARITY_ROW, PARITY_ROW.replace("1 TB", "500 GB"))
    assert any("menor que el mayor disco" in m for m in _critical(_report(tmp_path, text)))


def test_bigger_data_disk_than_parity_is_critical(tmp_path):
    text = SAMPLE.replace("| D2 | Samsung QVO | 1 TB |", "| D2 | Seagate | 2 TB |")
    assert any("menor que el mayor disco" in m for m in _critical(_report(tmp_path, text)))


def test_parity_in_pool_is_critical(tmp_path):
    text = SAMPLE.replace("/srv/dev-disk-by-uuid-… (parity) | No |", "/srv/x (parity) | Sí |")
    assert any("dentro del pool" in m for m in _critical(_report(tmp_path, text)))


def test_not_enough_content_files_is_critical(tmp_path):
    text = SAMPLE.replace("| / | No | Sí |", "| / | No | No |").replace(
        "(d2) | Sí | Sí |", "(d2) | Sí | No |"
    )
    assert any("content" in m for m in _critical(_report(tmp_path, text)))


def test_no_parity_is_critical(tmp_path):
    text = SAMPLE.replace("| Paridad | WD Blue", "| Extra | WD Blue")
    assert any("No hay disco de paridad" in m for m in _critical(_report(tmp_path, text)))


@pytest.mark.parametrize("port", ["22", "8000", "8080"])
def test_exposed_admin_ports_are_critical(tmp_path, port):
    lines = []
    for line in SAMPLE.split("\n"):
        if line.startswith(f"| {port} |"):
            line = line.replace("| No |", "| Sí |")
        lines.append(line)
    assert any("expuesto a Internet" in m for m in _critical(_report(tmp_path, "\n".join(lines))))


def test_missing_pcie_overlay_is_critical(tmp_path):
    text = SAMPLE.replace("dtoverlay=pcie-32bit-dma-pi5\n", "")
    assert any("pcie-32bit-dma-pi5" in m for m in _critical(_report(tmp_path, text)))


def test_unapproved_upstream_reference_is_critical(tmp_path):
    text = SAMPLE.replace("| NRD v1 (1.0, Aprobado)", "| la guía")
    assert any("NRD" in m for m in _critical(_report(tmp_path, text)))


def test_no_backup_mechanism_is_critical(tmp_path):
    text = SAMPLE.replace("restic", "nada").replace("Backup diario de AIO", "copia")
    text = text.replace("| Backup |", "| Copia |")
    assert any("backup" in m for m in _critical(_report(tmp_path, text)))


def test_missing_deletion_threshold_warns(tmp_path):
    text = SAMPLE.replace(
        "| Umbral de borrados | No sincronizar si hay más de 50 borrados; aviso por correo |\n", ""
    )
    assert any("umbral" in m for m in _warning(_report(tmp_path, text)))


def test_adr_without_requirement_warns(tmp_path):
    text = SAMPLE.replace("| Sin puertos abiertos | NRD §7 |", "| Sin puertos abiertos | |")
    assert any("ADR-005 sin requisito" in m for m in _warning(_report(tmp_path, text)))
