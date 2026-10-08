from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(SHARED))


def load_module(path: Path) -> ModuleType:
    """Importa un script por ruta (con su carpeta en sys.path para doc_validation)."""
    sys.path.insert(0, str(path.parent))
    try:
        name = f"_test_{path.parent.parent.name}_{path.stem}".replace("-", "_")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(path.parent))


def run_hook(script: Path, payload: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )
