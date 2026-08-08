# -*- coding: utf-8 -*-
import pytest

from core.docker_repair import (
    execute_repair_sync,
    get_docker_repair_history,
    get_docker_repair_scripts,
)


def test_get_repair_scripts():
    scripts = get_docker_repair_scripts()
    assert "restart_container" in scripts
    assert "ps" in scripts
    assert scripts["ps"]["read_only"] is True


async def test_execute_repair_dry_run():
    result = await execute_repair_sync("localhost", "ps", {})
    assert result["success"] is True
    assert result["dry_run"] is True
    assert "docker_available" in result


async def test_execute_repair_missing_param():
    result = await execute_repair_sync("localhost", "restart_container", {})
    assert result["success"] is False


async def test_history_is_recorded(monkeypatch, tmp_path):
    hist_file = tmp_path / "docker_repair_history.json"
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", hist_file)
    await execute_repair_sync("localhost", "ps", {})
    history = get_docker_repair_history(limit=10)
    assert len(history) >= 1
    assert history[-1]["script"] == "ps"
