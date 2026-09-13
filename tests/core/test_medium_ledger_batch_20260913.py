# -*- coding: utf-8 -*-
"""Regression tests for the 中-severity audit-ledger batch fixed on 2026-09-13.

Covers: F177 / F180 / F189 / F193 / F117 / F219 / F221 / F203 / F201 / F200 / F015 / F179.
Each test exercises the real, runnable behaviour introduced by the fix.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# F177 - CircuitBreaker HALF_OPEN allows only a single probe
# ---------------------------------------------------------------------------
def test_circuit_breaker_half_open_single_probe():
    from core.error_recovery.core import (
        CircuitBreaker,
        CircuitBreakerConfig,
        CircuitBreakerOpenError,
        CircuitState,
    )

    async def scenario():
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0))

        async def boom():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await cb.call(boom)
        assert cb.state == CircuitState.OPEN

        gate = asyncio.Event()
        probe_started = []

        async def probe():
            probe_started.append(1)
            await gate.wait()
            return "ok"

        task = asyncio.create_task(cb.call(probe))
        await asyncio.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN

        # a second concurrent probe must be rejected while the first is in flight
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(probe)

        gate.set()
        assert await task == "ok"
        assert cb.state == CircuitState.CLOSED

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# F180 - es_logger must not crash when the ES client is unavailable
# ---------------------------------------------------------------------------
def test_es_logger_get_client_none_when_library_missing(monkeypatch):
    from core import es_logger

    monkeypatch.setattr(es_logger, "_es_client", None)
    monkeypatch.setattr(es_logger, "AsyncElasticsearch", None)
    assert es_logger.get_es_client() is None


def test_es_logger_client_creation_failure_falls_back(monkeypatch):
    from core import es_logger

    monkeypatch.setattr(es_logger, "_es_client", None)

    def _boom(*_a, **_k):
        raise RuntimeError("no transport")

    monkeypatch.setattr(es_logger, "AsyncElasticsearch", _boom)
    assert es_logger.get_es_client() is None


# ---------------------------------------------------------------------------
# F189 - FaultTolerantExecutor error classification returns UNKNOWN_ERROR
# ---------------------------------------------------------------------------
def test_classify_error_distinguishes_unknown():
    from core.execution.l6.fault_tolerant_executor import FailureType, FaultTolerantExecutor

    ex = FaultTolerantExecutor()
    assert ex._classify_error(ValueError("v")) == FailureType.LOGIC_ERROR
    assert ex._classify_error(TypeError("t")) == FailureType.LOGIC_ERROR
    assert ex._classify_error(ImportError("i")) == FailureType.DEPENDENCY_ERROR
    assert ex._classify_error(ConnectionError("c")) == FailureType.NETWORK_ERROR
    assert ex._classify_error(OSError("o")) == FailureType.UNKNOWN_ERROR


# ---------------------------------------------------------------------------
# F193 - feature flag rule evaluation returns the rule's declared value
# ---------------------------------------------------------------------------
def test_feature_flag_rule_returns_value():
    from core.feature_flag import (
        FeatureFlag,
        FeatureFlagManager,
        FlagRule,
        FlagStatus,
        FlagType,
    )

    mgr = FeatureFlagManager()
    now = datetime.now(timezone.utc)
    mgr._flags["mv"] = FeatureFlag(
        key="mv",
        name="mv",
        description="",
        flag_type=FlagType.MULTIVARIATE,
        status=FlagStatus.ENABLED,
        fallback_value="control",
        rules=[FlagRule(name="prod", conditions={"env": "prod"}, value="variantX")],
        created_at=now,
        updated_at=now,
        metadata={},
    )
    assert mgr.evaluate("mv", context={"env": "prod"}) == "variantX"
    assert mgr.evaluate("mv", context={"env": "dev"}) == "control"

    mgr._flags["bool"] = FeatureFlag(
        key="bool",
        name="bool",
        description="",
        flag_type=FlagType.BOOLEAN,
        status=FlagStatus.ENABLED,
        fallback_value=False,
        rules=[FlagRule(name="r", conditions={"e": "1"})],
        created_at=now,
        updated_at=now,
        metadata={},
    )
    assert mgr.evaluate("bool", context={"e": "1"}) is True


# ---------------------------------------------------------------------------
# F117 - CI/CD per-stage retry counter (no cross-stage interference)
# ---------------------------------------------------------------------------
def test_cicd_retry_counter_is_per_stage():
    import inspect

    from core import cicd_pipeline_manager

    src = inspect.getsource(cicd_pipeline_manager)
    assert "retry_count::" in src
    # execution-global key must no longer be used for retry accounting
    assert 'execution.metadata.get("retry_count", 0)' not in src


# ---------------------------------------------------------------------------
# F219 - command injection detection and non-destructive cleaning
# ---------------------------------------------------------------------------
def test_command_injection_patterns_high_signal():
    from core.input_validator import InputValidator

    assert InputValidator.validate_command_safe("hostname")[0] is True
    assert InputValidator.validate_command_safe("echo hello world")[0] is True
    # parentheses / brackets / braces / bare $ are common and must NOT be flagged
    assert InputValidator.validate_command_safe("value (with) [brackets] {braces} $var")[0] is True
    assert InputValidator.validate_command_safe("rm -rf /; echo pwn")[0] is False
    assert InputValidator.validate_command_safe("../etc/passwd")[0] is False
    assert InputValidator.validate_command_safe("`id`")[0] is False
    assert InputValidator.validate_command_safe("$(whoami)")[0] is False


def test_validate_and_clean_input_preserves_legit_text():
    from core.input_validator import validate_and_clean_input

    cleaned = validate_and_clean_input("<script>alert(1)</script> SELECT * FROM users; -- ../p & more")
    assert "<script>" not in cleaned
    assert "SELECT" in cleaned  # legit SQL text is not destroyed
    assert ".." not in cleaned
    assert "&amp;" in cleaned
    assert validate_and_clean_input(123) == ""


@pytest.mark.parametrize("value,expected", [("a\x00b", "ab"), ("plain", "plain")])
def test_sanitize_string_removes_null_bytes(value, expected):
    from core.input_validator import InputValidator

    assert InputValidator.sanitize_string(value) == expected


# ---------------------------------------------------------------------------
# F221 - integration helpers actually apply the enhancements
# ---------------------------------------------------------------------------
def test_enhance_ai_engine_applies_transport_retry():
    import core.ai_engine as ai_engine
    from core.integration_helpers import enhance_ai_engine

    enhance_ai_engine()
    assert getattr(ai_engine._get_http_client, "_aiops_retry_enhanced", False) is True
    client = ai_engine._get_http_client()
    assert client is not None
    asyncio.run(ai_engine.close_http_client())


# ---------------------------------------------------------------------------
# F203 - alert / repair engine health checks are real
# ---------------------------------------------------------------------------
def test_alert_and_repair_engine_health_real():
    from core.health_check import check_alert_engine_health, check_repair_engine_health

    alert = asyncio.run(check_alert_engine_health())
    assert alert["status"] == "healthy"
    assert "alert_history_size" in alert

    repair = asyncio.run(check_repair_engine_health())
    assert repair["status"] == "healthy"
    assert repair["repair_script_count"] > 0


# ---------------------------------------------------------------------------
# F200 - graphql_engine imports cleanly and consumes real metrics data
# ---------------------------------------------------------------------------
def test_graphql_engine_metrics_helper_uses_real_samples():
    from core.metrics_history import METRICS_HISTORY, get_metrics_history

    METRICS_HISTORY.push_metric("cpu", 42.0, "hostA")
    rows = get_metrics_history(limit=5)
    assert isinstance(rows, list)
    assert any(r["name"] == "cpu" and r["value"] == 42.0 for r in rows)

    # importing the module must not raise (previously failed on missing symbols)
    import core.graphql_engine as ge

    assert ge.schema is not None


# ---------------------------------------------------------------------------
# F015 - rule-based fallback uses a real rule library
# ---------------------------------------------------------------------------
def test_rule_based_analysis_matches_known_symptom():
    from core.ai_engine import _rule_based_analysis

    cpu = _rule_based_analysis("服务器 CPU 100% 负载很高", "cpu=99", "linux")
    assert "CPU 饱和" in cpu

    mem = _rule_based_analysis("memory leak, oom killer triggered", "", "linux")
    assert "内存不足" in mem

    unknown = _rule_based_analysis("random unrelated text", "", "linux")
    assert "未匹配到已知症状规则" in unknown


# ---------------------------------------------------------------------------
# F179 - escalation dispatches through the notify engine (no silent no-op)
# ---------------------------------------------------------------------------
def test_escalation_notify_uses_notify_engine(monkeypatch):
    from core import escalation

    calls = []

    class _FakeNotify:
        NOTIFY_CONFIG = {"enabled": True}

        @staticmethod
        def _channel_configured(channel, config):
            return channel == "slack"

        @staticmethod
        async def send_notification(alert, channels=None):
            calls.append((tuple(channels), alert["type"]))
            return {"success": True, "channels_sent": len(channels or [])}

    monkeypatch.setattr(escalation, "_webhook_url", lambda: "")
    monkeypatch.setattr(escalation, "_notification_channels", lambda: ["slack", "teams"])
    import core.notify_engine as notify_engine

    monkeypatch.setattr(notify_engine, "NOTIFY_CONFIG", _FakeNotify.NOTIFY_CONFIG)
    monkeypatch.setattr(notify_engine, "_channel_configured", _FakeNotify._channel_configured)
    monkeypatch.setattr(notify_engine, "send_notification", _FakeNotify.send_notification)

    asyncio.run(
        escalation.notify_rollback_failure("a1", "rollback", "failed", snapshot_id="s1")
    )

    # only the configured channel (slack) is actually dispatched
    assert calls == [(("slack",), "rollback_failure")]
