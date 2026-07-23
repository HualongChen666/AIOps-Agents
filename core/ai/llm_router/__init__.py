# -*- coding: utf-8 -*-
"""
Enhanced LLM Router Module
"""

from typing import Any, Optional

from .capability_evaluator import CapabilityEvaluator, ModelCapability, TaskType
from .cost_optimizer import CostOptimizer, RoutingDecision
from .enhanced_router import EnhancedLLMRouter
from .load_balancer import CircuitBreaker, CircuitState, LoadBalancer, ModelStats

__all__ = [
    "CapabilityEvaluator",
    "TaskType",
    "ModelCapability",
    "CostOptimizer",
    "RoutingDecision",
    "LoadBalancer",
    "CircuitBreaker",
    "CircuitState",
    "ModelStats",
    "EnhancedLLMRouter",
    "get_llm_router",
]


_llm_router_instance: Optional[EnhancedLLMRouter] = None


def get_llm_router() -> EnhancedLLMRouter:
    """Return the global singleton Enhanced LLM Router.

    The router is lazily initialized using ``LLM_ROUTER_MODELS`` from the
    project ``config`` module.
    """
    global _llm_router_instance
    if _llm_router_instance is None:
        from config import LLM_ROUTER_MODELS  # noqa: E402

        _llm_router_instance = EnhancedLLMRouter(
            model_configs=LLM_ROUTER_MODELS,
            strategy="cost_optimized",
        )
    return _llm_router_instance


def reset_llm_router() -> None:
    """Reset the global singleton (useful for testing)."""
    global _llm_router_instance
    _llm_router_instance = None
