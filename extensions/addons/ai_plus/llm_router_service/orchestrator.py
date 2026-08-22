# -*- coding: utf-8 -*-
"""LLM Router orchestrator."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from loguru import logger

from core.ai.llm_router.capability_evaluator import TaskType as CoreTaskType
from core.ai.llm_router.enhanced_router import EnhancedLLMRouter

from . import metrics
from .cache import CacheManager
from .config import settings
from .providers import BaseLLMProvider, ProviderFactory
from .retry import LLMRetryEngine
from .schemas import (
    CircuitStateSchema,
    CostReport,
    GenerateRequest,
    GenerateResponse,
    LiteLLMChoice,
    LiteLLMRequest,
    LiteLLMResponse,
    LiteLLMUsage,
    ModelConfig,
    ModelStatsSchema,
    PerformanceReport,
    ProviderType,
    RouteRequest,
    RouteResponse,
    TaskType,
)


class LLMRouterOrchestrator:
    """Coordinates LLM routing, cost optimization, load balancing and retries."""

    def __init__(
        self,
        settings_obj: Any = None,
        model_configs: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.settings = settings_obj or settings
        self.model_configs = model_configs or self._default_model_configs()
        self.cache = CacheManager(self.settings.redis_url)
        self.retry_engine = LLMRetryEngine(self.settings.retry_policy)
        self.router = EnhancedLLMRouter(
            model_configs=self._to_core_configs(),
            strategy=self.settings.default_strategy,
            budget_per_request=self.settings.budget_per_request,
        )
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._build_providers()
        self._update_gauges()

    def _default_model_configs(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "gpt-4o",
                "model": "gpt-4o",
                "provider": ProviderType.OPENAI,
                "cost_per_1k": 0.03,
                "max_tokens": 128000,
                "context_window": 128000,
            },
            {
                "name": "gpt-3.5-turbo",
                "model": "gpt-3.5-turbo",
                "provider": ProviderType.OPENAI,
                "cost_per_1k": 0.0015,
                "max_tokens": 16385,
                "context_window": 16385,
            },
            {
                "name": "claude-3-opus",
                "model": "claude-3-opus-20240229",
                "provider": ProviderType.ANTHROPIC,
                "cost_per_1k": 0.03,
                "max_tokens": 200000,
                "context_window": 200000,
            },
            {
                "name": "claude-3-sonnet",
                "model": "claude-3-sonnet-20240229",
                "provider": ProviderType.ANTHROPIC,
                "cost_per_1k": 0.003,
                "max_tokens": 200000,
                "context_window": 200000,
            },
            {
                "name": "llama2-7b",
                "model": "llama2-7b",
                "provider": ProviderType.OPEN_SOURCE,
                "cost_per_1k": 0.0005,
                "max_tokens": 4096,
                "context_window": 4096,
                "base_url": "http://localhost:8000/v1",
            },
            {
                "name": "local-llm",
                "model": "local-llm",
                "provider": ProviderType.LOCAL,
                "cost_per_1k": 0.0,
                "max_tokens": 4096,
                "context_window": 4096,
                "base_url": "http://localhost:8080/v1",
            },
        ]

    def _to_core_configs(self) -> List[Dict[str, Any]]:
        core = []
        for config in self.model_configs:
            core.append(
                {
                    "model": config.get("model") or config.get("name", "unknown"),
                    "cost_per_1k": config.get("cost_per_1k", 0.0),
                    "max_tokens": config.get("max_tokens", 0),
                    "context_window": config.get("context_window", 0),
                }
            )
        return core

    def _build_providers(self) -> None:
        for config in self.model_configs:
            provider = ProviderFactory.create(config)
            model_name = config.get("model") or config.get("name")
            if model_name:
                self.providers[model_name] = provider
        self._update_circuit_gauge()
        metrics.ROUTER_ACTIVE_MODELS.labels(service=self.settings.service_name).set(
            len(self.providers)
        )

    def _to_core_task_type(self, task_type: TaskType) -> CoreTaskType:
        mapping = {
            TaskType.CODE_GENERATION: CoreTaskType.CODE_GENERATION,
            TaskType.ANALYSIS: CoreTaskType.ANALYSIS,
            TaskType.SUMMARIZATION: CoreTaskType.SUMMARIZATION,
            TaskType.QUESTION_ANSWERING: CoreTaskType.QUESTION_ANSWERING,
            TaskType.REASONING: CoreTaskType.REASONING,
            TaskType.GENERAL: CoreTaskType.GENERAL,
        }
        return mapping.get(task_type, CoreTaskType.GENERAL)

    def list_models(self) -> List[ModelConfig]:
        return [ModelConfig(**config) for config in self.model_configs]

    def _get_provider(self, model_name: str) -> Optional[BaseLLMProvider]:
        return self.providers.get(model_name)

    async def route(self, request: RouteRequest) -> RouteResponse:
        if request.use_cache:
            cache_key = self.cache._key(
                "route",
                hash(request.prompt),
                request.task_type.value,
                request.force_model,
                request.strategy,
            )
            cached = await self.cache.get(cache_key)
            if cached:
                return RouteResponse(**cached)
        if request.strategy:
            self.router.strategy = request.strategy
        if request.budget is not None:
            self.router.cost_optimizer.budget_per_request = request.budget
        start = time.perf_counter()
        decision = await self.router.route_request(
            request.prompt,
            task_type=self._to_core_task_type(request.task_type),
            force_model=request.force_model,
            context=request.context,
        )
        latency = time.perf_counter() - start
        provider = self._get_provider(decision.model_name)
        provider_type = provider.provider_type if provider else ProviderType.OPENAI
        response = RouteResponse(
            model_name=decision.model_name,
            provider=provider_type,
            estimated_cost=decision.estimated_cost,
            estimated_tokens=decision.estimated_tokens,
            confidence=decision.confidence,
            reason=decision.reason,
            latency_ms=latency * 1000,
        )
        if request.use_cache:
            await self.cache.set(cache_key, response.model_dump())
        return response

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        route_req = RouteRequest(
            prompt=request.prompt,
            task_type=request.task_type,
            force_model=request.model,
            budget=request.budget,
            strategy=request.strategy,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        return await self.route_and_generate(route_req)

    async def route_and_generate(self, request: RouteRequest) -> GenerateResponse:
        route = await self.route(request)
        provider = self._get_provider(route.model_name)
        if not provider:
            raise ValueError(f"No provider available for model {route.model_name}")
        start = time.perf_counter()
        try:
            result = await self.retry_engine.execute(
                provider.call,
                request.prompt,
                route.model_name,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
        except Exception as exc:
            metrics.ROUTER_REQUEST_FAILURES_TOTAL.labels(
                provider=route.provider.value,
                model=route.model_name,
                error=type(exc).__name__,
            ).inc()
            logger.warning(f"Model {route.model_name} failed: {exc}, trying fallback")
            fallback = self._select_fallback(route.model_name)
            if fallback and fallback != route.model_name:
                logger.info(f"Falling back from {route.model_name} to {fallback}")
                metrics.ROUTER_FALLBACK_TOTAL.labels(
                    from_model=route.model_name, to_model=fallback
                ).inc()
                provider = self.providers[fallback]
                result = await self.retry_engine.execute(
                    provider.call,
                    request.prompt,
                    fallback,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                )
                route.model_name = fallback
                route.provider = provider.provider_type
            else:
                raise
        latency = time.perf_counter() - start
        result.model = route.model_name
        result.provider = route.provider
        result.latency_ms = latency * 1000
        metrics.ROUTER_REQUESTS_TOTAL.labels(
            provider=route.provider.value,
            model=route.model_name,
            strategy=self.router.strategy,
        ).inc()
        metrics.ROUTER_LATENCY.labels(
            provider=route.provider.value, model=route.model_name
        ).observe(latency)
        metrics.ROUTER_COST.labels(provider=route.provider.value, model=route.model_name).observe(
            result.cost
        )
        metrics.ROUTER_TOKENS.labels(provider=route.provider.value, model=route.model_name).observe(
            result.tokens
        )
        self.router.record_success(route.model_name, latency, result.cost)
        self._update_cost_gauges()
        self._update_circuit_gauge()
        return result

    def _select_fallback(self, failed_model: str) -> Optional[str]:
        for model_name in self.providers:
            if model_name == failed_model:
                continue
            if self.router._is_model_available(model_name):
                return model_name
        return None

    async def completion(self, request: LiteLLMRequest) -> LiteLLMResponse:
        prompt = self._messages_to_prompt(request.messages)
        gen_req = GenerateRequest(
            prompt=prompt,
            model=None if request.model == "auto" else request.model,
            task_type=TaskType.GENERAL,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            budget=request.budget,
            strategy=request.strategy,
        )
        result = await self.generate(gen_req)
        return LiteLLMResponse(
            model=result.model,
            choices=[LiteLLMChoice(message={"role": "assistant", "content": result.content})],
            usage=LiteLLMUsage(
                prompt_tokens=max(0, result.tokens - result.tokens // 2),
                completion_tokens=result.tokens // 2,
                total_tokens=result.tokens,
            ),
        )

    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        return "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)

    def get_stats(self) -> Dict[str, Any]:
        return self.router.get_router_stats()

    async def get_cost_report(self) -> CostReport:
        stats = self.router.cost_optimizer.get_hourly_stats()
        return CostReport(
            hourly_cost=stats["hourly_cost"],
            request_count=stats["request_count"],
            avg_cost_per_request=stats["avg_cost_per_request"],
            budget_per_request=self.router.cost_optimizer.budget_per_request,
            max_cost_per_hour=self.router.cost_optimizer.max_cost_per_hour,
        )

    async def get_performance_report(self) -> PerformanceReport:
        stats = self.router.get_router_stats()
        model_stats = []
        for name, ms in stats.get("model_stats", {}).items():
            model_stats.append(
                ModelStatsSchema(
                    model_name=name,
                    total_requests=ms.total_requests,
                    successful_requests=ms.successful_requests,
                    failed_requests=ms.failed_requests,
                    avg_latency=ms.avg_latency,
                    last_error=ms.last_error,
                )
            )
        circuit_states = []
        for name, state in stats.get("circuit_states", {}).items():
            circuit_states.append(CircuitStateSchema(model_name=name, state=state.value))
        cost_report = await self.get_cost_report()
        total = sum(ms.total_requests for ms in model_stats)
        return PerformanceReport(
            model_stats=model_stats,
            circuit_states=circuit_states,
            cost_report=cost_report,
            total_requests=total,
        )

    async def route_batch(self, requests: List[RouteRequest]) -> List[RouteResponse]:
        metrics.ROUTER_BATCH_REQUESTS.labels(service=self.settings.service_name).inc()
        metrics.ROUTER_BATCH_SIZE.labels(service=self.settings.service_name).observe(len(requests))
        return await asyncio.gather(*(self.route(req) for req in requests))

    async def generate_batch(self, requests: List[GenerateRequest]) -> List[GenerateResponse]:
        metrics.ROUTER_BATCH_REQUESTS.labels(service=self.settings.service_name).inc()
        metrics.ROUTER_BATCH_SIZE.labels(service=self.settings.service_name).observe(len(requests))
        return await asyncio.gather(*(self.generate(req) for req in requests))

    def _update_gauges(self) -> None:
        self._update_circuit_gauge()
        self._update_cost_gauges()

    def _update_circuit_gauge(self) -> None:
        states = self.router.load_balancer.get_circuit_states()
        for model_name, state in states.items():
            provider = self.providers.get(model_name)
            provider_label = provider.provider_type.value if provider else "unknown"
            metrics.ROUTER_CIRCUIT_BREAKER_STATE.labels(
                provider=provider_label, model=model_name
            ).set(1 if state.value == "open" else 0)
            metrics.ROUTER_MODEL_AVAILABILITY.labels(provider=provider_label, model=model_name).set(
                1 if state.value == "closed" else 0
            )
            metrics.ROUTER_LOAD_BALANCE_SCORE.labels(provider=provider_label, model=model_name).set(
                1.0 if state.value == "closed" else 0.0
            )

    def _update_cost_gauges(self) -> None:
        stats = self.router.cost_optimizer.get_hourly_stats()
        metrics.ROUTER_HOURLY_COST.labels(service=self.settings.service_name).set(
            stats["hourly_cost"]
        )
        metrics.ROUTER_HOURLY_REQUESTS.labels(service=self.settings.service_name).set(
            stats["request_count"]
        )
