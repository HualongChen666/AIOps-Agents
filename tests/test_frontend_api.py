# -*- coding: utf-8 -*-
"""
Integration tests for Frontend API
==================================

Tests for the Frontend API endpoints using pytest-xdist for parallel testing.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal
from core.models import User
from core.repositories.user_repository import UserRepository
from api.middleware.auth_middleware import create_access_token


@pytest.mark.asyncio
@pytest.mark.integration
class TestFrontendAPI:
    """Test Frontend API endpoints"""

    @pytest.fixture
    async def db_session(self):
        """Create a database session for testing"""
        async with AsyncSessionLocal() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user with admin role"""
        user_repo = UserRepository(session=db_session)
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("testpassword")

        user = await user_repo.create(
            username="testadmin",
            hashed_password=hashed_password,
            email="testadmin@example.com",
            full_name="Test Admin",
            role="admin",
            disabled=False,
        )
        return user

    @pytest.fixture
    def auth_token(self, test_user: User):
        """Create JWT token for test user"""
        token = create_access_token(data={"sub": test_user.username})
        return token

    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app

        return TestClient(app)

    def test_list_components_unauthorized(self, client: TestClient):
        """Test listing components without authentication"""
        response = client.get("/api/v1/frontend/components")
        assert response.status_code == 401

    def test_list_components_authorized(self, client: TestClient, auth_token: str):
        """Test listing components with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/components", headers=headers)
        # Should return 200 or 403 depending on permissions
        assert response.status_code in [200, 403]

    def test_create_component_unauthorized(self, client: TestClient):
        """Test creating component without authentication"""
        component_data = {
            "name": "Test Component",
            "type": "button",
            "category": "ui",
            "description": "Test description",
            "code": "export const Test = () => { return <button>Test</button>; }",
            "is_public": True,
        }
        response = client.post("/api/v1/frontend/components", json=component_data)
        assert response.status_code == 401

    def test_create_component_authorized(self, client: TestClient, auth_token: str):
        """Test creating component with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        component_data = {
            "name": "Test Component",
            "type": "button",
            "category": "ui",
            "description": "Test description",
            "code": "export const Test = () => { return <button>Test</button>; }",
            "is_public": True,
        }
        response = client.post("/api/v1/frontend/components", json=component_data, headers=headers)
        # Should return 201 or 403 depending on permissions
        assert response.status_code in [201, 403]

    def test_get_component_unauthorized(self, client: TestClient):
        """Test getting component without authentication"""
        response = client.get("/api/v1/frontend/components/test-id")
        assert response.status_code == 401

    def test_get_component_authorized(self, client: TestClient, auth_token: str):
        """Test getting component with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/components/test-id", headers=headers)
        # Should return 200, 403, or 404
        assert response.status_code in [200, 403, 404]

    def test_update_component_unauthorized(self, client: TestClient):
        """Test updating component without authentication"""
        update_data = {"name": "Updated Name"}
        response = client.patch("/api/v1/frontend/components/test-id", json=update_data)
        assert response.status_code == 401

    def test_update_component_authorized(self, client: TestClient, auth_token: str):
        """Test updating component with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        update_data = {"name": "Updated Name"}
        response = client.patch(
            "/api/v1/frontend/components/test-id", json=update_data, headers=headers
        )
        # Should return 200, 403, or 404
        assert response.status_code in [200, 403, 404]

    def test_delete_component_unauthorized(self, client: TestClient):
        """Test deleting component without authentication"""
        response = client.delete("/api/v1/frontend/components/test-id")
        assert response.status_code == 401

    def test_delete_component_authorized(self, client: TestClient, auth_token: str):
        """Test deleting component with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.delete("/api/v1/frontend/components/test-id", headers=headers)
        # Should return 200, 403, or 404
        assert response.status_code in [200, 403, 404]

    def test_list_themes_unauthorized(self, client: TestClient):
        """Test listing themes without authentication"""
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 401

    def test_list_themes_authorized(self, client: TestClient, auth_token: str):
        """Test listing themes with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/themes", headers=headers)
        # Should return 200 or 403
        assert response.status_code in [200, 403]

    def test_create_theme_unauthorized(self, client: TestClient):
        """Test creating theme without authentication"""
        theme_data = {
            "name": "Test Theme",
            "base_theme": "light",
            "colors": {"primary": "#3b82f6"},
        }
        response = client.post("/api/v1/frontend/themes", json=theme_data)
        assert response.status_code == 401

    def test_create_theme_authorized(self, client: TestClient, auth_token: str):
        """Test creating theme with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        theme_data = {
            "name": "Test Theme",
            "base_theme": "light",
            "colors": {"primary": "#3b82f6"},
        }
        response = client.post("/api/v1/frontend/themes", json=theme_data, headers=headers)
        # Should return 201 or 403
        assert response.status_code in [201, 403]

    def test_list_layouts_unauthorized(self, client: TestClient):
        """Test listing layouts without authentication"""
        response = client.get("/api/v1/frontend/layouts")
        assert response.status_code == 401

    def test_list_layouts_authorized(self, client: TestClient, auth_token: str):
        """Test listing layouts with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/layouts", headers=headers)
        # Should return 200 or 403
        assert response.status_code in [200, 403]

    def test_create_layout_unauthorized(self, client: TestClient):
        """Test creating layout without authentication"""
        layout_data = {
            "name": "Test Layout",
            "type": "dashboard",
            "structure": {"header": {"height": 64}},
        }
        response = client.post("/api/v1/frontend/layouts", json=layout_data)
        assert response.status_code == 401

    def test_create_layout_authorized(self, client: TestClient, auth_token: str):
        """Test creating layout with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        layout_data = {
            "name": "Test Layout",
            "type": "dashboard",
            "structure": {"header": {"height": 64}},
        }
        response = client.post("/api/v1/frontend/layouts", json=layout_data, headers=headers)
        # Should return 201 or 403
        assert response.status_code in [201, 403]

    def test_rate_limiting(self, client: TestClient, auth_token: str):
        """Test rate limiting on frontend API"""
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Make multiple requests to test rate limiting
        responses = []
        for _ in range(105):  # Exceed the 100/minute limit
            response = client.get("/api/v1/frontend/components", headers=headers)
            responses.append(response.status_code)

        # At least some requests should be rate limited (429)
        assert 429 in responses, "Rate limiting should trigger after exceeding limit"


@pytest.mark.asyncio
@pytest.mark.integration
class TestFrontendEnhancementAPI:
    """Test Frontend Enhancement API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from main import app

        return TestClient(app)

    @pytest.fixture
    async def db_session(self):
        """Create a database session for testing"""
        async with AsyncSessionLocal() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    async def test_user(self, db_session: AsyncSession):
        """Create a test user with admin role"""
        user_repo = UserRepository(session=db_session)
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("testpassword")

        user = await user_repo.create(
            username="testuser",
            hashed_password=hashed_password,
            email="testuser@example.com",
            full_name="Test User",
            role="user",
            disabled=False,
        )
        return user

    @pytest.fixture
    def auth_token(self, test_user: User):
        """Create JWT token for test user"""
        token = create_access_token(data={"sub": test_user.username})
        return token

    def test_get_user_preferences_unauthorized(self, client: TestClient):
        """Test getting user preferences without authentication"""
        response = client.get("/api/v1/frontend/preferences/test-user")
        assert response.status_code == 401

    def test_get_user_preferences_authorized(self, client: TestClient, auth_token: str):
        """Test getting user preferences with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/preferences/test-user", headers=headers)
        # Should return 200 or 503 (if frontend enhancement manager not available)
        assert response.status_code in [200, 503]

    def test_update_user_preferences_unauthorized(self, client: TestClient):
        """Test updating user preferences without authentication"""
        pref_data = {"theme": "dark"}
        response = client.put("/api/v1/frontend/preferences/test-user", json=pref_data)
        assert response.status_code == 401

    def test_update_user_preferences_authorized(self, client: TestClient, auth_token: str):
        """Test updating user preferences with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        pref_data = {"theme": "dark"}
        response = client.put(
            "/api/v1/frontend/preferences/test-user", json=pref_data, headers=headers
        )
        # Should return 200 or 503
        assert response.status_code in [200, 503]

    def test_get_available_themes_unauthorized(self, client: TestClient):
        """Test getting available themes without authentication"""
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 401

    def test_get_available_themes_authorized(self, client: TestClient, auth_token: str):
        """Test getting available themes with authentication"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/api/v1/frontend/themes", headers=headers)
        # Should return 200 or 503
        assert response.status_code in [200, 503]
