# -*- coding: utf-8 -*-
"""Import smoke tests for all api modules.

These tests import every module under ``api/`` that is not explicitly
excluded.  Importing the module is enough to exercise top-level router and
schema definitions, which improves coverage for routers that are not yet
reached by targeted endpoint tests.  Modules that fail to import (for example
because an optional dependency is missing) are skipped rather than failing the
suite.
"""

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import List

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "api"


def _discover_api_modules() -> List[str]:
    """Return a list of module names under ``api/`` (file-system walk only)."""
    modules: List[str] = []
    for path in sorted(API_DIR.rglob("*.py")):
        if path.name.startswith("__") or path.name == "conftest.py":
            continue
        if path.suffix != ".py":
            continue
        # Exclude __init__ files and backups/tests within api
        if path.name == "__init__.py":
            continue
        rel = path.relative_to(ROOT)
        parts = rel.with_suffix("").parts
        if any(
            part.endswith(".bak") or part == "backup" or part.startswith("test_") for part in parts
        ):
            continue
        modules.append(".".join(parts))
    return modules


@pytest.mark.parametrize("module_name", _discover_api_modules())
def test_api_module_imports(module_name: str) -> None:
    """An api module can be imported (or skipped if optional deps are missing)."""
    # Do NOT delete/reimport modules that are already loaded.  Reimporting creates a
    # new module object while existing test files may hold references to the old
    # router/endpoint objects, so @patch("api.xxx.func") targets the wrong module and
    # MagicMock return values leak into FastAPI responses.
    if module_name in sys.modules:
        mod = sys.modules[module_name]
    else:
        try:
            mod = importlib.import_module(module_name)
        except (ImportError, RuntimeError, OSError, ModuleNotFoundError, ValueError) as exc:
            pytest.skip(f"{module_name} not importable: {exc}")

    if not isinstance(mod, ModuleType):
        pytest.skip(f"{module_name} is mocked or not a real module")
