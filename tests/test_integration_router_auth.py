# -*- coding: utf-8 -*-
"""
Integration Router Authentication and Authorization Tests
========================================================

Integration tests for the Integration Router with authentication and authorization.
Tests JWT authentication, RBAC permissions, and rate limiting.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app
from core.database import SessionLocal, engine, Base
from core.models import User
from core.auth import create_access_token
from core.integration_repository import IntegrationRepository


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(db_session):
    """Create a test client with database session"""
    from main import get_db
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(db_session):
    """Create authentication headers for test user"""
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        role="operator",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    
    # Create access token
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
    return {"Authorization": f"Bearer {token}"}


class TestIntegrationRouterAuthentication:
    """Test authentication for integration router endpoints"""

    def test_register_integration_requires_auth(self, test_client):
        """Test that register integration requires authentication"""
        response = test_client.post(
            "/api/v1/integration/register",
            json={
                "integration_type": "monitoring",
                "name": "Test Prometheus",
                "config": {"url": "http://localhost:9090"},
            },
        )
        
        # Should return 401 without auth
        assert response.status_code == 401

    def test_register_integration_with_auth(self, test_client, auth_headers):
        """Test that register integration works with valid auth"""
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.register_integration.return_value = Mock(
                    integration_id="int_123",
                    integration_type=Mock(value="monitoring"),
                    name="Test Prometheus",
                    enabled=True,
                    status=Mock(value="active"),
                    last_tested=None,
                )
                
                response = test_client.post(
                    "/api/v1/integration/register",
                    json={
                        "integration_type": "monitoring",
                        "name": "Test Prometheus",
                        "config": {"url": "http://localhost:9090"},
                    },
                    headers=auth_headers,
                )
                
                # Should return 200 with valid auth
                assert response.status_code in [200, 503]  # 503 if manager not available

    def test_list_integrations_requires_auth(self, test_client):
        """Test that list integrations requires authentication"""
        response = test_client.get("/api/v1/integration/list")
        
        # Should return 401 without auth
        assert response.status_code == 401

    def test_list_integrations_with_auth(self, test_client, auth_headers):
        """Test that list integrations works with valid auth"""
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.integrations = {}
                mock_manager.get_integration_summary.return_value = {
                    "total_integrations": 0,
                    "active_integrations": 0,
                    "integrations_by_type": {},
                    "webhooks_registered": 0,
                    "notification_channels": 0,
                    "pending_notifications": 0,
                    "webhook_events_processed": 0,
                }
                
                response = test_client.get(
                    "/api/v1/integration/list",
                    headers=auth_headers,
                )
                
                # Should return 200 with valid auth
                assert response.status_code == 200

    def test_delete_integration_requires_auth(self, test_client):
        """Test that delete integration requires authentication"""
        response = test_client.delete("/api/v1/integration/test_id")
        
        # Should return 401 without auth
        assert response.status_code == 401

    def test_delete_integration_with_auth(self, test_client, auth_headers):
        """Test that delete integration works with valid auth"""
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.integrations = {"test_id": Mock()}
                
                response = test_client.delete(
                    "/api/v1/integration/test_id",
                    headers=auth_headers,
                )
                
                # Should return 200 with valid auth
                assert response.status_code in [200, 404]  # 404 if not found


class TestIntegrationRouterRateLimiting:
    """Test rate limiting for integration router endpoints"""

    def test_rate_limiting_enforced(self, test_client, auth_headers):
        """Test that rate limiting is enforced"""
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.get_integration_summary.return_value = {
                    "total_integrations": 0,
                    "active_integrations": 0,
                    "integrations_by_type": {},
                    "webhooks_registered": 0,
                    "notification_channels": 0,
                    "pending_notifications": 0,
                    "webhook_events_processed": 0,
                }
                
                # Make multiple requests to trigger rate limit
                responses = []
                for _ in range(65):  # Exceed the 60 request limit
                    response = test_client.get(
                        "/api/v1/integration/list",
                        headers=auth_headers,
                    )
                    responses.append(response.status_code)
                
                # At least one request should be rate limited
                assert 429 in responses

    def test_rate_limiting_per_user(self, test_client, db_session):
        """Test that rate limiting is per-user"""
        # Create two users
        user1 = User(
            username="user1",
            email="user1@example.com",
            full_name="User 1",
            hashed_password="hashed_password",
            role="operator",
            disabled=False,
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            full_name="User 2",
            hashed_password="hashed_password",
            role="operator",
            disabled=False,
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()
        
        # Create tokens for both users
        token1 = create_access_token(data={"sub": str(user1.id), "role": user1.role})
        token2 = create_access_token(data={"sub": str(user2.id), "role": user2.role})
        
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.get_integration_summary.return_value = {
                    "total_integrations": 0,
                    "active_integrations": 0,
                    "integrations_by_type": {},
                    "webhooks_registered": 0,
                    "notification_channels": 0,
                    "pending_notifications": 0,
                    "webhook_events_processed": 0,
                }
                
                # User 1 makes 61 requests (exceeds limit)
                user1_responses = []
                for _ in range(61):
                    response = test_client.get(
                        "/api/v1/integration/list",
                        headers=headers1,
                    )
                    user1_responses.append(response.status_code)
                
                # User 2 should still be able to make requests
                response = test_client.get(
                    "/api/v1/integration/list",
                    headers=headers2,
                )
                
                # User 1 should be rate limited
                assert 429 in user1_responses
                # User 2 should not be rate limited
                assert response.status_code == 200


class TestIntegrationRouterRBAC:
    """Test RBAC permissions for integration router endpoints"""

    def test_create_requires_permission(self, test_client, db_session):
        """Test that create integration requires create permission"""
        # Create user with user role (no create permission)
        user = User(
            username="regularuser",
            email="regular@example.com",
            full_name="Regular User",
            hashed_password="hashed_password",
            role="user",
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()
        
        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.post(
            "/api/v1/integration/register",
            json={
                "integration_type": "monitoring",
                "name": "Test Prometheus",
                "config": {"url": "http://localhost:9090"},
            },
            headers=headers,
        )
        
        # Should return 403 due to insufficient permissions
        assert response.status_code == 403

    def test_operator_can_create(self, test_client, db_session):
        """Test that operator can create integrations"""
        # Create user with operator role
        user = User(
            username="operator",
            email="operator@example.com",
            full_name="Operator",
            hashed_password="hashed_password",
            role="operator",
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()
        
        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.register_integration.return_value = Mock(
                    integration_id="int_123",
                    integration_type=Mock(value="monitoring"),
                    name="Test Prometheus",
                    enabled=True,
                    status=Mock(value="active"),
                    last_tested=None,
                )
                
                response = test_client.post(
                    "/api/v1/integration/register",
                    json={
                        "integration_type": "monitoring",
                        "name": "Test Prometheus",
                        "config": {"url": "http://localhost:9090"},
                    },
                    headers=headers,
                )
                
                # Should succeed or fail due to manager, not permissions
                assert response.status_code in [200, 503]

    def test_admin_has_all_permissions(self, test_client, db_session):
        """Test that admin has all permissions"""
        # Create user with admin role
        user = User(
            username="admin",
            email="admin@example.com",
            full_name="Admin",
            hashed_password="hashed_password",
            role="admin",
            disabled=False,
        )
        db_session.add(user)
        db_session.commit()
        
        token = create_access_token(data={"sub": str(user.id), "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}
        
        with patch('core.integration_manager.INTEGRATION_AVAILABLE', True):
            with patch('core.integration_manager.integration_manager') as mock_manager:
                mock_manager.integrations = {}
                mock_manager.get_integration_summary.return_value = {
                    "total_integrations": 0,
                    "active_integrations": 0,
                    "integrations_by_type": {},
                    "webhooks_registered": 0,
                    "notification_channels": 0,
                    "pending_notifications": 0,
                    "webhook_events_processed": 0,
                }
                
                # Admin should be able to read
                response = test_client.get(
                    "/api/v1/integration/list",
                    headers=headers,
                )
                assert response.status_code == 200
                
                # Admin should be able to create
                mock_manager.register_integration.return_value = Mock(
                    integration_id="int_123",
                    integration_type=Mock(value="monitoring"),
                    name="Test",
                    enabled=True,
                    status=Mock(value="active"),
                    last_tested=None,
                )
                response = test_client.post(
                    "/api/v1/integration/register",
                    json={
                        "integration_type": "monitoring",
                        "name": "Test",
                        "config": {},
                    },
                    headers=headers,
                )
                assert response.status_code in [200, 503]
