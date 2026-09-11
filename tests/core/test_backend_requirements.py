# -*- coding: utf-8 -*-
"""Tests for the ``requires-backend`` signalling helper."""

import pytest
from fastapi import HTTPException

from core.backend_requirements import (
    REQUIRES_BACKEND,
    backend_required_detail,
    is_requires_backend,
    requires_backend,
)


def test_backend_required_detail_minimal():
    detail = backend_required_detail("prometheus")
    assert detail["error"] == REQUIRES_BACKEND
    assert detail["backend"] == "prometheus"
    assert "not configured" in detail["reason"]
    assert "capability" not in detail


def test_backend_required_detail_full():
    detail = backend_required_detail(
        "loki", capability="log query", reason="unreachable"
    )
    assert detail["capability"] == "log query"
    assert detail["reason"] == "unreachable"


def test_requires_backend_raises_503():
    with pytest.raises(HTTPException) as exc_info:
        requires_backend("tempo", capability="tracing")
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error"] == REQUIRES_BACKEND
    assert exc_info.value.detail["backend"] == "tempo"
    assert exc_info.value.detail["capability"] == "tracing"


def test_is_requires_backend():
    assert is_requires_backend({"error": "requires-backend"})
    assert not is_requires_backend({"error": "something-else"})
    assert not is_requires_backend("requires-backend")
    assert not is_requires_backend(None)
