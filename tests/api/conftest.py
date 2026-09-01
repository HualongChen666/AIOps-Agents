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


@pytest.fixture(scope="module", autouse=True)
def enable_test_mode():
    """Enable test mode to bypass authentication"""
    import os
    import sys
    from unittest.mock import patch, Mock, AsyncMock
    
    # Set TEST_MODE environment variable
    os.environ["TEST_MODE"] = "true"
    
    # Patch get_current_active_user at module level
    user = Mock()
    user.id = 1
    user.username = "test_admin"
    user.role = "admin"
    user.is_active = True
    user.disabled = False
    user.password_hash = "hashed_password"
    
    async def mock_get_current_active_user():
        return user
    
    # Patch in core.authentication
    import core.authentication
    original_auth_func = core.authentication.get_current_active_user
    core.authentication.get_current_active_user = mock_get_current_active_user
    
    # Patch get_current_user in core.auth_service
    try:
        import core.auth_service
        original_auth_service_func = core.auth_service.get_current_user
        async def mock_get_current_user(token):
            return user
        core.auth_service.get_current_user = mock_get_current_user
        
        # Patch require_roles to bypass role checks
        original_require_roles = core.auth_service.require_roles
        def mock_require_roles(*roles):
            def decorator(func):
                return func
            return decorator
        core.auth_service.require_roles = mock_require_roles
    except ImportError:
        original_auth_service_func = None
        original_require_roles = None
    
    # Patch core.auth_db.get_session
    try:
        import core.auth_db
        original_auth_db_get_session = core.auth_db.get_session
        def mock_auth_db_get_session():
            from unittest.mock import Mock
            mock_session = Mock()
            mock_session.query = Mock(return_value=Mock())
            return mock_session
        core.auth_db.get_session = mock_auth_db_get_session
    except ImportError:
        original_auth_db_get_session = None
    
    yield
    
    # Restore original functions
    core.authentication.get_current_active_user = original_auth_func
    if original_auth_service_func:
        core.auth_service.get_current_user = original_auth_service_func
    if original_require_roles:
        core.auth_service.require_roles = original_require_roles
    if original_auth_db_get_session:
        core.auth_db.get_session = original_auth_db_get_session
    
    # Clean up
    if "TEST_MODE" in os.environ:
        del os.environ["TEST_MODE"]
