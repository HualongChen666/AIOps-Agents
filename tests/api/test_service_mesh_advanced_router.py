# -*- coding: utf-8 -*-
"""
Test suite for Service Mesh Advanced Router (database-backed).

The router persists all entities through
:class:`core.service_mesh_repository.ServiceMeshRepository` on a real SQLAlchemy
session.  The previous version of this suite drove the endpoints via deleted
module-level dicts (``_configurations_db`` …), which no longer exist.  These
tests exercise the real repository against the file-backed test database.
"""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.service_mesh_advanced_router import router
from core.auth import get_current_user
from core.database import SessionLocal, get_db
from core.models import (
    MeshConfiguration,
    ObservabilityConfig,
    Policy,
    SecurityPolicy,
    TrafficRule,
)

_MODELS = (MeshConfiguration, TrafficRule, SecurityPolicy, ObservabilityConfig, Policy)


@pytest.fixture
def db_session():
    """Provide a clean database session and purge the mesh tables around each test."""
    db = SessionLocal()
    for model in _MODELS:
        db.query(model).delete()
    db.commit()
    try:
        yield db
    finally:
        for model in _MODELS:
            db.query(model).delete()
        db.commit()
        db.close()


@pytest.fixture
def admin_user():
    return SimpleNamespace(
        id="admin-1", username="admin", role="admin", disabled=False, is_active=True
    )


@pytest.fixture
def client(db_session, admin_user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: admin_user
    return TestClient(app)


# ---------------------------------------------------------------------------
# Mesh configurations
# ---------------------------------------------------------------------------


class TestMeshConfigurations:
    def test_create_and_list_configuration(self, client):
        payload = {"name": "prod-mesh", "mesh_type": "istio", "namespace": "prod"}
        created = client.post("/api/v1/service-mesh/configurations", json=payload)
        assert created.status_code == 201, created.text
        data = created.json()["data"]
        assert data["name"] == "prod-mesh"
        assert data["mesh_type"] == "istio"

        listed = client.get("/api/v1/service-mesh/configurations")
        assert listed.status_code == 200
        body = listed.json()["data"]
        assert body["total"] == 1
        assert body["configurations"][0]["name"] == "prod-mesh"

    def test_get_update_delete_configuration(self, client):
        created = client.post(
            "/api/v1/service-mesh/configurations", json={"name": "m1"}
        ).json()["data"]
        config_id = created["id"]

        got = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
        assert got.status_code == 200
        assert got.json()["data"]["id"] == config_id

        updated = client.patch(
            f"/api/v1/service-mesh/configurations/{config_id}", json={"name": "renamed"}
        )
        assert updated.status_code in (200, 204)
        assert (
            client.get(f"/api/v1/service-mesh/configurations/{config_id}").json()["data"]["name"]
            == "renamed"
        )

        deleted = client.delete(f"/api/v1/service-mesh/configurations/{config_id}")
        assert deleted.status_code in (200, 204)
        assert client.get(f"/api/v1/service-mesh/configurations/{config_id}").status_code == 404

    def test_get_configuration_not_found(self, client):
        assert client.get("/api/v1/service-mesh/configurations/nope").status_code == 404

    def test_list_configurations_filter_by_mesh_type(self, client):
        client.post("/api/v1/service-mesh/configurations", json={"name": "a", "mesh_type": "istio"})
        client.post("/api/v1/service-mesh/configurations", json={"name": "b", "mesh_type": "linkerd"})
        listed = client.get("/api/v1/service-mesh/configurations?mesh_type=linkerd")
        assert listed.status_code == 200
        configs = listed.json()["data"]["configurations"]
        assert len(configs) == 1
        assert configs[0]["mesh_type"] == "linkerd"


# ---------------------------------------------------------------------------
# Traffic rules
# ---------------------------------------------------------------------------


class TestTrafficRules:
    def _payload(self):
        return {
            "name": "canary",
            "service_name": "checkout",
            "match_conditions": {"headers": {"version": "v2"}},
            "destination": {"host": "checkout", "port": 8080},
            "weight": 50,
        }

    def test_create_list_get_update_delete(self, client):
        created = client.post("/api/v1/service-mesh/traffic", json=self._payload())
        assert created.status_code == 201, created.text
        rule = created.json()["data"]
        rule_id = rule["id"]
        assert rule["name"] == "canary"

        listed = client.get("/api/v1/service-mesh/traffic")
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] == 1

        got = client.get(f"/api/v1/service-mesh/traffic/{rule_id}")
        assert got.status_code == 200
        assert got.json()["data"]["id"] == rule_id

        updated = client.patch(
            f"/api/v1/service-mesh/traffic/{rule_id}", json={"weight": 90}
        )
        assert updated.status_code in (200, 204)

        deleted = client.delete(f"/api/v1/service-mesh/traffic/{rule_id}")
        assert deleted.status_code in (200, 204)
        assert client.get(f"/api/v1/service-mesh/traffic/{rule_id}").status_code == 404

    def test_get_traffic_rule_not_found(self, client):
        assert client.get("/api/v1/service-mesh/traffic/nope").status_code == 404


# ---------------------------------------------------------------------------
# Security policies
# ---------------------------------------------------------------------------


class TestSecurityPolicies:
    def test_create_list_update_delete(self, client):
        payload = {
            "name": "strict-mtls",
            "policy_type": "authentication",
            "target_service": "payments",
            "mtls_mode": "STRICT",
        }
        created = client.post("/api/v1/service-mesh/security", json=payload)
        assert created.status_code == 201, created.text
        policy = created.json()["data"]
        policy_id = policy["id"]
        assert policy["name"] == "strict-mtls"

        listed = client.get("/api/v1/service-mesh/security")
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] == 1

        updated = client.patch(
            f"/api/v1/service-mesh/security/{policy_id}", json={"mtls_mode": "PERMISSIVE"}
        )
        assert updated.status_code in (200, 204)

        deleted = client.delete(f"/api/v1/service-mesh/security/{policy_id}")
        assert deleted.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Observability configs
# ---------------------------------------------------------------------------


class TestObservabilityConfigs:
    def test_create_list_update_delete(self, client):
        created = client.post(
            "/api/v1/service-mesh/observability", json={"name": "trace-all"}
        )
        assert created.status_code == 201, created.text
        config_id = created.json()["data"]["id"]

        listed = client.get("/api/v1/service-mesh/observability")
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] == 1

        updated = client.patch(
            f"/api/v1/service-mesh/observability/{config_id}", json={"sampling_rate": 0.5}
        )
        assert updated.status_code in (200, 204)

        deleted = client.delete(f"/api/v1/service-mesh/observability/{config_id}")
        assert deleted.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


class TestPolicies:
    def test_create_list_update_delete(self, client):
        payload = {
            "name": "rate-limit",
            "policy_type": "traffic",
            "target_service": "checkout",
            "rules": [{"type": "rate_limit", "requests_per_second": 100}],
        }
        created = client.post("/api/v1/service-mesh/policies", json=payload)
        assert created.status_code == 201, created.text
        policy_id = created.json()["data"]["id"]

        listed = client.get("/api/v1/service-mesh/policies")
        assert listed.status_code == 200
        assert listed.json()["data"]["total"] == 1

        updated = client.patch(
            f"/api/v1/service-mesh/policies/{policy_id}", json={"enabled": False}
        )
        assert updated.status_code in (200, 204)

        deleted = client.delete(f"/api/v1/service-mesh/policies/{policy_id}")
        assert deleted.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Read-only / aggregate endpoints
# ---------------------------------------------------------------------------


class TestAggregateEndpoints:
    def test_health_summary(self, client):
        response = client.get("/api/v1/service-mesh/health/summary")
        assert response.status_code == 200

    def test_services_listing(self, client):
        response = client.get("/api/v1/service-mesh/services")
        assert response.status_code == 200
