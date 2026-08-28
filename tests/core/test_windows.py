# -*- coding: utf-8 -*-
"""Tests for core/windows_collector.py and core/windows_repair.py."""

import pytest
import core.windows_collector
import core.windows_repair


@pytest.mark.asyncio
async def test_collect_windows_host_without_winrm():
    result = await core.windows_collector.collect_windows_host(  # noqa: F841  # Variable for test verification
        {"ip": "192.168.1.1", "name": "win1"}
    )
    assert "host" in result
    assert "error" in result or "cpu_percent" in result


@pytest.mark.asyncio
async def test_collect_all_windows(monkeypatch):
    monkeypatch.setattr(core.windows_collector, "WIN_HOSTS", [])
    result = (
        await core.windows_collector.collect_all_windows()
    )  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_execute_windows_repair():
    result = await core.windows_repair.execute_windows_repair(  # noqa: F841  # Variable for test verification
        "restart_service", {"service_name": "foo"}
    )
    assert isinstance(result, dict)


def test_get_windows_repair_history():
    history = core.windows_repair.get_windows_repair_history(limit=5)
    assert history == []
