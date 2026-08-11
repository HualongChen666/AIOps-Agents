# -*- coding: utf-8 -*-
"""Shared test fixtures for the AIOps SRE Agent test suite.

These fixtures are discovered by all test files under tests/.
"""

import os

# Force test-friendly configuration before the app is imported.
os.environ["ALLOWED_LOCAL_IPS"] = "127.0.0.1,::1,localhost,testserver"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["RAG_ENABLED"] = "true"
os.environ["METRICS_ENABLED"] = "true"
os.environ["TRACING_ENABLED"] = "true"
os.environ["LOG_AGGREGATION_ENABLED"] = "true"
os.environ["TOPOLOGY_ENABLED"] = "true"
os.environ["RATE_LIMITING_ENABLED"] = "false"
os.environ["HARDWARE_REMEDIATION_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

import config
import core.auth_db

# Disable the global rate limiter so the full test suite is not throttled.
import core.security_middleware as _security_middleware
from core.auth_db import Base, SessionLocal, User, engine
from core.auth_service import hash_password
from main import app

_security_middleware.rate_limiter.check_rate_limit = lambda client_id: (True, None)


@pytest.fixture(scope="session", autouse=True)
def ensure_database():
    """Reset the SQLite database to a known state before each test module.

    The existing data/aiops.db may have an old schema, so it is removed and
    recreated with the current model definitions. A default admin user is
    always seeded for tests that require authentication.
    """
    db_file = core.auth_db._DB_PATH
    engine.dispose()
    if os.path.exists(db_file):
        os.remove(db_file)
    Base.metadata.create_all(bind=engine)
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
