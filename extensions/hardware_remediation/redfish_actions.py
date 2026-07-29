# -*- coding: utf-8 -*-
"""iDRAC / iLO / Redfish power and health actions (dry-run by default)."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

from . import HARDWARE_EXECUTE_ENABLED

logger = logging.getLogger(__name__)


def _run_redfish(
    host: str, username: str, password: str, action: str
) -> Dict[str, Any]:
    """Execute or simulate a Redfish action."""
    if not HARDWARE_EXECUTE_ENABLED:
        return {
            "success": True,
            "simulated": True,
            "command": (
                f"curl -k -u {username}:*** "
                f"-X POST https://{host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset "
                f"-d '{{\"ResetType\":\"{action}\"}}' -H 'Content-Type: application/json'"
            ),
        }
    try:
        body = json.dumps({"ResetType": action})
        result = subprocess.run(
            [
                "curl",
                "-k",
                "-u",
                f"{username}:{password}",
                "-X",
                "POST",
                f"https://{host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset",
                "-d",
                body,
                "-H",
                "Content-Type: application/json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:1000],
            "stderr": result.stderr[:1000],
        }
    except Exception as exc:
        logger.exception("Redfish action failed: %s on %s", action, host)
        return {"success": False, "error": str(exc)}


def reboot(host: str, username: str = "root", password: str = "") -> Dict[str, Any]:
    return _run_redfish(host, username, password, "ForceRestart")


def health(host: str, username: str = "root", password: str = "") -> Dict[str, Any]:
    if not HARDWARE_EXECUTE_ENABLED:
        return {
            "success": True,
            "simulated": True,
            "command": f"curl -k -u root:*** https://{host}/redfish/v1/Systems/1",
        }
    try:
        result = subprocess.run(
            ["curl", "-k", "-u", f"{username}:{password}", f"https://{host}/redfish/v1/Systems/1"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def register_redfish_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="redfish_reboot",
            name="Redfish / iDRAC / iLO Reboot",
            description="Reboot a server using Redfish BMC API.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            script_content=(
                "curl -k -u {username}:*** -X POST "
                "https://{host}/redfish/v1/Systems/1/Actions/ComputerSystem.Reset "
                '-d \'{"ResetType":"ForceRestart"}\' -H \'Content-Type: application/json\''
            ),
            rollback_script="echo 'Reboot rollback: ensure service is restored via health check'",
            metadata={"category": "hardware", "interface": "redfish"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="redfish_health",
            name="Redfish / iDRAC Health",
            description="Collect Redfish system health data.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content="curl -k -u {username}:*** https://{host}/redfish/v1/Systems/1",
            metadata={"category": "hardware", "interface": "redfish"},
        )
    )
