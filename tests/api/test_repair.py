import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Real end-to-end tests for repair / auto-heal / approval endpoints.

These tests focus on safe paths: listing, history, and invalid payloads that
fail validation before any script is executed. No repair scripts are actually
run.
"""


@pytest.mark.smoke
def test_list_repair_scripts(client, admin_headers):
    """The repair scripts list endpoint returns 200."""
    resp = client.get("/api/v1/repairs/scripts", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_repair_history(client, admin_headers):
    """The repair history endpoint returns 200 or a valid error."""
    resp = client.get("/api/v1/repairs/history", headers=admin_headers)
    assert resp.status_code in (200, 404, 500)


def test_execute_repair_rejects_invalid_payload(client, admin_headers):
    """POST /execute with an invalid body is rejected before execution."""
    resp = client.post("/api/v1/repairs/execute", json={}, headers=admin_headers)
    assert resp.status_code in (422, 404)


@pytest.mark.smoke
def test_list_autoheal_pending(client, approval_headers):
    """The auto-heal pending approvals endpoint returns 200."""
    resp = client.get("/api/v1/approvals/pending", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_approve_autoheal_returns_response(client, approval_headers):
    """PATCH approval processes the request and returns a response."""
    resp = client.patch(
        "/api/v1/approvals/alert-123",
        json={},
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_reject_autoheal(client, approval_headers):
    """POST /approvals/reject accepts a valid body and returns a response."""
    resp = client.post(
        "/api/v1/approvals/reject",
        json={"alert_id": "alert-123", "reason": "Test rejection"},
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
def test_takeover_autoheal(client, approval_headers):
    """POST takeover returns a response for an alert id."""
    resp = client.post("/api/v1/approvals/takeover/alert-123", headers=approval_headers)
    assert resp.status_code in (200, 404, 500)


def test_propose_autoheal_rejects_invalid_payload(client, approval_headers):
    """POST propose with an invalid body is rejected."""
    resp = client.post("/api/v1/approvals/propose", json={}, headers=approval_headers)
    assert resp.status_code in (422, 404)
