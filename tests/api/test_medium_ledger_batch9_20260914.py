# -*- coding: utf-8 -*-
"""Regression tests for the 9th batch of medium-severity ledger fixes (2026-09-14).

Covered ledger items:

* API-153 ``api/autoheal_router.py`` — ``_verify_internal_key`` is now
  fail-closed (503 when ``INTERNAL_API_KEY`` is unset) and compares the
  provided key in constant time; ``POST /propose`` (``ai_propose_repair``)
  now enforces the internal key like the other protected endpoints.
* API-129 ``api/maturity_advanced_router.py`` — error branches raise
  ``HTTPException`` with the declared status (404/403/400) instead of
  returning an HTTP 200 body carrying the error.  The dynamic
  ``/assessments/{id}`` route no longer shadows the static
  ``/assessments/trends`` and ``/assessments/stats`` routes.
* API-114 ``api/business_impact_advanced_router.py`` — ``create_dependency`` /
  ``create_report`` no longer contain unreachable returns after their
  ``try/finally`` blocks; the create paths return the persisted record.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import api.autoheal_router as autoheal
import api.business_impact_advanced_router as bi
import api.maturity_advanced_router as maturity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class _FakeQuery:
    def __init__(self, first=None):
        self._first = first

    def filter(self, *args, **kwargs):  # noqa: ANN001
        return self

    def first(self):
        return self._first

    def count(self):
        return 0

    def all(self):
        return []

    def offset(self, *args, **kwargs):  # noqa: ANN001
        return self

    def limit(self, *args, **kwargs):  # noqa: ANN001
        return self

    def order_by(self, *args, **kwargs):  # noqa: ANN001
        return self


class _FakeSession:
    def __init__(self, first=None):
        self._first = first
        self.added = []
        self.committed = False

    def query(self, *args, **kwargs):  # noqa: ANN001
        return _FakeQuery(self._first)

    def add(self, obj):  # noqa: ANN001
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def refresh(self, obj):  # noqa: ANN001
        return None

    def close(self):
        return None


def _user(role="admin"):
    return SimpleNamespace(role=role, username="tester", id=1, tenant_id="default")


def _request(headers=None):
    req = MagicMock()
    req.client = SimpleNamespace(host="127.0.0.1")
    req.headers = headers or {}
    return req


# ---------------------------------------------------------------------------
# API-153 — X-Internal-Key is fail-closed
# ---------------------------------------------------------------------------
def test_verify_internal_key_fail_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(autoheal, "INTERNAL_API_KEY", None)
    with pytest.raises(HTTPException) as exc:
        autoheal._verify_internal_key(_request({}))
    assert exc.value.status_code == 503
    assert "not configured" in exc.value.detail


def test_verify_internal_key_missing_header(monkeypatch):
    monkeypatch.setattr(autoheal, "INTERNAL_API_KEY", "s3cr3t")
    with pytest.raises(HTTPException) as exc:
        autoheal._verify_internal_key(_request({}))
    assert exc.value.status_code == 403
    assert "Missing" in exc.value.detail


def test_verify_internal_key_invalid_key(monkeypatch):
    monkeypatch.setattr(autoheal, "INTERNAL_API_KEY", "s3cr3t")
    with pytest.raises(HTTPException) as exc:
        autoheal._verify_internal_key(_request({"X-Internal-Key": "nope"}))
    assert exc.value.status_code == 403
    assert "Invalid" in exc.value.detail


def test_verify_internal_key_valid_key(monkeypatch):
    monkeypatch.setattr(autoheal, "INTERNAL_API_KEY", "s3cr3t")
    # Must not raise with a matching key.
    autoheal._verify_internal_key(_request({"X-Internal-Key": "s3cr3t"}))


def test_ai_propose_requires_internal_key(monkeypatch):
    """The previously unprotected POST /propose now rejects unsigned callers."""
    monkeypatch.setattr(autoheal, "INTERNAL_API_KEY", "s3cr3t")
    payload = autoheal.AIProposeRequest(alert_id="A1")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(autoheal.ai_propose_repair(payload, _request({})))
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# API-129 — error branches raise the declared status
# ---------------------------------------------------------------------------
def test_get_assessment_missing_raises_404():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            maturity.get_assessment("nope", current_user=_user(), db=_FakeSession(first=None))
        )
    assert exc.value.status_code == 404


def test_delete_assessment_non_admin_raises_403():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            maturity.delete_assessment(
                "x", _request(), current_user=_user("viewer"), db=_FakeSession()
            )
        )
    assert exc.value.status_code == 403


def test_trends_invalid_days_raises_400():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            maturity.get_maturity_trends(days=400, current_user=_user(), db=_FakeSession())
        )
    assert exc.value.status_code == 400


def test_export_unsupported_format_raises_400():
    db = _FakeSession(first=SimpleNamespace())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(maturity.export_assessment("a", "xml", current_user=_user(), db=db))
    assert exc.value.status_code == 400


def _maturity_test_app():
    """Minimal app mounting the maturity router with auth/DB overridden."""
    from fastapi import FastAPI
    from core.auth_db import get_session as core_get_session

    app = FastAPI()
    app.include_router(maturity.router)
    app.dependency_overrides[maturity.get_current_user] = lambda: _user()
    app.dependency_overrides[core_get_session] = lambda: _FakeSession()
    return app


def test_trends_route_is_not_shadowed_by_dynamic_id():
    """``/assessments/trends`` must resolve to the trends handler (not get_assessment)."""
    from fastapi.testclient import TestClient

    with TestClient(_maturity_test_app()) as client:
        resp = client.get("/api/v1/maturity/assessments/trends?days=30")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is True
    assert "trends" in body["data"]
    assert "statistics" in body["data"]


def test_stats_route_is_not_shadowed_by_dynamic_id():
    """``/assessments/stats`` must resolve to the stats handler (not get_assessment)."""
    from fastapi.testclient import TestClient

    with TestClient(_maturity_test_app()) as client:
        resp = client.get("/api/v1/maturity/assessments/stats")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("success") is True
    assert "total_assessments" in body["data"]


# ---------------------------------------------------------------------------
# API-114 — create paths return the persisted record (no unreachable return)
# ---------------------------------------------------------------------------
def test_create_dependency_returns_persisted_record(monkeypatch):
    session = _FakeSession(first=None)
    monkeypatch.setattr(bi, "get_session", lambda: session)
    monkeypatch.setattr(bi.cache_manager, "delete_pattern", lambda *a, **k: None)

    payload = bi.CreateDependencyRequest(
        source_service="api-service",
        target_service="database-service",
        criticality=bi.ImpactSeverityEnum.HIGH,
    )
    result = asyncio.run(bi.create_dependency(payload))

    assert result["success"] is True
    assert result["data"]["source_service"] == "api-service"
    assert result["data"]["criticality"] == "high"
    assert len(session.added) == 1
    assert session.committed is True


def test_create_report_returns_persisted_record(monkeypatch):
    session = _FakeSession(first=None)
    monkeypatch.setattr(bi, "get_session", lambda: session)
    monkeypatch.setattr(bi.cache_manager, "delete_pattern", lambda *a, **k: None)

    async def _fake_assess(service_name):
        return {
            "name": service_name,
            "revenueImpact": 12.5,
            "affectedUsers": 40,
            "impactScore": 8.0,
        }

    monkeypatch.setattr(bi, "assess_business_impact", _fake_assess)

    payload = bi.CreateReportRequest(title="Weekly", service_names=["api-service"], time_range="24h")
    result = asyncio.run(bi.create_report(payload))

    assert result["success"] is True
    assert result["data"]["title"] == "Weekly"
    assert len(session.added) == 1
    assert session.committed is True
