# -*- coding: utf-8 -*-
"""Regression tests for the SLO console router (``/api/v1/slo`` sub-resources).

The SLO pages ``kpi-management`` / ``kpi-config`` / ``sla-management`` previously
called endpoints that did not exist on the backend (404 -> whole page error).
``api/slo_console_router.py`` implements them on real persistent storage.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.slo_advanced_router import _get_current_user_or_internal
from api.slo_console_router import router
from core.auth_service import User, get_current_user
from core.persistent_store import PersistentStore


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: User(username="tester", role="admin")
    app.dependency_overrides[_get_current_user_or_internal] = lambda: User(
        username="tester", role="admin"
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def cleanup():
    created = {"kpi": [], "sla": []}
    yield created
    for kind, ids in created.items():
        store = PersistentStore("slo_console", kind, tenant_id="default")
        for item in ids:
            if item in store:
                del store[item]


def test_kpi_lifecycle(client, cleanup):
    assert client.get("/api/v1/slo/kpi-management").json() == {"kpis": []}

    resp = client.post(
        "/api/v1/slo/kpi-management",
        json={"name": "CPU使用率", "category": "资源", "unit": "%", "target": 80, "metric": "cpu"},
    )
    assert resp.status_code == 201
    kpi = resp.json()
    cleanup["kpi"].append(kpi["id"])
    assert kpi["name"] == "CPU使用率"
    assert kpi["target"] == 80.0
    # No cpu samples are seeded -> honest null instead of a fabricated value.
    assert kpi["current"] is None
    assert kpi["trend"] == "stable"

    listed = client.get("/api/v1/slo/kpi-management").json()["kpis"]
    assert any(k["id"] == kpi["id"] for k in listed)

    assert client.delete(f"/api/v1/slo/kpi-management/{kpi['id']}").status_code == 200
    cleanup["kpi"].remove(kpi["id"])
    assert client.delete(f"/api/v1/slo/kpi-management/{kpi['id']}").status_code == 404


def test_kpi_config_is_derived_then_editable(client, cleanup):
    kpi = client.post(
        "/api/v1/slo/kpi-management", json={"name": "延迟", "metric": "latency", "target": 200}
    ).json()
    cleanup["kpi"].append(kpi["id"])

    configs = client.get("/api/v1/slo/kpi-config").json()["configs"]
    cfg = next(c for c in configs if c["kpi_id"] == kpi["id"])
    assert cfg["data_source"] == "metrics_history"

    updated = client.put(
        f"/api/v1/slo/kpi-config/{cfg['id']}",
        json={"data_source": "prometheus", "query": "rate(latency[5m])", "alert_enabled": True},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["data_source"] == "prometheus"
    assert body["alert_enabled"] is True

    # persisted across a fresh read
    configs2 = client.get("/api/v1/slo/kpi-config").json()["configs"]
    cfg2 = next(c for c in configs2 if c["kpi_id"] == kpi["id"])
    assert cfg2["data_source"] == "prometheus"


def test_sla_management_lifecycle(client, cleanup):
    assert client.get("/api/v1/slo/sla-management").json() == {"slas": []}

    resp = client.post(
        "/api/v1/slo/sla-management",
        json={
            "name": "云服务SLA",
            "customer": "ACME",
            "service": "api",
            "availability_target": 99.95,
            "response_time_target": 200,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
    )
    assert resp.status_code == 201
    sla = resp.json()
    cleanup["sla"].append(sla["id"])
    assert sla["status"] == "active"

    listed = client.get("/api/v1/slo/sla-management").json()["slas"]
    assert any(s["id"] == sla["id"] for s in listed)


def test_kpi_config_unknown_id_404(client):
    assert client.put("/api/v1/slo/kpi-config/cfg-nope", json={"data_source": "x"}).status_code == 404
