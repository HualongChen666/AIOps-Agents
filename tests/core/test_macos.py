# -*- coding: utf-8 -*-
"""Tests for core/macos_collector.py and core/macos_repair.py."""

import asyncio  # noqa: F401  # Imported for test setup
from unittest.mock import MagicMock

import config
import core.macos_collector
import core.macos_repair


class FakeProc:
    def __init__(self, returncode=0, stdout=b"ok", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


async def fake_subprocess(cmd, **kwargs):
    return FakeProc()


async def test_run_command_local(monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_subprocess)
    result = await core.macos_collector._run_command(
        "localhost", "whoami"
    )  # noqa: F841  # Variable for test verification
    assert result["stdout"] == "ok"


async def test_run_command_remote_not_supported():
    result = await core.macos_collector._run_command(
        "remote", "whoami"
    )  # noqa: F841  # Variable for test verification
    assert "not supported" in result["stderr"]


async def test_collect_macos_metrics(monkeypatch):
    monkeypatch.setattr(config, "MAC_HOSTS", [], raising=False)
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent.return_value = 10.0
    mem = MagicMock()
    mem.percent = 50.0
    fake_psutil.virtual_memory.return_value = mem
    disk = MagicMock()
    disk.percent = 20.0
    fake_psutil.disk_usage.return_value = disk
    monkeypatch.setattr(core.macos_collector, "psutil", fake_psutil)
    monkeypatch.setattr(core.macos_collector.platform, "system", lambda: "Darwin")
    results = await core.macos_collector.collect_macos_metrics(hosts=["localhost"])
    assert results["localhost"]["cpu"] == 10.0


async def test_execute_macos_repair(monkeypatch):
    monkeypatch.setattr(asyncio, "create_subprocess_shell", fake_subprocess)
    result = await core.macos_repair.execute_macos_repair(
        "localhost", "cleanup"
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "output" in result


def test_get_available_macos_scripts():
    scripts = core.macos_repair.get_available_macos_scripts()
    assert isinstance(scripts, list)
