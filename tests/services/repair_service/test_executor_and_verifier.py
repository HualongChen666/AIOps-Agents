# -*- coding: utf-8 -*-
"""Tests for repair executor and verifier."""

from __future__ import annotations

import pytest

from services.repair_service.executor import RunbookExecutor
from services.repair_service.runbook_parser import RunbookParser
from services.repair_service.schemas import (
    PlatformType,
    RepairRequest,
    RepairTask,
)
from services.repair_service.verifier import RepairVerifierApp
from services.repair_service.verifier import app as verifier_app


class TestRunbookExecutor:
    @pytest.fixture
    def executor(self):
        return RunbookExecutor(dry_run=True)

    @pytest.mark.asyncio
    async def test_execute_example_runbook(self, executor):
        runbook = RunbookParser.load_example("memory_high")
        assert runbook is not None
        result = await executor.execute("t1", runbook, {"threshold": 90})
        assert result.success
        assert result.executed_steps == len(runbook.steps)

    @pytest.mark.asyncio
    async def test_execute_missing_runbook(self, executor):
        from services.repair_service.schemas import RepairRunbook

        runbook = RepairRunbook(runbook_id="missing", name="missing")
        result = await executor.execute("t1", runbook)
        assert not result.success


class TestStrategyEngine:
    @pytest.mark.asyncio
    async def test_execute_strategy(self):
        from services.repair_service.executor import StrategyEngine

        engine = StrategyEngine()
        request = RepairRequest(
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            metric="cpu_percent",
        )
        strategy = engine.manager.match(request)
        assert strategy is not None
        result = await engine.executor.execute_strategy("t1", strategy, request.params)
        assert result.success


class TestVerifier:
    def test_verifier_app(self):
        from fastapi.testclient import TestClient

        client = TestClient(verifier_app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "repair-verifier"

    @pytest.mark.asyncio
    async def test_verify_task(self):
        from services.repair_service.strategy_manager import RepairStrategyManager

        manager = RepairStrategyManager()
        request = RepairRequest(
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            metric="cpu_percent",
        )
        strategy = manager.match(request)
        task = RepairTask(
            task_id="t1",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            strategy=strategy,
        )
        vapp = RepairVerifierApp()
        result = await vapp.verifier.verify(task)
        assert result.verified in (True, False, None)
        assert result.strategy == "process_check"

    @pytest.mark.asyncio
    async def test_rollback(self):
        from services.repair_service.schemas import RepairExecutionResult

        vapp = RepairVerifierApp()
        task = RepairTask(
            task_id="t1",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
        )
        result = RepairExecutionResult(task_id="t1", success=False)
        rollback = await vapp.rollback.rollback(task, result)
        assert rollback.success


class TestAudit:
    @pytest.mark.asyncio
    async def test_record_and_query(self):
        from services.repair_service.audit import AuditStore

        store = AuditStore()
        event = await store.record("t1", "created", "tester", {"x": 1})
        assert event.task_id == "t1"
        events = await store.get_events("t1")
        assert len(events) == 1
