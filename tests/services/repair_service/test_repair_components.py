# -*- coding: utf-8 -*-
"""Component-level tests for repair microservice."""

from __future__ import annotations

import pytest

from services.repair_service.schemas import (
    PlatformType,
    RepairExecutionResult,
    RepairStrategy,
    RepairTask,
    RiskLevel,
)


class TestRepository:
    @pytest.mark.asyncio
    async def test_repository_crud(self):
        from services.repair_service.repository import InMemoryRepairRepository

        repo = InMemoryRepairRepository()
        task = RepairTask(
            task_id="repo-t1",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
        )
        await repo.save(task)
        assert await repo.count() == 1

        fetched = await repo.get("repo-t1")
        assert fetched is not None
        assert fetched.alert_id == "a1"

        updated = await repo.update("repo-t1", {"status": "approved"})
        assert updated
        assert (await repo.get("repo-t1")).status.value == "approved"

        listed = await repo.list(status=task.status, limit=10)
        assert len(listed) <= 10

        deleted = await repo.delete("repo-t1")
        assert deleted

    @pytest.mark.asyncio
    async def test_get_repository(self):
        from services.repair_service.repository import get_repository

        repo = await get_repository(True)
        assert repo is not None


class TestRollback:
    @pytest.fixture
    def engine(self):
        from services.repair_service.rollback import RollbackEngine

        return RollbackEngine()

    @pytest.mark.asyncio
    async def test_list_strategies(self, engine):
        strategies = engine.list_strategies()
        assert len(strategies) >= 10

    @pytest.mark.asyncio
    async def test_snapshot(self, engine):
        task = RepairTask(
            task_id="rb-t1",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
        )
        snapshot = engine.take_snapshot(task)
        assert snapshot["task_id"] == "rb-t1"

    @pytest.mark.parametrize(
        "script_key",
        [
            "cpu_high",
            "service_restart",
            "disk_high",
            "dns_flush",
            "memory_high",
            "cache_drop",
            "network_restart",
            "package_install",
            "config_change",
            "generic_task",
        ],
    )
    @pytest.mark.asyncio
    async def test_rollback_strategies(self, engine, script_key):
        strategy = RepairStrategy(
            name=script_key,
            script_key=script_key,
            platform=PlatformType.LINUX,
            risk_level=RiskLevel.LOW,
        )
        task = RepairTask(
            task_id=f"rb-{script_key}",
            alert_id="a1",
            host="h1",
            platform=PlatformType.LINUX,
            strategy=strategy,
        )
        result = RepairExecutionResult(task_id=task.task_id, success=False)
        rollback_result = await engine.rollback(task, result)
        assert rollback_result.success


class TestHealthCheck:
    @pytest.fixture
    def engine(self):
        from services.repair_service.health_check import HealthCheckEngine

        return HealthCheckEngine(timeout=10)

    @pytest.mark.asyncio
    async def test_service_status_windows(self, engine):
        result = await engine.check_service_status("Spooler", platform="windows")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_exists_windows(self, engine):
        result = await engine.check_process_exists(4, platform="windows")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_metric_threshold_pass(self, engine):
        result = await engine.check_metric_threshold("cpu", 100.0, 80.0, 5.0)
        assert result["success"]

    @pytest.mark.asyncio
    async def test_metric_threshold_fail(self, engine):
        result = await engine.check_metric_threshold("cpu", 80.0, 78.0, 5.0)
        assert not result["success"]

    @pytest.mark.asyncio
    async def test_timeout_fallback(self):
        from services.repair_service.health_check import HealthCheckEngine

        engine = HealthCheckEngine(timeout=0)
        result = await engine.check_service_status("nginx", platform="linux")
        assert not result["success"]
        assert result["stderr"] == "timeout"


class TestAuditStore:
    @pytest.fixture
    def store(self):
        from services.repair_service.audit import AuditStore

        return AuditStore()

    @pytest.mark.asyncio
    async def test_query_and_analyze(self, store):
        await store.record("audit-t1", "created", "tester", {"x": 1})
        await store.record("audit-t1", "executed", "system", {"x": 2})
        await store.record("audit-t2", "created", "tester", {"x": 3})

        events = await store.query(event_type="created", limit=10)
        assert len(events) == 2

        analysis = await store.analyze("audit-t1")
        assert analysis["total_events"] == 2
        assert "created" in analysis["event_types"]

    @pytest.mark.asyncio
    async def test_snapshot(self, store):
        await store.snapshot("audit-t1", {"status": "done"})
        events = await store.get_events("audit-t1")
        assert any(e.event_type == "snapshot" for e in events)


class TestGRPCClient:
    @pytest.mark.asyncio
    async def test_http_branch_raises(self):
        from services.repair_service.grpc.client import RPCClient

        client = RPCClient(base_url="http://localhost:99999")
        with pytest.raises(Exception):
            await client.call("noop")
        await client.close()


class TestExecutorEndpoints:
    def test_health_and_metrics(self):
        from fastapi.testclient import TestClient

        from services.repair_service.executor import app

        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/metrics").status_code == 200

    def test_list_scripts_and_strategies(self):
        from fastapi.testclient import TestClient

        from services.repair_service.executor import app

        with TestClient(app) as client:
            scripts = client.get("/scripts").json()
            assert "scripts" in scripts
            strategies = client.get("/strategies").json()
            assert "strategies" in strategies

    def test_execute_runbook_endpoint(self):
        from fastapi.testclient import TestClient

        from services.repair_service.executor import app

        with TestClient(app) as client:
            runbook = {
                "runbook_id": "test",
                "name": "test",
                "platform": "linux",
                "risk_level": "low",
                "steps": [{"name": "echo", "command": "echo hello", "timeout_seconds": 5}],
            }
            response = client.post("/execute/runbook?task_id=test-1", json=runbook)
            assert response.status_code == 200
            assert response.json()["success"]

    def test_execute_strategy_endpoint(self):
        from fastapi.testclient import TestClient

        from services.repair_service.executor import app

        with TestClient(app) as client:
            payload = {
                "request": {
                    "alert_id": "a1",
                    "host": "h1",
                    "platform": "linux",
                    "metric": "cpu_percent",
                },
                "strategy": {
                    "name": "cpu_high_linux",
                    "script_key": "cpu_high",
                    "platform": "linux",
                    "risk_level": "medium",
                    "conditions": {},
                },
            }
            response = client.post("/execute/strategy", json=payload)
            assert response.status_code == 200
            assert response.json()["success"]

    @pytest.mark.asyncio
    async def test_runbook_executor_real_subprocess(self):
        from services.repair_service.executor import RunbookExecutor
        from services.repair_service.schemas import RepairRunbook, RepairStep

        runbook = RepairRunbook(
            runbook_id="test-echo",
            name="test echo",
            platform="linux",
            steps=[RepairStep(name="echo", command="echo hello", timeout_seconds=5)],
        )
        executor = RunbookExecutor(dry_run=False)
        result = await executor.execute("t1", runbook)
        assert result.success


class TestVerifierEndpoints:
    def test_health_and_metrics(self):
        from fastapi.testclient import TestClient

        from services.repair_service.verifier import app

        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/metrics").status_code == 200

    @pytest.mark.parametrize(
        "script_key,expected_strategy",
        [
            ("service_restart", "service_status"),
            ("memory_high", "metric_threshold"),
            ("disk_high", "file_exists"),
            ("flush_dns", "dns_resolution"),
            ("generic", "noop"),
        ],
    )
    def test_verify_endpoint_strategies(self, script_key, expected_strategy):
        from fastapi.testclient import TestClient

        from services.repair_service.verifier import app

        payload = {
            "task": {
                "task_id": "v-1",
                "alert_id": "a1",
                "host": "h1",
                "platform": "linux",
                "strategy": {
                    "name": script_key,
                    "script_key": script_key,
                    "platform": "linux",
                    "risk_level": "low",
                    "conditions": {},
                },
            }
        }
        with TestClient(app) as client:
            response = client.post("/verify", json=payload)
            assert response.status_code == 200
            assert response.json()["strategy"] == expected_strategy

    def test_rollback_endpoint(self):
        from fastapi.testclient import TestClient

        from services.repair_service.verifier import app

        payload = {
            "task": {
                "task_id": "rb-1",
                "alert_id": "a1",
                "host": "h1",
                "platform": "linux",
            },
            "result": {
                "task_id": "rb-1",
                "success": False,
                "output": "",
                "error": "",
                "duration_seconds": 0.0,
                "return_code": 1,
                "executed_steps": 0,
            },
        }
        with TestClient(app) as client:
            response = client.post("/rollback", json=payload)
            assert response.status_code == 200
            assert response.json()["success"]

    def test_audit_endpoints(self):
        from fastapi.testclient import TestClient

        from services.repair_service.verifier import app

        with TestClient(app) as client:
            response = client.post(
                "/audit" "?task_id=audit-1" "&event_type=created" "&actor=tester",
                json={},
            )
            assert response.status_code == 200

            response = client.get("/audit/audit-1")
            assert response.status_code == 200
            assert len(response.json()["events"]) == 1

            response = client.get("/audit/analyze/audit-1")
            assert response.status_code == 200
            assert response.json()["total_events"] == 1
