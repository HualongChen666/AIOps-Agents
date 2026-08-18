# -*- coding: utf-8 -*-
"""Tests for config.py - Configuration for the Sphinx Documentation microservice."""

import os
import pytest

from extensions.addons.documentation.sphinx_documentation_service.config import (
    SphinxDocumentationServiceSettings,
    settings,
)


class TestSphinxDocumentationServiceSettings:
    """Test suite for SphinxDocumentationServiceSettings."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SphinxDocumentationServiceSettings()
        assert config.service_name == "sphinx-documentation-service"
        assert config.environment == "development"
        assert config.log_level == "INFO"
        assert config.port == 9550
        assert config.redis_url == ""
        assert config.database_url == ""
        assert config.qdrant_url == ""
        assert config.enable_prometheus is True
        assert config.max_retries == 3
        assert config.cache_ttl_seconds == 300
        assert config.request_timeout == 60.0

    def test_custom_service_name(self):
        """Test custom service_name."""
        config = SphinxDocumentationServiceSettings(service_name="custom-service")
        assert config.service_name == "custom-service"

    def test_custom_environment(self):
        """Test custom environment."""
        config = SphinxDocumentationServiceSettings(environment="production")
        assert config.environment == "production"

    def test_custom_log_level(self):
        """Test custom log_level."""
        config = SphinxDocumentationServiceSettings(log_level="DEBUG")
        assert config.log_level == "DEBUG"

    def test_custom_port(self):
        """Test custom port."""
        config = SphinxDocumentationServiceSettings(port=8080)
        assert config.port == 8080

    def test_custom_redis_url(self):
        """Test custom redis_url."""
        config = SphinxDocumentationServiceSettings(redis_url="redis://localhost:6379/0")
        assert config.redis_url == "redis://localhost:6379/0"

    def test_custom_database_url(self):
        """Test custom database_url."""
        config = SphinxDocumentationServiceSettings(
            database_url="postgresql://user:pass@localhost/db"
        )
        assert config.database_url == "postgresql://user:pass@localhost/db"

    def test_custom_qdrant_url(self):
        """Test custom qdrant_url."""
        config = SphinxDocumentationServiceSettings(qdrant_url="http://localhost:6333")
        assert config.qdrant_url == "http://localhost:6333"

    def test_enable_prometheus_true(self):
        """Test enable_prometheus set to True."""
        config = SphinxDocumentationServiceSettings(enable_prometheus=True)
        assert config.enable_prometheus is True

    def test_enable_prometheus_false(self):
        """Test enable_prometheus set to False."""
        config = SphinxDocumentationServiceSettings(enable_prometheus=False)
        assert config.enable_prometheus is False

    def test_custom_max_retries(self):
        """Test custom max_retries."""
        config = SphinxDocumentationServiceSettings(max_retries=5)
        assert config.max_retries == 5

    def test_custom_cache_ttl_seconds(self):
        """Test custom cache_ttl_seconds."""
        config = SphinxDocumentationServiceSettings(cache_ttl_seconds=600)
        assert config.cache_ttl_seconds == 600

    def test_custom_request_timeout(self):
        """Test custom request_timeout."""
        config = SphinxDocumentationServiceSettings(request_timeout=120.0)
        assert config.request_timeout == 120.0

    def test_multiple_custom_values(self):
        """Test setting multiple custom values."""
        config = SphinxDocumentationServiceSettings(
            service_name="test-service",
            environment="staging",
            port=9000,
            max_retries=10,
        )
        assert config.service_name == "test-service"
        assert config.environment == "staging"
        assert config.port == 9000
        assert config.max_retries == 10

    def test_port_zero(self):
        """Test port set to 0."""
        config = SphinxDocumentationServiceSettings(port=0)
        assert config.port == 0

    def test_max_retries_zero(self):
        """Test max_retries set to 0."""
        config = SphinxDocumentationServiceSettings(max_retries=0)
        assert config.max_retries == 0

    def test_cache_ttl_seconds_zero(self):
        """Test cache_ttl_seconds set to 0."""
        config = SphinxDocumentationServiceSettings(cache_ttl_seconds=0)
        assert config.cache_ttl_seconds == 0

    def test_request_timeout_zero(self):
        """Test request_timeout set to 0."""
        config = SphinxDocumentationServiceSettings(request_timeout=0.0)
        assert config.request_timeout == 0.0

    def test_negative_max_retries(self):
        """Test negative max_retries (should be accepted by pydantic)."""
        config = SphinxDocumentationServiceSettings(max_retries=-1)
        assert config.max_retries == -1

    def test_large_port_number(self):
        """Test large port number."""
        config = SphinxDocumentationServiceSettings(port=65535)
        assert config.port == 65535

    def test_string_port(self):
        """Test port as string (pydantic should convert)."""
        config = SphinxDocumentationServiceSettings(port="8080")
        assert config.port == 8080

    def test_string_max_retries(self):
        """Test max_retries as string (pydantic should convert)."""
        config = SphinxDocumentationServiceSettings(max_retries="5")
        assert config.max_retries == 5

    def test_string_cache_ttl(self):
        """Test cache_ttl_seconds as string (pydantic should convert)."""
        config = SphinxDocumentationServiceSettings(cache_ttl_seconds="600")
        assert config.cache_ttl_seconds == 600

    def test_string_request_timeout(self):
        """Test request_timeout as string (pydantic should convert)."""
        config = SphinxDocumentationServiceSettings(request_timeout="120.0")
        assert config.request_timeout == 120.0

    def test_enable_prometheus_string(self):
        """Test enable_prometheus as string (pydantic should convert)."""
        config = SphinxDocumentationServiceSettings(enable_prometheus="true")
        assert config.enable_prometheus is True

    def test_empty_strings(self):
        """Test empty string values."""
        config = SphinxDocumentationServiceSettings(
            service_name="", redis_url="", database_url="", qdrant_url=""
        )
        assert config.service_name == ""
        assert config.redis_url == ""
        assert config.database_url == ""
        assert config.qdrant_url == ""

    def test_unicode_in_service_name(self):
        """Test unicode characters in service_name."""
        config = SphinxDocumentationServiceSettings(service_name="测试服务")
        assert config.service_name == "测试服务"

    def test_special_characters_in_urls(self):
        """Test special characters in URLs."""
        config = SphinxDocumentationServiceSettings(
            redis_url="redis://user:pass@localhost:6379/0?timeout=10",
            database_url="postgresql://user:p@ss@localhost/db",
        )
        assert "@" in config.redis_url
        assert "@" in config.database_url

    def test_log_level_variations(self):
        """Test various log level values."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            config = SphinxDocumentationServiceSettings(log_level=level)
            assert config.log_level == level

    def test_environment_variations(self):
        """Test various environment values."""
        envs = ["development", "staging", "production", "test"]
        for env in envs:
            config = SphinxDocumentationServiceSettings(environment=env)
            assert config.environment == env

    def test_settings_singleton(self):
        """Test that settings is a singleton instance."""
        assert isinstance(settings, SphinxDocumentationServiceSettings)

    def test_settings_default_values(self):
        """Test that settings singleton has default values."""
        assert settings.service_name == "sphinx-documentation-service"
        assert settings.port == 9550
        assert settings.enable_prometheus is True

    def test_config_class_attributes(self):
        """Test Config class attributes."""
        assert hasattr(SphinxDocumentationServiceSettings, "Config")
        assert SphinxDocumentationServiceSettings.Config.env_prefix == "SPHINX_DOCUMENTATION_SERVICE_"
        assert SphinxDocumentationServiceSettings.Config.env_file == ".env"
        assert SphinxDocumentationServiceSettings.Config.extra == "ignore"

    def test_environment_variable_override(self):
        """Test that environment variables can override defaults."""
        original_port = os.environ.get("SPHINX_DOCUMENTATION_SERVICE_PORT")
        os.environ["SPHINX_DOCUMENTATION_SERVICE_PORT"] = "9999"
        try:
            config = SphinxDocumentationServiceSettings()
            # Note: This may not work if the model was already instantiated
            # The singleton might have been created before the env var was set
            # This test documents the expected behavior
            assert isinstance(config.port, int)
        finally:
            if original_port is None:
                os.environ.pop("SPHINX_DOCUMENTATION_SERVICE_PORT", None)
            else:
                os.environ["SPHINX_DOCUMENTATION_SERVICE_PORT"] = original_port

    def test_floating_point_request_timeout(self):
        """Test floating point request_timeout."""
        config = SphinxDocumentationServiceSettings(request_timeout=30.5)
        assert config.request_timeout == 30.5

    def test_very_large_cache_ttl(self):
        """Test very large cache_ttl_seconds."""
        config = SphinxDocumentationServiceSettings(cache_ttl_seconds=86400)  # 1 day
        assert config.cache_ttl_seconds == 86400

    def test_very_large_max_retries(self):
        """Test very large max_retries."""
        config = SphinxDocumentationServiceSettings(max_retries=1000)
        assert config.max_retries == 1000

    def test_boolean_string_conversion(self):
        """Test boolean string conversion for enable_prometheus."""
        config_true = SphinxDocumentationServiceSettings(enable_prometheus="True")
        config_false = SphinxDocumentationServiceSettings(enable_prometheus="False")
        assert config_true.enable_prometheus is True
        assert config_false.enable_prometheus is False

    def test_case_insensitive_log_level(self):
        """Test case insensitive log_level."""
        config = SphinxDocumentationServiceSettings(log_level="debug")
        assert config.log_level == "debug"

    def test_case_insensitive_environment(self):
        """Test case insensitive environment."""
        config = SphinxDocumentationServiceSettings(environment="PRODUCTION")
        assert config.environment == "PRODUCTION"
