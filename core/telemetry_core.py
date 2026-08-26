# -*- coding: utf-8 -*-
"""
Core Telemetry Module - OpenTelemetry Integration

Provides standardized tracing, metrics, and logging instrumentation
for AIOps Agent components using OpenTelemetry.

Phase 1 P1-5: Add OpenTelemetry instrumentation to collector layer
"""

import logging
from contextlib import contextmanager
from typing import Any, Optional

logger = logging.getLogger(__name__)

# OpenTelemetry imports
try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
except ImportError as e:
    OTEL_AVAILABLE = False
    logger.info(f"OpenTelemetry packages not available: {e}")


# Global tracer and meter providers
if OTEL_AVAILABLE:
    _tracer_provider: Optional[TracerProvider] = None
    _meter_provider: Optional[MeterProvider] = None
    _resource: Optional[Resource] = None
else:
    _tracer_provider = None
    _meter_provider = None
    _resource = None


def initialize_telemetry(
    service_name: str = "aiops-agent",
    service_version: str = "1.0.0",
    otlp_endpoint: str = "http://localhost:4317",
    enable_console_export: bool = False,
) -> bool:
    """
    Initialize OpenTelemetry tracing and metrics

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP endpoint for exporting traces and metrics
        enable_console_export: Enable console export for debugging

    Returns:
        True if initialization successful
    """
    global _tracer_provider, _meter_provider, _resource

    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping initialization")
        return False

    try:
        # Create resource with service metadata
        _resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                "deployment.environment": "production",
            }
        )

        # Initialize Tracer Provider
        _tracer_provider = TracerProvider(resource=_resource)

        # Add OTLP span exporter
        try:
            otlp_span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_span_exporter))
            logger.info(f"OTLP span exporter configured: {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP span exporter: {e}")
            if enable_console_export:
                _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Initialize Meter Provider
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
            export_interval_millis=15000,  # Export every 15 seconds
        )

        _meter_provider = MeterProvider(resource=_resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(_meter_provider)

        logger.info(f"OpenTelemetry initialized: service={service_name}, version={service_version}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}", exc_info=True)
        return False


def get_tracer(module_name: str) -> Optional[Any]:
    """
    Get a tracer for a specific module

    Args:
        module_name: Name of the module (typically __name__)

    Returns:
        Tracer instance or None if OTEL not available
    """
    if not OTEL_AVAILABLE or not _tracer_provider:
        return None
    return trace.get_tracer(module_name)


def get_meter(module_name: str) -> Optional[Any]:
    """
    Get a meter for a specific module

    Args:
        module_name: Name of the module (typically __name__)

    Returns:
        Meter instance or None if OTEL not available
    """
    if not OTEL_AVAILABLE or not _meter_provider:
        return None
    return metrics.get_meter(module_name)


@contextmanager
def trace_operation(tracer: Optional[Any], operation_name: str, **attributes: Any):
    """
    Context manager for tracing an operation

    Args:
        tracer: Tracer instance
        operation_name: Name of the operation
        **attributes: Additional span attributes

    Yields:
        Current span
    """
    if not tracer:
        yield None
        return

    with tracer.start_as_current_span(operation_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, str(value))
        yield span


def instrument_fastapi(app: Any) -> None:
    """
    Instrument FastAPI application with OpenTelemetry

    Args:
        app: FastAPI application instance
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping FastAPI instrumentation")
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_httpx():
    """
    Instrument httpx client with OpenTelemetry
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping httpx instrumentation")
        return

    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("httpx instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument httpx: {e}")


def instrument_asyncpg():
    """
    Instrument asyncpg with OpenTelemetry
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping asyncpg instrumentation")
        return

    try:
        AsyncPGInstrumentor().instrument()
        logger.info("asyncpg instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument asyncpg: {e}")


def instrument_redis():
    """
    Instrument Redis client with OpenTelemetry
    """
    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping Redis instrumentation")
        return

    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")


def shutdown_telemetry():
    """
    Shutdown OpenTelemetry providers
    """
    global _tracer_provider, _meter_provider

    if _tracer_provider and hasattr(_tracer_provider, "shutdown"):
        _tracer_provider.shutdown()
        _tracer_provider = None

    if _meter_provider and hasattr(_meter_provider, "shutdown"):
        _meter_provider.shutdown()
        _meter_provider = None

    logger.info("OpenTelemetry shutdown complete")


# 🔧 P1 Enhancement: APM metrics collection
_apm_metrics: dict[str, Any] = {
    "request_count": 0,
    "error_count": 0,
    "slow_request_count": 0,
    "last_reset": None,
}


def record_apm_metric(
    metric_name: str, value: float = 1.0, tags: Optional[dict[str, Any]] = None  # noqa: E501
) -> None:
    """🔧 P1 Enhancement: Record APM metric for application monitoring.

    Args:
        metric_name: Name of the metric
        value: Metric value
        tags: Optional tags for the metric
    """

    if metric_name == "request_count":
        if _apm_metrics["request_count"] is None:
            _apm_metrics["request_count"] = 0
        _apm_metrics["request_count"] += value
    elif metric_name == "error_count":
        if _apm_metrics["error_count"] is None:
            _apm_metrics["error_count"] = 0
        _apm_metrics["error_count"] += value
    elif metric_name == "slow_request_count":
        if _apm_metrics["slow_request_count"] is None:
            _apm_metrics["slow_request_count"] = 0
        _apm_metrics["slow_request_count"] += value

    # Also record to OpenTelemetry if available
    if OTEL_AVAILABLE:
        try:
            meter = get_meter(__name__)
            if meter:
                counter = meter.create_counter(
                    f"apm_{metric_name}", description=f"APM metric: {metric_name}"
                )
                counter.add(value, tags or {})
        except Exception as e:
            logger.warning(f"Failed to record APM metric to OpenTelemetry: {e}")


def get_apm_metrics() -> dict[str, Any]:
    """🔧 P1 Enhancement: Get current APM metrics.

    Returns:
        Dictionary with APM metrics
    """
    request_count = _apm_metrics.get("request_count", 0) or 0
    error_count = _apm_metrics.get("error_count", 0) or 0
    slow_request_count = _apm_metrics.get("slow_request_count", 0) or 0

    return {
        **_apm_metrics,
        "error_rate": (
            f"{(error_count / request_count * 100) if request_count > 0 else 0:.2f}%"
        ),  # noqa: E501
        "slow_request_rate": (  # noqa: E501
            f"{(slow_request_count / request_count * 100) if request_count > 0 else 0:.2f}%"
        ),
    }


def reset_apm_metrics() -> None:
    """🔧 P1 Enhancement: Reset APM metrics counters."""
    global _apm_metrics
    _apm_metrics = {
        "request_count": 0,
        "error_count": 0,
        "slow_request_count": 0,
        "last_reset": "2026-06-12T00:00:00Z",
    }


def get_traces(
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """🔧 P1 Enhancement: Get performance traces data.

    Args:
        service_name: Service name filter
        operation_name: Operation name filter
        min_duration: Minimum duration in milliseconds
        max_duration: Maximum duration in milliseconds
        page: Page number
        page_size: Page size

    Returns:
        Dictionary with traces data
    """
    # Mock traces data for now - in production, this would query OpenTelemetry backend
    mock_traces = [
        {
            "trace_id": "trace-123",
            "span_id": "span-456",
            "parent_span_id": "span-789",
            "operation_name": "GET /api/v1/alerts",
            "service_name": "aiops-agent",
            "start_time": "2026-06-12T00:00:00Z",
            "duration_ms": 150,
            "status": "success",
            "tags": {"http.method": "GET", "http.status_code": "200"},
            "logs": [],
        },
        {
            "trace_id": "trace-124",
            "span_id": "span-457",
            "parent_span_id": "span-790",
            "operation_name": "POST /api/v1/alerts",
            "service_name": "aiops-agent",
            "start_time": "2026-06-12T00:01:00Z",
            "duration_ms": 200,
            "status": "success",
            "tags": {"http.method": "POST", "http.status_code": "201"},
            "logs": [],
        },
    ]

    # Apply filters
    filtered_traces = mock_traces
    if service_name:
        filtered_traces = [t for t in filtered_traces if t.get("service_name") == service_name]
    if operation_name:
        filtered_traces = [t for t in filtered_traces if t.get("operation_name") == operation_name]
    if min_duration:
        filtered_traces = [t for t in filtered_traces if t.get("duration_ms", 0) >= min_duration]
    if max_duration:
        filtered_traces = [t for t in filtered_traces if t.get("duration_ms", 0) <= max_duration]

    # Apply pagination
    total = len(filtered_traces)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_traces = filtered_traces[start_idx:end_idx]

    return {
        "traces": paginated_traces,
        "total": total,
    }


__all__ = [
    "OTEL_AVAILABLE",
    "initialize_telemetry",
    "get_tracer",
    "get_meter",
    "trace_operation",
    "instrument_fastapi",
    "instrument_httpx",
    "instrument_asyncpg",
    "instrument_redis",
    "shutdown_telemetry",
    "record_apm_metric",
    "get_apm_metrics",
    "reset_apm_metrics",
    "get_traces",
]
