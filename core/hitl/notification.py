# -*- coding: utf-8 -*-
"""
Approval Notification
Handles approval notifications via Slack/Teams
"""

from dataclasses import dataclass
from typing import Dict

from loguru import logger


@dataclass
class NotificationConfig:
    """
    Notification configuration

    Attributes:
        platform: Notification platform (slack, teams)
        webhook_url: Webhook URL
        channel: Channel to notify
    """

    platform: str
    webhook_url: str
    channel: str


class ApprovalNotifier:
    """
    Approval notification manager

    Sends notifications for approval requests via Slack/Teams
    """

    def __init__(self):
        """Initialize approval notifier"""
        self.configs: Dict[str, NotificationConfig] = {}

    def configure(self, config: NotificationConfig) -> None:
        """
        Configure notification platform

        Args:
            config: Notification configuration
        """
        self.configs[config.platform] = config
        logger.info(f"Configured notification platform: {config.platform}")

    def send_approval_request(self, platform: str, approver: str, request_data: Dict) -> bool:
        """
        Send approval request notification

        Args:
            platform: Notification platform
            approver: Approver to notify
            request_data: Request data

        Returns:
            True if sent successfully
        """
        config = self.configs.get(platform)
        if not config:
            logger.warning(f"No configuration for platform: {platform}")
            return False

        # Build notification message
        message = self._build_approval_message(approver, request_data)

        # Send notification (simplified - would use actual API in production)
        logger.info(f"Sending approval notification to {approver} via {platform}")
        logger.info(f"Message: {message}")

        return True

    def send_approval_complete(
        self, platform: str, requester: str, request_data: Dict, approved: bool
    ) -> bool:
        """
        Send approval completion notification

        Args:
            platform: Notification platform
            requester: Requester to notify
            request_data: Request data
            approved: Whether approved

        Returns:
            True if sent successfully
        """
        config = self.configs.get(platform)
        if not config:
            return False

        # Build notification message
        message = self._build_completion_message(requester, request_data, approved)

        logger.info(f"Sending completion notification to {requester} via {platform}")
        logger.info(f"Message: {message}")

        return True

    def _build_approval_message(self, approver: str, request_data: Dict) -> str:
        """Build approval request message"""
        return (
            f"Approval Request for {approver}\n"
            f"Title: {request_data.get('title', 'N/A')}\n"
            f"Description: {request_data.get('description', 'N/A')}\n"
            "Please review and approve/reject."
        )

    def _build_completion_message(self, requester: str, request_data: Dict, approved: bool) -> str:
        """Build completion notification message"""
        status = "Approved" if approved else "Rejected"
        return f"Approval {status}\nRequest: {request_data.get('title', 'N/A')}\nStatus: {status}"
