from __future__ import annotations

from conftest import ROOT, load_module

PLUGIN = ROOT / "storage-plugin"
dcp = load_module(PLUGIN / "skills" / "validate-dcp" / "scripts" / "validate_dcp.py")
EXAMPLES = PLUGIN / "skills" / "create-dcp" / "examples"
FAILURE = (EXAMPLES / "sample-dcp-fallo-datos.md").read_text(encoding="utf-8")
UPGRADE = (EXAMPLES / "sample-dcp-ampliacion.md").read_text(encoding="utf-8")


def _report(tmp_path, text):
    path = tmp_path / "DCP-2027-03-02-d2.md"
    path.write_text(text, encoding="utf-8")
    return dcp.validate(path)


def _critical(report):
    return [r.message for r in report.results if r.level.value == "CRITICAL"]


def _warning(report):
    return [r.message for r in report.results if r.level.value == "WARNING"]


def test_examples_pass(tmp_path):
    for text in (FAILURE, UPGRADE):
        report = _report(tmp_path, text)
        assert report.passed, [r.message for r in report.results]


def test_sync_before_fix_is_critical(tmp_path):
    early_sync = (
        "Comando:\n\n```bash\nssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; "
        "sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync'\n```"
    )
    text = FAILURE.replace(
        "Comando:\n\n```bash\nssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; "
        "sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status | tail -8'\n```",
        early_sync,
    )
    assert any("antes del fix" in m for m in _critical(_report(tmp_path, text)))


def test_data_failure_without_fix_is_critical(tmp_path):
    text = FAILURE.replace("-d d2 -l fix.log fix", "status")
    assert any("sin `snapraid -d dN" in m for m in _critical(_report(tmp_path, text)))


def test_bigger_new_disk_as_data_is_critical(tmp_path):
    reserved = "ext4 (0 % reservado) | No | No |\n"
    text = UPGRADE.replace(
        f"| Paridad | WD Red Plus | 2 TB | {reserved}| D1 | WD Blue | 1 TB |",
        f"| Paridad | WD Blue | 1 TB | {reserved}| D1 | WD Red Plus | 2 TB |",
    )
    assert any("menor que el mayor disco" in m for m in _critical(_report(tmp_path, text)))


def test_sync_not_disabled_is_critical(tmp_path):
    text = FAILURE.replace(
        "- [ ] Sync programado de SnapRAID desactivado antes de cualquier otro paso (paso 1)\n", ""
    )
    assert any("sync programado" in m for m in _critical(_report(tmp_path, text)))


def test_no_backup_precondition_is_critical(tmp_path):
    text = FAILURE.replace(
        "- [ ] Fecha del último backup restic anotada (2027-02-05) "
        "por si la reconstrucción falla\n",
        "",
    )
    assert any("backup" in m for m in _critical(_report(tmp_path, text)))


def test_fix_run_by_agent_is_critical(tmp_path):
    start = FAILURE.index("### Paso 7")
    end = FAILURE.index("### Paso 8")
    step = FAILURE[start:end].replace("| **Ejecuta** | Usuario |", "| **Ejecuta** | Agente |")
    text = FAILURE[:start] + step + FAILURE[end:]
    assert any("ejecutado por el agente" in m for m in _critical(_report(tmp_path, text)))


def test_parity_failure_without_sync_is_critical(tmp_path):
    text = UPGRADE.replace(
        "| **Escenario** | Sustitución preventiva |", "| **Escenario** | Fallo de paridad |"
    )
    text = text.replace(" sync'", " status'")
    assert any("sin sync" in m for m in _critical(_report(tmp_path, text)))


def test_invalid_scenario_is_critical(tmp_path):
    text = FAILURE.replace(
        "| **Escenario** | Fallo de disco de datos |", "| **Escenario** | Cambio |"
    )
    assert any("Escenario 'Cambio'" in m for m in _critical(_report(tmp_path, text)))


def test_missing_design_change_warns(tmp_path):
    text = FAILURE.replace("- hd-idle: sin cambios (los SSD no se paran).\n", "")
    assert any("hd-idle" in m for m in _warning(_report(tmp_path, text)))


def test_missing_check_after_fix_warns(tmp_path):
    text = FAILURE.replace("-d d2 -a check", "-d d2 -a list")
    assert any("check" in m for m in _warning(_report(tmp_path, text)))
