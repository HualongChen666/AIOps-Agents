# -*- coding: utf-8 -*-
"""Alert processor microservice."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

from services.alert_service.config import settings
from services.alert_service.mq import message_queue
from services.alert_service.processor_core import AlertPipeline
from services.alert_service.repository import get_repository
from services.alert_service.schemas import (
    Alert,
    ClassificationRule,
    EscalationRule,
    RoutingRule,
    ServiceHealth,
    SuppressionRule,
)

PROCESSOR_PROCESSED = Counter(
    "alerts_processor_processed_total",
    "Total alerts processed",
)
PIPELINE_UPTIME = Gauge(
    "alerts_processor_uptime_seconds",
    "Processor uptime",
)
PIPELINE_LATENCY = Histogram(
    "alerts_processor_processing_seconds",
    "Processing latency",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = await get_repository(settings.use_in_memory)
    pipeline = AlertPipeline(
        repository=repo,
        mq=message_queue,
        window_seconds=settings.aggregator_window_seconds,
    )
    app.state.pipeline = pipeline
    app.state.start_time = time.time()
    task = asyncio.create_task(pipeline.run())
    app.state.pipeline_task = task
    logger.info("Alert processor started")
    yield
    await pipeline.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Alert processor stopped")


app = FastAPI(
    title="Alert Processor",
    description="Aggregates, deduplicates, classifies, routes and escalates alerts.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(
        status="ok",
        service="alert-processor",
        uptime_seconds=app.state.pipeline.uptime_seconds(),
    )


@app.get("/metrics")
async def metrics() -> Response:
    PIPELINE_UPTIME.set(app.state.pipeline.uptime_seconds())
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats")
async def stats() -> Dict[str, Any]:
    pipeline = cast(AlertPipeline, app.state.pipeline)
    return pipeline.get_stats()


@app.post("/rules/routing")
async def add_routing_rule(rule: RoutingRule) -> Dict[str, Any]:
    app.state.pipeline.router.add_rule(rule)
    return {"status": "added", "rule": rule.model_dump()}


@app.get("/rules/routing")
async def list_routing_rules() -> Dict[str, Any]:
    return {"rules": [r.model_dump() for r in app.state.pipeline.router.list_rules()]}


@app.post("/rules/suppression")
async def add_suppression_rule(rule: SuppressionRule) -> Dict[str, Any]:
    app.state.pipeline.noise_suppressor.add_rule(rule)
    return {"status": "added", "rule": rule.model_dump()}


@app.get("/rules/suppression")
async def list_suppression_rules() -> Dict[str, Any]:
    return {"rules": [r.model_dump() for r in app.state.pipeline.noise_suppressor.list_rules()]}


@app.post("/rules/escalation")
async def add_escalation_rule(rule: EscalationRule) -> Dict[str, Any]:
    app.state.pipeline.escalator.add_rule(rule)
    return {"status": "added", "rule": rule.model_dump()}


@app.get("/rules/escalation")
async def list_escalation_rules() -> Dict[str, Any]:
    return {"rules": [r.model_dump() for r in app.state.pipeline.escalator.list_rules()]}


@app.post("/rules/classification")
async def add_classification_rule(rule: ClassificationRule) -> Dict[str, Any]:
    app.state.pipeline.classifier.add_rule(rule)
    return {"status": "added", "rule": rule.model_dump()}


@app.get("/rules/classification")
async def list_classification_rules() -> Dict[str, Any]:
    return {"rules": [r.model_dump() for r in app.state.pipeline.classifier.list_rules()]}


@app.post("/process")
async def process_alert(raw: Dict[str, Any]) -> Dict[str, Any]:
    with PIPELINE_LATENCY.time():
        alert = Alert(**raw)
        pipeline = cast(AlertPipeline, app.state.pipeline)
        result = await pipeline.process_and_flush(alert)
        count = len(result.get("results", [])) + len(result.get("flushed", []))
        PROCESSOR_PROCESSED.inc(count)
        return result
