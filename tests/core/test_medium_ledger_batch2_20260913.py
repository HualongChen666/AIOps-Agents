# -*- coding: utf-8 -*-
"""Regression tests for the second 中-severity ledger repair batch.

Covers:
- core/cost_monitor.get_llm_costs (real Prometheus token/cost data)
- core/data_integration_manager field-aware masking
- core/enhanced_ai_capabilities learning-loop retraining
- core/ai_engine data-derived anomaly probabilities
- core/enhanced_root_cause_analyzer pattern similarity
- core/crypto fail-loud encryption
- core/dual_write async VictoriaMetrics accounting
- core/db_engine loop-safe synchronous wrappers
- core/external_api_audit selective URL sanitisation
- core/cpu_usage_optimizer real system actions
"""

import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

import core.db_engine as db_engine
from core.ai_engine import PredictiveAnalysisEngine
from core.cost_monitor import get_llm_costs
from core.cpu_usage_optimizer import CPUOptimizationAction, CPUUsageOptimizer
from core.crypto import encrypt_snapshot
from core.data_integration_manager import DataIntegrationManager, DataSensitivity
from core.dual_write import DualWriteStrategy
from core.enhanced_ai_capabilities import EnhancedAICapabilities, LearningMode
from core.enhanced_root_cause_analyzer import EnhancedRootCauseAnalyzer, HistoricalIncident
from core.external_api_audit import ExternalAPIAuditLogger

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# cost_monitor.get_llm_costs
# ---------------------------------------------------------------------------
def test_get_llm_costs_reads_real_registry():
    from core.prometheus_metrics import get_metrics_exporter

    exporter = get_metrics_exporter()
    exporter.record_llm_inference("gpt-4", "openai", 1.0, 1000, 500, 0.03)
    exporter.record_llm_inference("gpt-3.5", "openai", 0.5, 2000, 800, 0.004)

    result = get_llm_costs()
    assert result["source"] == "prometheus_metrics_registry"
    assert result["total_tokens"] >= 4300
    assert result["models"]["gpt-4"]["tokens"] >= 1500
    assert result["models"]["gpt-3.5"]["cost"] >= 0.004
    # no fabricated 0.6/0.4 split
    assert set(result["models"]) >= {"gpt-4", "gpt-3.5"}


# ---------------------------------------------------------------------------
# data_integration_manager masking
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_field_aware_masking(tmp_path):
    manager = DataIntegrationManager({"storage_dir": str(tmp_path)})
    masked = await manager._apply_data_masking(
        {
            "email": "alice@example.com",
            "ssn": "123456789",
            "card": "4111111111111111",
            "password": "hunter2",
            "city": "NYC",
            "nested": {"api_key": "abcdef"},
        },
        DataSensitivity.RESTRICTED,
    )
    assert masked["email"] == "a****@example.com"
    assert masked["ssn"][0] == "1" and masked["ssn"][-1] == "9"
    assert masked["card"] == "************1111"
    assert masked["password"] == "*" * len("hunter2")
    assert masked["city"] == "NYC"  # short non-sensitive value left intact
    assert masked["nested"]["api_key"] == "*" * 6

    unchanged = await manager._apply_data_masking({"name": "Alice"}, DataSensitivity.PUBLIC)
    assert unchanged["name"] == "Alice"


# ---------------------------------------------------------------------------
# enhanced_ai_capabilities learning loop
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_retrain_model_without_samples_is_noop():
    cap = EnhancedAICapabilities()
    cap.prediction_models["m1"] = None
    assert await cap._retrain_model("m1") is None


@pytest.mark.asyncio
async def test_adaptive_learn_buffers_samples():
    cap = EnhancedAICapabilities()
    cap.prediction_models["m1"] = None
    await cap.adaptive_learn("m1", [({"x": 1}, 1), ({"x": 2}, 0)], LearningMode.BATCH)
    assert len(cap.learning_samples["m1"]) == 2


@pytest.mark.asyncio
async def test_learning_loop_cancellable():
    cap = EnhancedAICapabilities()
    from datetime import timedelta

    cap.learning_interval = timedelta(seconds=0.01)
    cap.prediction_models = {"m1": None}
    cap.performance_metrics = {"m1": [0.9, 0.8]}
    task = asyncio.create_task(cap._learning_loop())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


# ---------------------------------------------------------------------------
# ai_engine anomaly probabilities
# ---------------------------------------------------------------------------
def test_anomaly_probability_is_data_derived():
    engine = PredictiveAnalysisEngine()
    result = asyncio.run(
        engine.predict_system_anomalies(
            {
                "cpu": {"usage_percent": 95},
                "memory": {"usage_percent": 90},
                "disk": [{"usage_percent": 95, "mount_point": "/"}],
            },
            prediction_horizon_hours=24,
        )
    )
    probs = {a["type"]: a["probability"] for a in result["predicted_anomalies"]}
    assert len(probs) == 3
    # higher exceedance -> higher probability (not hard-coded constants)
    assert probs["cpu_high"] > probs["memory_high"] >= 0.5
    assert 0.0 <= result["confidence"] <= 1.0

    # no anomaly below thresholds
    empty = asyncio.run(engine.predict_system_anomalies({"cpu": {"usage_percent": 10}}, 12))
    assert empty["predicted_anomalies"] == [] and empty["confidence"] == 0.0


# ---------------------------------------------------------------------------
# enhanced_root_cause_analyzer similarity
# ---------------------------------------------------------------------------
def test_pattern_similarity_is_semantic():
    analyzer = EnhancedRootCauseAnalyzer()
    assert analyzer._calculate_pattern_similarity("a", "a") == 1.0
    assert analyzer._calculate_pattern_similarity("a", "b") == 0.0
    partial = analyzer._calculate_pattern_similarity("cpu spike database", "cpu spike memory")
    assert 0.0 < partial < 1.0

    # volatile keys must not change the fingerprint
    h1 = analyzer._generate_similarity_hash({"a": 1, "timestamp": "t1"})
    h2 = analyzer._generate_similarity_hash({"a": 1, "timestamp": "t2"})
    assert h1 == h2


@pytest.mark.asyncio
async def test_record_incident_builds_pattern():
    analyzer = EnhancedRootCauseAnalyzer()
    incident = HistoricalIncident(
        id="i1",
        timestamp=datetime.now(),
        symptoms=["cpu spike"],
        root_causes=["db"],
        resolution="restart",
        similarity_hash="h",
    )
    await analyzer.record_incident(incident)
    assert incident.pattern


# ---------------------------------------------------------------------------
# crypto
# ---------------------------------------------------------------------------
def test_encrypt_snapshot_raises_when_enabled_but_unusable(monkeypatch):
    import core.crypto as crypto

    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "true")
    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_KEY", "not-a-valid-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    crypto._fernet = None
    with pytest.raises(RuntimeError):
        encrypt_snapshot("secret")


def test_encrypt_snapshot_plaintext_only_when_disabled(monkeypatch):
    import core.crypto as crypto

    monkeypatch.setenv("SNAPSHOT_ENCRYPTION_ENABLED", "false")
    crypto._fernet = None
    assert encrypt_snapshot("hello") == "PLAINTEXT::hello"


# ---------------------------------------------------------------------------
# dual_write async accounting
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_async_vm_write_accounted_on_failure():
    strategy = DualWriteStrategy(victoria_metrics_enabled=True, async_write=True)
    storage = AsyncMock()
    storage.store = AsyncMock(side_effect=RuntimeError("net"))
    strategy._vm_storage = storage

    await strategy.write_metric("cpu", 0.5, {"service": "web"})
    await strategy.flush()
    stats = strategy.get_stats()
    assert stats["vm_errors"] == 1
    assert stats["fallbacks"] == 1


@pytest.mark.asyncio
async def test_async_vm_write_accounted_on_success():
    strategy = DualWriteStrategy(victoria_metrics_enabled=True, async_write=True)
    storage = AsyncMock()
    storage.store = AsyncMock(return_value=True)
    strategy._vm_storage = storage

    await strategy.write_metric("cpu", 0.5, {"service": "web"})
    await strategy.flush()
    assert strategy.get_stats()["vm_writes"] == 1


# ---------------------------------------------------------------------------
# db_engine loop-safe wrappers
# ---------------------------------------------------------------------------
def test_db_engine_sync_wrapper_inside_event_loop():
    async def _run():
        # Must not raise ``asyncio.run() cannot be called from a running event loop``.
        db_engine.insert_alert({"id": "x"})
        db_engine.query_alerts(limit=1)
        db_engine.count_alerts()

    try:
        asyncio.run(_run())
    finally:
        # Leave the shared test database exactly as we found it.
        db_engine.clear_alerts()


# ---------------------------------------------------------------------------
# external_api_audit URL sanitisation
# ---------------------------------------------------------------------------
def test_sanitize_url_keeps_non_sensitive_params():
    logger_obj = ExternalAPIAuditLogger()
    sanitized = logger_obj._sanitize_url("https://api.example.com/v1?page=2&api_key=SECRET&q=ok")
    assert "page=2" in sanitized
    assert "q=ok" in sanitized
    assert "api_key=***" in sanitized
    assert "SECRET" not in sanitized


# ---------------------------------------------------------------------------
# cpu_usage_optimizer real actions
# ---------------------------------------------------------------------------
def test_optimize_cpu_applies_real_actions():
    optimizer = CPUUsageOptimizer(
        {"priority_step": 1, "component_processes": {"svc": [os.getpid()]}}
    )
    optimizer.set_cpu_limit("svc", 100.0, 80.0, 95.0, CPUOptimizationAction.DISTRIBUTE_LOAD)
    optimizer.component_cpu["svc"] = 120.0
    result = optimizer.optimize_cpu("svc")
    detail = result["optimization_details"][0]
    assert detail["applied"] is True
    assert len(list(detail["cpu_affinity"].values())[0]) == (os.cpu_count() or 1)


def test_scale_workers_without_pool_is_honest():
    optimizer = CPUUsageOptimizer({})
    optimizer.set_cpu_limit("svc", 100.0, 80.0, 95.0, CPUOptimizationAction.SCALE_WORKERS)
    optimizer.component_cpu["svc"] = 120.0
    detail = optimizer.optimize_cpu("svc")["optimization_details"][0]
    assert detail["applied"] is False
