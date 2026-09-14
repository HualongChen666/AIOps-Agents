# -*- coding: utf-8 -*-
"""Regression tests for the medium-severity ledger fix API-018 (2026-09-14).

``api/middleware/tenant_middleware.py`` must not let an arbitrary (or
non-privileged) caller pick the tenant through ``X-Tenant-ID`` / ``?tenant_id``;
only an authenticated admin / service account may impersonate a tenant, and
everyone else resolves to their own token tenant (or ``default``).
"""

import asyncio

import pytest
from starlette.requests import Request

import api.middleware.tenant_middleware as tm


def _make_request(headers=None, query_string=b""):
    raw = [(k.lower().encode(), str(v).encode()) for k, v in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/alerts",
            "headers": raw,
            "query_string": query_string,
        }
    )


def _middleware():
    return tm.TenantMiddleware(app=lambda *a, **k: None)


def test_anonymous_header_override_is_ignored():
    req = _make_request({"X-Tenant-ID": "victim-tenant"})
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "default"


def test_anonymous_query_override_is_ignored():
    req = _make_request(query_string=b"tenant_id=victim")
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "default"


def test_non_admin_header_override_is_ignored(monkeypatch):
    monkeypatch.setattr(tm, "decode_token", lambda token: {"tenant_id": "acme", "role": "viewer"})
    req = _make_request({"Authorization": "Bearer x.y.z", "X-Tenant-ID": "victim"})
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "acme"


def test_admin_header_override_is_honoured(monkeypatch):
    monkeypatch.setattr(tm, "decode_token", lambda token: {"tenant_id": "acme", "role": "admin"})
    req = _make_request({"Authorization": "Bearer x.y.z", "X-Tenant-ID": "oncall-tenant"})
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "oncall-tenant"


def test_token_tenant_used_without_override(monkeypatch):
    monkeypatch.setattr(tm, "decode_token", lambda token: {"tenant_id": "acme", "role": "operator"})
    req = _make_request({"Authorization": "Bearer x.y.z"})
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "acme"


def test_invalid_token_falls_back_to_default(monkeypatch):
    def _boom(token):
        raise ValueError("bad token")

    monkeypatch.setattr(tm, "decode_token", _boom)
    req = _make_request({"Authorization": "Bearer x.y.z", "X-Tenant-ID": "victim"})
    tenant = asyncio.run(_middleware()._resolve_tenant_id(req))
    assert tenant == "default"
