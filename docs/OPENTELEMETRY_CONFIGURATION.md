# OpenTelemetry配置文档

## 概述

本文档描述了AIOps SRE Agent的OpenTelemetry配置方案，包括初始化配置、追踪配置、指标配置和日志配置。

---

## OpenTelemetry架构

### 组件架构

```
┌─────────────────────────────────────────────────────────┐
│                    AIOps SRE Agent                      │
├─────────────────────────────────────────────────────────┤
│  Application Layer (FastAPI, Workers)                  │
│  ├── Tracing (Distributed Tracing)                     │
│  ├── Metrics (Performance Metrics)                     │
│  └── Logging (Structured Logging)                      │
├─────────────────────────────────────────────────────────┤
│  OpenTelemetry SDK                                      │
│  ├── Tracer Provider                                   │
│  ├── Meter Provider                                    │
│  └── Logger Provider                                   │
├─────────────────────────────────────────────────────────┤
│  OpenTelemetry Exporters                               │
│  ├── OTLP Span Exporter                                │
│  ├── OTLP Metric Exporter                              │
│  └── Console Exporter (Debug)                          │
├─────────────────────────────────────────────────────────┤
│  OpenTelemetry Collector (Jaeger/Tempo)                │
├─────────────────────────────────────────────────────────┤
│  APM Backend (Grafana, Prometheus, Loki)                │
└─────────────────────────────────────────────────────────┘
```

---

## 初始化配置

### 基础配置

#### 环境变量配置
```bash
# OpenTelemetry配置
OTEL_SERVICE_NAME=aiops-sre-agent
OTEL_SERVICE_VERSION=1.0.0
OTEL_DEPLOYMENT_ENVIRONMENT=production
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_METRICS_EXPORT_INTERVAL=15000
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
```

#### Python配置
```python
# config/telemetry.py
from pydantic import BaseSettings, Field

class TelemetryConfig(BaseSettings):
    """OpenTelemetry配置"""
    
    service_name: str = Field(default="aiops-sre-agent", env="OTEL_SERVICE_NAME")
    service_version: str = Field(default="1.0.0", env="OTEL_SERVICE_VERSION")
    deployment_environment: str = Field(default="production", env="OTEL_DEPLOYMENT_ENVIRONMENT")
    
    otlp_endpoint: str = Field(default="http://localhost:4317", env="OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_protocol: str = Field(default="grpc", env="OTEL_EXPORTER_OTLP_PROTOCOL")
    otlp_insecure: bool = Field(default=True, env="OTEL_EXPORTER_OTLP_INSECURE")
    
    metrics_export_interval: int = Field(default=15000, env="OTEL_METRICS_EXPORT_INTERVAL")
    
    traces_sampler: str = Field(default="parentbased_traceidratio", env="OTEL_TRACES_SAMPLER")
    traces_sampler_arg: float = Field(default=0.1, env="OTEL_TRACES_SAMPLER_ARG")
    
    enable_console_export: bool = Field(default=False, env="OTEL_ENABLE_CONSOLE_EXPORT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

#### 初始化代码
```python
# core/telemetry/__init__.py
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from config.telemetry import TelemetryConfig

def initialize_telemetry(config: TelemetryConfig) -> bool:
    """初始化OpenTelemetry"""
    try:
        # 创建资源
        resource = Resource.create({
            "service.name": config.service_name,
            "service.version": config.service_version,
            "deployment.environment": config.deployment_environment,
            "host.name": get_hostname(),
            "process.pid": os.getpid()
        })
        
        # 初始化Tracer Provider
        tracer_provider = TracerProvider(resource=resource)
        
        # 添加OTLP Span Exporter
        otlp_span_exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            insecure=config.otlp_insecure
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
        
        # 添加Console Exporter（调试用）
        if config.enable_console_export:
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        
        # 设置全局Tracer Provider
        trace.set_tracer_provider(tracer_provider)
        
        # 初始化Meter Provider
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=config.otlp_endpoint,
                insecure=config.otlp_insecure
            ),
            export_interval_millis=config.metrics_export_interval
        )
        
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        
        logger.info(f"OpenTelemetry initialized: {config.service_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return False
```

---

## 追踪配置

### 分布式追踪

#### 追踪器配置
```python
# core/telemetry/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampler import ParentBasedTraceIdRatio

def configure_tracing(config: TelemetryConfig) -> TracerProvider:
    """配置分布式追踪"""
    
    # 配置采样器
    sampler = ParentBasedTraceIdRatio(
        root_id_ratio=config.traces_sampler_arg
    )
    
    # 创建Tracer Provider
    tracer_provider = TracerProvider(
        resource=Resource.create({
            "service.name": config.service_name,
            "service.version": config.service_version
        }),
        sampler=sampler
    )
    
    # 添加Span Processor
    otlp_exporter = OTLPSpanExporter(
        endpoint=config.otlp_endpoint,
        insecure=config.otlp_insecure
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    return tracer_provider
```

#### 追踪使用示例
```python
# 使用追踪器
from core.telemetry import get_tracer

tracer = get_tracer(__name__)

@tracer.start_as_current_span("process_alert")
def process_alert(alert_id: str):
    """处理告警"""
    with tracer.start_as_current_span("validate_alert") as span:
        span.set_attribute("alert_id", alert_id)
        # 验证逻辑
        pass
    
    with tracer.start_as_current_span("execute_repair") as span:
        span.set_attribute("alert_id", alert_id)
        # 修复逻辑
        pass
```

### 自动追踪

#### FastAPI自动追踪
```python
# core/telemetry/fastapi.py
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def instrument_fastapi(app: FastAPI, config: TelemetryConfig):
    """自动追踪FastAPI应用"""
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=None,  # 使用全局Tracer Provider
        excluded_urls="/health,/metrics"
    )
    
    # 追踪HTTPX客户端
    HTTPXClientInstrumentor().instrument()
    
    # 追踪SQLAlchemy
    SQLAlchemyInstrumentor().instrument()
```

#### 数据库追踪
```python
# 数据库追踪配置
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def instrument_database():
    """追踪数据库操作"""
    # PostgreSQL追踪
    AsyncPGInstrumentor().instrument()
    
    # Redis追踪
    RedisInstrumentor().instrument()
```

---

## 指标配置

### 自定义指标

#### 指标定义
```python
# core/telemetry/metrics.py
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, Gauge

class CustomMetrics:
    """自定义指标"""
    
    def __init__(self, meter):
        self.meter = meter
        
        # 计数器
        self.alert_counter = meter.create_counter(
            "alerts_total",
            description="Total number of alerts processed"
        )
        
        self.repair_counter = meter.create_counter(
            "repairs_total",
            description="Total number of repairs executed"
        )
        
        # 直方图
        self.alert_processing_time = meter.create_histogram(
            "alert_processing_duration",
            description="Alert processing time in seconds",
            unit="s"
        )
        
        self.repair_execution_time = meter.create_histogram(
            "repair_execution_duration",
            description="Repair execution time in seconds",
            unit="s"
        )
        
        # 仪表
        self.active_repairs = meter.create_gauge(
            "active_repairs",
            description="Number of currently active repairs"
        )
        
        self.queue_size = meter.create_gauge(
            "alert_queue_size",
            description="Number of alerts in queue"
        )
    
    def record_alert(self, severity: str):
        """记录告警"""
        self.alert_counter.add(1, {"severity": severity})
    
    def record_repair(self, repair_type: str):
        """记录修复"""
        self.repair_counter.add(1, {"repair_type": repair_type})
    
    def record_processing_time(self, duration: float, operation: str):
        """记录处理时间"""
        self.alert_processing_time.record(duration, {"operation": operation})
    
    def set_active_repairs(self, count: int):
        """设置活跃修复数量"""
        self.active_repairs.set(count)
    
    def set_queue_size(self, size: int):
        """设置队列大小"""
        self.queue_size.set(size)
```

#### 指标使用示例
```python
# 使用自定义指标
from core.telemetry import get_meter, CustomMetrics

meter = get_meter(__name__)
custom_metrics = CustomMetrics(meter)

# 记录告警
custom_metrics.record_alert("high")

# 记录修复
custom_metrics.record_repair("automatic")

# 记录处理时间
import time
start_time = time.time()
# 执行操作
duration = time.time() - start_time
custom_metrics.record_processing_time(duration, "validate")
```

### 系统指标

#### 系统指标收集
```python
# core/telemetry/system_metrics.py
import psutil
from opentelemetry import metrics

def collect_system_metrics(meter):
    """收集系统指标"""
    
    # CPU使用率
    cpu_gauge = meter.create_gauge(
        "system_cpu_usage",
        description="System CPU usage percentage",
        unit="%"
    )
    
    # 内存使用率
    memory_gauge = meter.create_gauge(
        "system_memory_usage",
        description="System memory usage percentage",
        unit="%"
    )
    
    # 磁盘使用率
    disk_gauge = meter.create_gauge(
        "system_disk_usage",
        description="System disk usage percentage",
        unit="%"
    )
    
    # 网络I/O
    network_counter = meter.create_counter(
        "system_network_bytes",
        description="Network I/O in bytes",
        unit="By"
    )
    
    def update_metrics():
        """更新指标"""
        cpu_gauge.set(psutil.cpu_percent())
        memory_gauge.set(psutil.virtual_memory().percent)
        disk_gauge.set(psutil.disk_usage('/').percent)
        
        net_io = psutil.net_io_counters()
        network_counter.add(net_io.bytes_sent, {"direction": "sent"})
        network_counter.add(net_io.bytes_recv, {"direction": "received"})
    
    return update_metrics
```

---

## 日志配置

### 结构化日志

#### 日志配置
```python
# core/telemetry/logging.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
import logging
import json

class StructuredLogHandler(logging.Handler):
    """结构化日志处理器"""
    
    def __init__(self, tracer_provider: TracerProvider):
        super().__init__()
        self.tracer_provider = tracer_provider
    
    def emit(self, record):
        """发出日志"""
        # 添加追踪上下文
        span = trace.get_current_span()
        if span:
            trace_id = span.get_span_context().trace_id
            span_id = span.get_span_context().span_id
        else:
            trace_id = None
            span_id = None
        
        # 创建结构化日志
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": hex(trace_id) if trace_id else None,
            "span_id": hex(span_id) if span_id else None,
            "context": getattr(record, "context", {})
        }
        
        # 输出JSON格式日志
        print(json.dumps(log_entry))
    
    def formatTime(self, record):
        """格式化时间"""
        return self.formatTime(record)

def configure_logging(tracer_provider: TracerProvider):
    """配置结构化日志"""
    handler = StructuredLogHandler(tracer_provider)
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)
```

---

## 配置文件

### Docker Compose配置

```yaml
# docker-compose.telemetry.yml
version: '3.8'

services:
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC receiver
      - "4318:4318"  # OTLP HTTP receiver
      - "8888:8888"  # Prometheus metrics
      - "8889:8889"  # Prometheus exporter
      - "13133:13133"  # health check
    networks:
      - telemetry

  # Jaeger
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "5775:5775"  # Jaeger UI
      - "6831:6831"  # Jaeger collector
      - "6832:6832"  # Jaeger agent
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - telemetry

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - telemetry

  # Grafana
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/etc/grafana/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    networks:
      - telemetry

networks:
  telemetry:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
```

### OpenTelemetry Collector配置

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 10000

exporters:
  jaeger:
    endpoint: jaeger:6831
    tls:
      insecure: true
  
  prometheus:
    endpoint: "0.0.0.0:8889"
    const_labels:
      label1: value1

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
    
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
```

### Prometheus配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'otel-collector'
    static_configs:
      - targets: ['otel-collector:8889']
  
  - job_name: 'aiops-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## 验证配置

### 配置验证

#### 验证脚本
```python
# scripts/verify_telemetry.py
import requests
import time

def verify_telemetry():
    """验证OpenTelemetry配置"""
    
    # 验证OTLP Collector
    try:
        response = requests.get("http://localhost:13133")
        if response.status_code == 200:
            print("✓ OTLP Collector is running")
        else:
            print("✗ OTLP Collector is not responding")
    except Exception as e:
        print(f"✗ OTLP Collector connection failed: {e}")
    
    # 验证Jaeger
    try:
        response = requests.get("http://localhost:16686")
        if response.status_code == 200:
            print("✓ Jaeger is running")
        else:
            print("✗ Jaeger is not responding")
    except Exception as e:
        print(f"✗ Jaeger connection failed: {e}")
    
    # 验证Prometheus
    try:
        response = requests.get("http://localhost:9090/-/healthy")
        if response.status_code == 200:
            print("✓ Prometheus is running")
        else:
            print("✗ Prometheus is not responding")
    except Exception as e:
        print(f"✗ Prometheus connection failed: {e}")
    
    # 验证Grafana
    try:
        response = requests.get("http://localhost:3000/api/health")
        if response.status_code == 200:
            print("✓ Grafana is running")
        else:
            print("✗ Grafana is not responding")
    except Exception as e:
        print(f"✗ Grafana connection failed: {e}")

if __name__ == "__main__":
    verify_telemetry()
```

---

## 故障排除

### 常见问题

#### OTLP连接失败
```python
# 解决方案：检查OTLP端点配置
# 1. 验证OTLP Collector是否运行
# 2. 检查网络连接
# 3. 验证端点URL配置
# 4. 检查防火墙设置
```

#### 指标未显示
```python
# 解决方案：检查指标导出配置
# 1. 验证Meter Provider配置
# 2. 检查指标导出间隔
# 3. 验证Prometheus配置
# 4. 检查指标名称和标签
```

#### 追踪未显示
```python
# 解决方案：检查追踪配置
# 1. 验证Tracer Provider配置
# 2. 检查采样器配置
# 3. 验证Jaeger配置
# 4. 检查追踪上下文传播
```

---

**文档版本**: 1.0  
**创建日期**: 2026-08-31  
**最后更新**: 2026-08-31  
**维护团队**: AIOps SRE Agent 开发团队