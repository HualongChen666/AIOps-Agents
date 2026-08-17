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
