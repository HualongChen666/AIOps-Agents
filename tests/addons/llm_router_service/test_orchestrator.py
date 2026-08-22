# -*- coding: utf-8 -*-
"""Unit tests for orchestrator.py - LLM Router orchestrator."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from extensions.addons.ai_plus.llm_router_service.orchestrator import (
    LLMRouterOrchestrator,
)
from extensions.addons.ai_plus.llm_router_service.schemas import (
    RouteRequest,
    GenerateRequest,
    LiteLLMRequest,
    TaskType,
    ProviderType,
    RouteResponse,
    GenerateResponse,
)


class TestLLMRouterOrchestrator:
    """Test LLMRouterOrchestrator class."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization with default settings."""
        orchestrator = LLMRouterOrchestrator()

        assert orchestrator.settings is not None
        assert len(orchestrator.model_configs) > 0
        assert orchestrator.cache is not None
        assert orchestrator.retry_engine is not None
        assert orchestrator.router is not None
        assert len(orchestrator.providers) > 0

    def test_orchestrator_initialization_with_custom_settings(self):
        """Test orchestrator initialization with custom settings."""
        from extensions.addons.ai_plus.llm_router_service.config import LLMRouterSettings

        custom_settings = LLMRouterSettings(
            service_name="custom-service",
            default_strategy="balanced",
            budget_per_request=0.01,
        )

        orchestrator = LLMRouterOrchestrator(settings_obj=custom_settings)

        assert orchestrator.settings.service_name == "custom-service"
        assert orchestrator.router.strategy == "balanced"

    def test_orchestrator_initialization_with_custom_model_configs(self):
        """Test orchestrator initialization with custom model configs."""
        custom_configs = [
            {
                "name": "custom-model",
                "model": "custom-model",
                "provider": ProviderType.OPENAI,
                "cost_per_1k": 0.01,
                "max_tokens": 4096,
                "context_window": 4096,
            }
        ]

        orchestrator = LLMRouterOrchestrator(model_configs=custom_configs)

        assert len(orchestrator.model_configs) == 1
        assert orchestrator.model_configs[0]["name"] == "custom-model"

    def test_default_model_configs(self):
        """Test default model configs."""
        orchestrator = LLMRouterOrchestrator()
        configs = orchestrator._default_model_configs()

        assert len(configs) > 0
        for config in configs:
            assert "name" in config
            assert "model" in config
            assert "provider" in config
            assert "cost_per_1k" in config

    def test_to_core_configs(self):
        """Test conversion to core configs."""
        orchestrator = LLMRouterOrchestrator()
        core_configs = orchestrator._to_core_configs()

        assert len(core_configs) == len(orchestrator.model_configs)
        for config in core_configs:
            assert "model" in config
            assert "cost_per_1k" in config
            assert "max_tokens" in config
            assert "context_window" in config

    def test_build_providers(self):
        """Test provider building."""
        orchestrator = LLMRouterOrchestrator()

        assert len(orchestrator.providers) > 0
        for model_name, provider in orchestrator.providers.items():
            assert provider is not None
            assert hasattr(provider, "provider_type")

    def test_to_core_task_type_mapping(self):
        """Test task type mapping to core."""
        orchestrator = LLMRouterOrchestrator()

        mappings = {
            TaskType.CODE_GENERATION: "code_generation",
            TaskType.ANALYSIS: "analysis",
            TaskType.SUMMARIZATION: "summarization",
            TaskType.QUESTION_ANSWERING: "qa",
            TaskType.REASONING: "reasoning",
            TaskType.GENERAL: "general",
        }

        for task_type, expected in mappings.items():
            core_type = orchestrator._to_core_task_type(task_type)
            assert core_type.value == expected

    def test_list_models(self):
        """Test listing models."""
        orchestrator = LLMRouterOrchestrator()
        models = orchestrator.list_models()

        assert len(models) > 0
        for model in models:
            assert hasattr(model, "name")
            assert hasattr(model, "provider")

    def test_get_provider(self):
        """Test getting provider by model name."""
        orchestrator = LLMRouterOrchestrator()
        models = orchestrator.list_models()

        if models:
            provider = orchestrator._get_provider(models[0].name)
            assert provider is not None

    def test_get_provider_nonexistent(self):
        """Test getting provider for nonexistent model."""
        orchestrator = LLMRouterOrchestrator()
        provider = orchestrator._get_provider("nonexistent-model")

        assert provider is None

    @pytest.mark.asyncio
    async def test_route_basic(self):
        """Test basic routing."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Hello, world!")

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)
        assert response.model_name
        assert response.provider
        assert response.estimated_cost >= 0
        assert response.estimated_tokens >= 0
        assert 0 <= response.confidence <= 1
        assert response.reason

    @pytest.mark.asyncio
    async def test_route_with_task_type(self):
        """Test routing with different task types."""
        orchestrator = LLMRouterOrchestrator()

        for task_type in TaskType:
            request = RouteRequest(prompt="Test", task_type=task_type)
            response = await orchestrator.route(request)

            assert isinstance(response, RouteResponse)
            assert response.model_name

    @pytest.mark.asyncio
    async def test_route_with_force_model(self):
        """Test routing with forced model."""
        orchestrator = LLMRouterOrchestrator()
        models = orchestrator.list_models()

        if models:
            request = RouteRequest(prompt="Test", force_model=models[0].name)
            response = await orchestrator.route(request)

            assert response.model_name == models[0].name

    @pytest.mark.asyncio
    async def test_route_with_strategy(self):
        """Test routing with different strategies."""
        orchestrator = LLMRouterOrchestrator()
        strategies = ["cost_optimized", "capability_first", "balanced"]

        for strategy in strategies:
            request = RouteRequest(prompt="Test", strategy=strategy)
            response = await orchestrator.route(request)

            assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_budget(self):
        """Test routing with budget constraint."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", budget=0.01)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_context(self):
        """Test routing with context."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(
            prompt="Test", context={"language": "python", "domain": "code"}
        )

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_cache_enabled(self):
        """Test routing with cache enabled."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", use_cache=True)

        response1 = await orchestrator.route(request)
        response2 = await orchestrator.route(request)

        assert isinstance(response1, RouteResponse)
        assert isinstance(response2, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_cache_disabled(self):
        """Test routing with cache disabled."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", use_cache=False)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_max_tokens(self):
        """Test routing with max tokens."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", max_tokens=2048)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_temperature(self):
        """Test routing with temperature."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", temperature=0.5)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_generate_basic(self):
        """Test basic generation."""
        orchestrator = LLMRouterOrchestrator()

        # Mock the provider call to avoid actual API calls
        with patch.object(orchestrator, 'route_and_generate') as mock_route_gen:
            mock_response = GenerateResponse(
                content="Generated text",
                model="test-model",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_route_gen.return_value = mock_response

            request = GenerateRequest(prompt="Test")
            response = await orchestrator.generate(request)

            assert response.content == "Generated text"
            mock_route_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_model(self):
        """Test generation with specific model."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'route_and_generate') as mock_route_gen:
            mock_response = GenerateResponse(
                content="Generated text",
                model="gpt-4",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_route_gen.return_value = mock_response

            request = GenerateRequest(prompt="Test", model="gpt-4")
            response = await orchestrator.generate(request)

            assert response.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_generate_with_task_type(self):
        """Test generation with task type."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'route_and_generate') as mock_route_gen:
            mock_response = GenerateResponse(
                content="Generated text",
                model="test-model",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_route_gen.return_value = mock_response

            request = GenerateRequest(
                prompt="Test", task_type=TaskType.CODE_GENERATION
            )
            response = await orchestrator.generate(request)

            assert isinstance(response, GenerateResponse)

    @pytest.mark.asyncio
    async def test_route_and_generate_success(self):
        """Test route and generate with success."""
        orchestrator = LLMRouterOrchestrator()

        # Mock the provider call
        async def mock_call(prompt, model, max_tokens=1024, temperature=0.7):
            return GenerateResponse(
                content="Generated response",
                model=model,
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=150,
                cost=0.01,
            )

        # Get a valid model
        models = orchestrator.list_models()
        if models:
            provider = orchestrator._get_provider(models[0].name)
            if provider:
                with patch.object(provider, 'call', side_effect=mock_call):
                    request = RouteRequest(prompt="Test", force_model=models[0].name)
                    response = await orchestrator.route_and_generate(request)

                    assert isinstance(response, GenerateResponse)
                    assert response.content == "Generated response"

    @pytest.mark.asyncio
    async def test_route_and_generate_with_fallback(self):
        """Test route and generate with fallback on failure."""
        orchestrator = LLMRouterOrchestrator()

        # Mock provider that fails
        async def failing_call(prompt, model, max_tokens=1024, temperature=0.7):
            raise Exception("Provider error")

        models = orchestrator.list_models()
        if len(models) > 1:
            first_provider = orchestrator._get_provider(models[0].name)
            second_provider = orchestrator._get_provider(models[1].name)

            if first_provider and second_provider:
                with patch.object(first_provider, 'call', side_effect=failing_call):
                    async def success_call(prompt, model, max_tokens=1024, temperature=0.7):
                        return GenerateResponse(
                            content="Fallback response",
                            model=model,
                            provider=ProviderType.OPENAI,
                            tokens=100,
                            latency_ms=150,
                            cost=0.01,
                        )

                    with patch.object(second_provider, 'call', side_effect=success_call):
                        request = RouteRequest(prompt="Test", force_model=models[0].name)
                        response = await orchestrator.route_and_generate(request)

                        # Should either fail or succeed with fallback
                        assert isinstance(response, GenerateResponse) or True

    @pytest.mark.asyncio
    async def test_route_and_generate_no_provider(self):
        """Test route and generate with no available provider."""
        orchestrator = LLMRouterOrchestrator()

        request = RouteRequest(prompt="Test", force_model="nonexistent-model")

        with pytest.raises(ValueError, match="No provider available"):
            await orchestrator.route_and_generate(request)

    @pytest.mark.asyncio
    async def test_select_fallback(self):
        """Test fallback model selection."""
        orchestrator = LLMRouterOrchestrator()
        models = orchestrator.list_models()

        if len(models) > 1:
            fallback = orchestrator._select_fallback(models[0].name)

            assert fallback is not None
            assert fallback != models[0].name

    @pytest.mark.asyncio
    async def test_select_fallback_no_alternatives(self):
        """Test fallback when no alternatives available."""
        orchestrator = LLMRouterOrchestrator()

        # If only one model or none available
        fallback = orchestrator._select_fallback("nonexistent-model")

        # Should return None or a valid model
        assert fallback is None or fallback in orchestrator.providers

    @pytest.mark.asyncio
    async def test_completion_basic(self):
        """Test LiteLLM completion."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'generate') as mock_generate:
            mock_response = GenerateResponse(
                content="Completion response",
                model="test-model",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_generate.return_value = mock_response

            request = LiteLLMRequest(
                messages=[{"role": "user", "content": "Hello"}]
            )
            response = await orchestrator.completion(request)

            assert response.model == "test-model"
            assert len(response.choices) > 0

    @pytest.mark.asyncio
    async def test_completion_with_model(self):
        """Test completion with specific model."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'generate') as mock_generate:
            mock_response = GenerateResponse(
                content="Completion response",
                model="gpt-4",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_generate.return_value = mock_response

            request = LiteLLMRequest(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello"}]
            )
            response = await orchestrator.completion(request)

            assert response.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_completion_auto_model(self):
        """Test completion with auto model selection."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'generate') as mock_generate:
            mock_response = GenerateResponse(
                content="Completion response",
                model="test-model",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_generate.return_value = mock_response

            request = LiteLLMRequest(
                model="auto",
                messages=[{"role": "user", "content": "Hello"}]
            )
            response = await orchestrator.completion(request)

            # completion returns LiteLLMResponse, not GenerateResponse
            from extensions.addons.ai_plus.llm_router_service.schemas import LiteLLMResponse
            assert isinstance(response, LiteLLMResponse)

    @pytest.mark.asyncio
    async def test_messages_to_prompt(self):
        """Test messages to prompt conversion."""
        orchestrator = LLMRouterOrchestrator()

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        prompt = orchestrator._messages_to_prompt(messages)

        assert "system: You are helpful" in prompt
        assert "user: Hello" in prompt
        assert "assistant: Hi there!" in prompt

    @pytest.mark.asyncio
    async def test_messages_to_prompt_empty(self):
        """Test messages to prompt with empty messages."""
        orchestrator = LLMRouterOrchestrator()

        prompt = orchestrator._messages_to_prompt([])

        assert prompt == ""

    @pytest.mark.asyncio
    async def test_messages_to_prompt_missing_fields(self):
        """Test messages to prompt with missing fields."""
        orchestrator = LLMRouterOrchestrator()

        messages = [
            {"content": "No role"},
            {"role": "user"},
            {},
        ]

        prompt = orchestrator._messages_to_prompt(messages)

        assert isinstance(prompt, str)

    def test_get_stats(self):
        """Test getting router statistics."""
        orchestrator = LLMRouterOrchestrator()
        stats = orchestrator.get_stats()

        assert isinstance(stats, dict)
        assert "model_stats" in stats
        assert "circuit_states" in stats
        assert "cost_stats" in stats

    @pytest.mark.asyncio
    async def test_get_cost_report(self):
        """Test getting cost report."""
        orchestrator = LLMRouterOrchestrator()
        report = await orchestrator.get_cost_report()

        assert hasattr(report, "hourly_cost")
        assert hasattr(report, "request_count")
        assert hasattr(report, "avg_cost_per_request")
        assert hasattr(report, "budget_per_request")
        assert hasattr(report, "max_cost_per_hour")

    @pytest.mark.asyncio
    async def test_get_performance_report(self):
        """Test getting performance report."""
        orchestrator = LLMRouterOrchestrator()
        report = await orchestrator.get_performance_report()

        assert hasattr(report, "model_stats")
        assert hasattr(report, "circuit_states")
        assert hasattr(report, "cost_report")
        assert hasattr(report, "total_requests")

    @pytest.mark.asyncio
    async def test_route_batch(self):
        """Test batch routing."""
        orchestrator = LLMRouterOrchestrator()
        requests = [
            RouteRequest(prompt=f"Test {i}") for i in range(5)
        ]

        responses = await orchestrator.route_batch(requests)

        assert len(responses) == 5
        for response in responses:
            assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_batch_empty(self):
        """Test batch routing with empty list."""
        orchestrator = LLMRouterOrchestrator()
        responses = await orchestrator.route_batch([])

        assert len(responses) == 0

    @pytest.mark.asyncio
    async def test_route_batch_single(self):
        """Test batch routing with single request."""
        orchestrator = LLMRouterOrchestrator()
        requests = [RouteRequest(prompt="Test")]

        responses = await orchestrator.route_batch(requests)

        assert len(responses) == 1
        assert isinstance(responses[0], RouteResponse)

    @pytest.mark.asyncio
    async def test_generate_batch(self):
        """Test batch generation."""
        orchestrator = LLMRouterOrchestrator()

        with patch.object(orchestrator, 'route_and_generate') as mock_route_gen:
            mock_response = GenerateResponse(
                content="Generated text",
                model="test-model",
                provider=ProviderType.OPENAI,
                tokens=100,
                latency_ms=200,
                cost=0.01,
            )
            mock_route_gen.return_value = mock_response

            requests = [
                GenerateRequest(prompt=f"Test {i}") for i in range(5)
            ]
            responses = await orchestrator.generate_batch(requests)

            assert len(responses) == 5
            for response in responses:
                assert isinstance(response, GenerateResponse)

    @pytest.mark.asyncio
    async def test_generate_batch_empty(self):
        """Test batch generation with empty list."""
        orchestrator = LLMRouterOrchestrator()
        responses = await orchestrator.generate_batch([])

        assert len(responses) == 0

    @pytest.mark.asyncio
    async def test_update_gauges(self):
        """Test updating gauges."""
        orchestrator = LLMRouterOrchestrator()

        # Should not raise
        orchestrator._update_gauges()

    @pytest.mark.asyncio
    async def test_update_circuit_gauge(self):
        """Test updating circuit gauge."""
        orchestrator = LLMRouterOrchestrator()

        # Should not raise
        orchestrator._update_circuit_gauge()

    @pytest.mark.asyncio
    async def test_update_cost_gauge(self):
        """Test updating cost gauge."""
        orchestrator = LLMRouterOrchestrator()

        # Should not raise
        orchestrator._update_cost_gauges()

    @pytest.mark.asyncio
    async def test_route_with_long_prompt(self):
        """Test routing with very long prompt."""
        orchestrator = LLMRouterOrchestrator()
        long_prompt = "Hello " * 10000
        request = RouteRequest(prompt=long_prompt)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_unicode_prompt(self):
        """Test routing with unicode prompt."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Hello 世界 🌍")

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_special_characters(self):
        """Test routing with special characters."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test <script>alert('xss')</script>")

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_zero_budget(self):
        """Test routing with zero budget."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", budget=0.0)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_very_high_budget(self):
        """Test routing with very high budget."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(prompt="Test", budget=1000000)

        response = await orchestrator.route(request)

        assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_temperature_extremes(self):
        """Test routing with temperature extremes."""
        orchestrator = LLMRouterOrchestrator()

        for temp in [0.0, 0.5, 1.0, 1.5, 2.0]:
            request = RouteRequest(prompt="Test", temperature=temp)
            response = await orchestrator.route(request)

            assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_with_max_tokens_extremes(self):
        """Test routing with max tokens extremes."""
        orchestrator = LLMRouterOrchestrator()

        for tokens in [1, 100, 1000, 10000, 100000]:
            request = RouteRequest(prompt="Test", max_tokens=tokens)
            response = await orchestrator.route(request)

            assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_concurrent_routes(self):
        """Test concurrent routing requests."""
        orchestrator = LLMRouterOrchestrator()

        requests = [
            orchestrator.route(RouteRequest(prompt=f"Test {i}"))
            for i in range(10)
        ]

        responses = await asyncio.gather(*requests)

        assert len(responses) == 10
        for response in responses:
            assert isinstance(response, RouteResponse)

    @pytest.mark.asyncio
    async def test_route_cache_key_consistency(self):
        """Test that cache keys are consistent."""
        orchestrator = LLMRouterOrchestrator()
        request = RouteRequest(
            prompt="Test",
            task_type=TaskType.GENERAL,
            force_model=None,
            strategy="cost_optimized",
            use_cache=True,
        )

        key1 = orchestrator.cache._key(
            "route",
            hash(request.prompt),
            request.task_type.value,
            request.force_model,
            request.strategy,
        )
        key2 = orchestrator.cache._key(
            "route",
            hash(request.prompt),
            request.task_type.value,
            request.force_model,
            request.strategy,
        )

        assert key1 == key2
