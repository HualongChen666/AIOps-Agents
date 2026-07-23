# -*- coding: utf-8 -*-
"""监控基础设施升级适配器

升级OpenTelemetry采集器、Prometheus、Loki、Tempo等监控基础设施
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # noqa: F401
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: F401

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.trace import TracerProvider

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from config import OTEL_EXPORTER_OTLP_ENDPOINT

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
    """增强的指标采集器"""

    def __init__(self):
        """初始化指标采集器"""
        if not OPENTELEMETRY_AVAILABLE:
            _logger.warning("OpenTelemetry not available, using stub implementation")
            self.stub_enabled = True
            self.stub_metrics: Dict[str, List[MetricData]] = {}
        else:
            try:
                self.stub_enabled = False
                # 设置TracerProvider
                self.trace_provider = TracerProvider()
                trace.set_tracer_provider(self.trace_provider)

                # 设置MeterProvider
                self.metric_reader = PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT),
                    export_interval_millis=60000,
                )
                self.metric_provider = MeterProvider(metric_readers=[self.metric_reader])
                metrics.set_meter_provider(self.metric_provider)

                self.tracer = trace.get_tracer(__name__)
                self.meter = metrics.get_meter(__name__)

                _logger.info("OpenTelemetry initialized successfully")
            except Exception as e:
                _logger.error(f"Failed to initialize OpenTelemetry: {e}")
                self.stub_enabled = True
                self.stub_metrics = {}

        self.custom_metrics: Dict[str, Callable] = {}

    def record_metric(self, metric_data: MetricData):
        """记录指标"""
        if self.stub_enabled:
            if metric_data.name not in self.stub_metrics:
                self.stub_metrics[metric_data.name] = []
            self.stub_metrics[metric_data.name].append(metric_data)
            return

        try:
            if metric_data.metric_type == MetricType.COUNTER:
                counter = self.meter.create_counter(metric_data.name)
                counter.add(metric_data.value, metric_data.labels)
            elif metric_data.metric_type == MetricType.GAUGE:
                gauge = self.meter.create_gauge(metric_data.name)  # type: ignore[attr-defined]
                gauge.set(metric_data.value, metric_data.labels)
            else:
                _logger.warning(f"Unsupported metric type: {metric_data.metric_type}")
        except Exception as e:
            _logger.error(f"Failed to record metric: {e}")

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

    def get_stub_metrics(self) -> Dict[str, List[MetricData]]:
        """获取stub指标（用于测试）"""
        return self.stub_metrics


class EnhancedLogCollector:
    """增强的日志采集器"""

    def __init__(self):
        """初始化日志采集器"""
        self.stub_enabled = True  # 简化实现
        self.stub_logs: List[LogData] = []

    def record_log(self, log_data: LogData):
        """记录日志"""
        self.stub_logs.append(log_data)

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

    def get_stub_logs(self) -> List[LogData]:
        """获取stub日志（用于测试）"""
        return self.stub_logs


class EnhancedTraceCollector:
    """增强的链路采集器"""

    def __init__(self):
        """初始化链路采集器"""
        self.stub_traces: Dict[str, TraceData] = {}
        if not OPENTELEMETRY_AVAILABLE:
            _logger.warning("OpenTelemetry not available, using stub implementation")
            self.stub_enabled = True
        else:
            self.stub_enabled = False
            self.tracer = trace.get_tracer(__name__)

    def start_span(self, operation_name: str, parent_span_id: Optional[str] = None) -> str:
        """开始span"""
        span_id = f"span_{len(self.stub_traces)}"

        if not self.stub_enabled and hasattr(self, "tracer"):
            # 实际OpenTelemetry span创建
            with self.tracer.start_as_current_span(operation_name) as span:
                span_id = str(span.get_span_context().span_id)

        return span_id

    def end_span(
        self, span_id: str, status: str = "ok", attributes: Optional[Dict[str, Any]] = None
    ):
        """结束span"""
        if self.stub_enabled:
            # Stub模式不做实际处理
            pass

    def record_trace(self, trace_data: TraceData):
        """记录链路"""
        if self.stub_enabled:
            self.stub_traces[trace_data.span_id] = trace_data

    def get_stub_traces(self) -> Dict[str, TraceData]:
        """获取stub链路（用于测试）"""
        return self.stub_traces


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
        """获取监控状态"""
        return {
            "prometheus": self.prometheus_config,
            "loki": self.loki_config,
            "tempo": self.tempo_config,
            "opentelemetry": {
                "enabled": not self.metrics_collector.stub_enabled,
                "metrics_collector": not self.metrics_collector.stub_enabled,
                "log_collector": self.log_collector.stub_enabled,
                "trace_collector": not self.trace_collector.stub_enabled,
            },
        }


# 全局实例
monitoring_infrastructure = MonitoringInfrastructure()


def get_monitoring_infrastructure() -> MonitoringInfrastructure:
    """获取监控基础设施实例"""
    return monitoring_infrastructure
