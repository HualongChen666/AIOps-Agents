# -*- coding: utf-8 -*-
"""Unit tests for schemas.py - Pydantic schemas for LLM router service."""

import pytest
from datetime import datetime
from extensions.addons.ai_plus.llm_router_service.schemas import (
    ProviderType,
    TaskType,
    ModelConfig,
    RouteRequest,
    RouteResponse,
    GenerateRequest,
    GenerateResponse,
    ModelStatsSchema,
    CircuitStateSchema,
    CostReport,
    PerformanceReport,
    ServiceHealth,
    LiteLLMRequest,
    LiteLLMChoice,
    LiteLLMUsage,
    LiteLLMResponse,
)


class TestProviderType:
    """Test ProviderType enum."""

    def test_provider_type_values(self):
        """Test all provider type values."""
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.OPEN_SOURCE == "open_source"
        assert ProviderType.LOCAL == "local"

    def test_provider_type_iteration(self):
        """Test iterating over provider types."""
        providers = list(ProviderType)
        assert len(providers) == 4
        assert ProviderType.OPENAI in providers


class TestTaskType:
    """Test TaskType enum."""

    def test_task_type_values(self):
        """Test all task type values."""
        assert TaskType.CODE_GENERATION == "code_generation"
        assert TaskType.ANALYSIS == "analysis"
        assert TaskType.SUMMARIZATION == "summarization"
        assert TaskType.QUESTION_ANSWERING == "qa"
        assert TaskType.REASONING == "reasoning"
        assert TaskType.GENERAL == "general"

    def test_task_type_iteration(self):
        """Test iterating over task types."""
        task_types = list(TaskType)
        assert len(task_types) == 6


class TestModelConfig:
    """Test ModelConfig schema."""

    def test_model_config_minimal(self):
        """Test creating model config with minimal fields."""
        config = ModelConfig(name="gpt-4")
        assert config.name == "gpt-4"
        assert config.provider == ProviderType.OPENAI
        assert config.cost_per_1k == 0.0
        assert config.max_tokens == 0
        assert config.context_window == 0
        assert config.base_url is None
        assert config.api_key is None
        assert config.capabilities == []

    def test_model_config_full(self):
        """Test creating model config with all fields."""
        config = ModelConfig(
            name="gpt-4",
            provider=ProviderType.OPENAI,
            model_id="gpt-4-turbo",
            cost_per_1k=0.03,
            max_tokens=128000,
            context_window=128000,
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            capabilities=["chat", "code", "analysis"],
        )
        assert config.name == "gpt-4"
        assert config.provider == ProviderType.OPENAI
        assert config.model_id == "gpt-4-turbo"
        assert config.cost_per_1k == 0.03
        assert config.max_tokens == 128000
        assert config.context_window == 128000
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "sk-test"
        assert len(config.capabilities) == 3

    def test_model_config_different_providers(self):
        """Test model config with different providers."""
        openai_config = ModelConfig(name="gpt-4", provider=ProviderType.OPENAI)
        anthropic_config = ModelConfig(name="claude-3", provider=ProviderType.ANTHROPIC)
        open_source_config = ModelConfig(name="llama2", provider=ProviderType.OPEN_SOURCE)
        local_config = ModelConfig(name="local-llm", provider=ProviderType.LOCAL)

        assert openai_config.provider == ProviderType.OPENAI
        assert anthropic_config.provider == ProviderType.ANTHROPIC
        assert open_source_config.provider == ProviderType.OPEN_SOURCE
        assert local_config.provider == ProviderType.LOCAL

    def test_model_config_serialization(self):
        """Test model config serialization."""
        config = ModelConfig(name="gpt-4", cost_per_1k=0.03)
        data = config.model_dump()
        assert data["name"] == "gpt-4"
        assert data["cost_per_1k"] == 0.03

        # Test deserialization
        config2 = ModelConfig(**data)
        assert config2.name == config.name
        assert config2.cost_per_1k == config.cost_per_1k


class TestRouteRequest:
    """Test RouteRequest schema."""

    def test_route_request_minimal(self):
        """Test creating route request with minimal fields."""
        request = RouteRequest(prompt="Hello, world!")
        assert request.prompt == "Hello, world!"
        assert request.task_type == TaskType.GENERAL
        assert request.force_model is None
        assert request.context == {}
        assert request.budget is None
        assert request.strategy == "cost_optimized"
        assert request.max_tokens == 1024
        assert request.temperature == 0.7
        assert request.use_cache is True

    def test_route_request_full(self):
        """Test creating route request with all fields."""
        request = RouteRequest(
            prompt="Write code",
            task_type=TaskType.CODE_GENERATION,
            force_model="gpt-4",
            context={"language": "python"},
            budget=0.01,
            strategy="capability_first",
            max_tokens=2048,
            temperature=0.5,
            use_cache=False,
        )
        assert request.prompt == "Write code"
        assert request.task_type == TaskType.CODE_GENERATION
        assert request.force_model == "gpt-4"
        assert request.context == {"language": "python"}
        assert request.budget == 0.01
        assert request.strategy == "capability_first"
        assert request.max_tokens == 2048
        assert request.temperature == 0.5
        assert request.use_cache is False

    def test_route_request_different_task_types(self):
        """Test route request with different task types."""
        for task_type in TaskType:
            request = RouteRequest(prompt="test", task_type=task_type)
            assert request.task_type == task_type

    def test_route_request_validation(self):
        """Test route request validation."""
        # Valid temperature range
        request = RouteRequest(prompt="test", temperature=0.0)
        assert request.temperature == 0.0

        request = RouteRequest(prompt="test", temperature=2.0)
        assert request.temperature == 2.0

        # Valid max_tokens
        request = RouteRequest(prompt="test", max_tokens=1)
        assert request.max_tokens == 1

        request = RouteRequest(prompt="test", max_tokens=100000)
        assert request.max_tokens == 100000


class TestRouteResponse:
    """Test RouteResponse schema."""

    def test_route_response_minimal(self):
        """Test creating route response with minimal fields."""
        response = RouteResponse(
            model_name="gpt-4",
            provider=ProviderType.OPENAI,
            estimated_cost=0.01,
            estimated_tokens=100,
            confidence=0.9,
            reason="Best model for task",
        )
        assert response.model_name == "gpt-4"
        assert response.provider == ProviderType.OPENAI
        assert response.estimated_cost == 0.01
        assert response.estimated_tokens == 100
        assert response.confidence == 0.9
        assert response.reason == "Best model for task"
        assert response.latency_ms is None

    def test_route_response_with_latency(self):
        """Test route response with latency."""
        response = RouteResponse(
            model_name="gpt-4",
            provider=ProviderType.OPENAI,
            estimated_cost=0.01,
            estimated_tokens=100,
            confidence=0.9,
            reason="Best model",
            latency_ms=150.5,
        )
        assert response.latency_ms == 150.5

    def test_route_response_serialization(self):
        """Test route response serialization."""
        response = RouteResponse(
            model_name="gpt-4",
            provider=ProviderType.OPENAI,
            estimated_cost=0.01,
            estimated_tokens=100,
            confidence=0.9,
            reason="Test",
        )
        data = response.model_dump()
        assert data["model_name"] == "gpt-4"
        assert data["provider"] == "openai"


class TestGenerateRequest:
    """Test GenerateRequest schema."""

    def test_generate_request_minimal(self):
        """Test creating generate request with minimal fields."""
        request = GenerateRequest(prompt="Generate text")
        assert request.prompt == "Generate text"
        assert request.model is None
        assert request.task_type == TaskType.GENERAL
        assert request.max_tokens == 1024
        assert request.temperature == 0.7
        assert request.budget is None
        assert request.strategy == "cost_optimized"

    def test_generate_request_with_model(self):
        """Test generate request with specific model."""
        request = GenerateRequest(
            prompt="Generate code",
            model="gpt-4",
            task_type=TaskType.CODE_GENERATION,
        )
        assert request.model == "gpt-4"
        assert request.task_type == TaskType.CODE_GENERATION

    def test_generate_request_full(self):
        """Test generate request with all fields."""
        request = GenerateRequest(
            prompt="Test",
            model="claude-3",
            task_type=TaskType.ANALYSIS,
            max_tokens=4096,
            temperature=0.3,
            budget=0.05,
            strategy="balanced",
        )
        assert request.prompt == "Test"
        assert request.model == "claude-3"
        assert request.task_type == TaskType.ANALYSIS
        assert request.max_tokens == 4096
        assert request.temperature == 0.3
        assert request.budget == 0.05
        assert request.strategy == "balanced"


class TestGenerateResponse:
    """Test GenerateResponse schema."""

    def test_generate_response(self):
        """Test creating generate response."""
        response = GenerateResponse(
            content="Generated text",
            model="gpt-4",
            provider=ProviderType.OPENAI,
            tokens=150,
            latency_ms=200.0,
            cost=0.02,
        )
        assert response.content == "Generated text"
        assert response.model == "gpt-4"
        assert response.provider == ProviderType.OPENAI
        assert response.tokens == 150
        assert response.latency_ms == 200.0
        assert response.cost == 0.02

    def test_generate_response_different_providers(self):
        """Test generate response with different providers."""
        for provider in ProviderType:
            response = GenerateResponse(
                content="Test",
                model="test-model",
                provider=provider,
                tokens=100,
                latency_ms=100.0,
                cost=0.01,
            )
            assert response.provider == provider


class TestModelStatsSchema:
    """Test ModelStatsSchema."""

    def test_model_stats_minimal(self):
        """Test model stats with minimal fields."""
        stats = ModelStatsSchema(model_name="gpt-4")
        assert stats.model_name == "gpt-4"
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0
        assert stats.avg_latency == 0.0
        assert stats.last_error is None

    def test_model_stats_full(self):
        """Test model stats with all fields."""
        stats = ModelStatsSchema(
            model_name="gpt-4",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            avg_latency=150.5,
            last_error="Timeout error",
        )
        assert stats.model_name == "gpt-4"
        assert stats.total_requests == 100
        assert stats.successful_requests == 95
        assert stats.failed_requests == 5
        assert stats.avg_latency == 150.5
        assert stats.last_error == "Timeout error"

    def test_model_stats_serialization(self):
        """Test model stats serialization."""
        stats = ModelStatsSchema(model_name="gpt-4", total_requests=50)
        data = stats.model_dump()
        assert data["model_name"] == "gpt-4"
        assert data["total_requests"] == 50


class TestCircuitStateSchema:
    """Test CircuitStateSchema."""

    def test_circuit_state(self):
        """Test circuit state schema."""
        state = CircuitStateSchema(model_name="gpt-4", state="closed")
        assert state.model_name == "gpt-4"
        assert state.state == "closed"

    def test_circuit_state_different_states(self):
        """Test different circuit states."""
        for state_value in ["closed", "open", "half_open"]:
            state = CircuitStateSchema(model_name="test", state=state_value)
            assert state.state == state_value


class TestCostReport:
    """Test CostReport schema."""

    def test_cost_report_minimal(self):
        """Test cost report with minimal fields."""
        report = CostReport(hourly_cost=1.5, request_count=10, avg_cost_per_request=0.15)
        assert report.hourly_cost == 1.5
        assert report.request_count == 10
        assert report.avg_cost_per_request == 0.15
        assert report.budget_per_request is None
        assert report.max_cost_per_hour is None

    def test_cost_report_full(self):
        """Test cost report with all fields."""
        report = CostReport(
            hourly_cost=5.0,
            request_count=50,
            avg_cost_per_request=0.1,
            budget_per_request=0.2,
            max_cost_per_hour=10.0,
        )
        assert report.hourly_cost == 5.0
        assert report.request_count == 50
        assert report.avg_cost_per_request == 0.1
        assert report.budget_per_request == 0.2
        assert report.max_cost_per_hour == 10.0


class TestPerformanceReport:
    """Test PerformanceReport schema."""

    def test_performance_report(self):
        """Test performance report."""
        model_stats = [
            ModelStatsSchema(
                model_name="gpt-4",
                total_requests=100,
                successful_requests=95,
                failed_requests=5,
                avg_latency=150.0,
            )
        ]
        circuit_states = [
            CircuitStateSchema(model_name="gpt-4", state="closed")
        ]
        cost_report = CostReport(
            hourly_cost=2.0, request_count=20, avg_cost_per_request=0.1
        )

        report = PerformanceReport(
            model_stats=model_stats,
            circuit_states=circuit_states,
            cost_report=cost_report,
            total_requests=100,
        )
        assert len(report.model_stats) == 1
        assert len(report.circuit_states) == 1
        assert report.total_requests == 100
        assert report.cost_report.hourly_cost == 2.0


class TestServiceHealth:
    """Test ServiceHealth schema."""

    def test_service_health_minimal(self):
        """Test service health with minimal fields."""
        health = ServiceHealth(status="ok", service="llm-router")
        assert health.status == "ok"
        assert health.service == "llm-router"
        assert health.uptime_seconds == 0
        assert health.model_count == 0

    def test_service_health_full(self):
        """Test service health with all fields."""
        health = ServiceHealth(
            status="ok", service="llm-router", uptime_seconds=3600, model_count=5
        )
        assert health.status == "ok"
        assert health.service == "llm-router"
        assert health.uptime_seconds == 3600
        assert health.model_count == 5

    def test_service_health_different_statuses(self):
        """Test different health statuses."""
        for status in ["ok", "degraded", "error"]:
            health = ServiceHealth(status=status, service="test")
            assert health.status == status


class TestLiteLLMRequest:
    """Test LiteLLMRequest schema."""

    def test_litellm_request_minimal(self):
        """Test LiteLLM request with minimal fields."""
        request = LiteLLMRequest()
        assert request.model == "auto"
        assert request.messages == []
        assert request.max_tokens == 1024
        assert request.temperature == 0.7
        assert request.budget is None
        assert request.strategy == "cost_optimized"

    def test_litellm_request_with_messages(self):
        """Test LiteLLM request with messages."""
        messages = [{"role": "user", "content": "Hello"}]
        request = LiteLLMRequest(model="gpt-4", messages=messages)
        assert request.model == "gpt-4"
        assert len(request.messages) == 1
        assert request.messages[0]["role"] == "user"

    def test_litellm_request_full(self):
        """Test LiteLLM request with all fields."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        request = LiteLLMRequest(
            model="claude-3",
            messages=messages,
            max_tokens=2048,
            temperature=0.5,
            budget=0.02,
            strategy="balanced",
        )
        assert request.model == "claude-3"
        assert len(request.messages) == 2
        assert request.max_tokens == 2048
        assert request.temperature == 0.5
        assert request.budget == 0.02
        assert request.strategy == "balanced"


class TestLiteLLMChoice:
    """Test LiteLLMChoice schema."""

    def test_litellm_choice_minimal(self):
        """Test LiteLLM choice with minimal fields."""
        choice = LiteLLMChoice(message={"role": "assistant", "content": "Response"})
        assert choice.index == 0
        assert choice.message["role"] == "assistant"
        assert choice.finish_reason == "stop"

    def test_litellm_choice_full(self):
        """Test LiteLLM choice with all fields."""
        choice = LiteLLMChoice(
            index=1,
            message={"role": "assistant", "content": "Test response"},
            finish_reason="length",
        )
        assert choice.index == 1
        assert choice.message["content"] == "Test response"
        assert choice.finish_reason == "length"


class TestLiteLLMUsage:
    """Test LiteLLMUsage schema."""

    def test_litellm_usage_minimal(self):
        """Test LiteLLM usage with minimal fields."""
        usage = LiteLLMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_litellm_usage_full(self):
        """Test LiteLLM usage with all fields."""
        usage = LiteLLMUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80)
        assert usage.prompt_tokens == 50
        assert usage.completion_tokens == 30
        assert usage.total_tokens == 80


class TestLiteLLMResponse:
    """Test LiteLLMResponse schema."""

    def test_litellm_response_minimal(self):
        """Test LiteLLM response with minimal fields."""
        response = LiteLLMResponse()
        assert response.object == "chat.completion"
        assert response.model == ""
        assert response.choices == []
        assert response.usage.total_tokens == 0

    def test_litellm_response_full(self):
        """Test LiteLLM response with all fields."""
        choice = LiteLLMChoice(message={"role": "assistant", "content": "Hello"})
        usage = LiteLLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        response = LiteLLMResponse(
            id="chatcmpl-123",
            model="gpt-4",
            choices=[choice],
            usage=usage,
        )
        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-4"
        assert len(response.choices) == 1
        assert response.usage.total_tokens == 15

    def test_litellm_response_created_timestamp(self):
        """Test LiteLLM response created timestamp."""
        response = LiteLLMResponse()
        # The timestamp is set at creation time, just check it's a reasonable value
        assert response.created > 0
        assert response.created < 2147483647  # Reasonable upper bound
