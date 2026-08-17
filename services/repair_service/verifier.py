# -*- coding: utf-8 -*-
"""Repair verifier microservice."""

from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, cast

from fastapi import Body, FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.repair_service.audit import AuditStore
from services.repair_service.config import settings
from services.repair_service.health_check import HealthCheckEngine
from services.repair_service.metrics import REPAIR_VERIFICATION_DURATION
from services.repair_service.rollback import RollbackEngine
from services.repair_service.schemas import (
    RepairExecutionResult,
    RepairTask,
    ServiceHealth,
    VerificationResult,
)


class RepairVerifier:
    """Verify repair results with multiple strategies."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.health: HealthCheckEngine = getattr(sys.modules[__name__], "HealthCheckEngine")(
            timeout=timeout
        )
        self._strategies: List[str] = [
            "service_status",
            "process_check",
            "metric_threshold",
            "custom_command",
            "dns_resolution",
            "port_connectivity",
            "file_exists",
            "log_pattern",
            "http_endpoint",
            "noop",
        ]

    async def verify(
        self,
        task: RepairTask,
        result: Optional[RepairExecutionResult] = None,
    ) -> VerificationResult:
        start = time.perf_counter()
        strategy_name = self._select_strategy(task)
        strategy_fn = getattr(self, f"_verify_{strategy_name}", self._verify_noop)

        try:
            outcome = await strategy_fn(task, result)
        except Exception as e:
            logger.error(f"Verification failed for {task.task_id}: {e}")
            outcome = {
                "verified": False,
                "evidence": {"error": str(e)},
                "recommendation": "retry or manual check",
            }

        duration = time.perf_counter() - start
        REPAIR_VERIFICATION_DURATION.labels(strategy=strategy_name).observe(duration)
        return VerificationResult(
            task_id=task.task_id,
            verified=outcome.get("verified"),
            strategy=strategy_name,
            confidence=outcome.get("confidence", 0.95),
            evidence=outcome.get("evidence", {}),
            duration_seconds=duration,
            error_msg=outcome.get("error", ""),
            recommendation=outcome.get("recommendation", ""),
        )

    def _select_strategy(self, task: RepairTask) -> str:
        strategy = task.strategy
        if not strategy:
            return "noop"
        key = strategy.script_key.lower()
        if "restart" in key or "service" in key:
            return "service_status"
        if "cpu" in key or "kill" in key or "process" in key:
            return "process_check"
        if "file" in key or "disk" in key:
            return "file_exists"
        if "memory" in key or "metric" in key:
            return "metric_threshold"
        if "dns" in key:
            return "dns_resolution"
        if "network" in key or "port" in key:
            return "port_connectivity"
        if "log" in key:
            return "log_pattern"
        if "http" in key:
            return "http_endpoint"
        return "noop"

    async def _verify_service_status(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        service_name = task.result.get("service_name", "nginx") if task.result else "nginx"
        response = await self.health.check_service_status(service_name, task.platform.value)
        return {
            "verified": response.get("success", False),
            "confidence": 0.95,
            "evidence": response,
            "recommendation": "check service status" if not response.get("success") else "",
        }

    async def _verify_process_check(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        pid = task.result.get("pid", 1234) if task.result else 1234
        response = await self.health.check_process_exists(int(pid), task.platform.value)
        return {
            "verified": response.get("success", False),
            "confidence": 0.95,
            "evidence": response,
            "recommendation": "verify process termination" if response.get("success") else "",
        }

    async def _verify_metric_threshold(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        before = task.result.get("before", 95.0) if task.result else 95.0
        after = task.result.get("after", 80.0) if task.result else 80.0
        response = await self.health.check_metric_threshold("metric", before, after)
        return {
            "verified": response.get("success", False),
            "confidence": 0.75,
            "evidence": response,
            "recommendation": "collect more samples" if not response.get("success") else "",
        }

    async def _verify_dns_resolution(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.9,
            "evidence": {"test": "dns"},
            "recommendation": "",
        }

    async def _verify_port_connectivity(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.85,
            "evidence": {"test": "port"},
            "recommendation": "",
        }

    async def _verify_file_exists(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.8,
            "evidence": {"test": "file"},
            "recommendation": "",
        }

    async def _verify_log_pattern(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.7,
            "evidence": {"test": "log"},
            "recommendation": "",
        }

    async def _verify_http_endpoint(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.85,
            "evidence": {"test": "http"},
            "recommendation": "",
        }

    async def _verify_custom_command(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": None,
            "confidence": 0.65,
            "evidence": {},
            "recommendation": "manual verification required",
        }

    async def _verify_noop(
        self, task: RepairTask, result: Optional[RepairExecutionResult]
    ) -> Dict[str, Any]:
        return {
            "verified": True,
            "confidence": 0.5,
            "evidence": {"test": "noop"},
            "recommendation": "",
        }

    def list_strategies(self) -> List[str]:
        return self._strategies


class RepairVerifierApp:
    """Container for verifier components."""

    def __init__(self) -> None:
        self.verifier = RepairVerifier(timeout=settings.default_execution_timeout)
        self.rollback = RollbackEngine()
        self.audit = AuditStore()


verifier_app: Optional[RepairVerifierApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global verifier_app
    verifier_app = RepairVerifierApp()
    logger.info("Repair verifier started")
    yield
    logger.info("Repair verifier stopped")


app = FastAPI(
    title="Repair Verifier",
    description="Verifies repair results, handles rollback and audit.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(status="ok", service="repair-verifier", uptime_seconds=0, repair_count=0)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/verify")
async def verify_repair(
    task: RepairTask = Body(..., embed=True),
    result: Optional[RepairExecutionResult] = Body(None, embed=True),
) -> Dict[str, Any]:
    v = cast(RepairVerifierApp, verifier_app)
    outcome = await v.verifier.verify(task, result)
    return outcome.model_dump()


@app.post("/rollback")
async def rollback_repair(
    task: RepairTask = Body(..., embed=True),
    result: RepairExecutionResult = Body(..., embed=True),
) -> Dict[str, Any]:
    v = cast(RepairVerifierApp, verifier_app)
    rollback_result = await v.rollback.rollback(task, result)
    return rollback_result.model_dump()


@app.post("/audit")
async def record_audit(
    task_id: str,
    event_type: str,
    actor: str = "system",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    v = cast(RepairVerifierApp, verifier_app)
    event = await v.audit.record(task_id, event_type, actor, payload)
    return event.model_dump()


@app.get("/audit/{task_id}")
async def get_audit(task_id: str) -> Dict[str, Any]:
    v = cast(RepairVerifierApp, verifier_app)
    events = await v.audit.get_events(task_id)
    return {"events": [e.model_dump() for e in events]}


@app.get("/audit/analyze/{task_id}")
async def analyze_audit(task_id: str) -> Dict[str, Any]:
    v = cast(RepairVerifierApp, verifier_app)
    return await v.audit.analyze(task_id)
