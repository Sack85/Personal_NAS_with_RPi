from __future__ import annotations

import json

import pytest
from conftest import SHARED, load_module, run_hook

guard = load_module(SHARED / "hooks" / "ssh_guard.py")


@pytest.mark.parametrize(
    "command",
    [
        "ssh nas lsblk -o NAME,SIZE,MODEL,SERIAL",
        "ssh nas 'sudo smartctl -a /dev/sda'",
        "ssh nas sudo lspci -vv -d 197b: | grep LnkSta",
        "ssh nas 'vcgencmd measure_temp && vcgencmd get_throttled'",
        "ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-1.conf status'",
        "ssh nas 'sudo tune2fs -l /dev/sdb1 | grep \"Reserved block count\"'",
        "ssh nas systemctl status openmediavault-engined",
        "ssh nas 'apt list --upgradable'",
        "ssh nas 'sudo hdparm -C /dev/sdb'",
        "ssh -p 22 nas docker ps",
        "ssh nas cat /boot/firmware/config.txt",
    ],
)
def test_reads_are_allowed(command):
    assert guard.classify(command)[0] == "allow"


@pytest.mark.parametrize(
    "command",
    [
        "ssh nas 'sudo apt update && sudo apt full-upgrade -y'",
        "ssh nas sudo reboot",
        "ssh nas 'sudo systemctl enable --now hd-idle'",
        "ssh nas 'sudo snapraid -c /etc/snapraid/x.conf sync'",
        "ssh nas 'cd /srv/compose && docker compose up -d'",
        "ssh nas 'sudo smartctl -t long /dev/sdb'",
        "ssh nas",
        "ssh nas sudo nano /etc/default/hd-idle",
        "scp state/config/hd-idle nas:/tmp/hd-idle",
        "ssh nas 'sudo mount /dev/disk/by-label/backup /mnt/backup'",
    ],
)
def test_state_changes_ask(command):
    assert guard.classify(command)[0] == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "ssh nas sudo mkfs.ext4 /dev/sda1",
        "ssh nas 'sudo wipefs -a /dev/sdc'",
        "ssh nas 'sudo parted -s /dev/sdc mklabel gpt'",
        "ssh nas 'sudo tune2fs -m 0 /dev/sdb1'",
        "ssh nas 'sudo snapraid -c x.conf -d d1 -l fix.log fix'",
        "ssh nas 'sudo restic -r /mnt/backup/restic forget --keep-monthly 12 --prune'",
        "ssh nas 'sudo rm -rf /srv/mergerfs/pool/Fotos'",
        "ssh nas 'sudo dd if=/dev/zero of=/dev/sdb bs=1M'",
        "ssh nas 'sudo rpi-eeprom-config --edit'",
        "ssh nas 'sudo bash -c \"mkfs.ext4 /dev/sdb1\"'",
        "ssh nas 'lsblk && sudo wipefs -a /dev/sdb'",
        "sudo mkfs.ext4 /dev/sdb1",
        "echo x > /dev/sda",
        "ssh nas sudo bash <<'EOF'\nlsblk\nwipefs -a /dev/sdb\nEOF",
    ],
)
def test_destructive_is_denied(command):
    assert guard.classify(command)[0] == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "uv run pytest",
        "rm -rf .pytest_cache",
        "grep -rn mkfs outputs/",
        "git commit -m \"$(cat <<'EOF'\nRunbook: mkfs.ext4 y wipefs -a\nEOF\n)\"",
        'git commit -m "documenta snapraid fix; restic forget"',
        "fdisk -l",
    ],
)
def test_local_commands_are_ignored(command):
    assert guard.classify(command)[0] is None


def test_hook_emits_permission_decision():
    result = run_hook(
        SHARED / "hooks" / "ssh_guard.py",
        {"tool_name": "Bash", "tool_input": {"command": "ssh nas sudo wipefs -a /dev/sdb"}},
    )
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert result.returncode == 0
    assert out["permissionDecision"] == "deny"
    assert "usuario" in out["permissionDecisionReason"]


def test_hook_silent_for_local_commands():
    result = run_hook(SHARED / "hooks" / "ssh_guard.py", {"tool_input": {"command": "ls -la"}})
    assert result.returncode == 0 and result.stdout == ""
