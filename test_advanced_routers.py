# -*- coding: utf-8 -*-
"""
Test script for advanced service discovery, service mesh, and service monitoring routers
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from main import app


def test_service_discovery_advanced():
    """Test service discovery advanced router"""
    client = TestClient(app)

    print("\n=== Testing Service Discovery Advanced Router ===")

    # Test GET /api/v1/service-discovery/services
    response = client.get("/api/v1/service-discovery/services")
    print(f"GET /api/v1/service-discovery/services: {response.status_code}")
    assert response.status_code == 200
    print(f"Response: {response.json()}")

    # Test POST /api/v1/service-discovery/services
    service_data = {
        "name": "test-service",
        "host": "localhost",
        "port": 8080,
        "protocol": "http",
        "weight": 1,
    }
    response = client.post("/api/v1/service-discovery/services", json=service_data)
    print(f"POST /api/v1/service-discovery/services: {response.status_code}")
    assert response.status_code == 201
    result = response.json()
    print(f"Created service: {result}")
    service_id = result["data"]["id"]

    # Test GET /api/v1/service-discovery/services/{id}
    response = client.get(f"/api/v1/service-discovery/services/{service_id}")
    print(f"GET /api/v1/service-discovery/services/{service_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Service details: {response.json()}")

    # Test PATCH /api/v1/service-discovery/services/{id}
    update_data = {"weight": 5}
    response = client.patch(f"/api/v1/service-discovery/services/{service_id}", json=update_data)
    print(f"PATCH /api/v1/service-discovery/services/{service_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Updated service: {response.json()}")

    # Test GET /api/v1/service-discovery/health-checks
    response = client.get("/api/v1/service-discovery/health-checks")
    print(f"GET /api/v1/service-discovery/health-checks: {response.status_code}")
    assert response.status_code == 200
    print(f"Health checks: {response.json()}")

    # Test POST /api/v1/service-discovery/health-checks
    health_check_data = {
        "service_id": service_id,
        "check_type": "http",
        "endpoint": "/health",
        "interval_seconds": 30,
    }
    response = client.post("/api/v1/service-discovery/health-checks", json=health_check_data)
    print(f"POST /api/v1/service-discovery/health-checks: {response.status_code}")
    assert response.status_code == 201
    print(f"Created health check: {response.json()}")

    # Test GET /api/v1/service-discovery/endpoints
    response = client.get("/api/v1/service-discovery/endpoints")
    print(f"GET /api/v1/service-discovery/endpoints: {response.status_code}")
    assert response.status_code == 200
    print(f"Endpoints: {response.json()}")

    # Test POST /api/v1/service-discovery/registration
    registration_data = {
        "service_name": "test-service-2",
        "instance_id": "instance-123",
        "host": "localhost",
        "port": 9090,
        "weight": 1,
    }
    response = client.post("/api/v1/service-discovery/registration", json=registration_data)
    print(f"POST /api/v1/service-discovery/registration: {response.status_code}")
    assert response.status_code == 201
    print(f"Registered service: {response.json()}")

    # Test POST /api/v1/service-discovery/deregistration
    deregistration_data = {
        "service_name": "test-service-2",
        "instance_id": "instance-123",
    }
    response = client.post("/api/v1/service-discovery/deregistration", json=deregistration_data)
    print(f"POST /api/v1/service-discovery/deregistration: {response.status_code}")
    assert response.status_code == 200
    print(f"Deregistered service: {response.json()}")

    # Test DELETE /api/v1/service-discovery/services/{id}
    response = client.delete(f"/api/v1/service-discovery/services/{service_id}")
    print(f"DELETE /api/v1/service-discovery/services/{service_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Deleted service: {response.json()}")

    print("\n=== Service Discovery Advanced Router Tests Passed ===")


def test_service_mesh_advanced():
    """Test service mesh advanced router"""
    client = TestClient(app)

    print("\n=== Testing Service Mesh Advanced Router ===")

    # Test GET /api/v1/service-mesh/configurations
    response = client.get("/api/v1/service-mesh/configurations")
    print(f"GET /api/v1/service-mesh/configurations: {response.status_code}")
    assert response.status_code == 200
    print(f"Response: {response.json()}")

    # Test POST /api/v1/service-mesh/configurations
    config_data = {
        "name": "test-mesh-config",
        "mesh_type": "istio",
        "namespace": "default",
        "profile": "default",
        "auto_injection_enabled": True,
        "mtls_enabled": True,
    }
    response = client.post("/api/v1/service-mesh/configurations", json=config_data)
    print(f"POST /api/v1/service-mesh/configurations: {response.status_code}")
    assert response.status_code == 201
    result = response.json()
    print(f"Created configuration: {result}")
    config_id = result["data"]["id"]

    # Test GET /api/v1/service-mesh/configurations/{id}
    response = client.get(f"/api/v1/service-mesh/configurations/{config_id}")
    print(f"GET /api/v1/service-mesh/configurations/{config_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Configuration details: {response.json()}")

    # Test PATCH /api/v1/service-mesh/configurations/{id}
    update_data = {"auto_injection_enabled": False}
    response = client.patch(f"/api/v1/service-mesh/configurations/{config_id}", json=update_data)
    print(f"PATCH /api/v1/service-mesh/configurations/{config_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Updated configuration: {response.json()}")

    # Test GET /api/v1/service-mesh/traffic
    response = client.get("/api/v1/service-mesh/traffic")
    print(f"GET /api/v1/service-mesh/traffic: {response.status_code}")
    assert response.status_code == 200
    print(f"Traffic rules: {response.json()}")

    # Test POST /api/v1/service-mesh/traffic
    traffic_data = {
        "name": "test-traffic-rule",
        "service_name": "test-service",
        "match_conditions": {"uri": {"prefix": "/api"}},
        "destination": {"host": "test-service", "subset": "v1"},
        "weight": 100,
    }
    response = client.post("/api/v1/service-mesh/traffic", json=traffic_data)
    print(f"POST /api/v1/service-mesh/traffic: {response.status_code}")
    assert response.status_code == 201
    print(f"Created traffic rule: {response.json()}")

    # Test GET /api/v1/service-mesh/security
    response = client.get("/api/v1/service-mesh/security")
    print(f"GET /api/v1/service-mesh/security: {response.status_code}")
    assert response.status_code == 200
    print(f"Security policies: {response.json()}")

    # Test POST /api/v1/service-mesh/security
    security_data = {
        "name": "test-security-policy",
        "policy_type": "authentication",
        "target_service": "test-service",
        "mtls_mode": "STRICT",
    }
    response = client.post("/api/v1/service-mesh/security", json=security_data)
    print(f"POST /api/v1/service-mesh/security: {response.status_code}")
    assert response.status_code == 201
    print(f"Created security policy: {response.json()}")

    # Test GET /api/v1/service-mesh/observability
    response = client.get("/api/v1/service-mesh/observability")
    print(f"GET /api/v1/service-mesh/observability: {response.status_code}")
    assert response.status_code == 200
    print(f"Observability configs: {response.json()}")

    # Test POST /api/v1/service-mesh/observability
    observability_data = {
        "name": "test-observability-config",
        "tracing_enabled": True,
        "metrics_enabled": True,
        "sampling_rate": 1.0,
    }
    response = client.post("/api/v1/service-mesh/observability", json=observability_data)
    print(f"POST /api/v1/service-mesh/observability: {response.status_code}")
    assert response.status_code == 201
    print(f"Created observability config: {response.json()}")

    # Test GET /api/v1/service-mesh/policies
    response = client.get("/api/v1/service-mesh/policies")
    print(f"GET /api/v1/service-mesh/policies: {response.status_code}")
    assert response.status_code == 200
    print(f"Policies: {response.json()}")

    # Test POST /api/v1/service-mesh/policies
    policy_data = {
        "name": "test-policy",
        "policy_type": "rate-limit",
        "target_service": "test-service",
        "rules": [{"rate": 100, "burst": 200}],
    }
    response = client.post("/api/v1/service-mesh/policies", json=policy_data)
    print(f"POST /api/v1/service-mesh/policies: {response.status_code}")
    assert response.status_code == 201
    print(f"Created policy: {response.json()}")

    # Test DELETE /api/v1/service-mesh/configurations/{id}
    response = client.delete(f"/api/v1/service-mesh/configurations/{config_id}")
    print(f"DELETE /api/v1/service-mesh/configurations/{config_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Deleted configuration: {response.json()}")

    print("\n=== Service Mesh Advanced Router Tests Passed ===")


def test_service_monitoring_advanced():
    """Test service monitoring advanced router"""
    client = TestClient(app)

    print("\n=== Testing Service Monitoring Advanced Router ===")

    # Test GET /api/v1/service-monitoring/services
    response = client.get("/api/v1/service-monitoring/services")
    print(f"GET /api/v1/service-monitoring/services: {response.status_code}")
    assert response.status_code == 200
    print(f"Response: {response.json()}")

    # Test GET /api/v1/service-monitoring/metrics
    response = client.get("/api/v1/service-monitoring/metrics")
    print(f"GET /api/v1/service-monitoring/metrics: {response.status_code}")
    assert response.status_code == 200
    print(f"Metrics: {response.json()}")

    # Test GET /api/v1/service-monitoring/sla
    response = client.get("/api/v1/service-monitoring/sla")
    print(f"GET /api/v1/service-monitoring/sla: {response.status_code}")
    assert response.status_code == 200
    print(f"SLA metrics: {response.json()}")

    # Test GET /api/v1/service-monitoring/alerts
    response = client.get("/api/v1/service-monitoring/alerts")
    print(f"GET /api/v1/service-monitoring/alerts: {response.status_code}")
    assert response.status_code == 200
    print(f"Alerts: {response.json()}")

    # Test POST /api/v1/service-monitoring/alerts
    alert_data = {
        "name": "test-alert",
        "service_name": "test-service",
        "metric_name": "cpu_usage",
        "condition": "greater_than",
        "threshold": 80.0,
        "severity": "warning",
    }
    response = client.post("/api/v1/service-monitoring/alerts", json=alert_data)
    print(f"POST /api/v1/service-monitoring/alerts: {response.status_code}")
    assert response.status_code == 201
    result = response.json()
    print(f"Created alert: {result}")
    alert_id = result["data"]["id"]

    # Test GET /api/v1/service-monitoring/dashboards
    response = client.get("/api/v1/service-monitoring/dashboards")
    print(f"GET /api/v1/service-monitoring/dashboards: {response.status_code}")
    assert response.status_code == 200
    print(f"Dashboards: {response.json()}")

    # Test POST /api/v1/service-monitoring/dashboards
    dashboard_data = {
        "name": "test-dashboard",
        "description": "Test dashboard",
        "widgets": [
            {
                "type": "metric",
                "title": "CPU Usage",
                "metric": "cpu_usage",
                "service": "test-service",
            }
        ],
        "refresh_interval_seconds": 30,
    }
    response = client.post("/api/v1/service-monitoring/dashboards", json=dashboard_data)
    print(f"POST /api/v1/service-monitoring/dashboards: {response.status_code}")
    assert response.status_code == 201
    result = response.json()
    print(f"Created dashboard: {result}")
    dashboard_id = result["data"]["id"]

    # Test GET /api/v1/service-monitoring/dashboards/{id}
    response = client.get(f"/api/v1/service-monitoring/dashboards/{dashboard_id}")
    print(f"GET /api/v1/service-monitoring/dashboards/{dashboard_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Dashboard details: {response.json()}")

    # Test PATCH /api/v1/service-monitoring/dashboards/{id}
    update_data = {"refresh_interval_seconds": 60}
    response = client.patch(
        f"/api/v1/service-monitoring/dashboards/{dashboard_id}", json=update_data
    )
    print(f"PATCH /api/v1/service-monitoring/dashboards/{dashboard_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Updated dashboard: {response.json()}")

    # Test DELETE /api/v1/service-monitoring/dashboards/{id}
    response = client.delete(f"/api/v1/service-monitoring/dashboards/{dashboard_id}")
    print(f"DELETE /api/v1/service-monitoring/dashboards/{dashboard_id}: {response.status_code}")
    assert response.status_code == 200
    print(f"Deleted dashboard: {response.json()}")

    # Test GET /api/v1/service-monitoring/reports
    response = client.get("/api/v1/service-monitoring/reports")
    print(f"GET /api/v1/service-monitoring/reports: {response.status_code}")
    assert response.status_code == 200
    print(f"Reports: {response.json()}")

    print("\n=== Service Monitoring Advanced Router Tests Passed ===")


if __name__ == "__main__":
    print("Starting advanced router tests...")

    try:
        test_service_discovery_advanced()
        test_service_mesh_advanced()
        test_service_monitoring_advanced()
        print("\n✅ All tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
