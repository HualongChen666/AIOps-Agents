# -*- coding: utf-8 -*-
"""Repair executor microservice."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import Body, FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.repair_service.config import settings
from services.repair_service.metrics import (
    REPAIR_ACTIVE_EXECUTIONS,
    REPAIR_EXECUTION_DURATION,
    REPAIR_TASKS_COMPLETED,
)
from services.repair_service.runbook_parser import RunbookParser, get_runbook_catalog
from services.repair_service.schemas import (
    RepairExecutionResult,
    RepairRequest,
    RepairRunbook,
    RepairStep,
    RepairStrategy,
    ServiceHealth,
)
from services.repair_service.strategy_manager import RepairStrategyManager


class RunbookExecutor:
    """Parse and execute YAML runbooks with batch/parallel support."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    async def execute(
        self,
        task_id: str,
        runbook: RepairRunbook,
        params: Optional[Dict[str, Any]] = None,
    ) -> RepairExecutionResult:
        start = time.perf_counter()
        REPAIR_ACTIVE_EXECUTIONS.inc()
        try:
            merged_params = {**runbook.params, **(params or {})}
            errors = RunbookParser.validate(runbook)
            if errors:
                return RepairExecutionResult(
                    task_id=task_id,
                    success=False,
                    error="; ".join(errors),
                    duration_seconds=time.perf_counter() - start,
                    return_code=-1,
                )

            results = await asyncio.gather(
                *[self._execute_step(step, merged_params) for step in runbook.steps],
                return_exceptions=True,
            )

            success = all(isinstance(r, dict) and r.get("success", False) for r in results)
            outputs = [str(r.get("stdout", "")) if isinstance(r, dict) else str(r) for r in results]
            errors_list = [
                str(r.get("stderr", "")) if isinstance(r, dict) else str(r)
                for r in results
                if (isinstance(r, dict) and r.get("stderr")) or not isinstance(r, dict)
            ]

            return RepairExecutionResult(
                task_id=task_id,
                success=success,
                output="\n".join(outputs),
                error="; ".join(errors_list),
                duration_seconds=time.perf_counter() - start,
                return_code=0 if success else 1,
                executed_steps=len(runbook.steps),
            )
        finally:
            REPAIR_ACTIVE_EXECUTIONS.dec()

    async def _execute_step(
        self,
        step: RepairStep,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        command = RunbookParser.render_command(step.command, params)
        if self.dry_run:
            return await self._simulate(command, step.timeout_seconds)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=step.timeout_seconds
            )
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
                "return_code": proc.returncode if proc.returncode is not None else -1,
            }
        except asyncio.TimeoutError:
            return {"success": False, "stdout": "", "stderr": "timeout", "return_code": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "return_code": -1}

    async def _simulate(self, command: str, timeout: int) -> Dict[str, Any]:
        """Simulate execution for safety and performance testing."""
        await asyncio.sleep(0.001)
        if "fail" in command.lower() or "error" in command.lower():
            return {
                "success": False,
                "stdout": "",
                "stderr": f"simulated failure: {command}",
                "return_code": 1,
            }
        return {"success": True, "stdout": f"simulated: {command}", "stderr": "", "return_code": 0}

    async def execute_strategy(
        self,
        task_id: str,
        strategy: RepairStrategy,
        params: Optional[Dict[str, Any]] = None,
    ) -> RepairExecutionResult:
        runbook = RunbookParser.load_example(strategy.script_key)
        if not runbook:
            return RepairExecutionResult(
                task_id=task_id,
                success=False,
                error=f"Runbook not found for strategy {strategy.name}",
                duration_seconds=0.0,
                return_code=-1,
            )
        merged = {**strategy.conditions, **(params or {})}
        result = await self.execute(task_id, runbook, merged)
        REPAIR_EXECUTION_DURATION.labels(platform=strategy.platform.value).observe(
            result.duration_seconds
        )
        REPAIR_TASKS_COMPLETED.labels(
            status="success" if result.success else "failed", platform=strategy.platform.value
        ).inc()
        return result


class StrategyEngine:
    """Exposed strategy execution engine."""

    def __init__(self) -> None:
        self.manager = RepairStrategyManager()
        self.executor = RunbookExecutor(dry_run=settings.use_in_memory)


strategy_engine: Optional[StrategyEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global strategy_engine
    strategy_engine = StrategyEngine()
    logger.info("Repair executor started")
    yield
    logger.info("Repair executor stopped")


app = FastAPI(
    title="Repair Executor",
    description="Executes repair runbooks and strategies.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    return ServiceHealth(status="ok", service="repair-executor", uptime_seconds=0, repair_count=0)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/scripts")
async def list_scripts() -> Dict[str, Any]:
    return {"scripts": get_runbook_catalog()}


@app.get("/strategies")
async def list_strategies() -> Dict[str, Any]:
    engine = cast(StrategyEngine, strategy_engine)
    return {"strategies": [s.model_dump() for s in engine.manager.list_strategies()]}


@app.post("/execute/runbook")
async def execute_runbook(task_id: str, runbook: RepairRunbook) -> Dict[str, Any]:
    engine = cast(StrategyEngine, strategy_engine)
    result = await engine.executor.execute(task_id, runbook)
    return result.model_dump()


@app.post("/execute/strategy")
async def execute_strategy(
    request: RepairRequest = Body(..., embed=True),
    strategy: RepairStrategy = Body(..., embed=True),
) -> Dict[str, Any]:
    engine = cast(StrategyEngine, strategy_engine)
    result = await engine.executor.execute_strategy(
        request.alert_id,
        strategy,
        request.params,
    )
    return result.model_dump()
