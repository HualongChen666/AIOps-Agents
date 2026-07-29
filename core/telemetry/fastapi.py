# -*- coding: utf-8 -*-
"""
FastAPI OpenTelemetry Instrumentation
Provides automatic instrumentation for FastAPI applications
"""

from fastapi import FastAPI
from loguru import logger
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


def instrument_fastapi(
    app: FastAPI, service_name: str = "aiops-agent", excluded_urls: str = None
) -> None:
    """
    Instrument FastAPI application with OpenTelemetry

    Args:
        app: FastAPI application instance
        service_name: Name of the service
        excluded_urls: Comma-separated list of URLs to exclude from tracing
    """
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=None,  # Uses global tracer provider
            excluded_urls=excluded_urls,
        )
        logger.info(f"FastAPI instrumentation enabled for {service_name}")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")


def instrument_httpx() -> None:
    """Instrument HTTPX client for outgoing HTTP requests"""
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument HTTPX: {e}")


def instrument_sqlalchemy(engine) -> None:
    """
    Instrument SQLAlchemy for database operations

    Args:
        engine: SQLAlchemy engine instance
    """
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument SQLAlchemy: {e}")


def setup_fastapi_telemetry(
    app: FastAPI,
    service_name: str = "aiops-agent",
    instrument_http: bool = True,
    instrument_db: bool = True,
    enable_redis_instrumentation: bool = True,
    db_engine=None,
    otlp_endpoint: str = "localhost:4317",
    environment: str = "production",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
) -> bool:
    """
    Set up complete telemetry for FastAPI application

    Args:
        app: FastAPI application instance
        service_name: Name of the service
        instrument_http: Whether to instrument HTTPX
        instrument_db: Whether to instrument SQLAlchemy
        enable_redis_instrumentation: Whether to instrument Redis
        db_engine: SQLAlchemy engine (if instrument_db is True)
        otlp_endpoint: OTLP collector endpoint (Tempo / Prometheus OTLP / Jaeger)
        environment: Deployment environment label
        jaeger_host: Jaeger agent host
        jaeger_port: Jaeger agent port

    Returns:
        bool: True if setup successful, False otherwise
    """
    # Initialize OpenTelemetry
    try:
        from core.telemetry import initialize_telemetry

        if not initialize_telemetry(
            service_name=service_name,
            otlp_endpoint=otlp_endpoint,
            environment=environment,
            enable_jaeger=True,
            jaeger_host=jaeger_host,
            jaeger_port=jaeger_port,
        ):
            logger.warning("OpenTelemetry initialization failed")
            return False
    except ImportError:
        logger.warning("OpenTelemetry not available")
        return False

    # Instrument FastAPI
    instrument_fastapi(app, service_name=service_name)

    # Instrument HTTP client
    if instrument_http:
        instrument_httpx()

    # Instrument database
    if instrument_db and db_engine:
        instrument_sqlalchemy(db_engine)

    # Instrument Redis
    if enable_redis_instrumentation:
        instrument_redis()

    return True


def instrument_redis() -> None:
    """Instrument Redis client for caching operations"""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")
