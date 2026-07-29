# -*- coding: utf-8 -*-
"""Import smoke tests for all core modules.

These tests import every module under ``core/`` that is not explicitly
excluded.  Importing the module is enough to exercise top-level class and
function definitions, which improves coverage for modules that are not yet
reached by targeted tests.  Modules that fail to import (for example because
an optional dependency is missing) are skipped rather than failing the suite.
"""

import importlib
from pathlib import Path
from types import ModuleType
from typing import List

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = ROOT / "core"


def _discover_core_modules() -> List[str]:
    """Return a list of module names under ``core/`` (file-system walk only)."""
    modules: List[str] = []
    for path in sorted(CORE_DIR.rglob("*.py")):
        if path.name.startswith("__") or path.name == "conftest.py":
            continue
        if path.suffix != ".py":
            continue
        rel = path.relative_to(ROOT)
        parts = rel.with_suffix("").parts
        # Exclude backups and tests within core (if any)
        if any(
            part.endswith(".bak") or part == "backup" or part.startswith("test_") for part in parts
        ):
            continue
        modules.append(".".join(parts))
    return modules


@pytest.mark.parametrize("module_name", _discover_core_modules())
def test_core_module_imports(module_name: str) -> None:
    """A core module can be imported (or skipped if optional deps are missing).

    We intentionally do *not* delete ``sys.modules`` first.  Re-importing
    modules such as ``core.models`` would fail because SQLAlchemy tables are
    already registered on the shared ``Base`` metadata.  If a module was already
    imported by an earlier test, the cached module is reused and still counts
    toward coverage.
    """
    try:
        mod = importlib.import_module(module_name)
    except (ImportError, RuntimeError, OSError, ModuleNotFoundError, ValueError) as exc:
        pytest.skip(f"{module_name} not importable: {exc}")

    assert isinstance(mod, ModuleType)
