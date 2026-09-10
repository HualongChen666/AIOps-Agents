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
from datetime import datetime, timedelta, timezone
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


def _query_backend(promql: str, start_time: datetime, end_time: datetime, step: int = 60) -> List[Dict[str, Any]]:
    """Query the configured metrics backend (VictoriaMetrics/Prometheus).

    Returns the real samples; an empty list is returned when the backend is
    unreachable or has no data (never fabricated data).
    """
    import requests

    from config import VICTORIAMETRICS_TIMEOUT, VICTORIAMETRICS_URL

    params = {
        "query": promql,
        "start": int(start_time.timestamp()),
        "end": int(end_time.timestamp()),
        "step": step,
    }
    try:
        response = requests.get(
            f"{VICTORIAMETRICS_URL.rstrip('/')}/api/v1/query_range",
            params=params,
            timeout=VICTORIAMETRICS_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.error(f"Metrics backend query failed for {promql}: {exc}")
        return []

    if payload.get("status") != "success":
        logger.warning(f"Metrics backend returned non-success for {promql}: {payload}")
        return []

    samples: List[Dict[str, Any]] = []
    for result in payload.get("data", {}).get("result", []) or []:
        for ts, value in result.get("values", []) or []:
            try:
                samples.append(
                    {
                        "timestamp": datetime.fromtimestamp(
                            int(ts), tz=timezone.utc
                        ).isoformat(),
                        "value": round(float(value), 4),
                    }
                )
            except (TypeError, ValueError):
                continue
    return samples


def fetch_metric_series(
    metric: str,
    start_time: datetime,
    end_time: datetime,
    service: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch a real metric time series from the metrics backend."""
    promql = f'{metric}{{service="{service}"}}' if service else metric
    return _query_backend(promql, start_time, end_time)


def fetch_metric_prediction(
    metric: str,
    start_time: datetime,
    end_time: datetime,
    horizon_seconds: int,
    service: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Forecast a metric with the backend's real ``predict_linear`` function."""
    selector = f'{metric}{{service="{service}"}}' if service else metric
    promql = f"predict_linear({selector}[1h], {int(horizon_seconds)})"
    return _query_backend(promql, start_time, end_time)


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
                data = fetch_metric_series("cpu_usage", start_time, end_time)
                series.append({
                    "name": "CPU使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#3b82f6"
                })
            elif metric == "memory_usage":
                data = fetch_metric_series("memory_usage", start_time, end_time)
                series.append({
                    "name": "内存使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#10b981"
                })
            elif metric == "disk_usage":
                data = fetch_metric_series("disk_usage", start_time, end_time)
                series.append({
                    "name": "磁盘使用率",
                    "data": data,
                    "unit": "%",
                    "color": "#f59e0b"
                })
            elif metric == "network_in":
                data = fetch_metric_series("network_in", start_time, end_time)
                series.append({
                    "name": "网络入流量",
                    "data": data,
                    "unit": "MB/s",
                    "color": "#8b5cf6"
                })
            elif metric == "network_out":
                data = fetch_metric_series("network_out", start_time, end_time)
                series.append({
                    "name": "网络出流量",
                    "data": data,
                    "unit": "MB/s",
                    "color": "#ec4899"
                })
            elif metric == "request_count":
                data = fetch_metric_series("request_count", start_time, end_time)
                series.append({
                    "name": "请求数量",
                    "data": data,
                    "unit": "req/s",
                    "color": "#06b6d4"
                })
            elif metric == "error_rate":
                data = fetch_metric_series("error_rate", start_time, end_time)
                series.append({
                    "name": "错误率",
                    "data": data,
                    "unit": "%",
                    "color": "#ef4444"
                })
            elif metric == "response_time":
                data = fetch_metric_series("response_time", start_time, end_time)
                series.append({
                    "name": "响应时间",
                    "data": data,
                    "unit": "ms",
                    "color": "#f97316"
                })
            else:
                # 未知指标：直接按指标名查询后端
                data = fetch_metric_series(metric, start_time, end_time)
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
        
        # 真实聚合：读取告警引擎的告警历史并按分组键统计
        from collections import Counter

        from core.alert_engine import alert_history

        def _normalise(raw: Any) -> str:
            value = getattr(raw, "value", raw)
            text = str(value).strip() if value is not None else ""
            return text or "unknown"

        def _alert_time(alert: Dict[str, Any]) -> Optional[datetime]:
            raw = alert.get("detected_at") or alert.get("metric_time") or alert.get("raw_time")
            if isinstance(raw, datetime):
                return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
            if isinstance(raw, str):
                try:
                    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        if group_by == "severity":
            def _key(alert: Dict[str, Any]) -> str:
                return _normalise(alert.get("level"))
        elif group_by == "category":
            def _key(alert: Dict[str, Any]) -> str:
                return _normalise(alert.get("category"))
        elif group_by == "source":
            def _key(alert: Dict[str, Any]) -> str:
                return _normalise(alert.get("source") or alert.get("platform"))
        else:
            def _key(alert: Dict[str, Any]) -> str:
                return _normalise(alert.get("alert_type") or alert.get("metric"))

        selected = []
        for alert in alert_history:
            if severity and _normalise(alert.get("level")).lower() != severity.lower():
                continue
            detected = _alert_time(alert)
            if detected is not None and not (start_time <= detected <= end_time):
                continue
            selected.append(alert)

        palette = ["#ef4444", "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6", "#6b7280"]
        counts = Counter(_key(alert) for alert in selected)
        data = [
            {"name": name, "value": count, "color": palette[i % len(palette)]}
            for i, (name, count) in enumerate(sorted(counts.items()))
        ]
        
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
        response_time_data = fetch_metric_series("response_time", start_time, end_time)
        throughput_data = fetch_metric_series("request_count", start_time, end_time)
        error_rate_data = fetch_metric_series("error_rate", start_time, end_time)
        concurrency_data = fetch_metric_series("concurrency", start_time, end_time)
        
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
        
        # 历史数据来自指标后端
        historical_data = fetch_metric_series(metric_name, start_time, end_time)

        # 趋势线 = 对真实历史数据做最小二乘拟合
        trend_data = _linear_trend(historical_data)

        # 预测数据 = 后端 predict_linear 的真实外推
        prediction_start = end_time
        prediction_end = end_time + timedelta(hours=prediction_hours)
        prediction_data = fetch_metric_prediction(
            metric_name, prediction_start, prediction_end, prediction_hours * 3600
        )

        # 异常点 = 真实数据上的 2σ 离群点
        anomalies = _detect_anomalies(historical_data)
        
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
            data = fetch_metric_series(
                metric_name, start_time, end_time, service=entity.strip()
            )
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

def _linear_trend(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Least-squares linear trend fitted on the real samples."""
    if len(points) < 2:
        return []
    values = [float(p["value"]) for p in points]
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        slope = 0.0
    else:
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom
    intercept = mean_y - slope * mean_x
    return [
        {"timestamp": point["timestamp"], "value": round(slope * i + intercept, 4)}
        for i, point in enumerate(points)
    ]


def _detect_anomalies(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flag samples deviating more than 2 standard deviations from the mean."""
    if len(points) < 3:
        return []
    values = [float(p["value"]) for p in points]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    stddev = variance ** 0.5
    if stddev == 0:
        return []
    anomalies = []
    for point in points:
        value = float(point["value"])
        if abs(value - mean) > 2 * stddev:
            anomalies.append(
                {
                    "timestamp": point["timestamp"],
                    "value": point["value"],
                    "type": "high" if value > mean else "low",
                }
            )
    return anomalies
