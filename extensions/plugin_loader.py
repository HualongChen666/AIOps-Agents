# -*- coding: utf-8 -*-
"""Plugin discovery and loader for extensions/addons.

Walks the ``extensions/addons/`` tree and attempts to import every ``.py``
file as a plugin module.  Directory names containing hyphens are sanitized to
underscores for the generated module name.  Multiple loading passes are made so
that intra-package relative imports (``from . import x``) can resolve as
siblings are successfully loaded.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

ROOT = Path(__file__).with_name("addons").resolve()
PREFIX = "ext_addons"


def _sanitize(name: str) -> str:
    """Replace characters that are illegal in a Python identifier."""
    return name.replace("-", "_").replace(".", "_")


def _module_name(py_path: Path) -> str:
    rel = py_path.relative_to(ROOT)
    parts = tuple(_sanitize(p) for p in rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return f"{PREFIX}.{'.'.join(parts)}"


def _parent_package(name: str) -> str | None:
    if "." not in name:
        return None
    return name.rsplit(".", 1)[0]


def _load_one(py_path: Path, name: str) -> Tuple[ModuleType, bool, str]:
    """Load a single file as a module."""
    spec = importlib.util.spec_from_file_location(name, str(py_path))
    if spec is None or spec.loader is None:
        return None, False, "could not create spec"
    module = importlib.util.module_from_spec(spec)
    module.__addon_file__ = str(py_path)  # type: ignore[attr-defined]
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        return module, True, ""
    except Exception as exc:
        logger.debug(f"Failed to load addon {name}: {exc}")
        return module, False, f"{type(exc).__name__}: {exc}"


def load_all_addons(max_passes: int = 5) -> Dict[str, List[Dict[str, str]]]:
    """Attempt to load every ``.py`` under ``extensions/addons/``.

    Returns a summary dict with ``loaded``, ``failed`` and ``total`` counts.
    """
    py_files = sorted(p for p in ROOT.rglob("*.py") if p.is_file())
    names = [_module_name(p) for p in py_files]
    mapping = dict(zip(names, py_files))
    loaded: set[str] = set()
    failed: dict[str, str] = {}

    for attempt in range(max_passes):
        made_progress = False
        for name in names:
            if name in loaded or name in failed:
                continue
            py_path = mapping[name]
            _, ok, err = _load_one(py_path, name)
            if ok:
                loaded.add(name)
                made_progress = True
            else:
                # Only finalise failure on last pass; otherwise retry in case
                # a missing relative import becomes available.
                if attempt == max_passes - 1:
                    failed[name] = err
        if not made_progress:
            break

    # If any module ended up in sys.modules but failed, keep the last error.
    for name in list(mapping):
        if name not in loaded and name not in failed:
            failed[name] = "unknown"

    return {
        "loaded": sorted(loaded),
        "failed": [{"name": n, "error": e} for n, e in sorted(failed.items())],
        "total": len(names),
    }


def list_addons() -> List[str]:
    """Return all discovered addon file paths relative to ``extensions/addons/``."""
    return sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*.py") if p.is_file())


def get_addon(name: str) -> ModuleType | None:
    """Fetch an already-loaded addon module by its generated name."""
    return sys.modules.get(name)
