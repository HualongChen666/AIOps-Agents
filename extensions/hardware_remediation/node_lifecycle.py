# -*- coding: utf-8 -*-
"""Kubernetes node lifecycle actions (cordon / drain / uncordon)."""

from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

from . import HARDWARE_EXECUTE_ENABLED

logger = logging.getLogger(__name__)


def _run_kubectl(args: list[str]) -> Dict[str, Any]:
    """Execute or simulate a kubectl command."""
    if not HARDWARE_EXECUTE_ENABLED:
        return {"success": True, "simulated": True, "command": f"kubectl {' '.join(args)}"}
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            timeout=180,
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
        logger.error("kubectl command failed")
        return {"success": False, "error": str(exc)}


def cordon(node: str) -> Dict[str, Any]:
    return _run_kubectl(["cordon", node])


def drain(node: str) -> Dict[str, Any]:
    return _run_kubectl(
        [
            "drain",
            node,
            "--ignore-daemonsets",
            "--delete-emptydir-data",
            "--force",
            "--timeout=120s",
        ]
    )


def uncordon(node: str) -> Dict[str, Any]:
    return _run_kubectl(["uncordon", node])


def register_node_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="k8s_cordon",
            name="K8s Cordon Node",
            description="Mark a Kubernetes node as unschedulable.",
            platforms=[PlatformType.LINUX, PlatformType.KUBERNETES],
            risk_level=RiskLevel.MEDIUM,
            requires_approval=True,
            script_content="kubectl cordon {node}",
            rollback_script="kubectl uncordon {node}",
            metadata={"category": "hardware", "interface": "kubectl"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="k8s_drain",
            name="K8s Drain Node",
            description="Evacuate pods from a Kubernetes node.",
            platforms=[PlatformType.LINUX, PlatformType.KUBERNETES],
            risk_level=RiskLevel.HIGH,
            requires_approval=True,
            script_content=(
                "kubectl cordon {node}\n"
                "kubectl drain {node} "
                "--ignore-daemonsets --delete-emptydir-data --force --timeout=120s"
            ),
            rollback_script="kubectl uncordon {node}",
            metadata={"category": "hardware", "interface": "kubectl"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="k8s_uncordon",
            name="K8s Uncordon Node",
            description="Restore a Kubernetes node to schedulable.",
            platforms=[PlatformType.LINUX, PlatformType.KUBERNETES],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content="kubectl uncordon {node}",
            metadata={"category": "hardware", "interface": "kubectl"},
        )
    )
