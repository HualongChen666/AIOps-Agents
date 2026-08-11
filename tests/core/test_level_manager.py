# -*- coding: utf-8 -*-
"""Tests for core/logging/level/level_manager.py."""

import pytest

from core.logging.level.level_manager import (
    LogLevel,
    LogLevelManager,
    get_level_manager,
    get_log_level,
    set_log_level,
)


def test_log_level_enum():
    assert LogLevel.from_string("debug") == LogLevel.DEBUG
    assert LogLevel.from_int(20) == LogLevel.INFO
    assert LogLevel.WARNING.to_string() == "WARNING"


def test_log_level_manager():
    mgr = LogLevelManager()
    assert mgr.get_default_level() == LogLevel.INFO
    mgr.set_default_level(LogLevel.DEBUG)
    assert mgr.get_default_level() == LogLevel.DEBUG

    mgr.set_module_level("mod", LogLevel.ERROR)
    assert mgr.get_module_level("mod") == LogLevel.ERROR
    assert mgr.get_effective_level("mod") == LogLevel.ERROR
    mgr.remove_module_level("mod")
    assert mgr.get_effective_level("mod") == LogLevel.DEBUG

    mgr.set_level_from_string("warning")
    assert mgr.get_default_level() == LogLevel.WARNING


def test_global_get_set():
    mgr = get_level_manager()
    assert isinstance(mgr, LogLevelManager)
    set_log_level(LogLevel.CRITICAL)
    assert get_log_level() == LogLevel.CRITICAL


def test_invalid_log_level():
    with pytest.raises(ValueError):
        LogLevel.from_string("invalid")
