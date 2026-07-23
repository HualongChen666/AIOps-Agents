# -*- coding: utf-8 -*-
"""
OpenTelemetry Distributed Tracing Integration
Enterprise-grade distributed tracing system with OpenTelemetry
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter

    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False
    JaegerExporter = None  # type: ignore[misc, assignment]


class TracingBackend(Enum):
    """Tracing backend type"""

    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    OTLP = "otlp"
    CONSOLE = "console"


class SamplingStrategy(Enum):
    """Sampling strategy"""

    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILITY = "probability"
    PARENT_BASED_ALWAYS_ON = "parent_based_always_on"
    PARENT_BASED_ALWAYS_OFF = "parent_based_always_off"


@dataclass
class TracingConfig:
    """Tracing configuration"""

    service_name: str = "aiops-agent"
    backend: TracingBackend = TracingBackend.OTLP
    sampling_strategy: SamplingStrategy = SamplingStrategy.PROBABILITY
    sampling_rate: float = 0.1
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    otlp_endpoint: str = "localhost:4317"
    enable_fastapi_instrumentation: bool = True
    enable_httpx_instrumentation: bool = True
    enable_sqlalchemy_instrumentation: bool = True
    enable_redis_instrumentation: bool = True
    export_console_spans: bool = False
    resource_attributes: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanContext:
    """Span context information"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_state: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanData:
    """Span data"""

    span_name: str
    span_kind: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status_code: str = "OK"
    status_message: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenTelemetryTracingManager:
    """Enterprise-grade OpenTelemetry tracing manager"""

    def __init__(self, config: Optional[TracingConfig] = None):
        """
        Initialize OpenTelemetry tracing manager

        Args:
            config: Tracing configuration
        """
        self.config = config or TracingConfig()
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.is_initialized = False

        # Statistics
        self.total_spans = 0
        self.exported_spans = 0
        self.failed_exports = 0

        logger.info("OpenTelemetry tracing manager initialized")

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing"""
        try:
            # Create resource
            resource = Resource.create(
                {SERVICE_NAME: self.config.service_name, **self.config.resource_attributes}
            )

            # Configure sampling
            from opentelemetry.sdk.trace import sampling
            from opentelemetry.sdk.trace.sampling import Sampler

            if self.config.sampling_strategy == SamplingStrategy.ALWAYS_ON:
                sampler: Sampler = sampling.ALWAYS_ON
            elif self.config.sampling_strategy == SamplingStrategy.ALWAYS_OFF:
                sampler = sampling.ALWAYS_OFF
            elif self.config.sampling_strategy == SamplingStrategy.PROBABILITY:
                sampler = sampling.TraceIdRatioBased(self.config.sampling_rate)
            elif self.config.sampling_strategy == SamplingStrategy.PARENT_BASED_ALWAYS_ON:
                sampler = sampling.ParentBased(sampling.ALWAYS_ON)
            elif self.config.sampling_strategy == SamplingStrategy.PARENT_BASED_ALWAYS_OFF:
                sampler = sampling.ParentBased(sampling.ALWAYS_OFF)
            else:
                sampler = sampling.TraceIdRatioBased(self.config.sampling_rate)

            # Create tracer provider with sampler
            self.tracer_provider = TracerProvider(resource=resource, sampler=sampler)

            # Configure exporter based on backend
            if self.config.backend == TracingBackend.JAEGER:
                if not JAEGER_AVAILABLE or JaegerExporter is None:
                    raise ValueError(
                        "Jaeger backend selected but opentelemetry-exporter-jaeger is not installed"
                    )
                exporter = JaegerExporter(
                    agent_host_name=self.config.jaeger_host,
                    agent_port=self.config.jaeger_port,
                )
                self.tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"Jaeger exporter configured: {  # noqa: E501
                        self.config.jaeger_host}:{
                            self.config.jaeger_port}")

            elif self.config.backend == TracingBackend.ZIPKIN:
                exporter = ZipkinExporter(
                    endpoint=self.config.zipkin_endpoint,
                )
                self.tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"Zipkin exporter configured: {self.config.zipkin_endpoint}")

            elif self.config.backend == TracingBackend.OTLP:
                exporter = OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    insecure=True,
                )
                self.tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"OTLP exporter configured: {self.config.otlp_endpoint}")

            # Console exporter for debugging
            if self.config.export_console_spans:
                console_exporter = ConsoleSpanExporter()
                self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
                logger.info("Console exporter enabled")

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Configure propagators
            from opentelemetry.propagators.composite import CompositePropagator

            propagate.set_global_textmap(
                CompositePropagator(
                    [TraceContextTextMapPropagator(), B3MultiFormat(), JaegerPropagator()]
                )
            )

            self.is_initialized = True
            logger.info("OpenTelemetry tracing initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
            raise

    def instrument_fastapi(self, app) -> None:
        """
        Instrument FastAPI application

        Args:
            app: FastAPI application
        """
        if not self.config.enable_fastapi_instrumentation:
            return

        try:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=self.tracer_provider)
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")

    def instrument_httpx(self) -> None:
        """Instrument HTTPX client"""
        if not self.config.enable_httpx_instrumentation:
            return

        try:
            HTTPXClientInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("HTTPX instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument HTTPX: {e}")

    def instrument_sqlalchemy(self, engine) -> None:
        """
        Instrument SQLAlchemy engine

        Args:
            engine: SQLAlchemy engine
        """
        if not self.config.enable_sqlalchemy_instrumentation:
            return

        try:
            SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=self.tracer_provider)
            logger.info("SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument SQLAlchemy: {e}")

    def instrument_redis(self, redis_client) -> None:
        """
        Instrument Redis client

        Args:
            redis_client: Redis client
        """
        if not self.config.enable_redis_instrumentation:
            return

        try:
            RedisInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.error(f"Failed to instrument Redis: {e}")

    def create_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    ) -> trace.Span:
        """
        Create a new span

        Args:
            name: Span name
            attributes: Span attributes
            kind: Span kind

        Returns:
            Span object
        """
        if not self.is_initialized:
            logger.warning("Tracing not initialized, returning no-op span")
            return trace.get_current_span()

        if self.tracer is None:
            logger.warning("Tracer not initialized, returning no-op span")
            return trace.get_current_span()

        span = self.tracer.start_span(name, kind=kind)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        self.total_spans += 1

        return span

    def get_current_span(self) -> trace.Span:
        """
        Get current span

        Returns:
            Current span
        """
        return trace.get_current_span()

    def get_trace_id(self) -> Optional[str]:
        """
        Get current trace ID

        Returns:
            Trace ID or None
        """
        current_span = self.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context:
                return format(span_context.trace_id, "032x")
        return None

    def get_span_id(self) -> Optional[str]:
        """
        Get current span ID

        Returns:
            Span ID or None
        """
        current_span = self.get_current_span()
        if current_span:
            span_context = current_span.get_span_context()
            if span_context:
                return format(span_context.span_id, "016x")
        return None

    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add event to current span

        Args:
            name: Event name
            attributes: Event attributes
        """
        current_span = self.get_current_span()
        if current_span:
            current_span.add_event(name, attributes or {})

    def set_span_attribute(self, key: str, value: Any) -> None:
        """
        Set attribute on current span

        Args:
            key: Attribute key
            value: Attribute value
        """
        current_span = self.get_current_span()
        if current_span:
            current_span.set_attribute(key, str(value))

    def record_exception(self, exception: Exception) -> None:
        """
        Record exception on current span

        Args:
            exception: Exception to record
        """
        current_span = self.get_current_span()
        if current_span:
            current_span.record_exception(exception)

    def set_span_status(self, status_code: str, status_message: str = "") -> None:
        """
        Set status on current span

        Args:
            status_code: Status code
            status_message: Status message
        """
        current_span = self.get_current_span()
        if current_span:
            from opentelemetry.trace import Status, StatusCode

            # Map string status code to StatusCode enum
            status_mapping = {
                "OK": StatusCode.OK,
                "ERROR": StatusCode.ERROR,
                "UNSET": StatusCode.UNSET,
            }
            status_code_enum = status_mapping.get(status_code, StatusCode.UNSET)
            current_span.set_status(Status(status_code_enum, status_message))

    def get_statistics(self) -> Dict[str, Any]:
        """Get tracing statistics"""
        return {
            "is_initialized": self.is_initialized,
            "total_spans": self.total_spans,
            "exported_spans": self.exported_spans,
            "failed_exports": self.failed_exports,
            "success_rate": self.exported_spans / self.total_spans if self.total_spans > 0 else 0.0,
        }

    def shutdown(self) -> None:
        """Shutdown tracing manager"""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("OpenTelemetry tracing shutdown")


def get_opentelemetry_tracing_manager(
    config: Optional[TracingConfig] = None,
) -> OpenTelemetryTracingManager:
    """
    Factory function to get OpenTelemetry tracing manager instance

    Args:
        config: Optional tracing configuration

    Returns:
        OpenTelemetryTracingManager: Tracing manager instance
    """
    return OpenTelemetryTracingManager(config)
