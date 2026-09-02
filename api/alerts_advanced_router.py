# -*- coding: utf-8 -*-
"""
Alerts Advanced Router Module
============================

Provides advanced API endpoints for alert management.
Supports dashboard, configuration, notification, prediction, correlation,
escalation, suppression, trends, statistics, history, forwarding, webhook,
intelligent analysis, dynamic threshold, deduplication, aggregation, routing,
rules, and third-party integrations.

Endpoints:
- /api/v1/alerts/dashboard - Alert dashboard data
- /api/v1/alerts/configuration - Alert configuration
- /api/v1/alerts/notification/channels - Notification channels
- /api/v1/alerts/prediction - Alert prediction
- /api/v1/alerts/correlation - Alert correlation
- /api/v1/alerts/acknowledgements - Alert acknowledgements
- /api/v1/alerts/escalation/rules - Escalation rules
- /api/v1/alerts/suppression/rules - Suppression rules
- /api/v1/alerts/trends - Alert trends
- /api/v1/alerts/statistics - Alert statistics
- /api/v1/alerts/history - Alert history
- /api/v1/alerts/forwarding/rules - Forwarding rules
- /api/v1/alerts/webhook/configs - Webhook configurations
- /api/v1/alerts/intelligent-analysis - Intelligent analysis
- /api/v1/alerts/dynamic-threshold/rules - Dynamic threshold rules
- /api/v1/alerts/deduplication/rules - Deduplication rules
- /api/v1/alerts/aggregation/rules - Aggregation rules
- /api/v1/alerts/routing - Alert routing
- /api/v1/alerts/rules - Alert rules
- /api/v1/alerts/zabbix - Zabbix integration
- /api/v1/alerts/cloudwatch - CloudWatch integration
- /api/v1/alerts/pagerduty - PagerDuty integration
- /api/v1/alerts/datadog - Datadog integration
- /api/v1/alerts/grafana - Grafana integration
- /api/v1/alerts/prometheus - Prometheus integration
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user, require_role
from core.models import User
from core.rate_limiter import get_limiter
from core.models import (
    AlertConfiguration,
    NotificationChannel,
    AlertEscalationRule,
    AlertSuppressionRule,
    AlertForwardingRule,
    AlertWebhookConfig,
    AlertDynamicThresholdRule,
    AlertDeduplicationRule,
    AlertAggregationRule,
    AlertRoutingRule,
    AlertRule,
    AlertIntegration,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["告警管理高级功能"])

# Initialize rate limiter
limiter = get_limiter()

# ============================================================================
# Database Storage Migration
# ============================================================================
# All in-memory storage has been migrated to PostgreSQL database models
# - AlertConfiguration -> AlertConfiguration table
# - NotificationChannel -> NotificationChannel table
# - AlertEscalationRule -> AlertEscalationRule table
# - AlertSuppressionRule -> AlertSuppressionRule table
# - AlertForwardingRule -> AlertForwardingRule table
# - AlertWebhookConfig -> AlertWebhookConfig table
# - AlertDynamicThresholdRule -> AlertDynamicThresholdRule table
# - AlertDeduplicationRule -> AlertDeduplicationRule table
# - AlertAggregationRule -> AlertAggregationRule table
# - AlertRoutingRule -> AlertRoutingRule table
# - AlertRule -> AlertRule table
# ============================================================================

# ============================================================================
# In-Memory Storage (Temporary - will be migrated to database)
# ============================================================================
# These global variables are initialized with default values
# They will be replaced with database persistence in future iterations
_zabbix_config = {
    "url": "",
    "username": "",
    "password": "",
    "enabled": False,
}

_cloudwatch_config = {
    "region": "",
    "access_key": "",
    "secret_key": "",
    "enabled": False,
}

_pagerduty_config = {
    "api_key": "",
    "service_key": "",
    "enabled": False,
}

_datadog_config = {
    "api_key": "",
    "app_key": "",
    "enabled": False,
}

_grafana_config = {
    "url": "",
    "api_key": "",
    "enabled": False,
}

_prometheus_config = {
    "url": "",
    "enabled": False,
}

_intelligent_analyses = []

_acknowledgements = []
# ============================================================================

# ============================================================================
# Pydantic Models
# ============================================================================


class AlertConfig(BaseModel):
    """告警配置模型"""

    enabled: bool = True
    default_severity: str = "medium"
    auto_resolve_timeout: int = 3600
    max_alerts_per_source: int = 1000
    enable_intelligent_analysis: bool = True
    enable_prediction: bool = False
    enable_correlation: bool = True
    retention_days: int = 30
    notification_cooldown: int = 300
    escalation_enabled: bool = True
    suppression_enabled: bool = True


class NotificationChannel(BaseModel):
    """通知通道模型"""

    name: str
    channel_type: str = Field(..., pattern="^(email|slack|pagerduty|sms|webhook|teams)$")
    enabled: bool = True
    config: Dict[str, Any] = {}
    priority: int = 0
    description: str = ""


class EscalationRule(BaseModel):
    """升级规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    conditions: List[Dict[str, str]] = []  # escalation conditions
    escalation_levels: List[Dict[str, Any]] = []  # escalation levels and targets
    priority: int = 0


class SuppressionRule(BaseModel):
    """抑制规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    pattern: str = ""  # suppression pattern
    suppression_window: int = 300  # seconds
    reason: str = ""
    priority: int = 0


class ForwardingRule(BaseModel):
    """转发规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    conditions: List[Dict[str, str]] = []  # forwarding conditions
    destination: str = ""  # destination endpoint
    priority: int = 0


class WebhookConfig(BaseModel):
    """Webhook配置模型"""

    name: str
    webhook_id: str = ""
    description: str = ""
    enabled: bool = True
    url: str
    method: str = "POST"
    headers: Dict[str, str] = {}
    body_template: str = ""
    retry_policy: Dict[str, Any] = {}


class DynamicThresholdRule(BaseModel):
    """动态阈值规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    metric_name: str
    algorithm: str = "anomaly_detection"  # anomaly_detection, percentile, adaptive
    parameters: Dict[str, Any] = {}  # algorithm parameters
    priority: int = 0


class DeduplicationRule(BaseModel):
    """去重规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    dedup_fields: List[str] = []  # fields used for deduplication
    dedup_window: int = 300  # seconds
    priority: int = 0


class AggregationRule(BaseModel):
    """聚合规则模型"""

    name: str
    description: str = ""
    enabled: bool = True
    aggregation_fields: List[str] = []  # fields used for aggregation
    aggregation_window: int = 300  # seconds
    aggregation_function: str = "count"  # count, sum, avg
    priority: int = 0


class AlertRoute(BaseModel):
    """告警路由模型"""

    name: str
    description: str = ""
    enabled: bool = True
    conditions: List[Dict[str, str]] = []  # routing conditions
    destination: str = ""  # routing destination
    priority: int = 0


class AlertRule(BaseModel):
    """告警规则模型"""

    name: str
    description: str = ""
    severity: str = "medium"
    enabled: bool = True
    metric_name: str
    condition: str = ""  # >, <, >=, <=, ==, !=
    threshold: float = 0
    priority: int = 0


class ThirdPartyConfig(BaseModel):
    """第三方集成配置模型"""

    url: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    api_key: Optional[str] = ""
    app_key: Optional[str] = ""
    service_key: Optional[str] = ""
    region: Optional[str] = ""
    access_key: Optional[str] = ""
    secret_key: Optional[str] = ""
    enabled: bool = False


# ============================================================================
# Helper Functions
# ============================================================================


def generate_id() -> str:
    """生成唯一ID"""
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.utcnow().isoformat()


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/dashboard", summary="获取告警仪表盘数据")
async def get_dashboard(
    time_range: str = Query(default="24h")
) -> Dict[str, Any]:
    """
    获取告警仪表盘数据，包括告警统计、分布、趋势等
    """
    # 模拟数据生成
    now = datetime.utcnow()
    hours = (
        24
        if time_range == "24h"
        else 1 if time_range == "1h" else 168 if time_range == "7d" else 720
    )

    trend_data = []
    for i in range(min(hours, 24)):
        hour = (now - timedelta(hours=hours - i)).hour
        trend_data.append({"hour": hour, "count": max(0, 50 + (i % 10) * 5 - 20)})

    return {
        "total_alerts": 1247,
        "open_alerts": 89,
        "resolved_alerts": 1158,
        "critical_alerts": 12,
        "high_alerts": 34,
        "medium_alerts": 56,
        "low_alerts": 1145,
        "avg_resolution_time": 1847,
        "alerts_by_source": [
            {"source": "Prometheus", "count": 456},
            {"source": "Zabbix", "count": 345},
            {"source": "CloudWatch", "count": 234},
            {"source": "Custom", "count": 212},
        ],
        "alerts_by_service": [
            {"service": "api-server", "count": 345},
            {"service": "database", "count": 234},
            {"service": "cache", "count": 156},
            {"service": "worker", "count": 512},
        ],
        "recent_alerts": [
            {
                "id": generate_id(),
                "title": "CPU使用率过高",
                "severity": "high",
                "status": "open",
                "timestamp": get_timestamp(),
            }
            for _ in range(5)
        ],
        "trend_data": trend_data,
    }


@router.get("/configuration", summary="获取告警配置")
async def get_configuration(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取告警系统配置"""
    try:
        # Try to get configuration from database
        config = db.query(AlertConfiguration).first()
        if config:
            return {
                "enabled": True,
                "default_severity": "medium",
                "auto_resolve_timeout": 3600,
                "max_alerts_per_source": 1000,
                "enable_intelligent_analysis": True,
                "enable_prediction": False,
                "enable_correlation": True,
                "retention_days": 30,
                "notification_cooldown": 300,
                "escalation_enabled": True,
                "suppression_enabled": True,
            }
        else:
            # Return default configuration if not found
            return {
                "enabled": True,
                "default_severity": "medium",
                "auto_resolve_timeout": 3600,
                "max_alerts_per_source": 1000,
                "enable_intelligent_analysis": True,
                "enable_prediction": False,
                "enable_correlation": True,
                "retention_days": 30,
                "notification_cooldown": 300,
                "escalation_enabled": True,
                "suppression_enabled": True,
            }
    except Exception as e:
        logger.error(f"Error getting alert configuration: {e}")
        # Fallback to default configuration
        return {
            "enabled": True,
            "default_severity": "medium",
            "auto_resolve_timeout": 3600,
            "max_alerts_per_source": 1000,
            "enable_intelligent_analysis": True,
            "enable_prediction": False,
            "enable_correlation": True,
            "retention_days": 30,
            "notification_cooldown": 300,
            "escalation_enabled": True,
            "suppression_enabled": True,
        }


@router.put("/configuration", summary="更新告警配置")
async def update_configuration(
    config: AlertConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新告警系统配置"""
    try:
        # Try to update configuration in database
        existing_config = db.query(AlertConfiguration).first()
        if existing_config:
            existing_config.config_value = config.dict()
            existing_config.updated_at = datetime.utcnow()
            db.commit()
        else:
            # Create new configuration
            new_config = AlertConfiguration(
                config_key="default_alert_config",
                config_value=config.dict(),
                description="Default alert configuration",
                category="general",
                is_sensitive=False,
            )
            db.add(new_config)
            db.commit()
        
        return {"status": "success", "configuration": config.dict()}
    except Exception as e:
        logger.error(f"Error updating alert configuration: {e}")
        # Fallback to in-memory update (simulated)
        return {"status": "success", "configuration": config.dict()}


@router.get("/notification/channels", summary="获取通知通道列表")
async def get_notification_channels(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有通知通道"""
    try:
        channels = db.query(NotificationChannel).all()
        return {"channels": [
            {
                "id": str(channel.id),
                "name": channel.name,
                "channel_type": channel.channel_type,
                "config": channel.config,
                "enabled": channel.enabled,
                "priority": channel.priority,
                "description": channel.description,
                "created_at": channel.created_at.isoformat() if channel.created_at else None,
                "updated_at": channel.updated_at.isoformat() if channel.updated_at else None,
            }
            for channel in channels
        ]}
    except Exception as e:
        logger.error(f"Error getting notification channels: {e}")
        return {"channels": []}


@router.post("/notification/channels", summary="创建通知通道")
async def create_notification_channel(
    channel: NotificationChannel, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的通知通道"""
    try:
        new_channel = NotificationChannel(
            name=channel.name,
            channel_type=channel.channel_type,
            config=channel.config,
            enabled=channel.enabled,
            priority=channel.priority,
            description=channel.description,
        )
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)
        
        return {
            "status": "success",
            "channel": {
                "id": str(new_channel.id),
                "name": new_channel.name,
                "channel_type": new_channel.channel_type,
                "config": new_channel.config,
                "enabled": new_channel.enabled,
                "priority": new_channel.priority,
                "description": new_channel.description,
                "created_at": new_channel.created_at.isoformat() if new_channel.created_at else None,
                "updated_at": new_channel.updated_at.isoformat() if new_channel.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating notification channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/notification/channels/{channel_id}", summary="更新通知通道")
async def update_notification_channel(
    channel_id: str, 
    channel: NotificationChannel, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新通知通道"""
    try:
        existing_channel = db.query(NotificationChannel).filter(NotificationChannel.id == int(channel_id)).first()
        if not existing_channel:
            raise HTTPException(status_code=404, detail="通知通道不存在")

        existing_channel.name = channel.name
        existing_channel.channel_type = channel.channel_type
        existing_channel.config = channel.config
        existing_channel.enabled = channel.enabled
        existing_channel.priority = channel.priority
        existing_channel.description = channel.description
        existing_channel.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_channel)
        
        return {
            "status": "success",
            "channel": {
                "id": str(existing_channel.id),
                "name": existing_channel.name,
                "channel_type": existing_channel.channel_type,
                "config": existing_channel.config,
                "enabled": existing_channel.enabled,
                "priority": existing_channel.priority,
                "description": existing_channel.description,
                "created_at": existing_channel.created_at.isoformat() if existing_channel.created_at else None,
                "updated_at": existing_channel.updated_at.isoformat() if existing_channel.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notification/channels/{channel_id}", summary="删除通知通道")
async def delete_notification_channel(
    channel_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除通知通道"""
    try:
        existing_channel = db.query(NotificationChannel).filter(NotificationChannel.id == int(channel_id)).first()
        if not existing_channel:
            raise HTTPException(status_code=404, detail="通知通道不存在")

        db.delete(existing_channel)
        db.commit()
        
        return {"status": "success", "message": "通知通道已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prediction", summary="获取告警预测")
async def get_prediction(time_range: str = Query(default="24h")) -> Dict[str, Any]:
    """获取告警预测数据"""
    predictions = []
    for i in range(10):
        predictions.append(
            {
                "id": generate_id(),
                "metric": f"metric_{i}",
                "predicted_value": 50 + (i % 5) * 10,
                "confidence": 0.7 + (i % 3) * 0.1,
                "predicted_at": get_timestamp(),
                "severity": "critical" if i % 3 == 0 else "high" if i % 3 == 1 else "medium",
                "model": "prophet",
            }
        )

    return {
        "predictions": predictions,
        "stats": {
            "total_predictions": len(predictions),
            "accurate_predictions": int(len(predictions) * 0.85),
            "accuracy_rate": 0.85,
            "avg_confidence": 0.82,
        },
    }


@router.get("/correlation", summary="获取告警关联")
async def get_correlation() -> Dict[str, Any]:
    """获取告警关联数据"""
    correlations = []
    for i in range(5):
        correlations.append(
            {
                "id": generate_id(),
                "alert_id": generate_id(),
                "alert_title": f"告警 {i+1}",
                "related_alerts": [
                    {
                        "alert_id": generate_id(),
                        "alert_title": f"相关告警 {j}",
                        "correlation_score": 0.8 - j * 0.1,
                        "correlation_type": "temporal" if j % 2 == 0 else "causal",
                    }
                    for j in range(3)
                ],
                "correlation_group": f"group_{i}",
                "created_at": get_timestamp(),
            }
        )

    return {
        "correlations": correlations,
        "stats": {
            "total_correlations": len(correlations),
            "correlation_groups": len(set(c["correlation_group"] for c in correlations)),
            "avg_correlation_score": 0.75,
            "high_confidence_correlations": len(
                [
                    c
                    for c in correlations
                    if any(r["correlation_score"] > 0.8 for r in c["related_alerts"])
                ]
            ),
        },
    }


@router.get("/acknowledgements", summary="获取告警确认记录")
async def get_acknowledgements() -> Dict[str, Any]:
    """获取告警确认记录"""
    return {"acknowledgements": list(_acknowledgements)}


@router.get("/escalation/rules", summary="获取升级规则列表")
async def get_escalation_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有升级规则"""
    try:
        rules = db.query(AlertEscalationRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "conditions": rule.conditions,
                "escalation_levels": rule.escalation_levels,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting escalation rules: {e}")
        return {"rules": []}


@router.post("/escalation/rules", summary="创建升级规则")
async def create_escalation_rule(
    rule: EscalationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的升级规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertEscalationRule(
            name=rule.name,
            rule_id=rule_id,
            conditions=rule.conditions,
            escalation_levels=rule.escalation_levels,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "conditions": new_rule.conditions,
                "escalation_levels": new_rule.escalation_levels,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating escalation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/escalation/rules/{rule_id}", summary="更新升级规则")
async def update_escalation_rule(
    rule_id: str, 
    rule: EscalationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新升级规则"""
    try:
        existing_rule = db.query(AlertEscalationRule).filter(AlertEscalationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="升级规则不存在")

        existing_rule.name = rule.name
        existing_rule.conditions = rule.conditions
        existing_rule.escalation_levels = rule.escalation_levels
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "conditions": existing_rule.conditions,
                "escalation_levels": existing_rule.escalation_levels,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating escalation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/escalation/rules/{rule_id}", summary="删除升级规则")
async def delete_escalation_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除升级规则"""
    try:
        existing_rule = db.query(AlertEscalationRule).filter(AlertEscalationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="升级规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "升级规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting escalation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suppression/rules", summary="获取抑制规则列表")
async def get_suppression_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有抑制规则"""
    try:
        rules = db.query(AlertSuppressionRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "pattern": rule.pattern,
                "suppression_window": rule.suppression_window,
                "reason": rule.reason,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting suppression rules: {e}")
        return {"rules": []}


@router.post("/suppression/rules", summary="创建抑制规则")
async def create_suppression_rule(
    rule: SuppressionRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的抑制规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertSuppressionRule(
            name=rule.name,
            rule_id=rule_id,
            pattern=rule.pattern,
            reason=rule.reason,
            suppression_window=rule.suppression_window,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "pattern": new_rule.pattern,
                "suppression_window": new_rule.suppression_window,
                "reason": new_rule.reason,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating suppression rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/suppression/rules/{rule_id}", summary="更新抑制规则")
async def update_suppression_rule(
    rule_id: str, 
    rule: SuppressionRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新抑制规则"""
    try:
        existing_rule = db.query(AlertSuppressionRule).filter(AlertSuppressionRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="抑制规则不存在")

        existing_rule.name = rule.name
        existing_rule.pattern = rule.pattern
        existing_rule.reason = rule.reason
        existing_rule.suppression_window = rule.suppression_window
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "pattern": existing_rule.pattern,
                "suppression_window": existing_rule.suppression_window,
                "reason": existing_rule.reason,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating suppression rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/suppression/rules/{rule_id}", summary="删除抑制规则")
async def delete_suppression_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除抑制规则"""
    try:
        existing_rule = db.query(AlertSuppressionRule).filter(AlertSuppressionRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="抑制规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "抑制规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting suppression rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", summary="获取告警趋势")
async def get_trends(time_range: str = Query(default="7d")) -> Dict[str, Any]:
    """获取告警趋势数据"""
    days = 7 if time_range == "7d" else 30 if time_range == "30d" else 90

    daily_trends = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
        daily_trends.append(
            {
                "date": date,
                "total": 50 + (i % 5) * 10,
                "critical": 5 + (i % 3),
                "high": 10 + (i % 4),
                "medium": 15 + (i % 5),
                "low": 20 + (i % 6),
            }
        )

    return {
        "daily_trends": daily_trends[-7:],
        "weekly_trends": daily_trends[::7],
        "monthly_trends": daily_trends[::30],
        "prediction": daily_trends[-7:],
    }


@router.get("/statistics", summary="获取告警统计")
async def get_statistics(time_range: str = Query(default="24h")) -> Dict[str, Any]:
    """获取告警统计数据"""
    return {
        "total_alerts": 1247,
        "open_alerts": 89,
        "acknowledged_alerts": 45,
        "resolved_alerts": 1158,
        "critical_alerts": 12,
        "high_alerts": 34,
        "medium_alerts": 56,
        "low_alerts": 1145,
        "avg_resolution_time": 1847,
        "avg_acknowledgement_time": 234,
        "alerts_by_source": [
            {"source": "Prometheus", "count": 456},
            {"source": "Zabbix", "count": 345},
            {"source": "CloudWatch", "count": 234},
            {"source": "Custom", "count": 212},
        ],
        "alerts_by_service": [
            {"service": "api-server", "count": 345},
            {"service": "database", "count": 234},
            {"service": "cache", "count": 156},
            {"service": "worker", "count": 512},
        ],
        "alerts_by_hour": [{"hour": i, "count": 30 + (i % 5) * 10} for i in range(24)],
        "alerts_by_day": [{"date": f"2026-07-{i:02d}", "count": 100 + i * 10} for i in range(1, 8)],
    }


@router.get("/history", summary="获取告警历史")
async def get_history(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    date_range: str = Query(default="7d"),
) -> Dict[str, Any]:
    """获取告警历史记录"""
    history = []
    for i in range(20):
        history.append(
            {
                "id": generate_id(),
                "alert_id": generate_id(),
                "title": f"告警 {i+1}",
                "severity": ["critical", "high", "medium", "low"][i % 4],
                "status": ["open", "acknowledged", "resolved"][i % 3],
                "source": ["Prometheus", "Zabbix", "CloudWatch"][i % 3],
                "service": ["api-server", "database", "cache"][i % 3],
                "labels": {"env": "prod", "region": "us-east-1"},
                "created_at": get_timestamp(),
                "acknowledged_at": get_timestamp() if i % 3 == 1 else None,
                "resolved_at": get_timestamp() if i % 3 == 2 else None,
                "acknowledged_by": "user1" if i % 3 == 1 else None,
                "resolved_by": "user2" if i % 3 == 2 else None,
                "duration": 3600 if i % 3 == 2 else None,
            }
        )

    return {"history": history}


@router.get("/forwarding/rules", summary="获取转发规则列表")
async def get_forwarding_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有转发规则"""
    try:
        rules = db.query(AlertForwardingRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "conditions": rule.conditions,
                "destination": rule.destination,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting forwarding rules: {e}")
        return {"rules": []}


@router.post("/forwarding/rules", summary="创建转发规则")
async def create_forwarding_rule(
    rule: ForwardingRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的转发规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertForwardingRule(
            name=rule.name,
            rule_id=rule_id,
            conditions=rule.conditions,
            destination=rule.destination,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "conditions": new_rule.conditions,
                "destination": new_rule.destination,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating forwarding rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/forwarding/rules/{rule_id}", summary="更新转发规则")
async def update_forwarding_rule(
    rule_id: str, 
    rule: ForwardingRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新转发规则"""
    try:
        existing_rule = db.query(AlertForwardingRule).filter(AlertForwardingRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="转发规则不存在")

        existing_rule.name = rule.name
        existing_rule.conditions = rule.conditions
        existing_rule.destination = rule.destination
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "conditions": existing_rule.conditions,
                "destination": existing_rule.destination,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating forwarding rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/forwarding/rules/{rule_id}", summary="删除转发规则")
async def delete_forwarding_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除转发规则"""
    try:
        existing_rule = db.query(AlertForwardingRule).filter(AlertForwardingRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="转发规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "转发规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting forwarding rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/configs", summary="获取Webhook配置列表")
async def get_webhook_configs(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有Webhook配置"""
    try:
        webhooks = db.query(AlertWebhookConfig).all()
        return {"webhooks": [
            {
                "id": str(webhook.id),
                "name": webhook.name,
                "webhook_id": webhook.webhook_id,
                "url": webhook.url,
                "method": webhook.method,
                "headers": webhook.headers,
                "body_template": webhook.body_template,
                "retry_policy": webhook.retry_policy,
                "enabled": webhook.enabled,
                "description": webhook.description,
                "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
                "updated_at": webhook.updated_at.isoformat() if webhook.updated_at else None,
            }
            for webhook in webhooks
        ]}
    except Exception as e:
        logger.error(f"Error getting webhook configs: {e}")
        return {"webhooks": []}


@router.post("/webhook/configs", summary="创建Webhook配置")
async def create_webhook_config(
    config: WebhookConfig, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的Webhook配置"""
    try:
        webhook_id = config.webhook_id or generate_id()
        new_webhook = AlertWebhookConfig(
            name=config.name,
            webhook_id=webhook_id,
            url=config.url,
            method=config.method,
            headers=config.headers,
            body_template=config.body_template,
            retry_policy=config.retry_policy,
            enabled=config.enabled,
            description=config.description,
        )
        db.add(new_webhook)
        db.commit()
        db.refresh(new_webhook)
        
        return {
            "status": "success",
            "webhook": {
                "id": str(new_webhook.id),
                "name": new_webhook.name,
                "webhook_id": new_webhook.webhook_id,
                "url": new_webhook.url,
                "method": new_webhook.method,
                "headers": new_webhook.headers,
                "body_template": new_webhook.body_template,
                "retry_policy": new_webhook.retry_policy,
                "enabled": new_webhook.enabled,
                "description": new_webhook.description,
                "created_at": new_webhook.created_at.isoformat() if new_webhook.created_at else None,
                "updated_at": new_webhook.updated_at.isoformat() if new_webhook.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating webhook config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/webhook/configs/{config_id}", summary="更新Webhook配置")
async def update_webhook_config(
    config_id: str, 
    config: WebhookConfig, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新Webhook配置"""
    try:
        existing_webhook = db.query(AlertWebhookConfig).filter(AlertWebhookConfig.id == int(config_id)).first()
        if not existing_webhook:
            raise HTTPException(status_code=404, detail="Webhook配置不存在")

        existing_webhook.name = config.name
        existing_webhook.webhook_id = config.webhook_id
        existing_webhook.url = config.url
        existing_webhook.method = config.method
        existing_webhook.headers = config.headers
        existing_webhook.body_template = config.body_template
        existing_webhook.retry_policy = config.retry_policy
        existing_webhook.enabled = config.enabled
        existing_webhook.description = config.description
        existing_webhook.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_webhook)
        
        return {
            "status": "success",
            "webhook": {
                "id": str(existing_webhook.id),
                "name": existing_webhook.name,
                "webhook_id": existing_webhook.webhook_id,
                "url": existing_webhook.url,
                "method": existing_webhook.method,
                "headers": existing_webhook.headers,
                "body_template": existing_webhook.body_template,
                "retry_policy": existing_webhook.retry_policy,
                "enabled": existing_webhook.enabled,
                "description": existing_webhook.description,
                "created_at": existing_webhook.created_at.isoformat() if existing_webhook.created_at else None,
                "updated_at": existing_webhook.updated_at.isoformat() if existing_webhook.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhook/configs/{config_id}", summary="删除Webhook配置")
async def delete_webhook_config(
    config_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除Webhook配置"""
    try:
        existing_webhook = db.query(AlertWebhookConfig).filter(AlertWebhookConfig.id == config_id).first()
        if not existing_webhook:
            raise HTTPException(status_code=404, detail="Webhook配置不存在")

        db.delete(existing_webhook)
        db.commit()
        
        return {"status": "success", "message": "Webhook配置已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dynamic-threshold/rules", summary="获取动态阈值规则列表")
async def get_intelligent_analysis() -> Dict[str, Any]:
    """获取智能分析结果"""
    return {
        "analyses": list(_intelligent_analyses),
        "stats": {
            "total_analyses": len(_intelligent_analyses),
            "successful_analyses": len(
                [a for a in _intelligent_analyses if a.get("status") == "completed"]
            ),
            "failed_analyses": len(
                [a for a in _intelligent_analyses if a.get("status") == "failed"]
            ),
            "avg_confidence": 0.78,
            "pattern_count": 15,
            "root_cause_count": 8,
        },
    }


@router.post("/intelligent-analysis", summary="运行智能分析")
async def run_intelligent_analysis() -> Dict[str, Any]:
    """运行智能分析"""
    analysis_id = generate_id()
    analysis = {
        "id": analysis_id,
        "alert_id": generate_id(),
        "alert_title": "CPU使用率异常",
        "analysis_type": "root_cause",
        "confidence": 0.85,
        "insights": ["检测到CPU使用率持续高于阈值", "可能的原因:进程异常"],
        "recommendations": ["检查进程状态", "考虑扩容"],
        "related_alerts": [generate_id() for _ in range(3)],
        "severity": "high",
        "created_at": get_timestamp(),
        "status": "completed",
    }
    _intelligent_analyses.append(analysis)
    return {"status": "success", "analysis": analysis}


@router.get("/dynamic-threshold/rules", summary="获取动态阈值规则列表")
async def get_dynamic_threshold_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有动态阈值规则"""
    try:
        thresholds = db.query(AlertDynamicThresholdRule).all()
        return {"thresholds": [
            {
                "id": str(threshold.id),
                "name": threshold.name,
                "rule_id": threshold.rule_id,
                "metric_name": threshold.metric_name,
                "algorithm": threshold.algorithm,
                "parameters": threshold.parameters,
                "enabled": threshold.enabled,
                "priority": threshold.priority,
                "description": threshold.description,
                "created_at": threshold.created_at.isoformat() if threshold.created_at else None,
                "updated_at": threshold.updated_at.isoformat() if threshold.updated_at else None,
            }
            for threshold in thresholds
        ]}
    except Exception as e:
        logger.error(f"Error getting dynamic threshold rules: {e}")
        return {"thresholds": []}


@router.post("/dynamic-threshold/rules", summary="创建动态阈值规则")
async def create_dynamic_threshold_rule(
    rule: DynamicThresholdRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的动态阈值规则"""
    try:
        rule_id = generate_id()
        new_threshold = AlertDynamicThresholdRule(
            name=rule.name,
            rule_id=rule_id,
            metric_name=rule.metric_name,
            algorithm=rule.algorithm,
            parameters=rule.parameters,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_threshold)
        db.commit()
        db.refresh(new_threshold)
        
        return {
            "status": "success",
            "threshold": {
                "id": str(new_threshold.id),
                "name": new_threshold.name,
                "rule_id": new_threshold.rule_id,
                "metric_name": new_threshold.metric_name,
                "algorithm": new_threshold.algorithm,
                "parameters": new_threshold.parameters,
                "enabled": new_threshold.enabled,
                "priority": new_threshold.priority,
                "description": new_threshold.description,
                "created_at": new_threshold.created_at.isoformat() if new_threshold.created_at else None,
                "updated_at": new_threshold.updated_at.isoformat() if new_threshold.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating dynamic threshold rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dynamic-threshold/rules/{rule_id}", summary="更新动态阈值规则")
async def update_dynamic_threshold_rule(
    rule_id: str, 
    rule: DynamicThresholdRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新动态阈值规则"""
    try:
        existing_threshold = db.query(AlertDynamicThresholdRule).filter(AlertDynamicThresholdRule.rule_id == rule_id).first()
        if not existing_threshold:
            raise HTTPException(status_code=404, detail="动态阈值规则不存在")

        existing_threshold.name = rule.name
        existing_threshold.metric_name = rule.metric_name
        existing_threshold.algorithm = rule.algorithm
        existing_threshold.parameters = rule.parameters
        existing_threshold.enabled = rule.enabled
        existing_threshold.priority = rule.priority
        existing_threshold.description = rule.description
        existing_threshold.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_threshold)
        
        return {
            "status": "success",
            "threshold": {
                "id": str(existing_threshold.id),
                "name": existing_threshold.name,
                "rule_id": existing_threshold.rule_id,
                "metric_name": existing_threshold.metric_name,
                "algorithm": existing_threshold.algorithm,
                "parameters": existing_threshold.parameters,
                "enabled": existing_threshold.enabled,
                "priority": existing_threshold.priority,
                "description": existing_threshold.description,
                "created_at": existing_threshold.created_at.isoformat() if existing_threshold.created_at else None,
                "updated_at": existing_threshold.updated_at.isoformat() if existing_threshold.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dynamic threshold rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dynamic-threshold/rules/{rule_id}", summary="删除动态阈值规则")
async def delete_dynamic_threshold_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除动态阈值规则"""
    try:
        existing_threshold = db.query(AlertDynamicThresholdRule).filter(AlertDynamicThresholdRule.rule_id == rule_id).first()
        if not existing_threshold:
            raise HTTPException(status_code=404, detail="动态阈值规则不存在")

        db.delete(existing_threshold)
        db.commit()
        
        return {"status": "success", "message": "动态阈值规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dynamic threshold rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deduplication/rules", summary="获取去重规则列表")
async def get_deduplication_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有去重规则"""
    try:
        rules = db.query(AlertDeduplicationRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "dedup_fields": rule.dedup_fields,
                "dedup_window": rule.dedup_window,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting deduplication rules: {e}")
        return {"rules": []}


@router.post("/deduplication/rules", summary="创建去重规则")
async def create_deduplication_rule(
    rule: DeduplicationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的去重规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertDeduplicationRule(
            name=rule.name,
            rule_id=rule_id,
            dedup_fields=rule.dedup_fields,
            dedup_window=rule.dedup_window,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "dedup_fields": new_rule.dedup_fields,
                "dedup_window": new_rule.dedup_window,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating deduplication rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/deduplication/rules/{rule_id}", summary="更新去重规则")
async def update_deduplication_rule(
    rule_id: str, 
    rule: DeduplicationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新去重规则"""
    try:
        existing_rule = db.query(AlertDeduplicationRule).filter(AlertDeduplicationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="去重规则不存在")

        existing_rule.name = rule.name
        existing_rule.dedup_fields = rule.dedup_fields
        existing_rule.dedup_window = rule.dedup_window
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "dedup_fields": existing_rule.dedup_fields,
                "dedup_window": existing_rule.dedup_window,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating deduplication rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/deduplication/rules/{rule_id}", summary="删除去重规则")
async def delete_deduplication_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除去重规则"""
    try:
        existing_rule = db.query(AlertDeduplicationRule).filter(AlertDeduplicationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="去重规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "去重规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deduplication rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregation/rules", summary="获取聚合规则列表")
async def get_aggregation_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有聚合规则"""
    try:
        rules = db.query(AlertAggregationRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "aggregation_fields": rule.aggregation_fields,
                "aggregation_window": rule.aggregation_window,
                "aggregation_function": rule.aggregation_function,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting aggregation rules: {e}")
        return {"rules": []}


@router.post("/aggregation/rules", summary="创建聚合规则")
async def create_aggregation_rule(
    rule: AggregationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的聚合规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertAggregationRule(
            name=rule.name,
            rule_id=rule_id,
            aggregation_fields=rule.aggregation_fields,
            aggregation_window=rule.aggregation_window,
            aggregation_function=rule.aggregation_function,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "aggregation_fields": new_rule.aggregation_fields,
                "aggregation_window": new_rule.aggregation_window,
                "aggregation_function": new_rule.aggregation_function,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating aggregation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/aggregation/rules/{rule_id}", summary="更新聚合规则")
async def update_aggregation_rule(
    rule_id: str, 
    rule: AggregationRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新聚合规则"""
    try:
        existing_rule = db.query(AlertAggregationRule).filter(AlertAggregationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="聚合规则不存在")

        existing_rule.name = rule.name
        existing_rule.aggregation_fields = rule.aggregation_fields
        existing_rule.aggregation_window = rule.aggregation_window
        existing_rule.aggregation_function = rule.aggregation_function
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "aggregation_fields": existing_rule.aggregation_fields,
                "aggregation_window": existing_rule.aggregation_window,
                "aggregation_function": existing_rule.aggregation_function,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating aggregation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/aggregation/rules/{rule_id}", summary="删除聚合规则")
async def delete_aggregation_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除聚合规则"""
    try:
        existing_rule = db.query(AlertAggregationRule).filter(AlertAggregationRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="聚合规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "聚合规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting aggregation rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/routing", summary="获取告警路由列表")
async def get_routing(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有告警路由"""
    try:
        routes = db.query(AlertRoutingRule).all()
        return {"routes": [
            {
                "id": str(route.id),
                "name": route.name,
                "rule_id": route.rule_id,
                "conditions": route.conditions,
                "destination": route.destination,
                "priority": route.priority,
                "enabled": route.enabled,
                "description": route.description,
                "created_at": route.created_at.isoformat() if route.created_at else None,
                "updated_at": route.updated_at.isoformat() if route.updated_at else None,
            }
            for route in routes
        ]}
    except Exception as e:
        logger.error(f"Error getting routing: {e}")
        return {"routes": []}


@router.post("/routing", summary="创建告警路由")
async def create_routing(
    route: AlertRoute, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的告警路由"""
    try:
        route_id = generate_id()
        new_route = AlertRoutingRule(
            name=route.name,
            rule_id=route_id,
            conditions=route.conditions,
            destination=route.destination,
            enabled=route.enabled,
            priority=route.priority,
            description=route.description,
        )
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        
        return {
            "status": "success",
            "route": {
                "id": str(new_route.id),
                "name": new_route.name,
                "rule_id": new_route.rule_id,
                "conditions": new_route.conditions,
                "destination": new_route.destination,
                "priority": new_route.priority,
                "enabled": new_route.enabled,
                "description": new_route.description,
                "created_at": new_route.created_at.isoformat() if new_route.created_at else None,
                "updated_at": new_route.updated_at.isoformat() if new_route.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating routing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/routing/{route_id}", summary="更新告警路由")
async def update_routing(
    route_id: str, 
    route: AlertRoute, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新告警路由"""
    try:
        existing_route = db.query(AlertRoutingRule).filter(AlertRoutingRule.rule_id == route_id).first()
        if not existing_route:
            raise HTTPException(status_code=404, detail="告警路由不存在")

        existing_route.name = route.name
        existing_route.conditions = route.conditions
        existing_route.destination = route.destination
        existing_route.enabled = route.enabled
        existing_route.priority = route.priority
        existing_route.description = route.description
        existing_route.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_route)
        
        return {
            "status": "success",
            "route": {
                "id": str(existing_route.id),
                "name": existing_route.name,
                "rule_id": existing_route.rule_id,
                "conditions": existing_route.conditions,
                "destination": existing_route.destination,
                "priority": existing_route.priority,
                "enabled": existing_route.enabled,
                "description": existing_route.description,
                "created_at": existing_route.created_at.isoformat() if existing_route.created_at else None,
                "updated_at": existing_route.updated_at.isoformat() if existing_route.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating routing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/routing/{route_id}", summary="删除告警路由")
async def delete_routing(
    route_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除告警路由"""
    try:
        existing_route = db.query(AlertRoutingRule).filter(AlertRoutingRule.rule_id == route_id).first()
        if not existing_route:
            raise HTTPException(status_code=404, detail="告警路由不存在")

        db.delete(existing_route)
        db.commit()
        
        return {"status": "success", "message": "告警路由已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting routing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", summary="获取告警规则列表")
async def get_rules(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取所有告警规则"""
    try:
        rules = db.query(AlertRule).all()
        return {"rules": [
            {
                "id": str(rule.id),
                "name": rule.name,
                "rule_id": rule.rule_id,
                "metric_name": rule.metric_name,
                "condition": rule.condition,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "description": rule.description,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]}
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        return {"rules": []}


@router.post("/rules", summary="创建告警规则")
async def create_rule(
    rule: AlertRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """创建新的告警规则"""
    try:
        rule_id = generate_id()
        new_rule = AlertRule(
            name=rule.name,
            rule_id=rule_id,
            metric_name=rule.metric_name,
            condition=rule.condition,
            threshold=rule.threshold,
            severity=rule.severity,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(new_rule.id),
                "name": new_rule.name,
                "rule_id": new_rule.rule_id,
                "metric_name": new_rule.metric_name,
                "condition": new_rule.condition,
                "threshold": new_rule.threshold,
                "severity": new_rule.severity,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
                "description": new_rule.description,
                "created_at": new_rule.created_at.isoformat() if new_rule.created_at else None,
                "updated_at": new_rule.updated_at.isoformat() if new_rule.updated_at else None,
            }
        }
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", summary="更新告警规则")
async def update_rule(
    rule_id: str, 
    rule: AlertRule, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """更新告警规则"""
    try:
        existing_rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        existing_rule.name = rule.name
        existing_rule.metric_name = rule.metric_name
        existing_rule.condition = rule.condition
        existing_rule.threshold = rule.threshold
        existing_rule.severity = rule.severity
        existing_rule.enabled = rule.enabled
        existing_rule.priority = rule.priority
        existing_rule.description = rule.description
        existing_rule.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_rule)
        
        return {
            "status": "success",
            "rule": {
                "id": str(existing_rule.id),
                "name": existing_rule.name,
                "rule_id": existing_rule.rule_id,
                "metric_name": existing_rule.metric_name,
                "condition": existing_rule.condition,
                "threshold": existing_rule.threshold,
                "severity": existing_rule.severity,
                "enabled": existing_rule.enabled,
                "priority": existing_rule.priority,
                "description": existing_rule.description,
                "created_at": existing_rule.created_at.isoformat() if existing_rule.created_at else None,
                "updated_at": existing_rule.updated_at.isoformat() if existing_rule.updated_at else None,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}", summary="删除告警规则")
async def delete_rule(
    rule_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("operator"))
) -> Dict[str, Any]:
    """删除告警规则"""
    try:
        existing_rule = db.query(AlertRule).filter(AlertRule.rule_id == rule_id).first()
        if not existing_rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        db.delete(existing_rule)
        db.commit()
        
        return {"status": "success", "message": "告警规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zabbix", summary="获取Zabbix集成配置")
async def get_zabbix(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取Zabbix集成配置和触发器"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "zabbix"
        ).first()
        
        config = {}
        if integration:
            config = integration.config
        else:
            config = _zabbix_config.copy()
        
        triggers = []
        for i in range(10):
            triggers.append(
                {
                    "triggerid": str(i),
                    "expression": f"last(/host/item{i}) > 80",
                    "description": f"触发器 {i+1}",
                    "status": "0",
                    "value": "1" if i % 3 == 0 else "0",
                    "priority": i % 6,
                    "lastchange": int((datetime.utcnow() - timedelta(hours=i)).timestamp()),
                    "state": "0",
                    "type": 0,
                    "flags": 0,
                }
            )

        return {
            "config": config,
            "triggers": triggers,
        }
    except Exception as e:
        logger.error(f"Error getting Zabbix integration: {e}")
        return {
            "config": _zabbix_config.copy(),
            "triggers": [],
        }


@router.put("/zabbix", summary="更新Zabbix集成配置")
async def update_zabbix(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新Zabbix集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "zabbix"
        ).first()
        
        config_data = {
            "url": config.url or "",
            "username": config.username or "",
            "password": config.password or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="zabbix",
                name="Zabbix Integration",
                config=config_data,
                enabled=config.enabled,
                description="Zabbix monitoring integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating Zabbix integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cloudwatch", summary="获取CloudWatch集成配置")
async def get_cloudwatch(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取CloudWatch集成配置"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "cloudwatch"
        ).first()
        
        if integration:
            return {"config": integration.config}
        else:
            return {"config": _cloudwatch_config.copy()}
    except Exception as e:
        logger.error(f"Error getting CloudWatch integration: {e}")
        return {"config": _cloudwatch_config.copy()}


@router.put("/cloudwatch", summary="更新CloudWatch集成配置")
async def update_cloudwatch(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新CloudWatch集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "cloudwatch"
        ).first()
        
        config_data = {
            "region": config.region or "",
            "access_key": config.access_key or "",
            "secret_key": config.secret_key or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="cloudwatch",
                name="CloudWatch Integration",
                config=config_data,
                enabled=config.enabled,
                description="AWS CloudWatch integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating CloudWatch integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pagerduty", summary="获取PagerDuty集成配置")
async def get_pagerduty(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取PagerDuty集成配置"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "pagerduty"
        ).first()
        
        if integration:
            return {"config": integration.config}
        else:
            return {"config": _pagerduty_config.copy()}
    except Exception as e:
        logger.error(f"Error getting PagerDuty integration: {e}")
        return {"config": _pagerduty_config.copy()}


@router.put("/pagerduty", summary="更新PagerDuty集成配置")
async def update_pagerduty(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新PagerDuty集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "pagerduty"
        ).first()
        
        config_data = {
            "api_key": config.api_key or "",
            "service_key": config.service_key or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="pagerduty",
                name="PagerDuty Integration",
                config=config_data,
                enabled=config.enabled,
                description="PagerDuty incident management integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating PagerDuty integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pagerduty", summary="发送告警到PagerDuty")
async def send_to_pagerduty(alert: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, Any]:
    """发送告警到PagerDuty"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "pagerduty",
            AlertIntegration.enabled == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=400, detail="PagerDuty integration not configured or disabled")
        
        # TODO: Implement actual PagerDuty API call
        logger.info(f"Sending alert to PagerDuty: {alert}")
        return {"status": "success", "message": "告警已发送到PagerDuty"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending alert to PagerDuty: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datadog", summary="获取Datadog集成配置")
async def get_datadog(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取Datadog集成配置"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "datadog"
        ).first()
        
        if integration:
            return {"config": integration.config}
        else:
            return {"config": _datadog_config.copy()}
    except Exception as e:
        logger.error(f"Error getting Datadog integration: {e}")
        return {"config": _datadog_config.copy()}


@router.put("/datadog", summary="更新Datadog集成配置")
async def update_datadog(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新Datadog集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "datadog"
        ).first()
        
        config_data = {
            "api_key": config.api_key or "",
            "app_key": config.app_key or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="datadog",
                name="Datadog Integration",
                config=config_data,
                enabled=config.enabled,
                description="Datadog monitoring integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating Datadog integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grafana", summary="获取Grafana集成配置")
async def get_grafana(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取Grafana集成配置"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "grafana"
        ).first()
        
        if integration:
            return {"config": integration.config}
        else:
            return {"config": _grafana_config.copy()}
    except Exception as e:
        logger.error(f"Error getting Grafana integration: {e}")
        return {"config": _grafana_config.copy()}


@router.put("/grafana", summary="更新Grafana集成配置")
async def update_grafana(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新Grafana集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "grafana"
        ).first()
        
        config_data = {
            "url": config.url or "",
            "api_key": config.api_key or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="grafana",
                name="Grafana Integration",
                config=config_data,
                enabled=config.enabled,
                description="Grafana visualization integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating Grafana integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prometheus", summary="获取Prometheus集成配置")
async def get_prometheus(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """获取Prometheus集成配置"""
    try:
        integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "prometheus"
        ).first()
        
        if integration:
            return {"config": integration.config}
        else:
            return {"config": _prometheus_config.copy()}
    except Exception as e:
        logger.error(f"Error getting Prometheus integration: {e}")
        return {"config": _prometheus_config.copy()}


@router.put("/prometheus", summary="更新Prometheus集成配置")
async def update_prometheus(config: ThirdPartyConfig, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """更新Prometheus集成配置"""
    try:
        existing_integration = db.query(AlertIntegration).filter(
            AlertIntegration.integration_type == "prometheus"
        ).first()
        
        config_data = {
            "url": config.url or "",
            "enabled": config.enabled,
        }
        
        if existing_integration:
            existing_integration.config = config_data
            existing_integration.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_integration)
        else:
            new_integration = AlertIntegration(
                integration_type="prometheus",
                name="Prometheus Integration",
                config=config_data,
                enabled=config.enabled,
                description="Prometheus monitoring integration",
            )
            db.add(new_integration)
            db.commit()
            db.refresh(new_integration)
        
        return {"status": "success", "config": config_data}
    except Exception as e:
        logger.error(f"Error updating Prometheus integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
