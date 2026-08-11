# -*- coding: utf-8 -*-
"""Tests for core/config_validation.py."""

import json

import pytest
import yaml

from core import config_validation
from core.config_validation import (
    ConfigHealthChecker,
    ConfigValidator,
    ValidationSeverity,
    setup_config_validation,
)
from core.environment_config import EnvironmentConfigManager


@pytest.fixture
def good_config(tmp_path):
    with open("config/development.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["security"]["tls_cert_path"] = ""
    data["security"]["tls_key_path"] = ""
    path = tmp_path / "good_config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def env_manager(good_config):
    mgr = EnvironmentConfigManager(config_dir=str(good_config.parent))
    mgr.config_file = good_config
    return mgr


def test_config_validator(env_manager):
    config = env_manager.load_environment_config()
    validator = ConfigValidator()
    results = validator.validate_config(config)
    assert isinstance(results, list)
    assert all(hasattr(r, "is_valid") for r in results)


def test_config_health_checker(env_manager):
    config = env_manager.load_environment_config()
    checker = ConfigHealthChecker()
    health = checker.check_config_health(config)
    assert "healthy" in health
    assert "validation_results" in health


def test_setup_config_validation(env_manager, monkeypatch):
    monkeypatch.setattr(config_validation, "environment_config_manager", env_manager)
    result = setup_config_validation()
    assert result["status"] in ("success", "error")


def test_validation_severity():
    assert ValidationSeverity.ERROR.value == "error"
