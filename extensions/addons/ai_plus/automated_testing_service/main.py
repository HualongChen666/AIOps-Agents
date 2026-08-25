# -*- coding: utf-8 -*-
"""Main entry point for Automated Testing Service."""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .config import Config
from .grpc.server import AutomatedTestingRPCServer
from .test_reporter import TestReporter
from .test_runner import TestReport, TestRunner
from .test_scheduler import TestSchedule, TestScheduler

# Configure logging
Config.validate()
logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
)
logger = logging.getLogger(Config.SERVICE_NAME)

# Initialize FastAPI app
app = FastAPI(title=Config.SERVICE_NAME.replace("_", " ").title())

# Initialize service components
test_runner = TestRunner()
test_reporter = TestReporter()
test_scheduler = TestScheduler()
rpc_server = AutomatedTestingRPCServer()

# In-memory storage
test_suites: Dict[str, Dict[str, Any]] = {}
test_reports: Dict[str, TestReport] = {}
executions: Dict[str, Dict[str, Any]] = {}


# Pydantic models
class TestSuiteModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    test_path: str
    framework: str = "pytest"
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    active: bool = True


class RunTestsRequest(BaseModel):
    suite_id: str
    test_ids: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    collect_coverage: bool = False


class CreateScheduleRequest(BaseModel):
    suite_id: str
    schedule_type: str = "interval"
    schedule_expression: str = "3600"


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Config.SERVICE_NAME
    suite_count: int
    report_count: int
    schedule_count: int


class InfoResponse(BaseModel):
    service: str
    version: str = "1.0.0"
    status: str = "running"


class InvokeRequest(BaseModel):
    action: str = Field(
        ...,
        pattern="^(create_suite|get_suite|list_suites|update_suite|delete_suite|"
        "run_tests|get_report|list_reports|create_schedule|get_schedule|"
        "list_schedules|update_schedule|delete_schedule|get_coverage)$"
    )
    payload: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    success: bool
    service: str
    action: str
    result: Any


# Helper functions
def _create_suite(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test suite."""
    suite = TestSuiteModel(**payload)
    test_suites[suite.id] = suite.model_dump()
    logger.info(f"Created test suite {suite.id}: {suite.name}")
    return suite.model_dump()


def _get_suite(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a test suite by ID."""
    suite_id = payload.get("id")
    if not suite_id or suite_id not in test_suites:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return test_suites[suite_id]


def _list_suites(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all test suites."""
    active_only = payload.get("active_only", False)
    suites = list(test_suites.values())
    if active_only:
        suites = [s for s in suites if s.get("active", True)]
    return suites


def _update_suite(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a test suite."""
    suite_id = payload.pop("id", None)
    if not suite_id or suite_id not in test_suites:
        raise HTTPException(status_code=404, detail="Test suite not found")

    existing = test_suites[suite_id].copy()
    existing.update(payload)
    existing["updated_at"] = int(datetime.now().timestamp() * 1000)
    test_suites[suite_id] = existing

    logger.info(f"Updated test suite {suite_id}")
    return existing


def _delete_suite(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a test suite."""
    suite_id = payload.get("id")
    if not suite_id or suite_id not in test_suites:
        raise HTTPException(status_code=404, detail="Test suite not found")

    del test_suites[suite_id]
    logger.info(f"Deleted test suite {suite_id}")
    return {"deleted": suite_id}


def _run_tests(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run tests for a suite."""
    suite_id = payload.get("suite_id")
    if not suite_id or suite_id not in test_suites:
        raise HTTPException(status_code=404, detail="Test suite not found")

    suite = test_suites[suite_id]
    test_path = suite.get("test_path")

    if not test_path or not os.path.exists(test_path):
        raise HTTPException(status_code=400, detail="Invalid test path")

    # Create execution record
    execution_id = str(uuid4())
    executions[execution_id] = {
        "id": execution_id,
        "suite_id": suite_id,
        "status": "running",
        "started_at": int(datetime.now().timestamp() * 1000),
    }

    try:
        # Run tests
        report = test_runner.run_tests(
            suite_id=suite_id,
            test_path=test_path,
            test_ids=payload.get("test_ids"),
            tags=payload.get("tags"),
            collect_coverage=payload.get("collect_coverage", False),
        )

        # Store report
        test_reporter.create_report(report)
        test_reports[report.id] = report

        # Update execution
        executions[execution_id]["status"] = "completed"
        executions[execution_id]["report_id"] = report.id
        executions[execution_id]["completed_at"] = int(datetime.now().timestamp() * 1000)

        logger.info(f"Test execution {execution_id} completed")

        return {
            "execution_id": execution_id,
            "status": "completed",
            "report_id": report.id,
            "summary": {
                "total": report.total_tests,
                "passed": report.passed,
                "failed": report.failed,
                "skipped": report.skipped,
                "errors": report.errors,
                "duration": report.total_duration,
            },
        }

    except Exception as e:
        executions[execution_id]["status"] = "failed"
        executions[execution_id]["error"] = str(e)
        executions[execution_id]["completed_at"] = int(datetime.now().timestamp() * 1000)
        logger.error(f"Test execution {execution_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a test report."""
    report_id = payload.get("report_id")
    suite_id = payload.get("suite_id")

    if report_id:
        if report_id not in test_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        report = test_reports[report_id]
    elif suite_id:
        # Get latest report for suite
        suite_reports = [r for r in test_reports.values() if r.suite_id == suite_id]
        if not suite_reports:
            raise HTTPException(status_code=404, detail="No reports found for suite")
        report = max(suite_reports, key=lambda r: r.completed_at)
    else:
        raise HTTPException(status_code=400, detail="Must provide report_id or suite_id")

    return {
        "id": report.id,
        "suite_id": report.suite_id,
        "summary": {
            "total": report.total_tests,
            "passed": report.passed,
            "failed": report.failed,
            "skipped": report.skipped,
            "errors": report.errors,
            "duration": report.total_duration,
        },
        "timing": {
            "started_at": report.started_at,
            "completed_at": report.completed_at,
        },
        "coverage": (
            {
                "lines_covered": report.coverage.lines_covered,
                "lines_total": report.coverage.lines_total,
                "percentage": report.coverage.percentage,
            }
            if report.coverage
            else None
        ),
    }


def _list_reports(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List test reports."""
    suite_id = payload.get("suite_id")
    limit = payload.get("limit", 100)

    reports = list(test_reports.values())
    if suite_id:
        reports = [r for r in reports if r.suite_id == suite_id]

    reports.sort(key=lambda r: r.completed_at, reverse=True)
    reports = reports[:limit]

    return [
        {
            "id": r.id,
            "suite_id": r.suite_id,
            "summary": {
                "total": r.total_tests,
                "passed": r.passed,
                "failed": r.failed,
                "skipped": r.skipped,
                "errors": r.errors,
            },
            "completed_at": r.completed_at,
        }
        for r in reports
    ]


def _create_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a test schedule."""
    suite_id = payload.get("suite_id")
    if not suite_id or suite_id not in test_suites:
        raise HTTPException(status_code=404, detail="Test suite not found")

    # Define callback for scheduled runs
    def schedule_callback(suite_id: str):
        try:
            _run_tests({"suite_id": suite_id})
        except Exception as e:
            logger.error(f"Scheduled test run failed: {e}")

    schedule = test_scheduler.add_schedule(
        suite_id=suite_id,
        schedule_type=payload.get("schedule_type", "interval"),
        schedule_expression=payload.get("schedule_expression", "3600"),
        callback=schedule_callback,
    )

    return {
        "id": schedule.id,
        "suite_id": schedule.suite_id,
        "schedule_type": schedule.schedule_type,
        "schedule_expression": schedule.schedule_expression,
        "next_run": schedule.next_run,
        "active": schedule.active,
    }


def _get_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get a schedule by ID."""
    schedule_id = payload.get("id")
    schedule = test_scheduler.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "id": schedule.id,
        "suite_id": schedule.suite_id,
        "schedule_type": schedule.schedule_type,
        "schedule_expression": schedule.schedule_expression,
        "next_run": schedule.next_run,
        "active": schedule.active,
        "run_count": schedule.run_count,
    }


def _list_schedules(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List schedules."""
    suite_id = payload.get("suite_id")
    active_only = payload.get("active_only", False)

    schedules = test_scheduler.list_schedules(suite_id=suite_id, active_only=active_only)

    return [
        {
            "id": s.id,
            "suite_id": s.suite_id,
            "schedule_type": s.schedule_type,
            "schedule_expression": s.schedule_expression,
            "next_run": s.next_run,
            "active": s.active,
            "run_count": s.run_count,
        }
        for s in schedules
    ]


def _update_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a schedule."""
    schedule_id = payload.get("id")
    schedule = test_scheduler.update_schedule(
        schedule_id=schedule_id,
        active=payload.get("active"),
        schedule_expression=payload.get("schedule_expression"),
    )

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {
        "id": schedule.id,
        "suite_id": schedule.suite_id,
        "schedule_type": schedule.schedule_type,
        "schedule_expression": schedule.schedule_expression,
        "next_run": schedule.next_run,
        "active": schedule.active,
    }


def _delete_schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a schedule."""
    schedule_id = payload.get("id")
    if not test_scheduler.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"deleted": schedule_id}


def _get_coverage(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Get coverage information."""
    report_id = payload.get("report_id")
    suite_id = payload.get("suite_id")

    if report_id:
        if report_id not in test_reports:
            raise HTTPException(status_code=404, detail="Report not found")
        report = test_reports[report_id]
    elif suite_id:
        suite_reports = [r for r in test_reports.values() if r.suite_id == suite_id]
        if not suite_reports:
            raise HTTPException(status_code=404, detail="No reports found for suite")
        report = max(suite_reports, key=lambda r: r.completed_at)
    else:
        raise HTTPException(status_code=400, detail="Must provide report_id or suite_id")

    if not report.coverage:
        return {"error": "No coverage data available"}

    return {
        "suite_id": report.suite_id,
        "lines_covered": report.coverage.lines_covered,
        "lines_total": report.coverage.lines_total,
        "percentage": report.coverage.percentage,
        "file_coverage": report.coverage.file_coverage,
    }


# Register handlers
HANDLERS = {
    "create_suite": _create_suite,
    "get_suite": _get_suite,
    "list_suites": _list_suites,
    "update_suite": _update_suite,
    "delete_suite": _delete_suite,
    "run_tests": _run_tests,
    "get_report": _get_report,
    "list_reports": _list_reports,
    "create_schedule": _create_schedule,
    "get_schedule": _get_schedule,
    "list_schedules": _list_schedules,
    "update_schedule": _update_schedule,
    "delete_schedule": _delete_schedule,
    "get_coverage": _get_coverage,
}

# Register RPC handlers
for name, handler in HANDLERS.items():
    rpc_server.register(name, handler)


# FastAPI endpoints
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        service=Config.SERVICE_NAME,
        suite_count=len(test_suites),
        report_count=len(test_reports),
        schedule_count=len(test_scheduler.schedules),
    )


@app.get("/info", response_model=InfoResponse)
async def info() -> InfoResponse:
    """Service info endpoint."""
    return InfoResponse(service=Config.SERVICE_NAME)


@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    """Generic invoke endpoint for all actions."""
    handler = HANDLERS.get(req.action)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    try:
        result = handler(req.payload)
        return InvokeResponse(
            success=True, service=Config.SERVICE_NAME, action=req.action, result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invoke failed for action {req.action}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rpc/{method}")
async def rpc_call(method: str, payload: Dict[str, Any] = None):
    """RPC endpoint for inter-service communication."""
    try:
        result = await rpc_server.call(method, payload or {})
        return {"success": True, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RPC call {method} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rpc")
async def list_rpc_methods():
    """List available RPC methods."""
    return {"methods": rpc_server.list_methods()}


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info(f"Starting {Config.SERVICE_NAME}")
    await test_scheduler.start()
    await rpc_server.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info(f"Shutting down {Config.SERVICE_NAME}")
    await test_scheduler.stop()
    await rpc_server.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
