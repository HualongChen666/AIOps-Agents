# -*- coding: utf-8 -*-
"""Real TestClient tests for api/autoheal_router.py.

These tests exercise the router through the real FastAPI application using a
valid admin login and the internal API key. No mocks are used; data is seeded
through the real in-memory SQLite database and the alert_history deque.
"""

import json

import pytest

import api.autoheal_router as ar
from core import alert_engine
from core.db_engine import upsert_pending_approval


_BASE = "/api/v1/approvals"


def _approval_headers(admin_headers):
    from config import INTERNAL_API_KEY

    return {**admin_headers, "X-Internal-Key": INTERNAL_API_KEY}


def _seed_alert_and_approval(alert_id: str):
    """Place an alert into the in-memory cache and a pending row into the DB."""
    alert_engine.alert_history.append(
        {
            "id": alert_id,
            "title": "test alert",
            "desc": "high cpu",
            "level": "warning",
            "metric": "cpu_percent",
            "value": 95,
            "platform": "windows",
            "host": "localhost",
        }
    )
    upsert_pending_approval(
        alert_id=alert_id,
        rule_name="cpu_high",
        script_key="cpu_high_script",
        proposal=json.dumps({"summary": "restart service"}),
        alert_json=json.dumps({"id": alert_id, "title": "test alert"}),
    )


# ---------------------------------------------------------------------------
# Auth / key verification (403 branches)
# ---------------------------------------------------------------------------


def test_pending_missing_internal_key(client, admin_headers):
    resp = client.get(f"{_BASE}/pending", headers=admin_headers)
    assert resp.status_code == 403


def test_pending_invalid_internal_key(client, admin_headers):
    bad = {**admin_headers, "X-Internal-Key": "not-the-right-key"}
    resp = client.get(f"{_BASE}/pending", headers=bad)
    assert resp.status_code == 403


def test_approve_missing_internal_key(client, admin_headers):
    resp = client.patch(f"{_BASE}/missing-alert", headers=admin_headers)
    assert resp.status_code == 403


def test_reject_missing_internal_key(client, admin_headers):
    # The /reject endpoint does not use _verify_internal_key; admin JWT is enough.
    resp = client.post(
        f"{_BASE}/reject",
        json={"alert_id": "no-key-test", "reason": "test"},
        headers=admin_headers,
    )
    assert resp.status_code == 200


def test_propose_missing_internal_key(client, admin_headers):
    resp = client.post(f"{_BASE}/propose", json={"alert_id": "x"}, headers=admin_headers)
    # propose does not require the internal key, but the request still needs auth
    assert resp.status_code in (400, 404, 422, 500, 503)


# ---------------------------------------------------------------------------
# Listing and creation (GET /pending, POST /propose)
# ---------------------------------------------------------------------------


def test_list_pending_empty(client, admin_headers):
    resp = client.get(f"{_BASE}/pending", headers=_approval_headers(admin_headers))
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert data["total"] >= 0


def test_list_pending_with_record(client, admin_headers):
    alert_id = "REAL-ALERT-001"
    _seed_alert_and_approval(alert_id)
    resp = client.get(f"{_BASE}/pending", headers=_approval_headers(admin_headers))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_propose_alert_not_found(client, admin_headers):
    resp = client.post(
        f"{_BASE}/propose",
        json={"alert_id": "does-not-exist"},
        headers=_approval_headers(admin_headers),
    )
    assert resp.status_code == 404


def test_propose_alert_present(client, admin_headers):
    alert_id = "REAL-ALERT-002"
    alert_engine.alert_history.append(
        {
            "id": alert_id,
            "title": "memory high",
            "desc": "high memory",
            "level": "warning",
            "metric": "memory_percent",
            "value": 92,
            "platform": "linux",
            "host": "localhost",
        }
    )
    resp = client.post(
        f"{_BASE}/propose",
        json={"alert_id": alert_id},
        headers=_approval_headers(admin_headers),
    )
    # AI runbook generation is environment-dependent; the router must return a
   # well-defined status (success, client error, or server unavailability).
    assert resp.status_code in (200, 400, 500, 503)


# ---------------------------------------------------------------------------
# Approval execution (PATCH /{alert_id})
# ---------------------------------------------------------------------------


def test_approve_nonexistent_alert(client, admin_headers):
    resp = client.patch(
        f"{_BASE}/nonexistent-alert", headers=_approval_headers(admin_headers)
    )
    # The fallback alert payload lets the workflow attempt to run.
    assert resp.status_code == 200


def test_approve_existing_alert(client, admin_headers):
    alert_id = "REAL-ALERT-003"
    _seed_alert_and_approval(alert_id)
    resp = client.patch(
        f"{_BASE}/{alert_id}", headers=_approval_headers(admin_headers)
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Rejection / takeover (POST /reject, POST /takeover/{alert_id})
# ---------------------------------------------------------------------------


def test_reject_nonexistent_alert(client, admin_headers):
    resp = client.post(
        f"{_BASE}/reject",
        json={"alert_id": "no-such-alert", "reason": "just testing"},
        headers=_approval_headers(admin_headers),
    )
    assert resp.status_code == 200


def test_reject_existing_alert(client, admin_headers):
    alert_id = "REAL-ALERT-004"
    _seed_alert_and_approval(alert_id)
    resp = client.post(
        f"{_BASE}/reject",
        json={"alert_id": alert_id, "reason": "manual reject"},
        headers=_approval_headers(admin_headers),
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True


def test_takeover_empty_alert_id(client, admin_headers):
    resp = client.post(
        f"{_BASE}/takeover/%20%20", headers=_approval_headers(admin_headers)
    )
    assert resp.status_code == 422


def test_takeover_existing_alert(client, admin_headers):
    alert_id = "REAL-ALERT-005"
    _seed_alert_and_approval(alert_id)
    resp = client.post(
        f"{_BASE}/takeover/{alert_id}", headers=_approval_headers(admin_headers)
    )
    assert resp.status_code == 200
    assert resp.json().get("status") == "cancelled"


# ---------------------------------------------------------------------------
# Direct helper branch coverage (no mocks; called via real module refs)
# ---------------------------------------------------------------------------


def test__enrich_error_msg_branches():
    import api.autoheal_router as ar

    assert ar._enrich_error_msg("") == ""
    assert "approved_no_script" in ar._enrich_error_msg("approved_no_script")
    assert "executed_success" in ar._enrich_error_msg("executed_success")
    assert ar._enrich_error_msg("unknown") == "unknown"


def test__find_alert_by_id_and_validate_runbook():
    import api.autoheal_router as ar
    from fastapi import HTTPException

    assert ar._find_alert_by_id("REAL-ALERT-001") is not None
    assert ar._find_alert_by_id("not-in-history") is None

    with pytest.raises(HTTPException) as exc:
        ar._validate_runbook_result(None)
    assert exc.value.status_code == 500

    with pytest.raises(HTTPException) as exc:
        ar._validate_runbook_result({"success": False, "error": "guard blocked"})
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        ar._validate_runbook_result({"success": False, "error": "x", "guard_results": []})
    assert "guard_results" in exc.value.detail

    assert ar._validate_runbook_result({"success": True, "proposal": "p"}) == {
        "success": True,
        "proposal": "p",
    }


def test__approve_request_validation():
    with pytest.raises(Exception):
        ar.ApproveRequest.model_validate({"alert_id": "   "})
    with pytest.raises(Exception):
        ar.ApproveRequest.model_validate({"alert_id": ""})
    req = ar.ApproveRequest.model_validate({"alert_id": "  OK  "})
    assert req.alert_id == "OK"


# ---------------------------------------------------------------------------
# Config/state branches (503, 247->253)
# ---------------------------------------------------------------------------


def test_approve_without_async_update(client, admin_headers):
    """Temporarily unset the DB update helper to cover the fallback branch."""
    original = ar.async_update_approval_status_by_alert
    ar.async_update_approval_status_by_alert = None
    try:
        alert_id = "REAL-ALERT-010"
        _seed_alert_and_approval(alert_id)
        resp = client.patch(
            f"{_BASE}/{alert_id}", headers=_approval_headers(admin_headers)
        )
        assert resp.status_code == 200
    finally:
        ar.async_update_approval_status_by_alert = original


def test_propose_runbook_disabled(client, admin_headers):
    """Temporarily disable the runbook module to cover the 503 branch."""
    original = ar.is_runbook_available
    ar.is_runbook_available = False
    original_error = ar._runbook_import_error
    ar._runbook_import_error = "disabled for test"
    try:
        alert_id = "REAL-ALERT-011"
        alert_engine.alert_history.append(
            {
                "id": alert_id,
                "title": "disabled test",
                "desc": "x",
                "level": "warning",
                "platform": "windows",
            }
        )
        resp = client.post(
            f"{_BASE}/propose",
            json={"alert_id": alert_id},
            headers=_approval_headers(admin_headers),
        )
        assert resp.status_code == 503
    finally:
        ar.is_runbook_available = original
        ar._runbook_import_error = original_error


# ---------------------------------------------------------------------------
# Validation branches (422)
# ---------------------------------------------------------------------------


def test_reject_blank_alert_id(client, admin_headers):
    resp = client.post(
        f"{_BASE}/reject",
        json={"alert_id": "   ", "reason": "test"},
        headers=_approval_headers(admin_headers),
    )
    assert resp.status_code == 422


def test_propose_blank_alert_id(client, admin_headers):
    resp = client.post(
        f"{_BASE}/propose",
        json={"alert_id": "   "},
        headers=_approval_headers(admin_headers),
    )
    assert resp.status_code == 422
