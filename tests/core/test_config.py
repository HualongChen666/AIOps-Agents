# -*- coding: utf-8 -*-
"""Tests for the top-level config module helpers."""

import os
from pathlib import Path

import pytest

from config import (
    _safe_bool,
    _safe_float,
    _safe_int,
    disable_config_hot_reload,
    enable_config_hot_reload,
    generate_config_documentation,
    is_config_hot_reload_enabled,
    save_config_documentation,
    validate_config,
)


@pytest.fixture(autouse=True)
def _cleanup_test_env():
    """Remove any test-specific environment variables after each test."""
    keys = set(os.environ.keys())
    yield
    for key in list(os.environ.keys()):
        if key not in keys:
            os.environ.pop(key, None)


def test_safe_bool_true_values():
    for value in ("true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"):
        os.environ["TEST_BOOL"] = value
        assert _safe_bool("TEST_BOOL") is True


def test_safe_bool_false_values():
    for value in ("false", "False", "FALSE", "0", "no", "No", "off", "OFF"):
        os.environ["TEST_BOOL"] = value
        assert _safe_bool("TEST_BOOL") is False


def test_safe_bool_defaults():
    assert _safe_bool("NOT_SET_BOOL", default=True) is True
    assert _safe_bool("NOT_SET_BOOL", default=False) is False
    os.environ["NOT_SET_BOOL"] = "invalid"
    assert _safe_bool("NOT_SET_BOOL", default=True) is True


def test_safe_int_parsing_and_bounds():
    os.environ["TEST_INT"] = "42"
    assert _safe_int("TEST_INT") == 42

    os.environ["TEST_INT"] = "-5"
    assert _safe_int("TEST_INT", min_val=0) == 0

    os.environ["TEST_INT"] = "150"
    assert _safe_int("TEST_INT", max_val=100) == 100

    os.environ["TEST_INT"] = "not-a-number"
    assert _safe_int("TEST_INT", default=7) == 7


def test_safe_float_parsing_and_bounds():
    os.environ["TEST_FLOAT"] = "3.14"
    assert _safe_float("TEST_FLOAT") == pytest.approx(3.14)

    os.environ["TEST_FLOAT"] = "-1.0"
    assert _safe_float("TEST_FLOAT", min_val=0.0) == 0.0

    os.environ["TEST_FLOAT"] = "1e9"
    assert _safe_float("TEST_FLOAT", max_val=100.0) == 100.0

    os.environ["TEST_FLOAT"] = "invalid"
    assert _safe_float("TEST_FLOAT", default=2.5) == pytest.approx(2.5)


def test_validate_config_returns_result_dict():
    result = validate_config()
    assert isinstance(result, dict)
    assert "is_valid" in result
    assert "errors" in result
    assert "warnings" in result
    assert "info" in result
    assert isinstance(result["is_valid"], bool)


def test_generate_config_documentation():
    doc = generate_config_documentation()
    assert isinstance(doc, str)
    assert doc.startswith("# AIOps Agent Configuration Documentation")
    assert "## Table of Contents" in doc


def test_save_config_documentation(tmp_path: Path):
    output = tmp_path / "config_doc.md"
    save_config_documentation(str(output))
    assert output.exists()
    assert "# AIOps Agent Configuration Documentation" in output.read_text(encoding="utf-8")


def test_config_hot_reload_lifecycle():
    """Hot reload functions are safe to call regardless of watchdog availability."""
    disable_config_hot_reload()
    assert is_config_hot_reload_enabled() is False

    # enable_config_hot_reload returns early if watchdog is missing or disabled.
    enable_config_hot_reload()
    # The observer may or may not have started; the function should not raise.
    assert is_config_hot_reload_enabled() is False

    disable_config_hot_reload()
    assert is_config_hot_reload_enabled() is False
