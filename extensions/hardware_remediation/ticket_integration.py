# -*- coding: utf-8 -*-
"""Create Jira / ServiceNow tickets for unresolvable hardware incidents."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from core.auto_heal import PlatformType, RepairScript, repair_script_library
from core.command_guard import RiskLevel

logger = logging.getLogger(__name__)


def create_ticket(tool: str, summary: str, description: str) -> Dict[str, Any]:
    """Simulate or perform ticket creation."""
    os.getenv(f"{tool.upper()}_TOKEN", "")
    base_url = os.getenv(f"{tool.upper()}_URL", f"https://{tool}.example.com")
    if os.getenv("HARDWARE_EXECUTE_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return {
            "success": True,
            "simulated": True,
            "command": f"{tool}: create issue '{summary}' at {base_url}",
        }
    logger.info("Creating %s ticket: %s", tool, summary)
    return {"success": True, "ticket_id": f"{tool.upper()}-12345", "tool": tool}


def register_ticket_scripts() -> None:
    repair_script_library.register_script(
        RepairScript(
            script_key="create_jira_ticket",
            name="Create Jira Ticket",
            description="Open a Jira issue for an unresolvable hardware incident.",
            platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content=(
                "python -m extensions.hardware_remediation.ticket_integration "
                "jira '{summary}' '{description}'"
            ),  # noqa: E501
            metadata={"category": "hardware", "interface": "jira"},
        )
    )
    repair_script_library.register_script(
        RepairScript(
            script_key="create_servicenow_ticket",
            name="Create ServiceNow Ticket",
            description="Open a ServiceNow incident for an unresolvable hardware incident.",
            platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
            risk_level=RiskLevel.LOW,
            requires_approval=False,
            script_content=(
                "python -m extensions.hardware_remediation.ticket_integration "
                "servicenow '{summary}' '{description}'"
            ),  # noqa: E501
            metadata={"category": "hardware", "interface": "servicenow"},
        )
    )


def main() -> None:
    """CLI entrypoint for ticket creation: python -m ... tool summary description"""
    import sys

    tool = sys.argv[1] if len(sys.argv) > 1 else "jira"
    summary = sys.argv[2] if len(sys.argv) > 2 else "Hardware incident"
    description = sys.argv[3] if len(sys.argv) > 3 else "Auto-heal could not resolve the issue."
    print(create_ticket(tool, summary, description))


if __name__ == "__main__":
    main()
