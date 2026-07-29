# -*- coding: utf-8 -*-
"""
Enhanced LLM Router Module
"""

from typing import Optional

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

    The router is lazily initialized using the centralized ``LLMCostMonitor``
    for model catalog and cost budgets.
    """
    global _llm_router_instance
    if _llm_router_instance is None:
        from core.llm_cost_monitor import (  # noqa: E402
            get_llm_cost_monitor,
            set_llm_cost_monitor,
        )

        cost_monitor = get_llm_cost_monitor()
        _llm_router_instance = EnhancedLLMRouter(
            model_configs=cost_monitor.model_configs,
            strategy="cost_optimized",
            budget_per_request=cost_monitor.budget_per_request,
        )
        _llm_router_instance.cost_optimizer.max_cost_per_hour = cost_monitor.max_cost_per_hour
        _llm_router_instance.cost_optimizer.max_cost_per_day = cost_monitor.max_cost_per_day
        # 让 ai_engine 等模块共享同一个成本监控实例
        set_llm_cost_monitor(_llm_router_instance.cost_optimizer)
    return _llm_router_instance


def reset_llm_router() -> None:
    """Reset the global singleton (useful for testing)."""
    global _llm_router_instance
    _llm_router_instance = None
