# -*- coding: utf-8 -*-
"""Coverage tests for linux_router.py to reach 90%+ coverage."""

import asyncio
from types import SimpleNamespace

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.api]


def _async_return(value):
    """Return an async callable that returns *value*."""

    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    """Return an async callable that raises *exc*."""

    async def _inner(*args, **kwargs):
        raise exc

    return _inner


@pytest.fixture(autouse=True)
def _patch_linux_router(monkeypatch):
    """Patch linux_router dependencies for coverage tests."""
    import api.linux_router as _lrx

    # Default patches
    monkeypatch.setattr(
        _lrx,
        "get_configured_hosts",
        lambda: [{"name": "h1", "host": "1.1.1.1", "role": "app"}],
    )
    monkeypatch.setattr(_lrx, "get_available_metrics", lambda: [{"key": "cpu", "name": "CPU"}])
    monkeypatch.setattr(
        _lrx,
        "collect_all_linux",
        _async_return([{"host": "h1", "cpu": 1.0}]),
    )
    monkeypatch.setattr(
        _lrx,
        "collect_linux_host",
        _async_return({"host": "h1", "cpu": {"usage_percent": 1.0}}),
    )
    monkeypatch.setattr(_lrx, "get_linux_repair_scripts", lambda: [{"key": "clear_tmp"}])
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": True, "output": "ok", "exit_code": 0}),
    )
    # Patch find_linux_host_config for API tests (but not for unit tests of the function itself)
    # We'll conditionally patch this in specific tests
    monkeypatch.setattr(_lrx, "LINUX_HOSTS", {"h1": {"name": "h1", "host": "1.1.1.1"}})


# =============================================================================
# Test LinuxCollectRequest._validate_metrics (lines 84-97)
# =============================================================================


def test_linux_collect_request_metrics_not_list(client):
    """Test line 87: metrics must be a string list."""
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": "not-a-list"},
    )
    assert resp.status_code == 422


def test_linux_collect_request_metrics_too_long(client):
    """Test line 89: metrics list length exceeds _METRICS_LIST_MAX (50)."""
    long_list = [f"metric{i}" for i in range(51)]
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": long_list},
    )
    assert resp.status_code == 422


def test_linux_collect_request_metrics_non_string_items(client):
    """Test line 93: non-string items in metrics list are skipped.

    Note: Pydantic validates list item types before custom validators,
    so this test verifies the Pydantic layer validation (422 response).
    The custom validator at line 93 handles cases where validation is bypassed.
    """
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["cpu", 123, None, "memory"]},
    )
    # Pydantic rejects non-string items before our custom validator runs
    assert resp.status_code == 422


def test_linux_collect_request_metrics_empty_strings(client, monkeypatch):
    """Test lines 95-96: empty/whitespace-only strings are filtered out."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["cpu", "   ", "", "memory"]},
    )
    # Should succeed, empty strings are filtered out
    assert resp.status_code == 200


def test_linux_collect_request_metrics_long_string(client, monkeypatch):
    """Test line 94: strings are truncated to 64 chars."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    long_metric = "a" * 100
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": [long_metric]},
    )
    # Should succeed, string is truncated
    assert resp.status_code == 200


def test_linux_collect_request_metrics_none(client, monkeypatch):
    """Test line 85: metrics=None is allowed."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": None},
    )
    assert resp.status_code == 200


# =============================================================================
# Test list_available_metrics exception handling (lines 176-178)
# =============================================================================


def test_linux_available_metrics_error(client, monkeypatch):
    """Test lines 176-178: exception handling in list_available_metrics."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "get_available_metrics", lambda: (_ for _ in ()).throw(Exception("db error"))
    )
    resp = client.get("/api/v1/platforms/linux/metrics/available")
    assert resp.status_code == 500


def test_linux_hosts(client, monkeypatch):
    """Test line 143: successful hosts list retrieval."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    resp = client.get("/api/v1/platforms/linux/hosts")
    assert resp.status_code == 200


# =============================================================================
# Test collect_all_hosts_endpoint exception handling (lines 225-230)
# =============================================================================


def test_linux_collect_all_cancelled(client, monkeypatch):
    """Test lines 225-227: CancelledError in collect_all_hosts_endpoint."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "collect_all_linux", _async_raise(asyncio.CancelledError()))
    resp = client.get("/api/v1/platforms/linux/collect/all")
    # CancelledError is re-raised, which FastAPI handles as 500
    assert resp.status_code == 500


def test_linux_collect_all_general_error(client, monkeypatch):
    """Test lines 228-230: general exception in collect_all_hosts_endpoint."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "collect_all_linux", _async_raise(RuntimeError("network error")))
    resp = client.get("/api/v1/platforms/linux/collect/all")
    assert resp.status_code == 500


# =============================================================================
# Test collect_single_host exception handling (lines 276-281)
# =============================================================================


def test_linux_collect_host_cancelled(client, monkeypatch):
    """Test lines 276-278: CancelledError in collect_single_host."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "collect_linux_host", _async_raise(asyncio.CancelledError()))
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["cpu"]},
    )
    # CancelledError is re-raised, which FastAPI handles as 500
    assert resp.status_code == 500


def test_linux_collect_host_general_error(client, monkeypatch):
    """Test lines 279-281: general exception in collect_single_host."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "collect_linux_host", _async_raise(RuntimeError("ssh error")))
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["cpu"]},
    )
    assert resp.status_code == 500


# =============================================================================
# Test list_repair_scripts exception handling (lines 322-324)
# =============================================================================


def test_linux_repair_scripts_error(client, monkeypatch):
    """Test lines 322-324: exception handling in list_repair_scripts."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "get_linux_repair_scripts", lambda: (_ for _ in ()).throw(Exception("config error"))
    )
    resp = client.get("/api/v1/platforms/linux/repair/scripts")
    assert resp.status_code == 500


# =============================================================================
# Test run_repair CancelledError (lines 387-388)
# =============================================================================


def test_linux_repair_cancelled(client, monkeypatch):
    """Test lines 387-388: CancelledError in run_repair."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(_lrx, "execute_linux_repair", _async_raise(asyncio.CancelledError()))
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "clear_tmp", "params": {}},
    )
    # CancelledError is re-raised, which FastAPI handles as 500
    assert resp.status_code == 500


# =============================================================================
# Test run_repair blocked without safe_alternative (line 400->402)
# =============================================================================


def test_linux_repair_blocked_no_alternative(client, monkeypatch):
    """Test line 400->402: blocked without safe_alternative."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"blocked": True, "reason": "unsafe", "safe_alternative": ""}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "rm", "params": {}},
    )
    assert resp.status_code == 403
    # Verify that safe_alternative is not in the error message
    data = resp.json()
    message = data.get("error", {}).get("message", data.get("message", data.get("detail", "")))
    assert "安全替代方案" not in message


def test_linux_repair_blocked_with_alternative(client, monkeypatch):
    """Test line 401: blocked with safe_alternative (already covered but verify)."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"blocked": True, "reason": "unsafe", "safe_alternative": "use-rm-safe"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "rm", "params": {}},
    )
    assert resp.status_code == 403
    # Verify that safe_alternative is in the error message
    data = resp.json()
    message = data.get("error", {}).get("message", data.get("message", data.get("detail", "")))
    assert "安全替代方案" in message


# =============================================================================
# Additional edge cases for complete coverage
# =============================================================================


def test_linux_repair_blocked_no_alternative_key(client, monkeypatch):
    """Test blocked when safe_alternative key is missing."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"blocked": True, "reason": "unsafe"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "rm", "params": {}},
    )
    assert resp.status_code == 403
    data = resp.json()
    message = data.get("error", {}).get("message", data.get("message", data.get("detail", "")))
    assert "安全替代方案" not in message


def test_linux_repair_unknown_host_error(client, monkeypatch):
    """Test line 422-424: error message contains '未找到主机'."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "未找到主机 h1"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "clear_tmp", "params": {}},
    )
    assert resp.status_code == 404


def test_linux_repair_param_error_service_name(client, monkeypatch):
    """Test line 425-428: error contains 'service_name'."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "缺少参数 service_name"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "restart", "params": {}},
    )
    assert resp.status_code == 422


def test_linux_repair_param_error_forbidden(client, monkeypatch):
    """Test line 425-428: error contains '禁止操作'."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "禁止操作此进程"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "kill", "params": {}},
    )
    assert resp.status_code == 422


def test_linux_repair_param_error_must_be(client, monkeypatch):
    """Test line 425-428: error contains '必须为'."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "pid 必须为数字"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "kill", "params": {}},
    )
    assert resp.status_code == 422


def test_linux_repair_param_error_not_allowed(client, monkeypatch):
    """Test line 425-428: error contains '不允许'."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    monkeypatch.setattr(
        _lrx,
        "execute_linux_repair",
        _async_return({"success": False, "error": "不允许操作此服务"}),
    )
    resp = client.post(
        "/api/v1/platforms/linux/repair/execute",
        json={"host_name": "h1", "script_key": "restart", "params": {}},
    )
    assert resp.status_code == 422


def test_linux_collect_request_metrics_all_invalid(client):
    """Test when all metrics are invalid (empty/non-string).

    Note: Pydantic validates list item types before custom validators,
    so non-string items are rejected at the Pydantic layer (422 response).
    """
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["", "   ", 123, None]},
    )
    # Pydantic rejects non-string items before our custom validator runs
    assert resp.status_code == 422


def test_linux_collect_request_metrics_whitespace_only(client, monkeypatch):
    """Test metrics with only whitespace characters."""
    import api.linux_router as _lrx

    monkeypatch.setattr(
        _lrx, "find_linux_host_config", lambda host: {"name": host, "host": "1.1.1.1"}
    )
    resp = client.post(
        "/api/v1/platforms/linux/collect/host",
        json={"host_name": "h1", "metrics": ["\t", "\n", "  \t  "]},
    )
    # Should succeed, whitespace-only strings are filtered out
    assert resp.status_code == 200


# =============================================================================
# Unit tests for find_linux_host_config (lines 42-43)
# =============================================================================


def test_find_linux_host_config_dict(monkeypatch):
    """Test line 42: LINUX_HOSTS is a dict."""
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "LINUX_HOSTS", {"h1": {"name": "h1", "host": "1.1.1.1"}})
    result = _lrx.find_linux_host_config("h1")
    assert result is not None
    assert result["name"] == "h1"


def test_find_linux_host_config_list(monkeypatch):
    """Test line 42: LINUX_HOSTS is a list."""
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "LINUX_HOSTS", [{"name": "h1", "host": "1.1.1.1"}])
    result = _lrx.find_linux_host_config("h1")
    assert result is not None
    assert result["name"] == "h1"


def test_find_linux_host_config_not_found(monkeypatch):
    """Test find_linux_host_config returns None for unknown host."""
    import api.linux_router as _lrx

    monkeypatch.setattr(_lrx, "LINUX_HOSTS", {"h1": {"name": "h1", "host": "1.1.1.1"}})
    result = _lrx.find_linux_host_config("unknown")
    assert result is None


# =============================================================================
# Unit tests for LinuxCollectRequest._validate_metrics (lines 87, 93)
# =============================================================================


def test_linux_collect_request_validate_metrics_not_list():
    """Test line 87: direct validator call with non-list raises ValueError."""
    from api.linux_router import LinuxCollectRequest

    with pytest.raises(ValueError, match="metrics 必须是字符串列表"):
        LinuxCollectRequest._validate_metrics("not-a-list")


def test_linux_collect_request_validate_metrics_too_long():
    """Test line 89: direct validator call with too long list raises ValueError."""
    from api.linux_router import LinuxCollectRequest

    long_list = [f"metric{i}" for i in range(51)]
    with pytest.raises(ValueError, match="metrics 列表长度超出"):
        LinuxCollectRequest._validate_metrics(long_list)


def test_linux_collect_request_validate_metrics_non_string():
    """Test line 93: direct validator call filters out non-string items."""
    from api.linux_router import LinuxCollectRequest

    # The validator should skip non-string items (line 93: continue)
    result = LinuxCollectRequest._validate_metrics(["cpu", 123, None, "memory"])
    # Non-string items are filtered out
    assert result == ["cpu", "memory"]


# =============================================================================
# Test LinuxCollectRequest._validate_metrics line 87 directly
# =============================================================================
