# -*- coding: utf-8 -*-
"""Complementary tests for core.config_manager coverage."""

import pytest

from core.config_manager import (
    ConfigLoader,
    ConfigManager,
    ConfigValidator,
    get_config_value,
    load_config,
    save_config,
)
from core.config_models import Environment


@pytest.fixture(autouse=True)
def _default_env(monkeypatch):
    """Provide deterministic default env values so .env doesn't break tests."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("APP_NAME", "AIOps Agent")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("TLS_ENABLED", "false")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
    monkeypatch.setenv("CORS_ALLOW_HEADERS", "*")


class TestConfigManagerCoverage:
    """Targeted tests to raise core.config_manager coverage above 80%."""

    def test_detect_environment_invalid(self, monkeypatch):
        """Unknown environment values fall back to development."""
        monkeypatch.setenv("ENVIRONMENT", "not_a_real_env")
        manager = ConfigManager()
        assert manager._environment == Environment.DEVELOPMENT

    def test_load_config_missing_file(self, monkeypatch):
        """Loading a non-existent config file falls back to defaults."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        config = manager.load_config("/nonexistent/config.json")
        assert config is not None
        assert config.app_name == "AIOps Agent"
        assert manager._config_file.name == "config.json"

    def test_load_config_invalid_json_content(self, monkeypatch, tmp_path):
        """JSON files containing non-dict data are treated as empty."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        path = tmp_path / "bad.json"
        path.write_text("[]", encoding="utf-8")
        manager = ConfigManager()
        config = manager.load_config(str(path))
        assert config.app_name == "AIOps Agent"

    def test_load_config_unsupported_extension(self, monkeypatch, tmp_path):
        """Unsupported file extensions are ignored and defaults are used."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        path = tmp_path / "config.txt"
        path.write_text("app_name: Test", encoding="utf-8")
        manager = ConfigManager()
        config = manager.load_config(str(path))
        assert config.app_name == "AIOps Agent"

    def test_load_config_jwt_default(self, monkeypatch):
        """Missing JWT secret in development uses the default dev secret."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET_KEY", "")
        manager = ConfigManager()
        config = manager.load_config()
        assert config.security.jwt_secret_key == "dev-secret-key-change-me"

    def test_load_config_jwt_insecure(self, monkeypatch):
        """Insecure JWT secret values are allowed in development with a warning."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
        manager = ConfigManager()
        config = manager.load_config()
        assert config.security.jwt_secret_key == "dev-secret-key-change-me"

    def test_load_config_jwt_missing_production(self, monkeypatch):
        """Production requires JWT_SECRET_KEY."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "")
        manager = ConfigManager()
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
            manager.load_config()

    def test_load_config_jwt_insecure_production(self, monkeypatch):
        """Production rejects default/insecure JWT secrets."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
        manager = ConfigManager()
        with pytest.raises(ValueError, match="default/insecure value"):
            manager.load_config()

    def test_load_config_cors_override(self, monkeypatch):
        """Comma-separated CORS env variables override config values."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        monkeypatch.setenv("CORS_ORIGINS", "http://a,http://b")
        monkeypatch.setenv("CORS_ALLOW_METHODS", "GET,POST")
        monkeypatch.setenv("CORS_ALLOW_HEADERS", "X-Custom")
        manager = ConfigManager()
        config = manager.load_config()
        assert config.cors_origins == ["http://a", "http://b"]
        assert config.cors_allow_methods == ["GET", "POST"]
        assert config.cors_allow_headers == ["X-Custom"]

    def test_load_config_ai_api_key_fallback(self, monkeypatch):
        """AI_API_KEY is used as fallback when OPENAI_API_KEY is empty."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("AI_API_KEY", "fallback-key")
        manager = ConfigManager()
        config = manager.load_config()
        assert config.ai.api_key == "fallback-key"

    def test_validate_config_tls_production(self, monkeypatch):
        """Production with TLS enabled requires cert and key paths."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        monkeypatch.setenv("TLS_ENABLED", "true")
        manager = ConfigManager()
        with pytest.raises(ValueError, match="TLS_CERT_PATH and TLS_KEY_PATH"):
            manager.load_config()

    def test_update_config_from_dict(self, monkeypatch):
        """Updating config from a dict merges nested values."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        config = manager.load_config()
        updated = manager._update_config_from_dict(
            config,
            {"app_name": "Updated", "database": {"host": "db-host"}, "unknown": "x"},
        )
        assert updated.app_name == "Updated"
        assert updated.database.host == "db-host"

    def test_reload_config_with_file(self, monkeypatch, tmp_path):
        """Reloading from a previously loaded file re-reads the file."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        path = tmp_path / "config.json"
        path.write_text('{"app_name": "Reloaded"}', encoding="utf-8")
        manager = ConfigManager()
        manager.load_config(str(path))
        reloaded = manager.reload_config()
        assert reloaded.app_name == "Reloaded"

    def test_get_config_value(self, monkeypatch):
        """Dot-separated keys return nested values or defaults."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        assert manager.get_config_value("app_name") == "AIOps Agent"
        assert manager.get_config_value("database.host") == "localhost"
        assert manager.get_config_value("missing.key", "default") == "default"

    def test_set_config_value(self, monkeypatch):
        """Dot-separated keys set nested values."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        manager.set_config_value("app_name", "New")
        manager.set_config_value("database.host", "new-host")
        assert manager.get_config_value("app_name") == "New"
        assert manager.get_config_value("database.host") == "new-host"

    def test_save_config_json(self, monkeypatch, tmp_path):
        """Saving to JSON writes a file and returns success metadata."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        path = tmp_path / "config.json"
        result = manager.save_config(str(path))
        assert result["status"] == "success"
        assert path.exists()

    def test_save_config_yaml(self, monkeypatch, tmp_path):
        """Saving to YAML writes a file and returns success metadata."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        path = tmp_path / "config.yaml"
        result = manager.save_config(str(path))
        assert result["status"] == "success"
        assert path.exists()

    def test_save_config_unsupported_extension(self, monkeypatch, tmp_path):
        """Saving to an unsupported extension raises ValueError."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        with pytest.raises(ValueError, match="Unsupported config file extension"):
            manager.save_config(str(tmp_path / "config.txt"))


class TestConfigLoader:
    """Coverage for the convenience loader class."""

    def test_load_and_save(self, monkeypatch, tmp_path):
        """ConfigLoader delegates to the global config manager."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        loader = ConfigLoader()
        config = loader.load()
        assert config is not None
        result = loader.save(str(tmp_path / "config.json"))
        assert result["status"] == "success"


class TestConfigValidator:
    """Coverage for the public validator wrapper."""

    def test_validate_passes(self, monkeypatch):
        """Valid config returns an empty error list."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        manager = ConfigManager()
        manager.load_config()
        validator = ConfigValidator()
        assert validator.validate(manager.get_config()) == []

    def test_validate_fails(self):
        """Invalid config returns the validation error message."""
        validator = ConfigValidator()
        errors = validator.validate({"environment": "invalid"})
        assert len(errors) == 1


class TestGlobalFunctions:
    """Coverage for module-level helper functions."""

    def test_load_config_function(self, monkeypatch):
        """load_config() returns the global manager config."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        config = load_config()
        assert config is not None

    def test_save_config_function(self, monkeypatch, tmp_path):
        """save_config() writes via the global manager."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        load_config()
        path = tmp_path / "config.json"
        result = save_config(str(path))
        assert result["status"] == "success"

    def test_get_config_value_function(self, monkeypatch):
        """get_config_value() reads via the global manager."""
        monkeypatch.setenv("JWT_SECRET_KEY", "secure-secret")
        load_config()
        assert get_config_value("app_name") == "AIOps Agent"
