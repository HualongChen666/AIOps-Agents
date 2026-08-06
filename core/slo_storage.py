# -*- coding: utf-8 -*-
"""
core/slo_storage.py
===================

Persistence helpers for SLO rules. ``save_slos`` and ``load_slos``
serialize the in-memory rule store in ``core.slo_engine`` to
``data/slos.json``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import core.slo_engine as _slo_engine

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SLOS_FILE = _DATA_DIR / "slos.json"


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_slos() -> None:
    """Persist the current SLO store and id counter to disk."""
    _ensure_data_dir()
    data = {
        "counter": _slo_engine._slo_counter,
        "slos": {
            slo_id: asdict(rule)
            for slo_id, rule in _slo_engine._slo_store.items()
        },
    }
    with _SLOS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d SLO(s) to %s", len(_slo_engine._slo_store), _SLOS_FILE)


def load_slos() -> None:
    """Load SLOs from disk into the in-memory store."""
    if not _SLOS_FILE.exists():
        logger.debug("No SLO persistence file found at %s", _SLOS_FILE)
        return

    try:
        with _SLOS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load SLOs from %s: %s", _SLOS_FILE, exc)
        return

    _slo_engine._slo_store.clear()
    for rule_dict in data.get("slos", {}).values():
        rule = _slo_engine.SLORule(**rule_dict)
        _slo_engine._slo_store[rule.id] = rule
    _slo_engine._slo_counter = data.get("counter", 0)
    logger.info("Loaded %d SLO(s) from %s", len(_slo_engine._slo_store), _SLOS_FILE)
