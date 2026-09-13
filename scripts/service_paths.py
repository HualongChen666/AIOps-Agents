# -*- coding: utf-8 -*-
"""Resolve phase-4/5/6 addon service names to their REAL locations.

The phase-4/5/6 verification/format/benchmark scripts used to hard-code
``services/<name>`` and ``tests/services/<name>``. Those directories do not
exist — the services live under ``extensions/addons/<category>/<name>`` (and,
where present, their tests under ``tests/addons`` / ``tests/extensions/addons``).
This module is the single place that knows the mapping, so every script resolves
the same real path.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ADDONS_ROOT = PROJECT_ROOT / "extensions" / "addons"
_TESTS_ROOTS = (
    PROJECT_ROOT / "tests" / "addons",
    PROJECT_ROOT / "tests" / "extensions" / "addons",
    PROJECT_ROOT / "tests" / "services",
)


def service_dir(name: str) -> Path | None:
    """Return the on-disk directory of an addon service, or None if missing."""
    if not ADDONS_ROOT.is_dir():
        return None
    for category in sorted(p for p in ADDONS_ROOT.iterdir() if p.is_dir()):
        candidate = category / name
        if candidate.is_dir():
            return candidate
    return None


def service_relpath(name: str) -> str:
    """Repository-relative path of an addon service (for coverage/black/isort)."""
    directory = service_dir(name)
    if directory is None:
        raise FileNotFoundError(f"addon service not found under {ADDONS_ROOT}: {name}")
    return str(directory.relative_to(PROJECT_ROOT))


def service_module(name: str) -> str:
    """Dotted import path of an addon service package."""
    directory = service_dir(name)
    if directory is None:
        raise ModuleNotFoundError(f"addon service not found under {ADDONS_ROOT}: {name}")
    return ".".join(directory.relative_to(PROJECT_ROOT).parts)


def tests_dir(name: str) -> Path | None:
    """Return the test directory for an addon service, or None if it has none."""
    for root in _TESTS_ROOTS:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


def tests_relpath(name: str) -> str | None:
    """Repository-relative test path for an addon service, or None."""
    directory = tests_dir(name)
    return str(directory.relative_to(PROJECT_ROOT)) if directory is not None else None
