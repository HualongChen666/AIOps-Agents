# -*- coding: utf-8 -*-
"""Phase 1 Infrastructure Enhancement API Router

提供Phase 1基础设施增强功能的API接口
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import require_permission
from core.config_center import get_config_center
from core.database import get_db
from core.distributed_storage import get_distributed_storage_manager
from core.flink_stream_processor import FlinkJobConfig, FlinkJobType, get_flink_job_manager
from core.infrastructure_service import get_infrastructure_service
from core.kafka_stream_processor import get_kafka_processor
from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator
from core.monitoring_infrastructure import get_monitoring_infrastructure
from core.monitoring_system_integrator import get_monitoring_system_integrator
from core.rate_limiter import get_advanced_rate_limiter

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/infrastructure", tags=["Infrastructure"])

# Rate limiter instance
_rate_limiter = get_advanced_rate_limiter()


async def check_rate_limit_middleware(request: Request):
    """Rate limiting middleware for infrastructure endpoints"""
    client_id = request.client.host if request.client else "unknown"
    is_allowed, error_message = await _rate_limiter.check_rate_limit_advanced(
        key=client_id, limit=100, window=60, algorithm="sliding_window"
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_message or "Rate limit exceeded",
        )


class KafkaMessageRequest(BaseModel):
    """Kafka消息请求"""

    topic: str
    key: str
    value: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"topic": "example", "key": "example", "value": {}},
            "headers": "example",
        },
    }


class KafkaMessageResponse(BaseModel):
    """Kafka消息响应"""

    success: bool
    message: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"success": True, "message": "example"}},
    }


class FlinkJobRequest(BaseModel):
    """Flink作业请求"""

    job_name: str
    job_type: str
    parallelism: int = 2

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"job_name": "example", "job_type": "example", "parallelism": 0}
        },
    }


class FlinkJobResponse(BaseModel):
    """Flink作业响应"""

    job_name: str
    job_type: str
    status: str

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"job_name": "example", "job_type": "example", "status": "example"}
        },
    }


class ConfigItemRequest(BaseModel):
    """配置项请求"""

    key: str
    value: Any
    metadata: Optional[Dict[str, str]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"key": "example", "value": None, "metadata": "example"}},
    }


class ConfigItemResponse(BaseModel):
    """配置项响应"""

    key: str
    value: Any
    version: int

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"key": "example", "value": None, "version": 0}},
    }


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    kafka: bool
    flink: bool
    storage: bool
    config_center: bool
    monitoring: bool
    data_flow: bool

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "kafka": True,
                "flink": True,
                "storage": True,
                "config_center": True,
                "monitoring": True,
                "data_flow": True,
            }
        },
    }


class DataFlowStatsResponse(BaseModel):
    """数据流统计响应"""

    total_processed: int
    total_analyzed: int
    total_errors: int
    avg_processing_time_ms: float
    error_rate: float
    analysis_rate: float

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "total_processed": 0,
                "total_analyzed": 0,
                "total_errors": 0,
                "avg_processing_time_ms": 0.0,
                "error_rate": 0.0,
                "analysis_rate": 0.0,
            }
        },
    }


class MonitoringSummaryResponse(BaseModel):
    """监控摘要响应"""

    total_alerts: int
    active_alerts: int
    critical_alerts: int
    error_alerts: int
    warning_alerts: int
    total_dashboards: int

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "total_alerts": 0,
                "active_alerts": 0,
                "critical_alerts": 0,
                "error_alerts": 0,
                "warning_alerts": 0,
                "total_dashboards": 0,
            }
        },
    }


@router.post(
    "/kafka/send",
    response_model=KafkaMessageResponse,
    summary="发送Kafka消息",
    responses={
        (200): {
            "description": "消息发送结果",
            "content": {
                "application/json": {
                    "example": {"success": True, "message": "Message sent successfully"}
                }
            },
        },
        (500): {"description": "发送失败"},
    },
)
async def send_kafka_message(
    request: KafkaMessageRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "create")),
    __=Depends(check_rate_limit_middleware),
):
    """发送Kafka消息"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        result = infrastructure_service.kafka.send_message(
            topic=request.topic, key=request.key, value=request.value, headers=request.headers
        )
        return KafkaMessageResponse(
            success=result["success"], message=f"Message sent: {result['message_id']}"
        )
    except Exception as e:
        _logger.error(f"Error sending Kafka message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/kafka/status",
    summary="获取Kafka状态",
    responses={
        (200): {
            "description": "Kafka状态",
            "content": {
                "application/json": {
                    "example": {
                        "fallback_enabled": True,
                        "total_messages": 42,
                        "topics": ["metrics-topic", "logs-topic", "traces-topic", "alerts-topic"],
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def get_kafka_status(
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "read")),
    __=Depends(check_rate_limit_middleware),
):
    """获取Kafka状态（基于真实本地缓存/发送的消息）"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        return infrastructure_service.kafka.get_status()
    except Exception as e:
        _logger.error(f"Error getting Kafka status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/flink/job",
    response_model=FlinkJobResponse,
    summary="创建Flink作业",
    responses={
        (200): {
            "description": "作业创建结果",
            "content": {
                "application/json": {
                    "example": {
                        "job_name": "metrics-stream-job",
                        "job_type": "streaming",
                        "status": "created",
                    }
                }
            },
        },
        (500): {"description": "创建失败"},
    },
)
async def create_flink_job(
    request: FlinkJobRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "create")),
    __=Depends(check_rate_limit_middleware),
):
    """创建Flink作业"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        result = infrastructure_service.flink.create_job(
            job_name=request.job_name, job_type=request.job_type, parallelism=request.parallelism
        )
        return FlinkJobResponse(
            job_name=result["job_name"], job_type=result["job_type"], status=result["status"]
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid job_type: {request.job_type}")
    except Exception as e:
        _logger.error(f"Error creating Flink job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/flink/jobs",
    summary="列出Flink作业",
    responses={
        (200): {
            "description": "作业列表",
            "content": {
                "application/json": {
                    "example": {
                        "jobs": [
                            {
                                "job_name": "metrics-stream-job",
                                "job_type": "streaming",
                                "status": "running",
                            },
                            {
                                "job_name": "log-analysis-job",
                                "job_type": "batch",
                                "status": "finished",
                            },
                        ]
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def list_flink_jobs(
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "read")),
    __=Depends(check_rate_limit_middleware),
):
    """列出Flink作业"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        jobs = infrastructure_service.flink.list_jobs()
        return {"jobs": jobs}
    except Exception as e:
        _logger.error(f"Error listing Flink jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/storage/read-connection",
    summary="获取读连接信息",
    responses={(200): {"description": "读连接信息"}, (500): {"description": "获取失败"}},
)
async def get_read_connection():
    """获取读连接信息"""
    try:
        storage_manager = get_distributed_storage_manager()
        return storage_manager.get_read_connection_info()
    except Exception as e:
        _logger.error(f"Error getting read connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/storage/write-connection",
    summary="获取写连接信息",
    responses={(200): {"description": "写连接信息"}, (500): {"description": "获取失败"}},
)
async def get_write_connection():
    """获取写连接信息"""
    try:
        storage_manager = get_distributed_storage_manager()
        return storage_manager.get_write_connection_info()
    except Exception as e:
        _logger.error(f"Error getting write connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/storage/health",
    summary="获取存储健康状态",
    responses={(200): {"description": "存储健康状态"}, (500): {"description": "获取失败"}},
)
async def get_storage_health():
    """获取存储健康状态"""
    try:
        storage_manager = get_distributed_storage_manager()
        return storage_manager.health_check()
    except Exception as e:
        _logger.error(f"Error getting storage health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/config",
    response_model=ConfigItemResponse,
    summary="设置配置",
    responses={(200): {"description": "配置设置结果"}, (500): {"description": "设置失败"}},
)
async def set_config(
    request: ConfigItemRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "create")),
    __=Depends(check_rate_limit_middleware),
):
    """设置配置"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        result = infrastructure_service.config.set_config(
            key=request.key, value=request.value, metadata=request.metadata
        )
        return ConfigItemResponse(
            key=result["key"], value=result["value"], version=result["version"]
        )
    except Exception as e:
        _logger.error(f"Error setting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/config/{key}",
    summary="获取配置",
    responses={(200): {"description": "配置值"}, (500): {"description": "获取失败"}},
)
async def get_config(
    key: str,
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "read")),
    __=Depends(check_rate_limit_middleware),
):
    """获取配置"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        result = infrastructure_service.config.get_config(key)
        if not result:
            raise HTTPException(status_code=404, detail="Config not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/config",
    summary="获取所有配置",
    responses={(200): {"description": "所有配置"}, (500): {"description": "获取失败"}},
)
async def get_all_configs(
    db: Session = Depends(get_db),
    _=Depends(require_permission("infrastructure", "read")),
    __=Depends(check_rate_limit_middleware),
):
    """获取所有配置"""
    try:
        infrastructure_service = get_infrastructure_service(db)
        configs = infrastructure_service.config.get_all_configs()
        return {"configs": configs}
    except Exception as e:
        _logger.error(f"Error getting all configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/monitoring/status",
    summary="获取监控状态",
    responses={(200): {"description": "监控状态"}, (500): {"description": "获取失败"}},
)
async def get_monitoring_status():
    """获取监控状态"""
    try:
        monitoring = get_monitoring_infrastructure()
        return monitoring.get_monitoring_status()
    except Exception as e:
        _logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/monitoring/metrics",
    summary="记录指标",
    responses={(200): {"description": "记录成功"}, (500): {"description": "记录失败"}},
)
async def record_metric():
    """记录指标（简化版）"""
    try:
        monitoring = get_monitoring_infrastructure()
        monitoring.metrics_collector.increment_counter("api_metric_recorded")
        return {"success": True}
    except Exception as e:
        _logger.error(f"Error recording metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/data-flow/stats",
    response_model=DataFlowStatsResponse,
    summary="获取数据流统计",
    responses={(200): {"description": "数据流统计"}, (500): {"description": "获取失败"}},
)
async def get_data_flow_stats():
    """获取数据流统计"""
    try:
        data_flow = get_l1l2_data_flow_integrator()
        stats = data_flow.get_data_flow_stats()
        return DataFlowStatsResponse(**stats)
    except Exception as e:
        _logger.error(f"Error getting data flow stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/data-flow/start",
    summary="启动数据流",
    responses={(200): {"description": "启动成功"}, (500): {"description": "启动失败"}},
)
async def start_data_flow():
    """启动数据流"""
    try:
        data_flow = get_l1l2_data_flow_integrator()
        success = data_flow.start_data_flow()
        return {"success": success}
    except Exception as e:
        _logger.error(f"Error starting data flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/data-flow/stop",
    summary="停止数据流",
    responses={(200): {"description": "停止成功"}, (500): {"description": "停止失败"}},
)
async def stop_data_flow():
    """停止数据流"""
    try:
        data_flow = get_l1l2_data_flow_integrator()
        success = data_flow.stop_data_flow()
        return {"success": success}
    except Exception as e:
        _logger.error(f"Error stopping data flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/monitoring/summary",
    response_model=MonitoringSummaryResponse,
    summary="获取监控摘要",
    responses={(200): {"description": "监控摘要"}, (500): {"description": "获取失败"}},
)
async def get_monitoring_summary():
    """获取监控摘要"""
    try:
        monitoring_system = get_monitoring_system_integrator()
        summary = monitoring_system.get_monitoring_summary()
        return MonitoringSummaryResponse(**summary)
    except Exception as e:
        _logger.error(f"Error getting monitoring summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/alerts",
    summary="获取告警列表",
    responses={(200): {"description": "告警列表"}, (500): {"description": "获取失败"}},
)
async def get_alerts():
    """获取告警列表"""
    try:
        monitoring_system = get_monitoring_system_integrator()
        alerts = monitoring_system.get_active_alerts()
        return {"alerts": alerts}
    except Exception as e:
        _logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/alerts/{alert_id}/resolve",
    summary="解决告警",
    responses={(200): {"description": "解决成功"}, (500): {"description": "解决失败"}},
)
async def resolve_alert(alert_id: str):
    """解决告警"""
    try:
        monitoring_system = get_monitoring_system_integrator()
        monitoring_system.resolve_alert(alert_id)
        return {"success": True}
    except Exception as e:
        _logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="获取基础设施健康状态",
    responses={(200): {"description": "健康状态"}, (500): {"description": "获取失败"}},
)
async def get_infrastructure_health():
    """获取基础设施健康状态"""
    try:
        kafka_processor = get_kafka_processor()
        flink_manager = get_flink_job_manager()
        storage_manager = get_distributed_storage_manager()
        config_center = get_config_center()
        monitoring = get_monitoring_infrastructure()
        data_flow = get_l1l2_data_flow_integrator()

        def _is_healthy(obj: Any) -> bool:
            # 如果显式标记为 fallback，视为不健康；否则优先使用 _initialized/connected 等真实状态
            if getattr(obj, "fallback_enabled", False):
                return False
            for flag in ("_initialized", "connected", "initialized"):
                val = getattr(obj, flag, None)
                if val is not None:
                    return bool(val if not callable(val) else val())
            return True

        collector = getattr(monitoring, "metrics_collector", monitoring)

        return HealthCheckResponse(
            kafka=_is_healthy(kafka_processor),
            flink=_is_healthy(flink_manager),
            storage=_is_healthy(storage_manager),
            config_center=_is_healthy(config_center),
            monitoring=_is_healthy(collector),
            data_flow=_is_healthy(data_flow),
        )
    except Exception as e:
        _logger.error(f"Error getting infrastructure health: {e}")
        raise HTTPException(status_code=500, detail=str(e))
