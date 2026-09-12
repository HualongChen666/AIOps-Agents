# -*- coding: utf-8 -*-
"""监控基础设施升级适配器

升级OpenTelemetry采集器、Prometheus、Loki、Tempo等监控基础设施
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # noqa: F401
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: F401

try:
    import opentelemetry  # noqa: F401

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

try:
    import prometheus_client  # noqa: F401

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


_logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """指标类型"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """指标数据"""

    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LogData:
    """日志数据"""

    level: str
    message: str
    service: str
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TraceData:
    """链路数据"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    attributes: Dict[str, Any] = field(default_factory=dict)


class EnhancedMetricsCollector:
    """增强的指标采集器（真实落地：按标签序列累积并渲染 Prometheus 文本）。

    历史问题（已修复）：原 ``record_metric`` 仅 ``logging.info`` 后 ``return None``（空
    实现），指标不落地。现每次记录都写入真实的指标序列存储（counter 累加、gauge 覆盖、
    histogram 记录 sum/count），并可按 Prometheus 文本格式渲染与查询。
    """

    def __init__(self, max_history: int = 10000):
        """初始化指标采集器"""
        # name -> {(label_tuple): current_value}
        self._series: Dict[str, Dict[Any, float]] = {}
        self._series_meta: Dict[str, Dict[Any, Dict[str, str]]] = {}
        self._types: Dict[str, MetricType] = {}
        self._history: Dict[str, List[MetricData]] = {}
        self._max_history = max_history
        self._initialized = True

    def record_metric(self, metric_data: MetricData):
        """记录指标（真实累积到指标序列）。"""
        name = metric_data.name
        label_items = tuple(sorted(metric_data.labels.items()))
        series = self._series.setdefault(name, {})
        meta = self._series_meta.setdefault(name, {})
        self._types[name] = metric_data.metric_type

        if metric_data.metric_type == MetricType.COUNTER:
            series[label_items] = series.get(label_items, 0.0) + float(metric_data.value)
        elif metric_data.metric_type == MetricType.GAUGE:
            series[label_items] = float(metric_data.value)
        else:  # HISTOGRAM / SUMMARY -> track sum via _sum and count via _count keys
            sum_key = (label_items, "__sum__")
            cnt_key = (label_items, "__count__")
            series[sum_key] = series.get(sum_key, 0.0) + float(metric_data.value)
            series[cnt_key] = series.get(cnt_key, 0.0) + 1.0
        meta[label_items] = dict(metric_data.labels)

        history = self._history.setdefault(name, [])
        history.append(metric_data)
        if len(history) > self._max_history:
            del history[: len(history) - self._max_history]

    def render(self) -> bytes:
        """Render collected metrics in Prometheus exposition format (text)."""
        lines: List[str] = []
        for name, series in sorted(self._series.items()):
            mtype = self._types.get(name, MetricType.GAUGE)
            ptype = {MetricType.COUNTER: "counter", MetricType.GAUGE: "gauge"}.get(mtype, "summary")
            lines.append(f"# TYPE {name} {ptype}")
            if mtype in (MetricType.HISTOGRAM, MetricType.SUMMARY):
                agg: Dict[Any, Dict[str, float]] = {}
                for key, value in series.items():
                    label_items, kind = key
                    slot = agg.setdefault(label_items, {"__sum__": 0.0, "__count__": 0.0})
                    slot[kind if kind in ("__sum__", "__count__") else "__sum__"] = value
                for label_items, slot in agg.items():
                    labels = self._series_meta.get(name, {}).get(label_items, {})
                    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                    label_str = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{name}_sum{label_str} {slot['__sum__']}")
                    lines.append(f"{name}_count{label_str} {slot['__count__']}")
            else:
                for label_items, value in series.items():
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_items)
                    label_str = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{name}{label_str} {value}")
        return ("\n".join(lines) + "\n").encode("utf-8")

    def get_metrics(self) -> Dict[str, List[MetricData]]:
        """返回已采集的指标历史（真实数据）。"""
        return {name: list(items) for name, items in self._history.items()}

    def get_series(self) -> Dict[str, Dict[Any, float]]:
        """返回当前指标序列的实时值。"""
        return {name: dict(series) for name, series in self._series.items()}

    # 向后兼容旧名（返回真实数据，而非空 dict）
    def get_stub_metrics(self) -> Dict[str, List[MetricData]]:
        """兼容旧名：返回真实采集到的指标。"""
        return self.get_metrics()

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ):
        """增加计数器"""
        metric_data = MetricData(
            name=name, value=value, metric_type=MetricType.COUNTER, labels=labels or {}
        )
        self.record_metric(metric_data)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘"""
        metric_data = MetricData(
            name=name, value=value, metric_type=MetricType.GAUGE, labels=labels or {}
        )
        self.record_metric(metric_data)

    def record_timing(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None):
        """记录时间"""
        metric_data = MetricData(
            name=f"{name}_duration",
            value=duration_ms,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {},
        )
        self.record_metric(metric_data)


class EnhancedLogCollector:
    """增强的日志采集器（真实写入结构化日志并保留可查询历史）。"""

    def __init__(self, max_history: int = 10000):
        """初始化日志采集器"""
        self._logger = logging.getLogger("aiops.monitoring.infrastructure")
        self._history: List[LogData] = []
        self._max_history = max_history
        self._initialized = True

    def record_log(self, log_data: LogData):
        """记录日志（真实写入 logging 并保留历史）。"""
        level = getattr(logging, str(log_data.level).upper(), logging.INFO)
        self._logger.log(level, "[%s] %s", log_data.service, log_data.message)
        self._history.append(log_data)
        if len(self._history) > self._max_history:
            del self._history[: len(self._history) - self._max_history]

    def get_logs(self) -> List[LogData]:
        """返回已采集的日志（真实数据）。"""
        return list(self._history)

    def info(self, message: str, service: str, labels: Optional[Dict[str, str]] = None):
        """记录INFO日志"""
        log_data = LogData(level="INFO", message=message, service=service, labels=labels or {})
        self.record_log(log_data)

    def warning(self, message: str, service: str, labels: Optional[Dict[str, str]] = None):
        """记录WARNING日志"""
        log_data = LogData(level="WARNING", message=message, service=service, labels=labels or {})
        self.record_log(log_data)

    def error(self, message: str, service: str, labels: Optional[Dict[str, str]] = None):
        """记录ERROR日志"""
        log_data = LogData(level="ERROR", message=message, service=service, labels=labels or {})
        self.record_log(log_data)

    # 向后兼容旧名（返回真实数据，而非空 list）
    def get_stub_logs(self) -> List[LogData]:
        """兼容旧名：返回真实采集到的日志。"""
        return self.get_logs()


class EnhancedTraceCollector:
    """增强的链路采集器（真实生成 span id、记录耗时并保留历史）。"""

    def __init__(self, max_history: int = 10000):
        """初始化链路采集器"""
        import uuid

        self._uuid = uuid
        self._active_spans: Dict[str, TraceData] = {}
        self._history: List[TraceData] = []
        self._max_history = max_history
        self._initialized = True

    def start_span(self, operation_name: str, parent_span_id: Optional[str] = None) -> str:
        """开始span（真实生成 span_id 与 trace_id）"""
        span_id = self._uuid.uuid4().hex[:16]
        trace_id = self._uuid.uuid4().hex
        self._active_spans[span_id] = TraceData(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            end_time=None,
            status="running",
        )
        return span_id

    def end_span(
        self, span_id: str, status: str = "ok", attributes: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """结束span，返回真实耗时（毫秒）；未知 span 抛错（不静默）。"""
        span = self._active_spans.pop(span_id, None)
        if span is None:
            raise KeyError(f"unknown span_id: {span_id}")
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        if attributes:
            span.attributes.update(attributes)
        self._history.append(span)
        if len(self._history) > self._max_history:
            del self._history[: len(self._history) - self._max_history]
        return (span.end_time - span.start_time).total_seconds() * 1000

    def record_trace(self, trace_data: TraceData):
        """记录链路（真实写入历史）。"""
        self._history.append(trace_data)
        if len(self._history) > self._max_history:
            del self._history[: len(self._history) - self._max_history]

    def get_traces(self) -> Dict[str, TraceData]:
        """返回已记录的链路（真实数据）。"""
        return {t.span_id: t for t in self._history}

    # 向后兼容旧名（返回真实数据，而非空 dict）
    def get_stub_traces(self) -> Dict[str, TraceData]:
        """兼容旧名：返回真实记录的链路。"""
        return self.get_traces()


class MonitoringInfrastructure:
    """监控基础设施"""

    def __init__(self):
        """初始化监控基础设施"""
        self.metrics_collector = EnhancedMetricsCollector()
        self.log_collector = EnhancedLogCollector()
        self.trace_collector = EnhancedTraceCollector()
        self.prometheus_config = {
            "enabled": True,
            "scrape_interval": "15s",
            "evaluation_interval": "15s",
        }
        self.loki_config = {"enabled": True, "retention_period": "30d"}
        self.tempo_config = {"enabled": True, "retention_period": "7d"}

    def record_api_metric(self, endpoint: str, method: str, status_code: int, duration_ms: float):
        """记录API指标"""
        self.metrics_collector.increment_counter(
            "api_requests_total",
            labels={"endpoint": endpoint, "method": method, "status_code": str(status_code)},
        )
        self.metrics_collector.record_timing(
            "api_request_duration", duration_ms, labels={"endpoint": endpoint, "method": method}
        )

    def record_database_metric(self, operation: str, table: str, duration_ms: float, success: bool):
        """记录数据库指标"""
        self.metrics_collector.increment_counter(
            "database_operations_total",
            labels={"operation": operation, "table": table, "success": str(success)},
        )
        self.metrics_collector.record_timing(
            "database_operation_duration",
            duration_ms,
            labels={"operation": operation, "table": table},
        )

    def record_cache_metric(self, operation: str, hit: bool):
        """记录缓存指标"""
        self.metrics_collector.increment_counter(
            "cache_operations_total", labels={"operation": operation, "hit": str(hit)}
        )

    def record_system_metric(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """记录系统指标"""
        self.metrics_collector.set_gauge("system_cpu_percent", cpu_percent)
        self.metrics_collector.set_gauge("system_memory_percent", memory_percent)
        self.metrics_collector.set_gauge("system_disk_percent", disk_percent)

    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态（真实统计）。"""
        return {
            "metrics_recorded": sum(len(v) for v in self.metrics_collector.get_metrics().values()),
            "metric_series": sum(len(v) for v in self.metrics_collector.get_series().values()),
            "logs_recorded": len(self.log_collector.get_logs()),
            "traces_recorded": len(self.trace_collector.get_traces()),
            "active_spans": len(self.trace_collector._active_spans),
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "opentelemetry_available": OPENTELEMETRY_AVAILABLE,
            "prometheus_config": self.prometheus_config,
            "loki_config": self.loki_config,
            "tempo_config": self.tempo_config,
        }

    def render_prometheus_metrics(self) -> bytes:
        """Render collected metrics in Prometheus exposition format."""
        return self.metrics_collector.render()


# 全局实例
monitoring_infrastructure = MonitoringInfrastructure()


def get_monitoring_infrastructure() -> MonitoringInfrastructure:
    """获取监控基础设施实例"""
    return monitoring_infrastructure
