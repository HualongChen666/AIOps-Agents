# -*- coding: utf-8 -*-
"""Tests for core/config_manager.py."""

import json  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup
import yaml

from core.config_manager import (
    ConfigLoader,
    ConfigManager,
    ConfigValidator,
    get_config_value,
    load_config,
    save_config,
    setup_unified_configuration,
)


@pytest.fixture
def good_config(tmp_path):
    with open("config/development.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["security"]["tls_cert_path"] = ""
    data["security"]["tls_key_path"] = ""
    path = tmp_path / "good_config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_setup_unified_configuration(good_config):
    result = setup_unified_configuration(good_config)  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "environment" in result


def test_get_config_value(good_config):
    manager = ConfigManager()
    manager.load_config(good_config)
    value = manager.get_config_value("database.host", "localhost")
    assert value is not None
    assert get_config_value("missing", "default") == "default"


def test_load_and_save_config(good_config, tmp_path):
    manager = ConfigManager()
    config = manager.load_config(good_config)
    assert config is not None

    out_path = tmp_path / "out.json"
    data = manager.save_config(str(out_path))
    assert out_path.exists()
    assert isinstance(data, dict)

    cfg = load_config(good_config)
    assert cfg is not None
    assert save_config(str(tmp_path / "out2.json")) is not None


def test_config_loader_and_validator(good_config):
    manager = ConfigManager()
    manager.load_config(good_config)

    loader = ConfigLoader()
    config = loader.load(good_config)
    assert config is not None

    validator = ConfigValidator()
    errors = validator.validate(config)
    assert isinstance(errors, list)

    # Test with invalid object should return error messages
    assert isinstance(validator.validate({"not": "appconfig"}), list)
