from __future__ import annotations

from conftest import ROOT, load_module

PLUGIN = ROOT / "maintainer-plugin"
upd = load_module(PLUGIN / "skills" / "validate-upd" / "scripts" / "validate_upd.py")
SAMPLE = (PLUGIN / "skills" / "create-upd" / "examples" / "sample-upd.md").read_text(
    encoding="utf-8"
)


def _report(tmp_path, text):
    path = tmp_path / "UPD-2027-01-05-enero.md"
    path.write_text(text, encoding="utf-8")
    return upd.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def _warning(report):
    return [r.message for r in report.results if r.level.value == "WARNING"]


def test_sample_passes(tmp_path):
    report = _report(tmp_path, SAMPLE)
    assert report.passed, [r.message for r in report.results]


def test_kernel_change_without_disk_checks_is_critical(tmp_path):
    text = SAMPLE.replace(
        '| Enlace PCIe | `ssh nas "sudo lspci -vv -d 197b: \\| grep LnkSta"` | Speed 8GT/s |\n', ""
    ).replace("| Discos visibles | `ssh nas lsblk -d -o NAME,SIZE,MODEL` | XG5 + tres SATA |\n", "")
    assert any("enlace PCIe" in m for m in _critical(_report(tmp_path, text)))


def test_non_kernel_update_does_not_need_pcie_check(tmp_path):
    text = SAMPLE.replace(
        "| linux-image-rpi-2712 | 6.12.47 | 6.12.55 |", "| hd-idle | 1.21 | 1.22 |"
    )
    text = text.replace("Speed 8GT/s |", "ok |").replace("LnkSta", "x")
    assert not any("enlace PCIe" in m for m in _critical(_report(tmp_path, text)))


def test_missing_inventory_is_critical(tmp_path):
    text = SAMPLE.replace(
        "| **Inventario** | state/inventory/2027-01-05.yaml |", "| **Inventario** | — |"
    )
    assert any("inventario" in m for m in _critical(_report(tmp_path, text)))


def test_missing_backup_precondition_is_critical(tmp_path):
    start = SAMPLE.index("## Precondiciones")
    end = SAMPLE.index("## Pasos")
    text = SAMPLE[:start] + "## Precondiciones\n\n- [ ] SAI en OL\n\n" + SAMPLE[end:]
    assert any("snapraid" in m for m in _critical(_report(tmp_path, text)))


def test_empty_rollback_is_critical(tmp_path):
    start = SAMPLE.index("## Vuelta atrás")
    end = SAMPLE.index("## Historial de versiones")
    text = SAMPLE[:start] + "## Vuelta atrás\n\n" + SAMPLE[end:]
    assert any("Sin vuelta atrás" in m for m in _critical(_report(tmp_path, text)))


def test_destructive_step_rules_apply(tmp_path):
    text = SAMPLE.replace("ssh nas sudo reboot", "ssh nas sudo wipefs -a /dev/sdb")
    assert any("Comando destructivo" in m for m in _critical(_report(tmp_path, text)))


def test_change_without_source_warns(tmp_path):
    text = SAMPLE.replace("| Actualización automática de AIO |", "| |")
    assert any("sin fuente" in m for m in _warning(_report(tmp_path, text)))
