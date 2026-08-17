# -*- coding: utf-8 -*-
"""Low-coverage tests for extensions/hardware_remediation modules."""

import importlib.util
import os  # noqa: F401  # Imported for test setup
import subprocess
import sys  # noqa: F401  # Imported for test setup
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARDWARE_DIR = os.path.join(PROJECT_ROOT, "extensions", "hardware_remediation")

import extensions.hardware_remediation as _hw_pkg


def _load_module(filename, unique_name):
    path = os.path.join(HARDWARE_DIR, filename)
    spec = importlib.util.spec_from_file_location(unique_name, path)
    module = importlib.util.module_from_spec(spec)
    # Keep the real package namespace so relative imports resolve.
    module.__package__ = "extensions.hardware_remediation"
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _patch_hw_external_calls(monkeypatch):
    """Enable hardware execution paths and stub all subprocess/network calls."""
    _hw_pkg.HARDWARE_EXECUTE_ENABLED = True
    monkeypatch.setenv("HARDWARE_EXECUTE_ENABLED", "true")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )
    try:
        import requests

        monkeypatch.setattr(requests, "request", lambda *args, **kwargs: MagicMock())
    except Exception:
        pass
    try:
        import httpx

        monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: MagicMock())
        monkeypatch.setattr(httpx.Client, "send", lambda *args, **kwargs: MagicMock())
    except Exception:
        pass


def test_ipmi_actions():
    ipmi = _load_module("ipmi_actions.py", "_test_low_ipmi_actions")
    assert ipmi.power_cycle("bmc1")["success"] is True
    assert ipmi.power_reset("bmc1")["success"] is True
    assert ipmi.get_sensor_data("bmc1")["success"] is True
    ipmi.register_ipmi_scripts()


def test_node_lifecycle():
    node = _load_module("node_lifecycle.py", "_test_low_node_lifecycle")
    assert node.cordon("node-1")["success"] is True
    assert node.drain("node-1")["success"] is True
    assert node.uncordon("node-1")["success"] is True
    node.register_node_scripts()


def test_raid_storcli():
    raid = _load_module("raid_storcli.py", "_test_low_raid_storcli")
    assert raid.show_all()["success"] is True
    assert raid.show_rebuild()["success"] is True
    assert raid.start_rebuild()["success"] is True
    raid.register_raid_scripts()


def test_redfish_actions():
    redfish = _load_module("redfish_actions.py", "_test_low_redfish_actions")
    assert redfish.reboot("idrac-1")["success"] is True
    assert redfish.health("idrac-1")["success"] is True
    redfish.register_redfish_scripts()


def test_smartctl():
    smart = _load_module("smartctl.py", "_test_low_smartctl")
    assert smart.short_test("/dev/sda")["success"] is True
    assert smart.full_info("/dev/sda")["success"] is True
    smart.register_smart_scripts()


def test_ticket_integration():
    ticket = _load_module("ticket_integration.py", "_test_low_ticket_integration")
    assert ticket.create_ticket("jira", "summary", "description")["success"] is True
    ticket.register_ticket_scripts()
