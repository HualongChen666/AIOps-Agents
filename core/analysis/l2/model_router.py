# -*- coding: utf-8 -*-
"""
L2 Analysis Layer - Enhanced Multi-Model Router
Intelligent routing for multiple LLM models based on cost, capacity, and query complexity

Phase 2 集成: 使用增强型 LLM 路由器替换原有实现
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

# Phase 2 集成: 增强型 LLM 路由
try:
    from core.ai.llm_router import EnhancedLLMRouter

    ENHANCED_ROUTER_AVAILABLE = True
except ImportError:
    ENHANCED_ROUTER_AVAILABLE = False
    logger.warning("Phase 2 enhanced LLM router not available")


class MultiModelRouter:
    """
    Enhanced multi-model router for L2 Analysis Layer

    Phase 2 集成: 内部使用 EnhancedLLMRouter 实现智能路由

    This router provides:
    - Cost-based model selection
    - Capacity-aware routing
    - Query complexity analysis
    - Fallback to higher-capacity models when needed
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        # Phase 2 集成: 使用增强型路由器
        self._enhanced_router: Optional[EnhancedLLMRouter] = None
        if ENHANCED_ROUTER_AVAILABLE:
            try:
                model_configs = config.get("models", [])
                self._enhanced_router = EnhancedLLMRouter(
                    model_configs=model_configs,
                    strategy=config.get("strategy", "cost_optimized"),
                    budget_per_request=config.get("budget_per_request"),
                )
                logger.info("Phase 2 enhanced LLM router initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize enhanced router: {e}")

        # Load model configurations (用于降级)
        self.models = config.get("models", [])
        self.token_cost_threshold = config.get("token_cost_threshold", 20000)

        # Sort models by cost (ascending)
        self.models.sort(key=lambda m: m.get("cost_per_1k", float("inf")))

        self._is_initialized = len(self.models) > 0

        if self._is_initialized:
            logger.info(f"MultiModelRouter initialized with {len(self.models)} models")
            for model in self.models:
                logger.info(
                    f"  - {model['provider']}/{model['model']}: "
                    f"${model['cost_per_1k']}/1k tokens, max_tokens={model['max_tokens']}"
                )
        else:
            logger.warning("No models configured for MultiModelRouter")

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token for English
        return len(text) // 4

    async def select_model(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Select the best model for the given prompt

        Phase 2 集成: 优先使用增强型路由器

        Args:
            prompt: Input prompt
            context: Optional context data
            force_model: Force specific model if provided

        Returns:
            Selected model configuration
        """
        # Phase 2 集成: 使用增强型路由器
        if self._enhanced_router:
            try:
                from core.ai.llm_router import TaskType

                decision = await self._enhanced_router.route_request(
                    prompt=prompt,
                    task_type=TaskType.ANALYSIS,
                    force_model=force_model,
                    context=context,
                )
                # 转换为旧格式
                for model in self.models:
                    if model["model"] == decision.model_name:
                        return model  # type: ignore[no-any-return]
            except Exception as e:
                logger.warning(f"Enhanced router failed, using fallback: {e}")

        # 原有逻辑（降级）
        if force_model:
            # Force specific model if requested
            for model in self.models:
                if model["model"] == force_model or model.get("name") == force_model:
                    logger.info(f"Using forced model: {model['model']}")
                    return model  # type: ignore[no-any-return]
            logger.warning(f"Requested model not found: {force_model}, using default routing")

        # Estimate token count
        estimated_tokens = self.estimate_tokens(prompt)

        # Check if threshold exceeded
        if estimated_tokens > self.token_cost_threshold:
            # Use highest capacity model
            model = max(self.models, key=lambda m: m.get("max_tokens", 0))
            logger.info(
                f"Token threshold exceeded ({estimated_tokens}), "
                f"using high-capacity model: {model['model']}"
            )
            return model  # type: ignore[no-any-return]

        # Select cheapest model that can handle the prompt
        for model in self.models:
            if model.get("max_tokens", 0) >= estimated_tokens:
                logger.info(f"Selected model: {model['model']} (cost: ${model['cost_per_1k']}/1k)")
                return model  # type: ignore[no-any-return]

        # Fallback to highest capacity model
        model = max(self.models, key=lambda m: m.get("max_tokens", 0))
        logger.warning(
            f"No model can handle {estimated_tokens} tokens, using highest capacity: {  # noqa: E501
                model['model']}"
        )
        return model  # type: ignore[no-any-return]

    async def route_analysis(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route analysis request to appropriate model

        Args:
            prompt: Analysis prompt
            context: Optional context from RAG
            force_model: Force specific model

        Returns:
            Analysis result with model metadata
        """
        # Select model
        model = await self.select_model(prompt, context, force_model)

        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, context)

        # Route to AI engine with selected model
        try:
            from core.ai_engine import analyze

            # Temporarily override AI config with selected model
            original_config = self._get_ai_config()
            self._set_ai_config(model)

            # Perform analysis
            result = analyze(full_prompt)

            # Restore original config
            self._set_ai_config(original_config)

            # Add routing metadata
            result["routing_metadata"] = {
                "model": model["model"],
                "provider": model["provider"],
                "cost_per_1k": model["cost_per_1k"],
                "estimated_tokens": self.estimate_tokens(full_prompt),
                "rag_enabled": context is not None and context.get("rag_enabled", False),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(f"Analysis completed using {model['model']}")
            return result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Analysis failed with model {model['model']}: {e}")

            # Try fallback to next model
            try:
                next_model = self._get_next_model(model)
                if next_model:
                    logger.info(f"Falling back to {next_model['model']}")
                    return await self.route_analysis(
                        prompt, context, force_model=next_model["model"]
                    )
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")

            return {"error": str(e)}

    def _build_prompt(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        """Build full prompt with context"""
        if not context:
            return prompt

        full_prompt = prompt

        # Add RAG knowledge if available
        if context.get("rag_enabled") and context.get("rag_knowledge"):
            full_prompt += "\n\nRelevant knowledge:\n"
            for idx, knowledge in enumerate(context["rag_knowledge"], 1):
                full_prompt += f"{idx}. {knowledge['text']}\n"

        # Add metrics context if available
        if context.get("metrics"):
            full_prompt += f"\n\nMetrics context: {context['metrics']}\n"

        # Add logs context if available
        if context.get("logs"):
            full_prompt += f"\n\nLogs context: {context['logs']}\n"

        return full_prompt

    def _get_ai_config(self) -> Dict[str, Any]:
        """Get current AI configuration"""
        from config import AI_CONFIG

        return AI_CONFIG.copy()

    def _set_ai_config(self, model_config: Dict[str, Any]) -> None:
        """Set AI configuration for specific model"""
        # This would update the AI engine configuration
        # For now, we'll log it since the actual AI engine integration
        # would require more extensive changes
        logger.debug(f"Would set AI config for model: {model_config['model']}")

    def _get_next_model(self, current_model: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get next model in the sorted list"""
        try:
            current_idx = self.models.index(current_model)
            if current_idx + 1 < len(self.models):
                return self.models[current_idx + 1]  # type: ignore[no-any-return]
        except ValueError:
            pass
        return None

    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about available models"""
        return {
            "total_models": len(self.models),
            "models": [
                {
                    "name": m["model"],
                    "provider": m["provider"],
                    "cost_per_1k": m["cost_per_1k"],
                    "max_tokens": m["max_tokens"],
                }
                for m in self.models
            ],
            "token_cost_threshold": self.token_cost_threshold,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get router status"""
        return {
            "initialized": self._is_initialized,
            "model_count": len(self.models),
            "token_cost_threshold": self.token_cost_threshold,
        }


# Global singleton instance
_model_router: Optional[MultiModelRouter] = None


def get_model_router() -> Optional[MultiModelRouter]:
    """Get global model router instance"""
    return _model_router


def init_model_router(config: Dict[str, Any]) -> MultiModelRouter:
    """Initialize global model router"""
    global _model_router
    _model_router = MultiModelRouter(config)
    return _model_router
