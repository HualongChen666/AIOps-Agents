# -*- coding: utf-8 -*-
"""Hardware remediation dry-run extensions (IPMI/iDRAC/RAID/SMART/K8s drain/ticket)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

HARDWARE_EXECUTE_ENABLED = os.getenv("HARDWARE_EXECUTE_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)

from .ipmi_actions import register_ipmi_scripts
from .node_lifecycle import register_node_scripts
from .raid_storcli import register_raid_scripts
from .redfish_actions import register_redfish_scripts
from .smartctl import register_smart_scripts
from .ticket_integration import register_ticket_scripts


def register_all_hardware_scripts() -> None:
    """Register all hardware remediation scripts in the global RepairScriptLibrary."""
    register_ipmi_scripts()
    register_redfish_scripts()
    register_raid_scripts()
    register_smart_scripts()
    register_node_scripts()
    register_ticket_scripts()
    logger.info(
        "Hardware remediation scripts registered. HARDWARE_EXECUTE_ENABLED=%s",
        HARDWARE_EXECUTE_ENABLED,
    )


register_all_hardware_scripts()
