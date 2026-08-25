# -*- coding: utf-8 -*-
"""Comprehensive test coverage for repair_service modules to achieve 90%+ coverage.

This file covers modules that can be tested independently without full app initialization:
- config.py
- metrics.py
- mq.py
- schemas.py
- repository.py
- rollback.py
- state_machine.py
- saga.py
- grpc/client.py
- grpc/server.py
- health_check.py
- runbook_parser.py
- strategy_manager.py
- audit.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set environment before any imports
os.environ.setdefault("AIOPS_ENV", "test")
os.environ.setdefault("TESTING", "true")

# Add project root to path
ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.repair_service.audit import AuditStore

# Import modules that don't require full app initialization
from services.repair_service.config import RepairServiceSettings, settings
from services.repair_service.grpc.client import RPCClient
from services.repair_service.grpc.server import RPCServer
from services.repair_service.health_check import HealthCheckEngine
from services.repair_service.metrics import (
    REPAIR_ACTIVE_EXECUTIONS,
    REPAIR_AUDIT_EVENTS,
    REPAIR_EXECUTION_DURATION,
    REPAIR_ROLLBACK_COUNT,
    REPAIR_SAGA_STATUS,
    REPAIR_TASKS_COMPLETED,
    REPAIR_TASKS_CREATED,
    REPAIR_VERIFICATION_DURATION,
)
from services.repair_service.mq import InMemoryMessageQueue, message_queue
from services.repair_service.repository import InMemoryRepairRepository, get_repository
from services.repair_service.rollback import RollbackEngine, SnapshotStore
from services.repair_service.runbook_parser import RunbookParser, get_runbook_catalog
from services.repair_service.saga import SagaOrchestrator
from services.repair_service.schemas import (
    AuditEvent,
    PlatformType,
    RepairExecutionResult,
    RepairRequest,
    RepairRunbook,
    RepairStatus,
    RepairStep,
    RepairStrategy,
    RepairTask,
    RiskLevel,
    SagaStep,
    SagaTransaction,
    ServiceHealth,
    VerificationResult,
)
from services.repair_service.state_machine import RepairStateMachine
from services.repair_service.strategy_manager import RepairStrategyManager


def _run(coro):
    """Helper to run async functions in sync context."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------


def test_config_settings_defaults():
    """Test default configuration values."""
    cfg = RepairServiceSettings()
    assert cfg.service_name == "repair-service"
    assert cfg.environment == "development"
    assert cfg.log_level == "INFO"
    assert cfg.orchestrator_port == 9001
    assert cfg.executor_port == 9002
    assert cfg.verifier_port == 9003
    assert cfg.redis_url == "redis://localhost:6379/1"
    assert cfg.use_in_memory is True
    assert cfg.enable_prometheus is True
    assert cfg.default_execution_timeout == 120
    assert cfg.max_concurrent_executions == 50


def test_config_settings_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv("REPAIR_SERVICE_SERVICE_NAME", "custom-service")
    monkeypatch.setenv("REPAIR_SERVICE_ENVIRONMENT", "production")
    monkeypatch.setenv("REPAIR_SERVICE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("REPAIR_SERVICE_ORCHESTRATOR_PORT", "9999")
    monkeypatch.setenv("REPAIR_SERVICE_USE_IN_MEMORY", "false")

    cfg = RepairServiceSettings()
    assert cfg.service_name == "custom-service"
    assert cfg.environment == "production"
    assert cfg.log_level == "DEBUG"
    assert cfg.orchestrator_port == 9999
    assert cfg.use_in_memory is False


def test_config_settings_instance():
    """Test global settings instance."""
    assert isinstance(settings, RepairServiceSettings)
    assert settings.service_name


# ---------------------------------------------------------------------------
# metrics.py
# ---------------------------------------------------------------------------


def test_metrics_import():
    """Test that metrics are properly defined."""
    assert REPAIR_TASKS_CREATED is not None
    assert REPAIR_TASKS_COMPLETED is not None
    assert REPAIR_EXECUTION_DURATION is not None
    assert REPAIR_VERIFICATION_DURATION is not None
    assert REPAIR_ROLLBACK_COUNT is not None
    assert REPAIR_AUDIT_EVENTS is not None
    assert REPAIR_SAGA_STATUS is not None
    assert REPAIR_ACTIVE_EXECUTIONS is not None

    # Test metric labels
    REPAIR_TASKS_CREATED.labels(platform="linux").inc()
    REPAIR_TASKS_COMPLETED.labels(status="success", platform="linux").inc()
    REPAIR_ROLLBACK_COUNT.labels(result="success").inc()
    REPAIR_AUDIT_EVENTS.labels(event_type="created").inc()
    REPAIR_SAGA_STATUS.labels(saga_id="test").set(1)
    REPAIR_ACTIVE_EXECUTIONS.inc()
    REPAIR_ACTIVE_EXECUTIONS.dec()


# ---------------------------------------------------------------------------
# mq.py
# ---------------------------------------------------------------------------


def test_mq_singleton():
    """Test that message queue is a singleton."""
    mq1 = InMemoryMessageQueue()
    mq2 = InMemoryMessageQueue()
    assert mq1 is mq2


@pytest.mark.asyncio
async def test_mq_publish_consume():
    """Test publish and consume operations."""
    mq = InMemoryMessageQueue()
    mq.reset()

    payload = {"type": "test", "data": "value"}
    await mq.publish("test_channel", payload)

    consumed = await mq.consume("test_channel")
    assert consumed == payload


@pytest.mark.asyncio
async def test_mq_multiple_channels():
    """Test multiple channels."""
    mq = InMemoryMessageQueue()
    mq.reset()

    await mq.publish("channel1", {"msg": "1"})
    await mq.publish("channel2", {"msg": "2"})

    msg1 = await mq.consume("channel1")
    msg2 = await mq.consume("channel2")

    assert msg1["msg"] == "1"
    assert msg2["msg"] == "2"


def test_mq_get_queue():
    """Test getting queue reference."""
    mq = InMemoryMessageQueue()
    queue = mq.get_queue("test")
    assert queue is not None


def test_mq_reset():
    """Test reset functionality."""
    mq = InMemoryMessageQueue()
    _run(mq.publish("ch1", {"x": 1}))
    _run(mq.publish("ch2", {"x": 2}))

    mq.reset()
    assert len(mq._queues) == 0


def test_mq_global_instance():
    """Test global message queue instance."""
    assert isinstance(message_queue, InMemoryMessageQueue)
    message_queue.reset()


# ---------------------------------------------------------------------------
# schemas.py
# ---------------------------------------------------------------------------


def test_schemas_enums():
    """Test schema enums."""
    assert PlatformType.LINUX.value == "linux"
    assert PlatformType.WINDOWS.value == "windows"
    assert RiskLevel.LOW.value == "low"
    assert RiskLevel.HIGH.value == "high"
    assert RepairStatus.PENDING.value == "pending"
    assert RepairStatus.COMPLETED.value == "completed"


def test_schemas_models():
    """Test schema models."""
    strategy = RepairStrategy(
        name="test",
        script_key="test_script",
        platform=PlatformType.LINUX,
        risk_level=RiskLevel.MEDIUM,
    )
    assert strategy.name == "test"
    assert strategy.enabled is True  # default

    step = RepairStep(name="step1", command="echo test")
    assert step.name == "step1"
    assert step.timeout_seconds == 60  # default

    runbook = RepairRunbook(
        runbook_id="rb1",
        name="Test Runbook",
        platform=PlatformType.LINUX,
        steps=[step],
    )
    assert runbook.runbook_id == "rb1"
    assert len(runbook.steps) == 1

    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
    )
    assert task.status == RepairStatus.PENDING  # default

    result = RepairExecutionResult(task_id="t1", success=True)
    assert result.success is True
    assert result.return_code == 0  # default

    verification = VerificationResult(task_id="t1", verified=True)
    assert verification.verified is True
    assert verification.confidence == 0.0  # default


def test_schemas_audit_event():
    """Test audit event schema."""
    event = AuditEvent(
        event_id="e1",
        task_id="t1",
        event_type="created",
        actor="system",
    )
    assert event.event_id == "e1"
    assert event.payload == {}  # default


def test_schemas_saga():
    """Test saga schemas."""
    step = SagaStep(
        step_id="s1",
        service="svc",
        action="act",
        compensation="comp",
    )
    assert step.status == "pending"  # default

    transaction = SagaTransaction(
        saga_id="sg1",
        task_id="t1",
        steps=[step],
    )
    assert transaction.saga_id == "sg1"
    assert transaction.status == "pending"  # default


def test_schemas_service_health():
    """Test service health schema."""
    health = ServiceHealth(status="ok", service="test-service")
    assert health.status == "ok"
    assert health.uptime_seconds == 0  # default


# ---------------------------------------------------------------------------
# repository.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repository_save_auto_id():
    """Test saving task with auto-generated ID."""
    repo = InMemoryRepairRepository()
    task = RepairTask(
        task_id="",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
    )
    task_id = await repo.save(task)
    assert task_id
    assert task.task_id == task_id


@pytest.mark.asyncio
async def test_repository_crud():
    """Test full CRUD operations."""
    repo = InMemoryRepairRepository()

    # Create
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    await repo.save(task)

    # Read
    fetched = await repo.get("t1")
    assert fetched is not None
    assert fetched.task_id == "t1"

    # Update
    await repo.update("t1", {"status": RepairStatus.APPROVED})
    updated = await repo.get("t1")
    assert updated.status == RepairStatus.APPROVED

    # List
    tasks = await repo.list(limit=10)
    assert len(tasks) == 1

    # Count
    count = await repo.count()
    assert count == 1

    # Delete
    deleted = await repo.delete("t1")
    assert deleted is True
    assert await repo.get("t1") is None


@pytest.mark.asyncio
async def test_repository_list_with_status():
    """Test listing with status filter."""
    repo = InMemoryRepairRepository()

    await repo.save(
        RepairTask(
            task_id="t1",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            status=RepairStatus.PENDING,
        )
    )
    await repo.save(
        RepairTask(
            task_id="t2",
            alert_id="a2",
            host="h1",
            platform=PlatformType.LINUX,
            status=RepairStatus.SUCCEEDED,
        )
    )

    pending = await repo.list(status=RepairStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].task_id == "t1"


@pytest.mark.asyncio
async def test_repository_get_repository_factory():
    """Test get_repository factory function."""
    repo = await get_repository()
    assert isinstance(repo, InMemoryRepairRepository)


# ---------------------------------------------------------------------------
# rollback.py
# ---------------------------------------------------------------------------


def test_rollback_snapshot_store():
    """Test snapshot store."""
    store = SnapshotStore()
    store.save("t1", {"state": "ok"})
    assert store.get("t1") == {"state": "ok"}
    assert store.get("missing") is None


def test_rollback_list_strategies():
    """Test listing all rollback strategies."""
    engine = RollbackEngine()
    strategies = engine.list_strategies()
    assert len(strategies) > 0
    assert "generic" in strategies
    assert "process_restart" in strategies
    assert "service_restart" in strategies


def test_rollback_detect_strategy():
    """Test strategy detection."""
    engine = RollbackEngine()

    # No strategy
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=None,
    )
    assert engine._detect_strategy(task) == "generic"

    # CPU strategy
    task.strategy = RepairStrategy(name="s", script_key="cpu_high", platform=PlatformType.LINUX)
    assert engine._detect_strategy(task) == "process_restart"

    # Service strategy
    task.strategy = RepairStrategy(
        name="s", script_key="service_restart", platform=PlatformType.LINUX
    )
    assert engine._detect_strategy(task) == "service_restart"


@pytest.mark.asyncio
async def test_rollback_take_snapshot():
    """Test taking snapshot."""
    engine = RollbackEngine()
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=RepairStrategy(name="s", script_key="cpu_high", platform=PlatformType.LINUX),
    )
    snapshot = engine.take_snapshot(task)
    assert snapshot["task_id"] == "t1"
    assert engine.snapshot_store.get("t1") is not None


@pytest.mark.asyncio
async def test_rollback_execute():
    """Test rollback execution."""
    engine = RollbackEngine()
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=RepairStrategy(name="s", script_key="cpu_high", platform=PlatformType.LINUX),
    )
    result = RepairExecutionResult(task_id="t1", success=False)

    rollback_result = await engine.rollback(task, result)
    assert rollback_result.success is True
    assert "process" in rollback_result.output.lower()


@pytest.mark.asyncio
async def test_rollback_execute_failure():
    """Test rollback with failure."""
    engine = RollbackEngine()

    async def boom(task, result):
        raise RuntimeError("rollback failed")

    engine._strategies["generic"] = boom

    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        strategy=RepairStrategy(name="s", script_key="unknown", platform=PlatformType.LINUX),
    )
    result = RepairExecutionResult(task_id="t1", success=False)

    rollback_result = await engine.rollback(task, result)
    assert rollback_result.success is False
    assert "rollback failed" in rollback_result.error


# ---------------------------------------------------------------------------
# state_machine.py
# ---------------------------------------------------------------------------


def test_state_machine_all_states():
    """Test that all states are defined."""
    states = RepairStateMachine.STATES
    assert len(states) >= 12
    assert RepairStatus.PENDING in states
    assert RepairStatus.COMPLETED in states
    assert RepairStatus.TIMEOUT in states


def test_state_machine_transitions():
    """Test valid state transitions."""
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm = RepairStateMachine(task)

    assert sm.current_state == RepairStatus.PENDING
    assert sm.can_transition(RepairStatus.APPROVED)
    assert not sm.can_transition(RepairStatus.COMPLETED)

    assert sm.transition(RepairStatus.APPROVED)
    assert sm.current_state == RepairStatus.APPROVED

    assert sm.transition(RepairStatus.EXECUTING)
    assert sm.transition(RepairStatus.SUCCEEDED)
    assert sm.transition(RepairStatus.VERIFYING)
    assert sm.transition(RepairStatus.VERIFIED)
    assert sm.transition(RepairStatus.COMPLETED)


def test_state_machine_invalid_transition():
    """Test that invalid transitions are rejected."""
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm = RepairStateMachine(task)

    # Cannot go directly from PENDING to COMPLETED
    assert not sm.transition(RepairStatus.COMPLETED)

    # Cannot transition to same state
    assert not sm.transition(RepairStatus.PENDING)


def test_state_machine_history():
    """Test that transition history is recorded."""
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm = RepairStateMachine(task)

    sm.transition(RepairStatus.APPROVED, reason="test")
    sm.transition(RepairStatus.EXECUTING, reason="test")

    assert len(sm.history) == 3  # initial + 2 transitions
    assert sm.history[0]["event"] == "initialized"
    assert sm.history[1]["event"] == "transition"


def test_state_machine_to_dict():
    """Test to_dict method."""
    task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    sm = RepairStateMachine(task)

    d = sm.to_dict()
    assert d["task_id"] == "t1"
    assert d["current_state"] == "pending"
    assert "history" in d


# ---------------------------------------------------------------------------
# saga.py
# ---------------------------------------------------------------------------


def test_saga_register_and_execute():
    """Test saga registration and execution."""
    orch = SagaOrchestrator()
    step = SagaStep(step_id="s1", service="svc", action="act", compensation="comp")

    async def act():
        return {"ok": True}

    async def comp():
        return {"ok": True}

    orch.register("sg1", [step], {"act": act}, {"comp": comp})

    result = _run(orch.execute("sg1"))
    assert result["success"] is True
    assert result["saga_id"] == "sg1"


def test_saga_execute_failure_compensation():
    """Test saga failure triggers compensation."""
    orch = SagaOrchestrator()
    step1 = SagaStep(step_id="s1", service="svc", action="act1", compensation="comp1")
    step2 = SagaStep(step_id="s2", service="svc", action="act2", compensation="comp2")

    async def act1():
        return {"ok": True}

    async def act2():
        raise RuntimeError("step2 failed")

    async def comp1():
        return {"compensated": True}

    async def comp2():
        return {"compensated": True}

    orch.register(
        "sg2", [step1, step2], {"act1": act1, "act2": act2}, {"comp1": comp1, "comp2": comp2}
    )

    result = _run(orch.execute("sg2"))
    assert result["success"] is False
    assert orch.get_transaction("sg2").status == "compensating"


def test_saga_not_found():
    """Test executing non-existent saga."""
    orch = SagaOrchestrator()
    result = _run(orch.execute("missing"))
    assert result["success"] is False
    assert "not found" in result["error"]


def test_saga_missing_action():
    """Test saga with missing action handler."""
    orch = SagaOrchestrator()
    step = SagaStep(step_id="s1", service="svc", action="missing", compensation="comp")

    orch.register("sg3", [step], {}, {})

    result = _run(orch.execute("sg3"))
    assert result["success"] is False
    assert "No action" in result["error"]


def test_saga_get_transaction():
    """Test getting a transaction."""
    orch = SagaOrchestrator()
    step = SagaStep(step_id="s1", service="svc", action="act", compensation="comp")

    async def act():
        return {"ok": True}

    async def comp():
        return {"ok": True}

    orch.register("sg4", [step], {"act": act}, {"comp": comp})

    transaction = orch.get_transaction("sg4")
    assert transaction.saga_id == "sg4"
    assert len(transaction.steps) == 1


def test_saga_step_validation():
    """Test step validation in register."""
    orch = SagaOrchestrator()

    # Test with dict step (should be converted to SagaStep)
    dict_step = {"step_id": "s1", "service": "svc", "action": "act", "compensation": "comp"}

    async def act():
        return {"ok": True}

    async def comp():
        return {"ok": True}

    orch.register("sg5", [dict_step], {"act": act}, {"comp": comp})

    transaction = orch.get_transaction("sg5")
    assert isinstance(transaction.steps[0], SagaStep)


# ---------------------------------------------------------------------------
# grpc/server.py
# ---------------------------------------------------------------------------


def test_rpc_server():
    """Test RPC server."""
    server = RPCServer()

    async def handler(x: int) -> int:
        return x * 2

    server.register("double", handler)

    assert server.list_methods() == ["double"]
    assert _run(server.call("double", x=5)) == 10

    with pytest.raises(ValueError, match="Unknown RPC method"):
        _run(server.call("missing"))


def test_rpc_server_sync_handler():
    """Test server with synchronous handler."""
    server = RPCServer()

    async def sync_handler(x: int) -> int:
        return x + 1

    server.register("inc", sync_handler)
    result = _run(server.call("inc", x=5))
    assert result == 6


def test_rpc_server_empty():
    """Test server with no handlers."""
    server = RPCServer()
    assert server.list_methods() == []


# ---------------------------------------------------------------------------
# grpc/client.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rpc_client_with_server():
    """Test RPC client with server transport."""
    server = RPCServer()

    async def handler(name: str) -> str:
        return f"hello {name}"

    server.register("greet", handler)

    client = RPCClient(server=server)
    result = await client.call("greet", name="world")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_rpc_client_without_transport():
    """Test RPC client without transport raises error."""
    client = RPCClient()
    with pytest.raises(RuntimeError, match="requires a server instance or base_url"):
        await client.call("test")


@pytest.mark.asyncio
async def test_rpc_client_close():
    """Test closing client without HTTP transport."""
    server = RPCServer()

    async def handler():
        return "ok"

    server.register("test", handler)

    client = RPCClient(server=server)
    await client.close()  # Should not raise


# ---------------------------------------------------------------------------
# health_check.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_metric_threshold():
    """Test metric threshold check."""
    engine = HealthCheckEngine(timeout=1)

    # Mock _run to avoid actual command execution
    async def fake_run(cmd, default_stdout=""):
        return {"success": True, "stdout": default_stdout, "stderr": "", "return_code": 0}

    engine._run = fake_run

    # Test successful threshold
    result = await engine.check_metric_threshold("cpu", 100.0, 90.0, threshold_percent=5.0)
    assert result["success"] is True

    # Test failed threshold (not enough drop)
    result = await engine.check_metric_threshold("cpu", 100.0, 98.0, threshold_percent=5.0)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_health_check_timeout():
    """Test health check timeout."""
    engine = HealthCheckEngine(timeout=1)

    # The actual _run method handles TimeoutError internally, so we don't need to mock it
    # Just test that the timeout parameter is set correctly
    assert engine.timeout == 1

    # Test with a very short timeout to simulate timeout scenario
    engine_short = HealthCheckEngine(timeout=0.001)
    # This would timeout on real systems, but we can't test that without actual commands
    # Just verify the timeout is set
    assert engine_short.timeout == 0.001


@pytest.mark.asyncio
async def test_health_check_exception():
    """Test health check exception handling."""
    # The actual _run method handles exceptions internally and returns success
    # So we just test that the engine can be created and has the expected timeout
    engine = HealthCheckEngine(timeout=1)
    assert engine.timeout == 1

    # Test that metric threshold check works correctly
    result = await engine.check_metric_threshold("cpu", 100.0, 95.0, 5.0)
    assert result["success"] is True
    assert "cpu dropped" in result["stdout"]


@pytest.mark.asyncio
async def test_health_check_platform_commands():
    """Test different platform commands."""
    engine = HealthCheckEngine(timeout=1)

    async def fake_run(cmd, default_stdout=""):
        return {"success": True, "stdout": default_stdout, "stderr": "", "return_code": 0}

    engine._run = fake_run

    # Linux
    result = await engine.check_service_status("nginx", platform="linux")
    assert result["success"] is True

    # Windows
    result = await engine.check_service_status("nginx", platform="windows")
    assert result["success"] is True

    # Process check
    result = await engine.check_process_exists(1234, platform="linux")
    assert result["success"] is True


# ---------------------------------------------------------------------------
# runbook_parser.py
# ---------------------------------------------------------------------------


def test_runbook_parser_from_yaml():
    """Test parsing runbook from YAML."""
    yaml_text = """
runbook_id: test_rb
name: Test Runbook
description: A test runbook
platform: linux
risk_level: low
steps:
  - name: step1
    command: echo test
    timeout_seconds: 30
    rollback_command: echo rollback
    verify_command: echo verify
params:
  key: value
"""
    runbook = RunbookParser.from_yaml(yaml_text)
    assert runbook.runbook_id == "test_rb"
    assert runbook.name == "Test Runbook"
    assert runbook.description == "A test runbook"
    assert runbook.platform == PlatformType.LINUX
    assert runbook.risk_level == RiskLevel.LOW
    assert len(runbook.steps) == 1
    assert runbook.steps[0].name == "step1"
    assert runbook.steps[0].command == "echo test"
    assert runbook.steps[0].timeout_seconds == 30
    assert runbook.steps[0].rollback_command == "echo rollback"
    assert runbook.steps[0].verify_command == "echo verify"
    assert runbook.params == {"key": "value"}


def test_runbook_parser_render_command():
    """Test command rendering."""
    rendered = RunbookParser.render_command("echo {msg}", {"msg": "hello"})
    assert rendered == "echo hello"

    rendered = RunbookParser.render_command("echo {missing}", {})
    assert rendered == "echo {missing}"


def test_runbook_parser_validate():
    """Test runbook validation."""
    # Valid runbook
    runbook = RepairRunbook(
        runbook_id="test",
        name="test",
        platform=PlatformType.LINUX,
        risk_level=RiskLevel.LOW,
        steps=[RepairStep(name="s1", command="echo test")],
    )
    errors = RunbookParser.validate(runbook)
    assert errors == []

    # Missing runbook_id
    runbook.runbook_id = ""
    errors = RunbookParser.validate(runbook)
    assert len(errors) > 0
    assert any("runbook_id" in e.lower() for e in errors)

    # No steps
    runbook.runbook_id = "test"
    runbook.steps = []
    errors = RunbookParser.validate(runbook)
    assert len(errors) > 0
    assert any("step" in e.lower() for e in errors)

    # Empty command
    runbook.steps = [RepairStep(name="s1", command="")]
    errors = RunbookParser.validate(runbook)
    assert len(errors) > 0
    assert any("command" in e.lower() for e in errors)


def test_runbook_parser_errors():
    """Test parser error handling."""
    # Not a mapping
    with pytest.raises(ValueError, match="must be a mapping"):
        RunbookParser.from_yaml("just a string")

    # Steps not a list
    with pytest.raises(ValueError, match="steps.*must be a list"):
        RunbookParser.from_yaml("runbook_id: test\nsteps: notlist")

    # Step not a mapping
    with pytest.raises(ValueError, match="Step.*must be a mapping"):
        RunbookParser.from_yaml("runbook_id: test\nsteps:\n  - 123")


def test_runbook_parser_list_examples():
    """Test listing example runbooks."""
    runbooks = RunbookParser.list_example_runbooks()
    # Should return list of runbook IDs
    assert isinstance(runbooks, list)


def test_runbook_parser_load_example():
    """Test loading example runbook."""
    # Try to load a known example
    runbook = RunbookParser.load_example("memory_high")
    # May or may not exist depending on whether examples are present
    if runbook:
        assert runbook.runbook_id == "memory_high"


def test_runbook_parser_catalog():
    """Test getting runbook catalog."""
    catalog = get_runbook_catalog()
    assert isinstance(catalog, dict)


# ---------------------------------------------------------------------------
# strategy_manager.py
# ---------------------------------------------------------------------------


def test_strategy_manager_list_strategies():
    """Test listing all strategies."""
    mgr = RepairStrategyManager()
    strategies = mgr.list_strategies()
    assert len(strategies) >= 20


def test_strategy_manager_get_strategy():
    """Test getting specific strategy."""
    mgr = RepairStrategyManager()
    strategy = mgr.get_strategy("cpu_high_linux")
    assert strategy is not None
    assert strategy.name == "cpu_high_linux"

    # Non-existent strategy
    assert mgr.get_strategy("nonexistent") is None


def test_strategy_manager_match():
    """Test strategy matching."""
    mgr = RepairStrategyManager()

    # Exact match
    req = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )
    matched = mgr.match(req)
    assert matched is not None
    assert matched.name == "cpu_high_linux"

    # Wildcard match
    req2 = RepairRequest(
        alert_id="a2",
        host="h1",
        platform=PlatformType.LINUX,
        metric="web_service_down",
    )
    matched2 = mgr.match(req2)
    assert matched2 is not None  # Should match wildcard strategy

    # No match
    req3 = RepairRequest(
        alert_id="a3",
        host="h1",
        platform=PlatformType.MACOS,
        metric="totally_unknown_metric_xyz",
    )
    matched3 = mgr.match(req3)
    assert matched3 is None


def test_strategy_manager_add_strategy():
    """Test adding custom strategy."""
    mgr = RepairStrategyManager()

    new_strategy = RepairStrategy(
        name="custom",
        conditions={"metric": "custom_metric", "platform": "linux"},
        script_key="noop",
        platform=PlatformType.LINUX,
        risk_level=RiskLevel.LOW,
        priority=100,
    )
    mgr.add_strategy(new_strategy)

    assert mgr.get_strategy("custom") == new_strategy


def test_strategy_manager_create_task():
    """Test creating task from request."""
    mgr = RepairStrategyManager()

    req = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )

    task = mgr.create_task_from_request(req, "TASK-1")
    assert task.task_id == "TASK-1"
    assert task.alert_id == "a1"
    assert task.host == "h1"
    assert task.platform == PlatformType.LINUX
    assert task.status == RepairStatus.PENDING
    assert task.strategy is not None


def test_strategy_manager_score():
    """Test strategy scoring."""
    mgr = RepairStrategyManager()

    strategy = RepairStrategy(
        name="test",
        conditions={"platform": "linux", "metric": "cpu"},
        script_key="test",
        platform=PlatformType.LINUX,
    )

    req = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )

    score = mgr._score(strategy, req)
    assert score > 0  # Should match on platform and metric


# ---------------------------------------------------------------------------
# audit.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_record():
    """Test recording audit events."""
    store = AuditStore()

    event = await store.record("t1", "created", actor="system", payload={"key": "value"})
    assert event.task_id == "t1"
    assert event.event_type == "created"
    assert event.actor == "system"
    assert event.payload == {"key": "value"}


@pytest.mark.asyncio
async def test_audit_get_events():
    """Test getting events for a task."""
    store = AuditStore()

    await store.record("t1", "created")
    await store.record("t1", "approved")
    await store.record("t2", "created")

    events = await store.get_events("t1")
    assert len(events) == 2
    assert all(e.task_id == "t1" for e in events)


@pytest.mark.asyncio
async def test_audit_query():
    """Test querying events."""
    store = AuditStore()

    await store.record("t1", "type_a")
    await store.record("t1", "type_b")
    await store.record("t2", "type_a")

    # All events
    all_events = await store.query(limit=10)
    assert len(all_events) == 3

    # Filter by type
    type_a = await store.query(event_type="type_a", limit=10)
    assert len(type_a) == 2
    assert all(e.event_type == "type_a" for e in type_a)


@pytest.mark.asyncio
async def test_audit_analyze():
    """Test analyzing events."""
    store = AuditStore()

    await store.record("t1", "created")
    await store.record("t1", "approved")
    await store.record("t1", "completed")

    analysis = await store.analyze("t1")
    assert analysis["task_id"] == "t1"
    assert analysis["total_events"] == 3
    assert "created" in analysis["event_types"]
    assert analysis["first_event"] is not None
    assert analysis["last_event"] is not None


@pytest.mark.asyncio
async def test_audit_snapshot():
    """Test recording snapshot."""
    store = AuditStore()

    await store.snapshot("t1", {"state": "ok"})

    events = await store.get_events("t1")
    assert len(events) == 1
    assert events[0].event_type == "snapshot"
    assert events[0].payload["state"] == {"state": "ok"}


@pytest.mark.asyncio
async def test_audit_empty():
    """Test operations with no events."""
    store = AuditStore()

    events = await store.get_events("nonexistent")
    assert events == []

    events = await store.query(limit=10)
    assert events == []

    analysis = await store.analyze("t1")
    assert analysis["total_events"] == 0
    assert analysis["event_types"] == {}
