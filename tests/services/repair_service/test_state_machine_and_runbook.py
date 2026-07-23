# -*- coding: utf-8 -*-
"""Tests for repair state machine and runbook parser."""

from __future__ import annotations

from services.repair_service.runbook_parser import RunbookParser, get_runbook_catalog
from services.repair_service.schemas import (
    PlatformType,
    RepairRequest,
    RepairStatus,
    RepairTask,
    RiskLevel,
)
from services.repair_service.state_machine import RepairStateMachine


class TestStateMachine:
    def test_initial_state(self):
        task = RepairTask(task_id="t1", alert_id="a1", host="h1", platform=PlatformType.LINUX)
        machine = RepairStateMachine(task)
        assert machine.current_state == RepairStatus.PENDING

    def test_valid_transition(self):
        task = RepairTask(task_id="t1", alert_id="a1", host="h1", platform=PlatformType.LINUX)
        machine = RepairStateMachine(task)
        assert machine.transition(RepairStatus.APPROVED)
        assert machine.transition(RepairStatus.EXECUTING)
        assert machine.transition(RepairStatus.SUCCEEDED)

    def test_invalid_transition(self):
        task = RepairTask(task_id="t1", alert_id="a1", host="h1", platform=PlatformType.LINUX)
        machine = RepairStateMachine(task)
        assert not machine.transition(RepairStatus.SUCCEEDED)

    def test_state_count(self):
        assert len(RepairStateMachine.STATES) >= 10


class TestRunbookParser:
    def test_list_examples(self):
        ids = RunbookParser.list_example_runbooks()
        assert "cpu_high" in ids
        assert "memory_high" in ids

    def test_load_example(self):
        runbook = RunbookParser.load_example("memory_high")
        assert runbook is not None
        assert runbook.runbook_id == "memory_high"
        assert runbook.risk_level == RiskLevel.LOW

    def test_validate_runbook(self):
        runbook = RunbookParser.load_example("service_restart")
        errors = RunbookParser.validate(runbook)
        assert not errors

    def test_render_command(self):
        rendered = RunbookParser.render_command("echo {name} {value}", {"name": "cpu", "value": 80})
        assert rendered == "echo cpu 80"

    def test_catalog(self):
        catalog = get_runbook_catalog()
        assert "cpu_high" in catalog


class TestStrategyManager:
    def test_default_strategies_count(self):
        from services.repair_service.strategy_manager import RepairStrategyManager

        manager = RepairStrategyManager()
        assert len(manager.list_strategies()) >= 20

    def test_match_strategy(self):
        from services.repair_service.strategy_manager import RepairStrategyManager

        manager = RepairStrategyManager()
        request = RepairRequest(
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            metric="cpu_percent",
        )
        strategy = manager.match(request)
        assert strategy is not None
        assert "cpu" in strategy.script_key

    def test_create_task_from_request(self):
        from services.repair_service.strategy_manager import RepairStrategyManager

        manager = RepairStrategyManager()
        request = RepairRequest(
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            metric="service_down",
        )
        task = manager.create_task_from_request(request, "t1")
        assert task.task_id == "t1"
        assert task.status == RepairStatus.PENDING
