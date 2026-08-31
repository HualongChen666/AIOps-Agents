# -*- coding: utf-8 -*-
"""
L7 Integration Layer - Collaboration Integration (Slack, Teams)
Provides integration with collaboration platforms for notifications and approvals
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


class CollaborationIntegration:
    """
    Collaboration Integration for L7 Layer

    This integration provides:
    - Slack notifications and approvals
    - Microsoft Teams notifications and approvals
    - Rich message formatting
    - Interactive buttons and workflows
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        # Slack configuration
        self.slack_enabled = config.get("slack", {}).get("enabled", False)
        self.slack_bot_token = config.get("slack", {}).get("bot_token", "")
        self.slack_channel = config.get("slack", {}).get("channel", "")
        self.slack_api_url = config.get("slack", {}).get(
            "api_url", "https://slack.com/api/chat.postMessage"
        )

        # Teams configuration
        self.teams_enabled = config.get("teams", {}).get("enabled", False)
        self.teams_webhook = config.get("teams", {}).get("webhook", "")
        self.teams_channel = config.get("teams", {}).get("channel", "")

        self._is_initialized = False

        if self.slack_enabled or self.teams_enabled:
            self._is_initialized = True
            logger.info("Collaboration Integration initialized")

    async def send_slack_notification(
        self,
        message: str,
        channel: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a notification to Slack

        Args:
            message: Message text
            channel: Target channel (overrides default)
            attachments: Message attachments

        Returns:
            Send result
        """
        if not self.slack_enabled:
            logger.warning("Slack integration not enabled")
            return {"error": "Slack not enabled"}

        try:
            target_channel = channel or self.slack_channel
            payload = {
                "channel": target_channel,
                "text": message,
                "attachments": attachments or [],
            }

            async with httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            ) as client:
                response = await client.post(self.slack_api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    raise RuntimeError(result.get("error", "Slack API error"))

            logger.info(f"Sent Slack notification to {target_channel}")
            return {
                "success": True,
                "channel": target_channel,
                "timestamp": datetime.now().isoformat(),
                "ts": result.get("ts"),
            }

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return {"error": str(e)}

    async def send_slack_approval_request(
        self, title: str, description: str, actions: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Send an approval request to Slack with interactive buttons

        Args:
            title: Request title
            description: Request description
            actions: Button actions (approve, reject, etc.)

        Returns:
            Send result
        """
        if not self.slack_enabled:
            return {"error": "Slack not enabled"}

        try:
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{title}*\n{description}"},
                }
            ]
            action_elements = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": action["text"]},
                    "value": action["value"],
                    "action_id": action["value"],
                }
                for action in (actions or [])
            ]
            if action_elements:
                blocks.append({"type": "actions", "elements": action_elements})

            payload = {
                "channel": self.slack_channel,
                "text": title,
                "blocks": blocks,
            }

            async with httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            ) as client:
                response = await client.post(self.slack_api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    raise RuntimeError(result.get("error", "Slack API error"))

            logger.info(f"Sent Slack approval request: {title}")
            return {
                "success": True,
                "channel": self.slack_channel,
                "timestamp": datetime.now().isoformat(),
                "ts": result.get("ts"),
            }

        except Exception as e:
            logger.error(f"Failed to send Slack approval request: {e}")
            return {"error": str(e)}

    async def send_teams_notification(
        self, message: str, title: Optional[str] = None, color: str = "0078D4"
    ) -> Dict[str, Any]:
        """
        Send a notification to Microsoft Teams

        Args:
            message: Message text
            title: Message title
            color: Message color (hex)

        Returns:
            Send result
        """
        if not self.teams_enabled:
            logger.warning("Teams integration not enabled")
            return {"error": "Teams not enabled"}

        try:
            card = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "themeColor": color,
                "summary": title or "Notification",
                "sections": [
                    {
                        "activityTitle": title or "Notification",
                        "activitySubtitle": message,
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.teams_webhook, json=card)
                response.raise_for_status()

            logger.info("Sent Teams notification")
            return {"success": True, "timestamp": datetime.now().isoformat()}

        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return {"error": str(e)}

    async def send_teams_approval_card(
        self, title: str, description: str, actions: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Send an adaptive card to Teams with approval buttons

        Args:
            title: Card title
            description: Card description
            actions: Button actions

        Returns:
            Send result
        """
        if not self.teams_enabled:
            return {"error": "Teams not enabled"}

        try:
            body = [
                {
                    "type": "TextBlock",
                    "text": title,
                    "weight": "bolder",
                    "size": "medium",
                }
            ]
            if description:
                body.append({"type": "TextBlock", "text": description, "wrap": True})

            action_items = [
                {
                    "type": "Action.Submit",
                    "title": action["text"],
                    "data": {"value": action["value"]},
                }
                for action in (actions or [])
            ]

            card = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": {
                            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.0",
                            "body": body,
                            "actions": action_items,
                        },
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.teams_webhook, json=card)
                response.raise_for_status()

            logger.info(f"Sent Teams approval card: {title}")
            return {"success": True, "timestamp": datetime.now().isoformat()}

        except Exception as e:
            logger.error(f"Failed to send Teams approval card: {e}")
            return {"error": str(e)}

    async def send_slack_file_upload(
        self, file_path: str, channels: Optional[str] = None, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Slack

        Args:
            file_path: Path to the file
            channels: Target channels
            filename: Custom filename

        Returns:
            Upload result
        """
        if not self.slack_enabled:
            return {"error": "Slack not enabled"}

        try:
            target_channels = channels or self.slack_channel
            upload_url = "https://slack.com/api/files.upload"
            
            with open(file_path, "rb") as f:
                files = {"file": (filename or file_path.split("/")[-1], f)}
                data = {
                    "channels": target_channels,
                    "initial_comment": "File uploaded from AIOps Agent"
                }
                
                async with httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {self.slack_bot_token}"},
                    timeout=60.0,
                ) as client:
                    response = await client.post(upload_url, data=data, files=files)
                    response.raise_for_status()
                    result = response.json()
                    if not result.get("ok"):
                        raise RuntimeError(result.get("error", "Slack file upload error"))

            logger.info(f"Uploaded file to Slack: {file_path}")
            return {
                "success": True,
                "file": result.get("file", {}),
                "channels": target_channels,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to upload file to Slack: {e}")
            return {"error": str(e)}

    async def send_teams_file_upload(
        self, file_path: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Teams

        Args:
            file_path: Path to the file
            filename: Custom filename

        Returns:
            Upload result
        """
        if not self.teams_enabled:
            return {"error": "Teams not enabled"}

        try:
            card = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": {
                            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.0",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "File Upload",
                                    "weight": "bolder",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"File: {filename or file_path}",
                                    "wrap": True,
                                }
                            ],
                        },
                    }
                ],
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.teams_webhook, json=card)
                response.raise_for_status()

            logger.info(f"Sent file upload notification to Teams: {file_path}")
            return {"success": True, "timestamp": datetime.now().isoformat()}

        except Exception as e:
            logger.error(f"Failed to send file upload to Teams: {e}")
            return {"error": str(e)}

    async def get_slack_channel_info(self, channel: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a Slack channel

        Args:
            channel: Channel ID (overrides default)

        Returns:
            Channel information
        """
        if not self.slack_enabled:
            return {"error": "Slack not enabled"}

        try:
            target_channel = channel or self.slack_channel
            info_url = "https://slack.com/api/conversations.info"
            
            async with httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            ) as client:
                response = await client.post(info_url, json={"channel": target_channel})
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    raise RuntimeError(result.get("error", "Slack API error"))

            channel_info = result.get("channel", {})
            logger.info(f"Retrieved Slack channel info: {target_channel}")
            return {
                "id": channel_info.get("id", ""),
                "name": channel_info.get("name", ""),
                "is_channel": channel_info.get("is_channel", False),
                "is_private": channel_info.get("is_private", False),
                "members": channel_info.get("num_members", 0),
                "topic": channel_info.get("topic", {}).get("value", ""),
            }

        except Exception as e:
            logger.error(f"Failed to get Slack channel info: {e}")
            return {"error": str(e)}

    async def get_slack_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about a Slack user

        Args:
            user_id: User ID

        Returns:
            User information
        """
        if not self.slack_enabled:
            return {"error": "Slack not enabled"}

        try:
            users_url = "https://slack.com/api/users.info"
            
            async with httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.slack_bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            ) as client:
                response = await client.post(users_url, json={"user": user_id})
                response.raise_for_status()
                result = response.json()
                if not result.get("ok"):
                    raise RuntimeError(result.get("error", "Slack API error"))

            user_info = result.get("user", {})
            logger.info(f"Retrieved Slack user info: {user_id}")
            return {
                "id": user_info.get("id", ""),
                "name": user_info.get("real_name", ""),
                "display_name": user_info.get("display_name", ""),
                "email": user_info.get("profile", {}).get("email", ""),
                "is_admin": user_info.get("is_admin", False),
                "is_owner": user_info.get("is_owner", False),
            }

        except Exception as e:
            logger.error(f"Failed to get Slack user info: {e}")
            return {"error": str(e)}

    async def notify_alert(
        self, alert_id: str, alert_data: Dict[str, Any], platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send alert notification to collaboration platforms

        Args:
            alert_id: Alert ID
            alert_data: Alert data
            platforms: Target platforms (slack, teams, or both)

        Returns:
            Notification results
        """
        results = {}
        platforms = platforms or ["slack", "teams"]

        message = f"🚨 Alert: {alert_id}\n"
        message += f"Severity: {alert_data.get('severity', 'unknown')}\n"
        message += f"Description: {alert_data.get('description', 'No description')}"

        if "slack" in platforms and self.slack_enabled:
            results["slack"] = await self.send_slack_notification(message)

        if "teams" in platforms and self.teams_enabled:
            results["teams"] = await self.send_teams_notification(
                message, title=f"Alert: {alert_id}"
            )

        return results

    async def request_approval(
        self, repair_id: str, repair_data: Dict[str, Any], platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send approval request for a repair action

        Args:
            repair_id: Repair ID
            repair_data: Repair data
            platforms: Target platforms

        Returns:
            Approval request results
        """
        results = {}
        platforms = platforms or ["slack", "teams"]

        title = f"Repair Approval Required: {repair_id}"
        description = repair_data.get("description", "No description")

        actions = [{"text": "Approve", "value": "approve"}, {"text": "Reject", "value": "reject"}]

        if "slack" in platforms and self.slack_enabled:
            results["slack"] = await self.send_slack_approval_request(title, description, actions)

        if "teams" in platforms and self.teams_enabled:
            results["teams"] = await self.send_teams_approval_card(title, description, actions)

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            "initialized": self._is_initialized,
            "slack": {"enabled": self.slack_enabled, "channel": self.slack_channel},
            "teams": {"enabled": self.teams_enabled, "channel": self.teams_channel},
        }


# Global singleton instance
_collaboration_integration: Optional[CollaborationIntegration] = None


def get_collaboration_integration() -> Optional[CollaborationIntegration]:
    """Get global collaboration integration instance"""
    return _collaboration_integration


def init_collaboration_integration(config: Dict[str, Any]) -> CollaborationIntegration:
    """Initialize global collaboration integration"""
    global _collaboration_integration
    _collaboration_integration = CollaborationIntegration(config)
    return _collaboration_integration
