# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

from core.docker_repair import (
    execute_repair_sync,
    get_docker_repair_history,
    get_docker_repair_scripts,
)


@pytest.fixture(autouse=True)
def _isolate_docker_history(tmp_path, monkeypatch):
    """Keep docker repair history out of the version-controlled data/ directory."""
    monkeypatch.setattr(
        "core.docker_repair._HISTORY_FILE", tmp_path / "docker_repair_history.json"
    )


def test_get_repair_scripts():
    scripts = get_docker_repair_scripts()
    assert "restart_container" in scripts
    assert "ps" in scripts
    assert scripts["ps"]["read_only"] is True


@pytest.mark.asyncio
async def test_execute_repair_read_only_runs(monkeypatch):
    """Read-only scripts execute for real (no dry-run simulation)."""
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: "/bin/docker")
    fake_proc = MagicMock(returncode=0, stdout="containers", stderr="")
    monkeypatch.setattr("core.docker_repair.subprocess.run", lambda *a, **k: fake_proc)
    result = await execute_repair_sync(
        "localhost", "ps", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["read_only"] is True
    assert result["executed"] is True
    assert "docker_available" in result


@pytest.mark.asyncio
async def test_execute_repair_destructive_requires_confirmation(monkeypatch):
    """A destructive command without confirmation is not executed nor "success"."""
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: "/bin/docker")
    result = await execute_repair_sync(
        "localhost", "prune_images", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["requires_confirmation"] is True
    assert result["executed"] is False


@pytest.mark.asyncio
async def test_execute_repair_missing_param():
    result = await execute_repair_sync(
        "localhost", "restart_container", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False


@pytest.mark.asyncio
async def test_history_is_recorded(monkeypatch, tmp_path):
    hist_file = tmp_path / "docker_repair_history.json"
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", hist_file)
    await execute_repair_sync("localhost", "ps", {})
    history = get_docker_repair_history(limit=10)
    assert len(history) >= 1
    assert history[-1]["script"] == "ps"
