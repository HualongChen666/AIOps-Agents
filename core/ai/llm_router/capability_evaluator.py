# -*- coding: utf-8 -*-
"""
Model Capability Evaluator
Evaluates and scores LLM models for different tasks
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, cast

from loguru import logger


class TaskType(Enum):
    """Task type enumeration"""

    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    QUESTION_ANSWERING = "qa"
    REASONING = "reasoning"
    GENERAL = "general"


@dataclass
class ModelCapability:
    """Model capability score"""

    model_name: str
    task_type: TaskType
    score: float  # 0.0 to 1.0
    metadata: Dict[str, Any]


class CapabilityEvaluator:
    """
    Evaluates model capabilities for different tasks
    """

    def __init__(self, model_configs: List[Dict[str, Any]]):
        """
        Initialize capability evaluator

        Args:
            model_configs: List of model configurations
        """
        self.model_configs = model_configs
        self._capability_cache: Dict[str, Dict[TaskType, float]] = {}

    def evaluate_model(self, model_name: str, task_type: TaskType) -> float:
        """
        Evaluate model capability for task

        Args:
            model_name: Model name
            task_type: Task type

        Returns:
            Capability score (0.0 to 1.0)
        """
        # Check cache
        if model_name in self._capability_cache:
            if task_type in self._capability_cache[model_name]:
                return self._capability_cache[model_name][task_type]

        # Find model config
        model_config = None
        for config in self.model_configs:
            if config.get("model") == model_name or config.get("name") == model_name:
                model_config = config
                break

        if not model_config:
            logger.warning(f"Model config not found: {model_name}")
            return 0.5  # Default score

        # Calculate score based on model characteristics
        score = self._calculate_capability_score(model_config, task_type)

        # Cache result
        if model_name not in self._capability_cache:
            self._capability_cache[model_name] = {}
        self._capability_cache[model_name][task_type] = score

        return score

    def _calculate_capability_score(
        self, model_config: Dict[str, Any], task_type: TaskType
    ) -> float:
        """
        Calculate capability score based on model config

        Args:
            model_config: Model configuration
            task_type: Task type

        Returns:
            Capability score
        """
        model_name = model_config.get("model", "")
        max_tokens = model_config.get("max_tokens", 0)
        context_window = model_config.get("context_window", max_tokens)

        # Base score based on model family
        base_score = self._get_model_base_score(model_name)

        # Adjust for task-specific requirements
        if task_type == TaskType.CODE_GENERATION:
            # Code generation needs larger context
            if context_window >= 32000:
                return min(base_score + 0.2, 1.0)
            elif context_window >= 16000:
                return base_score
            else:
                return max(base_score - 0.2, 0.0)

        elif task_type == TaskType.ANALYSIS:
            # Analysis benefits from reasoning capabilities
            if "gpt-4" in model_name.lower() or "claude-3" in model_name.lower():
                return min(base_score + 0.2, 1.0)
            return base_score

        elif task_type == TaskType.REASONING:
            # Reasoning needs strong models
            if "gpt-4" in model_name.lower() or "claude-3-opus" in model_name.lower():
                return min(base_score + 0.3, 1.0)
            return base_score

        return base_score

    def _get_model_base_score(self, model_name: str) -> float:
        """Get base score for model family"""
        model_name_lower = model_name.lower()

        # Top-tier models
        if any(x in model_name_lower for x in ["gpt-4", "claude-3-opus", "gemini-pro"]):
            return 0.9

        # Mid-tier models
        if any(x in model_name_lower for x in ["gpt-3.5", "claude-3-sonnet", "claude-3-haiku"]):
            return 0.75

        # Budget models
        if any(x in model_name_lower for x in ["mini", "tiny", "lite"]):
            return 0.6

        return 0.7  # Default

    def rank_models_for_task(
        self, task_type: TaskType, models: Optional[List[str]] = None
    ) -> List[ModelCapability]:
        """
        Rank models for specific task

        Args:
            task_type: Task type
            models: List of model names (if None, use all)

        Returns:
            Ranked model capabilities
        """
        if models is None:
            models = cast(
                List[str],
                [
                    config.get("model")
                    for config in self.model_configs
                    if config.get("model") is not None
                ],
            )

        capabilities = []
        for model_name in models:
            score = self.evaluate_model(model_name, task_type)
            capabilities.append(
                ModelCapability(
                    model_name=model_name, task_type=task_type, score=score, metadata={}
                )
            )

        # Sort by score descending
        capabilities.sort(key=lambda x: x.score, reverse=True)
        return capabilities

    def get_best_model_for_task(
        self, task_type: TaskType, models: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Get best model for task

        Args:
            task_type: Task type
            models: List of model names

        Returns:
            Best model name
        """
        ranked = self.rank_models_for_task(task_type, models)
        return ranked[0].model_name if ranked else None
