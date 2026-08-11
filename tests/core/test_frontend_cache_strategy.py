# -*- coding: utf-8 -*-
"""Tests for core/frontend_cache_strategy.py."""

import pytest
from fastapi import Response

from core.frontend_cache_strategy import (
    CacheStrategy,
    FrontendCacheStrategies,
    apply_cache_headers,
    cache_response,
    get_etag_for_data,
    setup_cache_headers_middleware,
)


def test_cache_strategy_headers():
    strategy = CacheStrategy(max_age=120, stale_while_revalidate=30, private=True)
    header = strategy.to_cache_control_header()
    assert "max-age=120" in header
    assert "private" in header

    no_store = CacheStrategy(no_store=True)
    assert "no-store" in no_store.to_cache_control_header()


def test_frontend_cache_strategies_endpoint():
    strat = FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/alerts")
    assert strat.max_age == 60
    assert FrontendCacheStrategies.get_strategy_for_endpoint("/api/v1/unknown") is not None


def test_get_etag_for_data():
    etag1 = get_etag_for_data({"a": 1})
    etag2 = get_etag_for_data({"a": 1})
    assert isinstance(etag1, str)
    assert etag1 == etag2


def test_apply_cache_headers_and_middleware():
    response = Response(content="data")
    strategy = CacheStrategy(max_age=300)
    result = apply_cache_headers(response, strategy, etag="abc")
    assert result.headers.get("Cache-Control")
    assert result.headers.get("ETag") == "abc"
    assert "Expires" in result.headers

    config = setup_cache_headers_middleware()
    assert config["status"] == "success"


@pytest.mark.asyncio
async def test_cache_response_decorator():
    strategy = CacheStrategy(max_age=300)

    @cache_response(strategy)
    async def get_data():
        return Response(content='{"x":1}')

    response = await get_data()
    assert "Cache-Control" in response.headers
    assert "ETag" in response.headers
