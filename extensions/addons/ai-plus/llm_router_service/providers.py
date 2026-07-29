# -*- coding: utf-8 -*-
"""LLM provider adapters for OpenAI, Anthropic, open-source and local models."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from httpx import AsyncClient
from loguru import logger

from . import metrics
from .schemas import GenerateResponse, ProviderType


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    provider_type: ProviderType

    def __init__(
        self,
        name: str,
        model_id: str,
        cost_per_1k: float = 0.0,
        max_tokens: int = 0,
        context_window: int = 0,
        api_key: str = "",
        base_url: Optional[str] = None,
    ) -> None:
        self.name = name
        self.model_id = model_id
        self.cost_per_1k = cost_per_1k
        self.max_tokens = max_tokens
        self.context_window = context_window
        self.api_key = api_key
        self.base_url = base_url or ""

    @abstractmethod
    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GenerateResponse:
        """Call the provider and return a generation response."""

    def _build_messages(self, prompt: str) -> List[Dict[str, str]]:
        return [{"role": "user", "content": prompt}]

    def _estimate_cost(self, tokens: int) -> float:
        return (tokens / 1000.0) * self.cost_per_1k


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""

    provider_type = ProviderType.OPENAI

    def __init__(
        self,
        *,
        name: str,
        model_id: str,
        cost_per_1k: float = 0.0,
        max_tokens: int = 0,
        context_window: int = 0,
        api_key: str = "",
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            model_id=model_id,
            cost_per_1k=cost_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
        )

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GenerateResponse:
        target = model or self.model_id
        body = {
            "model": target,
            "messages": self._build_messages(prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        start = time.perf_counter()
        try:
            async with AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=body, headers=headers
                )
                resp.raise_for_status()
                data = resp.json()
            latency = time.perf_counter() - start
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            cost = self._estimate_cost(tokens)
            metrics.ROUTER_PROVIDER_LATENCY.labels(
                provider=self.provider_type.value, model=target
            ).observe(latency)
            return GenerateResponse(
                content=content,
                model=target,
                provider=self.provider_type,
                tokens=tokens,
                latency_ms=latency * 1000,
                cost=cost,
            )
        except Exception as exc:
            metrics.ROUTER_PROVIDER_FAILURES.labels(
                provider=self.provider_type.value, model=target
            ).inc()
            logger.error(f"OpenAI provider call failed: {exc}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic API provider."""

    provider_type = ProviderType.ANTHROPIC

    def __init__(
        self,
        *,
        name: str,
        model_id: str,
        cost_per_1k: float = 0.0,
        max_tokens: int = 0,
        context_window: int = 0,
        api_key: str = "",
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            model_id=model_id,
            cost_per_1k=cost_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            api_key=api_key,
            base_url=base_url or "https://api.anthropic.com/v1",
        )

    async def call(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> GenerateResponse:
        target = model or self.model_id
        body = {
            "model": target,
            "max_tokens": max_tokens,
            "messages": self._build_messages(prompt),
            "temperature": temperature,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        start = time.perf_counter()
        try:
            async with AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/messages", json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            latency = time.perf_counter() - start
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            cost = self._estimate_cost(tokens)
            metrics.ROUTER_PROVIDER_LATENCY.labels(
                provider=self.provider_type.value, model=target
            ).observe(latency)
            return GenerateResponse(
                content=content,
                model=target,
                provider=self.provider_type,
                tokens=tokens,
                latency_ms=latency * 1000,
                cost=cost,
            )
        except Exception as exc:
            metrics.ROUTER_PROVIDER_FAILURES.labels(
                provider=self.provider_type.value, model=target
            ).inc()
            logger.error(f"Anthropic provider call failed: {exc}")
            raise


class OpenSourceProvider(OpenAIProvider):
    """Open-source model provider using an OpenAI-compatible API."""

    provider_type = ProviderType.OPEN_SOURCE

    def __init__(
        self,
        *,
        name: str,
        model_id: str,
        cost_per_1k: float = 0.0,
        max_tokens: int = 0,
        context_window: int = 0,
        api_key: str = "",
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            model_id=model_id,
            cost_per_1k=cost_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            api_key=api_key,
            base_url=base_url or "http://localhost:8000/v1",
        )


class LocalProvider(OpenAIProvider):
    """Local model provider using an OpenAI-compatible API."""

    provider_type = ProviderType.LOCAL

    def __init__(
        self,
        *,
        name: str,
        model_id: str,
        cost_per_1k: float = 0.0,
        max_tokens: int = 0,
        context_window: int = 0,
        api_key: str = "",
        base_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            name=name,
            model_id=model_id,
            cost_per_1k=cost_per_1k,
            max_tokens=max_tokens,
            context_window=context_window,
            api_key=api_key,
            base_url=base_url or "http://localhost:8080/v1",
        )


class ProviderFactory:
    """Factory to create provider instances from model configurations."""

    @staticmethod
    def create(config: Dict[str, Any]) -> BaseLLMProvider:
        provider_type = config.get("provider", ProviderType.OPENAI.value)
        kwargs = {
            "name": config.get("name") or config.get("model", "unknown"),
            "model_id": config.get("model_id") or config.get("model", "unknown"),
            "cost_per_1k": config.get("cost_per_1k", 0.0),
            "max_tokens": config.get("max_tokens", 0),
            "context_window": config.get("context_window", 0),
            "api_key": config.get("api_key", ""),
            "base_url": config.get("base_url"),
        }
        if provider_type in (ProviderType.OPENAI, ProviderType.OPENAI.value):
            return OpenAIProvider(**kwargs)
        if provider_type in (ProviderType.ANTHROPIC, ProviderType.ANTHROPIC.value):
            return AnthropicProvider(**kwargs)
        if provider_type in (ProviderType.OPEN_SOURCE, ProviderType.OPEN_SOURCE.value):
            return OpenSourceProvider(**kwargs)
        return LocalProvider(**kwargs)
