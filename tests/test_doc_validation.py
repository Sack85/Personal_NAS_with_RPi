from __future__ import annotations

import pytest
from conftest import SHARED, load_module, run_hook

dv = load_module(SHARED / "doc_validation.py")

DOC = """# Documento de prueba

| Campo | Valor |
|---|---|
| **Documento** | NRD |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Última modificación** | 2026-10-08 |
| **Autor** | Requirements Agent |
| **Entregable previo** | NRD v1 (1.0, Aprobado) |

## 1. Contexto

Texto.

## 2. Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-08 | Agente | Creación |
"""


def test_parse_sections_ignores_code_blocks():
    sections = dv.parse_sections("## A\n```\n## no\n```\n## B\nx")
    assert list(sections) == ["A", "B"]


def test_find_section_ignores_numbering():
    assert dv.find_section(dv.parse_sections(DOC), "Contexto") == "Texto."


def test_metadata_ok():
    assert dv.check_metadata(DOC) == []


@pytest.mark.parametrize(
    "old,new",
    [("| **Estado** | Borrador |", "| **Estado** | Listo |"), ("| **Versión** | 1.0 |", "")],
)
def test_metadata_errors(old, new):
    results = dv.check_metadata(DOC.replace(old, new))
    assert results and all(r.level == dv.ValidationLevel.CRITICAL for r in results)


def test_required_sections():
    sections = dv.parse_sections(DOC)
    assert dv.check_required_sections(sections, ["Contexto", "Historial de versiones"]) == []
    assert len(dv.check_required_sections(sections, ["Red"])) == 1


def test_find_table_by_columns():
    text = (
        "| Carpeta | Volumen (GB) |\n|---|---|\n| Fotos | 300 |\n\n| A | B |\n|---|---|\n| 1 | 2 |"
    )
    rows = dv.find_table(text, "carpeta", "volumen")
    assert rows == [{"carpeta": "Fotos", "volumen (gb)": "300"}]
    assert dv.cell(rows[0], "volumen") == "300"
    assert dv.find_table(text, "inexistente") is None


def test_upstream_reference():
    assert dv.check_upstream_reference(DOC, "nrd") == []
    assert dv.check_upstream_reference(DOC, "hld")


def test_empty_version_history_is_critical():
    doc = DOC.split("| 1.0 | 2026")[0]
    assert dv.check_version_history(dv.parse_sections(doc))


def test_vague_language_is_warning():
    results = dv.check_vague_language("Reinicia si es necesario, etc.")
    assert results[0].level == dv.ValidationLevel.WARNING


def test_vague_language_ignores_code():
    assert dv.check_vague_language("```\n# etc.\n```") == []


@pytest.mark.parametrize(
    "line",
    [
        "password: S3cr3tValue",
        "Contraseña = hunter2hunter2",
        "frase de acceso: correct-horse-battery",
        "contraseña de aplicación: abcd efgh ijkl mnop",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "authkey tskey-auth-abcdef123456",
        "IP pública del router 81.56.120.33",
    ],
)
def test_secrets_detected(line):
    assert dv.find_secrets(line)


@pytest.mark.parametrize(
    "line",
    [
        "Usuario admin, contraseña openmediavault (la de fábrica; cámbiala)",
        "password: <en el gestor de contraseñas>",
        "contraseña: ${NC_PASSWORD}",
        "| Contraseña | La contraseña de aplicación |",
        "Reserva DHCP 192.168.1.200, DNS 1.1.1.1, Tailscale 100.101.102.103",
        "Ejemplo de documentación 203.0.113.10 y máscara 255.255.255.0",
        "Crea una contraseña de aplicación de 16 caracteres",
    ],
)
def test_no_false_positives(line):
    assert dv.find_secrets(line) == []


def test_secrets_only_cli(tmp_path):
    bad = tmp_path / "x.md"
    bad.write_text("token: ghp_abcdefghijklmnopqrstuvwx1234", encoding="utf-8")
    good = tmp_path / "y.md"
    good.write_text("nada", encoding="utf-8")
    import subprocess
    import sys

    cmd = [sys.executable, str(SHARED / "doc_validation.py"), "--secrets-only"]
    assert subprocess.run(cmd + [str(good)], capture_output=True).returncode == 0
    assert subprocess.run(cmd + [str(bad)], capture_output=True).returncode == 1


def test_secrets_guard_hook_blocks(tmp_path):
    target = tmp_path / "outputs" / "nrd" / "v1" / "NRD-2026-10-08-x.md"
    target.parent.mkdir(parents=True)
    target.write_text("password: S3cr3tValue", encoding="utf-8")
    payload = {"tool_input": {"file_path": str(target)}}
    result = run_hook(SHARED / "hooks" / "secrets_guard.py", payload)
    assert result.returncode == 2
    assert "GitHub" in result.stderr


def test_secrets_guard_ignores_other_paths(tmp_path):
    target = tmp_path / "notes.md"
    target.write_text("password: S3cr3tValue", encoding="utf-8")
    result = run_hook(
        SHARED / "hooks" / "secrets_guard.py", {"tool_input": {"file_path": str(target)}}
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "sudo wipefs -a /dev/sdX",
        "sudo mkfs.ext4 -L backup /dev/sdX1",
        "sudo parted -s /dev/sdX mklabel gpt mkpart backup ext4 0% 100%",
        "sudo tune2fs -m 0 /dev/sdX1",
        "sudo snapraid -c <conf> -d d1 -l fix.log fix",
        "sudo restic -r /mnt/backup/restic forget --keep-monthly 12 --prune",
    ],
)
def test_destructive_commands(command):
    assert dv.destructive_reason(command)


@pytest.mark.parametrize(
    "command",
    [
        "sudo tune2fs -l /dev/sdX1 | grep 'Reserved block count'",
        "lsblk -o NAME,SIZE,MODEL,SERIAL",
        "sudo smartctl -t long /dev/sdX",
        "sudo snapraid -c x.conf sync",
        "sudo parted -l",
    ],
)
def test_non_destructive_commands(command):
    assert dv.destructive_reason(command) is None
