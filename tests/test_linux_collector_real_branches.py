# -*- coding: utf-8 -*-
"""Real branch tests for core/linux_collector.py using real data and no mocks."""

import asyncio
import importlib
import os
import socket
import threading
import time
from typing import Any

import pytest

import config as _config_module
import core.linux_collector as lc


@pytest.fixture(autouse=True)
def _cleanup_lc_state():
    """Save and restore the module-level global state so tests stay isolated."""
    saved = {
        "path": os.environ.get("PATH", ""),
        "ssh_timeout": lc.LINUX_SSH_TIMEOUT,
        "hosts": lc.LINUX_HOSTS,
        "semaphores": dict(lc._host_semaphores),
        "cache": dict(lc._last_collect_cache),
        "tracker": {k: dict(v) for k, v in lc._host_failure_tracker.items()},
    }
    yield
    os.environ["PATH"] = saved["path"]
    lc.LINUX_SSH_TIMEOUT = saved["ssh_timeout"]
    lc.LINUX_HOSTS = saved["hosts"]
    lc._host_semaphores.clear()
    lc._host_semaphores.update(saved["semaphores"])
    lc._last_collect_cache.clear()
    lc._last_collect_cache.update(saved["cache"])
    lc._host_failure_tracker.clear()
    lc._host_failure_tracker.update(saved["tracker"])


def _run(coro):
    """Helper to run a single async coroutine without mocks."""
    return asyncio.run(coro)


def _start_hanging_listener(port: int):
    """Open a TCP socket, accept, and stay silent so ssh hangs waiting for a banner."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(1)

    def _loop():
        while True:
            try:
                conn, _ = sock.accept()
                # Send a fake server banner so the ssh client moves past connection timeout,
                # then stay silent long enough for the asyncio wait_for to fire.
                conn.sendall(b"SSH-2.0-Fake\r\n")
                time.sleep(30)
                conn.close()
            except OSError:
                break

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return sock


def test_module_default_config_excepts():
    """Cover the except branches for optional config imports."""
    attrs = ["LINUX_SSH_BATCH_SIZE", "LINUX_HOST_COOLDOWN_SEC", "LINUX_HOST_MAX_FAILURES"]
    saved = {a: getattr(_config_module, a, None) for a in attrs}
    try:
        for a in attrs:
            delattr(_config_module, a)
        importlib.reload(lc)
        assert lc._SSH_BATCH_SIZE == 20
        assert lc._HOST_COOLDOWN_SEC == 300
        assert lc._HOST_MAX_FAILURES == 3
    finally:
        for a, v in saved.items():
            if v is not None:
                setattr(_config_module, a, v)
        importlib.reload(lc)


def test_get_host_semaphore_fast_and_slow_paths():
    """Cover both the fast (cached) and slow (created) Semaphore paths."""
    lc._host_semaphores.clear()
    sem1 = lc._get_host_semaphore("h1")
    sem2 = lc._get_host_semaphore("h1")
    assert sem1 is sem2
    assert isinstance(sem1, asyncio.Semaphore)
    lc._host_semaphores.clear()


def test_get_last_snapshot():
    """Cover the shallow-copy snapshot helper with and without data."""
    lc._last_collect_cache.clear()
    assert lc.get_last_snapshot() == {}
    sample = {"h1": {"name": "h1", "status": "ok"}}
    lc._last_collect_cache.update(sample)
    snap = lc.get_last_snapshot()
    assert snap == sample
    assert snap is not sample
    lc._last_collect_cache.clear()


def test_cooldown_all_branches():
    """Exercise all branches in cooldown tracker and status helpers."""
    lc._host_failure_tracker.clear()
    host = "cooldown-host"
    max_fail = lc._HOST_MAX_FAILURES

    # No tracker yet
    assert lc._is_host_in_cooldown(host) is False

    # Count below threshold
    for _ in range(max_fail - 1):
        lc._record_host_failure(host)
    assert lc._is_host_in_cooldown(host) is False
    assert lc._host_failure_tracker[host]["count"] == max_fail - 1

    # Threshold reached -> cooldown
    lc._record_host_failure(host)
    assert lc._is_host_in_cooldown(host) is True
    status = lc.get_host_cooldown_status()
    assert status["total_tracked"] == 1
    assert any(item["host"] == host for item in status["stale_hosts"])

    # Negative elapsed / clock drift -> reset
    lc._host_failure_tracker[host]["last_fail"] = time.monotonic() + 100
    assert lc._is_host_in_cooldown(host) is False
    assert host not in lc._host_failure_tracker

    # Re-trigger and expire by backdating
    for _ in range(max_fail):
        lc._record_host_failure(host)
    lc._host_failure_tracker[host]["last_fail"] = time.monotonic() - lc._HOST_COOLDOWN_SEC - 1
    assert lc._is_host_in_cooldown(host) is False
    assert host not in lc._host_failure_tracker

    status = lc.get_host_cooldown_status()
    assert status["total_tracked"] == 0


def test_host_cooldown_failure_record():
    """Cover new-vs-existing tracker creation in _record_host_failure."""
    lc._host_failure_tracker.clear()
    lc._record_host_failure("new-host")
    assert lc._host_failure_tracker["new-host"]["count"] == 1
    lc._record_host_failure("new-host")
    assert lc._host_failure_tracker["new-host"]["count"] == 2
    lc._record_host_success("new-host")
    assert "new-host" not in lc._host_failure_tracker


def test_ssh_execute_input_defenses():
    """Cover the early validation branches of _ssh_execute."""

    async def _coro():
        # Invalid host_config type
        assert (await lc._ssh_execute("not-a-dict", "echo hi")) == "ERROR: invalid host_config"
        # Empty or non-string command
        assert (await lc._ssh_execute({"host": "h", "username": "u"}, None)) == ""
        assert (await lc._ssh_execute({"host": "h", "username": "u"}, "")) == ""
        # Missing/empty host
        assert (await lc._ssh_execute({"username": "u"}, "echo hi")).startswith("ERROR: host field")
        assert (await lc._ssh_execute({"username": "u", "host": "   "}, "echo hi")).startswith(
            "ERROR: host field"
        )
        # Missing username
        assert (await lc._ssh_execute({"host": "h"}, "echo hi")).startswith("ERROR: username field")

    _run(_coro())


def test_ssh_execute_batch_empty_and_invalid():
    """Cover _ssh_execute_batch empty commands and pre-SSH error handling."""

    async def _coro():
        # Empty commands returns empty dict
        assert (await lc._ssh_execute_batch({"host": "h", "username": "u"}, {})) == {}

        # Missing username causes _ssh_execute to return an ERROR string, propagated to all keys
        out = await lc._ssh_execute_batch({"host": "h"}, {"m1": "echo 1", "m2": "echo 2"})
        assert out == {"m1": "ERROR: username field missing", "m2": "ERROR: username field missing"}

    _run(_coro())


def test_ssh_execute_batch_sshpass_missing():
    """Password auth with no sshpass installed reaches the parser branch."""

    async def _coro():
        # No key, with password -> tries sshpass, which is not on Windows; returns SSHPASS_NOT_FOUND.
        # _ssh_execute_batch does not recognize it as a fatal error, so it attempts to parse
        # and falls back to empty values for each metric (no separator lines present).
        out = await lc._ssh_execute_batch(
            {"host": "h", "username": "u", "password": "p"},
            {"m1": "echo 1"},
        )
        assert out == {"m1": ""}

    _run(_coro())


def test_ssh_execute_ssh_not_found():
    """Clear PATH so ssh cannot be found and the FileNotFoundError branch is exercised."""

    async def _coro():
        return await lc._ssh_execute(
            {"host": "127.0.0.1", "username": "u", "key_file": "dummy"},
            "echo hi",
        )

    orig = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = ""
        assert _run(_coro()) == "SSH_NOT_FOUND"
    finally:
        os.environ["PATH"] = orig


def test_ssh_execute_timeout():
    """Real asyncio TimeoutError branch with a local hanging TCP listener."""
    listener = _start_hanging_listener(10022)
    try:
        original_timeout = lc.LINUX_SSH_TIMEOUT
        lc.LINUX_SSH_TIMEOUT = 1

        async def _coro():
            return await lc._ssh_execute(
                {"host": "127.0.0.1", "username": "u", "port": 10022, "key_file": "dummy"},
                "echo hi",
            )

        assert _run(_coro()) == "TIMEOUT"
        lc.LINUX_SSH_TIMEOUT = original_timeout
    finally:
        listener.close()


def test_parse_structured_metrics():
    """In-memory coverage of _parse_structured_metrics including invalid data."""
    result: dict[str, Any] = {
        "metrics": {
            "cpu_usage": {"value": "45.7\n"},
            "memory": {"value": "16000 8000 7500 50.0"},
            "load_avg": {"value": "0.1 0.5 1.2 2/100 5"},
            "swap": {"value": "2048 1024 50.0"},
            "hostname": {"value": "testhost"},
        }
    }
    lc._parse_structured_metrics(result)
    assert result["metrics"]["cpu_usage"]["parsed"]["usage_percent"] == 45.7
    assert result["metrics"]["memory"]["parsed"]["usage_percent"] == 50.0
    assert result["metrics"]["load_avg"]["parsed"]["load_5min"] == 0.5
    assert result["metrics"]["swap"]["parsed"]["usage_percent"] == 50.0

    # Missing/invalid data should be silently ignored and not add 'parsed' keys
    bad: dict[str, Any] = {
        "metrics": {
            "cpu_usage": {"value": ""},
            "memory": {"value": "not numbers"},
            "load_avg": {"value": "x"},
            "swap": {"value": "garbage"},
        }
    }
    lc._parse_structured_metrics(bad)
    assert "parsed" not in bad["metrics"]["cpu_usage"]
    assert "parsed" not in bad["metrics"]["memory"]
    assert "parsed" not in bad["metrics"]["load_avg"]
    assert "parsed" not in bad["metrics"]["swap"]

    # metrics field not a dict -> no error
    lc._parse_structured_metrics({"metrics": "bad"})

    # Non-dict individual metric values should not crash (covers isinstance branches)
    non_dict: dict[str, Any] = {
        "metrics": {
            "cpu_usage": "not-a-dict",
            "memory": 12345,
            "load_avg": None,
            "swap": [1, 2, 3],
        }
    }
    lc._parse_structured_metrics(non_dict)


def test_collect_linux_host_input_validation():
    """Cover collect_linux_host input validation, cooldown, and skipped states."""
    lc._host_failure_tracker.clear()
    lc._last_collect_cache.clear()

    # host_config not a dict
    out = _run(lc.collect_linux_host(None))
    assert out["status"] == "error"

    # missing host field
    out = _run(lc.collect_linux_host({"name": "n"}))
    assert out["status"] == "error"

    # skipped due to missing auth
    out = _run(lc.collect_linux_host({"name": "n", "host": "h"}))
    assert out["status"] == "skipped"

    # cooldown without cached data
    for _ in range(lc._HOST_MAX_FAILURES):
        lc._record_host_failure("cool")
    out = _run(lc.collect_linux_host({"name": "cool", "host": "h", "key_file": "k"}))
    assert out["status"] == "cooldown"

    # cooldown with cached data -> cached_stale
    lc._last_collect_cache["cool"] = {"name": "cool", "host": "h", "status": "ok", "metrics": {}}
    out = _run(lc.collect_linux_host({"name": "cool", "host": "h", "key_file": "k"}))
    assert out["status"] == "cached_stale"
    assert "stale_at" in out


def test_collect_linux_host_collection_statuses():
    """Real in-memory / environment-driven collection covering error, degraded, and ok."""
    lc._host_failure_tracker.clear()

    # error: all real metrics fail because ssh is not on PATH
    orig = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = ""
        out = _run(
            lc.collect_linux_host(
                {"name": "err", "host": "h", "key_file": "k"},
                metrics=["hostname"],
            )
        )
        assert out["status"] == "error"

        # degraded: 2 invalid + 3 valid, 3/5 errors
        out = _run(
            lc.collect_linux_host(
                {"name": "deg", "host": "h", "key_file": "k"},
                metrics=["bad1", "bad2", "hostname", "os_version", "uptime"],
            )
        )
        assert out["status"] == "degraded"
    finally:
        os.environ["PATH"] = orig

    # ok: sshpass not installed, so valid values become empty. Use many invalid metrics
    # so the single valid empty value is a small fraction of the requested metric count.
    out = _run(
        lc.collect_linux_host(
            {"name": "ok", "host": "h", "username": "u", "password": "p"},
            metrics=["bad1", "bad2", "bad3", "bad4", "bad5", "hostname"],
        )
    )
    assert out["status"] == "ok"


def test_collect_all_linux_and_get_hosts():
    """Cover collect_all_linux and get_configured_hosts with real in-memory host data."""
    saved = lc.LINUX_HOSTS
    try:
        lc.LINUX_HOSTS = {
            "enabled": True,
            "hosts": [
                {"name": "h1", "host": "1.2.3.4", "username": "u", "password": "p"},
                {
                    "name": "h2",
                    "host": "5.6.7.8",
                    "username": "u",
                    "key_file": "/tmp/dummy",
                    "role": "db",
                    "layer": 2,
                    "downstream": ["h1"],
                },
            ],
        }
        results = _run(lc.collect_all_linux(metrics=["hostname"]))
        assert len(results) == 2
        names = {r["name"] for r in results}
        assert names == {"h1", "h2"}

        # cache updated
        snap = lc.get_last_snapshot()
        assert "h1" in snap
        assert "h2" in snap

        hosts = lc.get_configured_hosts()
        assert len(hosts) == 2
        h2 = next(h for h in hosts if h["name"] == "h2")
        assert h2["role"] == "db"
        assert h2["layer"] == 2
        assert h2["downstream"] == ["h1"]
    finally:
        lc.LINUX_HOSTS = saved


def test_get_available_metrics():
    """Real public helper for metric listing."""
    metrics = lc.get_available_metrics()
    assert isinstance(metrics, list)
    assert all("key" in m and "desc" in m for m in metrics)
    assert any(m["key"] == "cpu_usage" for m in metrics)


def test_collect_linux_host_no_valid_metrics():
    """Cover the branch where none of the requested metrics are valid."""
    out = _run(
        lc.collect_linux_host(
            {"name": "nv", "host": "h", "username": "u", "password": "p"},
            metrics=["totally_invalid"],
        )
    )
    assert out["status"] == "error"
    assert out["error"] == "无有效的采集指标"


def test_collect_all_linux_empty_and_exception():
    """Cover empty host list and exception handling in collect_all_linux."""
    saved_hosts = lc.LINUX_HOSTS
    saved_cmds = dict(lc.COLLECT_COMMANDS)
    try:
        # Empty host list
        lc.LINUX_HOSTS = {"enabled": True, "hosts": []}
        assert _run(lc.collect_all_linux(metrics=["hostname"])) == []

        # Host task raises because a metric definition is missing the 'cmd' key
        lc.COLLECT_COMMANDS["boom"] = {"desc": "intentionally broken"}
        lc.LINUX_HOSTS = {"enabled": True, "hosts": [{"name": "x", "host": "h", "password": "p"}]}
        results = _run(lc.collect_all_linux(metrics=["boom"]))
        assert any(r["name"] == "x" and r["status"] == "error" for r in results)
    finally:
        lc.LINUX_HOSTS = saved_hosts
        lc.COLLECT_COMMANDS.clear()
        lc.COLLECT_COMMANDS.update(saved_cmds)
