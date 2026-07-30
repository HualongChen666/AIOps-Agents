# -*- coding: utf-8 -*-
"""Compatibility shim for imports expecting `core.config`.

The main configuration resides in the project root `config.py`.  Some legacy
modules (e.g., `api/k8s_router.py`) still import `core.config`.  To avoid
modifying many import statements we provide a thin wrapper that re‑exports all
symbols from the top‑level configuration module.
"""

import importlib.util
import os

# Explicitly load the top-level config.py to avoid namespace package conflicts
# with the config/ directory.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("config", os.path.join(_root, "config.py"))
if _spec is None or _spec.loader is None:
    raise ImportError("Failed to load top-level config.py")
_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config)  # type: ignore[union-attr]
for _name in dir(_config):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_config, _name)

# Expose common names to keep static linters happy
DOCKER_HOSTS = _config.DOCKER_HOSTS  # type: ignore[name-defined]
