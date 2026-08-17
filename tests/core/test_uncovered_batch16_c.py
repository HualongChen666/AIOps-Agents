# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 16-c modules."""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.ai.langgraph.executor as executor_mod
import core.cicd_integration_manager as cicd_mod
import core.security_audit_system as audit_mod
import core.vulnerability_manager as vuln_mod
from core.ai.langgraph.executor import WorkflowExecutor, WorkflowOrchestrator
from core.ai.langgraph.workflow import Workflow, WorkflowContext, WorkflowNode
from core.cicd_integration_manager import (
    CICDIntegrationManager,
    IntegrationConfig,
    IntegrationExecution,
    IntegrationStage,
    IntegrationStatus,
    get_cicd_integration_manager,
)
from core.enterprise_functionality import (
    ComplianceStandard,
    DataClassification,
    EncryptionLevel,
    EnterpriseFunctionalityManager,
)
from core.security_audit_system import (
    AuditEventType,
    AuditPolicy,
    AuditSeverity,
    SecurityAuditSystem,
    get_security_audit_system,
)
from core.vulnerability_manager import (
    Priority,
    RemediationPlan,
    VulnerabilityIssue,
    VulnerabilityManager,
    VulnerabilityStatus,
    get_vulnerability_manager,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.ai.langgraph.executor
# ---------------------------------------------------------------------------
class FakeNode(WorkflowNode):
    """Simple concrete workflow node for testing."""

    async def execute(self, context: WorkflowContext) -> str:
        context.set("executed", True)
        return "node_result"


async def test_workflow_executor_success():
    executor = WorkflowExecutor()
    workflow = MagicMock()
    workflow.name = "success_wf"
    workflow.execute = AsyncMock(return_value={"status": "ok"})

    result = await executor.execute(workflow, {"in": 1})
    assert result == {"status": "ok"}
    workflow.execute.assert_awaited_once_with({"in": 1})


async def test_workflow_executor_timeout():
    async def _never(input_data=None):
        await asyncio.Event().wait()

    executor = WorkflowExecutor(max_retries=0, retry_delay=0, timeout=0.01)
    workflow = MagicMock()
    workflow.name = "timeout_wf"
    workflow.execute = _never

    result = await executor.execute(workflow)
    assert result["status"] == "failed"
    assert "timeout" in result["last_error"].lower()


async def test_workflow_executor_retry_then_success(monkeypatch):
    monkeypatch.setattr(executor_mod.asyncio, "sleep", AsyncMock())
    executor = WorkflowExecutor(max_retries=2, retry_delay=0)
    workflow = MagicMock()
    workflow.name = "retry_wf"
    workflow.execute = AsyncMock(side_effect=[RuntimeError("transient"), {"status": "recovered"}])

    result = await executor.execute(workflow)
    assert result == {"status": "recovered"}
    assert workflow.execute.call_count == 2


async def test_workflow_executor_all_retries_fail(monkeypatch):
    monkeypatch.setattr(executor_mod.asyncio, "sleep", AsyncMock())
    executor = WorkflowExecutor(max_retries=2, retry_delay=0)
    workflow = MagicMock()
    workflow.name = "fail_wf"
    workflow.execute = AsyncMock(side_effect=RuntimeError("permanent"))

    result = await executor.execute(workflow)
    assert result["status"] == "failed"
    assert result["last_error"] == "permanent"
    assert workflow.execute.call_count == 3


async def test_workflow_orchestrator(monkeypatch):
    monkeypatch.setattr(executor_mod.asyncio, "sleep", AsyncMock())
    orch = WorkflowOrchestrator()
    wf = Workflow(name="orch_wf", description="")
    wf.add_node(FakeNode("start"))
    wf.set_start_node("start")
    wf.add_end_node("start")

    orch.register_workflow(wf)
    assert orch.get_workflow("orch_wf") is wf
    assert orch.list_workflows() == ["orch_wf"]

    result = await orch.execute_workflow("orch_wf", {"in": 1})
    assert result["status"] == "completed"
    assert result["context"]["executed"] is True

    with pytest.raises(ValueError, match="not found"):
        await orch.execute_workflow("missing")


# ---------------------------------------------------------------------------
# core.enterprise_functionality
# ---------------------------------------------------------------------------
async def test_enterprise_init_and_summary():
    mgr = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "encryption_password": "enterprise_secret",
            "encryption_level": "high",
            "compliance_standards": ["gdpr", "soc2", "iso27001", "invalid_standard"],
            "audit_retention_days": 30,
        }
    )
    assert mgr.encryption_enabled is True
    assert mgr.cipher_suite is not None
    summary = mgr.get_enterprise_summary()
    assert summary["tenant_isolation"]["enabled"] is True
    assert "gdpr" in summary["compliance"]["enabled_standards"]
    assert "invalid_standard" not in summary["compliance"]["enabled_standards"]
    assert summary["encryption"]["enabled"] is True
    assert summary["audit_logging"]["retention_days"] == 30


def test_enterprise_tenant_isolation():
    mgr = EnterpriseFunctionalityManager()
    mgr.tenant_isolation_enabled = True
    mgr.assign_resource_to_tenant("tenant_a", "resource_1")
    assert mgr.enforce_tenant_isolation("tenant_a", "resource_1", "file") is True
    assert mgr.enforce_tenant_isolation("tenant_b", "resource_1", "file") is False
    mgr.tenant_isolation_enabled = False
    assert mgr.enforce_tenant_isolation("tenant_b", "resource_1", "file") is True


async def test_enterprise_compliance_and_report():
    mgr = EnterpriseFunctionalityManager(
        config={
            "compliance_standards": ["gdpr", "soc2", "iso27001", "hipaa"],
            "tenant_isolation": True,
        }
    )
    # GDPR should pass with default privacy policies.
    gdpr = await mgr.run_compliance_check(ComplianceStandard.GDPR)
    assert gdpr.passed is True

    # SOC2 should fail without audit logs or encryption.
    soc2 = await mgr.run_compliance_check(ComplianceStandard.SOC2)
    assert soc2.passed is False
    assert any("encryption" in f.lower() for f in soc2.findings)

    # Make SOC2 pass.
    mgr.audit_logs.append(mgr.create_audit_log("t1", "u1", "access", "file", "r1", "success"))
    mgr.encryption_enabled = True
    mgr.encryption_level = EncryptionLevel.HIGH
    soc2_ok = await mgr.run_compliance_check(ComplianceStandard.SOC2)
    assert soc2_ok.passed is True

    # ISO27001 recommends high encryption; current is now high.
    iso = await mgr.run_compliance_check(ComplianceStandard.ISO27001)
    assert iso.passed is True

    # HIPAA has no specific checks.
    hipaa = await mgr.run_compliance_check(ComplianceStandard.HIPAA)
    assert hipaa.passed is True
    assert "No specific checks" in hipaa.findings[0]

    report = await mgr.generate_compliance_report(ComplianceStandard.GDPR)
    assert report["standard"] == "gdpr"
    assert report["summary"]["passed"] is True
    assert "recommendations" in report


def test_enterprise_encryption_and_masking():
    mgr = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "encryption_level": "high",
            "encryption_password": "pass",
        }
    )
    assert mgr.cipher_suite is not None

    encrypted = mgr.encrypt_data("secret", DataClassification.RESTRICTED)
    assert encrypted != "secret"
    assert mgr.decrypt_data(encrypted) == "secret"

    # Public/internal data with low/no encryption should not be encrypted.
    low = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "encryption_level": "none",
            "encryption_password": "pass",
        }
    )
    assert low.encrypt_data("hello", DataClassification.PUBLIC) == "hello"

    # Decrypting malformed data should return the input.
    assert mgr.decrypt_data("not-valid-base64!!!") == "not-valid-base64!!!"

    # Classification and masking.
    assert mgr.classify_data("ssn") == DataClassification.RESTRICTED
    assert mgr.classify_data("my_secret_key") == DataClassification.RESTRICTED
    assert mgr.classify_data("unknown") == DataClassification.INTERNAL

    data = {
        "customer_data": {
            "email": "test@example.com",
            "product_info": "public",
            "password": "hunter2",
        },
    }
    masked = mgr.mask_sensitive_data(data)
    assert masked["customer_data"]["email"] != "test@example.com"
    assert masked["customer_data"]["product_info"] == "public"
    assert masked["customer_data"]["password"] != "hunter2"


async def test_enterprise_audit_consent_and_cleanup():
    mgr = EnterpriseFunctionalityManager(config={"audit_retention_days": 7})
    entry = mgr.create_audit_log(
        "t1",
        "u1",
        "read",
        "file",
        "r1",
        "success",
        ip_address="10.0.0.1",
        user_agent="test-agent",
        metadata={"key": "value"},
    )
    assert entry.tenant_id == "t1"
    assert len(mgr.audit_logs) == 1

    filtered = await mgr.query_audit_logs(tenant_id="t1")
    assert len(filtered) == 1
    assert (await mgr.query_audit_logs(tenant_id="missing")) == []

    removed = await mgr.cleanup_old_audit_logs()
    assert removed == 0

    mgr.manage_consent("u1", True, "marketing")
    assert mgr.check_consent("u1", "marketing") is True
    assert mgr.check_consent("u1", "unknown") is False
    assert mgr.check_consent("u2", "marketing") is False


def test_enterprise_encryption_failure(monkeypatch):
    mgr = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "encryption_level": "high",
            "encryption_password": "pass",
        }
    )
    monkeypatch.setattr(mgr.cipher_suite, "encrypt", MagicMock(side_effect=RuntimeError("fail")))
    assert mgr.encrypt_data("plain", DataClassification.RESTRICTED) == "plain"


# ---------------------------------------------------------------------------
# core.cicd_integration_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def cicd_manager(monkeypatch, tmp_path):
    monkeypatch.setattr(cicd_mod.asyncio, "sleep", AsyncMock())
    return CICDIntegrationManager(config={"auto_approve": True, "default_timeout": 60})


async def test_cicd_factory_and_init():
    mgr = get_cicd_integration_manager()
    assert isinstance(mgr, CICDIntegrationManager)


def test_cicd_register_and_config(cicd_manager):
    integration = IntegrationConfig(
        integration_id="i1",
        integration_name="Build and Test",
        stages=[IntegrationStage.SOURCE_CONTROL, IntegrationStage.BUILD],
    )
    cicd_manager.register_integration(integration)
    cfg = cicd_manager.get_integration_config("i1")
    assert cfg["integration_name"] == "Build and Test"
    assert "source_control" in cfg["stages"]
    assert cicd_manager.get_integration_config("missing") is None


async def test_cicd_trigger_and_execute(monkeypatch, cicd_manager):
    monkeypatch.setattr(cicd_mod.asyncio, "create_task", lambda coro: coro.close())
    integration = IntegrationConfig(
        integration_id="i2",
        integration_name="Full Pipeline",
        stages=[IntegrationStage.BUILD, IntegrationStage.TEST],
        approval_required=False,
    )
    cicd_manager.register_integration(integration)
    exec_id = await cicd_manager.trigger_integration("i2")
    assert exec_id in cicd_manager.executions
    assert exec_id in cicd_manager.executions

    # Run execution synchronously for assertion.
    await cicd_manager._execute_integration(exec_id)
    status = cicd_manager.get_execution_status(exec_id)
    assert status["status"] == "success"
    assert status["integration_id"] == "i2"
    assert len(status["results"]) == 2

    with pytest.raises(ValueError, match="not found"):
        await cicd_manager.trigger_integration("missing")


async def test_cicd_execute_rollback(monkeypatch, cicd_manager):
    monkeypatch.setattr(cicd_mod.asyncio, "create_task", lambda coro: coro.close())
    integration = IntegrationConfig(
        integration_id="i3",
        integration_name="Failing",
        stages=[IntegrationStage.BUILD, IntegrationStage.TEST],
        rollback_on_failure=True,
    )
    cicd_manager.register_integration(integration)
    exec_id = await cicd_manager.trigger_integration("i3")

    async def _failing_stage(execution_id, stage):
        return {"success": False, "stage": stage.value, "error": "build broke"}

    monkeypatch.setattr(cicd_manager, "_execute_stage", _failing_stage)
    monkeypatch.setattr(cicd_manager, "_rollback_integration", AsyncMock())

    await cicd_manager._execute_integration(exec_id)
    status = cicd_manager.get_execution_status(exec_id)
    assert status["status"] == "failed"
    cicd_manager._rollback_integration.assert_awaited_once()


async def test_cicd_execute_exception(monkeypatch, cicd_manager):
    monkeypatch.setattr(cicd_mod.asyncio, "create_task", lambda coro: coro.close())
    integration = IntegrationConfig(
        integration_id="i4",
        integration_name="Exploding",
        stages=[IntegrationStage.BUILD],
    )
    cicd_manager.register_integration(integration)
    exec_id = await cicd_manager.trigger_integration("i4")

    async def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cicd_manager, "_execute_stage", _raise)
    await cicd_manager._execute_integration(exec_id)
    status = cicd_manager.get_execution_status(exec_id)
    assert status["status"] == "failed"
    assert "boom" in status["error_message"]


async def test_cicd_execute_cancelled(monkeypatch, cicd_manager):
    monkeypatch.setattr(cicd_mod.asyncio, "create_task", lambda coro: coro.close())
    integration = IntegrationConfig(
        integration_id="i5",
        integration_name="Cancelled",
        stages=[IntegrationStage.BUILD, IntegrationStage.TEST],
    )
    cicd_manager.register_integration(integration)
    exec_id = await cicd_manager.trigger_integration("i5")

    async def _cancel_stage(execution_id, stage):
        cicd_manager.executions[execution_id].status = IntegrationStatus.CANCELLED
        return {"success": True, "stage": stage.value}

    monkeypatch.setattr(cicd_manager, "_execute_stage", _cancel_stage)
    await cicd_manager._execute_integration(exec_id)
    status = cicd_manager.get_execution_status(exec_id)
    assert status["status"] == "success"
    assert status["current_stage"] == 0


async def test_cicd_approval_and_cancel(monkeypatch, cicd_manager):
    monkeypatch.setattr(cicd_mod.asyncio, "create_task", lambda coro: coro.close())
    mgr = CICDIntegrationManager(config={"auto_approve": False})
    integration = IntegrationConfig(
        integration_id="i6",
        integration_name="Approval Required",
        stages=[IntegrationStage.BUILD],
        approval_required=True,
    )
    mgr.register_integration(integration)
    exec_id = await mgr.trigger_integration("i6")
    assert exec_id in mgr.pending_approvals
    assert len(mgr.list_pending_approvals()) == 1

    assert await mgr.approve_execution(exec_id, "admin") is True
    assert exec_id not in mgr.pending_approvals
    assert await mgr.approve_execution("missing", "admin") is False

    running = IntegrationExecution(
        execution_id="e2",
        integration_id="i6",
        status=IntegrationStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    mgr.executions["e2"] = running
    assert await mgr.cancel_execution("e2") is True
    assert running.status == IntegrationStatus.CANCELLED
    assert await mgr.cancel_execution("missing") is False


def test_cicd_statistics(cicd_manager):
    integration = IntegrationConfig(integration_id="i7", integration_name="Stats")
    cicd_manager.register_integration(integration)
    stats = cicd_manager.get_statistics()
    assert stats["registered_integrations"] == 1
    assert stats["success_rate"] == 0.0
    assert stats["total_executions"] == 0


# ---------------------------------------------------------------------------
# core.vulnerability_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def vuln_manager(monkeypatch, tmp_path):
    monkeypatch.setattr(vuln_mod.asyncio, "sleep", AsyncMock())
    return VulnerabilityManager(config={"storage_dir": str(tmp_path / "vulns")})


def test_vuln_factory_and_init():
    mgr = get_vulnerability_manager({"storage_dir": "."})
    assert isinstance(mgr, VulnerabilityManager)


async def test_vuln_lifecycle(vuln_manager):
    v1 = VulnerabilityIssue(
        issue_id="v1",
        title="SQL Injection",
        description="Blind SQLi in login",
        severity="critical",
        priority=Priority.P0,
    )
    assert await vuln_manager.report_vulnerability(v1) == "v1"
    assert (Path(vuln_manager.storage_dir) / "v1.json").exists()

    assert await vuln_manager.assign_vulnerability("v1", "alice") is True
    assert await vuln_manager.assign_vulnerability("missing", "bob") is False

    plan_id = await vuln_manager.create_remediation_plan(
        "v1",
        ["Patch ORM", "Verify fix"],
        estimated_hours=8,
        assigned_team="security",
    )
    assert plan_id in vuln_manager.remediation_plans

    assert await vuln_manager.update_vulnerability_status(
        "v1", VulnerabilityStatus.RESOLVED, "Fixed in v1.2.3"
    )

    v2 = VulnerabilityIssue(
        issue_id="v2",
        title="Info Leak",
        description="Header exposes version",
        severity="low",
        priority=Priority.P4,
    )
    await vuln_manager.report_vulnerability(v2)

    assert len(vuln_manager.list_vulnerabilities()) == 2
    assert len(vuln_manager.list_vulnerabilities(status=VulnerabilityStatus.RESOLVED)) == 1
    assert len(vuln_manager.list_vulnerabilities(priority=Priority.P4)) == 1
    assert len(vuln_manager.list_vulnerabilities(assignee="alice")) == 1

    detail = vuln_manager.get_vulnerability("v1")
    assert detail["status"] == "resolved"
    assert detail["assigned_to"] == "alice"
    assert vuln_manager.get_vulnerability("missing") is None

    plan = vuln_manager.get_remediation_plan(plan_id)
    assert plan["steps"] == ["Patch ORM", "Verify fix"]
    assert vuln_manager.get_remediation_plan("missing") is None

    stats = vuln_manager.get_statistics()
    assert stats["total_vulnerabilities"] == 2
    assert stats["resolved_vulnerabilities"] == 1


async def test_vuln_overdue_and_notifications(vuln_manager, monkeypatch):
    overdue = VulnerabilityIssue(
        issue_id="v3",
        title="Old Bug",
        description="Still open",
        severity="high",
        priority=Priority.P1,
        due_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    await vuln_manager.report_vulnerability(overdue)
    overdue_list = await vuln_manager.get_overdue_vulnerabilities()
    assert any(item["issue_id"] == "v3" for item in overdue_list)

    sync_h = MagicMock()
    async_h = AsyncMock()
    fail_h = MagicMock(side_effect=RuntimeError("bad"))
    vuln_manager.register_notification_handler(sync_h)
    vuln_manager.register_notification_handler(async_h)
    vuln_manager.register_notification_handler(fail_h)

    v4 = VulnerabilityIssue(
        issue_id="v4",
        title="New Bug",
        description="Just reported",
        severity="low",
        priority=Priority.P4,
    )
    await vuln_manager.report_vulnerability(v4)
    sync_h.assert_called_once()
    async_h.assert_awaited_once()
    fail_h.assert_called_once()


async def test_vuln_sla_monitoring(vuln_manager, monkeypatch):
    monkeypatch.setattr(
        vuln_mod.asyncio, "sleep", AsyncMock(side_effect=[None, asyncio.CancelledError()])
    )

    monkeypatch.setattr(
        vuln_manager,
        "get_overdue_vulnerabilities",
        AsyncMock(side_effect=[[{"issue_id": "v3"}], []]),
    )
    notify = AsyncMock()
    monkeypatch.setattr(vuln_manager, "_notify_overdue_vulnerabilities", notify)

    captured = []
    monkeypatch.setattr(vuln_mod.asyncio, "create_task", lambda coro: captured.append(coro) or coro)

    await vuln_manager.start_sla_monitoring()
    assert len(captured) == 1
    await captured[0]
    notify.assert_awaited_once()


# ---------------------------------------------------------------------------
# core.security_audit_system
# ---------------------------------------------------------------------------
@pytest.fixture
def audit_system(tmp_path):
    return SecurityAuditSystem(config={"audit_log_dir": str(tmp_path / "audit"), "max_events": 5})


def test_audit_factory_and_init():
    sys = get_security_audit_system()
    assert isinstance(sys, SecurityAuditSystem)
    assert len(sys.audit_policies) >= 4


def test_audit_register_policy(audit_system):
    policy = AuditPolicy(
        policy_id="custom",
        policy_name="Custom",
        event_types=[AuditEventType.DATA_ACCESS],
    )
    audit_system.register_policy(policy)
    assert "custom" in audit_system.audit_policies


async def test_audit_log_and_query(audit_system):
    e1 = await audit_system.log_event(
        AuditEventType.USER_LOGIN,
        "login",
        user_id="u1",
        ip_address="10.0.0.1",
        severity=AuditSeverity.INFO,
    )
    assert e1.startswith("audit_")

    e2 = await audit_system.log_event(
        AuditEventType.PRIVILEGE_ESCALATION,
        "escalated",
        user_id="u1",
        severity=AuditSeverity.CRITICAL,
    )

    assert (
        audit_system.audit_log_dir / f"audit_{datetime.now(timezone.utc):%Y%m%d}.jsonl"
    ).exists()

    all_events = audit_system.query_events()
    assert len(all_events) == 2
    critical = audit_system.query_events(severity=AuditSeverity.CRITICAL)
    assert len(critical) == 1
    assert critical[0]["event_id"] == e2

    now = datetime.now(timezone.utc)
    ranged = audit_system.query_events(
        start_time=now - timedelta(minutes=1),
        end_time=now + timedelta(minutes=1),
    )
    assert len(ranged) == 2

    summary = audit_system.get_audit_summary()
    assert summary["total_events"] == 2
    assert summary["by_severity"]["critical"] == 1
    assert summary["by_type"]["user_login"] == 1


async def test_audit_alert_threshold(audit_system, monkeypatch):
    policy = audit_system.audit_policies["security_events"]
    policy.alert_threshold = 2

    async_h = AsyncMock()
    sync_h = MagicMock()
    fail_h = MagicMock(side_effect=RuntimeError("bad"))
    audit_system.register_alert_handler(async_h)
    audit_system.register_alert_handler(sync_h)
    audit_system.register_alert_handler(fail_h)

    for _ in range(2):
        await audit_system.log_event(
            AuditEventType.USER_LOGIN,
            "login",
            user_id="u1",
            severity=AuditSeverity.WARNING,
        )

    async_h.assert_awaited_once()
    sync_h.assert_called_once()
    fail_h.assert_called_once()


async def test_audit_report_and_prune(audit_system):
    for i in range(7):
        await audit_system.log_event(
            AuditEventType.API_ACCESS,
            f"access_{i}",
            user_id="u1",
            severity=AuditSeverity.INFO,
        )

    assert len(audit_system.audit_events) == 5  # pruned to max_events

    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    path = await audit_system.generate_audit_report(start, end, format="json")
    assert Path(path).exists()
    with open(path) as f:
        data = json.load(f)
    assert data["report_id"].startswith("audit_report_")


def test_audit_statistics(audit_system):
    stats = audit_system.get_statistics()
    assert stats["total_events"] == 0
    assert stats["registered_policies"] == 4
