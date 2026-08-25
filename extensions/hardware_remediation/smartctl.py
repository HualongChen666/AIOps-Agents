# -*- coding: utf-8 -*-
"""SMART disk health actions (dry-run by default)."""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

from . import HARDWARE_EXECUTE_ENABLED

logger = logging.getLogger(__name__)


def _run_smartctl(device: str, *args: str) -> Dict[str, Any]:
    """Execute or simulate a smartctl command."""
    if not HARDWARE_EXECUTE_ENABLED:
        return {
            "success": True,
            "simulated": True,
            "command": f"smartctl {' '.join(args)} {device}",
        }
    try:
        result = subprocess.run(
            ["smartctl", *args, device],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            shell=False,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
        }
    except Exception as exc:
        logger.error("smartctl command failed")
        return {"success": False, "error": str(exc)}


def short_test(device: str = "/dev/sda") -> Dict[str, Any]:
    return _run_smartctl(device, "-t", "short")


def full_info(device: str = "/dev/sda") -> Dict[str, Any]:
    return _run_smartctl(device, "-a")


def register_smart_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="smart_test",
            name="SMART Short Test",
            description="Run a SMART short self-test on a failing disk.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            script_content="smartctl -t short {device}\nsmartctl -a {device}",
            rollback_script="echo 'SMART test rollback: no destructive operation performed'",
            metadata={"category": "hardware", "interface": "smartctl"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="smart_info",
            name="SMART Info",
            description="Read SMART attributes for a disk.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content="smartctl -a {device}",
            metadata={"category": "hardware", "interface": "smartctl"},
        )
    )
