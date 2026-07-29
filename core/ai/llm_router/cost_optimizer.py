# -*- coding: utf-8 -*-
"""
Cost-Optimized Routing
Implements cost-aware model selection strategies
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from core.llm_cost_monitor import LLMCostMonitor

from .capability_evaluator import TaskType


@dataclass
class RoutingDecision:
    """Routing decision with cost analysis"""

    model_name: str
    estimated_cost: float
    estimated_tokens: int
    confidence: float
    reason: str


class CostOptimizer(LLMCostMonitor):
    """
    基于成本的模型选择优化器。

    继承自 ``LLMCostMonitor``，复用其定价、预算检查与费用累计能力，
    并在此基础上实现按能力阈值选择最便宜模型的路由逻辑。
    """

    def __init__(
        self,
        model_configs: List[Dict[str, Any]],
        budget_per_request: Optional[float] = None,
        max_cost_per_hour: Optional[float] = None,
        max_cost_per_day: Optional[float] = None,
    ):
        """
        Initialize cost optimizer

        Args:
            model_configs: Model configurations
            budget_per_request: Max cost per request
            max_cost_per_hour: Max cost per hour
            max_cost_per_day: Max cost per day
        """
        super().__init__(
            model_configs=model_configs,
            budget_per_request=budget_per_request,
            max_cost_per_hour=max_cost_per_hour,
            max_cost_per_day=max_cost_per_day,
        )

    def _find_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """查找模型配置（向后兼容的别名）。"""
        return self.get_model_config(model_name)

    def select_cheapest_model(
        self, prompt: str, task_type: TaskType = TaskType.GENERAL, min_capability_score: float = 0.5
    ) -> Optional[RoutingDecision]:
        """
        Select cheapest model that meets capability threshold

        Args:
            prompt: Input prompt
            task_type: Task type
            min_capability_score: Minimum capability score

        Returns:
            Routing decision
        """
        from .capability_evaluator import CapabilityEvaluator

        evaluator = CapabilityEvaluator(self.model_configs)
        estimated_tokens = self.estimate_tokens(prompt)

        # Get ranked models
        ranked = evaluator.rank_models_for_task(task_type)

        # Filter by capability score
        qualified = [m for m in ranked if m.score >= min_capability_score]

        if not qualified:
            logger.warning(f"No models meet capability threshold {min_capability_score}")
            # Use best available
            qualified = ranked[:1]

        # Select cheapest among qualified
        best_model = None
        best_cost = float("inf")

        for model_cap in qualified:
            model_config = self.get_model_config(model_cap.model_name)
            if model_config:
                cost = self.estimate_cost(model_cap.model_name, estimated_tokens)
                if cost < best_cost:
                    best_cost = cost
                    best_model = model_config

        if best_model:
            return RoutingDecision(
                model_name=best_model["model"],
                estimated_cost=best_cost,
                estimated_tokens=estimated_tokens,
                confidence=qualified[0].score,
                reason=f"Cheapest model meeting capability threshold {min_capability_score}",
            )

        return None
