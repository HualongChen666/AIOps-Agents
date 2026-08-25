# -*- coding: utf-8 -*-
"""
Integration Ecosystem Module
集成生态模块

Provides comprehensive integration capabilities:
- Standardized integration with mainstream monitoring tools (Prometheus, Grafana, ELK)
- Cloud platform integration (AWS, Azure, GCP)
- CI/CD tool integration (Jenkins, GitLab CI, GitHub Actions)
- ITSM tool integration (ServiceNow, Jira)
- Notification channel integration (Slack, Teams, DingTalk, WeCom)
- Standardized Webhook and API integration interfaces

P2 Enhancement:
- 50+ integrations support
- Connector marketplace
- Plugin SDK for custom integrations
"""

import asyncio
import hmac
import json
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, cast

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

# Optional integration library imports
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("Requests library not available")

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("Aiohttp library not available")


class IntegrationType(Enum):
    """集成类型"""

    MONITORING = "monitoring"
    CLOUD = "cloud"
    CICD = "cicd"
    ITSM = "itsm"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"


class IntegrationStatus(Enum):
    """集成状态"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class NotificationChannel(Enum):
    """通知渠道"""

    SLACK = "slack"
    TEAMS = "teams"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


@dataclass
class IntegrationConfig:
    """集成配置"""

    id: str
    name: str
    type: IntegrationType
    provider: str
    configuration: Dict[str, Any]
    status: IntegrationStatus
    credentials: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationEvent:
    """集成事件"""

    id: str
    integration_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    status: str
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class WebhookConfig:
    """Webhook配置"""

    id: str
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    secret: Optional[str] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)


class IntegrationEcosystem:
    """集成生态模块"""

    def __init__(self):
        """初始化集成生态模块"""
        # 集成配置
        self.integrations: Dict[str, IntegrationConfig] = {}
        self.webhooks: Dict[str, WebhookConfig] = {}

        # 事件处理
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: deque = deque(maxlen=10000)

        # 重试策略
        self.retry_config = {"max_retries": 3, "backoff_factor": 2, "retry_after": 1}

        # 会话管理
        self.http_session = None
        self.aiohttp_session = None

        # 配置
        self.max_integrations = 100
        self.webhook_timeout = 30
        self.event_processing_interval = timedelta(seconds=5)

        # 可观测性查询缓存 / 安全层
        self._observability_cache = QueryCache()

    async def initialize(self):
        """初始化集成生态模块"""
        logger.info("Initializing Integration Ecosystem")

        # 初始化HTTP会话
        if REQUESTS_AVAILABLE:
            self.http_session = self._create_retry_session()
            logger.info("HTTP session with retry policy initialized")

        if AIOHTTP_AVAILABLE:
            self.aiohttp_session = aiohttp.ClientSession()
            logger.info("Aiohttp session initialized")

        # 启动事件处理循环
        asyncio.create_task(self._event_processing_loop())

        # 加载现有集成配置
        await self._load_existing_integrations()

        logger.info("Integration Ecosystem initialized successfully")

    def _create_retry_session(self) -> requests.Session:
        """创建带重试策略的HTTP会话"""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.retry_config["max_retries"],
            backoff_factor=self.retry_config["backoff_factor"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    async def _load_existing_integrations(self):
        """加载现有集成配置（从 integrations.json 文件或环境变量指定路径）。"""
        logger.info("Loading existing integration configurations")
        try:
            import os

            path = os.getenv("AIOPS_INTEGRATIONS_PATH", "integrations.json")
            if not os.path.exists(path):
                logger.info(f"No integration configuration file found at {path}")
                return

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error(f"Failed to load integration configuration from {path}: {exc}")
                return

            for item in data:
                try:
                    config = IntegrationConfig(
                        id=item.get("id") or f"integration_{uuid.uuid4().hex[:12]}",
                        name=item["name"],
                        type=IntegrationType(item["type"]),
                        provider=item["provider"],
                        configuration=item.get("configuration", {}),
                        status=IntegrationStatus(item.get("status", "pending")),
                        credentials=item.get("credentials", {}),
                        metadata=item.get("metadata", {}),
                    )
                    self.integrations[config.id] = config
                except Exception as exc:
                    logger.warning(f"Failed to load integration entry: {exc}")

            logger.info(f"Loaded {len(self.integrations)} integrations from {path}")
        except Exception as exc:
            logger.warning(f"Failed to load existing integrations: {exc}")

    async def register_integration(
        self,
        name: str,
        integration_type: IntegrationType,
        provider: str,
        configuration: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
    ) -> IntegrationConfig:
        """注册集成"""
        logger.info(f"Registering integration: {name} ({provider})")

        # 检查集成数量限制
        if len(self.integrations) >= self.max_integrations:
            raise ValueError(f"Maximum integration limit ({self.max_integrations}) reached")

        # 生成集成ID
        integration_id = f"integration_{uuid.uuid4().hex[:12]}"

        # 创建集成配置
        integration = IntegrationConfig(
            id=integration_id,
            name=name,
            type=integration_type,
            provider=provider,
            configuration=configuration,
            status=IntegrationStatus.PENDING,
            credentials=credentials or {},
        )

        # 验证配置
        validation_result = await self._validate_integration(integration)
        if not validation_result["valid"]:
            raise ValueError(f"Integration validation failed: {validation_result['error']}")

        # 激活集成
        await self._activate_integration(integration)

        self.integrations[integration_id] = integration

        logger.info(f"Integration registered: {integration_id}")
        return integration

    async def _validate_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """验证集成配置"""
        try:
            # 根据集成类型进行验证
            if integration.type == IntegrationType.MONITORING:
                return await self._validate_monitoring_integration(integration)
            elif integration.type == IntegrationType.CLOUD:
                return await self._validate_cloud_integration(integration)
            elif integration.type == IntegrationType.CICD:
                return await self._validate_cicd_integration(integration)
            elif integration.type == IntegrationType.NOTIFICATION:
                return await self._validate_notification_integration(integration)
            else:
                return {"valid": True}

        except Exception as e:
            logger.error(f"Integration validation failed: {e}")
            return {"valid": False, "error": str(e)}

    async def _validate_monitoring_integration(
        self, integration: IntegrationConfig
    ) -> Dict[str, Any]:
        """验证监控工具集成"""
        config = integration.configuration
        provider = integration.provider

        if provider == "prometheus":
            # 验证Prometheus配置
            required_fields = ["url", "port"]
            for required_field in required_fields:
                if required_field not in config:
                    return {"valid": False, "error": f"Missing required field: {required_field}"}

            # 尝试连接
            try:
                if REQUESTS_AVAILABLE and self.http_session:
                    test_url = f"{config['url']}:{config.get('port', 9090)}/api/v1/status"
                    response = self.http_session.get(test_url, timeout=5)
                    if response.status_code == 200:
                        return {"valid": True}
            except Exception as e:
                return {"valid": False, "error": f"Connection test failed: {e}"}

        return {"valid": True}

    async def _validate_cloud_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """验证云平台集成"""
        provider = integration.provider

        if provider == "aws":
            required_fields = ["access_key", "secret_key", "region"]
            for required_field in required_fields:
                if required_field not in integration.credentials:
                    return {"valid": False, "error": f"Missing credential: {required_field}"}

        return {"valid": True}

    async def _validate_cicd_integration(self, integration: IntegrationConfig) -> Dict[str, Any]:
        """验证CI/CD工具集成"""
        provider = integration.provider

        if provider == "github":
            required_fields = ["repo", "token"]
            for required_field in required_fields:
                if required_field not in integration.credentials:
                    return {"valid": False, "error": f"Missing credential: {required_field}"}

        return {"valid": True}

    async def _validate_notification_integration(
        self, integration: IntegrationConfig
    ) -> Dict[str, Any]:
        """验证通知渠道集成"""
        config = integration.configuration
        provider = integration.provider

        if provider == "slack":
            required_fields = ["webhook_url", "channel"]
            for required_field in required_fields:
                if required_field not in config:
                    return {"valid": False, "error": f"Missing required field: {required_field}"}

        return {"valid": True}

    async def _activate_integration(self, integration: IntegrationConfig):
        """激活集成"""
        logger.info(f"Activating integration: {integration.id}")

        # 根据集成类型进行激活
        if integration.type == IntegrationType.MONITORING:
            await self._activate_monitoring_integration(integration)
        elif integration.type == IntegrationType.CLOUD:
            await self._activate_cloud_integration(integration)
        elif integration.type == IntegrationType.CICD:
            await self._activate_cicd_integration(integration)
        elif integration.type == IntegrationType.NOTIFICATION:
            await self._activate_notification_integration(integration)

        integration.status = IntegrationStatus.ACTIVE
        integration.updated_at = datetime.now()

    async def _activate_monitoring_integration(self, integration: IntegrationConfig):
        """激活监控工具集成"""
        provider = integration.provider

        if provider == "prometheus":
            # 配置Prometheus查询接口
            pass
        elif provider == "grafana":
            # 配置Grafana API
            pass
        elif provider == "elk":
            # 配置ELK Stack API
            pass

    async def _activate_cloud_integration(self, integration: IntegrationConfig):
        """激活云平台集成"""
        provider = integration.provider

        if provider == "aws":
            # 配置AWS SDK
            pass
        elif provider == "azure":
            # 配置Azure SDK
            pass
        elif provider == "gcp":
            # 配置GCP SDK
            pass

    async def _activate_cicd_integration(self, integration: IntegrationConfig):
        """激活CI/CD工具集成"""
        provider = integration.provider

        if provider == "jenkins":
            # 配置Jenkins API
            pass
        elif provider == "gitlab":
            # 配置GitLab CI API
            pass
        elif provider == "github":
            # 配置GitHub Actions API
            pass

    async def _activate_notification_integration(self, integration: IntegrationConfig):
        """激活通知渠道集成"""
        provider = integration.provider

        if provider == "slack":
            # 配置Slack Webhook
            await self.register_webhook(
                url=integration.configuration["webhook_url"],
                secret=integration.credentials.get("signing_secret"),
                events=["alert", "incident", "recovery"],
            )
        elif provider == "teams":
            # 配置Teams Webhook
            await self.register_webhook(
                url=integration.configuration["webhook_url"], events=["alert", "incident"]
            )

    async def send_notification(
        self, channel: NotificationChannel, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """发送通知"""
        logger.info(f"Sending notification via {channel.value}")

        try:
            if channel == NotificationChannel.SLACK:
                return await self._send_slack_notification(message, metadata or {})
            elif channel == NotificationChannel.TEAMS:
                return await self._send_teams_notification(message, metadata or {})
            elif channel == NotificationChannel.DINGTALK:
                return await self._send_dingtalk_notification(message, metadata or {})
            elif channel == NotificationChannel.WECOM:
                return await self._send_wecom_notification(message, metadata or {})
            elif channel == NotificationChannel.EMAIL:
                return await self._send_email_notification(message, metadata or {})
            else:
                logger.warning(f"Notification channel {channel.value} not supported")
                return False

        except Exception as e:
            logger.error(f"Failed to send notification via {channel.value}: {e}")
            return False

    async def _send_slack_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """发送Slack通知"""
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests library not available for Slack notification")
            return False

        # 查找Slack集成配置
        slack_integration = None
        for integration in self.integrations.values():
            if integration.type == IntegrationType.NOTIFICATION and integration.provider == "slack":
                slack_integration = integration
                break

        if not slack_integration:
            logger.error("Slack integration not found")
            return False

        webhook_url = slack_integration.configuration.get("webhook_url")
        channel = slack_integration.configuration.get("channel", "#general")

        payload = {
            "text": message,
            "channel": channel,
            "username": "AIOps Agent",
            "icon_emoji": ":robot_face:",
            "attachments": [],
        }

        if metadata:
            payload["attachments"].append(
                {
                    "color": "danger" if "error" in message.lower() else "good",
                    "fields": [
                        {"title": k, "value": str(v), "short": False} for k, v in metadata.items()
                    ],
                }
            )

        try:
            if not self.http_session:
                logger.error("HTTP session not available")
                return False
            response = self.http_session.post(webhook_url, json=payload, timeout=10)
            return int(response.status_code) == 200
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return False

    async def _send_teams_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """发送Teams通知"""
        return await self._post_webhook_notification("teams", message, metadata)

    async def _send_dingtalk_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """发送钉钉通知"""
        return await self._post_webhook_notification("dingtalk", message, metadata)

    async def _send_wecom_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """发送企业微信通知"""
        return await self._post_webhook_notification("wecom", message, metadata)

    async def _send_email_notification(self, message: str, metadata: Dict[str, Any]) -> bool:
        """发送邮件通知（使用 smtplib 发送配置 SMTP）。"""
        integration = self._find_notification_integration("email")
        if not integration:
            logger.error("Email integration not found")
            return False

        smtp_config = integration.configuration
        smtp_host = smtp_config.get("smtp_host")
        smtp_port = smtp_config.get("smtp_port", 587)
        sender = smtp_config.get("sender")
        recipient = metadata.get("to") or smtp_config.get("default_recipient")
        password = integration.credentials.get("password")

        if not smtp_host or not sender or not recipient:
            logger.error("Email integration missing host, sender or recipient")
            return False

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = metadata.get("subject", "AIOps Notification")
            msg.attach(MIMEText(message, "plain", "utf-8"))

            def _send():
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    if password:
                        server.login(sender, password)
                    server.sendmail(sender, [recipient], msg.as_string())

            await asyncio.get_event_loop().run_in_executor(None, _send)
            logger.info(f"Email notification sent to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    async def _post_webhook_notification(
        self, provider: str, message: str, metadata: Dict[str, Any]
    ) -> bool:
        """Generic webhook POST for notification providers."""
        integration = self._find_notification_integration(provider)
        if not integration:
            logger.error(f"{provider} integration not found")
            return False

        webhook_url = integration.configuration.get("webhook_url")
        if not webhook_url:
            logger.error(f"{provider} integration missing webhook_url")
            return False

        secret = integration.credentials.get("secret")
        payload: Dict[str, Any] = {"text": message, "provider": provider}
        if metadata:
            payload.update(metadata)

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if secret:
            timestamp = str(datetime.now(timezone.utc).timestamp())
            signature = hmac.new(
                secret.encode(),
                f"{timestamp}\n{secret}".encode(),
                "sha256",
            ).hexdigest()
            headers["X-Timestamp"] = timestamp
            headers["X-Signature"] = signature

        try:
            if self.http_session is None:
                logger.error("HTTP session not available")
                return False

            http_session = self.http_session
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: http_session.post(webhook_url, json=payload, headers=headers, timeout=10),
            )
            return int(response.status_code) in (200, 201, 204)
        except Exception as e:
            logger.error(f"{provider} notification failed: {e}")
            return False

    def _find_notification_integration(self, provider: str) -> Optional[IntegrationConfig]:
        """查找指定 provider 的通知集成配置。"""
        for integration in self.integrations.values():
            if (
                integration.type == IntegrationType.NOTIFICATION
                and integration.provider == provider
            ):
                return integration
        return None

    async def register_webhook(
        self, url: str, secret: Optional[str] = None, events: Optional[List[str]] = None
    ) -> WebhookConfig:
        """注册Webhook"""
        logger.info(f"Registering webhook: {url}")

        webhook_id = f"webhook_{uuid.uuid4().hex[:12]}"

        webhook = WebhookConfig(id=webhook_id, url=url, secret=secret, events=events or [])

        self.webhooks[webhook_id] = webhook

        logger.info(f"Webhook registered: {webhook_id}")
        return webhook

    async def trigger_webhook(self, webhook_id: str, event_data: Dict[str, Any]) -> bool:
        """触发Webhook"""
        if webhook_id not in self.webhooks:
            logger.error(f"Webhook {webhook_id} not found")
            return False

        webhook = self.webhooks[webhook_id]

        # 验证签名
        if webhook.secret:
            if "signature" not in event_data:
                logger.warning("Webhook signature missing")
                return False

            expected_signature = self._calculate_signature(event_data, webhook.secret)
            if not hmac.compare_digest(expected_signature, event_data["signature"]):
                logger.warning("Webhook signature mismatch")
                return False

        # 发送请求
        try:
            if REQUESTS_AVAILABLE and self.http_session:
                headers = webhook.headers.copy()
                headers["Content-Type"] = "application/json"

                response = self.http_session.request(
                    method=webhook.method,
                    url=webhook.url,
                    headers=headers,
                    json=event_data,
                    timeout=self.webhook_timeout,
                )

                return response.status_code in [200, 201, 202, 204]
            elif AIOHTTP_AVAILABLE and self.aiohttp_session:
                headers = webhook.headers.copy()
                headers["Content-Type"] = "application/json"

                async with self.aiohttp_session.post(
                    url=webhook.url, headers=headers, json=event_data, timeout=self.webhook_timeout
                ) as response:
                    return response.status in [200, 201, 202, 204]
            else:
                logger.warning("No HTTP client available for webhook")
                return False

        except Exception as e:
            logger.error(f"Webhook trigger failed: {e}")
            return False

    def _calculate_signature(self, data: Dict[str, Any], secret: str) -> str:
        """计算签名"""
        import hashlib
        import hmac

        # The signature itself must not be part of the signed payload.
        payload_data = {k: v for k, v in data.items() if k != "signature"}
        payload = json.dumps(payload_data, sort_keys=True)
        signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

        return signature

    async def publish_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """发布集成事件"""
        logger.info(f"Publishing event: {event_type}")

        # 创建事件
        event = IntegrationEvent(
            id=str(uuid.uuid4()),
            integration_id="system",
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now(),
            status="pending",
        )

        # 加入事件队列
        self.event_queue.append(event)

        return True

    async def _event_processing_loop(self):
        """事件处理循环"""
        while True:
            try:
                await asyncio.sleep(self.event_processing_interval.total_seconds())

                while self.event_queue:
                    event = self.event_queue.popleft()
                    await self._process_event(event)

            except Exception as e:
                logger.error(f"Event processing loop error: {e}")

    async def _process_event(self, event: IntegrationEvent):
        """处理事件"""
        logger.info(f"Processing event: {event.event_type}")

        # 查找相关的事件处理器
        handlers = self.event_handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")

        # 更新事件状态
        event.status = "processed"

    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event type: {event_type}")

    async def query_prometheus_metrics(
        self, query: str, integration_id: str, time_range: str = "1h"
    ) -> Optional[Dict[str, Any]]:
        """查询Prometheus指标，支持 PromQL 校验、时间窗口对齐和查询缓存"""
        prometheus_integration = self.integrations.get(integration_id)

        if not prometheus_integration or prometheus_integration.provider != "prometheus":
            logger.error(f"Prometheus integration {integration_id} not found")
            return None

        config = prometheus_integration.configuration
        base_url = f"{config['url']}:{config.get('port', 9090)}"

        try:
            validate_promql(query)
        except ValueError as exc:
            logger.warning("Invalid PromQL rejected for integration %s: %s", integration_id, exc)
            return None

        try:
            duration_seconds = parse_duration_to_seconds(time_range)
        except ValueError as exc:
            logger.warning(
                "Invalid time_range rejected for integration %s: %s", integration_id, exc
            )
            return None

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

            cache_key = make_cache_key("ecosystem_prometheus", base_url, query, time_range, step)

            if not REQUESTS_AVAILABLE or not self.http_session:
                logger.warning("HTTP session not available")
                return None

            http_session = self.http_session
            if http_session is None:
                return None

            async def _run_query() -> Dict[str, Any]:
                def _sync_query():
                    return http_session.get(
                        f"{base_url}/api/v1/query_range",
                        params={
                            "query": query,
                            "start": int(start.timestamp()),
                            "end": int(end.timestamp()),
                            "step": int(step),
                            "timeout": "30s",
                        },
                        timeout=30,
                    )

                response = await asyncio.get_running_loop().run_in_executor(None, _sync_query)
                if response.status_code == 200:
                    return cast(Dict[str, Any], response.json())
                logger.error(f"Prometheus query failed: {response.status_code}")
                return {"error": f"Prometheus query failed: {response.status_code}"}

            return cast(
                Dict[str, Any] | None,
                await cached_query(
                    self._observability_cache,
                    cache_key,
                    with_query_timeout(_run_query()),
                ),
            )

        except Exception as e:
            safe_error = sanitize_error_for_llm(e)
            logger.error(f"Prometheus query failed for {integration_id}: {safe_error}")
            return {"error": safe_error}

    async def trigger_jenkins_build(
        self, job_name: str, integration_id: str, parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """触发Jenkins构建"""
        jenkins_integration = self.integrations.get(integration_id)

        if not jenkins_integration or jenkins_integration.provider != "jenkins":
            logger.error(f"Jenkins integration {integration_id} not found")
            return False

        config = jenkins_integration.configuration
        token = jenkins_integration.credentials.get("api_token")

        build_url = f"{config['url']}/job/{job_name}/buildWithParameters"

        try:
            if REQUESTS_AVAILABLE and self.http_session:
                headers = {"Authorization": f"Bearer {token}"}
                response = self.http_session.post(
                    build_url, json=parameters or {}, headers=headers, timeout=30
                )

                return int(response.status_code) == 201
            else:
                logger.warning("HTTP session not available")
                return False

        except Exception as e:
            logger.error(f"Jenkins build trigger failed: {e}")
            return False

    async def create_jira_ticket(
        self,
        summary: str,
        description: str,
        integration_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """创建Jira工单"""
        jira_integration = self.integrations.get(integration_id)

        if not jira_integration or jira_integration.provider != "jira":
            logger.error(f"Jira integration {integration_id} not found")
            return None

        config = jira_integration.configuration
        username = jira_integration.credentials.get("username")
        api_token = jira_integration.credentials.get("api_token")

        api_url = f"{config['url']}/rest/api/2/issue/"

        payload = {
            "fields": {
                "project": {"key": config.get("project_key", "OPS")},
                "summary": summary,
                "description": description,
                "issuetype": {"name": config.get("issue_type", "Bug")},
            }
        }

        try:
            if REQUESTS_AVAILABLE and self.http_session:
                response = self.http_session.post(
                    api_url,
                    auth=(username, api_token),
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )

                if response.status_code == 201:
                    return cast(Optional[str], response.json().get("key"))
                else:
                    logger.error(f"Jira ticket creation failed: {response.status_code}")
                    return None
            else:
                logger.warning("HTTP session not available")
                return None

        except Exception as e:
            logger.error(f"Jira ticket creation failed: {e}")
            return None

    async def get_integration_status(self, integration_id: str) -> Optional[IntegrationConfig]:
        """获取集成状态"""
        return self.integrations.get(integration_id)

    async def list_integrations(
        self, integration_type: Optional[IntegrationType] = None
    ) -> List[IntegrationConfig]:
        """列出集成"""
        integrations = list(self.integrations.values())

        if integration_type:
            integrations = [i for i in integrations if i.type == integration_type]

        return integrations

    async def disable_integration(self, integration_id: str) -> bool:
        """禁用集成"""
        if integration_id not in self.integrations:
            return False

        self.integrations[integration_id].status = IntegrationStatus.INACTIVE
        self.integrations[integration_id].updated_at = datetime.now()

        return True

    async def enable_integration(self, integration_id: str) -> bool:
        """启用集成"""
        if integration_id not in self.integrations:
            return False

        integration = self.integrations[integration_id]

        # 重新激活集成
        await self._activate_integration(integration)

        return True

    async def remove_integration(self, integration_id: str) -> bool:
        """移除集成"""
        if integration_id not in self.integrations:
            return False

        # 清理集成
        await self._cleanup_integration(integration_id)

        del self.integrations[integration_id]

        return True

    async def _cleanup_integration(self, integration_id: str):
        """清理集成相关资源（Webhook、事件处理器等）。"""
        integration = self.integrations.get(integration_id)
        if not integration:
            return

        # 移除与该集成 URL 关联的 webhook
        url = integration.configuration.get("webhook_url") or integration.configuration.get("url")
        if url:
            self.webhooks = {wid: wh for wid, wh in self.webhooks.items() if wh.url != url}

        # 注销该集成注册的事件处理器
        self.event_handlers.pop(integration_id, None)
        logger.info(f"Integration {integration_id} resources cleaned up")

    async def get_integration_statistics(self) -> Dict[str, Any]:
        """获取集成统计信息"""
        return {
            "total_integrations": len(self.integrations),
            "active_integrations": sum(
                1 for i in self.integrations.values() if i.status == IntegrationStatus.ACTIVE
            ),
            "by_type": {
                itype.value: sum(1 for i in self.integrations.values() if i.type == itype)
                for itype in IntegrationType
            },
            "total_webhooks": len(self.webhooks),
            "event_queue_size": len(self.event_queue),
            "registered_handlers": sum(len(handlers) for handlers in self.event_handlers.values()),
        }


# 全局实例
INTEGRATION_ECOSYSTEM = IntegrationEcosystem()


# ============================================================
# P2 Enhancement: Extended Integration Registry (50+ Integrations)
# ============================================================
class ExtendedIntegrationRegistry:
    """
    P2 Enhanced integration registry with 50+ supported integrations
    """

    def __init__(self):
        self.integration_templates = self._initialize_integration_templates()

    def _initialize_integration_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize 50+ integration templates"""
        return {
            # Monitoring Tools (10)
            "prometheus": {
                "name": "Prometheus",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Open-source monitoring and alerting toolkit",
                "required_fields": ["url", "port"],
                "optional_fields": ["auth_token", "tls_config"],
                "icon": "prometheus",
            },
            "grafana": {
                "name": "Grafana",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Open-source analytics and visualization platform",
                "required_fields": ["url", "api_key"],
                "icon": "grafana",
            },
            "elasticsearch": {
                "name": "Elasticsearch",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Distributed search and analytics engine",
                "required_fields": ["url", "index"],
                "icon": "elasticsearch",
            },
            "kibana": {
                "name": "Kibana",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Data visualization dashboard for Elasticsearch",
                "required_fields": ["url"],
                "icon": "kibana",
            },
            "datadog": {
                "name": "Datadog",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Cloud-based monitoring and analytics platform",
                "required_fields": ["api_key", "app_key"],
                "icon": "datadog",
            },
            "new_relic": {
                "name": "New Relic",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Application performance monitoring",
                "required_fields": ["api_key", "account_id"],
                "icon": "newrelic",
            },
            "splunk": {
                "name": "Splunk",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Data analysis and monitoring platform",
                "required_fields": ["url", "token"],
                "icon": "splunk",
            },
            "zabbix": {
                "name": "Zabbix",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Enterprise-class distributed monitoring solution",
                "required_fields": ["url", "username", "password"],
                "icon": "zabbix",
            },
            "nagios": {
                "name": "Nagios",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "IT infrastructure monitoring system",
                "required_fields": ["url", "api_token"],
                "icon": "nagios",
            },
            "appdynamics": {
                "name": "AppDynamics",
                "type": IntegrationType.MONITORING,
                "category": "monitoring",
                "description": "Application performance management",
                "required_fields": ["url", "account_name", "api_key"],
                "icon": "appdynamics",
            },
            # Cloud Platforms (10)
            "aws": {
                "name": "AWS",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Amazon Web Services cloud platform",
                "required_fields": ["access_key", "secret_key", "region"],
                "icon": "aws",
            },
            "azure": {
                "name": "Azure",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Microsoft Azure cloud platform",
                "required_fields": ["subscription_id", "tenant_id", "client_id", "client_secret"],
                "icon": "azure",
            },
            "gcp": {
                "name": "GCP",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Google Cloud Platform",
                "required_fields": ["project_id", "service_account_key"],
                "icon": "gcp",
            },
            "alibaba_cloud": {
                "name": "Alibaba Cloud",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Alibaba Cloud computing platform",
                "required_fields": ["access_key", "secret_key", "region"],
                "icon": "alicloud",
            },
            "tencent_cloud": {
                "name": "Tencent Cloud",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Tencent Cloud platform",
                "required_fields": ["secret_id", "secret_key", "region"],
                "icon": "tencent",
            },
            "huawei_cloud": {
                "name": "Huawei Cloud",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Huawei Cloud platform",
                "required_fields": ["access_key", "secret_key", "region"],
                "icon": "huawei",
            },
            "digitalocean": {
                "name": "DigitalOcean",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Cloud computing platform for developers",
                "required_fields": ["api_token"],
                "icon": "digitalocean",
            },
            "linode": {
                "name": "Linode",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Cloud hosting provider",
                "required_fields": ["api_token"],
                "icon": "linode",
            },
            "heroku": {
                "name": "Heroku",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Cloud application platform",
                "required_fields": ["api_key"],
                "icon": "heroku",
            },
            "openstack": {
                "name": "OpenStack",
                "type": IntegrationType.CLOUD,
                "category": "cloud",
                "description": "Open-source cloud computing platform",
                "required_fields": ["auth_url", "username", "password", "project_name"],
                "icon": "openstack",
            },
            # CI/CD Tools (10)
            "jenkins": {
                "name": "Jenkins",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Open-source automation server",
                "required_fields": ["url", "username", "api_token"],
                "icon": "jenkins",
            },
            "gitlab": {
                "name": "GitLab",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "DevOps platform with CI/CD",
                "required_fields": ["url", "private_token"],
                "icon": "gitlab",
            },
            "github": {
                "name": "GitHub",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Version control and CI/CD platform",
                "required_fields": ["repo", "token"],
                "icon": "github",
            },
            "bitbucket": {
                "name": "Bitbucket",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Git-based code hosting and CI/CD",
                "required_fields": ["workspace", "username", "app_password"],
                "icon": "bitbucket",
            },
            "circleci": {
                "name": "CircleCI",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Continuous integration and delivery platform",
                "required_fields": ["project_slug", "api_token"],
                "icon": "circleci",
            },
            "travisci": {
                "name": "Travis CI",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Continuous integration service",
                "required_fields": ["repo_slug", "api_token"],
                "icon": "travisci",
            },
            "teamcity": {
                "name": "TeamCity",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Continuous integration server",
                "required_fields": ["url", "username", "password"],
                "icon": "teamcity",
            },
            "bamboo": {
                "name": "Bamboo",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Continuous integration and deployment",
                "required_fields": ["url", "username", "api_token"],
                "icon": "bamboo",
            },
            "drone": {
                "name": "Drone CI",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "Container-native continuous integration",
                "required_fields": ["url", "api_token"],
                "icon": "drone",
            },
            "argo": {
                "name": "Argo CD",
                "type": IntegrationType.CICD,
                "category": "cicd",
                "description": "GitOps continuous delivery tool",
                "required_fields": ["url", "auth_token"],
                "icon": "argo",
            },
            # ITSM Tools (10)
            "servicenow": {
                "name": "ServiceNow",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "IT service management platform",
                "required_fields": ["url", "username", "password"],
                "icon": "servicenow",
            },
            "jira": {
                "name": "Jira",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Issue tracking and project management",
                "required_fields": ["url", "username", "api_token"],
                "icon": "jira",
            },
            "zendesk": {
                "name": "Zendesk",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Customer service and support platform",
                "required_fields": ["url", "api_token"],
                "icon": "zendesk",
            },
            "freshdesk": {
                "name": "Freshdesk",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Customer support software",
                "required_fields": ["url", "api_key"],
                "icon": "freshdesk",
            },
            "pagerduty": {
                "name": "PagerDuty",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Incident management platform",
                "required_fields": ["api_key", "service_key"],
                "icon": "pagerduty",
            },
            "opsgenie": {
                "name": "Opsgenie",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Incident management and alerting",
                "required_fields": ["api_key"],
                "icon": "opsgenie",
            },
            "victorops": {
                "name": "VictorOps",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Incident management platform",
                "required_fields": ["api_key", "routing_key"],
                "icon": "victorops",
            },
            "xmatters": {
                "name": "xMatters",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Incident management and communication",
                "required_fields": ["url", "api_key"],
                "icon": "xmatters",
            },
            "statuspage": {
                "name": "Statuspage",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Status page and incident communication",
                "required_fields": ["page_id", "api_key"],
                "icon": "statuspage",
            },
            "otrs": {
                "name": "OTRS",
                "type": IntegrationType.ITSM,
                "category": "itsm",
                "description": "Open-source ticketing system",
                "required_fields": ["url", "username", "password"],
                "icon": "otrs",
            },
            # Notification Channels (10)
            "slack": {
                "name": "Slack",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Team communication platform",
                "required_fields": ["webhook_url"],
                "icon": "slack",
            },
            "teams": {
                "name": "Microsoft Teams",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Microsoft team collaboration platform",
                "required_fields": ["webhook_url"],
                "icon": "teams",
            },
            "dingtalk": {
                "name": "DingTalk",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Enterprise communication platform",
                "required_fields": ["webhook_url", "secret"],
                "icon": "dingtalk",
            },
            "wecom": {
                "name": "WeCom",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "WeChat Work enterprise communication",
                "required_fields": ["webhook_url"],
                "icon": "wecom",
            },
            "discord": {
                "name": "Discord",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Voice, video, and text communication",
                "required_fields": ["webhook_url"],
                "icon": "discord",
            },
            "telegram": {
                "name": "Telegram",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Cloud-based messaging service",
                "required_fields": ["bot_token", "chat_id"],
                "icon": "telegram",
            },
            "twilio": {
                "name": "Twilio",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "SMS and voice communication API",
                "required_fields": ["account_sid", "auth_token", "phone_number"],
                "icon": "twilio",
            },
            "sendgrid": {
                "name": "SendGrid",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Email delivery API",
                "required_fields": ["api_key"],
                "icon": "sendgrid",
            },
            "pushover": {
                "name": "Pushover",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Push notification service",
                "required_fields": ["user_key", "api_token"],
                "icon": "pushover",
            },
            "pushbullet": {
                "name": "Pushbullet",
                "type": IntegrationType.NOTIFICATION,
                "category": "notification",
                "description": "Push notification and file sharing",
                "required_fields": ["api_key"],
                "icon": "pushbullet",
            },
            # Additional Integrations (10)
            "kubernetes": {
                "name": "Kubernetes",
                "type": IntegrationType.CLOUD,
                "category": "container",
                "description": "Container orchestration platform",
                "required_fields": ["kubeconfig"],
                "icon": "kubernetes",
            },
            "docker": {
                "name": "Docker",
                "type": IntegrationType.CLOUD,
                "category": "container",
                "description": "Container platform",
                "required_fields": ["host", "cert_path", "key_path"],
                "icon": "docker",
            },
            "ansible": {
                "name": "Ansible",
                "type": IntegrationType.CICD,
                "category": "automation",
                "description": "IT automation tool",
                "required_fields": ["inventory_path"],
                "icon": "ansible",
            },
            "terraform": {
                "name": "Terraform",
                "type": IntegrationType.CICD,
                "category": "iac",
                "description": "Infrastructure as code tool",
                "required_fields": ["state_path", "token"],
                "icon": "terraform",
            },
            "consul": {
                "name": "Consul",
                "type": IntegrationType.CLOUD,
                "category": "service_mesh",
                "description": "Service discovery and configuration",
                "required_fields": ["url", "token"],
                "icon": "consul",
            },
            "etcd": {
                "name": "etcd",
                "type": IntegrationType.CLOUD,
                "category": "database",
                "description": "Distributed key-value store",
                "required_fields": ["endpoints"],
                "icon": "etcd",
            },
            "redis": {
                "name": "Redis",
                "type": IntegrationType.CLOUD,
                "category": "database",
                "description": "In-memory data structure store",
                "required_fields": ["host", "port"],
                "icon": "redis",
            },
            "mongodb": {
                "name": "MongoDB",
                "type": IntegrationType.CLOUD,
                "category": "database",
                "description": "NoSQL database",
                "required_fields": ["connection_string"],
                "icon": "mongodb",
            },
            "postgresql": {
                "name": "PostgreSQL",
                "type": IntegrationType.CLOUD,
                "category": "database",
                "description": "Relational database",
                "required_fields": ["host", "port", "database", "username", "password"],
                "icon": "postgresql",
            },
            "mysql": {
                "name": "MySQL",
                "type": IntegrationType.CLOUD,
                "category": "database",
                "description": "Relational database",
                "required_fields": ["host", "port", "database", "username", "password"],
                "icon": "mysql",
            },
        }

    def get_integration_template(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get integration template by provider"""
        return self.integration_templates.get(provider)

    def list_integrations_by_category(self, category: str) -> List[Dict[str, Any]]:
        """List integrations by category"""
        return [
            template
            for template in self.integration_templates.values()
            if template.get("category") == category
        ]

    def search_integrations(self, query: str) -> List[Dict[str, Any]]:
        """Search integrations by name or description"""
        query_lower = query.lower()
        return [
            template
            for template in self.integration_templates.values()
            if query_lower in template["name"].lower()
            or query_lower in template["description"].lower()
        ]


# ============================================================
# P2 Enhancement: Connector Marketplace
# ============================================================
class ConnectorMarketplace:
    """
    P2 Enhanced connector marketplace for discovering and managing connectors
    """

    def __init__(self):
        self.registry = ExtendedIntegrationRegistry()
        self.installed_connectors: Dict[str, Dict[str, Any]] = {}
        self.connector_ratings: Dict[str, List[float]] = {}

    async def discover_connectors(
        self, category: Optional[str] = None, search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover available connectors

        Args:
            category: Filter by category
            search_query: Search by name or description

        Returns:
            List of available connectors
        """
        if category:
            connectors = self.registry.list_integrations_by_category(category)
        elif search_query:
            connectors = self.registry.search_integrations(search_query)
        else:
            connectors = list(self.registry.integration_templates.values())

        # Add installation status and ratings
        for connector in connectors:
            provider = list(self.registry.integration_templates.keys())[
                list(self.registry.integration_templates.values()).index(connector)
            ]
            connector["installed"] = provider in self.installed_connectors
            connector["rating"] = self._get_average_rating(provider)
            connector["downloads"] = self._get_download_count(provider)

        return connectors

    async def install_connector(
        self, provider: str, configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Install a connector

        Args:
            provider: Provider name
            configuration: Connector configuration

        Returns:
            Installation result
        """
        template = self.registry.get_integration_template(provider)
        if not template:
            return {"success": False, "error": "Connector not found"}

        # Validate required fields
        for required_field in template["required_fields"]:
            if required_field not in configuration:
                return {"success": False, "error": f"Missing required field: {required_field}"}

        # Install connector
        self.installed_connectors[provider] = {
            "template": template,
            "configuration": configuration,
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
        }

        return {"success": True, "connector_id": provider}

    async def uninstall_connector(self, provider: str) -> Dict[str, Any]:
        """
        Uninstall a connector

        Args:
            provider: Provider name

        Returns:
            Uninstallation result
        """
        if provider not in self.installed_connectors:
            return {"success": False, "error": "Connector not installed"}

        del self.installed_connectors[provider]

        return {"success": True}

    async def rate_connector(self, provider: str, rating: float) -> Dict[str, Any]:
        """
        Rate a connector

        Args:
            provider: Provider name
            rating: Rating value (1-5)

        Returns:
            Rating result
        """
        if provider not in self.registry.integration_templates:
            return {"success": False, "error": "Connector not found"}

        if not 1 <= rating <= 5:
            return {"success": False, "error": "Rating must be between 1 and 5"}

        if provider not in self.connector_ratings:
            self.connector_ratings[provider] = []

        self.connector_ratings[provider].append(rating)

        return {"success": True, "average_rating": self._get_average_rating(provider)}

    def _get_average_rating(self, provider: str) -> float:
        """Get average rating for a connector"""
        ratings = self.connector_ratings.get(provider, [])
        if not ratings:
            return 0.0
        return sum(ratings) / len(ratings)

    def _get_download_count(self, provider: str) -> int:
        """Get download count for a connector (simulated)"""
        # In production, this would come from a database
        return hash(provider) % 10000 + 100

    async def get_connector_details(self, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a connector

        Args:
            provider: Provider name

        Returns:
            Connector details
        """
        template = self.registry.get_integration_template(provider)
        if not template:
            return None

        return {
            **template,
            "installed": provider in self.installed_connectors,
            "rating": self._get_average_rating(provider),
            "downloads": self._get_download_count(provider),
            "configuration": self.installed_connectors.get(provider, {}).get("configuration"),
        }


# ============================================================
# P2 Enhancement: Plugin SDK
# ============================================================
class PluginSDK:
    """
    P2 Enhanced plugin SDK for creating custom integrations
    """

    def __init__(self):
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.plugin_hooks: Dict[str, List[Callable]] = {}

    async def register_plugin(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_version: str,
        plugin_config: Dict[str, Any],
        plugin_handler: Callable,
    ) -> Dict[str, Any]:
        """
        Register a custom plugin

        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Plugin name
            plugin_version: Plugin version
            plugin_config: Plugin configuration
            plugin_handler: Plugin handler function

        Returns:
            Registration result
        """
        if plugin_id in self.plugins:
            return {"success": False, "error": "Plugin already registered"}

        self.plugins[plugin_id] = {
            "name": plugin_name,
            "version": plugin_version,
            "config": plugin_config,
            "handler": plugin_handler,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        return {"success": True, "plugin_id": plugin_id}

    async def unregister_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """
        Unregister a plugin

        Args:
            plugin_id: Plugin identifier

        Returns:
            Unregistration result
        """
        if plugin_id not in self.plugins:
            return {"success": False, "error": "Plugin not found"}

        del self.plugins[plugin_id]

        return {"success": True}

    async def execute_plugin(self, plugin_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a plugin

        Args:
            plugin_id: Plugin identifier
            event_data: Event data to pass to the plugin

        Returns:
            Execution result
        """
        if plugin_id not in self.plugins:
            return {"success": False, "error": "Plugin not found"}

        plugin = self.plugins[plugin_id]

        try:
            result = await plugin["handler"](event_data)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def register_hook(self, hook_name: str, hook_handler: Callable) -> Dict[str, Any]:
        """
        Register a hook for plugin events

        Args:
            hook_name: Hook name
            hook_handler: Hook handler function

        Returns:
            Registration result
        """
        if hook_name not in self.plugin_hooks:
            self.plugin_hooks[hook_name] = []

        self.plugin_hooks[hook_name].append(hook_handler)

        return {"success": True}

    async def trigger_hook(self, hook_name: str, hook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Trigger a hook

        Args:
            hook_name: Hook name
            hook_data: Data to pass to hook handlers

        Returns:
            List of hook execution results
        """
        if hook_name not in self.plugin_hooks:
            return []

        results = []
        for handler in self.plugin_hooks[hook_name]:
            try:
                result = await handler(hook_data)
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return results

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins"""
        return [
            {
                "plugin_id": plugin_id,
                "name": plugin["name"],
                "version": plugin["version"],
                "registered_at": plugin["registered_at"],
            }
            for plugin_id, plugin in self.plugins.items()
        ]

    def get_plugin_template(self) -> str:
        """
        Get a plugin template for developers

        Returns:
            Plugin template code
        """
        return '''
from typing import Dict, Any

async def plugin_handler(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Plugin handler function

    Args:
        event_data: Event data passed to the plugin

    Returns:
        Plugin execution result
    """
    # Your plugin logic here
    return {
        "success": True,
        "message": "Plugin executed successfully",
        "data": event_data
    }

# Plugin configuration
plugin_config = {
    "name": "My Custom Plugin",
    "version": "1.0.0",
    "description": "A custom integration plugin",
    "author": "Your Name",
}
'''


# ============================================================
# P2 Enhancement: Global instances
# ============================================================
EXTENDED_INTEGRATION_REGISTRY = ExtendedIntegrationRegistry()
CONNECTOR_MARKETPLACE = ConnectorMarketplace()
PLUGIN_SDK = PluginSDK()
