# -*- coding: utf-8 -*-
"""测试 core/linux_collector 的 SSH 采集、冷却与解析逻辑"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.linux_collector as lc


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """重置 linux_collector 的模块级状态,避免测试间互相污染。"""
    lc._host_semaphores.clear()
    lc._host_failure_tracker.clear()
    lc._last_collect_cache.clear()
    monkeypatch.setattr(lc, "LINUX_HOSTS", {"hosts": []})


class TestGetHostSemaphore:
    def test_creates_semaphore(self):
        sem = lc._get_host_semaphore("host1")
        assert isinstance(sem, asyncio.Semaphore)

    def test_reuses_semaphore(self):
        sem1 = lc._get_host_semaphore("host1")
        sem2 = lc._get_host_semaphore("host1")
        assert sem1 is sem2


class TestCooldown:
    def test_is_host_in_cooldown_false(self):
        assert lc._is_host_in_cooldown("host1") is False

    def test_is_host_in_cooldown_true(self, monkeypatch):
        lc._host_failure_tracker["host1"] = {
            "count": lc._HOST_MAX_FAILURES,
            "last_fail": lc.time.monotonic(),
        }
        assert lc._is_host_in_cooldown("host1") is True

    def test_record_host_failure(self):
        lc._record_host_failure("host1")
        assert lc._host_failure_tracker["host1"]["count"] == 1

    def test_record_host_success_clears(self):
        lc._host_failure_tracker["host1"] = {"count": 1, "last_fail": 0}
        lc._record_host_success("host1")
        assert "host1" not in lc._host_failure_tracker

    def test_get_host_cooldown_status(self, monkeypatch):
        now = lc.time.monotonic()
        lc._host_failure_tracker["host1"] = {"count": lc._HOST_MAX_FAILURES, "last_fail": now}
        status = lc.get_host_cooldown_status()
        assert status["total_tracked"] == 1
        assert status["stale_hosts"][0]["host"] == "host1"


class TestParseStructuredMetrics:
    def test_cpu_usage(self):
        result = {"metrics": {"cpu_usage": {"value": "45.5\nother"}}}
        lc._parse_structured_metrics(result)
        assert result["metrics"]["cpu_usage"]["parsed"]["usage_percent"] == 45.5

    def test_memory(self):
        result = {"metrics": {"memory": {"value": "8000 4000 2000 50.0"}}}
        lc._parse_structured_metrics(result)
        parsed = result["metrics"]["memory"]["parsed"]
        assert parsed["total_mb"] == 8000
        assert parsed["usage_percent"] == 50.0

    def test_load_avg(self):
        result = {"metrics": {"load_avg": {"value": "0.5 1.2 2.3"}}}
        lc._parse_structured_metrics(result)
        parsed = result["metrics"]["load_avg"]["parsed"]
        assert parsed["load_1min"] == 0.5

    def test_swap(self):
        result = {"metrics": {"swap": {"value": "2048 1024 50.0"}}}
        lc._parse_structured_metrics(result)
        parsed = result["metrics"]["swap"]["parsed"]
        assert parsed["total_mb"] == 2048
        assert parsed["usage_percent"] == 50.0


@pytest.mark.asyncio
class TestSshExecute:
    async def test_invalid_host_config(self):
        result = await lc._ssh_execute("not-a-dict", "cmd")
        assert result.startswith("ERROR:")

    async def test_empty_command(self):
        result = await lc._ssh_execute({"host": "h1", "username": "u"}, "")
        assert result == ""

    async def test_missing_username(self):
        result = await lc._ssh_execute({"host": "h1"}, "cmd")
        assert "username" in result

    async def test_command_not_found(self, monkeypatch):
        monkeypatch.setattr(
            lc.asyncio,
            "create_subprocess_exec",
            AsyncMock(side_effect=FileNotFoundError("no ssh")),
        )
        result = await lc._ssh_execute({"host": "h1", "username": "u", "password": "p"}, "cmd")
        assert result == "SSHPASS_NOT_FOUND"

    async def test_timeout(self, monkeypatch):
        proc = MagicMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        proc.kill = MagicMock()
        proc.wait = AsyncMock()
        monkeypatch.setattr(lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))
        result = await lc._ssh_execute({"host": "h1", "username": "u"}, "cmd")
        assert result == "TIMEOUT"

    async def test_success(self, monkeypatch):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"stdout data", b""))
        monkeypatch.setattr(lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))
        result = await lc._ssh_execute({"host": "h1", "username": "u"}, "cmd")
        assert result == "stdout data"

    async def test_with_key_file(self, monkeypatch):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"ok", b""))
        monkeypatch.setattr(lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))
        result = await lc._ssh_execute({"host": "h1", "username": "u", "key_file": "/key"}, "cmd")
        assert result == "ok"


@pytest.mark.asyncio
class TestSshExecuteBatch:
    async def test_empty(self):
        result = await lc._ssh_execute_batch({}, {})
        assert result == {}

    async def test_failed(self, monkeypatch):
        monkeypatch.setattr(lc, "_ssh_execute", AsyncMock(return_value="TIMEOUT"))
        result = await lc._ssh_execute_batch({"host": "h1"}, {"cpu": "top"})
        assert result["cpu"] == "TIMEOUT"

    async def test_success(self, monkeypatch):
        monkeypatch.setattr(lc.secrets, "token_hex", lambda n: "123")
        raw = "===AIOPS123METRIC:cpu:123===AIOPSEND===\n45.2\n"
        monkeypatch.setattr(lc, "_ssh_execute", AsyncMock(return_value=raw))
        result = await lc._ssh_execute_batch({"host": "h1"}, {"cpu": "top"})
        assert "cpu" in result
        assert "45.2" in result["cpu"]


@pytest.mark.asyncio
class TestCollectLinuxHost:
    async def test_invalid_host(self):
        result = await lc.collect_linux_host("not-a-dict")
        assert result["status"] == "error"

    async def test_missing_host(self):
        result = await lc.collect_linux_host({"name": "h1"})
        assert result["status"] == "error"

    async def test_cooldown_no_cache(self):
        lc._host_failure_tracker["h1"] = {
            "count": lc._HOST_MAX_FAILURES,
            "last_fail": lc.time.monotonic(),
        }
        result = await lc.collect_linux_host({"name": "h1", "host": "1.2.3.4"})
        assert result["status"] == "cooldown"

    async def test_cooldown_with_cache(self, monkeypatch):
        lc._host_failure_tracker["h1"] = {
            "count": lc._HOST_MAX_FAILURES,
            "last_fail": lc.time.monotonic(),
        }
        lc._last_collect_cache["h1"] = {"name": "h1", "host": "1.2.3.4", "metrics": {}}
        result = await lc.collect_linux_host({"name": "h1", "host": "1.2.3.4"})
        assert result["status"] == "cached_stale"

    async def test_skipped_no_auth(self):
        result = await lc.collect_linux_host({"name": "h1", "host": "1.2.3.4"})
        assert result["status"] == "skipped"

    async def test_no_valid_metrics(self):
        result = await lc.collect_linux_host(
            {"name": "h1", "host": "1.2.3.4", "password": "p"}, metrics=["unknown"]
        )
        assert result["status"] == "error"

    async def test_success(self, monkeypatch):
        monkeypatch.setattr(lc, "_ssh_execute_batch", AsyncMock(return_value={"cpu_usage": "45.2"}))
        result = await lc.collect_linux_host(
            {"name": "h1", "host": "1.2.3.4", "password": "p"}, metrics=["cpu_usage"]
        )
        assert result["status"] == "ok"
        assert result["metrics"]["cpu_usage"]["value"] == "45.2"

    async def test_degraded(self, monkeypatch):
        monkeypatch.setattr(
            lc,
            "_ssh_execute_batch",
            AsyncMock(return_value={"cpu_usage": "", "load_avg": "", "memory": "ok"}),
        )
        result = await lc.collect_linux_host(
            {"name": "h1", "host": "1.2.3.4", "password": "p"},
            metrics=["cpu_usage", "load_avg", "memory"],
        )
        assert result["status"] == "degraded"

    async def test_error(self, monkeypatch):
        monkeypatch.setattr(
            lc, "_ssh_execute_batch", AsyncMock(return_value={"cpu_usage": "TIMEOUT"})
        )
        result = await lc.collect_linux_host(
            {"name": "h1", "host": "1.2.3.4", "password": "p"}, metrics=["cpu_usage"]
        )
        assert result["status"] == "error"


@pytest.mark.asyncio
class TestCollectAllLinux:
    async def test_no_hosts(self):
        lc.LINUX_HOSTS = {"hosts": []}
        result = await lc.collect_all_linux()
        assert result == []

    async def test_with_hosts(self, monkeypatch):
        lc.LINUX_HOSTS = {"hosts": [{"name": "h1", "host": "1.2.3.4", "password": "p"}]}
        monkeypatch.setattr(lc, "_ssh_execute_batch", AsyncMock(return_value={"cpu_usage": "45"}))
        result = await lc.collect_all_linux(metrics=["cpu_usage"])
        assert len(result) == 1
        assert result[0]["status"] == "ok"

    async def test_host_exception(self, monkeypatch):
        lc.LINUX_HOSTS = {"hosts": [{"name": "h1", "host": "1.2.3.4"}]}
        monkeypatch.setattr(lc, "collect_linux_host", AsyncMock(side_effect=RuntimeError("boom")))
        result = await lc.collect_all_linux(metrics=["cpu_usage"])
        assert result[0]["status"] == "error"


class TestQueryHelpers:
    def test_get_available_metrics(self):
        result = lc.get_available_metrics()
        assert len(result) == len(lc.COLLECT_COMMANDS)
        assert "cpu_usage" in {r["key"] for r in result}

    def test_get_configured_hosts(self, monkeypatch):
        lc.LINUX_HOSTS = {
            "hosts": [{"name": "h1", "host": "1.2.3.4", "port": 22, "username": "u", "role": "app"}]
        }
        result = lc.get_configured_hosts()
        assert result[0]["name"] == "h1"
        assert result[0]["auth"] == "none"
