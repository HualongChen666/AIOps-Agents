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
    import os
    from unittest.mock import Mock, AsyncMock, patch
    from fastapi import FastAPI

    # Set TEST_MODE environment variable
    os.environ["TEST_MODE"] = "true"

    # Patch get_current_active_user at module level
    user = Mock()
    user.id = 1
    user.username = "test_admin"
    user.role = "admin"
    user.is_active = True
    user.disabled = False
    # A *real* bcrypt hash so password checks (login / change-password) against
    # this identity do not blow up inside passlib with a Mock argument.
    try:
        from passlib.context import CryptContext as _CryptContext

        _MOCK_PASSWORD_HASH = _CryptContext(schemes=["bcrypt"]).hash("admin123")
    except Exception:  # pragma: no cover - hashing backend always present in CI
        _MOCK_PASSWORD_HASH = "$2b$12$" + "x" * 53
    user.password_hash = _MOCK_PASSWORD_HASH
    user.hashed_password = _MOCK_PASSWORD_HASH

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
        # The real ``get_current_user`` is synchronous; keep the mock sync so
        # routers that lazily ``from core.auth_service import get_current_user``
        # (and call it directly, e.g. slo_router) do not receive a coroutine.
        def mock_get_current_user(token=None, request=None):
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
            from unittest.mock import MagicMock

            db_user = MagicMock()
            db_user.id = 1
            db_user.username = "admin"
            db_user.email = "admin@example.com"
            db_user.full_name = "Admin"
            db_user.role = "admin"
            db_user.disabled = False
            db_user.is_active = True
            db_user.hashed_password = _MOCK_PASSWORD_HASH
            db_user.mfa_enabled = False
            db_user.created_at = None
            db_user.last_login_at = None

            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = db_user
            mock_session.query.return_value.filter.return_value.all.return_value = [db_user]
            mock_session.query.return_value.first.return_value = db_user
            mock_session.query.return_value.all.return_value = [db_user]
            mock_session.query.return_value.count.return_value = 1
            return mock_session

        core.auth_db.get_session = mock_auth_db_get_session
    except ImportError:
        original_auth_db_get_session = None

    try:
        from main import app

        # --- Wave2 #24: production routers no longer return a placeholder admin
        # for unauthenticated requests (they raise 401).  API tests exercise
        # endpoint logic with an authenticated identity, so override the
        # router-level get_current_user dependencies of the hardened routers.
        from fastapi.routing import APIRoute as _APIRoute

        _auth_user = Mock()
        _auth_user.id = 1
        _auth_user.username = "test_admin"
        _auth_user.full_name = "Test Admin"
        _auth_user.email = "test@example.com"
        _auth_user.role = "admin"
        _auth_user.is_active = True
        _auth_user.disabled = False
        _auth_user.tenant_id = "default"

        def _override_current_user():
            return _auth_user

        _AUTH_MODULES = {
            "api.user_router",
            "api.maturity_router",
            "api.dashboard_advanced_router",
            "api.tenant_advanced_router",
            "api.users_advanced_router",
            "api.maturity_advanced_router",
            "api.ai_advanced_router",
            "api.test_automation_advanced_router",
            "api.test_coverage_advanced_router",
            "api.test_framework_advanced_router",
        }

        def _walk_dep(_dep):
            for _sub in getattr(_dep, "dependencies", []) or []:
                _call = getattr(_sub, "call", None)
                if (
                    _call is not None
                    and getattr(_call, "__name__", "") == "get_current_user"
                    and getattr(_call, "__module__", "") in _AUTH_MODULES
                ):
                    app.dependency_overrides[_call] = _override_current_user
                _walk_dep(_sub)

        try:
            for _route in app.routes:
                if isinstance(_route, _APIRoute):
                    _walk_dep(_route.dependant)
        except Exception:
            pass

        # Authenticate ``core.authentication`` dependencies too.  Routers that
        # import ``get_current_active_user`` at module-import time (which happens
        # before this fixture runs when a test module imports the router at the
        # top, e.g. api.system_resource_router) capture that original function
        # object, so it must be overridden by identity.  The global RBAC
        # middleware is bypassed under TEST_MODE, so this only affects the
        # routers' own auth dependencies.
        try:
            import core.authentication as _core_auth

            app.dependency_overrides.setdefault(
                _core_auth.get_current_active_user, _override_current_user
            )
            app.dependency_overrides.setdefault(_core_auth.get_current_user, _override_current_user)
        except Exception:
            pass

        with TestClient(app) as test_client:
            yield test_client
    except Exception as e:
        # If main app cannot be imported, create a minimal app for testing
        from api.user_router import router as users_router
        from api.cost_router import router as cost_router
        from api.disaster_router import router as disaster_router
        from api.knowledge_base_router import router as knowledge_base_router

        app = FastAPI()
        app.include_router(users_router)
        app.include_router(cost_router)
        app.include_router(disaster_router)
        app.include_router(knowledge_base_router)
        with TestClient(app) as test_client:
            yield test_client
    finally:
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


@pytest.fixture(scope="module")
def admin_headers():
    """Create admin authentication headers"""
    try:
        from core.auth_service import create_access_token
        token = create_access_token({"sub": "admin", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}
    except Exception:
        # If auth service is not available, return a mock token
        return {"Authorization": "Bearer mock_admin_token"}


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
def _internal_api_key() -> str:
    """Internal API key for X-Internal-Key protected endpoints (Wave2 #25)."""
    try:
        import config

        return config.INTERNAL_API_KEY or "test-internal-key"
    except Exception:
        return "test-internal-key"


@pytest.fixture(scope="module")
def approval_headers():
    """Create approval authentication headers for API tests"""
    try:
        from core.auth_service import create_access_token
        token = create_access_token({"sub": "approver", "role": "admin", "permissions": ["approve"]})
        return {"Authorization": f"Bearer {token}", "X-Internal-Key": _internal_api_key()}
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


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Reset all in-process rate limiters before and after every test.

    The API app installs global rate-limit middleware (per client IP → all
    ``TestClient`` traffic shares ``127.0.0.1``).  Without resetting between
    tests, suites that log in / call the same endpoint repeatedly trip the
    limiter and get spurious ``429`` responses.
    """
    def _clear() -> None:
        try:
            from core.middleware.rate_limit_middleware import rate_limiter as _rl

            _rl._requests.clear()
        except Exception:
            pass
        try:
            from core.rate_limiter import get_advanced_rate_limiter

            get_advanced_rate_limiter()._requests.clear()
        except Exception:
            pass
        try:
            from core import rate_limiter as _module

            _module._in_memory_rate_limits.clear()
        except Exception:
            pass
        try:
            from core import auth as _auth

            for _limiter in getattr(_auth, "_rate_limiters", {}).values():
                if hasattr(_limiter, "requests"):
                    _limiter.requests.clear()
        except Exception:
            pass

    _clear()
    yield
    _clear()
