# -*- coding: utf-8 -*-
"""
Enhanced LLM Router Tests
"""

import pytest

from core.ai.llm_router import (
    CapabilityEvaluator,
    CostOptimizer,
    EnhancedLLMRouter,
    LoadBalancer,
    TaskType,
)


class TestCapabilityEvaluator:
    """Test capability evaluator"""

    def test_init(self):
        """Test initialization"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        evaluator = CapabilityEvaluator(model_configs)
        assert evaluator.model_configs == model_configs

    def test_evaluate_model(self):
        """Test model evaluation"""
        model_configs = [{"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03}]
        evaluator = CapabilityEvaluator(model_configs)
        score = evaluator.evaluate_model("gpt-4", TaskType.CODE_GENERATION)
        assert 0.0 <= score <= 1.0

    def test_rank_models_for_task(self):
        """Test model ranking"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        evaluator = CapabilityEvaluator(model_configs)
        ranked = evaluator.rank_models_for_task(TaskType.ANALYSIS)
        assert len(ranked) == 2
        assert ranked[0].score >= ranked[1].score


class TestCostOptimizer:
    """Test cost optimizer"""

    def test_estimate_tokens(self):
        """Test token estimation"""
        model_configs = []
        optimizer = CostOptimizer(model_configs)
        tokens = optimizer.estimate_tokens("Hello world")
        assert tokens > 0

    def test_estimate_cost(self):
        """Test cost estimation"""
        model_configs = [{"model": "gpt-3.5-turbo", "cost_per_1k": 0.002}]
        optimizer = CostOptimizer(model_configs)
        cost = optimizer.estimate_cost("gpt-3.5-turbo", 1000, 500)
        assert cost == 0.003  # (1500 / 1000) * 0.002

    def test_select_cheapest_model(self):
        """Test cheapest model selection"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        optimizer = CostOptimizer(model_configs)
        decision = optimizer.select_cheapest_model("test prompt", TaskType.GENERAL)
        assert decision is not None
        assert decision.model_name in ["gpt-4", "gpt-3.5-turbo"]


class TestLoadBalancer:
    """Test load balancer"""

    def test_init(self):
        """Test initialization"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000},
        ]
        balancer = LoadBalancer(model_configs)
        assert len(balancer.model_stats) == 2

    def test_select_model(self):
        """Test model selection"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000},
        ]
        balancer = LoadBalancer(model_configs)
        model = balancer.select_model()
        assert model in ["gpt-4", "gpt-3.5-turbo"]

    def test_record_success(self):
        """Test recording success"""
        model_configs = [{"model": "gpt-4", "max_tokens": 8000}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_success("gpt-4", 0.5)
        stats = balancer.get_model_stats("gpt-4")
        assert stats.successful_requests == 1

    def test_record_failure(self):
        """Test recording failure"""
        model_configs = [{"model": "gpt-4", "max_tokens": 8000}]
        balancer = LoadBalancer(model_configs)
        balancer.record_request_failure("gpt-4", "test error")
        stats = balancer.get_model_stats("gpt-4")
        assert stats.failed_requests == 1

    def test_circuit_breaker(self):
        """Test circuit breaker"""
        model_configs = [{"model": "gpt-4", "max_tokens": 8000}]
        balancer = LoadBalancer(model_configs)

        # Record multiple failures
        for _ in range(6):
            balancer.record_request_failure("gpt-4", "error")

        # Circuit should be open
        model = balancer.select_model()
        assert model is None  # No models available


class TestEnhancedLLMRouter:
    """Test enhanced router"""

    def test_init(self):
        """Test initialization"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        router = EnhancedLLMRouter(model_configs, strategy="cost_optimized")
        assert router.strategy == "cost_optimized"

    @pytest.mark.asyncio
    async def test_route_request(self):
        """Test request routing"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        router = EnhancedLLMRouter(model_configs)
        decision = await router.route_request("test prompt", TaskType.GENERAL)
        assert decision is not None
        assert decision.model_name in ["gpt-4", "gpt-3.5-turbo"]

    @pytest.mark.asyncio
    async def test_force_model(self):
        """Test forced model selection"""
        model_configs = [
            {"model": "gpt-4", "max_tokens": 8000, "cost_per_1k": 0.03},
            {"model": "gpt-3.5-turbo", "max_tokens": 4000, "cost_per_1k": 0.002},
        ]
        router = EnhancedLLMRouter(model_configs)
        decision = await router.route_request("test prompt", TaskType.GENERAL, force_model="gpt-4")
        assert decision.model_name == "gpt-4"
