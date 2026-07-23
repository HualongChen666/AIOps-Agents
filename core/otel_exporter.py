# -*- coding: utf-8 -*-
"""core/otel_exporter.py - OpenTelemetry 标准化采集实现

OpenTelemetry 标准化采集实现

本模块负责把 AIOps Agent 采集的快照数据通过 OpenTelemetry
OTLP exporter 推送到外部可观测平台（如 VictoriaMetrics、Tempo、Grafana Cloud 等）。

实现思路
-----------
1. 使用 `opentelemetry-sdk` 创建全局 `MeterProvider`。
2. 根据环境变量或 `config.py` 中的配置实例化 `OTLPMetricExporter`（默认使用 gRPC）。
3. 通过 `PeriodicExportingMetricReader` 自动周期性上报（默认 10s），也提供手动 `export_snapshot` 接口供业务侧即时上报。
4. 将采集的 snapshot（由 `core.collector.get_cached_snapshot` 返回）映射为 OTel Gauge 类型的指标，
   - cpu_usage_percent、cpu_per_core、memory_total_gb、memory_used_gb、swap_total_gb、disk_total_gb 等。
   - 进程信息使用 `process_` 前缀的标签（pid、name、username）并记录 `process_cpu_percent`、`process_memory_percent`。
5. 采用模块级单例模式，避免重复初始化。

使用方式
~~~~~~~~~~
```python
from core.otel_exporter import init_otel, export_snapshot

# 在应用启动时调用一次
init_otel()

# 采集循环中（如 metrics_router）
snapshot = get_cached_snapshot()
if snapshot:
    export_snapshot(snapshot)
```

配置（可在 `.env` 或系统环境变量中设置）
----------------------------------------
- OTEL_EXPORTER_OTLP_ENDPOINT   : OTLP 接收端地址，默认 "http://localhost:4317"
# 🔧 技术债修复：从 config 模块导入统一配置
from config import OTEL_EXPORTER_OTLP_ENDPOINT
- OTEL_EXPORTER_OTLP_TIMEOUT    : 请求超时时间（秒），默认 10
- OTEL_EXPORT_INTERVAL_SECONDS  : 周期上报间隔（秒），默认 10
- OTEL_SERVICE_NAME             : 本服务在追踪系统中的名称，默认 "aiops-agent"
"""

import logging
import os
from typing import Any, Dict, Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 单例维护的 MeterProvider 与 Meter
# ---------------------------------------------------------------------------
_meter_provider: Optional[MeterProvider] = None
_meter = None

# ---------------------------------------------------------------------------
# 单例维护的 TracerProvider 与 Tracer
# ---------------------------------------------------------------------------
_tracer_provider: Optional[TracerProvider] = None
_tracer = None


def _create_meter_provider() -> MeterProvider:
    """创建并返回全局 MeterProvider（仅初始化一次）。"""
    global _meter_provider, _meter

    if _meter_provider is not None:
        return _meter_provider

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    timeout = int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10"))
    export_interval = int(os.getenv("OTEL_EXPORT_INTERVAL_SECONDS", "10"))
    service_name = os.getenv("OTEL_SERVICE_NAME", "aiops-agent")

    exporter: MetricExporter = OTLPMetricExporter(
        endpoint=endpoint,
        timeout=timeout,
        insecure=True,
    )

    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=export_interval * 1000)
    _meter_provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(_meter_provider)
    _meter = metrics.get_meter(service_name)
    _logger.info(
        f"OTel exporter initialized: endpoint={endpoint}, "
        f"interval={export_interval}s, service={service_name}"
    )
    return _meter_provider


def _create_tracer_provider() -> TracerProvider:
    """创建并返回全局 TracerProvider（仅初始化一次），并注册 OTLP Span Exporter。"""
    global _tracer_provider, _tracer

    if _tracer_provider is not None:
        return _tracer_provider

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    timeout = int(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10"))
    service_name = os.getenv("OTEL_SERVICE_NAME", "aiops-agent")

    # 使用相同的 OTLP endpoint（可通过 OTEL_EXPORTER_OTLP_TRACES_ENDPOINT 覆盖）
    traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", endpoint)
    span_exporter: SpanExporter = OTLPSpanExporter(
        endpoint=traces_endpoint,
        timeout=timeout,
        insecure=True,
    )
    span_processor = BatchSpanProcessor(span_exporter)
    _tracer_provider = TracerProvider()
    _tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(_tracer_provider)
    _tracer = trace.get_tracer(service_name)
    _logger.info(f"OTel tracer initialized: endpoint={traces_endpoint}, service={service_name}")
    return _tracer_provider


def init_otel() -> None:
    """在应用启动阶段调用，完成全局 MeterProvider 与 TracerProvider 的初始化。"""
    _create_meter_provider()
    _create_tracer_provider()


# ---------------------------------------------------------------------------
# 快照到 OTel 指标的映射函数
# ---------------------------------------------------------------------------
def _record_gauge(
    name: str,
    value: float,
    description: str = "",
    unit: str = "",
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    """创建或获取 Gauge 并记录单个值。"""
    if _meter is None:
        _logger.warning("OTel meter not initialized, call init_otel() first")
        return
    attrs = attributes or {}

    def _callback(observable_gauge):
        observable_gauge.observe(value, attrs)

    _meter.create_observable_gauge(name, callbacks=[_callback], description=description, unit=unit)


def export_snapshot(snapshot: Dict[str, Any]) -> None:
    """将 collector 快照转换为 OTel 指标并上报。同步创建一个 Tracing span 用于记录导出过程。"""
    if not snapshot:
        _logger.debug("Empty snapshot, nothing to export")
        return

    # 使用 Tracing span 包裹整个导出流程
    span = None
    if _tracer is None:
        _logger.warning("OTel tracer not initialized, call init_otel() first")
    else:
        span = _tracer.start_as_current_span("export_snapshot")
        span.__enter__()

    try:
        # CPU
        cpu = snapshot.get("cpu", {})
        _record_gauge(
            "cpu.usage_percent",
            float(cpu.get("usage_percent", 0.0)),
            description="Overall CPU usage percent",
        )
        for idx, core_val in enumerate(cpu.get("per_core", [])):
            _record_gauge(
                "cpu.per_core_percent",
                float(core_val),
                description="CPU usage percent per core",
                attributes={"core": idx},
            )

        # Memory
        mem = snapshot.get("memory", {})
        _record_gauge(
            "memory.total_gb", float(mem.get("total_gb", 0.0)), description="Total memory GB"
        )
        _record_gauge(
            "memory.used_gb", float(mem.get("used_gb", 0.0)), description="Used memory GB"
        )
        _record_gauge(
            "memory.swap_total_gb",
            float(mem.get("swap_total_gb", 0.0)),
            description="Swap total GB",
        )
        _record_gauge(
            "memory.swap_used_gb",
            float(mem.get("swap_used_gb", 0.0)),
            description="Swap used GB",
        )

        # Disk (aggregate across partitions)
        disks = snapshot.get("disk", [])
        total_disk = sum(d.get("total_gb", 0.0) for d in disks)
        used_disk = sum(d.get("used_gb", 0.0) for d in disks)
        _record_gauge("disk.total_gb", total_disk, description="Total disk space across partitions")
        _record_gauge("disk.used_gb", used_disk, description="Used disk space across partitions")

        # Network
        net = snapshot.get("network", {})
        _record_gauge(
            "network.recv_speed_mb",
            float(net.get("recv_speed_mb", 0.0)),
            description="Network receive speed MB/s",
        )
        _record_gauge(
            "network.sent_speed_mb",
            float(net.get("sent_speed_mb", 0.0)),
            description="Network send speed MB/s",
        )

        # Processes (export top 10)
        procs = snapshot.get("processes", [])[:10]
        for proc in procs:
            attrs = {
                "pid": proc.get("pid"),
                "name": proc.get("name"),
                "username": proc.get("username"),
            }
            _record_gauge(
                "process.cpu_percent",
                float(proc.get("cpu_percent", 0.0)),
                description="Process CPU usage percent",
                attributes=attrs,
            )
            _record_gauge(
                "process.memory_percent",
                float(proc.get("memory_percent", 0.0)),
                description="Process memory usage percent",
                attributes=attrs,
            )

        # System info
        sys_info = snapshot.get("system", {})
        if sys_info:
            _record_gauge(
                "system.uptime_seconds",
                float(sys_info.get("uptime_seconds", 0)),
                description="System uptime seconds",
            )
    finally:
        if span is not None:
            span.__exit__(None, None, None)

    _logger.debug("Exported snapshot to OpenTelemetry")


# ---------------------------------------------------------------------------
# 供外部直接使用的快捷接口
# ---------------------------------------------------------------------------
def shutdown() -> None:
    """在进程退出前调用，确保 Exporter 正常关闭。"""
    if _meter_provider is not None:
        _meter_provider.shutdown()
        _logger.info("OTel MeterProvider shutdown")
