# -*- coding: utf-8 -*-
import logging
"""
Enhanced LLM Router
Integrates capability evaluation, cost optimization, and load balancing
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from core.ai.token_budget import prompt_fits, select_model_that_fits

from .capability_evaluator import CapabilityEvaluator, TaskType
from .cost_optimizer import CostOptimizer, RoutingDecision
from .load_balancer import LoadBalancer

try:
    from core.error_recovery.core import RetryConfig, retry_with_policy
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    RetryConfig = None  # type: ignore
    retry_with_policy = None  # type: ignore


class EnhancedLLMRouter:
    """
    Enhanced LLM router with intelligent strategies
    """

    def __init__(
        self,
        model_configs: List[Dict[str, Any]],
        strategy: str = "cost_optimized",
        budget_per_request: Optional[float] = None,
    ):
        """
        Initialize enhanced router

        Args:
            model_configs: Model configurations
            strategy: Routing strategy (cost_optimized, capability_first, balanced)
            budget_per_request: Max cost per request
        """
        self.model_configs = model_configs
        self.strategy = strategy
        self.budget_per_request = budget_per_request

        # Initialize components
        self.capability_evaluator = CapabilityEvaluator(model_configs)
        self.cost_optimizer = CostOptimizer(model_configs, budget_per_request)
        self.load_balancer = LoadBalancer(model_configs)

        logger.info(f"Enhanced LLM Router initialized with strategy: {strategy}")

    async def route_request(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        force_model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Route request to best model

        Args:
            prompt: Input prompt
            task_type: Task type
            force_model: Force specific model
            context: Additional context

        Returns:
            Routing decision
        """
        if force_model:
            # Use forced model if available
            if self._is_model_available(force_model):
                return RoutingDecision(
                    model_name=force_model,
                    estimated_cost=self.cost_optimizer.estimate_cost(
                        force_model, self.cost_optimizer.estimate_tokens(prompt)
                    ),
                    estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                    confidence=1.0,
                    reason="Forced model selection",
                )
            else:
                logger.warning(f"Forced model {force_model} not available, using routing")

        # Apply routing strategy
        if self.strategy == "cost_optimized":
            return await self._cost_optimized_routing(prompt, task_type)
        elif self.strategy == "capability_first":
            return await self._capability_first_routing(prompt, task_type)
        elif self.strategy == "balanced":
            return await self._balanced_routing(prompt, task_type)
        else:
            logger.warning(f"Unknown strategy {self.strategy}, using cost_optimized")
            return await self._cost_optimized_routing(prompt, task_type)

    async def _cost_optimized_routing(self, prompt: str, task_type: TaskType) -> RoutingDecision:
        """Cost-optimized routing"""
        decision = self.cost_optimizer.select_cheapest_model(prompt, task_type)

        if not decision:
            # Fallback to load balancer
            model = self.load_balancer.select_model()
            if model:
                return RoutingDecision(
                    model_name=model,
                    estimated_cost=self.cost_optimizer.estimate_cost(
                        model, self.cost_optimizer.estimate_tokens(prompt)
                    ),
                    estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                    confidence=0.5,
                    reason="Fallback to load balancer",
                )
            else:
                # Last resort: use first available model
                if self.model_configs:
                    first_model = self.model_configs[0].get("model") or self.model_configs[0].get(
                        "name", "unknown"
                    )
                    return RoutingDecision(
                        model_name=first_model,
                        estimated_cost=self.cost_optimizer.estimate_cost(
                            first_model, self.cost_optimizer.estimate_tokens(prompt)
                        ),
                        estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                        confidence=0.1,
                        reason="Last resort fallback",
                    )
                else:
                    raise ValueError("No models available for routing")

        return decision

    async def _capability_first_routing(self, prompt: str, task_type: TaskType) -> RoutingDecision:
        """Capability-first routing"""
        # Get best model by capability
        best_model = self.capability_evaluator.get_best_model_for_task(task_type)

        if best_model and self._is_model_available(best_model):
            return RoutingDecision(
                model_name=best_model,
                estimated_cost=self.cost_optimizer.estimate_cost(
                    best_model, self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=self.capability_evaluator.evaluate_model(best_model, task_type),
                reason="Best capability model",
            )

        # Fallback
        model = self.load_balancer.select_model()
        if model:
            return RoutingDecision(
                model_name=model,
                estimated_cost=self.cost_optimizer.estimate_cost(
                    model, self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=0.5,
                reason="Fallback to load balancer",
            )

        # Last resort: use first available model
        if self.model_configs:
            first_model = self.model_configs[0].get("model") or self.model_configs[0].get(
                "name", "unknown"
            )
            return RoutingDecision(
                model_name=first_model,
                estimated_cost=self.cost_optimizer.estimate_cost(
                    first_model, self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=0.1,
                reason="Last resort fallback",
            )
        else:
            raise ValueError("No models available for routing")

    async def _balanced_routing(self, prompt: str, task_type: TaskType) -> RoutingDecision:
        """Balanced routing (capability + cost)"""
        # Get ranked models by capability
        ranked = self.capability_evaluator.rank_models_for_task(task_type)

        # Filter to top 3 by capability
        top_models = ranked[:3]

        # Select cheapest among top capable models
        best_model = None
        best_score = 0.0

        for model_cap in top_models:
            model_config = self._find_model_config(model_cap.model_name)
            if model_config and self._is_model_available(model_cap.model_name):
                # Combined score: capability * (1 - cost_factor)
                cost = self.cost_optimizer.estimate_cost(
                    model_cap.model_name, self.cost_optimizer.estimate_tokens(prompt)
                )
                max_cost = max(
                    [
                        self.cost_optimizer.estimate_cost(
                            m.model_name, self.cost_optimizer.estimate_tokens(prompt)
                        )
                        for m in top_models
                    ]
                )
                cost_factor = cost / max_cost if max_cost > 0 else 0

                combined_score = model_cap.score * (1 - cost_factor * 0.3)  # 30% weight to cost

                if combined_score > best_score:
                    best_score = combined_score
                    best_model = model_config

        if best_model:
            return RoutingDecision(
                model_name=best_model["model"],
                estimated_cost=self.cost_optimizer.estimate_cost(
                    best_model["model"], self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=best_score,
                reason="Balanced capability and cost",
            )

        # Fallback
        model = self.load_balancer.select_model()
        if model:
            return RoutingDecision(
                model_name=model,
                estimated_cost=self.cost_optimizer.estimate_cost(
                    model, self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=0.5,
                reason="Fallback to load balancer",
            )

        # Last resort: use first available model
        if self.model_configs:
            first_model = self.model_configs[0].get("model") or self.model_configs[0].get(
                "name", "unknown"
            )
            return RoutingDecision(
                model_name=first_model,
                estimated_cost=self.cost_optimizer.estimate_cost(
                    first_model, self.cost_optimizer.estimate_tokens(prompt)
                ),
                estimated_tokens=self.cost_optimizer.estimate_tokens(prompt),
                confidence=0.1,
                reason="Last resort fallback",
            )
        else:
            raise ValueError("No models available for routing")

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_new_tokens: int = 1500,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Route the prompt to the best model and generate a response.

        Enforces per-request and hourly/daily cost budgets.  If the budget is
        exceeded or the call fails, a deterministic fallback result is
        returned so that the AI engine can continue without warnings.

        Returns:
            Dict with keys ``content``, ``model`` and ``usage``.
        """
        import os
        import time

        from config import AI_CONFIG

        from .capability_evaluator import TaskType

        decision = await self.route_request(prompt, task_type=TaskType.GENERAL)
        model_name = decision.model_name

        # Enforce model context window; if the routed model cannot hold the
        # prompt + max_new_tokens, fallback to the cheapest fitting model.
        full_prompt = f"{system}\n{prompt}" if system else prompt
        model_config = self._find_model_config(model_name) or {}
        context_window = model_config.get("context_window") or model_config.get("max_tokens", 0)
        if (
            context_window
            and not prompt_fits(full_prompt, max_new_tokens, context_window, model_name)[0]
        ):
            fitting = select_model_that_fits(
                full_prompt,
                max_new_tokens,
                self.model_configs,
                preferred_model=model_name,
            )
            if fitting:
                model_name = fitting.get("model") or fitting.get("name", model_name)
                logger.warning(
                    f"Model {decision.model_name} context window exceeded; "
                    f"falling back to {model_name}"
                )
            else:
                logger.error("No configured model fits the prompt; using fallback")
                return self._fallback_result(prompt, model_name)

        # Budget guard: refuse expensive calls before spending money.
        if not self.cost_optimizer.check_budget(decision.estimated_cost):
            logger.warning(f"Cost budget would be exceeded for {model_name}; using fallback")
            return self._fallback_result(prompt, model_name)

        api_key = os.getenv("AI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            api_key = AI_CONFIG.get("api_key", "") or ""

        if not api_key:
            return self._fallback_result(prompt, model_name)

        # Cap max_new_tokens to the configured model/token limit.
        model_config = self._find_model_config(model_name) or {}
        model_max_tokens = model_config.get("max_tokens", AI_CONFIG.get("max_new_tokens", 2000))
        max_new_tokens = min(int(max_new_tokens), int(model_max_tokens))

        async def _call_once() -> tuple[Any, float]:
            from openai import AsyncOpenAI

            base_url = AI_CONFIG.get("base_url")
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None,
                timeout=AI_CONFIG.get("timeout", 30),
            )
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            start = time.monotonic()
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_new_tokens,
                **kwargs,
            )
            latency = time.monotonic() - start
            return response, latency

        try:
            if retry_with_policy is not None and RetryConfig is not None:
                retry_config = RetryConfig(
                    max_attempts=AI_CONFIG.get("max_retries", 2) + 1,
                    base_delay=1.0,
                    max_delay=10.0,
                    retryable_exceptions=[Exception],
                )
                response, latency = await retry_with_policy(_call_once, retry_config)
            else:
                response, latency = await _call_once()

            content = response.choices[0].message.content or ""
            usage: Dict[str, Any] = response.usage.model_dump() if response.usage else {}
            prompt_tokens = usage.get("prompt_tokens", self.cost_optimizer.estimate_tokens(prompt))
            completion_tokens = usage.get("completion_tokens", 0)
            actual_cost = self.cost_optimizer.estimate_cost(
                model_name, prompt_tokens, completion_tokens
            )
            self.record_success(model_name, latency=latency, actual_cost=actual_cost)
            return {"content": content, "model": model_name, "usage": usage}
        except Exception as e:
            logger.warning(f"LLM generation failed for {model_name}: {e}, using fallback")
            self.record_failure(model_name, str(e))
            return self._fallback_result(prompt, model_name)

    def _fallback_result(self, prompt: str, model_name: str) -> Dict[str, Any]:
        """Return a deterministic fallback result when no API key is configured."""
        input_tokens = self.cost_optimizer.estimate_tokens(prompt)
        output_tokens = min(50, max(10, input_tokens // 4))
        total_tokens = input_tokens + output_tokens
        return {
            "content": (
                f"[AI Router fallback] AIOps analysis result for prompt: {prompt[:100]}..."
            ),
            "model": model_name,
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
        }

    def _is_model_available(self, model_name: str) -> bool:
        """Check if model is available (circuit not open)"""
        breaker = self.load_balancer.circuit_breakers.get(model_name)
        if breaker:
            return bool(breaker.can_request())
        return True

    def _find_model_config(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Find model configuration"""
        for config in self.model_configs:
            if config.get("model") == model_name or config.get("name") == model_name:
                return config
        return None

    def record_success(
        self, model_name: str, latency: float, actual_cost: Optional[float] = None
    ) -> None:
        """Record successful request"""
        self.load_balancer.record_request_start(model_name)
        self.load_balancer.record_request_success(model_name, latency)
        if actual_cost:
            self.cost_optimizer.record_cost(actual_cost)

    def record_failure(self, model_name: str, error: str) -> None:
        """Record failed request"""
        self.load_balancer.record_request_failure(model_name, error)

    def get_router_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "model_stats": self.load_balancer.get_all_stats(),
            "circuit_states": self.load_balancer.get_circuit_states(),
            "cost_stats": self.cost_optimizer.get_hourly_stats(),
        }