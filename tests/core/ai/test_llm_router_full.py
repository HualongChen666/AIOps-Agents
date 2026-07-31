# -*- coding: utf-8 -*-
"""
Comprehensive tests for core/ai/llm_router modules.
"""

import asyncio

import pytest

pytestmark = pytest.mark.smoke
from core.ai.llm_router.capability_evaluator import (
    CapabilityEvaluator,
    ModelCapability,
    TaskType,
)
from core.ai.llm_router.cost_optimizer import CostOptimizer, RoutingDecision
from core.ai.llm_router.enhanced_router import EnhancedLLMRouter

# ----------------------------------------------------------------------
# CapabilityEvaluator
# ----------------------------------------------------------------------


class TestCapabilityEvaluator:
    @pytest.fixture
    def model_configs(self):
        return [
            {"model": "gpt-4", "max_tokens": 8192, "context_window": 32000},
            {"model": "gpt-3.5", "max_tokens": 4096, "context_window": 16000, "cost_per_1k": 0.002},
            {"model": "gemini-pro", "max_tokens": 32768, "context_window": 128000},
        ]

    def test_task_type_enum(self):
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.ANALYSIS.value == "analysis"

    def test_model_capability_dataclass(self):
        cap = ModelCapability("gpt-4", TaskType.QUESTION_ANSWERING, 0.9, {})
        assert cap.model_name == "gpt-4"

    def test_evaluate_model_caching(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        score1 = evaluator.evaluate_model("gpt-4", TaskType.CODE_GENERATION)
        score2 = evaluator.evaluate_model("gpt-4", TaskType.CODE_GENERATION)
        assert score1 == score2
        assert "gpt-4" in evaluator._capability_cache

    def test_evaluate_missing_model(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        score = evaluator.evaluate_model("unknown", TaskType.GENERAL)
        assert score == 0.5

    def test_base_score_top_tier(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        assert evaluator._get_model_base_score("gpt-4") == 0.9
        assert evaluator._get_model_base_score("claude-3-opus") == 0.9

    def test_base_score_mid_tier(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        assert evaluator._get_model_base_score("gpt-3.5") == 0.75

    def test_base_score_budget(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        assert evaluator._get_model_base_score("gpt-mini") == 0.6

    def test_base_score_default(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        assert evaluator._get_model_base_score("other-model") == 0.7

    def test_code_generation_score_large_context(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        score = evaluator._calculate_capability_score(model_configs[0], TaskType.CODE_GENERATION)
        assert score == 1.0

    def test_code_generation_score_small_context(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        config = {"model": "small", "max_tokens": 1000, "context_window": 4000}
        score = evaluator._calculate_capability_score(config, TaskType.CODE_GENERATION)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_analysis_score_gpt4(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        score = evaluator._calculate_capability_score(model_configs[0], TaskType.ANALYSIS)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_reasoning_score_opus(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        config = {"model": "claude-3-opus", "max_tokens": 8192}
        score = evaluator._calculate_capability_score(config, TaskType.REASONING)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_rank_models_for_task(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        ranked = evaluator.rank_models_for_task(TaskType.CODE_GENERATION)
        assert len(ranked) == 3
        assert ranked[0].score >= ranked[1].score >= ranked[2].score

    def test_get_best_model_for_task(self, model_configs):
        evaluator = CapabilityEvaluator(model_configs)
        best = evaluator.get_best_model_for_task(TaskType.CODE_GENERATION)
        assert best is not None

    def test_get_best_model_for_task_empty(self):
        evaluator = CapabilityEvaluator([])
        assert evaluator.get_best_model_for_task(TaskType.GENERAL) is None


# ----------------------------------------------------------------------
# CostOptimizer
# ----------------------------------------------------------------------


class TestCostOptimizer:
    @pytest.fixture
    def model_configs(self):
        return [
            {"model": "gpt-4", "cost_per_1k": 0.03, "context_window": 32000},
            {"model": "gpt-3.5", "cost_per_1k": 0.002, "context_window": 16000},
            {"model": "cheap", "cost_per_1k": 0.001, "context_window": 16000},
        ]

    def test_routing_decision_dataclass(self):
        decision = RoutingDecision("gpt-4", 0.1, 100, 0.9, "reason")
        assert decision.model_name == "gpt-4"

    def test_estimate_tokens(self, model_configs):
        opt = CostOptimizer(model_configs)
        assert opt.estimate_tokens("hello world") == 2

    def test_estimate_cost(self, model_configs):
        opt = CostOptimizer(model_configs)
        cost = opt.estimate_cost("gpt-4", 1000)
        assert cost == pytest.approx(0.03, abs=0.001)

    def test_estimate_cost_unknown_model(self, model_configs):
        opt = CostOptimizer(model_configs)
        assert opt.estimate_cost("unknown", 1000) == 0.0

    def test_select_cheapest_model(self, model_configs):
        opt = CostOptimizer(model_configs)
        decision = opt.select_cheapest_model("test", TaskType.GENERAL)
        assert decision is not None
        assert decision.model_name == "cheap"

    def test_select_cheapest_model_respects_capability_threshold(self, model_configs):
        opt = CostOptimizer(model_configs)
        # high threshold may exclude cheap models
        decision = opt.select_cheapest_model("test", TaskType.GENERAL, min_capability_score=0.95)
        assert decision is not None

    def test_select_cheapest_model_empty_configs(self):
        opt = CostOptimizer([])
        assert opt.select_cheapest_model("test") is None

    def test_check_budget_within(self, model_configs):
        opt = CostOptimizer(model_configs, budget_per_request=1.0)
        assert opt.check_budget(0.5) is True

    def test_check_budget_exceeds_request(self, model_configs):
        opt = CostOptimizer(model_configs, budget_per_request=0.01)
        assert opt.check_budget(0.1) is False

    def test_check_budget_hourly(self, model_configs):
        opt = CostOptimizer(model_configs, max_cost_per_hour=0.1)
        opt._hourly_cost = 0.05
        assert opt.check_budget(0.05) is True
        assert opt.check_budget(0.06) is False

    def test_record_cost_and_stats(self, model_configs):
        opt = CostOptimizer(model_configs)
        opt.record_cost(0.1)
        opt.record_cost(0.2)
        stats = opt.get_hourly_stats()
        assert stats["hourly_cost"] == pytest.approx(0.3, abs=0.01)
        assert stats["request_count"] == 2

    def test_hourly_tracking_reset(self, model_configs):
        import time

        opt = CostOptimizer(model_configs, max_cost_per_hour=10.0)
        opt._hour_start = time.time() - 3700
        opt._hourly_cost = 5.0
        opt._update_hourly_tracking()
        assert opt._hourly_cost == 0.0
        assert opt._request_count == 0

    def test_find_model_config_by_name(self, model_configs):
        opt = CostOptimizer(model_configs)
        config = opt._find_model_config("gpt-4")
        assert config["model"] == "gpt-4"


# ----------------------------------------------------------------------
# EnhancedLLMRouter
# ----------------------------------------------------------------------


class TestEnhancedLLMRouter:
    @pytest.fixture
    def model_configs(self):
        return [
            {"model": "gpt-4", "cost_per_1k": 0.03, "context_window": 32000},
            {"model": "gpt-3.5", "cost_per_1k": 0.002, "context_window": 16000},
        ]

    @pytest.fixture
    def router(self, model_configs):
        return EnhancedLLMRouter(model_configs, strategy="cost_optimized")

    def test_initialization(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="balanced")
        assert router.strategy == "balanced"
        assert router.capability_evaluator is not None
        assert router.cost_optimizer is not None
        assert router.load_balancer is not None

    def test_force_model(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="cost_optimized")
        decision = asyncio.run(router.route_request("test", force_model="gpt-4"))
        assert decision.model_name == "gpt-4"
        assert decision.confidence == 1.0

    def test_force_model_unavailable(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="cost_optimized")
        # open circuit for gpt-4 so it is unavailable
        router.load_balancer.circuit_breakers["gpt-4"].state = "open"
        decision = asyncio.run(router.route_request("test", force_model="gpt-4"))
        assert decision.model_name != "gpt-4"

    def test_cost_optimized_strategy(self, router):
        decision = asyncio.run(router.route_request("test"))
        assert decision.model_name == "gpt-3.5"
        assert decision.estimated_tokens > 0

    def test_capability_first_strategy(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="capability_first")
        decision = asyncio.run(router.route_request("test", TaskType.CODE_GENERATION))
        assert decision.model_name == "gpt-4"

    def test_balanced_strategy(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="balanced")
        decision = asyncio.run(router.route_request("test", TaskType.CODE_GENERATION))
        assert decision.model_name in ["gpt-4", "gpt-3.5"]

    def test_unknown_strategy_fallback(self, model_configs):
        router = EnhancedLLMRouter(model_configs, strategy="unknown")
        decision = asyncio.run(router.route_request("test"))
        assert decision is not None

    def test_cost_optimized_routing_no_models(self):
        router = EnhancedLLMRouter([])
        with pytest.raises(ValueError, match="No models available"):
            asyncio.run(router.route_request("test"))

    def test_record_success(self, router):
        router.record_success("gpt-4", 0.5, 0.1)
        stats = router.get_router_stats()
        assert "model_stats" in stats
        assert "cost_stats" in stats

    def test_record_failure(self, router):
        router.record_failure("gpt-4", "timeout")
        stats = router.get_router_stats()
        assert stats["model_stats"]["gpt-4"].failed_requests == 1

    def test_is_model_available(self, router):
        assert router._is_model_available("gpt-4") is True
        router.load_balancer.circuit_breakers["gpt-4"].state = "open"
        assert router._is_model_available("gpt-4") is False

    def test_find_model_config(self, router):
        assert router._find_model_config("gpt-4") is not None
        assert router._find_model_config("missing") is None

    def test_route_request_no_qualified_uses_fallback(self, router):
        # Make capability evaluator return no qualified models
        router.cost_optimizer.budget_per_request = 0.0
        decision = asyncio.run(router.route_request("test"))
        assert decision is not None
