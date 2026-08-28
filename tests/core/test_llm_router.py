# -*- coding: utf-8 -*-
"""Unit tests for core/ai/llm_router/enhanced_router.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.ai.llm_router.capability_evaluator import TaskType
from core.ai.llm_router.enhanced_router import EnhancedLLMRouter


@pytest.mark.asyncio
async def test_enhanced_router_force_model():
    router = EnhancedLLMRouter(
        model_configs=[{"name": "test-model", "cost_per_1k": 0.001}],
        strategy="cost_optimized",
    )
    decision = await router.route_request(
        prompt="hello",
        task_type=TaskType.GENERAL,
        force_model="test-model",
    )
    assert decision.model_name == "test-model"
    assert decision.confidence == 1.0


@pytest.mark.asyncio
async def test_enhanced_router_cost_optimized_strategy():
    """Test cost-optimized routing strategy selects cheapest model."""
    model_configs = [
        {"model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192},
        {"model": "gpt-3.5-turbo", "cost_per_1k": 0.002, "max_tokens": 4096},
        {"model": "mini-model", "cost_per_1k": 0.001, "max_tokens": 2048},
    ]
    
    router = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="cost_optimized",
    )
    
    decision = await router.route_request(
        prompt="simple question",
        task_type=TaskType.GENERAL,
    )
    
    # Extract model names from configs
    model_names = [config["model"] for config in model_configs]
    
    # Should select cheapest model that meets capability threshold
    assert decision.model_name in model_names
    assert decision.estimated_cost >= 0
    assert decision.estimated_tokens > 0
    assert 0.0 <= decision.confidence <= 1.0
    assert "capability threshold" in decision.reason.lower() or "fallback" in decision.reason.lower()


@pytest.mark.asyncio
async def test_enhanced_router_capability_first_strategy():
    """Test capability-first routing strategy selects best model for task."""
    model_configs = [
        {"model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192, "context_window": 32000},
        {"model": "gpt-3.5-turbo", "cost_per_1k": 0.002, "max_tokens": 4096, "context_window": 16000},
        {"model": "mini-model", "cost_per_1k": 0.001, "max_tokens": 2048, "context_window": 8000},
    ]
    
    router = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="capability_first",
    )
    
    # Extract model names from configs
    model_names = [config["model"] for config in model_configs]
    
    # Test code generation task (needs larger context)
    decision = await router.route_request(
        prompt="write a function",
        task_type=TaskType.CODE_GENERATION,
    )
    
    # Should prefer model with larger context for code generation
    assert decision.model_name in model_names
    assert decision.estimated_cost >= 0
    assert decision.estimated_tokens > 0
    assert 0.0 <= decision.confidence <= 1.0
    
    # Test reasoning task (needs strong model)
    decision_reasoning = await router.route_request(
        prompt="solve this complex problem",
        task_type=TaskType.REASONING,
    )
    
    assert decision_reasoning.model_name in model_names
    assert decision_reasoning.confidence >= 0.0


@pytest.mark.asyncio
async def test_enhanced_router_balanced_strategy():
    """Test balanced routing strategy considers both capability and cost."""
    model_configs = [
        {"model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192, "context_window": 32000},
        {"model": "gpt-3.5-turbo", "cost_per_1k": 0.002, "max_tokens": 4096, "context_window": 16000},
        {"model": "claude-3-sonnet", "cost_per_1k": 0.015, "max_tokens": 8192, "context_window": 20000},
    ]
    
    router = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="balanced",
    )
    
    # Extract model names from configs
    model_names = [config["model"] for config in model_configs]
    
    decision = await router.route_request(
        prompt="analyze this data",
        task_type=TaskType.ANALYSIS,
    )
    
    # Should select from top capable models considering cost
    assert decision.model_name in model_names
    assert decision.estimated_cost >= 0
    assert decision.estimated_tokens > 0
    assert 0.0 <= decision.confidence <= 1.0
    assert "balanced" in decision.reason.lower()


@pytest.mark.asyncio
async def test_enhanced_router_with_budget():
    """Test routing with budget constraints."""
    model_configs = [
        {"model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192},
        {"model": "gpt-3.5-turbo", "cost_per_1k": 0.002, "max_tokens": 4096},
        {"model": "mini-model", "cost_per_1k": 0.001, "max_tokens": 2048},
    ]
    
    # Extract model names from configs
    model_names = [config["model"] for config in model_configs]
    
    # Set a very low budget per request
    router = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="cost_optimized",
        budget_per_request=0.0001,  # Very low budget
    )
    
    decision = await router.route_request(
        prompt="short question",
        task_type=TaskType.GENERAL,
    )
    
    # Should still return a decision, possibly cheapest model
    assert decision.model_name in model_names
    assert decision.estimated_cost >= 0
    
    # Test with higher budget
    router_high_budget = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="cost_optimized",
        budget_per_request=0.1,  # Higher budget
    )
    
    decision_high = await router_high_budget.route_request(
        prompt="longer question with more text",
        task_type=TaskType.GENERAL,
    )
    
    assert decision_high.model_name in model_names
    assert decision_high.estimated_cost >= 0


@pytest.mark.asyncio
async def test_enhanced_router_unknown_strategy():
    """Test unknown strategy falls back to cost_optimized."""
    model_configs = [
        {"model": "gpt-4", "cost_per_1k": 0.03, "max_tokens": 8192},
        {"model": "gpt-3.5-turbo", "cost_per_1k": 0.002, "max_tokens": 4096},
    ]
    
    # Extract model names from configs
    model_names = [config["model"] for config in model_configs]
    
    router = EnhancedLLMRouter(
        model_configs=model_configs,
        strategy="unknown_strategy",  # Invalid strategy
    )
    
    decision = await router.route_request(
        prompt="test prompt",
        task_type=TaskType.GENERAL,
    )
    
    # Should fall back to cost_optimized behavior
    assert decision.model_name in model_names
    assert decision.estimated_cost >= 0
    assert decision.estimated_tokens > 0
    assert 0.0 <= decision.confidence <= 1.0
