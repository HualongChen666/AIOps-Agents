# -*- coding: utf-8 -*-
import logging

"""
Approval Notification
Handles approval notifications via Slack/Teams
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from core.notify_engine import (
        _send_dingtalk,
        _send_feishu,
        _send_wecom,
        send_email_notification,
        send_slack_notification,
        send_teams_notification,
    )

    NOTIFY_ENGINE_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    NOTIFY_ENGINE_AVAILABLE = False
    (
        _send_wecom,
        _send_dingtalk,
        _send_feishu,
        send_slack_notification,
        send_teams_notification,
        send_email_notification,
    ) = (None, None, None, None, None, None)


@dataclass
class NotificationConfig:
    """
    Notification configuration

    Attributes:
        platform: Notification platform (wecom, dingtalk, feishu, slack, teams, email)
        webhook_url: Webhook URL (or email SMTP host URL for email)
        channel: Channel to notify (for slack)
        address: Email/phone address (for email/sms)
        smtp_host: SMTP host for email
        smtp_port: SMTP port for email
    """

    platform: str
    webhook_url: str = ""
    channel: str = ""
    address: str = ""
    smtp_host: str = "localhost"
    smtp_port: int = 25


class ApprovalNotifier:
    """
    Approval notification manager

    Sends notifications for approval requests via all configured channels with
    automatic fallback. Messages carry rich context for escalation.
    """

    def __init__(self, configs: Optional[Dict[str, NotificationConfig]] = None):
        """Initialize approval notifier"""
        self.configs: Dict[str, NotificationConfig] = configs or {}
        self._notification_history: List[Dict[str, Any]] = []

    def configure(self, config: NotificationConfig) -> None:
        """
        Configure notification platform

        Args:
            config: Notification configuration
        """
        self.configs[config.platform] = config
        logger.info(f"Configured notification platform: {config.platform}")

    def auto_configure_from_env(self) -> None:
        """Auto-configure channels from core.notify_engine environment config."""
        if not NOTIFY_ENGINE_AVAILABLE:
            logger.warning("notify_engine not available, cannot auto-configure")
            return
        try:
            from core.notify_engine import NOTIFY_CONFIG
        except Exception as exc:  # pragma: no cover
            logger.warning(f"Failed to load NOTIFY_CONFIG: {exc}")
            return

        if NOTIFY_CONFIG.get("wecom_webhook"):
            self.configure(
                NotificationConfig(platform="wecom", webhook_url=NOTIFY_CONFIG["wecom_webhook"])
            )
        if NOTIFY_CONFIG.get("dingtalk_webhook"):
            self.configure(
                NotificationConfig(
                    platform="dingtalk", webhook_url=NOTIFY_CONFIG["dingtalk_webhook"]
                )
            )
        if NOTIFY_CONFIG.get("feishu_webhook"):
            self.configure(
                NotificationConfig(platform="feishu", webhook_url=NOTIFY_CONFIG["feishu_webhook"])
            )
        if NOTIFY_CONFIG.get("email_to"):
            self.configure(NotificationConfig(platform="email", address=NOTIFY_CONFIG["email_to"]))

    async def send_approval_request(
        self,
        approver: str,
        request_data: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        strategy: str = "parallel",
    ) -> Dict[str, Any]:
        """
        Send approval request notification to configured channels.

        Args:
            strategy: 'parallel' tries all channels at once; 'sequential'
                tries them one-by-one until the first success.

        Returns:
            dict with 'success', 'channels', and 'errors'.
        """
        message = self._build_approval_message(approver, request_data)
        return await self._send_to_channels(
            approver,
            request_data,
            message,
            is_completion=False,
            platforms=platforms,
            strategy=str(strategy).lower(),
        )

    async def send_approval_complete(
        self,
        requester: str,
        request_data: Dict[str, Any],
        approved: bool,
        platforms: Optional[List[str]] = None,
        strategy: str = "parallel",
    ) -> Dict[str, Any]:
        """
        Send approval completion notification to configured channels.

        Args:
            strategy: 'parallel' tries all channels at once; 'sequential'
                tries them one-by-one until the first success.

        Returns:
            dict with 'success', 'channels', and 'errors'.
        """
        message = self._build_completion_message(requester, request_data, approved)
        return await self._send_to_channels(
            requester,
            request_data,
            message,
            is_completion=True,
            platforms=platforms,
            strategy=str(strategy).lower(),
        )

    async def _send_to_channels(
        self,
        recipient: str,
        request_data: Dict[str, Any],
        message: str,
        is_completion: bool,
        platforms: Optional[List[str]] = None,
        strategy: str = "parallel",
    ) -> Dict[str, Any]:
        targets = platforms or list(self.configs.keys())
        if not targets:
            return {"success": False, "channels": [], "errors": ["no channels configured"]}

        filtered_targets = []
        for platform in targets:
            if self.configs.get(platform):
                filtered_targets.append(platform)
        if not filtered_targets:
            return {"success": False, "channels": [], "errors": ["no valid channel configs"]}

        if str(strategy).lower() == "sequential":
            return await self._send_to_channels_sequential(
                recipient, request_data, message, is_completion, filtered_targets
            )

        tasks = []
        for platform in filtered_targets:
            config = self.configs[platform]
            tasks.append(self._send_one(platform, config, recipient, request_data, message))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        errors: List[str] = []
        sent: List[str] = []
        for platform, result in zip(filtered_targets, results):
            if isinstance(result, Exception):
                logger.error(f"Approval notification failed for {platform}: {result}")
                errors.append(f"{platform}: {result}")
            elif isinstance(result, dict) and result.get("success"):
                sent.append(platform)
            else:
                error = result.get("error", "unknown") if isinstance(result, dict) else str(result)
                errors.append(f"{platform}: {error}")

        success = len(sent) > 0
        self._notification_history.append(
            {
                "recipient": recipient,
                "request_id": request_data.get("request_id"),
                "is_completion": is_completion,
                "success": success,
                "channels": sent,
                "errors": errors,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return {"success": success, "channels": sent, "errors": errors}

    async def _send_to_channels_sequential(
        self,
        recipient: str,
        request_data: Dict[str, Any],
        message: str,
        is_completion: bool,
        targets: List[str],
    ) -> Dict[str, Any]:
        """Try channels in order until one succeeds, providing strict fallback."""
        errors: List[str] = []
        sent: List[str] = []
        for platform in targets:
            config = self.configs.get(platform)
            if not config:
                continue
            try:
                result = await self._send_one(platform, config, recipient, request_data, message)
                if isinstance(result, dict) and result.get("success"):
                    sent.append(platform)
                    break
                error = result.get("error", "unknown") if isinstance(result, dict) else str(result)
                errors.append(f"{platform}: {error}")
                logger.warning(f"Approval notification channel {platform} failed: {error}")
            except Exception as exc:
                logger.error(f"Approval notification failed for {platform}: {exc}")
                errors.append(f"{platform}: {exc}")

        success = len(sent) > 0
        self._notification_history.append(
            {
                "recipient": recipient,
                "request_id": request_data.get("request_id"),
                "is_completion": is_completion,
                "success": success,
                "channels": sent,
                "errors": errors,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return {"success": success, "channels": sent, "errors": errors}

    async def _send_one(
        self,
        platform: str,
        config: NotificationConfig,
        recipient: str,
        request_data: Dict[str, Any],
        message: str,
    ) -> Dict[str, Any]:
        alert_payload = {
            "title": request_data.get("title", "Approval Request"),
            "desc": message,
            "level": request_data.get("context", {}).get("risk_level", "critical"),
            "raw_time": datetime.now().isoformat(),
        }

        if platform == "wecom" and _send_wecom:
            return await _send_wecom(alert_payload)
        if platform == "dingtalk" and _send_dingtalk:
            return await _send_dingtalk(alert_payload)
        if platform == "feishu" and _send_feishu:
            return await _send_feishu(alert_payload)
        if platform == "teams" and send_teams_notification:
            return await send_teams_notification(message, config.webhook_url)
        if platform == "slack" and send_slack_notification:
            return await send_slack_notification(message, config.channel or "#alerts")
        if platform == "email" and send_email_notification:
            to = config.address or recipient
            subject = request_data.get("title", "Approval Request")
            return await send_email_notification(
                to=to,
                subject=subject,
                body=message,
                smtp_host=config.smtp_host,
                smtp_port=config.smtp_port,
            )

        return {"success": False, "error": f"unsupported or unavailable channel: {platform}"}

    def _build_approval_message(self, approver: str, request_data: Dict[str, Any]) -> str:
        """Build rich approval request message with full context."""
        context = request_data.get("context") or {}
        lines = [
            f"Hi {approver}, you have an approval request.",
            f"Title: {request_data.get('title', 'N/A')}",
            f"Description: {request_data.get('description', 'N/A')}",
            f"Request ID: {request_data.get('request_id', 'N/A')}",
        ]

        alert = context.get("alert")
        if alert:
            lines.append(f"Original Alert: {alert}")

        diagnosis = context.get("diagnosis") or context.get("root_cause")
        if diagnosis:
            lines.append(f"Diagnosis / Root Cause: {diagnosis}")

        excluded = context.get("excluded_causes")
        if excluded:
            lines.append(f"Excluded Causes: {excluded}")

        hypothesis = context.get("hypothesis")
        if hypothesis:
            lines.append(f"Current Hypothesis: {hypothesis}")

        confidence = context.get("confidence")
        if confidence is not None:
            lines.append(f"Confidence: {confidence}")

        executed = context.get("executed_commands") or context.get("actions")
        if executed:
            lines.append(f"Executed Operations: {executed}")

        links = {
            k: v
            for k, v in context.items()
            if isinstance(v, str) and ("dashboard" in k or "log" in k or "trace" in k or "url" in k)
        }
        if links:
            lines.append("Links:")
            for name, url in links.items():
                lines.append(f"  - {name}: {url}")

        lines.append("Please review and approve/reject.")
        return "\n".join(lines)

    def _build_completion_message(
        self, requester: str, request_data: Dict[str, Any], approved: bool
    ) -> str:
        """Build rich completion notification message."""
        status = "Approved" if approved else "Rejected"
        context = request_data.get("context") or {}
        result_summary = context.get("result_summary", "")
        return (
            f"Approval {status}\n"
            f"Request: {request_data.get('title', 'N/A')}\n"
            f"Request ID: {request_data.get('request_id', 'N/A')}\n"
            f"Result: {result_summary or status}\n"
            "Please check the system for details."
        )
