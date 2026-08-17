# -*- coding: utf-8 -*-
"""Targeted functional tests for core/alert_rules, core/anomaly_detection,
core/backup_manager and core/circuit_breaker."""

import asyncio
import subprocess
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

import core.alert_rules as alert_rules
import core.anomaly_detection as anomaly
import core.backup_manager as bm
import core.circuit_breaker as cb

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core/alert_rules.py
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_alert_rules():
    """Reset the global alert rule store around every test."""
    alert_rules.reset_alert_rules()
    yield
    alert_rules.reset_alert_rules()


def test_load_and_get_alert_rules():
    custom = {
        "cpu_high": {
            "enabled": True,
            "threshold": 80.0,
            "severity": "warning",
            "description": "CPU high",
        },
        "memory_high": {
            "enabled": True,
            "threshold": 85.0,
            "severity": "critical",
            "description": "Memory high",
        },
    }
    alert_rules.load_alert_rules(custom)
    assert alert_rules.get_all_alert_rules() == custom
    assert alert_rules.get_alert_rule("cpu_high") == custom["cpu_high"]
    assert alert_rules.get_alert_rule("missing") is None


def test_add_remove_alert_rules():
    alert_rules.add_alert_rule(
        "disk_high",
        {"enabled": True, "threshold": 90.0, "severity": "warning"},
    )
    assert "disk_high" in alert_rules.get_all_alert_rules()
    assert alert_rules.remove_alert_rule("disk_high") is True
    assert alert_rules.remove_alert_rule("disk_high") is False


def test_evaluate_alert_rule():
    alert_rules.load_alert_rules(
        {
            "cpu_high": {
                "enabled": True,
                "threshold": 80.0,
                "severity": "warning",
                "description": "CPU high",
            }
        }
    )
    assert alert_rules.evaluate_alert_rule("missing", 90.0) is None
    assert alert_rules.evaluate_alert_rule("cpu_high", 70.0) is None

    alert_rules.disable_rule("cpu_high")
    assert alert_rules.evaluate_alert_rule("cpu_high", 90.0) is None

    alert_rules.enable_rule("cpu_high")
    alert = alert_rules.evaluate_alert_rule("cpu_high", 90.0, metadata={"host": "web-01"})
    assert alert is not None
    assert alert["rule_name"] == "cpu_high"
    assert alert["severity"] == "warning"
    assert alert["threshold"] == 80.0
    assert alert["current_value"] == 90.0
    assert alert["metadata"] == {"host": "web-01"}
    assert "timestamp" in alert


def test_evaluate_all_rules_and_enabled():
    rules = {
        "cpu_high": {
            "enabled": True,
            "threshold": 80.0,
            "severity": "warning",
        },
        "cpu_critical": {
            "enabled": True,
            "threshold": 95.0,
            "severity": "critical",
        },
        "memory_high": {
            "enabled": True,
            "threshold": 85.0,
            "severity": "warning",
        },
        "io_high": {
            "enabled": False,
            "threshold": 100.0,
            "severity": "warning",
        },
    }
    alert_rules.load_alert_rules(rules)
    metrics = {"cpu": 96.0, "memory": 70.0}
    alerts = alert_rules.evaluate_all_rules(metrics)
    alert_names = {a["rule_name"] for a in alerts}
    # cpu_high and cpu_critical both map to the 'cpu' metric.
    assert alert_names == {"cpu_high", "cpu_critical"}

    enabled = alert_rules.get_enabled_rules()
    assert "cpu_high" in enabled
    assert "io_high" not in enabled

    # No metric for 'io' means it is skipped regardless of enabled state.
    metrics_no_match = {"cpu": 50.0}
    assert alert_rules.evaluate_all_rules(metrics_no_match) == []


def test_enable_disable_and_reset():
    alert_rules.load_alert_rules({"a": {"enabled": True}})
    assert alert_rules.disable_rule("missing") is False
    assert alert_rules.disable_rule("a") is True
    assert alert_rules.get_alert_rule("a")["enabled"] is False
    assert alert_rules.enable_rule("missing") is False
    assert alert_rules.enable_rule("a") is True
    assert alert_rules.get_alert_rule("a")["enabled"] is True

    alert_rules.load_alert_rules({"x": {"enabled": True}})
    alert_rules.reset_alert_rules()
    assert "cpu_high" in alert_rules.get_all_alert_rules()


# ---------------------------------------------------------------------------
# core/anomaly_detection.py
# ---------------------------------------------------------------------------


class _FakeProphet:
    def __init__(self, growth="linear", yearly_seasonality=True, weekly_seasonality=True):
        self.growth = growth
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self._df = None

    def fit(self, df):
        self._df = df.copy()

    def make_future_dataframe(self, periods=0, freq="D"):
        return self._df[["ds"]].copy()

    def predict(self, future):
        merged = future[["ds"]].merge(self._df[["ds", "y"]], on="ds", how="left")
        yhat = merged["y"].fillna(0).reset_index(drop=True)
        return pd.DataFrame({"ds": future["ds"].reset_index(drop=True), "yhat": yhat})


class _FakeIsolationForest:
    def __init__(self, n_estimators=100, contamination="auto", random_state=42):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

    def fit(self, X):
        return self

    def predict(self, X):
        return np.ones(len(X), dtype=int)

    def decision_function(self, X):
        return np.zeros(len(X))


@pytest.fixture
def fake_anomaly_models(monkeypatch):
    """Inject deterministic Prophet and IsolationForest replacements."""
    monkeypatch.setitem(sys.modules, "prophet", SimpleNamespace(Prophet=_FakeProphet))
    monkeypatch.setattr(anomaly, "IsolationForest", _FakeIsolationForest, raising=False)


def test_anomaly_detector_init_and_prepare(fake_anomaly_models):
    detector = anomaly.AnomalyDetector(
        growth="linear", yearly_seasonality=False, weekly_seasonality=False
    )
    assert detector.growth == "linear"
    assert detector.prophet_model is None
    assert detector.iforest is None

    valid = pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-02T00:00:00Z"],
            "value": [10.0, 20.0],
        }
    )
    prepared = detector._prepare_dataframe(valid)
    assert list(prepared.columns) == ["ds", "y"]
    assert len(prepared) == 2

    # Missing required columns.
    with pytest.raises(ValueError, match="timestamp.*value"):
        detector._prepare_dataframe(pd.DataFrame({"x": [1]}))

    # Unparseable timestamps.
    bad_ts = pd.DataFrame({"timestamp": ["not-a-date"], "value": [1.0]})
    with pytest.raises(ValueError, match="Failed to parse some timestamps"):
        detector._prepare_dataframe(bad_ts)

    # NaN values: first value NaN -> filled with 0; middle NaN -> ffill.
    with_nan = pd.DataFrame(
        {
            "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "value": [None, 2.0, None],
        }
    )
    prepared_nan = detector._prepare_dataframe(with_nan)
    assert prepared_nan["y"].tolist() == [0.0, 2.0, 2.0]


def test_anomaly_train_and_detect(fake_anomaly_models):
    detector = anomaly.AnomalyDetector()
    train_df = pd.DataFrame(
        {
            "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
            "value": [10.0, 12.0, 11.0, 13.0],
        }
    )
    detector.train(train_df)
    assert detector.prophet_model is not None
    assert detector.iforest is not None

    # Detect on the same data: fake model returns yhat == y, so all normal.
    result = detector.detect(train_df)
    assert "is_anomaly" in result.columns
    assert "anomaly_score" in result.columns
    assert not result["is_anomaly"].any()
    assert result["anomaly_score"].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_anomaly_detect_before_train(fake_anomaly_models):
    detector = anomaly.AnomalyDetector()
    df = pd.DataFrame({"timestamp": ["2024-01-01"], "value": [1.0]})
    with pytest.raises(RuntimeError, match="Model not trained"):
        detector.detect(df)


# ---------------------------------------------------------------------------
# core/backup_manager.py
# ---------------------------------------------------------------------------


def _patch_subprocess_runner(monkeypatch, *, stdout="ok\n", fail_on=None, return_dict=False):
    """Patch backup_manager's subprocess_runner for deterministic commands."""
    calls = []

    class _Runner:
        CompletedProcess = subprocess.CompletedProcess

        def run(self, parts, **kwargs):
            calls.append(parts)
            command = " ".join(str(p) for p in parts)
            if fail_on and fail_on in command:
                raise RuntimeError("wal-g failed")
            if return_dict:
                return {"stdout": stdout, "stderr": ""}
            return subprocess.CompletedProcess(parts, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(bm, "subprocess_runner", _Runner())
    return calls


def test_validate_config_value():
    assert bm._validate_config_value("wal-g", "WALG_PATH") == "wal-g"
    assert bm._validate_config_value("s3://aiops-backups", "S3_URL") == "s3://aiops-backups"
    with pytest.raises(ValueError, match="cannot be empty"):
        bm._validate_config_value("", "X")
    with pytest.raises(ValueError, match="invalid characters"):
        bm._validate_config_value("s3://bad bucket", "X")
    with pytest.raises(ValueError, match="invalid characters"):
        bm._validate_config_value("wal;g", "X")


def test_sanitize_for_logging():
    pg = "wal-g backup-push postgresql://user:secret@host:5432/db"
    assert "***" in bm._sanitize_for_logging(pg)
    s3 = "wal-g --bucket s3://bucket:secret@host backup-list"
    assert "***" in bm._sanitize_for_logging(s3)
    clean = "wal-g backup-list"
    assert bm._sanitize_for_logging(clean) == clean


def test_backup_database_success(monkeypatch):
    calls = _patch_subprocess_runner(monkeypatch, return_dict=True, stdout="backup pushed")
    assert bm.backup_database() is True
    assert any("backup-push" in " ".join(str(p) for p in c) for c in calls)


def test_backup_database_failure(monkeypatch):
    _patch_subprocess_runner(monkeypatch, fail_on="backup-push")
    assert bm.backup_database() is False


def test_restore_latest_backup_success(monkeypatch):
    calls = _patch_subprocess_runner(monkeypatch, stdout="restored")
    assert bm.restore_latest_backup() is True
    commands = [" ".join(str(p) for p in c) for c in calls]
    assert any("backup-fetch" in c and "LATEST" in c for c in commands)
    assert any("restore" in c for c in commands)


def test_restore_latest_backup_fetch_fails(monkeypatch):
    _patch_subprocess_runner(monkeypatch, fail_on="backup-fetch")
    assert bm.restore_latest_backup() is False


def test_list_backups(monkeypatch):
    _patch_subprocess_runner(monkeypatch, stdout="backup_1\nbackup_2\n\n")
    backups = bm.list_backups()
    assert backups == ["backup_1", "backup_2"]


# ---------------------------------------------------------------------------
# core/circuit_breaker.py
# ---------------------------------------------------------------------------


def test_circuit_breaker_state_transitions():
    breaker = cb.CircuitBreaker(failure_threshold=3, recovery_timeout=1)
    assert breaker.state == cb.CircuitState.CLOSED

    # Three failures should open the circuit.
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == cb.CircuitState.OPEN
    assert breaker.allow_request() is False

    # Simulate that the recovery timeout has elapsed.
    breaker._last_failure_time = datetime.now() - timedelta(seconds=2)
    assert breaker.state == cb.CircuitState.HALF_OPEN

    # In HALF_OPEN, a failure re-opens immediately.
    breaker.record_failure()
    assert breaker.state == cb.CircuitState.OPEN

    # Set to HALF_OPEN again and record two successes to close.
    breaker._state = cb.CircuitState.HALF_OPEN
    breaker._success_count = 0
    breaker.record_success()
    assert breaker.state == cb.CircuitState.HALF_OPEN
    breaker.record_success()
    assert breaker.state == cb.CircuitState.CLOSED


def test_circuit_breaker_stats_and_reset():
    breaker = cb.CircuitBreaker(failure_threshold=2)
    breaker.record_failure()
    stats = breaker.get_stats()
    assert stats["state"] == "closed"
    assert stats["failure_count"] == 1
    assert stats["last_failure_time"] is not None

    breaker.reset()
    stats = breaker.get_stats()
    assert stats["failure_count"] == 0
    assert stats["success_count"] == 0
    assert stats["last_failure_time"] is None


def test_sync_circuit_breaker_success_and_expected_exception():
    call_count = 0

    @cb.circuit_breaker(failure_threshold=2, expected_exception=ValueError)
    def may_fail(value):
        nonlocal call_count
        call_count += 1
        if value < 0:
            raise ValueError("negative")
        return value * 2

    assert may_fail(5) == 10
    with pytest.raises(ValueError):
        may_fail(-1)
    assert call_count == 2


def test_sync_circuit_breaker_unexpected_exception():
    @cb.circuit_breaker(failure_threshold=2, expected_exception=ValueError)
    def boom():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        boom()


def test_sync_circuit_breaker_timeout():
    @cb.circuit_breaker(timeout=0.01)
    def slow():
        time.sleep(0.1)

    with pytest.raises(TimeoutError):
        slow()


def test_sync_circuit_breaker_opens():
    @cb.circuit_breaker(failure_threshold=2, expected_exception=Exception)
    def always_fails():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError, match="fail"):
        always_fails()
    with pytest.raises(RuntimeError, match="fail"):
        always_fails()
    with pytest.raises(cb.CircuitBreakerError, match="open"):
        always_fails()


def test_async_circuit_breaker():
    @cb.circuit_breaker(failure_threshold=2, expected_exception=ValueError, timeout=0.01)
    async def async_may_fail(value):
        if value == "timeout":
            await asyncio.sleep(1)
        if value == "error":
            raise ValueError("expected")
        return value

    assert asyncio.run(async_may_fail("ok")) == "ok"
    with pytest.raises(ValueError):
        asyncio.run(async_may_fail("error"))
    with pytest.raises(cb.CircuitBreakerError, match="timeout"):
        asyncio.run(async_may_fail("timeout"))


def test_circuit_breaker_registry():
    registry = cb.CircuitBreakerRegistry()
    b1 = registry.register("api", failure_threshold=3)
    b2 = registry.register("db", failure_threshold=5)

    assert registry.get("api") is b1
    assert registry.get("missing") is None

    all_stats = registry.get_all_stats()
    assert set(all_stats.keys()) == {"api", "db"}

    b1.record_failure()
    assert registry.reset("api") is True
    assert b1.get_stats()["failure_count"] == 0
    assert registry.reset("missing") is False

    registry.reset_all()
    assert b2.get_stats()["failure_count"] == 0


def test_global_circuit_breaker_helpers():
    b = cb.register_circuit_breaker("global_test", failure_threshold=2)
    assert cb.get_circuit_breaker("global_test") is b
    assert cb.get_circuit_breaker("not_registered") is None
    cb._global_registry.reset_all()
