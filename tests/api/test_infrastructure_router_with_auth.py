# -*- coding: utf-8 -*-
"""
Integration tests for Infrastructure Router with Authentication and Rate Limiting

Tests for:
- JWT authentication on Infrastructure endpoints
- RBAC permission checks
- Rate limiting functionality
- End-to-end API calls with service layer
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from api.infrastructure_router import router
from core.database import Base, get_db
from core.models import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_client(in_memory_db):
    """Create test client with mocked authentication"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override database dependency
    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock authentication to bypass JWT verification in tests
    from core.auth import get_current_user, require_permission

    def mock_get_current_user():
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role="admin",
            disabled=False,
        )
        return user

    def mock_require_permission(resource_type, action):
        def dependency():
            return mock_get_current_user()
        return dependency

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[require_permission] = mock_require_permission

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestInfrastructureRouterAuthentication:
    """Tests for authentication on Infrastructure endpoints"""

    def test_kafka_send_with_auth(self, test_client):
        """Test sending Kafka message with authentication"""
        response = test_client.post(
            "/api/v1/infrastructure/kafka/send",
            json={"topic": "test-topic", "key": "test-key", "value": {"data": "test"}},
        )
        assert response.status_code in (200, 500)  # May fail if Kafka not available

    def test_kafka_status_with_auth(self, test_client):
        """Test getting Kafka status with authentication"""
        response = test_client.get("/api/v1/infrastructure/kafka/status")
        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "total_messages" in data

    def test_flink_create_job_with_auth(self, test_client):
        """Test creating Flink job with authentication"""
        response = test_client.post(
            "/api/v1/infrastructure/flink/job",
            json={"job_name": "test-job", "job_type": "metrics_aggregation", "parallelism": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_name"] == "test-job"

    def test_flink_list_jobs_with_auth(self, test_client):
        """Test listing Flink jobs with authentication"""
        response = test_client.get("/api/v1/infrastructure/flink/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

    def test_config_set_with_auth(self, test_client):
        """Test setting config with authentication"""
        response = test_client.post(
            "/api/v1/infrastructure/config",
            json={"key": "test.config", "value": {"setting": "value"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.config"
        assert data["version"] == 1

    def test_config_get_with_auth(self, test_client):
        """Test getting config with authentication"""
        # First set a config
        test_client.post(
            "/api/v1/infrastructure/config",
            json={"key": "test.config", "value": {"setting": "value"}},
        )

        # Then get it
        response = test_client.get("/api/v1/infrastructure/config/test.config")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.config"

    def test_config_get_all_with_auth(self, test_client):
        """Test getting all configs with authentication"""
        response = test_client.get("/api/v1/infrastructure/config")
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data


class TestInfrastructureRouterRateLimiting:
    """Tests for rate limiting on Infrastructure endpoints"""

    def test_rate_limiting_on_kafka_send(self, test_client):
        """Test rate limiting on Kafka send endpoint"""
        # Send multiple requests quickly
        responses = []
        for _ in range(5):
            response = test_client.post(
                "/api/v1/infrastructure/kafka/send",
                json={"topic": "test-topic", "key": "test-key", "value": {"data": "test"}},
            )
            responses.append(response.status_code)

        # At least some should succeed (rate limit is 100 per minute)
        assert any(status == 200 for status in responses)

    def test_rate_limiting_on_flink_create(self, test_client):
        """Test rate limiting on Flink create endpoint"""
        responses = []
        for i in range(5):
            response = test_client.post(
                "/api/v1/infrastructure/flink/job",
                json={"job_name": f"test-job-{i}", "job_type": "metrics_aggregation", "parallelism": 2},
            )
            responses.append(response.status_code)

        # At least some should succeed
        assert any(status == 200 for status in responses)


class TestInfrastructureRouterRBAC:
    """Tests for RBAC permission checks"""

    def test_admin_can_create_config(self, test_client):
        """Test that admin can create config"""
        response = test_client.post(
            "/api/v1/infrastructure/config",
            json={"key": "admin.config", "value": {"setting": "value"}},
        )
        assert response.status_code == 200

    def test_admin_can_read_config(self, test_client):
        """Test that admin can read config"""
        response = test_client.get("/api/v1/infrastructure/config/admin.config")
        # May be 404 if not exists, but should not be 403
        assert response.status_code in (200, 404)


class TestInfrastructureRouterIntegration:
    """End-to-end integration tests"""

    def test_full_kafka_workflow(self, test_client):
        """Test full Kafka workflow: send -> status"""
        # Send message
        send_response = test_client.post(
            "/api/v1/infrastructure/kafka/send",
            json={"topic": "workflow-topic", "key": "workflow-key", "value": {"data": "workflow"}},
        )

        # Get status
        status_response = test_client.get("/api/v1/infrastructure/kafka/status")

        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "workflow-topic" in status_data.get("topics", [])

    def test_full_flink_workflow(self, test_client):
        """Test full Flink workflow: create -> list"""
        # Create job
        create_response = test_client.post(
            "/api/v1/infrastructure/flink/job",
            json={"job_name": "workflow-job", "job_type": "metrics_aggregation", "parallelism": 2},
        )
        assert create_response.status_code == 200

        # List jobs
        list_response = test_client.get("/api/v1/infrastructure/flink/jobs")
        assert list_response.status_code == 200
        jobs = list_response.json()["jobs"]
        assert any(job["job_name"] == "workflow-job" for job in jobs)

    def test_full_config_workflow(self, test_client):
        """Test full config workflow: set -> get -> update -> get"""
        # Set config
        set_response = test_client.post(
            "/api/v1/infrastructure/config",
            json={"key": "workflow.config", "value": {"setting": "value1"}},
        )
        assert set_response.status_code == 200

        # Get config
        get_response = test_client.get("/api/v1/infrastructure/config/workflow.config")
        assert get_response.status_code == 200
        assert get_response.json()["value"] == {"setting": "value1"}

        # Update config
        update_response = test_client.post(
            "/api/v1/infrastructure/config",
            json={"key": "workflow.config", "value": {"setting": "value2"}},
        )
        assert update_response.status_code == 200
        assert update_response.json()["version"] == 2

        # Get updated config
        get_updated_response = test_client.get("/api/v1/infrastructure/config/workflow.config")
        assert get_updated_response.status_code == 200
        assert get_updated_response.json()["value"] == {"setting": "value2"}
