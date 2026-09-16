# -*- coding: utf-8 -*-
"""Medium-ledger batch 16 (2026-09-16) — alerts/dashboard real-data fixes.

Regression coverage for the defects repaired in batch 16:

* FE-188 ``/api/v1/alerts/statistics`` now computes the **real** average
  acknowledgement / resolution time from ``alert_acknowledgements`` instead of
  hard-coding ``None`` (which made the UI read a bogus ``0m``).
* FE-190 ``/api/v1/alerts/trends`` now aggregates **real** weekly / monthly
  buckets and produces a real least-squares ``prediction`` series instead of
  always returning ``prediction: []``.
* FE-215 ``/api/v1/metrics/history`` now exposes the real ``disk`` series so
  the dashboard resource trend chart can plot cpu / memory / disk.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import alerts_advanced_router as aar
from api.metrics_router import get_history
from core.database import get_db
from core.metrics_history import metrics_history
from core.models import Alert, AlertAcknowledgement


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Alert.__table__.create(engine)
    AlertAcknowledgement.__table__.create(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    app = FastAPI()

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    app.include_router(aar.router)
    return TestClient(app)


def _add_alert(db, alert_id: str, level: str, detected_at: datetime, status: str = "pending"):
    db.add(
        Alert(
            id=alert_id,
            level=level,
            category="system",
            alert_type="threshold",
            title=f"alert {alert_id}",
            description="d",
            detected_at=detected_at,
            status=status,
            host="host-1",
            platform="linux",
        )
    )


# --------------------------------------------------------------------------
# FE-188 — real average acknowledgement / resolution time
# --------------------------------------------------------------------------


def test_statistics_returns_real_average_times(db_session, client):
    now = datetime.utcnow()
    _add_alert(db_session, "a1", "critical", now - timedelta(hours=2), status="resolved")
    _add_alert(db_session, "a2", "high", now - timedelta(hours=1))
    # a1 resolved 600s after detection; a2 acknowledged 300s after detection.
    db_session.add(
        AlertAcknowledgement(
            alert_id="a1",
            acknowledged_by="ops",
            acknowledged_at=now - timedelta(hours=2) + timedelta(seconds=600),
            status="resolved",
        )
    )
    db_session.add(
        AlertAcknowledgement(
            alert_id="a2",
            acknowledged_by="ops",
            acknowledged_at=now - timedelta(hours=1) + timedelta(seconds=300),
            status="acknowledged",
        )
    )
    db_session.commit()

    resp = client.get("/api/v1/alerts/statistics?time_range=24h")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_alerts"] == 2
    assert body["avg_resolution_time"] == 600.0
    # acknowledgement covers both records → (600 + 300) / 2
    assert body["avg_acknowledgement_time"] == 450.0


def test_statistics_average_is_none_without_acknowledgements(db_session, client):
    db_session.add(
        Alert(
            id="solo",
            level="low",
            category="system",
            alert_type="threshold",
            title="solo",
            description="d",
            detected_at=datetime.utcnow(),
            status="pending",
            host="host-1",
            platform="linux",
        )
    )
    db_session.commit()

    body = client.get("/api/v1/alerts/statistics?time_range=24h").json()
    assert body["avg_resolution_time"] is None
    assert body["avg_acknowledgement_time"] is None


# --------------------------------------------------------------------------
# FE-190 — real weekly / monthly aggregation + prediction
# --------------------------------------------------------------------------


def test_trends_aggregates_weeks_months_and_predicts(db_session, client):
    base = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    for offset in range(6):
        day = base - timedelta(days=offset)
        _add_alert(db_session, f"t{offset}a", "critical", day)
        _add_alert(db_session, f"t{offset}b", "high", day)
    db_session.commit()

    body = client.get("/api/v1/alerts/trends?time_range=7d").json()

    # 7 daily buckets, all real.
    assert len(body["daily_trends"]) == 7
    assert all("date" in row for row in body["daily_trends"])

    # weekly / monthly are sums over real days (not [::7]/[::30] slices).
    assert body["weekly_trends"], "weekly aggregation must not be empty"
    assert sum(row["total"] for row in body["weekly_trends"]) == sum(
        row["total"] for row in body["daily_trends"]
    )
    assert body["monthly_trends"], "monthly aggregation must not be empty"

    # prediction is a real 7-day forecast derived from the real series.
    assert len(body["prediction"]) == 7
    for row in body["prediction"]:
        assert "date" in row and "total" in row
        assert row["total"] >= 0
    # the series is flat (2/day), so the forecast must also be non-zero.
    assert body["prediction"][0]["total"] >= 1


def test_trends_prediction_is_empty_without_history(db_session, client):
    body = client.get("/api/v1/alerts/trends?time_range=7d").json()
    assert body["prediction"] == []
    assert sum(row["total"] for row in body["weekly_trends"]) == 0
    assert sum(row["total"] for row in body["monthly_trends"]) == 0


# --------------------------------------------------------------------------
# FE-215 — metrics history exposes the real disk series
# --------------------------------------------------------------------------


def test_metrics_history_includes_real_disk_series():
    metrics_history.push_disk(42.5)
    result = asyncio.run(get_history())
    assert "disk" in result
    assert result["disk"][-1] == 42.5
    # cpu / memory / timestamps are still present (contract preserved).
    assert "timestamps" in result
    assert "_meta" in result
