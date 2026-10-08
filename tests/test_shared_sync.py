from __future__ import annotations

from sync_shared import targets


def test_plugin_copies_match_shared():
    stale = [
        str(dst)
        for src, dst in targets()
        if not dst.exists() or dst.read_bytes() != src.read_bytes()
    ]
    assert not stale, f"Ejecuta `uv run python tools/sync_shared.py`: {stale}"
