# -*- coding: utf-8 -*-
"""Real branch-coverage tests for services/alert_service/collector.py.

These tests exercise the collector's normalization, parsing, rate limiting,
and error handling with real AlertService/Collector instances and in-memory
data sources. No mocks are used; state is reset between tests via real
repository and message queue instances.
"""

from __future__ import annotations

import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.alert_service.collector import (
    _SlidingWindowRateLimiter,
    _alert_priority,
    _extract_severity,
    _from_generic,
    _from_grafana,
    _from_zabbix,
    _normalize_alert,
    _parse_prometheus_alert,
    _severity_from_label,
    app,
)
from services.alert_service.mq import message_queue
from services.alert_service.repository import InMemoryAlertRepository
from services.alert_service.schemas import (
    Alert,
    AlertSeverity,
    AlertStatus,
    PrometheusAlert,
)


@pytest.fixture
def client():
    """Resettable TestClient for the collector app."""
    message_queue.reset()
    with TestClient(app) as c:
        c.app.state.repo = InMemoryAlertRepository()
        c.app.state.mq = message_queue
        c.app.state.rate_limiter = _SlidingWindowRateLimiter(100_000)
        c.app.state.start_time = time.time()
        yield c


# ---------------------------------------------------------------------------
# Helper-function branches
# ---------------------------------------------------------------------------

def test_severity_from_label_all_branches():
    """Cover every mapped severity and the default fallback."""
    assert _severity_from_label("critical") == AlertSeverity.CRITICAL
    assert _severity_from_label("WARNING") == AlertSeverity.WARNING
    assert _severity_from_label("Info") == AlertSeverity.INFO
    assert _severity_from_label("HIGH") == AlertSeverity.HIGH
    assert _severity_from_label("fatal") == AlertSeverity.FATAL
    assert _severity_from_label("unknown") == AlertSeverity.WARNING


def test_extract_severity_branches():
    """Cover severity extraction from text and the miss branch."""
    assert _extract_severity("this is CRITICAL") == "critical"
    assert _extract_severity("a fatal error") == "fatal"
    assert _extract_severity("high load") == "high"
    assert _extract_severity("warning condition") == "warning"
    assert _extract_severity("info message") == "info"
    assert _extract_severity("") is None
    assert _extract_severity("nothing here") is None


def test_alert_priority_branches():
    """Cover resolved fast-path and severity/priority weight branches."""
    resolved = Alert(
        id="1",
        title="t",
        status=AlertStatus.RESOLVED,
        level=AlertSeverity.CRITICAL,
        priority="P0",
    )
    assert _alert_priority(resolved) == -1000

    fatal = Alert(
        id="2",
        title="t",
        status=AlertStatus.PENDING,
        level=AlertSeverity.FATAL,
        priority="P0",
    )
    assert _alert_priority(fatal) == -(5 * 10 + 30)

    high = Alert(
        id="3",
        title="t",
        status=AlertStatus.PENDING,
        level=AlertSeverity.HIGH,
        priority="P1",
    )
    assert _alert_priority(high) == -(3 * 10 + 20)

    info_p3 = Alert(
        id="4",
        title="t",
        status=AlertStatus.PENDING,
        level=AlertSeverity.INFO,
        priority="P3",
    )
    assert _alert_priority(info_p3) == -(1 * 10 + 0)

    unknown_priority = Alert(
        id="5",
        title="t",
        status=AlertStatus.PENDING,
        level=AlertSeverity.WARNING,
        priority="P9",
    )
    assert _alert_priority(unknown_priority) == -(2 * 10 + 0)


async def test_rate_limiter_acquisition_and_window_cleanup():
    """Cover accept, reject, window cleanup and the zero-count branch."""
    rl = _SlidingWindowRateLimiter(2)
    assert await rl.acquire(2)
    assert not await rl.acquire(1)

    # Negative window forces all timestamps to expire and exercise popleft.
    fast = _SlidingWindowRateLimiter(1, window_seconds=-1.0)
    assert await fast.acquire(1)
    assert await fast.acquire(1)

    zero = _SlidingWindowRateLimiter(10)
    assert await zero.acquire(0)


def test_parse_prometheus_alert_branches():
    """Cover alertname, host/instance fallbacks, value parsing and status."""
    a1 = PrometheusAlert(
        labels={
            "alertname": "CPUHigh",
            "instance": "srv-1",
            "severity": "critical",
            "priority": "P0",
            "value": "99.5",
        },
        status="resolved",
        startsAt=datetime.utcnow(),
        fingerprint="fp-1",
    )
    alert1 = _parse_prometheus_alert(a1)
    assert alert1.status == AlertStatus.RESOLVED
    assert alert1.level == AlertSeverity.CRITICAL
    assert alert1.value == 99.5
    assert alert1.fingerprint == "fp-1"

    a2 = PrometheusAlert(
        labels={
            "alertname": "NoHost",
        },
    )
    alert2 = _parse_prometheus_alert(a2)
    assert alert2.host == "unknown"

    a3 = PrometheusAlert(
        labels={
            "alertname": "HostOnly",
            "host": "srv-2",
            "value": "not-a-number",
            "__name__": "metric_name",
        },
    )
    alert3 = _parse_prometheus_alert(a3)
    assert alert3.host == "srv-2"
    assert alert3.value is None
    assert alert3.metric == "metric_name"


# ---------------------------------------------------------------------------
# Normalizer branches
# ---------------------------------------------------------------------------

def test_normalize_grafana_branches():
    """Cover grafana title fallback, resolved state, tags as string, bad value."""
    resolved = _normalize_alert(
        "grafana",
        {
            "state": "ok",
            "message": "critical: disk full",
            "evalMatches": [
                {
                    "metric": "disk",
                    "value": "bad",
                    "tags": {"host": "grafana-1"},
                }
            ],
        },
    )
    assert resolved.status == AlertStatus.RESOLVED
    assert resolved.level == AlertSeverity.CRITICAL
    assert resolved.value is None
    assert resolved.host == "grafana-1"

    minimal = _normalize_alert(
        "grafana",
        {
            "ruleName": "RuleNameAlert",
            "state": "alerting",
            "evalMatches": [{"tags": "not-a-dict"}],
        },
    )
    assert minimal.title == "RuleNameAlert"
    assert minimal.host == "unknown"
    assert minimal.status == AlertStatus.PENDING


def test_normalize_zabbix_branches():
    """Cover zabbix host/name/message fallbacks and resolved status."""
    resolved = _normalize_alert(
        "zabbix",
        {
            "hostname": "zbx-1",
            "alert_name": "MemLow",
            "message": "fatal memory",
            "status": "OK",
            "value": "also-bad",
            "item": "memory",
        },
    )
    assert resolved.status == AlertStatus.RESOLVED
    assert resolved.level == AlertSeverity.FATAL
    assert resolved.value is None
    assert resolved.host == "zbx-1"

    minimal = _normalize_alert(
        "zabbix",
        {
            "host": "zbx-2",
            "trigger_name": "Trigger",
            "description": "high cpu",
            "severity": "high",
            "item": "cpu",
        },
    )
    assert minimal.host == "zbx-2"
    assert minimal.title == "Trigger"
    assert minimal.level == AlertSeverity.HIGH


def test_normalize_generic_branches():
    """Cover list payload, missing id/fingerprint, and invalid payload."""
    from_list = _normalize_alert(
        "custom",
        [{"title": "FromList", "id": "list-1"}],
    )
    assert from_list.title == "FromList"
    assert from_list.id == "list-1"

    with_id = _normalize_alert(
        "custom",
        {
            "title": "HasFingerprint",
            "id": "generic-1",
            "fingerprint": "fp-2",
        },
    )
    assert with_id.fingerprint == "fp-2"

    no_fp = _normalize_alert(
        "custom",
        {
            "title": "NoFingerprint",
            "id": "generic-2",
        },
    )
    assert no_fp.fingerprint == "generic-2"

    empty = _normalize_alert(
        "custom",
        {
            "title": "EmptyIds",
            "id": "",
            "fingerprint": "",
        },
    )
    assert empty.id.startswith("generic-")
    assert empty.fingerprint == empty.id

    with pytest.raises(ValueError):
        _normalize_alert("custom", "not a dict")

    with pytest.raises(ValueError):
        _normalize_alert("custom", [])

    with pytest.raises(ValueError):
        _normalize_alert("custom", [123])

    with pytest.raises(ValidationError):
        _normalize_alert("generic", {"id": "missing-title"})


# ---------------------------------------------------------------------------
# Endpoint branches
# ---------------------------------------------------------------------------

def test_receive_alerts_empty_and_defaults(client):
    """Cover empty groups, default labels and the zero-count path."""
    r = client.post("/alerts", json={})
    assert r.status_code == 200
    assert r.json() == {"received": 0, "saved": 0, "ids": []}

    r2 = client.post("/alerts", json={"alerts": []})
    assert r2.status_code == 200
    assert r2.json()["received"] == 0


def test_receive_prometheus_alerts_variants(client):
    """Cover valid, resolved, numeric/invalid value and host fallbacks."""
    payload = {
        "alerts": [
            {
                "labels": {
                    "alertname": "CPUHigh",
                    "instance": "srv-1",
                    "severity": "critical",
                    "priority": "P0",
                    "value": "99.5",
                },
                "status": "firing",
            },
            {
                "labels": {
                    "alertname": "ResolvedAlert",
                    "host": "srv-2",
                    "severity": "info",
                    "value": "not-a-number",
                },
                "status": "resolved",
            },
            {
                "labels": {
                    "alertname": "NoHostAlert",
                    "value": [1, 2, 3],
                },
            },
        ]
    }
    r = client.post("/alerts", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["received"] == 3
    assert data["saved"] == 3
    assert len(data["ids"]) == 3


def test_receive_prometheus_alert_malformed(client):
    """Cover the validation-error branch in the Prometheus handler."""
    payload = {
        "alerts": [
            {
                "labels": {"alertname": "BadTitle"},
                "annotations": {"summary": [1, 2, 3]},
            }
        ]
    }
    r = client.post("/alerts", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["received"] == 1
    assert data["saved"] == 0
    assert data["ids"] == []


def test_receive_alerts_rate_limited(client):
    """Cover the 429/rate-limited branch."""
    client.app.state.rate_limiter = _SlidingWindowRateLimiter(1)
    payload = {
        "alerts": [
            {"labels": {"alertname": "A"}},
            {"labels": {"alertname": "B"}},
        ]
    }
    r = client.post("/alerts", json=payload)
    assert r.status_code == 429
    assert "rate limit" in r.text.lower()


def test_receive_generic_grafana(client):
    """Cover the grafana endpoint including resolved and tags branches."""
    r = client.post(
        "/alerts/grafana",
        json={
            "title": "Grafana Disk",
            "message": "critical: disk usage",
            "state": "ok",
            "evalMatches": [
                {
                    "metric": "disk",
                    "value": "n/a",
                    "tags": {"instance": "g-1"},
                }
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["saved"] == 1
    assert data["ids"]


def test_receive_generic_grafana_defaults(client):
    """Cover grafana title fallback and tags-as-string branch."""
    r = client.post(
        "/alerts/grafana",
        json={
            "state": "alerting",
            "evalMatches": [{"tags": "bad-tags"}],
        },
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1


def test_receive_generic_zabbix(client):
    """Cover the zabbix endpoint and its fallbacks."""
    r = client.post(
        "/alerts/zabbix",
        json={
            "hostname": "z-1",
            "alert_name": "Zabbix Mem",
            "message": "high load",
            "status": "RESOLVED",
            "value": "bad",
            "item": "memory",
        },
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1


def test_receive_generic_valid_and_invalid(client):
    """Cover valid custom, unknown source, and 422 validation error."""
    r = client.post(
        "/alerts/custom",
        json={
            "id": "c-1",
            "title": "Custom Alert",
            "level": "critical",
            "status": "pending",
        },
    )
    assert r.status_code == 200
    assert r.json()["ids"] == ["c-1"]

    r2 = client.post(
        "/alerts/unknownsource",
        json={
            "id": "u-1",
            "title": "Unknown Source",
        },
    )
    assert r2.status_code == 200

    r3 = client.post(
        "/alerts/generic",
        json={"id": "invalid"},
    )
    assert r3.status_code == 422


def test_receive_generic_rate_limited(client):
    """Cover the 429 branch for the generic /{source} endpoint."""
    client.app.state.rate_limiter = _SlidingWindowRateLimiter(0)
    r = client.post("/alerts/custom", json={"id": "c-1", "title": "Custom"})
    assert r.status_code == 429


def test_health_metrics_and_list(client):
    """Cover health, metrics and the list endpoint."""
    # Seed one alert first.
    client.post(
        "/alerts",
        json={
            "alerts": [
                {"labels": {"alertname": "Listable", "severity": "warning"}}
            ]
        },
    )

    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["service"] == "alert-collector"

    m = client.get("/metrics")
    assert m.status_code == 200

    l = client.get("/alerts?limit=1")
    assert l.status_code == 200
    assert l.json()["total"] >= 1
