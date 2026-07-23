# OpenTelemetry Integration Design for AIOps Agent

## Overview
This document describes the OpenTelemetry integration strategy for AIOps Agent, covering tracing, metrics, and logging integration with the L4 storage layer (VictoriaMetrics, Loki, Tempo).

## Architecture

### Components
1. **OpenTelemetry SDK**: Python SDK for instrumenting applications
2. **OTLP Exporter**: Exports telemetry data via OpenTelemetry Protocol
3. **Tempo**: Receives and stores trace data
4. **VictoriaMetrics**: Receives and stores metrics data
5. **Loki**: Receives and stores log data

### Data Flow
```
AIOps Agent Application
    ↓
OpenTelemetry SDK (Python)
    ↓
OTLP Exporter (gRPC/HTTP)
    ↓
┌─────────────┬──────────────┬────────────┐
│   Tempo     │VictoriaMetrics│   Loki     │
│  (Traces)   │   (Metrics)   │  (Logs)    │
└─────────────┴──────────────┴────────────┘
```

## Tracing Integration

### Instrumentation Points
1. **API Endpoints**: FastAPI request/response cycles
2. **Collector Operations**: Data collection and processing
3. **AI Engine**: AI model inference and responses
4. **Repair Engine**: Repair execution and results
5. **Database Operations**: SQLite queries and transactions
6. **External API Calls**: Third-party service interactions

### Trace Context Propagation
- Use W3C Trace Context format
- Propagate trace ID across service boundaries
- Include span context in log entries

### Sampling Strategy
- **Default**: 10% sampling rate
- **Critical paths**: 100% sampling (error paths, repair operations)
- **Development**: 100% sampling
- **Production**: Adaptive sampling based on traffic

## Metrics Integration

### Metric Types
1. **Counters**: Monotonically increasing values
   - HTTP requests
   - AI model invocations
   - Repair operations
   - Error counts

2. **Gauges**: Point-in-time values
   - Active connections
   - Queue sizes
   - Memory usage
   - CPU utilization

3. **Histograms**: Distributions of values
   - Request durations
   - AI response times
   - Database query times

4. **Summaries**: Pre-computed quantiles
   - Request latency percentiles
   - Throughput metrics

### Metric Naming Convention
- Use snake_case
- Include unit suffix when applicable
- Format: `aiops_<component>_<metric>_<unit>`

Examples:
- `aiops_http_requests_total`
- `aiops_ai_response_duration_seconds`
- `aiops_memory_usage_bytes`

## Logging Integration

### Structured Logging
- Use JSON format for logs
- Include trace ID and span ID in log entries
- Use consistent log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Log Attributes
- Trace ID: `trace_id`
- Span ID: `span_id`
- Service name: `service`
- Component: `component`
- Severity: `level`
- Timestamp: ISO 8601 format

### Log Correlation
- Link logs to traces via trace ID
- Link logs to metrics via common labels
- Use consistent resource attributes

## Configuration

### OpenTelemetry Configuration
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure tracer provider
provider = TracerProvider()
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="localhost:4317", insecure=True)
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

### Metrics Configuration
```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Configure meter provider
reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="localhost:4317", insecure=True),
    export_interval_millis=60000
)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)
```

### Resource Attributes
```python
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "aiops-agent",
    "service.version": "1.0.0",
    "deployment.environment": "production",
    "host.name": "aiops-server-1"
})
```

## Implementation Steps

### Step 1: Install Dependencies
```bash
pip install opentelemetry-api opentelemetry-sdk
pip install opentelemetry-exporter-otlp
pip install opentelemetry-instrumentation-fastapi
pip install opentelemetry-instrumentation-httpx
```

### Step 2: Initialize OpenTelemetry
Create `core/telemetry/__init__.py` with initialization logic

### Step 3: Instrument FastAPI
Use `opentelemetry-instrumentation-fastapi` for automatic instrumentation

### Step 4: Add Custom Spans
Add manual instrumentation for business logic

### Step 5: Configure Exporters
Set up OTLP exporters for Tempo, VictoriaMetrics, and Loki

### Step 6: Add Metrics
Create custom metrics for AIOps-specific operations

### Step 7: Integrate Logging
Configure structured logging with trace correlation

### Step 8: Validate
Verify traces appear in Tempo, metrics in VictoriaMetrics, logs in Loki

## Performance Considerations

### Sampling
- Use adaptive sampling to control overhead
- Sample less for high-volume endpoints
- Sample 100% for critical operations

### Batching
- Use batch exporters to reduce network overhead
- Configure appropriate batch sizes
- Tune flush intervals

### Resource Limits
- Monitor memory usage of telemetry SDK
- Limit span attribute sizes
- Use efficient serialization

## Security

### TLS Configuration
- Enable TLS for production environments
- Use certificate-based authentication
- Secure OTLP endpoints

### Data Privacy
- Sanitize sensitive data from traces
- Redact PII from logs
- Anonymize user identifiers

## Monitoring

### Telemetry Health Checks
- Monitor exporter health
- Track export failures
- Alert on telemetry pipeline issues

### Self-Monitoring
- Monitor OpenTelemetry SDK metrics
- Track buffer sizes
- Monitor export latency

## Troubleshooting

### Common Issues
1. **Traces not appearing in Tempo**
   - Check OTLP endpoint configuration
   - Verify Tempo is running
   - Check network connectivity

2. **Metrics not appearing in VictoriaMetrics**
   - Verify OTLP exporter configuration
   - Check VictoriaMetrics remote write configuration
   - Validate metric naming

3. **Logs not appearing in Loki**
   - Check Promtail configuration
   - Verify Loki is running
   - Check log format

## Best Practices

1. **Consistent Naming**: Use consistent naming across all telemetry data
2. **Semantic Conventions**: Follow OpenTelemetry semantic conventions
3. **Resource Attributes**: Include relevant resource attributes
4. **Error Handling**: Handle export failures gracefully
5. **Performance**: Monitor telemetry overhead
6. **Testing**: Validate instrumentation in development
