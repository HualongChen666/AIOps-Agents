# -*- coding: utf-8 -*-
"""Real API tests for uncovered routers (batch A)."""

import datetime
import sys  # noqa: F401  # Imported for test setup
import types
from types import SimpleNamespace

import jwt
import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

import config

pytestmark = [pytest.mark.api]

# Fake disaster_recovery module used by api.backup_router.
_dr = types.ModuleType("disaster_recovery")


class _FakeDisasterRecovery:
    """Minimal DisasterRecovery stand-in for backup_router."""

    def backup_database(self) -> str:
        return "/backups/db_backup_test.sql"

    def backup_redis(self) -> str:
        return "/backups/redis_backup_test.rdb"

    def backup_configuration(self) -> str:
        return "/backups/config_test"

    def restore_database(self, backup_file: str) -> bool:
        return True

    def cleanup_old_backups(self, retention_days: int = 30) -> bool:
        return True


_dr.DisasterRecovery = _FakeDisasterRecovery
sys.modules.setdefault("disaster_recovery", _dr)


def _async_return(value):
    """Return an async function that awaits to the given value."""

    async def _inner(*args, **kwargs):
        return value

    return _inner


class _FakeMfaService:
    """Fake MFA service to avoid real TOTP secrets during user router tests."""

    async def is_mfa_enabled(self, username: str) -> bool:
        return False

    async def enable_mfa_for_user(self, username: str):
        return ("fake-secret", "data:image/png;base64,fake", ["code1", "code2"])

    async def disable_mfa_for_user(self, username: str) -> bool:
        return True

    async def get_mfa_status(self, username: str) -> dict:
        return {"enabled": False, "method": "totp"}


class _FakeAuditService:
    """Fake audit service to avoid external persistence in user_router."""

    async def log_action(self, **kwargs):
        return None

    async def get_audit_logs(self, **kwargs):
        return []


class _FakeUserService:
    """In-memory user service that shadows core.user_service to avoid async Postgres."""

    def __init__(self):
        from core.authentication import get_password_hash

        self._users = {}
        self._counter = 1
        self._users["admin"] = SimpleNamespace(
            id=0,
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            disabled=False,
            mfa_enabled=False,
            hashed_password=get_password_hash("admin123"),
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
        )
        self._counter += 1

    async def get_user_by_username(self, username: str):
        return self._users.get(username)

    async def get_user_by_email(self, email: str):
        for u in self._users.values():
            if u.email == email:  # noqa: F841  # Variable for test verification
                return u
        return None

    async def create_user(
        self, username, hashed_password, email=None, full_name=None, role="viewer"
    ):
        if username in self._users:
            return None
        user = SimpleNamespace(
            id=self._counter,
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            disabled=False,
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
            mfa_enabled=False,
        )
        self._users[username] = user
        self._counter += 1
        return user

    async def list_users(self, limit=100, offset=0):
        return list(self._users.values())[offset : offset + limit]

    async def update_user(self, username, email=None, full_name=None, role=None, disabled=None):
        user = self._users.get(username)
        if not user:
            return False
        if email is not None:
            user.email = email  # noqa: F841  # Variable for test verification
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if disabled is not None:
            user.disabled = disabled
        return True

    async def update_password(self, username, hashed_password):
        user = self._users.get(username)
        if not user:
            return False
        user.hashed_password = hashed_password
        return True

    async def delete_user(self, username):
        return self._users.pop(username, None) is not None


@pytest.fixture(autouse=True)
def _patch_external_dependencies(monkeypatch):
    """Isolate external / infrastructure dependencies for the batch routers."""

    # user_router
    import api.user_router as _ur
    import core.user_service as _cus

    _fake_user_svc = _FakeUserService()
    monkeypatch.setattr(_ur, "user_service", _fake_user_svc)
    monkeypatch.setattr(_cus, "user_service", _fake_user_svc)
    monkeypatch.setattr(_ur, "mfa_service", _FakeMfaService())
    monkeypatch.setattr(_ur, "audit_service", _FakeAuditService())

    def _fake_verify_token(token):
        return jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            audience=config.JWT_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "jti"]},
        )

    monkeypatch.setattr(_ur, "verify_token", _fake_verify_token)

    import core.authentication as _auth

    monkeypatch.setattr(_auth, "is_token_revoked", _async_return(False))

    # alert_service uses PostgreSQL persistence; keep in-memory behavior for tests
    import core.alert_service as _alert_s

    monkeypatch.setattr(_alert_s.alert_service, "update_alert_status", _async_return(True))
    monkeypatch.setattr(
        _alert_s.alert_service,
        "clear_alerts",
        lambda operator_ip="unknown": {"status": "success", "cleared_count": 0},
    )

    # slack_router
    import api.slack_router as _slackr
    import config as _config
    import core.chat_command_handler as _cch
    import core.slack_adapter as _sa

    monkeypatch.setattr(_slackr, "post_message", _async_return({"ok": True, "ts": "123"}))
    monkeypatch.setattr(
        _slackr, "post_interactive_message", _async_return({"ok": True, "ts": "124"})
    )
    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", lambda *a, **k: {"action": "noop"})
    monkeypatch.setattr(_sa, "post_message", _async_return({"ok": True, "ts": "123"}))
    monkeypatch.setattr(_sa, "post_interactive_message", _async_return({"ok": True, "ts": "124"}))
    monkeypatch.setattr(_sa, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_cch, "handle_instruction", lambda *a, **k: {"action": "noop"})
    monkeypatch.setattr(_config, "SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setattr(_config, "SLACK_DEFAULT_CHANNEL", "#test")

    # docker_router
    import api.docker_router as _dr

    monkeypatch.setattr(_dr, "DOCKER_HOSTS", [{"host": "demo"}])
    monkeypatch.setattr(
        _dr,
        "collect_docker",
        lambda host_cfg: {"host": host_cfg.get("host"), "containers": 1},
    )
    monkeypatch.setattr(
        _dr,
        "execute_repair_sync",
        _async_return({"success": True, "output": "repaired", "exit_code": 0}),
    )

    # cloud_router
    import api.cloud_router as _cr
    import core.cloud_repair as _ccr

    monkeypatch.setattr(_cr, "CLOUD_PROVIDERS", [{"provider": "aws", "region": "us-east-1"}])
    monkeypatch.setattr(_cr, "collect_all_cloud", lambda: [{"provider": "aws"}])
    monkeypatch.setattr(
        _cr,
        "collect_cloud",
        lambda cfg: {"provider": cfg.get("provider"), "region": cfg.get("region")},
    )
    monkeypatch.setattr(_cr, "get_cloud_collect_history", lambda limit: [])
    monkeypatch.setattr(
        _ccr, "execute_cloud_repair", _async_return({"success": True, "output": "ok"})
    )
    monkeypatch.setattr(_ccr, "get_cloud_repair_history", lambda limit: [])

    # log_router
    import api.linux_router as _linuxr
    import api.log_router as _lr
    import core.es_logger as _el

    monkeypatch.setattr(_lr, "LINUX_HOSTS", [{"host": "test-host"}])
    sample_log = {"time": "2026-07-02T10:30:00Z", "level": "Error", "message": "boom"}
    monkeypatch.setattr(_lr, "get_system_errors", _async_return([sample_log]))
    monkeypatch.setattr(_lr, "get_application_errors", _async_return([sample_log]))
    monkeypatch.setattr(_lr, "get_event_logs", _async_return([{**sample_log, "source": "System"}]))
    monkeypatch.setattr(_lr, "search_logs", _async_return([sample_log]))
    monkeypatch.setattr(_lr, "get_linux_errors", _async_return([sample_log]))
    monkeypatch.setattr(_lr, "get_linux_logs", _async_return([sample_log]))
    monkeypatch.setattr(_lr, "search_linux_logs", _async_return([sample_log]))
    monkeypatch.setattr(_el, "es_search_logs", _async_return([{"_id": "1"}]))
    monkeypatch.setattr(_lr, "es_search_logs", _async_return([{"_id": "1"}]))
    monkeypatch.setattr(_linuxr, "find_linux_host_config", lambda host: {"host": host})

    # health_router
    import api.health_router as _hr

    monkeypatch.setattr(_hr, "get_liveness_status", lambda: {"status": "healthy"})
    monkeypatch.setattr(_hr, "get_readiness_status", lambda: {"ready": True})
    monkeypatch.setattr(_hr, "get_detailed_health", lambda: {"status": "healthy"})
    monkeypatch.setattr(_hr, "perform_health_checks", _async_return({"status": "healthy"}))


def test_user_router_endpoints(admin_headers):
    import api.user_router as _ur

    app_user = FastAPI()
    app_user.include_router(_ur.router)
    with TestClient(app_user) as client:
        # create user (operator is valid for both router and security validator)
        resp = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={
                "username": "batchuser",
                "email": "batch@example.com",
                "full_name": "Batch User",
                "password": "ComplexPass123!",
                "role": "operator",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "batchuser"
        assert data["role"] == "operator"

        # list users
        resp = client.get("/api/v1/users/", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert any(u["username"] == "batchuser" for u in users)

        # me
        resp = client.get("/api/v1/users/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

        # get by username
        resp = client.get("/api/v1/users/batchuser", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "batchuser"

        # update user
        resp = client.put(
            "/api/v1/users/batchuser",
            headers=admin_headers,
            json={"full_name": "Updated Batch User"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Batch User"

        # change password (validates against the admin user's hashed password)
        resp = client.post(
            "/api/v1/users/me/change-password",
            headers=admin_headers,
            json={"current_password": "admin123", "new_password": "NewSecurePass1!"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

        # create then delete another user
        resp = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={
                "username": "deleteme",
                "email": "del@example.com",
                "password": "ComplexPass123!",
                "role": "operator",
            },
        )
        assert resp.status_code == 201
        resp = client.delete("/api/v1/users/deleteme", headers=admin_headers)
        assert resp.status_code == 204

        # mfa enable / disable / status (after password change, use new password)
        resp = client.post(
            "/api/v1/users/me/mfa/enable",
            headers=admin_headers,
            json={"password": "NewSecurePass1!"},
        )
        assert resp.status_code == 200
        assert "secret" in resp.json()

        resp = client.post("/api/v1/users/me/mfa/disable", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "MFA disabled successfully"

        resp = client.get("/api/v1/users/me/mfa/status", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        # audit logs
        resp = client.get("/api/v1/users/batchuser/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        resp = client.get("/api/v1/users/me/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


def test_assets_router_endpoints(client, admin_headers):
    resp = client.post(
        "/api/v1/assets/",
        headers=admin_headers,
        json={
            "name": "batch-asset",
            "service": "payments",
            "business_unit": "finance",
            "env": "prod",
            "owner": "admin",
        },
    )
    assert resp.status_code == 201
    asset = resp.json()
    assert asset["name"] == "batch-asset"
    asset_id = asset["id"]

    resp = client.get("/api/v1/assets/", headers=admin_headers)
    assert resp.status_code == 200
    assert any(a["id"] == asset_id for a in resp.json())

    resp = client.get(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == asset_id

    resp = client.put(
        f"/api/v1/assets/{asset_id}",
        headers=admin_headers,
        json={"service": "billing"},
    )
    assert resp.status_code == 200
    assert resp.json()["service"] == "billing"

    resp = client.delete(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Asset deleted"


def test_alert_router_endpoints(client, admin_headers, monkeypatch):
    import asyncio  # noqa: F401  # Imported for test setup

    from core.alert_service import alert_service

    # seed an alert directly so acknowledge/resolve can be exercised
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    alert = loop.run_until_complete(
        alert_service.create_alert("warning", "batch test alert", "pytest")
    )
    alert_id = alert["id"]

    resp = client.get("/api/v1/alerts/", headers=admin_headers)
    assert resp.status_code == 200
    assert "alerts" in resp.json()

    resp = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"

    resp = client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    resp = client.delete("/api/v1/alerts/", headers=admin_headers)
    assert resp.status_code == 200
    assert "cleared_count" in resp.json()

    # intelligence endpoints
    resp = client.get("/api/v1/alerts/intelligence/statistics", headers=admin_headers)
    assert resp.status_code == 200
    assert "total_patterns" in resp.json()

    resp = client.get(
        "/api/v1/alerts/intelligence/patterns",
        headers=admin_headers,
        params={"limit": 10},
    )
    assert resp.status_code == 200
    assert "patterns" in resp.json()

    resp = client.post(
        "/api/v1/alerts/intelligence/routing-rules",
        headers=admin_headers,
        json={
            "conditions": {"level": "critical"},
            "destination": "oncall",
            "description": "route critical",
            "priority": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post(
        "/api/v1/alerts/intelligence/suppression-rules",
        headers=admin_headers,
        json={
            "pattern": "cpu_normal",
            "reason": "normal fluctuation",
            "suppression_window": 300,
            "enabled": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.get("/api/v1/alerts/intelligence/topology", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.post("/api/v1/alerts/intelligence/route-alerts", headers=admin_headers)
    assert resp.status_code == 200
    assert "routes" in resp.json()

    # predict needs mock metric history with >=10 aligned points
    import core.metrics_history as _mh

    monkeypatch.setattr(
        _mh.metrics_history,
        "to_dict",
        lambda: {
            "timestamps": ["10:00:00"] * 12,
            "cpu_usage": [float(i) for i in range(12)],
        },
    )
    import api.alert_router as _ar

    pred = SimpleNamespace(
        metric_name="cpu_usage",
        predicted_values=[1.0, 2.0],
        predicted_anomalies=[],
        confidence=0.9,
        prediction_horizon=24,
        model_used="prophet",
    )
    monkeypatch.setattr(_ar.alert_intelligence_engine, "predict_alert_trends", _async_return(pred))

    resp = client.post(
        "/api/v1/alerts/intelligence/predict",
        headers=admin_headers,
        json={"metric_name": "cpu_usage", "horizon_hours": 24},
    )
    assert resp.status_code == 200
    assert resp.json()["metric_name"] == "cpu_usage"


def test_health_router_endpoints(client, admin_headers):
    resp = client.get("/api/v1/health/ping", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"

    resp = client.get("/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = client.get("/ready", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["ready"] is True

    resp = client.get("/api/v1/health/detailed", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = client.post("/api/v1/health/check", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_backup_router_endpoints(client, admin_headers):
    resp = client.post("/api/v1/backup/database", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post("/api/v1/backup/redis", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post("/api/v1/backup/configuration", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post("/api/v1/backup/full", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert "backups" in resp.json()

    resp = client.post(
        "/api/v1/backup/restore/database",
        headers=admin_headers,
        params={"backup_file": "/backups/db.sql"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.get("/api/v1/backup/list", headers=admin_headers)
    assert resp.status_code == 200
    assert "backups" in resp.json()

    resp = client.delete(
        "/api/v1/backup/cleanup",
        headers=admin_headers,
        params={"retention_days": 30},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_system_resource_router_endpoints(client, admin_headers):
    get_paths = [
        "/api/system-resources/status",
        "/api/system-resources/summary",
        "/api/system-resources/memory",
        "/api/system-resources/cpu",
        "/api/system-resources/network",
    ]
    for path in get_paths:
        resp = client.get(path, headers=admin_headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["status"] == "success"

    post_paths = [
        "/api/system-resources/memory/optimize",
        "/api/system-resources/cpu/optimize",
        "/api/system-resources/network/optimize",
        "/api/system-resources/optimize",
    ]
    for path in post_paths:
        resp = client.post(path, headers=admin_headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["status"] == "success"


def test_localization_resource_router_endpoints(client, admin_headers):
    # add then retrieve translation
    resp = client.post(
        "/api/localization/translation/add",
        headers=admin_headers,
        params={"language": "zh-CN", "namespace": "common", "key": "batch", "value": "批次"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["added"] is True

    resp = client.get(
        "/api/localization/translations",
        headers=admin_headers,
        params={"language": "zh-CN", "namespace": "common"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["language"] == "zh-CN"
    assert data["data"]["namespace"] == "common"

    resp = client.get("/api/localization/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post(
        "/api/localization/translation/export",
        headers=admin_headers,
        params={
            "language": "zh-CN",
            "namespace": "common",
            "output_path": "/tmp/translations_export.json",
        },
    )
    assert resp.status_code == 200
    assert "exported" in resp.json()["data"]

    resp = client.post(
        "/api/localization/translation/import",
        headers=admin_headers,
        params={
            "language": "zh-CN",
            "namespace": "common",
            "input_path": "/tmp/translations_export.json",
        },
    )
    assert resp.status_code == 200
    assert "imported" in resp.json()["data"]

    resp = client.get(
        "/api/localization/translations/missing",
        headers=admin_headers,
        params={"source_language": "zh-CN", "target_language": "en-US", "namespace": "common"},
    )
    assert resp.status_code == 200
    assert "missing_keys" in resp.json()["data"]


def test_localization_resource_router_error_paths(client, admin_headers):
    """Test error paths in localization_resource_router to improve coverage."""
    import core.localization_resource_manager as lrm_module

    # Test get_resource_status exception (lines 41-43)
    original_get = lrm_module.get_resource_manager

    def mock_get_error():
        raise RuntimeError("Test error in resource status")

    lrm_module.get_resource_manager = mock_get_error

    try:
        resp = client.get("/api/localization/status", headers=admin_headers)
        assert resp.status_code == 500
        # Check if error message is in response (format may vary due to global error handler)
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Test error in resource status" in error_msg or "error" in str(resp_json).lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test get_translations 404 response (line 79)
    def mock_get_manager_empty():
        class FakeManager:
            def get_translations(self, language, namespace):
                return {}  # Empty dict triggers 404

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

            def add_translation(self, language, namespace, key, value):
                return True

            def export_translations(self, language, namespace, output_path):
                return True

            def import_translations(self, language, namespace, input_path):
                return True

            def get_missing_translations(self, source, target, namespace):
                return []

        return FakeManager()

    lrm_module.get_resource_manager = mock_get_manager_empty

    try:
        resp = client.get(
            "/api/localization/translations",
            headers=admin_headers,
            params={"language": "nonexistent", "namespace": "nonexistent"},
        )
        assert resp.status_code == 404
        # Check for 404 response
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Translations not found" in error_msg or "not found" in error_msg.lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test get_translations exception (lines 90-94)
    def mock_get_translations_error():
        class FakeManager:
            def get_translations(self, language, namespace):
                raise ValueError("Test error getting translations")

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

        return FakeManager()

    lrm_module.get_resource_manager = mock_get_translations_error

    try:
        resp = client.get(
            "/api/localization/translations",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common"},
        )
        assert resp.status_code == 500
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Test error getting translations" in error_msg or "error" in error_msg.lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test add_translation exception (lines 133-135)
    def mock_add_translation_error():
        class FakeManager:
            def add_translation(self, language, namespace, key, value):
                raise RuntimeError("Test error adding translation")

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

        return FakeManager()

    lrm_module.get_resource_manager = mock_add_translation_error

    try:
        resp = client.post(
            "/api/localization/translation/add",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common", "key": "test", "value": "test"},
        )
        assert resp.status_code == 500
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Test error adding translation" in error_msg or "error" in error_msg.lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test export_translations exception (lines 177-179)
    def mock_export_translations_error():
        class FakeManager:
            def export_translations(self, language, namespace, output_path):
                raise IOError("Test error exporting translations")

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

        return FakeManager()

    lrm_module.get_resource_manager = mock_export_translations_error

    try:
        resp = client.post(
            "/api/localization/translation/export",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common", "output_path": "/tmp/test.json"},
        )
        assert resp.status_code == 500
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Test error exporting translations" in error_msg or "error" in error_msg.lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test import_translations exception (lines 207-209)
    def mock_import_translations_error():
        class FakeManager:
            def import_translations(self, language, namespace, input_path):
                raise Exception("Test error importing translations")

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

        return FakeManager()

    lrm_module.get_resource_manager = mock_import_translations_error

    try:
        resp = client.post(
            "/api/localization/translation/import",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common", "input_path": "/tmp/test.json"},
        )
        assert resp.status_code == 500
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert "Test error importing translations" in error_msg or "error" in error_msg.lower()
    finally:
        lrm_module.get_resource_manager = original_get

    # Test get_missing_translations exception (lines 238-240)
    def mock_get_missing_translations_error():
        class FakeManager:
            def get_missing_translations(self, source, target, namespace):
                raise RuntimeError("Test error getting missing translations")

            def get_resource_summary(self):
                return {"total_languages": 1, "total_translations": 0}

        return FakeManager()

    lrm_module.get_resource_manager = mock_get_missing_translations_error

    try:
        resp = client.get(
            "/api/localization/translations/missing",
            headers=admin_headers,
            params={"source_language": "en-US", "target_language": "zh-CN", "namespace": "common"},
        )
        assert resp.status_code == 500
        resp_json = resp.json()
        error_msg = str(resp_json)
        assert (
            "Test error getting missing translations" in error_msg or "error" in error_msg.lower()
        )
    finally:
        lrm_module.get_resource_manager = original_get


def test_localization_resource_router_success_paths_detailed(client, admin_headers):
    """Test detailed success paths to cover remaining lines (39-40, 80, 128, 167, 197, 227)."""
    import core.localization_resource_manager as lrm_module

    original_get = lrm_module.get_resource_manager

    # Test get_resource_status success path (lines 39-40)
    def mock_get_manager_success():
        class FakeManager:
            def get_resource_summary(self):
                return {"total_languages": 5, "total_translations": 1000}

            def get_translations(self, language, namespace):
                return {"hello": "world"}

            def add_translation(self, language, namespace, key, value):
                return True

            def export_translations(self, language, namespace, output_path):
                return True

            def import_translations(self, language, namespace, input_path):
                return True

            def get_missing_translations(self, source, target, namespace):
                return ["key1", "key2"]

        return FakeManager()

    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.get("/api/localization/status", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["total_languages"] == 5
        assert data["data"]["total_translations"] == 1000
    finally:
        lrm_module.get_resource_manager = original_get

    # Test get_translations success path with non-empty translations (line 80 check)
    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.get(
            "/api/localization/translations",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["language"] == "en-US"
        assert data["data"]["namespace"] == "common"
        assert data["data"]["translations"] == {"hello": "world"}
        assert data["data"]["count"] == 1
    finally:
        lrm_module.get_resource_manager = original_get

    # Test add_translation success path (line 128)
    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.post(
            "/api/localization/translation/add",
            headers=admin_headers,
            params={
                "language": "en-US",
                "namespace": "common",
                "key": "new_key",
                "value": "new_value",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["added"] is True
    finally:
        lrm_module.get_resource_manager = original_get

    # Test export_translations success path (line 167)
    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.post(
            "/api/localization/translation/export",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common", "output_path": "/tmp/export.json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["exported"] is True
    finally:
        lrm_module.get_resource_manager = original_get

    # Test import_translations success path (line 197)
    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.post(
            "/api/localization/translation/import",
            headers=admin_headers,
            params={"language": "en-US", "namespace": "common", "input_path": "/tmp/import.json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["imported"] is True
    finally:
        lrm_module.get_resource_manager = original_get

    # Test get_missing_translations success path (line 227)
    lrm_module.get_resource_manager = mock_get_manager_success

    try:
        resp = client.get(
            "/api/localization/translations/missing",
            headers=admin_headers,
            params={"source_language": "en-US", "target_language": "zh-CN", "namespace": "common"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["source_language"] == "en-US"
        assert data["data"]["target_language"] == "zh-CN"
        assert data["data"]["namespace"] == "common"
        assert data["data"]["missing_keys"] == ["key1", "key2"]
        assert data["data"]["count"] == 2
    finally:
        lrm_module.get_resource_manager = original_get


def test_localization_adapter_router_endpoints(client, admin_headers):
    resp = client.get("/api/localization-adapter/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.get("/api/localization-adapter/locales", headers=admin_headers)
    assert resp.status_code == 200
    assert "locales" in resp.json()["data"]

    resp = client.post(
        "/api/localization-adapter/locale/set",
        headers=admin_headers,
        params={"locale_id": "zh-CN"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["set"] is True

    resp = client.get(
        "/api/localization-adapter/format/date",
        headers=admin_headers,
        params={"date_str": "2026-07-03", "format_type": "short", "locale": "zh-CN"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["formatted"]

    resp = client.get(
        "/api/localization-adapter/format/datetime",
        headers=admin_headers,
        params={
            "datetime_str": "2026-07-03T10:00:00",
            "format_type": "full",
            "locale": "en-US",
        },
    )
    assert resp.status_code == 200

    resp = client.get(
        "/api/localization-adapter/format/number",
        headers=admin_headers,
        params={
            "number": 1234.56,
            "format_type": "decimal",
            "locale": "zh-CN",
            "decimals": 2,
        },
    )
    assert resp.status_code == 200

    resp = client.get(
        "/api/localization-adapter/format/currency",
        headers=admin_headers,
        params={
            "amount": 100.5,
            "currency_code": "USD",
            "locale": "en-US",
            "decimals": 2,
        },
    )
    assert resp.status_code == 200

    resp = client.get(
        "/api/localization-adapter/format/unit",
        headers=admin_headers,
        params={
            "value": 10,
            "unit": "meter",
            "target_system": "metric",
            "locale": "zh-CN",
        },
    )
    assert resp.status_code == 200


def test_slack_router_endpoints(client, admin_headers):
    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "hello", "channel": "#test", "thread_ts": "123"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.post(
        "/api/slack/interactive",
        headers=admin_headers,
        json={"text": "approve", "channel": "#test", "actions": [{"name": "yes"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # url verification (no auth required)
    resp = client.post(
        "/api/slack/events",
        json={"type": "url_verification", "challenge": "abc"},
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["challenge"] == "abc"

    # message / app_mention event
    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "<@U123> hello",
                "user": "U123",
                "channel": "C123",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # block_actions approve
    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [{"action_id": "approve_123", "value": "item-1"}],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"]["type"] == "approve"

    # block_actions reject
    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [{"action_id": "reject_123", "value": "item-1"}],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"]["type"] == "reject"

    # health
    resp = client.get("/api/slack/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["token_configured"] is True


def test_docker_router_endpoints():
    import api.docker_router as _dr

    app_docker = FastAPI()
    app_docker.include_router(_dr.router)
    with TestClient(app_docker) as client:
        resp = client.get("/api/v1/platforms/docker/metrics")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert resp.json()[0]["containers"] == 1

        resp = client.post(
            "/api/v1/platforms/docker/repair",
            json={"host": "demo", "script_name": "restart", "args": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


def test_enterprise_router_endpoints(client, admin_headers):
    resp = client.post(
        "/api/v1/enterprise/tenant/isolation/check",
        headers=admin_headers,
        json={"tenant_id": "t1", "resource_id": "r1", "resource_type": "db"},
    )
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == "t1"

    resp = client.post(
        "/api/v1/enterprise/tenant/resource/assign",
        headers=admin_headers,
        params={"tenant_id": "t1", "resource_id": "r1"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post(
        "/api/v1/enterprise/compliance/check",
        headers=admin_headers,
        json={"standard": "gdpr"},
    )
    assert resp.status_code == 200
    assert "compliance_check" in resp.json()

    resp = client.post(
        "/api/v1/enterprise/compliance/report",
        headers=admin_headers,
        json={"standard": "gdpr"},
    )
    assert resp.status_code == 200
    assert "compliance_report" in resp.json()

    resp = client.post(
        "/api/v1/enterprise/encryption/encrypt",
        headers=admin_headers,
        json={"data": "hello", "classification": "internal"},
    )
    assert resp.status_code == 200
    encrypted = resp.json()["encrypted_data"]

    resp = client.post(
        "/api/v1/enterprise/encryption/decrypt",
        headers=admin_headers,
        params={"encrypted_data": encrypted},
    )
    assert resp.status_code == 200
    assert resp.json()["decrypted_data"] == "hello"

    audit_payload = {
        "tenant_id": "t1",
        "user_id": "u1",
        "action": "read",
        "resource_type": "db",
        "resource_id": "r1",
        "outcome": "success",
        "ip_address": "127.0.0.1",
        "user_agent": "pytest",
        "metadata": {},
        "data_classification": "internal",
    }
    resp = client.post(
        "/api/v1/enterprise/audit/log",
        headers=admin_headers,
        json=audit_payload,
    )
    assert resp.status_code == 200
    assert "audit_entry" in resp.json()

    resp = client.get(
        "/api/v1/enterprise/audit/logs",
        headers=admin_headers,
        params={"limit": 10},
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    resp = client.post("/api/v1/enterprise/audit/cleanup", headers=admin_headers)
    assert resp.status_code == 200
    assert "removed_logs_count" in resp.json()

    resp = client.post(
        "/api/v1/enterprise/privacy/consent",
        headers=admin_headers,
        json={"user_id": "u1", "consent_given": True, "consent_purpose": "analytics"},
    )
    assert resp.status_code == 200
    assert resp.json()["consent_given"] is True

    resp = client.get(
        "/api/v1/enterprise/privacy/consent/u1",
        headers=admin_headers,
        params={"consent_purpose": "analytics"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/enterprise/privacy/mask",
        headers=admin_headers,
        json={"email": "foo@example.com", "phone": "1234567890"},
    )
    assert resp.status_code == 200
    assert "masked_data" in resp.json()

    resp = client.get("/api/v1/enterprise/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert "enterprise_summary" in resp.json()

    resp = client.get("/api/v1/enterprise/compliance/standards", headers=admin_headers)
    assert resp.status_code == 200
    assert "supported_standards" in resp.json()

    resp = client.get("/api/v1/enterprise/encryption/status", headers=admin_headers)
    assert resp.status_code == 200
    assert "encryption_status" in resp.json()

    resp = client.get("/api/v1/enterprise/data/classification/rules", headers=admin_headers)
    assert resp.status_code == 200
    assert "classification_rules" in resp.json()

    resp = client.post(
        "/api/v1/enterprise/data/classify",
        headers=admin_headers,
        params={"data_key": "email"},
    )
    assert resp.status_code == 200
    assert resp.json()["classification"] == "confidential"


def test_log_router_endpoints(client, admin_headers):
    resp = client.get(
        "/api/v1/logs/system/errors",
        headers=admin_headers,
        params={"newest": 5},
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    resp = client.get(
        "/api/v1/logs/application/errors",
        headers=admin_headers,
        params={"newest": 5},
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    resp = client.get(
        "/api/v1/logs/query",
        headers=admin_headers,
        params={"log_name": "System", "level": "Error", "newest": 5},
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    resp = client.get(
        "/api/v1/logs/search",
        headers=admin_headers,
        params={"keyword": "error", "newest": 10},
    )
    assert resp.status_code == 200
    assert resp.json()["keyword"] == "error"

    resp = client.get(
        "/api/v1/logs/linux/errors",
        headers=admin_headers,
        params={"host_name": "test-host", "newest": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["host"] == "test-host"

    resp = client.get(
        "/api/v1/logs/linux/query",
        headers=admin_headers,
        params={"host_name": "test-host", "source": "syslog", "newest": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "syslog"

    resp = client.get(
        "/api/v1/logs/es/search",
        headers=admin_headers,
        params={"query": "test", "size": 10, "from_": 0},
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    resp = client.get(
        "/api/v1/logs/linux/search",
        headers=admin_headers,
        params={"host_name": "test-host", "keyword": "error", "newest": 10},
    )
    assert resp.status_code == 200
    assert resp.json()["keyword"] == "error"


def test_cloud_router_endpoints(client, admin_headers):
    resp = client.get("/api/v1/platforms/cloud/metrics", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.post(
        "/api/v1/platforms/cloud/collect",
        headers=admin_headers,
        json={"provider": "aws", "region": "us-east-1"},
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "aws"

    resp = client.get("/api/v1/platforms/cloud/history", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.get("/api/v1/platforms/cloud/aws/metrics", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.post("/api/v1/platforms/cloud/aws/collect", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["provider"] == "aws"

    resp = client.get("/api/v1/platforms/cloud/aws/history", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = client.post(
        "/api/v1/platforms/cloud/aws/repair",
        headers=admin_headers,
        json={"action": "restart_instance", "params": {"instance_id": "i-123"}},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.get("/api/v1/platforms/cloud/aws/repair/history", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_integration_router_endpoints(client, admin_headers):
    reg = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "monitoring",
            "name": "Prometheus",
            "config": {"url": "http://localhost:9090"},
            "enabled": True,
        },
    )
    assert reg.status_code == 200, reg.text
    integration_id = reg.json()["integration"]["integration_id"]

    resp = client.get("/api/v1/integration/list", headers=admin_headers)
    assert resp.status_code == 200
    assert any(i["integration_id"] == integration_id for i in resp.json()["integrations"])

    resp = client.post(f"/api/v1/integration/test/{integration_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert "test_result" in resp.json()

    resp = client.delete(f"/api/v1/integration/{integration_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post(
        "/api/v1/integration/notification/send",
        headers=admin_headers,
        json={
            "channel": "email",
            "recipient": "a@b.com",
            "subject": "test",
            "body": "hello",
            "priority": "normal",
        },
    )
    assert resp.status_code == 200
    assert "message" in resp.json()

    resp = client.get("/api/v1/integration/notification/channels", headers=admin_headers)
    assert resp.status_code == 200
    assert "channels" in resp.json()

    webhook = client.post(
        "/api/v1/integration/webhook/register",
        headers=admin_headers,
        json={"source": "github", "event_type": "push", "endpoint": "http://x"},
    )
    assert webhook.status_code == 200
    webhook_id = webhook.json()["webhook_id"]

    resp = client.post(
        "/api/v1/integration/webhook/handle",
        headers=admin_headers,
        params={"webhook_id": webhook_id},
        json={"ref": "main"},
    )
    assert resp.status_code == 200
    assert "result" in resp.json()

    resp = client.get("/api/v1/integration/webhooks", headers=admin_headers)
    assert resp.status_code == 200
    assert any(w["webhook_id"] == webhook_id for w in resp.json()["webhooks"])

    resp = client.post(
        "/api/v1/integration/prometheus/query",
        headers=admin_headers,
        json={"integration_id": integration_id, "query": "up", "time_range": "1h"},
    )
    assert resp.status_code == 200
    assert "query_result" in resp.json()

    resp = client.post(
        "/api/v1/integration/jenkins/trigger",
        headers=admin_headers,
        json={"integration_id": integration_id, "job_name": "build", "parameters": {}},
    )
    assert resp.status_code == 200
    assert "trigger_result" in resp.json()

    resp = client.post(
        "/api/v1/integration/jira/issue",
        headers=admin_headers,
        json={
            "integration_id": integration_id,
            "summary": "bug",
            "description": "desc",
            "issue_type": "Bug",
            "priority": "Medium",
        },
    )
    assert resp.status_code == 200
    assert "creation_result" in resp.json()

    resp = client.get("/api/v1/integration/templates", headers=admin_headers)
    assert resp.status_code == 200
    assert "templates" in resp.json()

    resp = client.get("/api/v1/integration/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert "integration_summary" in resp.json()

    resp = client.get("/api/v1/integration/types", headers=admin_headers)
    assert resp.status_code == 200
    assert "monitoring" in resp.json()["integration_types"]

    resp = client.get("/api/v1/integration/events", headers=admin_headers)
    assert resp.status_code == 200
    assert "events" in resp.json()

    # query_integration: register an AWS integration then exercise cloudwatch branch
    aws = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "cloud",
            "name": "aws",
            "config": {
                "provider": "aws",
                "region": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            },
            "enabled": True,
        },
    )
    assert aws.status_code == 200, aws.text
    aws_id = aws.json()["integration"]["integration_id"]
    import api.integration_router as _ir
    import core.integration_manager as _im

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        _im.integration_manager,
        "query_cloudwatch_metrics",
        _async_return({"values": [1, 2]}),
    )
    resp = client.post(
        f"/api/v1/integration/{aws_id}/query",
        headers=admin_headers,
        json={"query": "cpu", "params": {"time_range": "1h"}},
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "aws"
    monkeypatch.undo()


def test_advanced_ai_router_endpoints(client, admin_headers):
    history = [
        {"timestamp": f"2026-07-01T{i:02d}:00:00Z", "value": float(i % 10)} for i in range(12)
    ]
    resp = client.post(
        "/api/v1/ai-advanced/predict/time-series",
        headers=admin_headers,
        json={"historical_data": history, "prediction_horizon": 24},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "prediction" in data
    assert data["prediction"]["type"] == "time_series"

    resp = client.post(
        "/api/v1/ai-advanced/predict/anomalies",
        headers=admin_headers,
        json={
            "current_data": {"cpu": 95.0},
            "historical_baseline": {"cpu": [10.0] * 20},
            "threshold_std": 2.0,
        },
    )
    assert resp.status_code == 200
    assert "prediction" in resp.json()

    resp = client.post(
        "/api/v1/ai-advanced/learning/update",
        headers=admin_headers,
        json={"new_data": {"x": 1}, "feedback": {"score": 0.9}, "learning_mode": "online"},
    )
    assert resp.status_code == 200
    assert "learning_update" in resp.json()

    conv_resp = client.post(
        "/api/v1/ai-advanced/conversation",
        headers=admin_headers,
        json={
            "user_input": "status",
            "conversation_id": "conv-batch",
            "user_id": "user-1",
        },
    )
    assert conv_resp.status_code == 200
    assert "response" in conv_resp.json()

    resp = client.get("/api/v1/ai-advanced/conversation/conv-batch", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["conversation"]["conversation_id"] == "conv-batch"

    resp = client.post(
        "/api/v1/ai-advanced/explain",
        headers=admin_headers,
        json={
            "decision": "restart_service",
            "decision_context": {"cpu": 95},
            "decision_type": "default",
        },
    )
    assert resp.status_code == 200
    assert "explanation" in resp.json()

    resp = client.post(
        "/api/v1/ai-advanced/knowledge/learn",
        headers=admin_headers,
        json={"experience_data": {"action": "restart"}, "outcome": "success"},
    )
    assert resp.status_code == 200
    assert "learning_result" in resp.json()

    resp = client.get(
        "/api/v1/ai-advanced/knowledge",
        headers=admin_headers,
        params={"limit": 10},
    )
    assert resp.status_code == 200
    assert "items" in resp.json()

    resp = client.get("/api/v1/ai-advanced/statistics", headers=admin_headers)
    assert resp.status_code == 200
    assert "capabilities_summary" in resp.json()

    resp = client.get("/api/v1/ai-advanced/learning/history", headers=admin_headers)
    assert resp.status_code == 200
    assert "recent_updates" in resp.json()

    resp = client.get(
        "/api/v1/ai-advanced/predictions/history",
        headers=admin_headers,
        params={"prediction_type": "time_series", "limit": 10},
    )
    assert resp.status_code == 200
    assert "recent_predictions" in resp.json()

    resp = client.delete("/api/v1/ai-advanced/conversation/conv-batch", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
