# -*- coding: utf-8 -*-
"""Compatibility shim for imports expecting `core.config`.

The main configuration resides in the project root `config.py`.  Some legacy
modules (e.g., `api/k8s_router.py`) still import `core.config`.  To avoid
modifying many import statements we provide a thin wrapper that re‑exports all
symbols from the top‑level configuration module.
"""

import os
import sys

from config import *  # re‑export everything  # noqa: F401, F403

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
