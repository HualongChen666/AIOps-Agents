# -*- coding: utf-8 -*-
"""Regression tests for medium ledger batch 11 (2026-09-14).

Covers genuine behaviour fixes (the code under test is exercised for real; only
external boundaries such as scikit-learn / Prophet / Qdrant / RAG are replaced
with faithful doubles where the real dependency is unavailable in this env):

- core/intelligent_alert_analyzer.py (F226): the Prophet model is fitted on the
  real history before ``predict`` is called (was used untrained).
- core/model_fine_tuner.py (F305): ``export_model`` persists the trained model
  and tokenizer via ``save_pretrained`` (was a path-string placeholder).
- core/performance_scheduler.py (F317): daily collection stores real host
  resource samples and ``cleanup_old_metrics`` deletes rows past the retention
  window (both were empty shells).
- core/performance_regression_detector.py (F331): isolation-forest detector uses
  a real ``sklearn.ensemble.IsolationForest`` (was a proxy to IQR).
- core/plugin_marketplace_manager.py (F335): the quality gate evaluates a real
  AST-based ``performance_check`` (was hard-coded ``True``).
- core/qdrant_service.py (F350): ``search`` uses ``query_points`` with a legacy
  ``search`` fallback (was the deprecated ``search`` only).
- core/security_audit_system.py (F372): policy thresholds count events per
  event_type instead of slicing the tail then filtering.
- core/security_input_validator.py (F373): the middleware fails closed on an
  unexpected validator error (was fail-open).
- core/ui_experience_support.py (F435): chart data is derived from real metrics
  (was synthetic constants).
- core/runbook_generator.py (F439): the history prompt section is built from the
  real verified-repair retrieval (was an empty stub).
"""

from datetime import datetime as dt, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import select

# ---------------------------------------------------------------------------
# F226 — Prophet model must be trained before predicting
# ---------------------------------------------------------------------------


async def test_prophet_model_is_fitted_before_predict(monkeypatch):
    import core.intelligent_alert_analyzer as mod

    fitted = {"called": False}

    class FakeProphet:
        def __init__(self, *args, **kwargs):
            self.df = None
            self._last = None

        def fit(self, df):
            fitted["called"] = True
            self.df = df
            self._last = df["ds"].max()
            return self

        def make_future_dataframe(self, periods=0, freq="D"):
            idx = pd.date_range(self._last, periods=periods + 1, freq=freq)[1:]
            return pd.DataFrame({"ds": list(self.df["ds"]) + list(idx)})

        def predict(self, future):
            return pd.DataFrame({"ds": future["ds"], "yhat": [1.0] * len(future)})

    monkeypatch.setattr(mod, "Prophet", FakeProphet)
    monkeypatch.setattr(mod, "PROPHET_AVAILABLE", True)

    analyzer = mod.IntelligentAlertAnalyzer()
    history = [(dt.now() - timedelta(hours=i), float(i)) for i in range(12)]

    result = await analyzer.predict_alert_trends("cpu_usage", history)

    assert fitted["called"] is True, "Prophet.fit() must run before predict()"
    assert result is not None
    assert len(result.predicted_values) == 24
    assert result.metric_name == "cpu_usage"


# ---------------------------------------------------------------------------
# F305 — export_model persists a real artifact
# ---------------------------------------------------------------------------


class _FakeModel:
    def __init__(self):
        self.saved_to = None

    def save_pretrained(self, path):
        self.saved_to = path
        Path(path).mkdir(parents=True, exist_ok=True)
        return path


class _FakeTokenizer:
    def __init__(self):
        self.saved_to = None

    def save_pretrained(self, path):
        self.saved_to = path
        return path


async def test_export_model_persists_real_artifact(tmp_path):
    from core.model_fine_tuner import ModelFineTuner, TrainingProgress, TrainingStatus

    tuner = ModelFineTuner(
        config={"models_dir": str(tmp_path / "models"), "checkpoints_dir": str(tmp_path / "ckpt")}
    )
    job_id = "job-export"
    tuner.training_jobs[job_id] = TrainingProgress(job_id=job_id, status=TrainingStatus.COMPLETED)

    model = _FakeModel()
    tokenizer = _FakeTokenizer()
    tuner._training_state[job_id] = {"model": model, "tokenizer": tokenizer}

    out = await tuner.export_model(job_id, export_format="pytorch")

    assert out is not None
    assert Path(out).is_dir()
    assert (Path(out) / "export_meta.json").exists()
    assert model.saved_to == out
    assert tokenizer.saved_to == out


async def test_export_model_returns_none_without_trained_model(tmp_path):
    from core.model_fine_tuner import ModelFineTuner, TrainingProgress, TrainingStatus

    tuner = ModelFineTuner(
        config={"models_dir": str(tmp_path / "models"), "checkpoints_dir": str(tmp_path / "ckpt")}
    )
    job_id = "job-no-model"
    tuner.training_jobs[job_id] = TrainingProgress(job_id=job_id, status=TrainingStatus.COMPLETED)

    assert await tuner.export_model(job_id) is None


# ---------------------------------------------------------------------------
# F317 — scheduler collects real samples and enforces retention
# ---------------------------------------------------------------------------


async def test_scheduler_collects_and_cleans_up(tmp_path, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from core.models import PerformanceMetric

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(PerformanceMetric.__table__.create)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(
        "core.performance_data_collector.AsyncSessionLocal", session_factory
    )
    monkeypatch.setattr("core.db_engine.AsyncSessionLocal", session_factory)

    try:
        from core.performance_scheduler import PerformanceTaskScheduler

        scheduler = PerformanceTaskScheduler()

        # collect_daily_metrics stores a real sample with measured cpu/memory/disk
        await scheduler.collect_daily_metrics()
        async with session_factory() as session:
            rows = (await session.execute(select(PerformanceMetric))).scalars().all()
        assert rows, "collect_daily_metrics must persist a real sample"
        assert rows[0].cpu_usage is not None
        assert rows[0].memory_usage is not None

        # cleanup_old_metrics deletes only rows past the retention window
        old_ts = dt.now() - timedelta(days=90)
        async with session_factory() as session:
            session.add(
                PerformanceMetric(
                    test_id="old",
                    test_name="old",
                    test_type="system",
                    component="host",
                    operation="resource_sample",
                    mean_time_ms=0.0,
                    min_time_ms=0.0,
                    max_time_ms=0.0,
                    total_requests=1,
                    environment="dev",
                    timestamp=old_ts,
                )
            )
            await session.commit()

        deleted = await scheduler.cleanup_old_metrics(retention_days=30)
        assert deleted == 1

        async with session_factory() as session:
            remaining = (await session.execute(select(PerformanceMetric))).scalars().all()
        assert all(r.test_id != "old" for r in remaining)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# F331 — isolation forest is real
# ---------------------------------------------------------------------------


def test_isolation_forest_detects_planted_outlier():
    from core.performance_regression_detector import AnomalyDetector

    values = [10.0, 10.1, 9.9, 10.2, 10.0, 9.8, 10.3, 10.1, 9.95, 10.05, 1000.0]
    indices = AnomalyDetector.detect_anomalies_isolation_forest(values, contamination=0.1)

    assert 10 in indices, "the planted outlier must be flagged"
    assert len(indices) < len(values)


def test_isolation_forest_handles_short_series():
    from core.performance_regression_detector import AnomalyDetector

    assert AnomalyDetector.detect_anomalies_isolation_forest([1.0, 2.0]) == []


# ---------------------------------------------------------------------------
# F335 — plugin quality gate evaluates a real performance check
# ---------------------------------------------------------------------------


def test_plugin_quality_flags_nested_loops():
    from core.plugin_marketplace_manager import PluginMarketplaceManager

    manager = PluginMarketplaceManager()
    code = (
        '"""doc"""\n\n'
        "def run(items):\n"
        "    for i in items:\n"
        "        for j in items:\n"
        "            print(i, j)\n"
    )
    result = manager._perform_quality_check(code, {})

    assert result["performance_check"] is False
    assert any("Nested loops" in issue for issue in result["issues"])
    assert result["overall_score"] < 1.0


def test_plugin_quality_passes_clean_code():
    from core.plugin_marketplace_manager import PluginMarketplaceManager

    manager = PluginMarketplaceManager()
    code = '"""doc"""\n\n\ndef add(a, b):\n    return a + b\n'
    result = manager._perform_quality_check(code, {})

    assert result["performance_check"] is True
    assert result["overall_score"] == 1.0


# ---------------------------------------------------------------------------
# F350 — qdrant search uses query_points with a legacy fallback
# ---------------------------------------------------------------------------


class _Point:
    def __init__(self, point_id, score, payload):
        self.id = point_id
        self.score = score
        self.payload = payload


class _QueryResponse:
    def __init__(self, points):
        self.points = points


def test_qdrant_search_prefers_query_points(monkeypatch):
    from core import qdrant_service as qs

    class ModernClient:
        def __init__(self):
            self.kwargs = None

        def query_points(self, **kwargs):
            self.kwargs = kwargs
            return _QueryResponse([_Point(1, 0.9, {"a": 1})])

        def search(self, **kwargs):  # pragma: no cover - must not be used
            raise AssertionError("deprecated search() must not be used")

    client = ModernClient()
    monkeypatch.setattr(qs, "_qdrant_client", client)
    monkeypatch.setattr(qs, "QDRANT_AVAILABLE", True)

    out = qs.search("coll", [0.1, 0.2], top_k=3)

    assert out == [{"id": 1, "score": 0.9, "payload": {"a": 1}}]
    assert client.kwargs["collection_name"] == "coll"
    assert client.kwargs["limit"] == 3


def test_qdrant_search_falls_back_to_legacy_search(monkeypatch):
    from core import qdrant_service as qs

    class LegacyClient:
        def search(self, **kwargs):
            return [_Point(2, 0.5, {"b": 2})]

    monkeypatch.setattr(qs, "_qdrant_client", LegacyClient())
    monkeypatch.setattr(qs, "QDRANT_AVAILABLE", True)

    out = qs.search("coll", [0.1], top_k=1)

    assert out == [{"id": 2, "score": 0.5, "payload": {"b": 2}}]


# ---------------------------------------------------------------------------
# F372 — audit thresholds count per event_type
# ---------------------------------------------------------------------------


async def test_audit_policy_counts_per_event_type(tmp_path):
    from core.security_audit_system import (
        AuditEventType,
        AuditPolicy,
        AuditSeverity,
        SecurityAuditSystem,
    )

    system = SecurityAuditSystem(config={"audit_log_dir": str(tmp_path)})
    alerts = []
    system.register_alert_handler(lambda data: alerts.append(data))
    system.register_policy(
        AuditPolicy(
            policy_id="custom_api",
            policy_name="Custom API policy",
            event_types=[AuditEventType.API_ACCESS],
            alert_threshold=5,
            enabled=True,
        )
    )

    # Interleave filler events so that, at the 5th API_ACCESS event, the tail of
    # the buffer is dominated by DATA_ACCESS events. The old tail-slice logic
    # would therefore never reach the threshold; per-type counting does.
    for _ in range(4):
        await system.log_event(
            AuditEventType.DATA_ACCESS, action="read", severity=AuditSeverity.INFO
        )
    for _ in range(4):
        await system.log_event(
            AuditEventType.API_ACCESS, action="call", severity=AuditSeverity.INFO
        )
        for _ in range(4):
            await system.log_event(
                AuditEventType.DATA_ACCESS, action="read", severity=AuditSeverity.INFO
            )
    await system.log_event(
        AuditEventType.API_ACCESS, action="call", severity=AuditSeverity.INFO
    )

    api_alerts = [a for a in alerts if a["policy_id"] == "custom_api"]
    assert api_alerts, "the 5th API_ACCESS event must trigger the per-type threshold"
    assert api_alerts[-1]["related_events_count"] == 5


# ---------------------------------------------------------------------------
# F373 — middleware fails closed
# ---------------------------------------------------------------------------


def test_security_middleware_fails_closed_on_error(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.security_input_validator import (
        SecurityInputValidator,
        SecurityInputValidatorMiddleware,
    )

    app = FastAPI()

    @app.get("/api/v1/echo")
    async def echo(x: str = ""):  # pragma: no cover - handler not reached
        return {"x": x}

    validator = SecurityInputValidator()

    def _boom(*args, **kwargs):
        raise RuntimeError("validator exploded")

    monkeypatch.setattr(validator, "validate_dict", _boom)
    app.add_middleware(SecurityInputValidatorMiddleware, validator=validator)

    client = TestClient(app)
    resp = client.get("/api/v1/echo", params={"x": "1"})

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Input validation failed"


# ---------------------------------------------------------------------------
# F435 — chart data is derived from real metrics
# ---------------------------------------------------------------------------


def _report_config(mod, chart_type):
    return mod.ReportConfig(
        id="r1",
        name="report",
        type="system",
        time_range="1h",
        metrics=["cpu"],
        chart_type=chart_type,
    )


async def test_ui_charts_use_real_metrics(monkeypatch):
    import core.ui_experience_support as mod
    from core.metrics_history import METRICS_HISTORY

    METRICS_HISTORY.clear()
    monkeypatch.setattr(
        mod,
        "_collect_realtime_metrics",
        lambda: {"cpu_usage": 12.5, "memory_usage": 88.0, "disk_usage": 95.0},
    )

    service = mod.UIExperienceSupport()

    bar = await service._generate_bar_chart_data(_report_config(mod, mod.ChartType.BAR))
    assert bar["data"]["values"] == [12.5, 88.0, 95.0]

    pie = await service._generate_pie_chart_data(_report_config(mod, mod.ChartType.PIE))
    assert pie["data"]["labels"] == ["Healthy", "Warning", "Critical"]
    assert pie["data"]["values"] == [1, 1, 1]

    line = await service._generate_line_chart_data(_report_config(mod, mod.ChartType.LINE))
    assert line["data"]["metric"] == "cpu"
    assert line["data"]["values"] == [12.5]


# ---------------------------------------------------------------------------
# F439 — history prompt section from real verified-repair retrieval
# ---------------------------------------------------------------------------


def test_history_prompt_section_uses_verified_records(monkeypatch):
    import core.runbook_generator as mod

    monkeypatch.setattr(mod, "VERIFY_CONFIG", {"self_learning_enabled": True})
    monkeypatch.setattr(
        mod,
        "search_similar",
        lambda query, top_k=5: [
            {
                "score": 0.9,
                "payload": {
                    "verified": True,
                    "script_key": "restart_service",
                    "host": "h1",
                    "comment": "recovered",
                },
            },
            {
                "score": 0.8,
                "payload": {"verified": False, "script_key": "ignore_me", "host": "h2"},
            },
        ],
    )

    section = mod._build_history_prompt_section("cpu high")

    assert "历史验证经验" in section
    assert "restart_service" in section
    assert "ignore_me" not in section


def test_history_prompt_section_empty_without_verified(monkeypatch):
    import core.runbook_generator as mod

    monkeypatch.setattr(mod, "VERIFY_CONFIG", {"self_learning_enabled": True})
    monkeypatch.setattr(
        mod, "search_similar", lambda query, top_k=5: [{"score": 0.1, "payload": {"verified": False}}]
    )

    assert mod._build_history_prompt_section("cpu high") == ""
