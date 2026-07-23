# -*- coding: utf-8 -*-
"""
Cost-Optimized Routing
Implements cost-aware model selection strategies
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger

from .capability_evaluator import TaskType


@dataclass
class RoutingDecision:
    """Routing decision with cost analysis"""

    model_name: str
    estimated_cost: float
    estimated_tokens: int
    confidence: float
    reason: str


class CostOptimizer:
    """
    Optimizes routing decisions based on cost
    """

    def __init__(
        self,
        model_configs: List[Dict[str, Any]],
        budget_per_request: Optional[float] = None,
        max_cost_per_hour: Optional[float] = None,
    ):
        """
        Initialize cost optimizer

        Args:
            model_configs: Model configurations
            budget_per_request: Max cost per request
            max_cost_per_hour: Max cost per hour
        """
        self.model_configs = model_configs
        self.budget_per_request = budget_per_request
        self.max_cost_per_hour = max_cost_per_hour
        self._hourly_cost = 0.0
        self._request_count = 0
        self._hour_start: Optional[float] = None

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English
        return len(text) // 4

    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int = 0) -> float:
        """
        Estimate cost for model usage

        Args:
            model_name: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        model_config = self._find_model_config(model_name)
        if not model_config:
            return 0.0

        cost_per_1k: float = model_config.get("cost_per_1k", 0.0)
        total_tokens: float = input_tokens + output_tokens

        return (total_tokens / 1000.0) * cost_per_1k

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
            model_config = self._find_model_config(model_cap.model_name)
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

    def check_budget(self, estimated_cost: float) -> bool:
        """
        Check if cost is within budget

        Args:
            estimated_cost: Estimated cost

        Returns:
            True if within budget
        """
        if self.budget_per_request and estimated_cost > self.budget_per_request:
            logger.warning(f"Cost {estimated_cost} exceeds budget {self.budget_per_request}")
            return False

        if self.max_cost_per_hour:
            self._update_hourly_tracking()
            if self._hourly_cost + estimated_cost > self.max_cost_per_hour:
                logger.warning(f"Hourly cost would exceed {self.max_cost_per_hour}")
                return False

        return True

    def _update_hourly_tracking(self) -> None:
        """Update hourly cost tracking"""
        import time

        now = time.time()
        if self._hour_start is None:
            self._hour_start = now
        elif now - self._hour_start > 3600:
            # Reset hourly tracking
            self._hourly_cost = 0.0
            self._request_count = 0
            self._hour_start = now

    def record_cost(self, actual_cost: float) -> None:
        """
        Record actual cost after request

        Args:
            actual_cost: Actual cost incurred
        """
        self._hourly_cost += actual_cost
        self._request_count += 1

    def get_hourly_stats(self) -> Dict[str, Any]:
        """Get hourly cost statistics"""
        return {
            "hourly_cost": self._hourly_cost,
            "request_count": self._request_count,
            "avg_cost_per_request": (
                self._hourly_cost / self._request_count if self._request_count else 0
            ),
        }

    def _find_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Find model configuration"""
        for config in self.model_configs:
            if config.get("model") == model_name or config.get("name") == model_name:
                return config
        return None
