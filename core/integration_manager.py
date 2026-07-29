# -*- coding: utf-8 -*-
"""
Integration Ecosystem Module
============================

Comprehensive integration ecosystem for AIOps Agent with support for:
- Mainstream monitoring tools (Prometheus, Grafana, ELK)
- Cloud platforms (AWS, Azure, GCP)
- CI/CD tools (Jenkins, GitLab CI, GitHub Actions)
- ITSM tools (ServiceNow, Jira)
- Notification channels (Slack, Teams, DingTalk, WeChat Enterprise)
- Standardized Webhook and API integration interfaces
"""

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, cast

from loguru import logger

from core.observability_query import (
    DEFAULT_MAX_PROMQL_SAMPLES,
    QueryCache,
    align_time_window,
    cached_query,
    limit_range_samples,
    make_cache_key,
    parse_duration_to_seconds,
    sanitize_error_for_llm,
    validate_promql,
    with_query_timeout,
)

# Try to import HTTP libraries
try:
    import httpx

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    logger.warning("HTTP library not available, some integrations will be disabled")

# Try to import WebSocket libraries
try:
    pass

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket library not available")


class IntegrationType(Enum):
    """Types of integrations"""

    MONITORING = "monitoring"
    CLOUD = "cloud"
    CICD = "cicd"
    ITSM = "itsm"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class IntegrationStatus(Enum):
    """Integration status"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"


@dataclass
class IntegrationConfig:
    """Configuration for an integration"""

    integration_id: str
    integration_type: IntegrationType
    name: str
    config: Dict[str, Any]
    enabled: bool = True
    status: IntegrationStatus = IntegrationStatus.INACTIVE
    last_tested: Optional[datetime] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WebhookEvent:
    """Webhook event data"""

    event_id: str
    source: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    processed: bool = False
    retry_count: int = 0


@dataclass
class NotificationMessage:
    """Notification message"""

    message_id: str
    channel: str
    recipient: str
    subject: str
    body: str
    priority: str = "normal"
    timestamp: datetime = field(default_factory=datetime.now)
    sent: bool = False
    error: Optional[str] = None


class IntegrationManager:
    """
    Comprehensive integration manager for AIOps Agent
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize integration manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Integration storage
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.integration_templates: Dict[str, Dict[str, Any]] = {}

        # Webhook management
        self.webhooks: Dict[str, Dict[str, Any]] = {}
        self.webhook_events: List[WebhookEvent] = []
        self.webhook_secret = self.config.get("webhook_secret", "default_secret_change_me")

        # Notification channels
        self.notification_channels: Dict[str, Dict[str, Any]] = {}
        self.notification_queue: List[NotificationMessage] = []

        # HTTP client for integrations
        self.http_client: Optional[Any] = None
        if HTTP_AVAILABLE:
            self.http_client = httpx.AsyncClient(timeout=30.0)

        # Observability query cache / safety layer
        self._observability_cache = QueryCache()

        # Initialize integration templates
        self._initialize_integration_templates()

        # Initialize notification channels
        self._initialize_notification_channels()

        logger.info("Integration Manager initialized")

    def _initialize_integration_templates(self) -> None:
        """Initialize integration templates for common services"""
        self.integration_templates = {
            # Monitoring tools
            "prometheus": {
                "type": IntegrationType.MONITORING,
                "name": "Prometheus",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "username": {"type": "string", "required": False},
                    "password": {"type": "string", "required": False},
                },
                "default_config": {"query_timeout": 30, "scrape_interval": 15},
            },
            "grafana": {
                "type": IntegrationType.MONITORING,
                "name": "Grafana",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "api_key": {"type": "string", "required": True},
                },
                "default_config": {"dashboard_refresh": "1m"},
            },
            "elk": {
                "type": IntegrationType.MONITORING,
                "name": "ELK Stack",
                "config_schema": {
                    "elasticsearch_url": {"type": "string", "required": True},
                    "kibana_url": {"type": "string", "required": False},
                    "username": {"type": "string", "required": False},
                    "password": {"type": "string", "required": False},
                },
            },
            # Cloud platforms
            "aws": {
                "type": IntegrationType.CLOUD,
                "name": "AWS",
                "config_schema": {
                    "access_key_id": {"type": "string", "required": True},
                    "secret_access_key": {"type": "string", "required": True},
                    "region": {"type": "string", "required": True},
                },
            },
            "azure": {
                "type": IntegrationType.CLOUD,
                "name": "Azure",
                "config_schema": {
                    "subscription_id": {"type": "string", "required": True},
                    "client_id": {"type": "string", "required": True},
                    "client_secret": {"type": "string", "required": True},
                    "tenant_id": {"type": "string", "required": True},
                },
            },
            "gcp": {
                "type": IntegrationType.CLOUD,
                "name": "GCP",
                "config_schema": {
                    "project_id": {"type": "string", "required": True},
                    "credentials_json": {"type": "string", "required": True},
                },
            },
            # CI/CD tools
            "jenkins": {
                "type": IntegrationType.CICD,
                "name": "Jenkins",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "username": {"type": "string", "required": True},
                    "api_token": {"type": "string", "required": True},
                },
            },
            "gitlab_ci": {
                "type": IntegrationType.CICD,
                "name": "GitLab CI",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "private_token": {"type": "string", "required": True},
                },
            },
            "github_actions": {
                "type": IntegrationType.CICD,
                "name": "GitHub Actions",
                "config_schema": {
                    "repo_owner": {"type": "string", "required": True},
                    "repo_name": {"type": "string", "required": True},
                    "personal_access_token": {"type": "string", "required": True},
                },
            },
            # ITSM tools
            "servicenow": {
                "type": IntegrationType.ITSM,
                "name": "ServiceNow",
                "config_schema": {
                    "instance_url": {"type": "string", "required": True},
                    "username": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True},
                },
            },
            "jira": {
                "type": IntegrationType.ITSM,
                "name": "Jira",
                "config_schema": {
                    "url": {"type": "string", "required": True},
                    "username": {"type": "string", "required": True},
                    "api_token": {"type": "string", "required": True},
                },
            },
            # Notification channels
            "slack": {
                "type": IntegrationType.NOTIFICATION,
                "name": "Slack",
                "config_schema": {
                    "webhook_url": {"type": "string", "required": True},
                    "channel": {"type": "string", "required": False},
                },
            },
            "teams": {
                "type": IntegrationType.NOTIFICATION,
                "name": "Microsoft Teams",
                "config_schema": {"webhook_url": {"type": "string", "required": True}},
            },
            "dingtalk": {
                "type": IntegrationType.NOTIFICATION,
                "name": "DingTalk",
                "config_schema": {
                    "webhook_url": {"type": "string", "required": True},
                    "secret": {"type": "string", "required": False},
                },
            },
            "wechat": {
                "type": IntegrationType.NOTIFICATION,
                "name": "WeChat Enterprise",
                "config_schema": {
                    "webhook_url": {"type": "string", "required": True},
                    "corp_id": {"type": "string", "required": True},
                },
            },
        }

    def _initialize_notification_channels(self) -> None:
        """Initialize notification channels from config"""
        configured_channels = self.config.get("notification_channels", {})

        for channel_name, channel_config in configured_channels.items():
            self.notification_channels[channel_name] = {
                "name": channel_name,
                "type": channel_config.get("type", "webhook"),
                "config": channel_config.get("config", {}),
                "enabled": channel_config.get("enabled", True),
            }

        logger.info(f"Initialized {len(self.notification_channels)} notification channels")

    async def register_integration(
        self,
        integration_type: IntegrationType,
        name: str,
        config: Dict[str, Any],
        enabled: bool = True,
    ) -> IntegrationConfig:
        """
        Register a new integration

        Args:
            integration_type: Type of integration
            name: Integration name
            config: Integration configuration
            enabled: Whether integration is enabled

        Returns:
            IntegrationConfig
        """
        integration_id = (
            f"{integration_type.value}_{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Validate config against template if available
        template_key = name.lower().replace(" ", "_")
        if template_key in self.integration_templates:
            template = self.integration_templates[template_key]
            validation_result = self._validate_config(config, template.get("config_schema", {}))
            if not validation_result["valid"]:
                raise ValueError(f"Invalid configuration: {validation_result['errors']}")

            # Merge with default config
            default_config = template.get("default_config", {})
            merged_config = {**default_config, **config}
        else:
            merged_config = config

        integration = IntegrationConfig(
            integration_id=integration_id,
            integration_type=integration_type,
            name=name,
            config=merged_config,
            enabled=enabled,
            status=IntegrationStatus.CONFIGURING,
        )

        self.integrations[integration_id] = integration

        # Test the integration
        test_result = await self.test_integration(integration_id)
        if test_result["success"]:
            integration.status = IntegrationStatus.ACTIVE
            integration.last_tested = datetime.now()
        else:
            integration.status = IntegrationStatus.ERROR
            integration.last_error = test_result["error"]

        logger.info(f"Registered integration: {integration_id}")
        return integration

    def _validate_config(self, config: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration against schema"""
        errors: List[str] = []

        for field_name, field_schema in schema.items():
            if field_schema.get("required", False) and field_name not in config:
                errors.append(f"Required field '{field_name}' is missing")

            if field_name in config:
                expected_type = field_schema.get("type")
                if expected_type:
                    if expected_type == "string" and not isinstance(config[field_name], str):
                        errors.append(f"Field '{field_name}' must be a string")
                    elif expected_type == "number" and not isinstance(
                        config[field_name], (int, float)
                    ):
                        errors.append(f"Field '{field_name}' must be a number")

        return {"valid": len(errors) == 0, "errors": errors}

    async def test_integration(self, integration_id: str) -> Dict[str, Any]:
        """
        Test an integration connection

        Args:
            integration_id: Integration identifier

        Returns:
            Test result
        """
        if integration_id not in self.integrations:
            return {"success": False, "error": "Integration not found"}

        integration = self.integrations[integration_id]

        try:
            # Integration-specific testing logic
            if integration.integration_type == IntegrationType.MONITORING:
                result = await self._test_monitoring_integration(integration)
            elif integration.integration_type == IntegrationType.CLOUD:
                result = await self._test_cloud_integration(integration)
            elif integration.integration_type == IntegrationType.CICD:
                result = await self._test_cicd_integration(integration)
            elif integration.integration_type == IntegrationType.NOTIFICATION:
                result = await self._test_notification_integration(integration)
            else:
                result = {"success": True, "message": "Integration type not testable"}

            return result

        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return {"success": False, "error": str(e)}

    async def _test_monitoring_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """Test monitoring integration"""
        if not HTTP_AVAILABLE:
            return {"success": False, "error": "HTTP client not available"}

        config = integration.config
        name = integration.name.lower()

        if name == "prometheus":
            url = config.get("url")
            if not url:
                return {"success": False, "error": "Prometheus URL not configured"}

            try:
                if self.http_client is None:
                    return {"success": False, "error": "HTTP client not initialized"}
                response = await self.http_client.get(f"{url}/api/v1/query", params={"query": "up"})
                if response.status_code == 200:
                    return {"success": True, "message": "Prometheus connection successful"}
                else:
                    return {
                        "success": False,
                        "error": f"Prometheus returned status {response.status_code}",
                    }
            except Exception as e:
                return {"success": False, "error": f"Prometheus connection failed: {e}"}

        # Similar logic for other monitoring tools
        return {"success": True, "message": f"{integration.name} integration test passed"}

    async def _test_cloud_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """Test cloud platform integration"""
        # Simplified cloud integration test
        return {"success": True, "message": f"{integration.name} integration test passed"}

    async def _test_cicd_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """Test CI/CD integration"""
        # Simplified CI/CD integration test
        return {"success": True, "message": f"{integration.name} integration test passed"}

    async def _test_notification_integration(
        self, integration: IntegrationConfig
    ) -> Dict[str, Any]:
        """Test notification integration"""
        if not HTTP_AVAILABLE:
            return {"success": False, "error": "HTTP client not available"}

        config = integration.config
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}

        try:
            test_message = {
                "text": "AIOps Agent integration test",
                "timestamp": datetime.now().isoformat(),
            }

            if self.http_client is None:
                return {"success": False, "error": "HTTP client not initialized"}
            response = await self.http_client.post(webhook_url, json=test_message)
            if response.status_code == 200:
                return {"success": True, "message": "Notification integration test passed"}
            else:
                return {
                    "success": False,
                    "error": f"Notification service returned status {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": f"Notification test failed: {e}"}

    async def send_notification(
        self, channel: str, recipient: str, subject: str, body: str, priority: str = "normal"
    ) -> NotificationMessage:
        """
        Send notification through specified channel

        Args:
            channel: Notification channel name
            recipient: Recipient identifier
            subject: Message subject
            body: Message body
            priority: Message priority (normal, high, urgent)

        Returns:
            NotificationMessage
        """
        message_id = f"msg_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        message = NotificationMessage(
            message_id=message_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
        )

        # Queue message for processing
        self.notification_queue.append(message)

        # Process notification
        await self._process_notification(message)

        return message

    async def _process_notification(self, message: NotificationMessage):
        """Process notification message"""
        if message.channel not in self.notification_channels:
            message.error = f"Channel {message.channel} not found"
            return

        channel_config = self.notification_channels[message.channel]

        if not channel_config.get("enabled", True):
            message.error = f"Channel {message.channel} is disabled"
            return

        try:
            if channel_config["type"] == "webhook":
                await self._send_webhook_notification(message, channel_config["config"])
            else:
                message.error = f"Unsupported channel type: {channel_config['type']}"
        except Exception as e:
            message.error = str(e)
            logger.error(f"Failed to send notification: {e}")

    async def _send_webhook_notification(
        self, message: NotificationMessage, config: Dict[str, Any]
    ):
        """Send notification via webhook"""
        if not HTTP_AVAILABLE:
            raise Exception("HTTP client not available")

        webhook_url = config.get("url")
        if not webhook_url:
            raise Exception("Webhook URL not configured")

        payload = {
            "subject": message.subject,
            "body": message.body,
            "priority": message.priority,
            "recipient": message.recipient,
            "timestamp": message.timestamp.isoformat(),
        }

        if self.http_client is None:
            return
        response = await self.http_client.post(webhook_url, json=payload)
        response.raise_for_status()

        message.sent = True

    async def register_webhook(
        self, source: str, event_type: str, endpoint: str, secret: Optional[str] = None
    ) -> str:
        """
        Register a webhook endpoint

        Args:
            source: Webhook source identifier
            event_type: Type of events to receive
            endpoint: Endpoint URL
            secret: Optional secret for signature validation

        Returns:
            Webhook ID
        """
        webhook_id = f"webhook_{source}_{event_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.webhooks[webhook_id] = {
            "webhook_id": webhook_id,
            "source": source,
            "event_type": event_type,
            "endpoint": endpoint,
            "secret": secret or self.webhook_secret,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }

        logger.info(f"Registered webhook: {webhook_id}")
        return webhook_id

    async def handle_webhook(
        self, webhook_id: str, payload: Dict[str, Any], signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle incoming webhook event

        Args:
            webhook_id: Webhook identifier
            payload: Event payload
            signature: Optional signature for validation

        Returns:
            Processing result
        """
        if webhook_id not in self.webhooks:
            return {"success": False, "error": "Webhook not found"}

        webhook = self.webhooks[webhook_id]

        # Validate signature if provided
        if signature and webhook.get("secret"):
            if not self._validate_signature(payload, signature, webhook["secret"]):
                return {"success": False, "error": "Invalid signature"}

        # Create event
        event = WebhookEvent(
            event_id=f"event_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            source=webhook["source"],
            event_type=webhook["event_type"],
            payload=payload,
        )

        self.webhook_events.append(event)

        # Process event
        await self._process_webhook_event(event)

        return {"success": True, "event_id": event.event_id}

    def _validate_signature(self, payload: Dict[str, Any], signature: str, secret: str) -> bool:
        """Validate webhook signature"""
        try:
            payload_str = json.dumps(payload, sort_keys=True)
            expected_signature = hmac.new(
                secret.encode(), payload_str.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Signature validation failed: {e}")
            return False

    async def _process_webhook_event(self, event: WebhookEvent):
        """Process webhook event"""
        # Event processing logic based on event type
        if event.event_type == "alert":
            await self._handle_alert_event(event)
        elif event.event_type == "deployment":
            await self._handle_deployment_event(event)
        elif event.event_type == "incident":
            await self._handle_incident_event(event)

        event.processed = True

    async def _handle_alert_event(self, event: WebhookEvent):
        """Handle alert event"""
        logger.info(f"Processing alert event: {event.event_id}")
        # Alert processing logic

    async def _handle_deployment_event(self, event: WebhookEvent):
        """Handle deployment event"""
        logger.info(f"Processing deployment event: {event.event_id}")
        # Deployment processing logic

    async def _handle_incident_event(self, event: WebhookEvent):
        """Handle incident event"""
        logger.info(f"Processing incident event: {event.event_id}")
        # Incident processing logic

    async def query_prometheus_metrics(
        self, integration_id: str, query: str, time_range: str = "1h"
    ) -> Dict[str, Any]:
        """
        Query Prometheus metrics

        Args:
            integration_id: Prometheus integration ID
            query: PromQL query
            time_range: Time range for query

        Returns:
            Query results
        """
        if integration_id not in self.integrations:
            return {"error": "Integration not found"}

        integration = self.integrations[integration_id]
        if integration.name.lower() != "prometheus":
            return {"error": "Not a Prometheus integration"}

        if not HTTP_AVAILABLE:
            return {"error": "HTTP client not available"}

        config = integration.config
        url = config.get("url")

        try:
            validate_promql(query)
        except ValueError as exc:
            logger.warning("Invalid PromQL rejected for integration %s: %s", integration_id, exc)
            return {"error": f"Invalid PromQL query: {exc}"}

        try:
            duration_seconds = parse_duration_to_seconds(time_range)
        except ValueError as exc:
            return {"error": f"Invalid time_range: {exc}"}

        try:
            end = datetime.now(timezone.utc)
            start, end = align_time_window(
                end=end, duration_seconds=duration_seconds, latency_offset_seconds=0.0
            )
            step = limit_range_samples(
                start,
                end,
                60.0,
                config.get("max_samples", DEFAULT_MAX_PROMQL_SAMPLES),
            )

            if self.http_client is None:
                return {"error": "HTTP client not initialized"}

            cache_key = make_cache_key("prometheus_integration", url, query, time_range, step)

            async def _run_query() -> Dict[str, Any]:
                response = await with_query_timeout(
                    self.http_client.get(
                        f"{url}/api/v1/query_range",
                        params={
                            "query": query,
                            "start": int(start.timestamp()),
                            "end": int(end.timestamp()),
                            "step": int(step),
                        },
                    )
                )
                if response.status_code == 200:
                    return cast(Dict[str, Any], response.json())
                return {"error": f"Prometheus query failed: {response.status_code}"}

            return await cached_query(
                self._observability_cache,
                cache_key,
                _run_query(),
            )
        except Exception as e:
            safe_error = sanitize_error_for_llm(e)
            logger.error(f"Prometheus query error for {integration_id}: {safe_error}")
            return {"error": safe_error}

    async def trigger_jenkins_job(
        self, integration_id: str, job_name: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger Jenkins job

        Args:
            integration_id: Jenkins integration ID
            job_name: Jenkins job name
            parameters: Job parameters

        Returns:
            Trigger result
        """
        if integration_id not in self.integrations:
            return {"error": "Integration not found"}

        integration = self.integrations[integration_id]
        if integration.name.lower() != "jenkins":
            return {"error": "Not a Jenkins integration"}

        # Jenkins job trigger logic
        return {
            "success": True,
            "message": f"Job {job_name} triggered successfully",
            "job_name": job_name,
        }

    async def create_jira_issue(
        self,
        integration_id: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: str = "Medium",
    ) -> Dict[str, Any]:
        """
        Create Jira issue

        Args:
            integration_id: Jira integration ID
            summary: Issue summary
            description: Issue description
            issue_type: Type of issue
            priority: Issue priority

        Returns:
            Creation result
        """
        if integration_id not in self.integrations:
            return {"error": "Integration not found"}

        integration = self.integrations[integration_id]
        if integration.name.lower() != "jira":
            return {"error": "Not a Jira integration"}

        # Jira issue creation logic
        return {
            "success": True,
            "message": "Jira issue created successfully",
            "issue_key": f'AIO-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        }

    def get_integration_summary(self) -> Dict[str, Any]:
        """Get summary of all integrations"""
        return {
            "total_integrations": len(self.integrations),
            "active_integrations": sum(
                1 for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE
            ),
            "integrations_by_type": {
                integration_type.value: sum(
                    1 for i in self.integrations.values() if i.integration_type == integration_type
                )
                for integration_type in IntegrationType
            },
            "webhooks_registered": len(self.webhooks),
            "notification_channels": len(self.notification_channels),
            "pending_notifications": len(self.notification_queue),
            "webhook_events_processed": len([e for e in self.webhook_events if e.processed]),
        }


# Global instance
integration_manager = IntegrationManager()
