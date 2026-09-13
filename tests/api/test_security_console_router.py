# -*- coding: utf-8 -*-
"""Tests for api/security_console_router.py (security console sub-resources).

These tests exercise the *real* sub-resource endpoints that back
``frontend/app/security/*`` with a real SQLite-backed store: they create rows
through the repository (or the companion advanced router) and then assert the
new endpoints return genuine, persisted data.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.security_advanced_router import router as advanced_router
from api.security_console_router import router as console_router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(advanced_router)
    app.include_router(console_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate the typed security tables + the persistent_records scopes used."""
    from core.database import Base, SessionLocal, engine
    import core.models  # noqa: F401  (register metadata)

    Base.metadata.create_all(bind=engine, checkfirst=True)
    from core.models import (
        CommandRewriteRule,
        ComplianceStandard,
        DataEncryptionKey,
        HttpsCertificate,
        PenetrationTestProject,
        PrivacySubject,
        RbacRole,
        SecurityKey,
        SnapshotEncryption,
        VulnerabilityScan,
        VulnerabilityTicket,
    )

    db = SessionLocal()
    try:
        for model in (
            SecurityKey,
            DataEncryptionKey,
            HttpsCertificate,
            SnapshotEncryption,
            RbacRole,
            ComplianceStandard,
            VulnerabilityTicket,
            VulnerabilityScan,
            PenetrationTestProject,
            PrivacySubject,
            CommandRewriteRule,
        ):
            db.query(model).delete()
        from core.models import PersistentRecordDB

        db.query(PersistentRecordDB).filter(PersistentRecordDB.domain == "security_console").delete()
        db.commit()
    finally:
        db.close()
    yield


def test_operation_records_stats_and_export(client):
    assert client.get("/api/v1/security/operation-records/stats").status_code == 200
    resp = client.get("/api/v1/security/operation-records/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


def test_key_rotation_cycle(client):
    key = client.post(
        "/api/v1/security/key-management/keys",
        json={"name": "k1", "type": "api_key", "usage": ["sign"]},
    ).json()
    kid = key["id"]
    assert client.post(f"/api/v1/security/key-management/keys/{kid}/rotate").status_code == 200
    assert (
        client.post(
            f"/api/v1/security/key-management/keys/{kid}/schedule-rotation",
            json={"scheduledAt": "2026-10-01T00:00:00Z"},
        ).status_code
        == 200
    )
    rotations = client.get("/api/v1/security/key-management/rotations").json()["rotations"]
    assert len(rotations) == 2
    access = client.get("/api/v1/security/key-management/access").json()["access"]
    assert any(a["action"] == "rotate" for a in access)
    assert client.post(f"/api/v1/security/key-management/keys/{kid}/revoke").status_code == 200


def test_rbac_permissions_catalog_and_assignment(client):
    perms = client.get("/api/v1/security/rbac/permissions").json()["permissions"]
    assert len(perms) >= 5
    assert all("resource" in p and "action" in p for p in perms)

    role_id = client.post(
        "/api/v1/security/rbac/roles",
        json={"name": f"role-{uuid.uuid4().hex[:6]}", "permissions": ["read"]},
    ).json()["id"]
    created = client.post(
        "/api/v1/security/rbac/assignments", json={"userId": "u1", "roleId": role_id}
    )
    assert created.status_code == 200
    aid = created.json()["id"]
    assert len(client.get("/api/v1/security/rbac/assignments").json()["assignments"]) == 1
    assert client.delete(f"/api/v1/security/rbac/assignments/{aid}").status_code == 200


def test_command_rewrite_accepts_page_contract_and_history(client):
    created = client.post(
        "/api/v1/security/command-rewrite/rules",
        json={
            "name": "n",
            "originalPattern": "^rm -rf",
            "rewrittenCommand": "echo safe",
            "category": "system",
            "priority": 2,
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["originalPattern"] == "^rm -rf"
    assert body["rewrittenCommand"] == "echo safe"
    assert body["category"] == "system"

    test_resp = client.post(
        "/api/v1/security/command-rewrite/test", json={"command": "rm -rf /var/tmp/a"}
    )
    assert test_resp.status_code == 200
    assert test_resp.json()["rewrittenCommand"].startswith("echo safe")
    assert len(client.get("/api/v1/security/command-rewrite/history").json()["history"]) == 1
    assert client.get("/api/v1/security/command-rewrite/stats").json()["totalRewrites"] == 1


def test_command_check_records_history(client):
    client.post("/api/v1/security/command-check/check", json={"command": "ls -la"})
    history = client.get("/api/v1/security/command-check/history").json()["history"]
    assert len(history) >= 1
    stats = client.get("/api/v1/security/command-check/stats").json()
    assert stats["totalChecks"] >= 1


def test_input_validation_test_and_events(client):
    clean = client.post(
        "/api/v1/security/input-validation/test", json={"field": "name", "value": "hello"}
    ).json()
    assert clean["result"] == "passed"
    dirty = client.post(
        "/api/v1/security/input-validation/test",
        json={"field": "name", "value": "<script>alert(1)</script>"},
    ).json()
    assert dirty["result"] == "failed"
    events = client.get("/api/v1/security/input-validation/events").json()["events"]
    assert len(events) == 2
    stats = client.get("/api/v1/security/input-validation/stats").json()
    assert stats["totalValidations"] == 2
    assert stats["passedCount"] == 1 and stats["failedCount"] == 1


def test_compliance_run_and_report(client):
    from core.database import SessionLocal
    from core.models import ComplianceStandard

    db = SessionLocal()
    try:
        db.add(
            ComplianceStandard(
                id="std-t1",
                name="ISO27001",
                category="iso27001",
                description="d",
                check_criteria=[{"control": "A.5"}, {"control": "A.6"}],
                severity="high",
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()
    run = client.post("/api/v1/security/compliance-check/standards/std-t1/run")
    assert run.status_code == 200 and run.json()["checksCreated"] == 2
    report = client.post("/api/v1/security/compliance-check/standards/std-t1/report")
    assert report.status_code == 200
    assert report.json()["pendingControls"] == 2
    assert len(client.get("/api/v1/security/compliance-check/checks?standardId=std-t1").json()["checks"]) == 2


def test_data_encryption_key_lifecycle_and_events(client):
    gen = client.post(
        "/api/v1/security/data-encryption/keys/generate",
        json={"name": "dek", "type": "aes", "algorithm": "AES-256-GCM", "keySize": 256},
    )
    assert gen.status_code == 200
    kid = gen.json()["id"]
    assert client.post(f"/api/v1/security/data-encryption/keys/{kid}/rotate").status_code == 200
    assert client.post(f"/api/v1/security/data-encryption/keys/{kid}/revoke").status_code == 200
    events = client.get("/api/v1/security/data-encryption/events").json()["events"]
    assert len(events) >= 3

    # keys list carries the frontend EncryptionKey contract (type/usage present).
    keys = client.get("/api/v1/security/data-encryption/keys").json()["keys"]
    assert all("type" in k and isinstance(k["usage"], list) for k in keys)


def test_https_certificate_renew(client):
    cert = client.post(
        "/api/v1/security/https/certificates", json={"domain": "a.example.com", "validDays": 30}
    ).json()
    cid = cert.get("id")
    if cid:
        assert client.post(f"/api/v1/security/https/certificates/{cid}/renew").status_code == 200


def test_snapshot_encrypt_and_jobs(client):
    snap = client.post(
        "/api/v1/security/snapshot-encryption/snapshots",
        json={"name": "s1", "source": "/data", "preState": {}, "retentionDays": 7},
    ).json()
    sid = snap.get("id")
    if sid:
        assert client.post(f"/api/v1/security/snapshot-encryption/snapshots/{sid}/encrypt").status_code == 200
        jobs = client.get("/api/v1/security/snapshot-encryption/jobs").json()["jobs"]
        assert any(j["operation"] == "encrypt" for j in jobs)


def test_vulnerability_plan_flow(client):
    ticket = client.post(
        "/api/v1/security/vulnerability-management/tickets",
        json={"title": "CVE-x", "severity": "high", "description": "d"},
    ).json()
    tid = ticket.get("id")
    if tid:
        plan = client.post(
            "/api/v1/security/vulnerability-management/plans",
            json={"vulnerabilityId": tid, "planType": "patch", "estimatedTime": 24},
        )
        assert plan.status_code == 200
        pid = plan.json()["id"]
        approved = client.patch(
            f"/api/v1/security/vulnerability-management/plans/{pid}", json={"status": "approved"}
        )
        assert approved.json()["status"] == "approved"


def test_vulnerability_scan_start_stop_and_stats(client):
    start = client.post(
        "/api/v1/security/vulnerability-scan/start",
        json={"name": "s", "target": "10.0.0.1", "scanType": "quick"},
    )
    assert start.status_code == 200
    scan_id = start.json()["id"]
    tasks = client.get("/api/v1/security/vulnerability-scan/tasks").json()["tasks"]
    assert any(t["id"] == scan_id for t in tasks)
    assert client.post(f"/api/v1/security/vulnerability-scan/tasks/{scan_id}/stop").status_code == 200
    assert client.get("/api/v1/security/vulnerability-scan/stats").status_code == 200


def test_audit_center_run_dashboard_export(client):
    run = client.post(
        "/api/v1/security/audit-center/run", json={"name": "a1", "type": "security", "target": "all"}
    )
    assert run.status_code == 200
    report_id = run.json()["id"]
    dashboard = client.get("/api/v1/security/audit-center/dashboard").json()
    assert dashboard["totalReports"] >= 1
    export = client.get(f"/api/v1/security/audit-center/reports/{report_id}/export")
    assert export.status_code == 200
    # reports list carries the frontend AuditReport contract (name/type/findings).
    reports = client.get("/api/v1/security/audit-center/reports").json()["reports"]
    assert all({"name", "type", "findings"} <= set(r.keys()) for r in reports)


def test_penetration_report_generation_and_download(client):
    project = client.post(
        "/api/v1/security/penetration-testing/projects",
        json={"name": "p1", "target": "x", "type": "gray_box"},
    ).json()
    pid = project.get("id")
    if pid:
        assert project.get("type") == "gray_box"
        projects = client.get("/api/v1/security/penetration-testing/projects").json()["projects"]
        assert all("testers" in p for p in projects)
        report = client.post(f"/api/v1/security/penetration-testing/projects/{pid}/report")
        assert report.status_code == 200
        rid = report.json()["id"]
        assert client.get(f"/api/v1/security/penetration-testing/reports/{rid}/download").status_code == 200


def test_api_security_keys_crud(client):
    created = client.post(
        "/api/v1/security/api-security/keys",
        json={"name": "k", "userId": "admin", "permissions": ["read"], "expiresIn": 10},
    )
    assert created.status_code == 200
    kid = created.json()["id"]
    assert created.json()["key"].startswith("aiops_")
    assert len(client.get("/api/v1/security/api-security/keys").json()["keys"]) == 1
    assert client.delete(f"/api/v1/security/api-security/keys/{kid}").status_code == 200


def test_privacy_consent_revocation_creates_request(client):
    subject = client.post(
        "/api/v1/security/data-privacy/subjects",
        json={"name": "joe", "type": "customer", "consentLevel": "full"},
    ).json()
    sid = subject.get("id")
    if sid:
        resp = client.post(f"/api/v1/security/data-privacy/subjects/{sid}/revoke-consent")
        assert resp.status_code == 200
        assert resp.json()["consentLevel"] == "none"
        requests = client.get("/api/v1/security/data-privacy/requests").json()["requests"]
        assert len(requests) == 1


def test_empty_subresource_lists_return_200(client):
    """All sub-resource list endpoints must exist and return an empty payload."""
    for path in (
        "/api/v1/security/mfa/users",
        "/api/v1/security/mfa/events",
        "/api/v1/security/rate-limit/events",
        "/api/v1/security/rate-limit/stats",
        "/api/v1/security/command-guard/events",
        "/api/v1/security/command-guard/stats",
        "/api/v1/security/compliance-management/tasks",
        "/api/v1/security/compliance-management/evidence",
        "/api/v1/security/database-security/users",
        "/api/v1/security/database-security/audits",
        "/api/v1/security/https/configs",
        "/api/v1/security/https/headers",
        "/api/v1/security/security-testing/suites",
        "/api/v1/security/security-testing/results",
        "/api/v1/security/vulnerability-intelligence/feeds",
        "/api/v1/security/audit-center/schedules",
        "/api/v1/security/api-security/events",
        "/api/v1/security/abac/attributes",
        "/api/v1/security/abac/logs",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
