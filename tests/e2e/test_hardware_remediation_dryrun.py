# -*- coding: utf-8 -*-
"""E2E tests for hardware remediation dry-run mode.

These tests confirm that hardware alerts generate the correct BMC / RAID /
SMART / K8s remediation runbooks, are classified as high-risk and remain in
dry-run unless ``HARDWARE_EXECUTE_ENABLED=true``.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("HEAL_EXECUTE_ENABLED", "false")
os.environ.setdefault("HARDWARE_EXECUTE_ENABLED", "false")

import extensions.hardware_remediation  # noqa: F401  registers scripts
from core.heal_graph import HealState, run_heal


def _commands(final) -> list[str]:
    runbook = final.runbook or {}
    inner = runbook.get("runbook") or runbook
    if isinstance(inner, dict):
        return [str(c) for c in inner.get("commands", []) if c]
    return []


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ipmi_alert_generates_power_cycle_dryrun():
    alert = {
        "id": "PROM-IPMI-01",
        "title": "IPMI critical host unreachable",
        "metric": "ipmi_power_status",
        "category": "hardware",
        "platform": "linux",
    }
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final.runbook is not None
    cmds = _commands(final)
    assert any("ipmitool" in cmd for cmd in cmds)
    # HIGH risk hardware action must await explicit approval by default
    assert not final.fix_applied
    assert final.error and "not approved" in final.error.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_raid_degraded_alert_generates_rebuild_dryrun():
    alert = {
        "id": "PROM-RAID-01",
        "title": "RAID volume degraded",
        "metric": "raid_degraded",
        "category": "hardware",
        "platform": "linux",
    }
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final.runbook is not None
    cmds = _commands(final)
    assert any("storcli" in cmd for cmd in cmds)
    assert not final.fix_applied
    assert final.error and "not approved" in final.error.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_smart_disk_alert_generates_test_dryrun():
    alert = {
        "id": "PROM-SMART-01",
        "title": "SMART failure predicted",
        "metric": "smart_reallocated_sectors",
        "category": "hardware",
        "platform": "linux",
    }
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final.runbook is not None
    cmds = _commands(final)
    assert any("smartctl" in cmd for cmd in cmds)
    assert not final.fix_applied
    assert final.error and "not approved" in final.error.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_k8s_node_alert_generates_drain_dryrun():
    alert = {
        "id": "PROM-K8S-01",
        "title": "K8s node needs drain",
        "metric": "k8s_drain_node",
        "category": "hardware",
        "platform": "linux",
        "node": "worker-03",
    }
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final.runbook is not None
    cmds = _commands(final)
    assert any("kubectl" in cmd for cmd in cmds)
    assert not final.fix_applied
    assert final.error and "not approved" in final.error.lower()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_redfish_alert_generates_reboot_dryrun():
    alert = {
        "id": "PROM-REDFISH-01",
        "title": "iDRAC host power failure",
        "metric": "redfish_power_state",
        "category": "hardware",
        "platform": "linux",
    }
    state = HealState(alert=alert)
    final = await run_heal(state)
    assert final.runbook is not None
    cmds = _commands(final)
    assert any("curl" in cmd for cmd in cmds)
    assert not final.fix_applied
    assert final.error and "not approved" in final.error.lower()
