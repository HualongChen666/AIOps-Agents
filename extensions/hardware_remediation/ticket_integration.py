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
    """
    Create a Jira / ServiceNow ticket.

    When ``HARDWARE_EXECUTE_ENABLED`` is not set the function returns a *dry-run
    preview* (``simulated: True``) without contacting any external system.  When
    execution is enabled it performs a **real** REST call and only reports
    ``success`` when the remote system actually created the ticket.
    """
    tool = (tool or "").lower()
    if tool not in ("jira", "servicenow"):
        return {"success": False, "error": f"unsupported ticket tool: {tool}"}

    token = os.getenv(f"{tool.upper()}_TOKEN", "")
    base_url = os.getenv(f"{tool.upper()}_URL", "")
    username = os.getenv(f"{tool.upper()}_USER", "")

    if os.getenv("HARDWARE_EXECUTE_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return {
            "success": True,
            "simulated": True,
            "command": (
                f"{tool}: create issue '{summary}' at {base_url or f'https://{tool}.example.com'}"
            ),
        }

    if not base_url:
        return {"success": False, "error": f"{tool.upper()}_URL is not configured"}
    if not token:
        return {"success": False, "error": f"{tool.upper()}_TOKEN is not configured"}

    import httpx

    try:
        if tool == "jira":
            project_key = os.getenv("JIRA_PROJECT", "")
            if not project_key:
                return {"success": False, "error": "JIRA_PROJECT is not configured"}
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": os.getenv("JIRA_ISSUE_TYPE", "Bug")},
                }
            }
            auth = (username, token) if username else None
            response = httpx.post(
                f"{base_url.rstrip('/')}/rest/api/2/issue",
                json=payload,
                headers={"Content-Type": "application/json"},
                auth=auth,
                timeout=30.0,
            )
            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "success": True,
                    "ticket_id": data.get("key"),
                    "tool": tool,
                    "url": f"{base_url.rstrip('/')}/browse/{data.get('key')}",
                }
            return {
                "success": False,
                "tool": tool,
                "error": f"Jira returned status {response.status_code}",
                "body": response.text[:500],
            }

        # ServiceNow
        payload = {"short_description": summary, "description": description}
        response = httpx.post(
            f"{base_url.rstrip('/')}/api/now/table/incident",
            json=payload,
            auth=(username, token) if username else None,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=30.0,
        )
        if response.status_code in (200, 201):
            data = response.json().get("result", {})
            return {
                "success": True,
                "ticket_id": data.get("number") or data.get("sys_id"),
                "tool": tool,
            }
        return {
            "success": False,
            "tool": tool,
            "error": f"ServiceNow returned status {response.status_code}",
            "body": response.text[:500],
        }
    except Exception as exc:  # noqa: BLE001 - surface the real transport error
        return {"success": False, "tool": tool, "error": str(exc)}


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
