# -*- coding: utf-8 -*-
"""Tests for core/exception_handler.py, core/smart_cache_strategy.py,
core/phase3_metrics.py and core/rate_limiting.py."""

import asyncio
import json
from unittest.mock import MagicMock

import pytest

from core.exception_handler import (
    AIOpsException,
    AIException,
    AuthenticationException,
    AuthorizationException,
    ConfigurationException,
    DatabaseException,
    ResourceNotFoundException,
    ValidationException,
    aiops_exception_handler,
    generic_exception_handler,
    setup_exception_handlers,
)
from core.phase3_metrics import (
    HEAL_FAILED,
    HEAL_PENDING_APPROVAL,
    HEAL_SUCCESS,
    HEAL_TOTAL,
    LLM_COST_PER_INCIDENT,
    VERIFY_FAILED,
    VERIFY_PASSED,
)
from core.rate_limiting import ENDPOINT_LIMITS, USER_LIMITS
from core.smart_cache_strategy import SmartCacheStrategy

pytestmark = [pytest.mark.core]


def test_aiops_exception_attributes():
    exc = AIOpsException("boom", error_code="ERR_1", status_code=418, details={"x": 1})
    assert exc.message == "boom"
    assert exc.error_code == "ERR_1"
    assert exc.status_code == 418
    assert exc.details == {"x": 1}
    assert str(exc) == "boom"


def test_aiops_exception_default_details():
    exc = AIOpsException("default")
    assert exc.details == {}
    assert exc.error_code == "INTERNAL_ERROR"
    assert exc.status_code == 500


def test_all_exception_subclasses():
    excs = [
        DatabaseException("db fail", details={"host": "h"}),
        AIException("ai fail"),
        ValidationException("bad input"),
        AuthenticationException("unauthorized"),
        AuthorizationException("forbidden"),
        ResourceNotFoundException("missing"),
        ConfigurationException("bad config"),
    ]
    for exc in excs:
        assert exc.message
        assert exc.error_code
        assert exc.status_code


def _make_request():
    request = MagicMock()
    request.url.path = "/api/v1/test"
    request.method = "POST"
    return request


def test_aiops_exception_handler():
    request = _make_request()
    exc = ValidationException("validation failed")
    resp = asyncio.run(aiops_exception_handler(request, exc))
    assert resp.status_code == 422
    body = json.loads(resp.body)
    assert body["success"] is False
    assert body["error"] == "validation failed"
    assert body["error_code"] == exc.error_code


def test_generic_exception_handler():
    request = _make_request()
    exc = ValueError("something broke")
    resp = asyncio.run(generic_exception_handler(request, exc))
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body["success"] is False
    assert body["error_code"] == "INTERNAL_ERROR"
    assert "ValueError" in body["message"]
    assert "something broke" in body["message"]


def test_setup_exception_handlers():
    app = MagicMock()
    setup_exception_handlers(app)
    assert app.add_exception_handler.call_count == 2


def test_smart_cache_ttl_hot():
    assert SmartCacheStrategy.get_ttl("k", 101, 100) == 60


def test_smart_cache_ttl_warm():
    assert SmartCacheStrategy.get_ttl("k", 11, 100) == 300


def test_smart_cache_ttl_cold():
    assert SmartCacheStrategy.get_ttl("k", 0, 100) == 3600


def test_smart_cache_tier_cold():
    assert SmartCacheStrategy.get_cache_tier("any") == "cold"


def test_phase3_metrics_counters_and_gauge():
    HEAL_TOTAL.labels("script-a").inc()
    HEAL_SUCCESS.labels("script-a").inc()
    HEAL_FAILED.labels("script-a").inc()
    HEAL_PENDING_APPROVAL.labels("alert-1").set(2)
    VERIFY_PASSED.labels("manual").inc()
    VERIFY_FAILED.labels("auto").inc()
    LLM_COST_PER_INCIDENT.labels("gpt-4").inc(0.5)

    assert "script_key" in str(HEAL_TOTAL._labelnames)
    assert HEAL_PENDING_APPROVAL._name == "heal_pending_approval"


def test_endpoint_rate_limits():
    assert ENDPOINT_LIMITS["/api/v1/alerts"]["requests"] == 100
    assert ENDPOINT_LIMITS["/api/v1/ai/analyze"]["window"] == 60


def test_user_rate_limits():
    assert USER_LIMITS["default"]["requests"] == 100
    assert USER_LIMITS["admin"]["requests"] == 1000
