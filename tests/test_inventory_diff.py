from __future__ import annotations

import subprocess
import sys

import inventory_diff as inv
from conftest import ROOT

EXAMPLES = ROOT / "maintainer-plugin" / "skills" / "inventory" / "examples"
NOV = inv.load(EXAMPLES / "inventory-2026-11-01.yaml")
DEC = inv.load(EXAMPLES / "inventory-2026-12-01.yaml")


def _messages(findings, level):
    return [f.message for f in findings if f.level == level]


def test_single_healthy_inventory_has_no_alerts():
    assert not [f for f in inv.compare(None, NOV) if f.level != "INFO"]


def test_container_version_change_is_reported():
    assert any(
        "nextcloud-aio-mastercontainer" in m for m in _messages(inv.compare(NOV, DEC), "INFO")
    )


def test_pending_kernel_is_warning():
    assert any("linux-image" in m for m in _messages(inv.compare(NOV, DEC), "WARNING"))


def test_growing_failure_attributes_are_critical():
    critical = _messages(inv.compare(NOV, DEC), "CRITICAL")
    assert any("atributo 5 crece 0 → 8" in m for m in critical)
    assert any("atributo 197 crece 0 → 2" in m for m in critical)


def test_load_cycles_per_day_warning():
    assert any("193 sube" in m for m in _messages(inv.compare(NOV, DEC), "WARNING"))


def test_temperature_thresholds():
    assert any("41 °C" in m for m in _messages(inv.compare(NOV, DEC), "WARNING"))
    hot = {
        **DEC,
        "salud": {**DEC["salud"], "discos": [{**DEC["salud"]["discos"][0], "temp_c": 47}]},
    }
    assert any("47 °C" in m for m in _messages(inv.compare(None, hot), "CRITICAL"))


def test_pcie_link_downgrade_is_critical():
    slow = {**NOV, "salud": {**NOV["salud"], "pcie_enlace": "5GT/s"}}
    assert any("5GT/s" in m for m in _messages(inv.compare(None, slow), "CRITICAL"))


def test_cli_exit_codes():
    cmd = [sys.executable, str(ROOT / "tools" / "inventory_diff.py")]
    ok = subprocess.run(cmd + [str(EXAMPLES / "inventory-2026-11-01.yaml")], capture_output=True)
    bad = subprocess.run(
        cmd
        + [
            str(EXAMPLES / "inventory-2026-11-01.yaml"),
            str(EXAMPLES / "inventory-2026-12-01.yaml"),
        ],
        capture_output=True,
    )
    assert ok.returncode == 0
    assert bad.returncode == 1
