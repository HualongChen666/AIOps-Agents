# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.alert_engine and core.authentication."""

import asyncio
import datetime
import importlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException

import core.alert_engine as ae
import core.authentication as auth

pytestmark = [pytest.mark.core]


@pytest.fixture(autouse=True)
def _reset_global_state(monkeypatch):
    """Reset shared caches and external clients before each test."""
    ae._dedup_cache.clear()
    ae._ssh_failed_window.clear()
    ae._ssh_last_alert_time.clear()
    ae._ws_subscribers.clear()
    ae.alert_history.clear()
    ae.alert_repository = None
    ae.ALERT_INTELLIGENCE_AVAILABLE = False
    ae.alert_intelligence_engine = None

    auth._token_blacklist.clear()
    auth.redis_client = None
    auth._redis_available = False
    yield


# ---------------------------------------------------------------------------
# core.alert_engine
# ---------------------------------------------------------------------------


def test_safe_float():
    assert ae._safe_float(None, 5.0) == 5.0
    assert ae._safe_float(42, 0.0) == 42.0
    assert ae._safe_float("3.14", 0.0) == 3.14
    assert ae._safe_float("nope", 0.0) == 0.0


def test_check_and_generate_alerts_empty_and_bad_input():
    assert ae.check_and_generate_alerts(None) == []
    assert ae.check_and_generate_alerts("bad") == []


def test_check_and_generate_alerts_thresholds(monkeypatch):
    monkeypatch.setattr(ae, "_CPU_WARN_THRESHOLD", 80.0)
    monkeypatch.setattr(ae, "_MEM_WARN_THRESHOLD", 85.0)
    monkeypatch.setattr(ae, "_DISK_WARN_THRESHOLD", 90.0)
    monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})

    metrics = {
        "cpu": {"usage_percent": 95.0},
        "memory": {"usage_percent": 86.0, "used_gb": 4, "total_gb": 8},
        "disk": [
            {"device": "C:", "usage_percent": 50.0, "used_gb": 10, "total_gb": 100},
            {"device": "D:", "usage_percent": 99.0, "used_gb": 9, "total_gb": 10},
        ],
    }
    alerts = ae.check_and_generate_alerts(metrics)
    assert len(alerts) == 3
    assert any(a["metric"] == "cpu_percent" and a["level"] == "critical" for a in alerts)
    assert any(a["metric"] == "memory_percent" and a["level"] == "warning" for a in alerts)
    assert any(a["metric"] == "disk_percent" and a["level"] == "critical" for a in alerts)


def test_check_and_generate_alerts_dynamic_threshold(monkeypatch):
    monkeypatch.setattr(
        ae,
        "DYNAMIC_THRESHOLD_CONFIG",
        {"enabled": True, "min_samples": 1, "sigma": 2.0, "flat_boost": 5.0},
    )
    monkeypatch.setattr(
        ae.metrics_history,
        "get_dynamic_threshold",
        MagicMock(
            return_value=(70.0, {"source": "history", "samples": 100, "mean": 50.0, "std": 2.0})
        ),
    )
    alerts = ae.check_and_generate_alerts({"cpu": {"usage_percent": 80.0}})
    assert any(a["metric"] == "cpu_percent" for a in alerts)


def test_check_and_generate_alerts_non_dict_fallbacks(monkeypatch):
    monkeypatch.setattr(ae, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": False})
    alerts = ae.check_and_generate_alerts({"cpu": "bad", "memory": None, "disk": "bad"})
    assert alerts == []


def test_dedup_key_and_try_dedup(monkeypatch):
    monkeypatch.setattr(ae, "_DEDUP_WINDOW_SEC", 60)
    monkeypatch.setattr(ae, "_DEDUP_CACHE_MAX", 2)

    a1 = {"metric": "cpu_percent", "level": "critical"}
    assert ae._try_dedup(a1) is False
    assert ae._try_dedup(a1) is True  # deduped within window

    a2 = {"metric": "disk_percent", "level": "warning", "id": "DISK-C:-12:00:00"}
    assert ae._dedup_key(a2).startswith("disk_percent_warning_")
    assert ae._try_dedup(a2) is False

    # prev_suppressed when previous window is stale
    key = ae._dedup_key(a1)
    ae._dedup_cache[key] = {
        "last_time": datetime.datetime.now() - datetime.timedelta(seconds=120),
        "repeat_count": 3,
        "last_alert": {},
    }
    a1_copy = {"metric": "cpu_percent", "level": "critical"}
    assert ae._try_dedup(a1_copy) is False
    assert a1_copy.get("prev_suppressed") == 3

    # capacity eviction
    ae._dedup_cache.clear()
    ae._try_dedup({"metric": "m1", "level": "warning"})
    ae._try_dedup({"metric": "m2", "level": "warning"})
    # should evict oldest when inserting third
    ae._try_dedup({"metric": "m3", "level": "warning"})
    assert len(ae._dedup_cache) <= 2


def test_get_dedup_stats_and_clear():
    ae._try_dedup({"metric": "x", "level": "critical"})
    stats = ae.get_dedup_stats()
    assert stats["cache_size"] >= 1
    assert "active_windows" in stats
    assert ae.clear_dedup_cache() >= 0


def test_check_ssh_brute_force(monkeypatch):
    host = "web01"
    monkeypatch.setattr(ae, "_SSH_FAIL_THRESHOLD", 10)
    monkeypatch.setattr(ae, "_SSH_ALERT_COOLDOWN_SEC", 600)

    # first sample, no alert
    assert ae._check_ssh_brute_force(host, 0) is None
    # large increment triggers
    alert = ae._check_ssh_brute_force(host, 20)
    assert alert is not None
    assert alert["metric"] == "ssh_failed_logins"

    # still in cooldown
    assert ae._check_ssh_brute_force(host, 35) is None

    # reset cooldown to far past and trigger again
    ae._ssh_last_alert_time[host] = datetime.datetime.now() - datetime.timedelta(seconds=700)
    alert2 = ae._check_ssh_brute_force(host, 40)
    assert alert2 is not None

    # auth.log rotation: count drops
    assert ae._check_ssh_brute_force(host, 5) is None


def test_cleanup_ssh_brute_force_cache(monkeypatch):
    monkeypatch.setattr(ae, "_SSH_CACHE_EXPIRY_SEC", 1)
    monkeypatch.setattr(ae, "_SSH_CACHE_MAX_HOSTS", 2)

    old = datetime.datetime.now() - datetime.timedelta(seconds=5)
    ae._ssh_failed_window["old"] = [(old, 0)]
    ae._ssh_last_alert_time["old"] = old

    now = datetime.datetime.now()
    ae._ssh_failed_window["new1"] = [(now, 0)]
    ae._ssh_failed_window["new2"] = [(now, 0)]
    ae._ssh_failed_window["new3"] = [(now, 0)]

    ae._cleanup_ssh_brute_force_cache()
    assert "old" not in ae._ssh_failed_window
    assert len(ae._ssh_failed_window) <= 2


def test_restore_alert_cache(monkeypatch):
    repo = MagicMock(get_recent=AsyncMock(return_value=[{"id": "1"}, {"id": "2"}]))
    monkeypatch.setattr(ae, "alert_repository", repo)
    asyncio.run(ae._restore_alert_cache())
    assert len(ae.alert_history) == 2
    repo.get_recent.assert_awaited_once_with(limit=ae.ALERT_HISTORY_MAX)

    # exception path
    ae.alert_history.clear()
    repo = MagicMock(get_recent=AsyncMock(side_effect=Exception("db")))
    monkeypatch.setattr(ae, "alert_repository", repo)
    asyncio.run(ae._restore_alert_cache())
    assert len(ae.alert_history) == 0


async def test_get_summary_metrics(monkeypatch):
    monkeypatch.setattr("core.stats_engine.get_real_summary", AsyncMock(return_value={"ok": True}))
    result = await ae.get_summary_metrics()
    assert result["ok"] is True


def test_ws_register_unregister_and_broadcast():
    ws = MagicMock()
    ae.register_ws(ws)
    assert ws in ae._ws_subscribers
    ae.unregister_ws(ws)
    assert ws not in ae._ws_subscribers

    # empty broadcast short-circuits
    asyncio.run(ae.broadcast({"type": "test"}))

    good_ws = AsyncMock()
    bad_ws = AsyncMock()
    bad_ws.send_text.side_effect = Exception("dead")
    ae.register_ws(good_ws)
    ae.register_ws(bad_ws)
    asyncio.run(ae.broadcast({"type": "msg"}))
    good_ws.send_text.assert_awaited_once()
    assert bad_ws not in ae._ws_subscribers


async def test_check_linux_security_alerts(monkeypatch):
    repo = MagicMock(save=AsyncMock())
    monkeypatch.setattr(ae, "alert_repository", repo)
    monkeypatch.setattr("core.notify_engine.send_alert_notification", AsyncMock(return_value="ok"))
    monkeypatch.setattr(
        "core.auto_heal.try_auto_heal", AsyncMock(return_value={"status": "dispatched"})
    )

    results = [
        None,
        "not-a-dict",
        {"status": "error", "name": "h0"},
        {"status": "ok", "name": "h1", "metrics": "bad"},
        {"status": "ok", "name": "h2", "metrics": {"ssh_failed_logins": "ERROR"}},
        {"status": "ok", "name": "h3", "metrics": {"ssh_failed_logins": {"value": "abc"}}},
        {"status": "ok", "name": "h4", "metrics": {"ssh_failed_logins": {"value": "15"}}},
    ]
    alerts = await ae.check_linux_security_alerts(results)
    assert len(alerts) == 1
    assert alerts[0]["host"] == "h4"
    repo.save.assert_awaited()

    # persistence failure path
    repo = MagicMock(save=AsyncMock(side_effect=Exception("db")))
    monkeypatch.setattr(ae, "alert_repository", repo)
    alerts = await ae.check_linux_security_alerts(
        [{"status": "ok", "name": "h5", "metrics": {"ssh_failed_logins": {"value": "25"}}}]
    )
    assert len(alerts) == 1


async def test_alert_monitor_loop(monkeypatch):
    metrics = {
        "cpu": {"usage_percent": 95.0},
        "memory": {"usage_percent": 60.0},
        "network": {"recv_speed_mb": 1.0},
        "disk": [{"usage_percent": 55.0}],
        "top_processes": [1, 2, 3],
    }
    monkeypatch.setattr(
        ae, "collect_all", MagicMock(side_effect=[metrics, asyncio.CancelledError()])
    )
    monkeypatch.setattr(ae, "alert_repository", AsyncMock())
    monkeypatch.setattr(ae, "record_ingestion", MagicMock())
    monkeypatch.setattr(ae, "record_alert_noise", MagicMock())
    monkeypatch.setattr(ae.metrics_history, "push", MagicMock())
    monkeypatch.setattr(ae.metrics_history, "to_dict", MagicMock(return_value=[]))
    monkeypatch.setattr("core.stats_engine.get_real_summary", AsyncMock(return_value={}))
    monkeypatch.setattr("core.notify_engine.send_alert_notification", AsyncMock(return_value="ok"))
    monkeypatch.setattr(
        "core.auto_heal.try_auto_heal", AsyncMock(return_value={"healed": True, "rule": "x"})
    )
    monkeypatch.setattr("asyncio.sleep", AsyncMock(return_value=None))

    monkeypatch.setattr(ae, "ALERT_INTELLIGENCE_AVAILABLE", True)
    monkeypatch.setattr(
        ae,
        "alert_intelligence_engine",
        MagicMock(analyze_and_aggregate_alerts=AsyncMock(side_effect=lambda alerts: alerts)),
    )

    await ae.alert_monitor_loop()
    ae.record_ingestion.assert_called()
    ae.record_alert_noise.assert_called()


async def test_alert_monitor_loop_exception(monkeypatch):
    monkeypatch.setattr(
        ae, "collect_all", MagicMock(side_effect=[Exception("boom"), asyncio.CancelledError()])
    )
    monkeypatch.setattr("asyncio.sleep", AsyncMock(return_value=None))
    await ae.alert_monitor_loop()


def test_cleanup_dedup_cache():
    now = datetime.datetime.now()
    ae._dedup_cache["stale"] = {
        "last_time": now - datetime.timedelta(seconds=9999),
        "repeat_count": 0,
        "last_alert": {},
    }
    ae._cleanup_dedup_cache()
    assert "stale" not in ae._dedup_cache


def test_alert_topology_correlation():
    topo = ae.AlertTopologyCorrelation()
    alerts = [
        {"source": "host1", "type": "cpu_high"},
        {"source": "host1", "type": "disk_high"},
    ]
    graph = topo.build_topology_from_alerts(alerts)
    assert "host1" in graph
    roots = topo.correlate_alerts_with_topology({"source": "host1"})
    impact = topo.get_impact_analysis({"source": "storage"})
    assert "affected_services" in impact


def test_automatic_alert_router():
    router = ae.AutomaticAlertRouter()
    router.add_route("cpu", {"severity": "critical"}, "email", priority=10)
    router.add_route("mem", {"severity": "warning"}, "webhook", priority=5)
    channels = router.route_alert({"id": "a1", "severity": "critical"})
    assert "email" in channels
    assert router.get_routing_stats()["total_routes"] == 1


async def test_alert_trend_predictor():
    pred = ae.AlertTrendPredictor(model=ae.TrendPredictionModel.LINEAR_REGRESSION)
    for i in range(15):
        pred.add_historical_data("m1", float(i))
    result = pred.predict_trend("m1", 3)
    assert result is not None
    assert result.trend_direction == "increasing"
    summary = pred.get_prediction_summary()
    assert summary["metrics_with_predictions"] == 1


# ---------------------------------------------------------------------------
# core.authentication
# ---------------------------------------------------------------------------


def test_parse_int_and_get_environment(monkeypatch):
    monkeypatch.setenv("TEST_INT_X", "abc")
    assert auth._parse_int_with_default("TEST_INT_X", 7) == 7
    monkeypatch.setenv("TEST_INT_X", "12")
    assert auth._parse_int_with_default("TEST_INT_X", 7) == 12

    monkeypatch.setenv("ENVIRONMENT", "PROD")
    assert auth._get_environment() == "prod"
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert auth._get_environment() == "development"


def test_pwd_context_and_hash_verify():
    hashed = auth.hash_password("ValidPass123!")
    assert hashed
    assert auth.verify_password("ValidPass123!", hashed) is True
    assert auth.verify_password("wrong", hashed) is False
    assert auth.hash_password("") == ""
    assert auth.verify_password("", "") is False
    assert auth.verify_password("x", "not-a-hash") is False


def test_validate_password_complexity():
    assert auth.validate_password_complexity("short1!")[0] is False
    assert auth.validate_password_complexity("NoSpecial123")[0] is False
    assert auth.validate_password_complexity("password")[0] is False
    ok, msg = auth.validate_password_complexity("StrongPass123!")
    assert ok is True
    assert msg == ""


def test_create_and_verify_token():
    assert auth.create_access_token({}) == ""
    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    payload = auth.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["type"] == "access"

    assert auth.verify_token("") is None
    assert auth.verify_token("not.a.token") is None

    bad_type = auth.create_access_token({"sub": "u", "type": "other"})
    # type is overwritten to access by create_access_token, so build a token manually
    no_jti = jwt.encode(
        {
            "sub": "u",
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    assert auth.verify_token(no_jti) is None

    expired = auth.create_access_token({"sub": "u"}, expires_delta=datetime.timedelta(seconds=-1))
    assert auth.verify_token(expired) is None


def test_refresh_access_token():
    refresh = auth.create_refresh_token({"sub": "admin"})
    new_access = auth.refresh_access_token(refresh)
    assert new_access
    assert auth.verify_token(new_access) is not None
    assert auth.refresh_access_token("invalid") is None
    access = auth.create_access_token({"sub": "admin"})
    assert auth.refresh_access_token(access) is None


def test_decode_for_revocation():
    now = datetime.datetime.now(datetime.timezone.utc)
    token = jwt.encode(
        {"sub": "u", "exp": now + datetime.timedelta(hours=1), "iat": now},
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    payload = auth._decode_for_revocation(token)
    assert payload["sub"] == "u"


async def test_revoke_and_is_token_revoked(monkeypatch):
    token = auth.create_access_token({"sub": "u", "jti": str(uuid.uuid4())})

    # redis path
    redis_mock = MagicMock()
    await auth.revoke_token(token, redis_client=redis_mock)
    assert redis_mock.setex.called

    # memory fallback
    auth._token_blacklist.clear()
    monkeypatch.setattr(auth, "_get_redis_client", lambda: None)
    await auth.revoke_token(token, redis_client=None)
    assert token in auth._token_blacklist
    assert await auth.is_token_revoked(token, redis_client=None) is True

    # invalid token
    await auth.revoke_token("not.valid", redis_client=None)
    assert await auth.is_token_revoked("not.valid", redis_client=None) is False


async def test_is_token_revoked_memory_expiry(monkeypatch):
    monkeypatch.setattr(auth, "_get_redis_client", lambda: None)
    token = auth.create_access_token({"sub": "u", "jti": str(uuid.uuid4())})
    auth.redis_client = None
    auth._redis_available = False
    auth._token_blacklist[token] = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(hours=2)
    assert await auth.is_token_revoked(token, redis_client=None) is False
    assert token not in auth._token_blacklist

    payload = auth._decode_for_revocation(token)
    jti = payload.get("jti")
    auth._token_blacklist[f"jti:{jti}"] = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(hours=2)
    assert await auth.is_token_revoked(token, redis_client=None) is False
    assert f"jti:{jti}" not in auth._token_blacklist


def test_get_redis_client(monkeypatch):
    auth.redis_client = None
    auth._redis_available = False
    monkeypatch.setattr(
        "core.authentication.redis.Redis", MagicMock(return_value=MagicMock(ping=MagicMock()))
    )
    assert auth._get_redis_client() is not None

    auth.redis_client = None
    monkeypatch.setattr(
        "core.authentication.redis.Redis", MagicMock(side_effect=auth.redis.ConnectionError("down"))
    )
    assert auth._get_redis_client() is None


def test_is_ip_allowed(monkeypatch):
    monkeypatch.setenv("IP_WHITELIST", "*")
    assert auth.is_ip_allowed("anything") is True

    monkeypatch.setenv("IP_WHITELIST", "192.168.1.0/24,10.0.0.0/8")
    assert auth.is_ip_allowed("192.168.1.5") is True
    assert auth.is_ip_allowed("10.0.0.5") is True
    assert auth.is_ip_allowed("1.2.3.4") is False
    assert auth.is_ip_allowed("") is False


async def test_get_user(monkeypatch):
    mock_user = MagicMock(
        id=1,
        username="admin",
        full_name=None,
        email=None,
        disabled=False,
        role="admin",
        hashed_password="x",
        mfa_enabled=False,
    )
    monkeypatch.setattr(
        "core.user_service.user_service",
        MagicMock(get_user_by_username=AsyncMock(return_value=mock_user)),
    )
    user = await auth.get_user("admin")
    assert user is not None
    assert user.username == "admin"

    monkeypatch.setattr(
        "core.user_service.user_service",
        MagicMock(get_user_by_username=AsyncMock(return_value=None)),
    )
    assert await auth.get_user("admin") is None


def test_get_user_by_username(monkeypatch):
    monkeypatch.setattr(auth, "get_user", MagicMock(return_value="user"))
    assert auth.get_user_by_username("u") == "user"
    monkeypatch.setattr(auth, "get_user", MagicMock(side_effect=Exception("x")))
    assert auth.get_user_by_username("u") is None


def test_authenticate_user(monkeypatch):
    pwd = auth.hash_password("pass123")
    user = auth.UserInDB(username="u", hashed_password=pwd, disabled=False, role="user")
    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(return_value=user))
    assert auth.authenticate_user("u", "pass123") is not None
    assert auth.authenticate_user("u", "wrong") is None

    # dict user
    monkeypatch.setattr(
        auth,
        "get_user_by_username",
        MagicMock(return_value={"is_active": True, "hashed_password": pwd}),
    )
    assert auth.authenticate_user("u", "pass123") is not None
    monkeypatch.setattr(
        auth,
        "get_user_by_username",
        MagicMock(return_value={"is_active": False, "hashed_password": pwd}),
    )
    assert auth.authenticate_user("u", "pass123") is None

    # fallback to get_user
    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(return_value=None))
    monkeypatch.setattr(auth, "get_user", MagicMock(return_value=user))
    assert auth.authenticate_user("u", "pass123") is not None

    # exception
    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(side_effect=Exception("boom")))
    assert auth.authenticate_user("u", "x") is None


async def test_get_current_user(monkeypatch):
    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
    user = auth.UserInDB(username="admin", hashed_password="x", disabled=False, role="admin")
    monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=user))
    result = await auth.get_current_user(token=token)
    assert result.username == "admin"

    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=True))
    with pytest.raises(HTTPException):
        await auth.get_current_user(token=token)

    with pytest.raises(HTTPException):
        await auth.get_current_user(token="bad.token")

    no_sub = auth.create_access_token({"role": "admin"})
    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
    with pytest.raises(HTTPException):
        await auth.get_current_user(token=no_sub)


async def test_get_current_active_user(monkeypatch):
    active = auth.User(username="u", role="user", disabled=False)
    result = await auth.get_current_active_user(current_user=active)
    assert result.username == "u"

    disabled = auth.User(username="u", role="user", disabled=True)
    with pytest.raises(HTTPException):
        await auth.get_current_active_user(current_user=disabled)

    monkeypatch.setattr(auth, "verify_token", MagicMock(return_value={"sub": "u"}))
    monkeypatch.setattr(
        auth,
        "get_user_by_username",
        MagicMock(return_value={"is_active": True, "hashed_password": "x"}),
    )
    result = await auth.get_current_active_user(current_user=None, token="tok")
    assert result is not None

    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(return_value=None))
    assert await auth.get_current_active_user(current_user=None, token="tok") is None


async def test_verify_ip_whitelist():
    req = MagicMock(client=MagicMock(host="127.0.0.1"))
    assert await auth.verify_ip_whitelist(req) is None

    req = MagicMock(client=MagicMock(host="1.2.3.4"))
    with pytest.raises(HTTPException):
        await auth.verify_ip_whitelist(req)


async def test_role_required():
    admin = auth.User(username="a", role="admin")
    user = auth.User(username="u", role="user")
    verifier = auth.role_required("admin")
    assert (await verifier(current_user=admin)).username == "a"
    with pytest.raises(HTTPException):
        await verifier(current_user=user)


async def test_jwt_auth_service(monkeypatch):
    service = auth.JWTAuthService()
    token = service.create_access_token({"sub": "admin"})
    assert token
    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
    user = auth.UserInDB(username="admin", hashed_password="x", disabled=False, role="admin")
    monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=user))
    u = await service.get_current_user(token)
    assert u["username"] == "admin"

    assert await service.verify_permission({"role": "admin"}, auth.Permission.ADMIN) is True
    assert await service.verify_permission({"role": "user"}, auth.Permission.WRITE) is False
    assert await service.verify_role({"role": "admin"}, "admin") is True

    monkeypatch.setattr(auth, "authenticate_user", MagicMock(return_value=user))
    info = await service.authenticate_user("admin", "pass")
    assert info["username"] == "admin"


async def test_login_and_revoke_endpoints(monkeypatch):
    user = auth.UserInDB(username="admin", hashed_password="x", disabled=False, role="admin")
    monkeypatch.setattr(auth, "authenticate_user", MagicMock(return_value=user))
    result = await auth.login_for_access_token(username="admin", password="pass")
    assert "access_token" in result

    monkeypatch.setattr(auth, "authenticate_user", MagicMock(return_value=None))
    with pytest.raises(HTTPException):
        await auth.login_for_access_token(username="admin", password="pass")

    monkeypatch.setattr(auth, "revoke_token", AsyncMock())
    revoke_result = await auth.revoke_current_token(current_user=user, token="tok")
    assert revoke_result["detail"] == "Token revoked successfully"


async def test_tenant_context_and_sso():
    ctx = auth.TenantContext()
    cfg = await ctx.get_tenant_config("t1")
    assert cfg["tenant_id"] == "t1"
    assert await ctx.validate_tenant_access("t1", "u1") is True

    sso = auth.SSOProvider()
    assert await sso.authenticate_with_sso("oidc", "t") is not None
    assert await sso.authenticate_with_sso("saml", "t") is None
    assert "oidc" in (await sso.generate_sso_link("oidc", "http://app/cb"))
    assert await sso.generate_sso_link("saml", "http://app/cb") is None


async def test_abac_policy():
    policy = auth.ABACPolicy()
    assert await policy.evaluate_access({"role": "admin"}, "alerts", "delete") is True
    assert await policy.evaluate_access({"role": "operator"}, "repairs", "execute") is True
    assert await policy.evaluate_access({"role": "viewer"}, "alerts", "delete") is False
    assert await policy.evaluate_access({"role": "viewer"}, "metrics", "read") is True
    assert await policy.evaluate_access({"role": "unknown"}, "alerts", "read") is False


async def test_compliance_manager():
    mgr = auth.ComplianceManager()
    await mgr.log_audit_event("login", "u1", "auth", "read")
    iso = await mgr.run_compliance_check(auth.ComplianceFramework.ISO27001)
    assert iso["overall_status"] == "pass"
    soc2 = await mgr.run_compliance_check(auth.ComplianceFramework.SOC2)
    assert soc2["framework"] == "soc2"
    hipaa = await mgr.run_compliance_check(auth.ComplianceFramework.HIPAA)
    assert any(c["name"] == "unsupported" for c in hipaa["checks"])

    now = datetime.datetime.now(datetime.timezone.utc)
    report = await mgr.get_audit_report(
        start_date=now - datetime.timedelta(days=1), end_date=now + datetime.timedelta(days=1)
    )
    assert report["total_events"] == 1
    assert report["summary"]["by_user"]["u1"] == 1


async def test_jwt_auth_service_failures(monkeypatch):
    service = auth.JWTAuthService()
    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=True))
    assert await service.get_current_user(token) is None

    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=None))
    assert await service.get_current_user(token) is None

    no_sub = auth.create_access_token({"role": "admin"})
    assert await service.get_current_user(no_sub) is None
    assert await service.get_current_user("bad.token") is None

    monkeypatch.setattr(auth, "authenticate_user", MagicMock(return_value=None))
    assert await service.authenticate_user("u", "p") is None


async def test_get_current_user_not_found(monkeypatch):
    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=None))
    with pytest.raises(HTTPException):
        await auth.get_current_user(token=token)


async def test_get_current_active_user_branches(monkeypatch):
    monkeypatch.setattr(auth, "verify_token", MagicMock(return_value={"sub": "u"}))
    monkeypatch.setattr(
        auth, "get_user_by_username", MagicMock(return_value={"hashed_password": "x"})
    )
    result = await auth.get_current_active_user(current_user=None, token="tok")
    assert result == {"hashed_password": "x"}

    monkeypatch.setattr(auth, "verify_token", MagicMock(return_value=None))
    assert await auth.get_current_active_user(current_user=None, token="tok") is None

    assert await auth.get_current_active_user(current_user="not-a-user", token=None) is None
    good_user = auth.User(username="u", role="user", disabled=False)
    assert await auth.get_current_active_user(current_user=good_user, token=None) == good_user


def test_verify_token_branches():
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=1)
    bad_type = jwt.encode(
        {
            "sub": "u",
            "exp": exp,
            "iat": now,
            "iss": auth.JWT_ISSUER,
            "aud": auth.JWT_AUDIENCE,
            "type": "other",
            "jti": "x",
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    assert auth.verify_token(bad_type) is None

    no_jti = jwt.encode(
        {
            "sub": "u",
            "exp": exp,
            "iat": now,
            "iss": auth.JWT_ISSUER,
            "aud": auth.JWT_AUDIENCE,
            "type": "access",
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    assert auth.verify_token(no_jti) is None


def test_authenticate_user_disabled_object(monkeypatch):
    pwd = auth.hash_password("pass123")
    user = auth.UserInDB(username="u", hashed_password=pwd, disabled=True, role="user")
    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(return_value=user))
    assert auth.authenticate_user("u", "pass123") is None

    monkeypatch.setattr(auth, "get_user_by_username", MagicMock(return_value=None))
    monkeypatch.setattr(auth, "get_user", MagicMock(return_value=None))
    assert auth.authenticate_user("u", "pass123") is None


async def test_compliance_frameworks():
    mgr = auth.ComplianceManager()
    gdpr = await mgr.run_compliance_check(auth.ComplianceFramework.GDPR)
    assert gdpr["framework"] == "gdpr"
    report = await mgr.get_audit_report()
    assert "total_events" in report
    report_start = await mgr.get_audit_report(
        start_date=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    )
    assert report_start["period"]["start"] is not None


def test_authentication_module_reload(monkeypatch):
    original_key = "test-secret-key"
    # empty dev -> generated key
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "development")
    importlib.reload(auth)
    assert auth.SECRET_KEY

    # insecure value in dev -> warning path
    monkeypatch.setenv("JWT_SECRET_KEY", "default-secret-key")
    importlib.reload(auth)
    assert auth.SECRET_KEY

    # production without key raises
    monkeypatch.setenv("JWT_SECRET_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValueError):
        importlib.reload(auth)

    # restore safe state
    monkeypatch.setenv("JWT_SECRET_KEY", original_key)
    monkeypatch.setenv("ENVIRONMENT", "development")
    importlib.reload(auth)
