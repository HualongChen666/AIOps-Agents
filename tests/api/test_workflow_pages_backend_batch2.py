# -*- coding: utf-8 -*-
"""Functional tests for the workflow page backends (batch 2).

Covers change-approval / change-records (projections of the real
change-management engine) and task-scheduler / executor / performance-scheduler.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_change_engine(tmp_path, monkeypatch):
    """Redirect the change engine's JSON store to a temp dir (no repo pollution)."""
    import core.change_management_engine as cme

    monkeypatch.setattr(cme, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(cme, "_DATA_FILE", tmp_path / "change_requests.json")
    cme._REQUESTS.clear()
    monkeypatch.setattr(cme, "_LOADED", False)
    yield
    cme._REQUESTS.clear()
    monkeypatch.setattr(cme, "_LOADED", False)


@pytest.fixture(scope="module")
def workflow_id(client):
    """A workflow with steps used by scheduler/executor tests."""
    from core.database import SessionLocal
    from core.models import Workflow

    wf_id = "wf-batch2"
    db = SessionLocal()
    try:
        if db.query(Workflow).filter(Workflow.id == wf_id).first() is None:
            db.add(
                Workflow(
                    id=wf_id,
                    name="批量2工作流",
                    description="",
                    definition={"steps": [{"key": "a", "title": "A"}, {"key": "b", "title": "B"}]},
                    status="active",
                    version=1,
                )
            )
            db.commit()
    finally:
        db.close()
    yield wf_id
    db = SessionLocal()
    try:
        db.query(Workflow).filter(Workflow.id == wf_id).delete()
        db.commit()
    finally:
        db.close()


async def _make_change(title: str, *, submit: bool = True, implement: bool = False) -> str:
    from core.change_management_engine import (
        approve_request,
        create_request,
        implement_request,
        submit_request,
    )

    request = await create_request(
        {
            "title": title,
            "description": "d",
            "requester": "alice",
            "approver": "bob",
            "risk_level": "high",
            "schedule": "2026-01-01 00:00",
            "affected_services": ["svc-a"],
        },
        tenant_id="default",
    )
    if submit:
        await submit_request(request.id, tenant_id="default")
    if implement:
        await approve_request(request.id, tenant_id="default")
        await implement_request(request.id, tenant_id="default")
    return request.id


@pytest.mark.asyncio
async def test_change_approval_flow(client):
    request_id = await _make_change("审批流程测试")

    listing = client.get("/api/v1/change-approval")
    assert listing.status_code == 200
    row = next(r for r in listing.json() if r["id"] == request_id)
    assert row["status"] == "pending"
    assert row["type"] == "emergency"  # high risk
    assert row["changeTitle"] == "审批流程测试"

    approved = client.post(f"/api/v1/change-approval/{request_id}/approve", json={"comment": "同意"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["comment"] == "同意"

    # approving again is invalid
    again = client.post(f"/api/v1/change-approval/{request_id}/approve", json={"comment": ""})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_change_records_and_export(client):
    request_id = await _make_change("已完成变更", implement=True)

    resp = client.get("/api/v1/change-records")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"records", "stats"}
    record = next(r for r in body["records"] if r["id"] == request_id)
    assert record["status"] == "completed"
    assert record["rollbackExecuted"] is False
    assert "completedChanges" in body["stats"]

    export = client.get("/api/v1/change-records/export")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "已完成变更" in export.content.decode("utf-8-sig")


def test_task_scheduler_lifecycle(client, workflow_id):
    # invalid cron
    bad = client.post(
        "/api/v1/task-scheduler",
        json={"name": "bad", "workflowId": workflow_id, "schedule": "not-a-cron"},
    )
    assert bad.status_code == 400

    created = client.post(
        "/api/v1/task-scheduler",
        json={
            "name": "每5分钟",
            "description": "d",
            "workflowId": workflow_id,
            "schedule": "*/5 * * * *",
            "timezone": "Asia/Shanghai",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["nextRun"] is not None
    task_id = task["id"]

    listing = client.get("/api/v1/task-scheduler")
    assert listing.status_code == 200
    assert listing.json()["stats"]["totalTasks"] >= 1

    toggled = client.patch(f"/api/v1/task-scheduler/{task_id}/toggle", json={"enabled": False})
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False

    ran = client.post(f"/api/v1/task-scheduler/{task_id}/run-now")
    assert ran.status_code == 200, ran.text
    assert ran.json()["runCount"] == 1
    assert ran.json()["successCount"] == 1

    assert client.delete(f"/api/v1/task-scheduler/{task_id}").status_code == 200


def test_executor_pause_resume_and_retry(client, workflow_id):
    listing = client.get("/api/v1/executor")
    assert listing.status_code == 200
    assert set(listing.json().keys()) == {"tasks", "stats"}

    assert client.post("/api/v1/executor/pause").status_code == 200
    started = client.post("/api/v1/workflow-execution", json={"workflowId": workflow_id, "params": {}})
    assert started.status_code == 201
    assert started.json()["status"] == "pending"

    resumed = client.post("/api/v1/executor/resume")
    assert resumed.status_code == 200
    assert resumed.json()["launched"] >= 1

    assert client.post("/api/v1/executor/nope/retry").status_code == 404
    assert client.post("/api/v1/executor/nope/cancel").status_code == 404


def test_performance_scheduler(client):
    metrics = client.get("/api/v1/performance-scheduler/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    for key in (
        "cpuUsage",
        "memoryUsage",
        "diskUsage",
        "networkIn",
        "networkOut",
        "activeWorkflows",
        "queueSize",
    ):
        assert key in body

    created = client.post(
        "/api/v1/performance-scheduler/rules",
        json={
            "name": "CPU过高",
            "description": "d",
            "metric": "cpuUsage",
            "operator": "gt",
            "threshold": -1.0,  # always matches → exercises real evaluation
            "action": "alert",
            "cooldown": 0,
        },
    )
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]

    rules = client.get("/api/v1/performance-scheduler/rules")
    assert rules.status_code == 200
    assert any(r["id"] == rule_id for r in rules.json())

    # a metrics poll should trigger the always-matching rule
    client.get("/api/v1/performance-scheduler/metrics")
    rules_after = client.get("/api/v1/performance-scheduler/rules").json()
    triggered = next(r for r in rules_after if r["id"] == rule_id)
    assert triggered["triggeredCount"] >= 1

    assert (
        client.patch(f"/api/v1/performance-scheduler/rules/{rule_id}/toggle", json={"enabled": False}).status_code
        == 200
    )
    assert client.delete(f"/api/v1/performance-scheduler/rules/{rule_id}").status_code == 200


def test_performance_scheduler_invalid(client):
    bad = client.post(
        "/api/v1/performance-scheduler/rules",
        json={
            "name": "bad",
            "metric": "nope",
            "operator": "gt",
            "threshold": 1,
            "action": "alert",
        },
    )
    assert bad.status_code == 400
