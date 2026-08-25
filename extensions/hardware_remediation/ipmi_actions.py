# -*- coding: utf-8 -*-
"""IPMI power actions (dry-run by default)."""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

from . import HARDWARE_EXECUTE_ENABLED

logger = logging.getLogger(__name__)


def _run_ipmi(host: str, username: str, password: str, action: str) -> Dict[str, Any]:
    """Execute or simulate an IPMI action."""
    if not HARDWARE_EXECUTE_ENABLED:
        return {
            "success": True,
            "simulated": True,
            "command": f"ipmitool -I lanplus -H {host} -U {username} -P *** {action}",
        }
    try:
        result = subprocess.run(
            ["ipmitool", "-I", "lanplus", "-H", host, "-U", username, "-P", password, action],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=False,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:1000],
            "stderr": result.stderr[:1000],
        }
    except Exception as exc:
        logger.error("IPMI action failed: %s on %s", action, host)
        return {"success": False, "error": str(exc)}


def power_cycle(host: str, username: str = "root", password: str = "") -> Dict[str, Any]:
    return _run_ipmi(host, username, password, "power cycle")


def power_reset(host: str, username: str = "root", password: str = "") -> Dict[str, Any]:
    return _run_ipmi(host, username, password, "power reset")


def get_sensor_data(host: str, username: str = "root", password: str = "") -> Dict[str, Any]:
    return _run_ipmi(host, username, password, "sensor list")


def register_ipmi_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="ipmi_power_cycle",
            name="IPMI Power Cycle",
            description="Power cycle a server via IPMI (BMC).",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            script_content=(
                "ipmitool -I lanplus -H {host} -U {username} -P {password} power cycle\n"
                "ipmitool -I lanplus -H {host} -U {username} -P {password} power on"
            ),
            rollback_script="ipmitool -I lanplus -H {host} -U {username} -P {password} power on",
            metadata={"category": "hardware", "interface": "ipmi"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="ipmi_get_sensor",
            name="IPMI Sensor Data",
            description="Collect IPMI sensor data for diagnostics.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content="ipmitool -I lanplus -H {host} -U {username} -P {password} sensor list",
            metadata={"category": "hardware", "interface": "ipmi"},
        )
    )
