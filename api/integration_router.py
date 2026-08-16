import os

# -*- coding: utf-8 -*-
"""
Integration Ecosystem Router
============================

API endpoints for comprehensive integration ecosystem including:
- Monitoring tools integration (Prometheus, Grafana, ELK)
- Cloud platform integration (AWS, Azure, GCP)
- CI/CD tools integration (Jenkins, GitLab CI, GitHub Actions)
- ITSM tools integration (ServiceNow, Jira)
- Notification channels (Slack, Teams, DingTalk, WeChat)
- Webhook management and handling
"""

import logging
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integration", tags=["集成生态"])
try:
    from core.integration_manager import IntegrationStatus, IntegrationType, integration_manager

    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False
    logger.warning("Integration manager not available")

try:
    from gateway.services_client import (
        remote_datadog_query,
        remote_elk_search,
        remote_grafana_query,
    )

    REMOTE_CLIENT_AVAILABLE = True
except ImportError:
    REMOTE_CLIENT_AVAILABLE = False
    logger.warning("Remote integration client not available")


class IntegrationRegistrationRequest(BaseModel):
    """Request for integration registration"""

    integration_type: str
    name: str
    config: dict[str, Any]
    enabled: bool = True

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"integration_type": "example", "name": "example", "config": {}},
            "enabled": True,
        },
    }


class NotificationRequest(BaseModel):
    """Request for sending notification"""

    channel: str
    recipient: str
    subject: str
    body: str
    priority: str = "normal"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "channel": "example",
                "recipient": "example",
                "subject": "example",
                "body": "example",
                "priority": "example",
            }
        },
    }


class WebhookRegistrationRequest(BaseModel):
    """Request for webhook registration"""

    source: str
    event_type: str
    endpoint: str
    secret: Optional[str] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "source": "example",
                "event_type": "example",
                "endpoint": "example",
                "secret": os.environ.get("EXAMPLE_SECRET", ""),
            }
        },
    }


class PrometheusQueryRequest(BaseModel):
    """Request for Prometheus query"""

    integration_id: str
    query: str
    time_range: str = "1h"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"integration_id": "example", "query": "example", "time_range": "example"}
        },
    }


class JenkinsJobRequest(BaseModel):
    """Request for Jenkins job trigger"""

    integration_id: str
    job_name: str
    parameters: Optional[dict[str, Any]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"integration_id": "example", "job_name": "example", "parameters": "example"}
        },
    }


class JiraIssueRequest(BaseModel):
    """Request for Jira issue creation"""

    integration_id: str
    summary: str
    description: str
    issue_type: str = "Bug"
    priority: str = "Medium"

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "integration_id": "example",
                "summary": "example",
                "description": "example",
                "issue_type": "example",
                "priority": "example",
            }
        },
    }


class IntegrationQueryRequest(BaseModel):
    """Request for querying an integration data source."""

    query: str = ""
    params: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"query": "avg:system.cpu.user{*}", "params": {"from": "now-1h", "to": "now"}}
        },
    }


@router.post(
    "/register",
    summary="注册集成",
    responses={
        (200): {
            "description": "注册成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "integration": {
                            "integration_id": "int-123",
                            "integration_type": "prometheus",
                            "name": "Prometheus监控",
                            "enabled": True,
                            "status": "active",
                            "last_tested": "2026-07-03T09:00:00Z",
                        },
                    }
                }
            },
        },
        (400): {"description": "无效的集成类型"},
        (503): {"description": "集成管理器不可用"},
    },
)
async def register_integration(request: IntegrationRegistrationRequest) -> dict[str, Any]:
    """
    注册新的集成
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    try:
        integration_type: IntegrationType = IntegrationType(request.integration_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的集成类型: {request.integration_type}")
    integration = await integration_manager.register_integration(
        integration_type=integration_type,
        name=request.name,
        config=request.config,
        enabled=request.enabled,
    )
    return {
        "status": "success",
        "integration": {
            "integration_id": integration.integration_id,
            "integration_type": integration.integration_type.value,
            "name": integration.name,
            "enabled": integration.enabled,
            "status": integration.status.value,
            "last_tested": integration.last_tested.isoformat() if integration.last_tested else None,
        },
    }


@router.get(
    "/list",
    summary="获取集成列表",
    responses={
        (200): {
            "description": "集成列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "total_integrations": 2,
                        "integrations": [
                            {
                                "integration_id": "int-123",
                                "integration_type": "prometheus",
                                "name": "Prometheus监控",
                                "enabled": True,
                                "status": "active",
                                "last_tested": "2026-07-03T09:00:00Z",
                                "last_error": None,
                            },
                            {
                                "integration_id": "int-124",
                                "integration_type": "grafana",
                                "name": "Grafana仪表板",
                                "enabled": True,
                                "status": "active",
                                "last_tested": "2026-07-03T08:30:00Z",
                                "last_error": None,
                            },
                        ],
                    }
                }
            },
        },
        (400): {"description": "无效的参数"},
        (503): {"description": "集成管理器不可用"},
    },
)
async def list_integrations(
    integration_type: Optional[str] = None, status: Optional[str] = None
) -> dict[str, Any]:
    """
    获取所有集成列表
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    integrations: List[Any] = list(integration_manager.integrations.values())
    if integration_type:
        try:
            filter_type: IntegrationType = IntegrationType(integration_type)
            integrations = [i for i in integrations if i.integration_type == filter_type]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的集成类型: {integration_type}")
    if status:
        try:
            filter_status: IntegrationStatus = IntegrationStatus(status)
            integrations = [i for i in integrations if i.status == filter_status]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {status}")
    return {
        "status": "success",
        "total_integrations": len(integrations),
        "integrations": [
            {
                "integration_id": i.integration_id,
                "integration_type": i.integration_type.value,
                "name": i.name,
                "enabled": i.enabled,
                "status": i.status.value,
                "last_tested": i.last_tested.isoformat() if i.last_tested else None,
                "last_error": i.last_error,
            }
            for i in integrations
        ],
    }


@router.post(
    "/test/{integration_id}",
    summary="测试集成",
    responses={(200): {"description": "测试结果"}, (503): {"description": "集成管理器不可用"}},
)
async def test_integration(integration_id: str) -> dict[str, Any]:
    """
    测试指定集成的连接
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    result: dict[str, Any] = await integration_manager.test_integration(integration_id)
    return {"status": "success", "test_result": result}


@router.delete(
    "/{integration_id}",
    summary="删除集成",
    responses={
        (200): {"description": "删除成功"},
        (404): {"description": "集成不存在"},
        (503): {"description": "集成管理器不可用"},
    },
)
async def delete_integration(integration_id: str) -> dict[str, Any]:
    """
    删除指定的集成
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    if integration_id not in integration_manager.integrations:
        raise HTTPException(status_code=404, detail=f"集成 {integration_id} 不存在")
    del integration_manager.integrations[integration_id]
    return {"status": "success", "message": f"集成 {integration_id} 已删除"}


@router.post(
    "/notification/send",
    summary="发送通知",
    responses={(200): {"description": "发送成功"}, (503): {"description": "集成管理器不可用"}},
)
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    """
    通过指定渠道发送通知
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    message = await integration_manager.send_notification(
        channel=request.channel,
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        priority=request.priority,
    )
    return {
        "status": "success",
        "message": {
            "message_id": message.message_id,
            "channel": message.channel,
            "recipient": message.recipient,
            "sent": message.sent,
            "error": message.error,
            "timestamp": message.timestamp.isoformat(),
        },
    }


@router.get(
    "/notification/channels",
    summary="获取通知渠道",
    responses={(200): {"description": "通知渠道列表"}, (503): {"description": "集成管理器不可用"}},
)
async def get_notification_channels() -> dict[str, Any]:
    """
    获取所有通知渠道
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    channels = [
        {"name": name, "type": channel["type"], "enabled": channel.get("enabled", True)}
        for name, channel in integration_manager.notification_channels.items()
    ]
    return {"status": "success", "channels": channels}


@router.post(
    "/webhook/register",
    summary="注册Webhook",
    responses={(200): {"description": "注册成功"}, (503): {"description": "集成管理器不可用"}},
)
async def register_webhook(request: WebhookRegistrationRequest) -> dict[str, Any]:
    """
    注册Webhook端点
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    webhook_id = await integration_manager.register_webhook(
        source=request.source,
        event_type=request.event_type,
        endpoint=request.endpoint,
        secret=request.secret,
    )
    return {"status": "success", "webhook_id": webhook_id}


@router.post(
    "/webhook/handle",
    summary="处理Webhook事件",
    responses={(200): {"description": "处理结果"}, (503): {"description": "集成管理器不可用"}},
)
async def handle_webhook(
    webhook_id: str, payload: dict[str, Any], signature: Optional[str] = None
) -> dict[str, Any]:
    """
    处理传入的Webhook事件
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    result = await integration_manager.handle_webhook(
        webhook_id=webhook_id, payload=payload, signature=signature
    )
    return {"status": "success", "result": result}


@router.get(
    "/webhooks",
    summary="获取Webhook列表",
    responses={(200): {"description": "Webhook列表"}, (503): {"description": "集成管理器不可用"}},
)
async def list_webhooks() -> dict[str, Any]:
    """
    获取所有注册的Webhook
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    webhooks = [
        {
            "webhook_id": webhook["webhook_id"],
            "source": webhook["source"],
            "event_type": webhook["event_type"],
            "endpoint": webhook["endpoint"],
            "enabled": webhook.get("enabled", True),
            "created_at": webhook["created_at"],
        }
        for webhook in integration_manager.webhooks.values()
    ]
    return {"status": "success", "webhooks": webhooks}


@router.post(
    "/prometheus/query",
    summary="查询Prometheus指标",
    responses={(200): {"description": "查询结果"}, (503): {"description": "集成管理器不可用"}},
)
async def query_prometheus_metrics(request: PrometheusQueryRequest) -> dict[str, Any]:
    """
    查询Prometheus指标
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    result = await integration_manager.query_prometheus_metrics(
        integration_id=request.integration_id, query=request.query, time_range=request.time_range
    )
    return {"status": "success", "query_result": result}


@router.post(
    "/jenkins/trigger",
    summary="触发Jenkins任务",
    responses={(200): {"description": "触发结果"}, (503): {"description": "集成管理器不可用"}},
)
async def trigger_jenkins_job(request: JenkinsJobRequest) -> dict[str, Any]:
    """
    触发Jenkins构建任务
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    result = await integration_manager.trigger_jenkins_job(
        integration_id=request.integration_id,
        job_name=request.job_name,
        parameters=request.parameters,
    )
    return {"status": "success", "trigger_result": result}


@router.post(
    "/jira/issue",
    summary="创建Jira问题",
    responses={(200): {"description": "创建结果"}, (503): {"description": "集成管理器不可用"}},
)
async def create_jira_issue(request: JiraIssueRequest) -> dict[str, Any]:
    """
    创建Jira问题
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    result = await integration_manager.create_jira_issue(
        integration_id=request.integration_id,
        summary=request.summary,
        description=request.description,
        issue_type=request.issue_type,
        priority=request.priority,
    )
    return {"status": "success", "creation_result": result}


@router.get(
    "/templates",
    summary="获取集成模板",
    responses={(200): {"description": "集成模板"}, (503): {"description": "集成管理器不可用"}},
)
async def get_integration_templates() -> dict[str, Any]:
    """
    获取可用的集成模板
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    templates = {}
    for template_key, template in integration_manager.integration_templates.items():
        templates[template_key] = {
            "type": template["type"].value,
            "name": template["name"],
            "config_schema": template.get("config_schema", {}),
            "default_config": template.get("default_config", {}),
        }
    return {"status": "success", "templates": templates}


@router.get(
    "/summary",
    summary="获取集成摘要",
    responses={(200): {"description": "集成摘要"}, (503): {"description": "集成管理器不可用"}},
)
async def get_integration_summary() -> dict[str, Any]:
    """
    获取集成生态的摘要信息
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    summary = integration_manager.get_integration_summary()
    return {"status": "success", "integration_summary": summary}


@router.get(
    "/types", summary="获取支持的集成类型", responses={(200): {"description": "集成类型列表"}}
)
async def get_integration_types() -> dict[str, Any]:
    """
    获取支持的集成类型列表
    """
    integration_types = [t.value for t in IntegrationType]
    return {"status": "success", "integration_types": integration_types}


@router.get(
    "/events",
    summary="获取Webhook事件",
    responses={
        (200): {"description": "Webhook事件列表"},
        (503): {"description": "集成管理器不可用"},
    },
)
async def get_webhook_events(
    processed: bool = Query(default=False), limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    """
    获取Webhook事件历史
    """
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")
    events = integration_manager.webhook_events
    if processed is not None:
        events = [e for e in events if e.processed == processed]
    events.sort(key=lambda x: x.timestamp, reverse=True)
    return {
        "status": "success",
        "total_events": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "source": e.source,
                "event_type": e.event_type,
                "processed": e.processed,
                "retry_count": e.retry_count,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events[:limit]
        ],
    }


@router.post(
    "/{integration_id}/query",
    summary="查询集成真实数据",
    responses={
        (200): {"description": "查询结果"},
        (400): {"description": "参数错误或不支持的集成类型"},
        (404): {"description": "集成不存在"},
        (503): {"description": "集成管理器或远程客户端不可用"},
    },
)
async def query_integration(
    request: IntegrationQueryRequest,
    integration_id: str = Path(..., min_length=1, description="集成 ID"),
) -> dict[str, Any]:
    """Query real data from an external integration (Datadog, Grafana, ELK, CloudWatch, PagerDuty)."""
    if not INTEGRATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="集成管理器不可用")

    integration = integration_manager.integrations.get(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail=f"集成 {integration_id} 不存在")
    if not integration.enabled:
        raise HTTPException(status_code=400, detail="集成未启用")

    provider = integration.config.get("provider", integration.name.lower())
    config = dict(integration.config)
    config["query"] = request.query
    config.update(request.params)
    time_range = request.params.get("time_range", "1h")

    try:
        if provider in ("datadog", "datadoghq"):
            if not REMOTE_CLIENT_AVAILABLE:
                raise HTTPException(status_code=503, detail="远程集成客户端不可用")
            result = await remote_datadog_query(config)
        elif provider in ("grafana",):
            if not REMOTE_CLIENT_AVAILABLE:
                raise HTTPException(status_code=503, detail="远程集成客户端不可用")
            result = await remote_grafana_query(config)
        elif provider in ("elk", "elasticsearch", "elk_stack"):
            if not REMOTE_CLIENT_AVAILABLE:
                raise HTTPException(status_code=503, detail="远程集成客户端不可用")
            result = await remote_elk_search(config)
        elif provider in ("cloudwatch", "aws"):
            result = await integration_manager.query_cloudwatch_metrics(
                integration_id=integration_id, query=request.query, time_range=time_range
            )
        elif provider in ("pagerduty", "pd"):
            result = await integration_manager.query_pagerduty_incidents(
                integration_id=integration_id, query=request.query, time_range=time_range
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的集成类型: {provider}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"查询失败: {exc}") from exc

    return {"status": "success", "provider": provider, "query_result": result}
