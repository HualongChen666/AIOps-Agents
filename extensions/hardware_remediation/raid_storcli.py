# -*- coding: utf-8 -*-
"""RAID / StorCLI actions (dry-run by default)."""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

from . import HARDWARE_EXECUTE_ENABLED

logger = logging.getLogger(__name__)


def _run_storcli(args: list[str]) -> Dict[str, Any]:
    """Execute or simulate a StorCLI command."""
    if not HARDWARE_EXECUTE_ENABLED:
        return {
            "success": True,
            "simulated": True,
            "command": f"storcli {' '.join(args)}",
        }
    try:
        result = subprocess.run(
            ["storcli", *args],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:1000],
        }
    except Exception as exc:
        logger.exception("StorCLI command failed: %s", args)
        return {"success": False, "error": str(exc)}


def show_all() -> Dict[str, Any]:
    return _run_storcli(["/c0", "/vall", "show"])


def show_rebuild() -> Dict[str, Any]:
    return _run_storcli(["/c0", "/eall", "/sall", "show", "rebuild"])


def start_rebuild(controller: str = "c0", enclosure: str = "e252", slot: str = "s0") -> Dict[str, Any]:
    return _run_storcli([f"/{controller}", f"/{enclosure}", f"/{slot}", "start", "rebuild"])


def register_raid_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="raid_rebuild",
            name="RAID Rebuild (StorCLI)",
            description="Inspect and start RAID rebuild via StorCLI.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            script_content="storcli /c0 /vall show\nstorcli /c0 /eall /sall show rebuild\nstorcli /c0 /e252 /s0 start rebuild",
            rollback_script="storcli /c0 /e252 /s0 stop rebuild",
            metadata={"category": "hardware", "interface": "storcli"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="raid_status",
            name="RAID Status",
            description="Display RAID controller and virtual drive status.",
            platforms=[PlatformType.LINUX],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content="storcli /c0 /vall show",
            metadata={"category": "hardware", "interface": "storcli"},
        )
    )
