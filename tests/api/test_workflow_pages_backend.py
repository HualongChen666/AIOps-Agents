# -*- coding: utf-8 -*-
"""Functional tests for the workflow *page* backends (batch 1).

Covers ``/api/v1/workflow-management`` / ``-execution`` / ``-status`` /
``-visualization`` — the four domains that back ``frontend/app/workflow`` pages
directly.  These exercise the real SQLAlchemy-backed implementation.
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture(scope="module")
def seeded_workflow(client):
    """Create a workflow *with steps* directly in the DB for execution tests."""
    from core.database import SessionLocal
    from core.models import Workflow

    wf_id = "wf-page-test"
    db = SessionLocal()
    try:
        existing = db.query(Workflow).filter(Workflow.id == wf_id).first()
        if existing is None:
            db.add(
                Workflow(
                    id=wf_id,
                    name="页面测试工作流",
                    description="用于执行/状态/可视化测试",
                    definition={
                        "steps": [
                            {"key": "s1", "title": "准备", "desc": ""},
                            {"key": "s2", "title": "执行", "desc": ""},
                            {"key": "s3", "title": "收尾", "desc": ""},
                        ]
                    },
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


def test_workflow_management_crud(client):
    # create
    resp = client.post(
        "/api/v1/workflow-management",
        json={"name": "demo-flow", "description": "desc", "status": "draft"},
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["name"] == "demo-flow"
    assert created["status"] == "draft"
    wf_id = created["id"]

    # list contains it
    listing = client.get("/api/v1/workflow-management")
    assert listing.status_code == 200
    assert any(w["id"] == wf_id for w in listing.json())

    # update
    updated = client.put(
        f"/api/v1/workflow-management/{wf_id}",
        json={"name": "demo-flow-2", "description": "d2", "status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "demo-flow-2"
    assert updated.json()["status"] == "active"

    # status patch
    toggled = client.patch(
        f"/api/v1/workflow-management/{wf_id}/status", json={"status": "inactive"}
    )
    assert toggled.status_code == 200
    assert toggled.json()["status"] == "inactive"

    # delete
    deleted = client.delete(f"/api/v1/workflow-management/{wf_id}")
    assert deleted.status_code == 200


def test_workflow_execution_start_and_logs(client, seeded_workflow):
    start = client.post(
        "/api/v1/workflow-execution",
        json={"workflowId": seeded_workflow, "params": {"env": "test"}},
    )
    assert start.status_code == 201, start.text
    execution = start.json()
    assert execution["workflowId"] == seeded_workflow
    assert execution["totalSteps"] == 3
    exec_id = execution["id"]

    # let the background execution finish
    for _ in range(50):
        listing = client.get("/api/v1/workflow-execution?workflowId=" + seeded_workflow)
        assert listing.status_code == 200
        match = [e for e in listing.json() if e["id"] == exec_id]
        if match and match[0]["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    logs = client.get(f"/api/v1/workflow-execution/{exec_id}/logs")
    assert logs.status_code == 200
    assert isinstance(logs.json()["logs"], list)
    assert len(logs.json()["logs"]) >= 1


def test_workflow_execution_cancel_unknown(client):
    assert client.post("/api/v1/workflow-execution/nope/cancel").status_code == 404
    assert client.post("/api/v1/workflow-execution/nope/retry").status_code == 404


def test_workflow_status_summary(client, seeded_workflow):
    resp = client.get("/api/v1/workflow-status")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"statuses", "summary"}
    assert body["summary"]["total"] >= 1
    row = next((s for s in body["statuses"] if s["workflowId"] == seeded_workflow), None)
    assert row is not None
    # totalSteps must never be zero (the page divides by it)
    assert row["totalSteps"] >= 1


def test_workflow_visualization_and_export(client, seeded_workflow):
    resp = client.get("/api/v1/workflow-visualization")
    assert resp.status_code == 200
    graphs = resp.json()
    graph = next((g for g in graphs if g["id"] == seeded_workflow), None)
    assert graph is not None
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2
    assert graph["nodes"][0]["type"] == "start"
    assert graph["nodes"][-1]["type"] == "end"

    layout = client.patch(
        f"/api/v1/workflow-visualization/{seeded_workflow}/layout",
        json={"layout": "vertical"},
    )
    assert layout.status_code == 200
    assert layout.json()["layout"] == "vertical"

    export = client.get(f"/api/v1/workflow-visualization/{seeded_workflow}/export")
    assert export.status_code == 200
    assert export.headers["content-type"] == "image/png"
    assert export.content[:8] == b"\x89PNG\r\n\x1a\n"
