# -*- coding: utf-8 -*-
"""
Chart Data Aggregation Router Module
====================================

Provides API endpoints for chart data aggregation.
Supports time-series data aggregation, grouping, and filtering for monitoring charts.

Endpoints:
- GET /api/v1/charts/metrics - Get aggregated metrics data
- GET /api/v1/charts/alerts - Get aggregated alerts data
- GET /api/v1/charts/performance - Get aggregated performance data
- GET /api/v1/charts/trends - Get trend analysis data
- GET /api/v1/charts/compare - Get comparison data
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/charts", tags=["图表数据聚合"])


# ============================================================================
# Pydantic Models
# ============================================================================


class TimeRange(BaseModel):
    """时间范围模型"""

    start: Optional[datetime] = Field(None, description="开始时间")
    end: Optional[datetime] = Field(None, description="结束时间")
    preset: Optional[str] = Field(None, description="预设时间范围")


class AggregationConfig(BaseModel):
    """聚合配置模型"""

    interval: str = Field("1h", description="聚合间隔")
    aggregation: str = Field("avg", description="聚合函数")
    group_by: Optional[List[str]] = Field(None, description="分组字段")


class ChartDataPoint(BaseModel):
    """图表数据点模型"""

    timestamp: datetime
    value: float
    labels: Optional[Dict[str, str]] = None


class ChartSeries(BaseModel):
    """图表数据系列模型"""

    name: str
    data: List[ChartDataPoint]
    color: Optional[str] = None


class ChartResponse(BaseModel):
    """图表响应模型"""

    title: str
    series: List[ChartSeries]
    time_range: TimeRange
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Helper Functions
# ============================================================================


def generate_mock_data(
    start_time: datetime,
    end_time: datetime,
    interval_minutes: int = 60,
    base_value: float = 100.0,
    variance: float = 20.0,
) -> List[Dict[str, Any]]:
    """生成模拟数据"""
    import random

    data = []
    current_time = start_time
    while current_time <= end_time:
        value = base_value + random.uniform(-variance, variance)
        data.append({
            "timestamp": current_time.isoformat(),
            "value": round(value, 2),
        })
        current_time += timedelta(minutes=interval_minutes)
    return data


def get_time_range_from_preset(preset: str) -> tuple[datetime, datetime]:
    """根据预设获取时间范围"""
    end_time = datetime.utcnow()
    if preset == "1h":
        start_time = end_time - timedelta(hours=1)
    elif preset == "6h":
        start_time = end_time - timedelta(hours=6)
    elif preset == "24h":
        start_time = end_time - timedelta(hours=24)
    elif preset == "7d":
        start_time = end_time - timedelta(days=7)
    elif preset == "30d":
        start_time = end_time - timedelta(days=30)
    elif preset == "90d":
        start_time = end_time - timedelta(days=90)
    else:
        start_time = end_time - timedelta(hours=24)
    return start_time, end_time


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/metrics", summary="获取聚合指标数据")
async def get_aggregated_metrics(
    metric_names: Optional[str] = Query(None, description="指标名称，逗号分隔"),
    time_range: Optional[str] = Query("24h", description="时间范围预设"),
    interval: Optional[str] = Query("1h", description="聚合间隔"),
    aggregation: Optional[str] = Query("avg", description="聚合函数"),
    group_by: Optional[str] = Query(None, description="分组字段"),
) -> Dict[str, Any]:
    """
    获取聚合指标数据
    
    支持的指标：
    - cpu_usage: CPU使用率
    - memory_usage: 内存使用率
    - disk_usage: 磁盘使用率
    - network_in: 网络入流量
    - network_out: 网络出流量
    - request_count: 请求数量
    - error_rate: 错误率
    - response_time: 响应时间
    """
    try:
        start_time, end_time = get_time_range_from_preset(time_range)
        
        # 解析指标名称
        metrics = metric_names.split(",") if metric_names else ["cpu_usage", "memory_usage"]
        
        # 生成每个指标的数据
        series = []
        for metric in metrics:
            if metric == "cpu_usage":
                data = generate_mock_data(start_time, end_time, 60, 45.0, 15.0)
                series.append({
                    "name": "CPU使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#3b82f6"
                })
            elif metric == "memory_usage":
                data = generate_mock_data(start_time, end_time, 60, 65.0, 10.0)
                series.append({
                    "name": "内存使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#10b981"
                })
            elif metric == "disk_usage":
                data = generate_mock_data(start_time, end_time, 60, 55.0, 5.0)
                series.append({
                    "name": "磁盘使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#f59e0b"
                })
            elif metric == "network_in":
                data = generate_mock_data(start_time, end_time, 60, 100.0, 50.0)
                series.append({
                    "name": "网络入流量",
                    "data": data,
                    "unit": "MB/s",
                    "color": "#8b5cf6"
                })
            elif metric == "network_out":
                data = generate_mock_data(start_time, end_time, 60, 80.0, 40.0)
                series.append({
                    "name": "网络出流量",
                    "data": data,
                    "unit": "MB/s",
                    "color": "#ec4899"
                })
            elif metric == "request_count":
                data = generate_mock_data(start_time, end_time, 60, 500.0, 200.0)
                series.append({
                    "name": "请求数量",
                    "data": data,
                    "unit": "req/s",
                    "color": "#06b6d4"
                })
            elif metric == "error_rate":
                data = generate_mock_data(start_time, end_time, 60, 2.0, 1.5)
                series.append({
                    "name": "错误率",
                    "data": data,
                    "unit": "%",
                    "color": "#ef4444"
                })
            elif metric == "response_time":
                data = generate_mock_data(start_time, end_time, 60, 150.0, 50.0)
                series.append({
                    "name": "响应时间",
                    "data": data,
                    "unit": "ms",
                    "color": "#f97316"
                })
            else:
                # 默认生成通用数据
                data = generate_mock_data(start_time, end_time, 60, 100.0, 20.0)
                series.append({
                    "name": metric,
                    "data": data,
                    "unit": "",
                    "color": "#6b7280"
                })
        
        return {
            "title": "系统指标监控",
            "series": series,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "preset": time_range
            },
            "metadata": {
                "interval": interval,
                "aggregation": aggregation,
                "group_by": group_by
            }
        }
    except Exception as e:
        logger.error(f"获取聚合指标数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取聚合指标数据失败: {str(e)[:200]}")


@router.get("/alerts", summary="获取聚合告警数据")
async def get_aggregated_alerts(
    severity: Optional[str] = Query(None, description="告警级别过滤"),
    time_range: Optional[str] = Query("24h", description="时间范围预设"),
    group_by: Optional[str] = Query("severity", description="分组字段"),
) -> Dict[str, Any]:
    """
    获取聚合告警数据
    
    支持的分组：
    - severity: 按告警级别分组
    - category: 按告警类别分组
    - source: 按告警来源分组
    """
    try:
        start_time, end_time = get_time_range_from_preset(time_range)
        
        # 模拟告警数据
        if group_by == "severity":
            data = [
                {
                    "name": "Critical",
                    "value": 15,
                    "color": "#ef4444"
                },
                {
                    "name": "Warning",
                    "value": 42,
                    "color": "#f59e0b"
                },
                {
                    "name": "Info",
                    "value": 128,
                    "color": "#3b82f6"
                }
            ]
        elif group_by == "category":
            data = [
                {
                    "name": "系统",
                    "value": 45,
                    "color": "#3b82f6"
                },
                {
                    "name": "网络",
                    "value": 32,
                    "color": "#10b981"
                },
                {
                    "name": "应用",
                    "value": 78,
                    "color": "#f59e0b"
                },
                {
                    "name": "数据库",
                    "value": 30,
                    "color": "#8b5cf6"
                }
            ]
        elif group_by == "source":
            data = [
                {
                    "name": "Prometheus",
                    "value": 67,
                    "color": "#c73e3d"
                },
                {
                    "name": "Zabbix",
                    "value": 45,
                    "color": "#e55a32"
                },
                {
                    "name": "CloudWatch",
                    "value": 28,
                    "color": "#ff9900"
                },
                {
                    "name": "自定义",
                    "value": 45,
                    "color": "#6b7280"
                }
            ]
        else:
            data = []
        
        return {
            "title": "告警统计",
            "data": data,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "preset": time_range
            },
            "metadata": {
                "group_by": group_by,
                "severity_filter": severity
            }
        }
    except Exception as e:
        logger.error(f"获取聚合告警数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取聚合告警数据失败: {str(e)[:200]}")


@router.get("/performance", summary="获取聚合性能数据")
async def get_aggregated_performance(
    service_name: Optional[str] = Query(None, description="服务名称过滤"),
    time_range: Optional[str] = Query("24h", description="时间范围预设"),
    interval: Optional[str] = Query("1h", description="聚合间隔"),
) -> Dict[str, Any]:
    """
    获取聚合性能数据
    
    包含：
    - 响应时间
    - 吞吐量
    - 错误率
    - 并发数
    """
    try:
        start_time, end_time = get_time_range_from_preset(time_range)
        
        # 生成性能数据
        response_time_data = generate_mock_data(start_time, end_time, 60, 150.0, 50.0)
        throughput_data = generate_mock_data(start_time, end_time, 60, 500.0, 200.0)
        error_rate_data = generate_mock_data(start_time, end_time, 60, 2.0, 1.5)
        concurrency_data = generate_mock_data(start_time, end_time, 60, 50.0, 20.0)
        
        series = [
            {
                "name": "响应时间",
                "data": response_time_data,
                "unit": "ms",
                "color": "#3b82f6"
            },
            {
                "name": "吞吐量",
                "data": throughput_data,
                "unit": "req/s",
                "color": "#10b981"
            },
            {
                "name": "错误率",
                "data": error_rate_data,
                "unit": "%",
                "color": "#ef4444"
            },
            {
                "name": "并发数",
                "data": concurrency_data,
                "unit": "connections",
                "color": "#f59e0b"
            }
        ]
        
        return {
            "title": f"性能监控 - {service_name if service_name else '所有服务'}",
            "series": series,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "preset": time_range
            },
            "metadata": {
                "interval": interval,
                "service_name": service_name
            }
        }
    except Exception as e:
        logger.error(f"获取聚合性能数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取聚合性能数据失败: {str(e)[:200]}")


@router.get("/trends", summary="获取趋势分析数据")
async def get_trend_analysis(
    metric_name: str = Query(..., description="指标名称"),
    time_range: Optional[str] = Query("7d", description="时间范围预设"),
    prediction_hours: Optional[int] = Query(24, description="预测小时数"),
) -> Dict[str, Any]:
    """
    获取趋势分析数据
    
    包含：
    - 历史数据
    - 趋势线
    - 预测数据
    - 异常点
    """
    try:
        start_time, end_time = get_time_range_from_preset(time_range)
        
        # 生成历史数据
        historical_data = generate_mock_data(start_time, end_time, 60, 100.0, 30.0)
        
        # 生成趋势线（简化版）
        trend_data = []
        for i, point in enumerate(historical_data):
            trend_value = 100.0 + (i * 0.5)  # 简单的线性趋势
            trend_data.append({
                "timestamp": point["timestamp"],
                "value": round(trend_value, 2)
            })
        
        # 生成预测数据
        prediction_start = end_time
        prediction_end = end_time + timedelta(hours=prediction_hours)
        prediction_data = generate_mock_data(prediction_start, prediction_end, 60, 115.0, 15.0)
        
        # 识别异常点（简化版）
        anomalies = []
        for i, point in enumerate(historical_data):
            if point["value"] > 130.0 or point["value"] < 70.0:
                anomalies.append({
                    "timestamp": point["timestamp"],
                    "value": point["value"],
                    "type": "high" if point["value"] > 130.0 else "low"
                })
        
        return {
            "title": f"{metric_name} 趋势分析",
            "historical": historical_data,
            "trend": trend_data,
            "prediction": prediction_data,
            "anomalies": anomalies,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "preset": time_range
            },
            "metadata": {
                "metric_name": metric_name,
                "prediction_hours": prediction_hours
            }
        }
    except Exception as e:
        logger.error(f"获取趋势分析数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取趋势分析数据失败: {str(e)[:200]}")


@router.get("/compare", summary="获取对比数据")
async def get_comparison_data(
    metric_name: str = Query(..., description="指标名称"),
    entities: str = Query(..., description="对比实体，逗号分隔"),
    time_range: Optional[str] = Query("24h", description="时间范围预设"),
) -> Dict[str, Any]:
    """
    获取对比数据
    
    支持对比：
    - 不同服务
    - 不同环境
    - 不同时间段
    """
    try:
        start_time, end_time = get_time_range_from_preset(time_range)
        
        # 解析实体列表
        entity_list = entities.split(",") if entities else ["Entity A", "Entity B"]
        
        # 为每个实体生成数据
        series = []
        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
        
        for i, entity in enumerate(entity_list):
            base_value = 100.0 + (i * 20.0)  # 不同实体有不同的基准值
            data = generate_mock_data(start_time, end_time, 60, base_value, 25.0)
            series.append({
                "name": entity.strip(),
                "data": data,
                "color": colors[i % len(colors)]
            })
        
        return {
            "title": f"{metric_name} 对比分析",
            "series": series,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "preset": time_range
            },
            "metadata": {
                "metric_name": metric_name,
                "entities": entity_list
            }
        }
    except Exception as e:
        logger.error(f"获取对比数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取对比数据失败: {str(e)[:200]}")