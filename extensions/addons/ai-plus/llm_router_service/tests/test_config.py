# -*- coding: utf-8 -*-
"""Unit tests for config.py - LLM router service configuration."""

import pytest
from pydantic import ValidationError
from extensions.addons.ai_plus.llm_router_service.config import (
    LLMRouterSettings,
    settings,
)


class TestLLMRouterSettings:
    """Test LLMRouterSettings class."""

    def test_default_settings(self):
        """Test default settings values."""
        config = LLMRouterSettings()
        assert config.service_name == "llm-router-service"
        assert config.environment == "development"
        assert config.log_level == "INFO"
        assert config.port == 9405
        assert config.redis_url == ""
        assert config.enable_prometheus is True
        assert config.openai_api_key == ""
        assert config.anthropic_api_key == ""
        assert config.default_strategy == "cost_optimized"
        assert config.budget_per_request is None
        assert config.max_cost_per_hour is None
        assert config.retry_policy == "exponential"
        assert config.max_retries == 3
        assert config.request_timeout == 60.0

    def test_custom_settings(self):
        """Test custom settings initialization."""
        config = LLMRouterSettings(
            service_name="custom-service",
            environment="production",
            log_level="DEBUG",
            port=8000,
            redis_url="redis://localhost:6379",
            enable_prometheus=False,
            openai_api_key="sk-test-openai",
            anthropic_api_key="sk-test-anthropic",
            default_strategy="balanced",
            budget_per_request=0.01,
            max_cost_per_hour=10.0,
            retry_policy="fixed_1s",
            max_retries=5,
            request_timeout=120.0,
        )
        assert config.service_name == "custom-service"
        assert config.environment == "production"
        assert config.log_level == "DEBUG"
        assert config.port == 8000
        assert config.redis_url == "redis://localhost:6379"
        assert config.enable_prometheus is False
        assert config.openai_api_key == "sk-test-openai"
        assert config.anthropic_api_key == "sk-test-anthropic"
        assert config.default_strategy == "balanced"
        assert config.budget_per_request == 0.01
        assert config.max_cost_per_hour == 10.0
        assert config.retry_policy == "fixed_1s"
        assert config.max_retries == 5
        assert config.request_timeout == 120.0

    def test_settings_from_env(self, monkeypatch):
        """Test settings from environment variables."""
        monkeypatch.setenv("LLM_ROUTER_SERVICE_SERVICE_NAME", "env-service")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_ENVIRONMENT", "staging")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_LOG_LEVEL", "WARNING")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_PORT", "9000")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_REDIS_URL", "redis://test:6379")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_ENABLE_PROMETHEUS", "false")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_OPENAI_API_KEY", "sk-env-openai")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_ANTHROPIC_API_KEY", "sk-env-anthropic")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_DEFAULT_STRATEGY", "capability_first")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_BUDGET_PER_REQUEST", "0.05")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_MAX_COST_PER_HOUR", "50.0")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_RETRY_POLICY", "aggressive")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_MAX_RETRIES", "10")
        monkeypatch.setenv("LLM_ROUTER_SERVICE_REQUEST_TIMEOUT", "90.0")

        config = LLMRouterSettings()
        assert config.service_name == "env-service"
        assert config.environment == "staging"
        assert config.log_level == "WARNING"
        assert config.port == 9000
        assert config.redis_url == "redis://test:6379"
        assert config.enable_prometheus is False
        assert config.openai_api_key == "sk-env-openai"
        assert config.anthropic_api_key == "sk-env-anthropic"
        assert config.default_strategy == "capability_first"
        assert config.budget_per_request == 0.05
        assert config.max_cost_per_hour == 50.0
        assert config.retry_policy == "aggressive"
        assert config.max_retries == 10
        assert config.request_timeout == 90.0

    def test_settings_env_prefix(self):
        """Test environment variable prefix."""
        config = LLMRouterSettings()
        assert config.Config.env_prefix == "LLM_ROUTER_SERVICE_"

    def test_settings_env_file(self):
        """Test .env file configuration."""
        config = LLMRouterSettings()
        assert config.Config.env_file == ".env"

    def test_settings_extra_ignore(self):
        """Test extra fields are ignored."""
        config = LLMRouterSettings(
            service_name="test",
            extra_field="should_be_ignored",
        )
        assert not hasattr(config, "extra_field")

    def test_port_validation(self):
        """Test port validation."""
        # Valid ports
        config = LLMRouterSettings(port=1)
        assert config.port == 1

        config = LLMRouterSettings(port=65535)
        assert config.port == 65535

    def test_boolean_validation(self):
        """Test boolean field validation."""
        config = LLMRouterSettings(enable_prometheus=True)
        assert config.enable_prometheus is True

        config = LLMRouterSettings(enable_prometheus=False)
        assert config.enable_prometheus is False

    def test_numeric_validation(self):
        """Test numeric field validation."""
        config = LLMRouterSettings(
            budget_per_request=0.001,
            max_cost_per_hour=100.0,
            max_retries=0,
            request_timeout=1.0,
        )
        assert config.budget_per_request == 0.001
        assert config.max_cost_per_hour == 100.0
        assert config.max_retries == 0
        assert config.request_timeout == 1.0

    def test_string_validation(self):
        """Test string field validation."""
        config = LLMRouterSettings(
            service_name="test-service",
            environment="production",
            log_level="ERROR",
            redis_url="redis://localhost:6379/0",
            openai_api_key="sk-1234567890",
            anthropic_api_key="sk-ant-1234567890",
            default_strategy="cost_optimized",
            retry_policy="exponential",
        )
        assert config.service_name == "test-service"
        assert config.environment == "production"
        assert config.log_level == "ERROR"
        assert config.redis_url == "redis://localhost:6379/0"
        assert config.openai_api_key == "sk-1234567890"
        assert config.anthropic_api_key == "sk-ant-1234567890"
        assert config.default_strategy == "cost_optimized"
        assert config.retry_policy == "exponential"

    def test_none_values(self):
        """Test None values for optional fields."""
        config = LLMRouterSettings(
            budget_per_request=None,
            max_cost_per_hour=None,
        )
        assert config.budget_per_request is None
        assert config.max_cost_per_hour is None

    def test_settings_model_dump(self):
        """Test settings serialization."""
        config = LLMRouterSettings(service_name="test", port=8000)
        data = config.model_dump()
        assert data["service_name"] == "test"
        assert data["port"] == 8000

    def test_settings_model_dump_json(self):
        """Test settings JSON serialization."""
        config = LLMRouterSettings(service_name="test", port=8000)
        json_str = config.model_dump_json()
        assert "test" in json_str
        assert "8000" in json_str

    def test_global_settings_instance(self):
        """Test global settings instance."""
        assert isinstance(settings, LLMRouterSettings)
        assert settings.service_name == "llm-router-service"

    def test_settings_immutability_after_creation(self):
        """Test that settings can be modified after creation."""
        config = LLMRouterSettings(port=8000)
        assert config.port == 8000
        # Pydantic v2 allows modification by default
        config.port = 9000
        assert config.port == 9000

    def test_different_strategies(self):
        """Test different routing strategies."""
        strategies = ["cost_optimized", "capability_first", "balanced"]
        for strategy in strategies:
            config = LLMRouterSettings(default_strategy=strategy)
            assert config.default_strategy == strategy

    def test_different_retry_policies(self):
        """Test different retry policies."""
        policies = ["no_retry", "fixed_1s", "exponential", "aggressive", "conservative"]
        for policy in policies:
            config = LLMRouterSettings(retry_policy=policy)
            assert config.retry_policy == policy

    def test_edge_case_zero_values(self):
        """Test edge case with zero values."""
        config = LLMRouterSettings(
            port=0,
            budget_per_request=0.0,
            max_cost_per_hour=0.0,
            max_retries=0,
            request_timeout=0.0,
        )
        assert config.port == 0
        assert config.budget_per_request == 0.0
        assert config.max_cost_per_hour == 0.0
        assert config.max_retries == 0
        assert config.request_timeout == 0.0

    def test_edge_case_negative_values(self):
        """Test edge case with negative values (should be allowed by Pydantic)."""
        config = LLMRouterSettings(
            budget_per_request=-0.01,
            max_cost_per_hour=-10.0,
        )
        assert config.budget_per_request == -0.01
        assert config.max_cost_per_hour == -10.0

    def test_large_values(self):
        """Test large numeric values."""
        config = LLMRouterSettings(
            port=65535,
            budget_per_request=1000.0,
            max_cost_per_hour=1000000.0,
            max_retries=1000,
            request_timeout=3600.0,
        )
        assert config.port == 65535
        assert config.budget_per_request == 1000.0
        assert config.max_cost_per_hour == 1000000.0
        assert config.max_retries == 1000
        assert config.request_timeout == 3600.0

    def test_empty_strings(self):
        """Test empty string values."""
        config = LLMRouterSettings(
            service_name="",
            redis_url="",
            openai_api_key="",
            anthropic_api_key="",
        )
        assert config.service_name == ""
        assert config.redis_url == ""
        assert config.openai_api_key == ""
        assert config.anthropic_api_key == ""
