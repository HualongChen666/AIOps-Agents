# -*- coding: utf-8 -*-
"""Shared test fixtures for the AIOps SRE Agent test suite.

These fixtures are discovered by all test files under tests/.
"""

import asyncio
import os

# Force test-friendly configuration before the app is imported.
os.environ["ALLOWED_LOCAL_IPS"] = "127.0.0.1,::1,localhost,testserver"
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["RAG_ENABLED"] = "true"
os.environ["METRICS_ENABLED"] = "true"
os.environ["TRACING_ENABLED"] = "true"
os.environ["LOG_AGGREGATION_ENABLED"] = "true"
os.environ["LOKI_HOST"] = "127.0.0.1"
os.environ["LOKI_PORT"] = "1"
os.environ["TOPOLOGY_ENABLED"] = "true"
os.environ["RATE_LIMITING_ENABLED"] = "false"
os.environ["HARDWARE_REMEDIATION_ENABLED"] = "true"

# Per-worker SQLite path to avoid xdist database file races in tests.
_worker = os.environ.get("PYTEST_XDIST_WORKER")
_db_suffix = f"_{_worker}" if _worker else ""
_db_file = os.path.join(os.path.dirname(__file__), "..", "data", f"aiops{_db_suffix}.db")
os.environ["AIOPS_TEST_DB_PATH"] = os.path.abspath(_db_file).replace(os.sep, "/")
_db_main_file = os.path.join(os.path.dirname(__file__), "..", "data", f"aiops_main{_db_suffix}.db")
os.environ["USE_SQLITE"] = "true"
os.environ["SQLITE_PATH"] = os.path.abspath(_db_main_file).replace(os.sep, "/")

import pytest
from fastapi.testclient import TestClient

import config
import core.auth_db

# Disable the global rate limiter so the full test suite is not throttled.
import core.security_middleware as _security_middleware
from core.auth_db import Base, SessionLocal, User, engine
from core.auth_service import hash_password
from main import app

# Main async DB (core.db_engine / core.models) shares per-worker SQLite for tests.
from core.database import Base as MainBase
from core.db_engine import AsyncSessionLocal, engine as main_engine
from core.models import User as MainUser
from sqlalchemy import select

# Avoid trying to reach a real Redis during tests (no revocation checks needed).
import core.authentication as _auth_module
_auth_module._get_redis_client = lambda: None

_security_middleware.rate_limiter.check_rate_limit = lambda client_id: (True, None)


@pytest.fixture(scope="module", autouse=True)
def ensure_database():
    """Reset the SQLite database to a known state before each test module.

    The existing data/aiops.db may have an old schema, so it is removed and
    recreated with the current model definitions. A default admin user is
    always seeded for tests that require authentication.
    """
    auth_engine = core.auth_db.engine
    auth_engine.dispose()
    Base.metadata.drop_all(bind=auth_engine)
    Base.metadata.create_all(bind=auth_engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if user is None:
            user = User(username="admin", role="admin", is_active=True)
            db.add(user)
        user.password_hash = hash_password("admin123")
        db.commit()
    finally:
        db.close()

    async def _seed_main_db() -> None:
        async with main_engine.begin() as conn:
            await conn.run_sync(MainBase.metadata.drop_all)
            await conn.run_sync(MainBase.metadata.create_all)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MainUser.username).where(MainUser.username == "admin"))
            if result.scalar_one_or_none() is None:
                session.add(
                    MainUser(
                        username="admin",
                        hashed_password=hash_password("admin123"),
                        role="admin",
                        disabled=False,
                    )
                )
                await session.commit()

    asyncio.run(_seed_main_db())
    yield


@pytest.fixture(scope="module")
def client():
    c = TestClient(app)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture(scope="module")
def admin_token(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def approval_headers(admin_headers):
    """Admin headers plus the internal API key used by approval/AI routers."""
    return {**admin_headers, "X-Internal-Key": config.INTERNAL_API_KEY}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.nodeid.startswith("tests/core"):
            item.add_marker(pytest.mark.core)
        elif item.nodeid.startswith("tests/api"):
            item.add_marker(pytest.mark.api)
