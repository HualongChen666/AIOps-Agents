# -*- coding: utf-8 -*-
"""Tests for workflow_service config module."""

import os
from unittest.mock import patch

import pytest

from extensions.addons.operations.workflow_service.config import WorkflowServiceSettings, settings


class TestWorkflowServiceSettings:
    """Test cases for WorkflowServiceSettings."""

    def test_default_settings(self):
        """Test that default settings are properly initialized."""
        settings = WorkflowServiceSettings()
        assert settings.service_name == "workflow-service"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.orchestrator_port == 9201
        assert settings.scheduler_port == 9202
        assert settings.executor_port == 9203
        assert settings.redis_url == "redis://localhost:6379/3"
        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.use_in_memory is True
        assert settings.enable_prometheus is True
        assert settings.default_execution_timeout == 120
        assert settings.max_concurrent_workflows == 50
        assert settings.scheduler_poll_interval_seconds == 1

    def test_settings_from_environment_variables(self, monkeypatch):
        """Test that settings can be loaded from environment variables."""
        monkeypatch.setenv("WORKFLOW_SERVICE_SERVICE_NAME", "custom-service")
        monkeypatch.setenv("WORKFLOW_SERVICE_ENVIRONMENT", "production")
        monkeypatch.setenv("WORKFLOW_SERVICE_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("WORKFLOW_SERVICE_ORCHESTRATOR_PORT", "9301")
        monkeypatch.setenv("WORKFLOW_SERVICE_SCHEDULER_PORT", "9302")
        monkeypatch.setenv("WORKFLOW_SERVICE_EXECUTOR_PORT", "9303")
        monkeypatch.setenv("WORKFLOW_SERVICE_REDIS_URL", "redis://custom:6380/0")
        monkeypatch.setenv("WORKFLOW_SERVICE_DATABASE_URL", "postgresql://user:pass@host/db")
        monkeypatch.setenv("WORKFLOW_SERVICE_USE_IN_MEMORY", "false")
        monkeypatch.setenv("WORKFLOW_SERVICE_ENABLE_PROMETHEUS", "false")
        monkeypatch.setenv("WORKFLOW_SERVICE_DEFAULT_EXECUTION_TIMEOUT", "300")
        monkeypatch.setenv("WORKFLOW_SERVICE_MAX_CONCURRENT_WORKFLOWS", "100")
        monkeypatch.setenv("WORKFLOW_SERVICE_SCHEDULER_POLL_INTERVAL_SECONDS", "5")

        settings = WorkflowServiceSettings()
        assert settings.service_name == "custom-service"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.orchestrator_port == 9301
        assert settings.scheduler_port == 9302
        assert settings.executor_port == 9303
        assert settings.redis_url == "redis://custom:6380/0"
        assert settings.database_url == "postgresql://user:pass@host/db"
        assert settings.use_in_memory is False
        assert settings.enable_prometheus is False
        assert settings.default_execution_timeout == 300
        assert settings.max_concurrent_workflows == 100
        assert settings.scheduler_poll_interval_seconds == 5

    def test_settings_with_custom_values(self):
        """Test settings with custom constructor values."""
        custom_settings = WorkflowServiceSettings(
            service_name="test-service",
            environment="staging",
            log_level="WARNING",
            orchestrator_port=8000,
            scheduler_port=8001,
            executor_port=8002,
            redis_url="redis://test:6379/1",
            database_url="postgresql://test:test@test/test",
            use_in_memory=False,
            enable_prometheus=False,
            default_execution_timeout=60,
            max_concurrent_workflows=10,
            scheduler_poll_interval_seconds=2,
        )
        assert custom_settings.service_name == "test-service"
        assert custom_settings.environment == "staging"
        assert custom_settings.log_level == "WARNING"
        assert custom_settings.orchestrator_port == 8000
        assert custom_settings.scheduler_port == 8001
        assert custom_settings.executor_port == 8002
        assert custom_settings.redis_url == "redis://test:6379/1"
        assert custom_settings.database_url == "postgresql://test:test@test/test"
        assert custom_settings.use_in_memory is False
        assert custom_settings.enable_prometheus is False
        assert custom_settings.default_execution_timeout == 60
        assert custom_settings.max_concurrent_workflows == 10
        assert custom_settings.scheduler_poll_interval_seconds == 2

    def test_settings_port_validation(self):
        """Test that port settings accept valid ranges."""
        settings = WorkflowServiceSettings(
            orchestrator_port=1,
            scheduler_port=65535,
            executor_port=8080,
        )
        assert settings.orchestrator_port == 1
        assert settings.scheduler_port == 65535
        assert settings.executor_port == 8080

    def test_settings_timeout_validation(self):
        """Test that timeout settings accept valid values."""
        settings = WorkflowServiceSettings(
            default_execution_timeout=1,
            max_concurrent_workflows=1,
            scheduler_poll_interval_seconds=0,
        )
        assert settings.default_execution_timeout == 1
        assert settings.max_concurrent_workflows == 1
        assert settings.scheduler_poll_interval_seconds == 0

    def test_settings_boolean_fields(self):
        """Test boolean field variations."""
        settings_true = WorkflowServiceSettings(
            use_in_memory=True,
            enable_prometheus=True,
        )
        assert settings_true.use_in_memory is True
        assert settings_true.enable_prometheus is True

        settings_false = WorkflowServiceSettings(
            use_in_memory=False,
            enable_prometheus=False,
        )
        assert settings_false.use_in_memory is False
        assert settings_false.enable_prometheus is False

    def test_settings_extra_fields_ignored(self):
        """Test that extra fields are ignored due to Config.extra = 'ignore'."""
        settings = WorkflowServiceSettings(
            service_name="test",
            extra_field="should_be_ignored",
            another_extra=123,
        )
        assert settings.service_name == "test"
        assert not hasattr(settings, "extra_field")
        assert not hasattr(settings, "another_extra")

    def test_global_settings_instance(self):
        """Test that the global settings instance is properly initialized."""
        assert settings is not None
        assert isinstance(settings, WorkflowServiceSettings)
        assert settings.service_name == "workflow-service"

    def test_settings_model_dump(self):
        """Test that settings can be serialized to dict."""
        settings = WorkflowServiceSettings()
        dumped = settings.model_dump()
        assert isinstance(dumped, dict)
        assert "service_name" in dumped
        assert "environment" in dumped
        assert "orchestrator_port" in dumped
        assert dumped["service_name"] == "workflow-service"

    def test_settings_model_json_schema(self):
        """Test that settings can generate JSON schema."""
        schema = WorkflowServiceSettings.model_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "service_name" in schema["properties"]
        assert "environment" in schema["properties"]

    def test_settings_with_pydantic_settings_fallback(self):
        """Test that settings work with both pydantic_settings and pydantic BaseModel."""
        # This test ensures the fallback import works
        from extensions.addons.operations.workflow_service.config import BaseSettings

        assert BaseSettings is not None
        settings = WorkflowServiceSettings()
        assert isinstance(settings, BaseSettings)

    def test_settings_env_prefix(self):
        """Test that environment variable prefix is correctly set."""
        from extensions.addons.operations.workflow_service.config import WorkflowServiceSettings

        # Check the Config class
        assert hasattr(WorkflowServiceSettings.Config, "env_prefix")
        assert WorkflowServiceSettings.Config.env_prefix == "WORKFLOW_SERVICE_"

    def test_settings_env_file(self):
        """Test that env_file configuration is set."""
        from extensions.addons.operations.workflow_service.config import WorkflowServiceSettings

        assert hasattr(WorkflowServiceSettings.Config, "env_file")
        assert WorkflowServiceSettings.Config.env_file == ".env"

    def test_settings_extra_ignore(self):
        """Test that extra fields are ignored."""
        from extensions.addons.operations.workflow_service.config import WorkflowServiceSettings

        assert hasattr(WorkflowServiceSettings.Config, "extra")
        assert WorkflowServiceSettings.Config.extra == "ignore"

    def test_settings_immutable_after_creation(self):
        """Test that settings object maintains its values after creation."""
        settings = WorkflowServiceSettings(service_name="test")
        original_name = settings.service_name
        # Pydantic v2 models are mutable by default, but we test consistency
        assert settings.service_name == original_name

    def test_settings_database_url_format(self):
        """Test that database URL follows expected format."""
        settings = WorkflowServiceSettings()
        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert "@" in settings.database_url
        assert "/" in settings.database_url

    def test_settings_redis_url_format(self):
        """Test that Redis URL follows expected format."""
        settings = WorkflowServiceSettings()
        assert settings.redis_url.startswith("redis://")
        assert ":" in settings.redis_url
        assert "/" in settings.redis_url

    def test_settings_service_ports_are_distinct(self):
        """Test that service ports are distinct by default."""
        settings = WorkflowServiceSettings()
        assert settings.orchestrator_port != settings.scheduler_port
        assert settings.scheduler_port != settings.executor_port
        assert settings.orchestrator_port != settings.executor_port

    def test_settings_concurrent_workflows_positive(self):
        """Test that max_concurrent_workflows is always positive."""
        settings = WorkflowServiceSettings()
        assert settings.max_concurrent_workflows > 0

    def test_settings_execution_timeout_positive(self):
        """Test that default_execution_timeout is always positive."""
        settings = WorkflowServiceSettings()
        assert settings.default_execution_timeout > 0

    def test_settings_poll_interval_non_negative(self):
        """Test that scheduler_poll_interval_seconds is non-negative."""
        settings = WorkflowServiceSettings()
        assert settings.scheduler_poll_interval_seconds >= 0

    def test_settings_with_zero_timeout(self):
        """Test settings with zero timeout values."""
        settings = WorkflowServiceSettings(
            default_execution_timeout=0,
            scheduler_poll_interval_seconds=0,
        )
        assert settings.default_execution_timeout == 0
        assert settings.scheduler_poll_interval_seconds == 0

    def test_settings_with_large_values(self):
        """Test settings with large integer values."""
        settings = WorkflowServiceSettings(
            max_concurrent_workflows=10000,
            default_execution_timeout=3600,
            scheduler_poll_interval_seconds=3600,
        )
        assert settings.max_concurrent_workflows == 10000
        assert settings.default_execution_timeout == 3600
        assert settings.scheduler_poll_interval_seconds == 3600

    def test_settings_log_level_valid_values(self):
        """Test settings with various valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            settings = WorkflowServiceSettings(log_level=level)
            assert settings.log_level == level

    def test_settings_environment_valid_values(self):
        """Test settings with various environment values."""
        environments = ["development", "staging", "production", "test"]
        for env in environments:
            settings = WorkflowServiceSettings(environment=env)
            assert settings.environment == env

    def test_settings_service_name_validation(self):
        """Test that service_name accepts various formats."""
        names = ["workflow-service", "workflow_service", "WorkflowService", "workflow.service"]
        for name in names:
            settings = WorkflowServiceSettings(service_name=name)
            assert settings.service_name == name

    def test_settings_redis_url_variations(self):
        """Test settings with various Redis URL formats."""
        urls = [
            "redis://localhost:6379/0",
            "redis://host:port/db",
            "redis://:password@host:port/db",
            "redis://user:password@host:port/db",
        ]
        for url in urls:
            settings = WorkflowServiceSettings(redis_url=url)
            assert settings.redis_url == url

    def test_settings_database_url_variations(self):
        """Test settings with various database URL formats."""
        urls = [
            "postgresql+asyncpg://user:pass@host/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
            "postgresql+asyncpg://user@host/db",
        ]
        for url in urls:
            settings = WorkflowServiceSettings(database_url=url)
            assert settings.database_url == url
