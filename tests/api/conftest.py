# -*- coding: utf-8 -*-
"""
Pytest configuration for API tests
Provides shared fixtures for API endpoint testing
"""

import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI application"""
    try:
        from main import app
        with TestClient(app) as test_client:
            yield test_client
    except Exception as e:
        # If main app cannot be imported, create a minimal app for testing
        from fastapi import FastAPI
        from api.cost_router import router as cost_router
        from api.disaster_router import router as disaster_router

        app = FastAPI()
        app.include_router(cost_router)
        app.include_router(disaster_router)
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture(scope="module")
def admin_headers():
    """Create admin authentication headers"""
    try:
        from core.auth_service import create_access_token
        token = create_access_token({"sub": "admin", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # If auth service is not available, return empty headers
        return {}


@pytest.fixture(scope="module")
def admin_user():
    """Mock admin user for authentication tests"""
    user = Mock()
    user.id = "admin-1"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    user.disabled = False
    return user


@pytest.fixture(scope="module")
def regular_user():
    """Mock regular user for authentication tests"""
    user = Mock()
    user.id = "user-1"
    user.username = "user"
    user.role = "user"
    user.is_active = True
    user.disabled = False
    return user


@pytest.fixture(scope="module")
def approval_headers():
    """Create approval authentication headers for API tests"""
    try:
        from core.auth_service import create_access_token
        token = create_access_token({"sub": "approver", "role": "admin", "permissions": ["approve"]})
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # If auth service is not available, return admin headers or empty headers
        try:
            return admin_headers()
        except Exception:
            return {}


@pytest.fixture(scope="module")
def auth_headers():
    """Create generic authentication headers for API tests"""
    try:
        from core.auth_service import create_access_token
        token = create_access_token({"sub": "user", "role": "user"})
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # If auth service is not available, return empty headers
        return {}


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing"""
    try:
        from core.auth_db import SessionLocal
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    except Exception:
        # If database is not available, return None
        yield None


@pytest.fixture(scope="function")
def mock_db():
    """Create a mock database session for testing"""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def mock_auth():
    """Mock authentication for tests that use get_current_active_user"""
    from unittest.mock import AsyncMock, patch
    
    user = Mock()
    user.id = "admin-1"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    user.disabled = False
    
    async def mock_get_current_active_user():
        return user
    
    return patch("core.authentication.get_current_active_user", return_value=AsyncMock(return_value=user))
