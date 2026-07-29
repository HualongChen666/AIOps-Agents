# -*- coding: utf-8 -*-
"""Tests for verification wait/poll logic (Pod Ready / service startup)."""

import json
from unittest.mock import patch

import pytest

from core import verifier


@pytest.fixture(autouse=True)
def _short_wait_times(monkeypatch):
    """Use short wait windows so tests run quickly."""
    verifier.SNAPSHOT_CONFIG["verify_wait_timeout"] = 2.0
    verifier.SNAPSHOT_CONFIG["verify_poll_interval"] = 0.3
    verifier.VERIFY_CONFIG["timeout_sec"] = 5.0
    yield


@pytest.mark.asyncio
async def test_service_status_polls_until_active():
    """service_status waits through transient states until active/running."""
    outputs = iter(["activating\n", "active\n"])

    async def _fake_execute_linux(alert, cmd):
        return next(outputs)

    with patch.object(verifier, "_execute_linux_verify_command", _fake_execute_linux):
        result = await verifier._verify_service_status(
            alert={"host": "localhost"},
            params={"service_name": "nginx"},
            platform="linux",
        )

    assert result["verified"] is True
    assert result["evidence"]["actual"] == "active"
    assert result["evidence"]["waited_sec"] > 0


@pytest.mark.asyncio
async def test_service_status_fails_when_inactive():
    """service_status returns False immediately for a terminal inactive state."""

    async def _fake_execute_linux(alert, cmd):
        return "inactive\n"

    with patch.object(verifier, "_execute_linux_verify_command", _fake_execute_linux):
        result = await verifier._verify_service_status(
            alert={"host": "localhost"},
            params={"service_name": "nginx"},
            platform="linux",
        )

    assert result["verified"] is False
    assert result["evidence"]["actual"] == "inactive"


@pytest.mark.asyncio
async def test_k8s_status_polls_until_running_and_ready():
    """k8s_status waits from Pending to Running + Ready."""
    pending = {
        "status": {
            "phase": "Pending",
            "conditions": [{"type": "Ready", "status": "False"}],
        }
    }
    running_ready = {
        "status": {
            "phase": "Running",
            "conditions": [{"type": "Ready", "status": "True"}],
        }
    }
    outputs = iter([json.dumps(pending), json.dumps(running_ready)])

    async def _fake_execute_linux(alert, cmd):
        return next(outputs)

    with patch.object(verifier, "_execute_linux_verify_command", _fake_execute_linux):
        result = await verifier._verify_k8s_status(
            alert={"host": "localhost"},
            params={"resource": "pod", "name": "nginx-xxx", "namespace": "default"},
            platform="linux",
        )

    assert result["verified"] is True
    assert result["evidence"]["phase"] == "running"
    assert result["evidence"]["ready"] is True
    assert result["evidence"]["waited_sec"] > 0


@pytest.mark.asyncio
async def test_k8s_status_fails_terminal_phase():
    """k8s_status returns False for terminal phases like Failed."""
    failed = {
        "status": {
            "phase": "Failed",
            "conditions": [{"type": "Ready", "status": "False"}],
        }
    }

    async def _fake_execute_linux(alert, cmd):
        return json.dumps(failed)

    with patch.object(verifier, "_execute_linux_verify_command", _fake_execute_linux):
        result = await verifier._verify_k8s_status(
            alert={"host": "localhost"},
            params={"resource": "pod", "name": "nginx-xxx", "namespace": "default"},
            platform="linux",
        )

    assert result["verified"] is False
    assert result["evidence"]["phase"] == "failed"


@pytest.mark.asyncio
async def test_k8s_status_skipped_on_windows():
    """k8s_status is skipped when platform is windows."""
    result = await verifier._verify_k8s_status(
        alert={"host": "localhost"},
        params={"resource": "pod", "name": "nginx-xxx", "namespace": "default"},
        platform="windows",
    )
    assert result["verified"] is None
    assert result["strategy"] == "k8s_status"
