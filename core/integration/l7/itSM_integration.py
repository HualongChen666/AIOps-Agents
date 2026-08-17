# -*- coding: utf-8 -*-
"""
L7 Integration Layer - ITSM Integration (ServiceNow, Jira)
Provides integration with ITSM systems for incident management and workflow automation
"""

from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from loguru import logger


class ITSMIntegration:
    """
    ITSM Integration for L7 Layer

    This integration provides:
    - ServiceNow incident management
    - Jira issue tracking
    - Bi-directional synchronization
    - Workflow automation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        # ServiceNow configuration
        self.servicenow_enabled = config.get("servicenow", {}).get("enabled", False)
        self.servicenow_instance = config.get("servicenow", {}).get("instance", "")
        self.servicenow_base_url = config.get("servicenow", {}).get("base_url", "")
        self.servicenow_username = config.get("servicenow", {}).get("username", "")
        self.servicenow_password = config.get("servicenow", {}).get("password", "")

        # Jira configuration
        self.jira_enabled = config.get("jira", {}).get("enabled", False)
        self.jira_url = config.get("jira", {}).get("url", "")
        self.jira_username = config.get("jira", {}).get("username", "")
        self.jira_api_token = config.get("jira", {}).get("api_token", "")

        self._is_initialized = False

        if self.servicenow_enabled or self.jira_enabled:
            self._is_initialized = True
            logger.info("ITSM Integration initialized")

    async def create_servicenow_incident(
        self,
        title: str,
        description: str,
        severity: str = "medium",
        priority: int = 3,
        assignment_group: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an incident in ServiceNow

        Args:
            title: Incident title
            description: Incident description
            severity: Incident severity
            priority: Incident priority
            assignment_group: Assignment group

        Returns:
            Created incident details
        """
        if not self.servicenow_enabled:
            logger.warning("ServiceNow integration not enabled")
            return {"error": "ServiceNow not enabled"}

        try:
            base_url = (
                self.servicenow_base_url
                or f"https://{self.servicenow_instance}.service-now.com/api/now/table"
            )
            severity_map = {"low": "3", "medium": "2", "high": "1"}
            payload = {
                "short_description": title,
                "description": description,
                "urgency": severity_map.get(severity, "2"),
                "priority": str(priority),
            }
            if assignment_group:
                payload["assignment_group"] = assignment_group

            async with httpx.AsyncClient(
                auth=(self.servicenow_username, self.servicenow_password),
                timeout=30.0,
            ) as client:
                response = await client.post(f"{base_url}/incident", json=payload)
                response.raise_for_status()
                result = response.json().get("result", {})

            logger.info(f"Created ServiceNow incident: {result.get('number')}")
            return {
                "number": result.get("number", ""),
                "title": title,
                "description": description,
                "severity": severity,
                "priority": priority,
                "assignment_group": assignment_group,
                "status": result.get("state", "New"),
                "created_at": result.get("sys_created_on", datetime.now().isoformat()),
            }

        except Exception as e:
            logger.error(f"Failed to create ServiceNow incident: {e}")
            return {"error": str(e)}

    async def update_servicenow_incident(
        self, incident_number: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing ServiceNow incident

        Args:
            incident_number: Incident number
            updates: Fields to update

        Returns:
            Updated incident details
        """
        if not self.servicenow_enabled:
            return {"error": "ServiceNow not enabled"}

        try:
            base_url = (
                self.servicenow_base_url
                or f"https://{self.servicenow_instance}.service-now.com/api/now/table"
            )
            async with httpx.AsyncClient(
                auth=(self.servicenow_username, self.servicenow_password),
                timeout=30.0,
            ) as client:
                lookup = await client.get(
                    f"{base_url}/incident",
                    params={
                        "sysparm_query": f"number={incident_number}",
                        "sysparm_limit": "1",
                    },
                )
                lookup.raise_for_status()
                results = lookup.json().get("result", [])
                if not results:
                    return {"error": "Incident not found"}
                sys_id = results[0].get("sys_id")
                response = await client.patch(f"{base_url}/incident/{sys_id}", json=updates)
                response.raise_for_status()
                result = response.json().get("result", {})

            logger.info(f"Updated ServiceNow incident: {incident_number}")
            return {
                "number": incident_number,
                "updated": True,
                "updates": updates,
                "updated_at": result.get("sys_updated_on", datetime.now().isoformat()),
            }

        except Exception as e:
            logger.error(f"Failed to update ServiceNow incident: {e}")
            return {"error": str(e)}

    async def create_jira_issue(
        self,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: str = "Medium",
        project_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an issue in Jira

        Args:
            summary: Issue summary
            description: Issue description
            issue_type: Type of issue
            priority: Issue priority
            project_key: Project key

        Returns:
            Created issue details
        """
        if not self.jira_enabled:
            logger.warning("Jira integration not enabled")
            return {"error": "Jira not enabled"}

        try:
            if not project_key:
                project_key = self.config.get("jira", {}).get("default_project")
            if not project_key:
                return {"error": "Project key is required"}

            base_url = f"{self.jira_url.rstrip('/')}/rest/api/2/issue"
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type},
                    "priority": {"name": priority},
                }
            }

            async with httpx.AsyncClient(
                auth=(self.jira_username, self.jira_api_token),
                timeout=30.0,
            ) as client:
                response = await client.post(base_url, json=payload)
                response.raise_for_status()
                result = response.json()

            logger.info(f"Created Jira issue: {result.get('key')}")
            return {
                "key": result.get("key", ""),
                "summary": summary,
                "description": description,
                "issue_type": issue_type,
                "priority": priority,
                "project_key": project_key,
                "status": "To Do",
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to create Jira issue: {e}")
            return {"error": str(e)}

    async def update_jira_issue(self, issue_key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing Jira issue

        Args:
            issue_key: Issue key
            updates: Fields to update

        Returns:
            Updated issue details
        """
        if not self.jira_enabled:
            return {"error": "Jira not enabled"}

        try:
            base_url = f"{self.jira_url.rstrip('/')}/rest/api/2/issue/{issue_key}"
            async with httpx.AsyncClient(
                auth=(self.jira_username, self.jira_api_token),
                timeout=30.0,
            ) as client:
                response = await client.put(base_url, json={"fields": updates})
                response.raise_for_status()

            logger.info(f"Updated Jira issue: {issue_key}")
            return {
                "key": issue_key,
                "updated": True,
                "updates": updates,
                "updated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to update Jira issue: {e}")
            return {"error": str(e)}

    async def sync_alert_to_itsm(
        self, alert_id: str, alert_data: Dict[str, Any], target_system: str = "both"
    ) -> Dict[str, Any]:
        """
        Synchronize an alert to ITSM systems

        Args:
            alert_id: Alert ID
            alert_data: Alert data
            target_system: Target system (servicenow, jira, or both)

        Returns:
            Sync results
        """
        results = {}

        if target_system in ["servicenow", "both"] and self.servicenow_enabled:
            results["servicenow"] = await self.create_servicenow_incident(
                title=f"Alert: {alert_id}",
                description=alert_data.get("description", ""),
                severity=alert_data.get("severity", "medium"),
            )

        if target_system in ["jira", "both"] and self.jira_enabled:
            results["jira"] = await self.create_jira_issue(
                summary=f"Alert: {alert_id}",
                description=alert_data.get("description", ""),
                priority=alert_data.get("severity", "Medium"),
            )

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            "initialized": self._is_initialized,
            "servicenow": {
                "enabled": self.servicenow_enabled,
                "instance": self.servicenow_instance,
            },
            "jira": {"enabled": self.jira_enabled, "url": self.jira_url},
        }


# Global singleton instance
_itsm_integration: Optional[ITSMIntegration] = None


def get_itsm_integration() -> Optional[ITSMIntegration]:
    """Get global ITSM integration instance"""
    return _itsm_integration


def init_itsm_integration(config: Dict[str, Any]) -> ITSMIntegration:
    """Initialize global ITSM integration"""
    global _itsm_integration
    _itsm_integration = ITSMIntegration(config)
    return _itsm_integration
