# -*- coding: utf-8 -*-
# isort: skip_file
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

from .ticket_integration import register_ticket_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .smartctl import register_smart_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .redfish_actions import register_redfish_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .raid_storcli import register_raid_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .node_lifecycle import register_node_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .ipmi_actions import register_ipmi_scripts  # noqa: E402  # Module level import not at top (intentional for env var setup)
from .hardware_log_analyzer import (  # noqa: E402  # Module level import not at top (intentional for env var setup)
    register_hardware_log_scripts,
)


def register_all_hardware_scripts() -> None:
    """Register all hardware remediation scripts in the global RepairScriptLibrary."""
    register_ipmi_scripts()
    register_redfish_scripts()
    register_raid_scripts()
    register_smart_scripts()
    register_node_scripts()
    register_ticket_scripts()
    register_hardware_log_scripts()
    logger.info(
        "Hardware remediation scripts registered. HARDWARE_EXECUTE_ENABLED=%s",
        HARDWARE_EXECUTE_ENABLED,
    )


register_all_hardware_scripts()
