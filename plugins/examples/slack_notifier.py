# -*- coding: utf-8 -*-
"""
Example Plugin 3: Slack Notifier

This plugin demonstrates how to send notifications to Slack
with custom formatting and severity levels.
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from core.plugin_system import BasePlugin, PluginMetadata, PluginType

logger = logging.getLogger(__name__)


class SlackNotifierPlugin(BasePlugin):
    """
    Slack Notifier Plugin
    
    Sends formatted notifications to Slack channels
    with support for different severity levels and custom message formatting.
    """
    
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        return PluginMetadata(
            name="slack_notifier",
            version="1.0.0",
            description="Sends formatted notifications to Slack channels",
            author="AIOps Team",
            plugin_type=PluginType.NOTIFIER,
            dependencies=["aiohttp"],
            config_schema={
                "type": "object",
                "properties": {
                    "webhook_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "Slack webhook URL"
                    },
                    "channel": {
                        "type": "string",
                        "default": "#alerts",
                        "description": "Slack channel to send notifications to"
                    },
                    "username": {
                        "type": "string",
                        "default": "AIOps Bot",
                        "description": "Bot username"
                    },
                    "icon_emoji": {
                        "type": "string",
                        "default": ":robot_face:",
                        "description": "Bot icon emoji"
                    },
                    "default_severity": {
                        "type": "string",
                        "enum": ["info", "warning", "error", "critical"],
                        "default": "info",
                        "description": "Default severity level"
                    }
                },
                "required": ["webhook_url"]
            }
        )
    
    def initialize(self) -> bool:
        """Initialize the plugin"""
        if not self.validate_config(["webhook_url"]):
            logger.error("Invalid configuration: missing webhook_url")
            return False
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._channel = self.config.get("channel", "#alerts")
        self._username = self.config.get("username", "AIOps Bot")
        self._icon_emoji = self.config.get("icon_emoji", ":robot_face:")
        self._default_severity = self.config.get("default_severity", "info")
        
        logger.info(f"SlackNotifierPlugin initialized for channel: {self._channel}")
        self._is_initialized = True
        return True
    
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic to send notification"""
        if not self._is_initialized:
            return {"status": "error", "error": "Plugin not initialized"}
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            # Extract message details
            message = data.get("message", "No message provided")
            severity = data.get("severity", self._default_severity)
            title = data.get("title", "AIOps Alert")
            timestamp = data.get("timestamp", "")
            fields = data.get("fields", [])
            
            # Validate severity
            valid_severities = ["info", "warning", "error", "critical"]
            if severity not in valid_severities:
                severity = self._default_severity
                logger.warning(f"Invalid severity, using default: {severity}")
            
            # Build Slack payload
            payload = self._build_slack_payload(
                title=title,
                message=message,
                severity=severity,
                timestamp=timestamp,
                fields=fields
            )
            
            # Send to Slack
            async with self._session.post(
                self.config["webhook_url"],
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Notification sent to Slack: {title}")
                    return {
                        "status": "success",
                        "channel": self._channel,
                        "severity": severity
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Slack API error: {response.status} - {error_text}")
                    return {
                        "status": "error",
                        "error": f"Slack API returned {response.status}",
                        "details": error_text
                    }
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {"status": "error", "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
    
    def _build_slack_payload(
        self,
        title: str,
        message: str,
        severity: str,
        timestamp: str,
        fields: list
    ) -> Dict[str, Any]:
        """Build Slack message payload"""
        # Color based on severity
        colors = {
            "info": "#36a64f",      # Green
            "warning": "#ff9900",   # Orange
            "error": "#ff0000",     # Red
            "critical": "#990000"   # Dark red
        }
        color = colors.get(severity, "#36a64f")
        
        # Build attachment fields
        attachment_fields = [
            {
                "title": "Severity",
                "value": severity.upper(),
                "short": True
            },
            {
                "title": "Timestamp",
                "value": timestamp or "N/A",
                "short": True
            }
        ]
        
        # Add custom fields
        for field in fields:
            if isinstance(field, dict) and "title" in field and "value" in field:
                attachment_fields.append({
                    "title": field["title"],
                    "value": field["value"],
                    "short": field.get("short", False)
                })
        
        # Build payload
        payload = {
            "channel": self._channel,
            "username": self._username,
            "icon_emoji": self._icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "fields": attachment_fields,
                    "footer": "AIOps Platform",
                    "ts": None  # Disable timestamp for now
                }
            ]
        }
        
        return payload
    
    def close(self) -> None:
        """Close the plugin and release resources"""
        if self._session:
            self._session.close()
            self._session = None
        
        self._is_initialized = False
        logger.info("SlackNotifierPlugin closed")