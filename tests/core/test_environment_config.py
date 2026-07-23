# -*- coding: utf-8 -*-
"""测试 core/environment_config 的环境检测与配置加载"""

from unittest.mock import MagicMock

import pytest

from core import environment_config as ec
from core.unified_config import Environment


def _make_config_manager():
    fake_config = MagicMock()
    fake_config.security = MagicMock()
    fake_config.security.jwt_secret_key = "dev-secret-key-change-me"
    fake_config.security.tls_enabled = False

    class FakeConfigManager:
        def load_config(self, config_file=None):
            return fake_config

    return FakeConfigManager


@pytest.fixture
def patch_config_manager(monkeypatch):
    monkeypatch.setattr(ec, "ConfigManager", _make_config_manager())


class TestEnvironmentDetection:
    def test_detect_development(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ENVIRONMENT", "development")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.environment == Environment.DEVELOPMENT

    def test_detect_production(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.environment == Environment.PRODUCTION

    def test_detect_invalid_defaults_to_development(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ENVIRONMENT", "unknown")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.environment == Environment.DEVELOPMENT


class TestConfigFile:
    def test_get_config_file_for_environment(self, monkeypatch, tmp_path):
        config_file = tmp_path / "production.yaml"
        config_file.write_text("x: 1")
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.config_file == config_file

    def test_fallback_to_development(self, monkeypatch, tmp_path):
        dev_file = tmp_path / "development.yaml"
        dev_file.write_text("x: 1")
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.config_file == dev_file

    def test_no_config_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        assert manager.config_file is None


class TestLoadAndValidate:
    def test_load_environment_config(self, tmp_path, monkeypatch, patch_config_manager):
        (tmp_path / "development.yaml").write_text("app_name: test\nworkers: 2")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        config = manager.load_environment_config()
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is True
        assert config.workers == 1

    def test_list_available_environments(self, tmp_path):
        (tmp_path / "development.yaml").write_text("x: 1")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        result = manager.list_available_environments()
        assert result["development"] is True
        assert result["production"] is False

    def test_validate_no_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        result = manager.validate_environment_config()
        assert result["config_file_exists"] is False
        assert len(result["validation_errors"]) > 0

    def test_validate_production_invalid(self, tmp_path, monkeypatch, patch_config_manager):
        (tmp_path / "production.yaml").write_text("x: 1")
        monkeypatch.setenv("ENVIRONMENT", "production")
        manager = ec.EnvironmentConfigManager(config_dir=str(tmp_path))
        result = manager.validate_environment_config()
        assert result["valid"] is False
        assert any("Default JWT secret key" in e or "TLS" in e for e in result["validation_errors"])


class TestSetupEnvironment:
    def test_setup_environment_configuration(self, monkeypatch):
        class FakeManager:
            environment = Environment.DEVELOPMENT
            config_file = None

            def validate_environment_config(self):
                return {"valid": True}

            def load_environment_config(self):
                return {}

            def get_config_file_path(self):
                return None

        monkeypatch.setattr(ec, "environment_config_manager", FakeManager())
        monkeypatch.setattr(ec, "setup_unified_configuration", lambda config_file: {"status": "ok"})
        result = ec.setup_environment_configuration()
        assert result["status"] == "success"

    def test_setup_environment_configuration_error(self, monkeypatch):
        monkeypatch.setattr(
            ec.environment_config_manager,
            "validate_environment_config",
            MagicMock(side_effect=RuntimeError("boom")),
        )
        result = ec.setup_environment_configuration()
        assert result["status"] == "error"
