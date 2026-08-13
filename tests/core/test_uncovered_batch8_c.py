# -*- coding: utf-8 -*-
"""Functional tests for core.cost_monitor, core.context_compression,
core.capacity_engine, core.data_lifecycle_operations and core.compliance."""

import asyncio
import os
import sys
import time
import types
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest

import core.capacity_engine as capacity_engine
import core.compliance as compliance
import core.context_compression as context_compression
import core.cost_monitor as cost_monitor
import core.data_lifecycle_operations as dlo

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.cost_monitor
# ---------------------------------------------------------------------------
def _make_fake_boto3(response=None, client_error=None):
    """Build a minimal fake boto3 module for cost collection tests."""
    response = response or {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-15"},
                "Groups": [
                    {
                        "Keys": ["EC2"],
                        "Metrics": {
                            "BlendedCost": {"Amount": "12.50", "Unit": "USD"}
                        },
                    },
                    {
                        "Keys": [],
                        "Metrics": {
                            "BlendedCost": {"Amount": "3.00", "Unit": "USD"}
                        },
                    },
                ],
            }
        ]
    }

    class _FakeClient:
        def __init__(self, service):
            self._service = service

        def get_cost_and_usage(self, **kwargs):
            if client_error:
                raise client_error
            assert kwargs["Granularity"] == "DAILY"
            assert self._service == "ce"
            return response

    return types.SimpleNamespace(client=_FakeClient)


@pytest.fixture
def _fixed_costs(monkeypatch):
    """Return deterministic cost records and patch collect_costs for dependent tests."""
    today = datetime.now()
    records = [
        {"timestamp": (today - timedelta(days=1)).isoformat(), "cost": 10.0, "source": "aws"},
        {"timestamp": (today - timedelta(days=2)).isoformat(), "cost": 20.0, "source": "aws"},
    ]
    return records


def test_collect_costs_from_aws(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", _make_fake_boto3())
    records = cost_monitor.collect_costs()
    assert len(records) == 2
    assert records[0]["service"] == "EC2"
    assert records[0]["cost"] == 12.5
    assert records[0]["currency"] == "USD"
    assert records[1]["service"] == "unknown"
    assert records[1]["cost"] == 3.0


def test_collect_costs_aws_api_error(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "boto3", _make_fake_boto3(client_error=RuntimeError("aws down"))
    )
    assert cost_monitor.collect_costs() == []


def test_collect_costs_when_boto3_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)
    assert cost_monitor.collect_costs() == []


def test_forecast_costs_with_history(monkeypatch, _fixed_costs):
    monkeypatch.setattr(cost_monitor, "collect_costs", lambda: _fixed_costs)
    forecast = cost_monitor.forecast_costs(days=3)
    assert len(forecast) == 3
    avg = sum(r["cost"] for r in _fixed_costs) / len(_fixed_costs)
    assert forecast[0]["forecasted_cost"] == pytest.approx(avg * 1.01, rel=1e-6)
    assert forecast[1]["forecasted_cost"] == pytest.approx(avg * 1.02, rel=1e-6)
    assert forecast[0]["confidence"] == "medium"
    assert forecast[0]["currency"] == "USD"


def test_forecast_costs_empty_history(monkeypatch):
    monkeypatch.setattr(cost_monitor, "collect_costs", lambda: [])
    assert cost_monitor.forecast_costs(days=5) == []


def test_forecast_costs_error_handling(monkeypatch):
    monkeypatch.setattr(
        cost_monitor, "collect_costs", MagicMock(side_effect=RuntimeError("boom"))
    )
    assert cost_monitor.forecast_costs(days=5) == []


def _sample_costs_for_budget(total):
    today = datetime.now()
    per = total / 2.0
    return [
        {"timestamp": (today - timedelta(days=2)).isoformat(), "cost": per},
        {"timestamp": (today - timedelta(days=1)).isoformat(), "cost": per},
    ]


def test_budget_status_healthy(monkeypatch):
    monkeypatch.setattr(
        cost_monitor, "collect_costs", lambda: _sample_costs_for_budget(1000.0)
    )
    status = cost_monitor.budget_status()
    assert status["status"] == "healthy"
    assert status["alert_level"] == "low"
    assert status["budget"]["current_spend"] == pytest.approx(1000.0)
    assert status["recommendations"] == []


def test_budget_status_warning(monkeypatch):
    monkeypatch.setattr(
        cost_monitor, "collect_costs", lambda: _sample_costs_for_budget(4200.0)
    )
    status = cost_monitor.budget_status()
    assert status["status"] == "warning"
    assert status["alert_level"] == "medium"
    assert len(status["recommendations"]) == 3


def test_budget_status_critical(monkeypatch):
    monkeypatch.setattr(
        cost_monitor, "collect_costs", lambda: _sample_costs_for_budget(4600.0)
    )
    status = cost_monitor.budget_status()
    assert status["status"] == "critical"
    assert status["alert_level"] == "high"
    assert len(status["recommendations"]) == 3


def test_budget_status_error(monkeypatch):
    monkeypatch.setattr(
        cost_monitor, "collect_costs", MagicMock(side_effect=RuntimeError("db fail"))
    )
    status = cost_monitor.budget_status()
    assert status["status"] == "error"
    assert status["budget"] is None
    assert "Unable to retrieve" in status["message"]


# ---------------------------------------------------------------------------
# core.context_compression
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _cheap_token_count(monkeypatch):
    """Use a deterministic, cheap token count during context compression tests."""
    monkeypatch.setattr(
        context_compression, "estimate_tokens", lambda text, model=None: len(text) if text else 0
    )


def test_compress_context_already_under_budget():
    context = {"goal": "fix checkout latency", "history": []}
    compressed = context_compression.compress_context(context, max_tokens=1000)
    assert compressed == context


def test_compress_context_empty():
    assert context_compression.compress_context({}, max_tokens=100) == {}


def test_compress_context_summarizes_long_history():
    context = {
        "goal": "find root cause",
        "history": [{"step": i, "action": f"check service {i}"} for i in range(100)],
    }
    compressed = context_compression.compress_context(context, max_tokens=1500)
    assert "goal" in compressed
    assert len(compressed["history"]) == 4  # summary string + 3 kept items
    assert "earlier items" in compressed["history"][0]


def test_compress_context_truncates_long_strings():
    long_value = "word " * 500
    context = {
        "goal": "keep me",
        "notes": long_value,
    }
    compressed = context_compression.compress_context(context, max_tokens=350)
    assert compressed["goal"] == "keep me"
    assert "chars omitted" in compressed["notes"]


def test_compress_context_drops_auxiliary_keys():
    context = {"goal": "preserve"}
    for i in range(40):
        context[f"auxiliary_metadata_field_{i:02d}"] = "x"
    compressed = context_compression.compress_context(context, max_tokens=250)
    assert "goal" in compressed
    # some auxiliary keys were removed so token count dropped
    assert len(compressed) < len(context)


def test_compress_context_respects_custom_protected_keys():
    context = {"my_query": "important", "noise": "n" * 1000}
    compressed = context_compression.compress_context(
        context, max_tokens=50, protected_keys={"my_query"}
    )
    assert "my_query" in compressed
    assert "noise" not in compressed


def test_compress_prompt_text_already_fits():
    text = "Short prompt."
    assert context_compression.compress_prompt_text(text, max_tokens=100) == text


def test_compress_prompt_text_empty():
    assert context_compression.compress_prompt_text("", max_tokens=10) == ""


def test_compress_prompt_text_protects_and_truncates():
    sections = []
    for i in range(6):
        if i % 2 == 0:
            sections.append(f"用户问题\nWhat is wrong with service {i}?\nline2\nline3\nline4\nline5")
        else:
            sections.append(
                f"辅助分析 {i}\nline1\nline2\nline3\nline4\nline5\nline6\nline7"
            )
    text = "\n\n".join(sections)
    compressed = context_compression.compress_prompt_text(text, max_tokens=200)
    assert "用户问题" in compressed
    assert len(compressed) < len(text)
    # Non-protected sections were summarized or removed
    assert "辅助分析" not in compressed or "summarized" in compressed


def test_json_summary_variants():
    assert context_compression._json_summary([]) == "[]"
    assert "more" in context_compression._json_summary([{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}])
    assert "a=" in context_compression._json_summary({"a": 1, "b": 2})
    assert context_compression._json_summary("hello") == "hello"


def test_summarize_list_and_truncate():
    assert context_compression._summarize_list([1, 2]) == [1, 2]
    summarized = context_compression._summarize_list([1, 2, 3, 4, 5], keep_last=2)
    assert len(summarized) == 3
    assert summarized[-2:] == [4, 5]

    short = "abc"
    assert context_compression._truncate_text(short, 200) == short
    long = "x" * 500
    truncated = context_compression._truncate_text(long, 200)
    assert truncated.startswith("x" * 80)
    assert truncated.endswith("x" * 80)
    assert "chars omitted" in truncated


def test_serialize_handles_strings_and_errors(monkeypatch):
    assert context_compression._serialize("plain") == "plain"
    assert "{" in context_compression._serialize({"a": 1})

    monkeypatch.setattr(context_compression.json, "dumps", MagicMock(side_effect=RuntimeError("bad")))
    assert context_compression._serialize("value") == "value"


# ---------------------------------------------------------------------------
# core.capacity_engine
# ---------------------------------------------------------------------------
def test_to_floats_filters_invalid():
    assert capacity_engine._to_floats([1, "2.5", "bad", None, 3]) == [1.0, 2.5, 3.0]
    assert capacity_engine._to_floats("not a list") == []
    assert capacity_engine._to_floats([]) == []


def test_linear_forecast_corner_cases():
    assert capacity_engine._linear_forecast([], 7) == 0.0
    assert capacity_engine._linear_forecast([42.0], 7) == 42.0


def test_linear_forecast_trend():
    values = [10.0, 20.0, 30.0]
    assert capacity_engine._linear_forecast(values, 1) == pytest.approx(40.0, rel=1e-6)
    assert capacity_engine._linear_forecast(values, 7) == pytest.approx(100.0, rel=1e-6)


def test_forecast_capacity_with_history():
    history = {
        "cpu": [45.0, 46.5, 48.0, 49.2, 50.1],
        "memory": [55.0, 57.0, 59.0, 60.5, 62.0],
        "disk": [40.0, 42.0, 44.0, 46.0, 48.0],
        "network": [30.0, 32.0, 34.0, 36.0, 38.0],
    }
    forecasts = capacity_engine.forecast_capacity(history, 7)
    for key in capacity_engine._METRIC_META:
        assert key in forecasts
        assert "forecast7d" in forecasts[key]
        assert "forecast30d" in forecasts[key]
    assert forecasts["cpu"]["currentValue"] == pytest.approx(50.1)


def test_forecast_capacity_uses_defaults_for_missing_and_short():
    forecasts = capacity_engine.forecast_capacity({"cpu": [50.0]}, 7)
    assert forecasts["cpu"]["currentValue"] == pytest.approx(50.1)
    assert forecasts["memory"]["currentValue"] > 0  # default series used


def test_forecast_capacity_non_dict_history():
    forecasts = capacity_engine.forecast_capacity("invalid", 30)
    assert all(forecasts[k]["currentValue"] > 0 for k in capacity_engine._METRIC_META)


def test_generate_scaling_recommendations():
    forecasts = {
        "cpu": {
            "metric": "CPU",
            "forecast7d": 90.0,
            "forecast30d": 95.0,
            "currentValue": 75.0,
            "threshold": 80.0,
            "unit": "%",
        },
        "memory": {
            "metric": "Memory",
            "forecast7d": 70.0,
            "forecast30d": 88.0,
            "currentValue": 75.0,
            "threshold": 85.0,
            "unit": "%",
        },
        "disk": {
            "metric": "Disk",
            "forecast7d": 30.0,
            "forecast30d": 35.0,
            "currentValue": 30.0,
            "threshold": 80.0,
            "unit": "%",
        },
        "network": {
            "metric": "Network",
            "forecast7d": 50.0,
            "forecast30d": 55.0,
            "currentValue": 50.0,
            "threshold": 70.0,
            "unit": "%",
        },
    }
    recs = capacity_engine.generate_scaling_recommendations(forecasts)
    actions = {r["action"] for r in recs}
    priorities = {r["priority"] for r in recs}
    assert "scale-up" in actions
    assert "scale-down" in actions
    assert "no-action" in actions
    assert "high" in priorities
    assert "medium" in priorities
    assert "low" in priorities
    assert all("estimatedCost" in r for r in recs)


# ---------------------------------------------------------------------------
# core.data_lifecycle_operations
# ---------------------------------------------------------------------------
def _fake_sqlalchemy(text_value=lambda s: s):
    return types.SimpleNamespace(text=text_value)


class _FakeAsyncSession:
    def __init__(self, rowcount=5, fail_enter=False, fail_execute=False):
        self.rowcount = rowcount
        self.fail_enter = fail_enter
        self.fail_execute = fail_execute

    async def __aenter__(self):
        if self.fail_enter:
            raise RuntimeError("db unavailable")
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, *args, **kwargs):
        if self.fail_execute:
            raise RuntimeError("execute failed")
        return MagicMock(rowcount=self.rowcount)

    async def commit(self):
        return None


def _set_lifecycle_db_mocks(monkeypatch, rowcount=5, fail_enter=False, fail_execute=False):
    fake_db = types.SimpleNamespace(
        AsyncSessionLocal=lambda: _FakeAsyncSession(
            rowcount=rowcount, fail_enter=fail_enter, fail_execute=fail_execute
        )
    )
    monkeypatch.setitem(sys.modules, "sqlalchemy", _fake_sqlalchemy())
    monkeypatch.setitem(sys.modules, "core.db_engine", fake_db)


def test_archive_alerts_success(monkeypatch):
    _set_lifecycle_db_mocks(monkeypatch, rowcount=12)
    cutoff = datetime(2024, 1, 1, 0, 0, 0)
    assert asyncio.run(dlo.archive_alerts(cutoff)) == 12


def test_archive_metrics_success(monkeypatch):
    _set_lifecycle_db_mocks(monkeypatch, rowcount=7)
    cutoff = datetime(2024, 1, 1, 0, 0, 0)
    assert asyncio.run(dlo.archive_metrics(cutoff)) == 7


def test_archive_alerts_failure(monkeypatch):
    _set_lifecycle_db_mocks(monkeypatch, fail_enter=True)
    cutoff = datetime(2024, 1, 1, 0, 0, 0)
    assert asyncio.run(dlo.archive_alerts(cutoff)) == 0


def test_cleanup_temporary_files_success(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    os.makedirs("temp", exist_ok=True)
    old_file = os.path.join("temp", "old.log")
    new_file = os.path.join("temp", "new.log")
    open(old_file, "w").close()
    open(new_file, "w").close()
    now = time.time()
    os.utime(old_file, (now - 86400, now - 86400))
    os.utime(new_file, (now, now))

    cutoff = datetime.fromtimestamp(now - 3600)
    deleted = asyncio.run(dlo.cleanup_temporary_files(cutoff))
    assert deleted == 1
    assert not os.path.exists(old_file)
    assert os.path.exists(new_file)


def test_cleanup_temporary_files_missing_dir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert asyncio.run(dlo.cleanup_temporary_files(datetime.now())) == 0


def test_cleanup_temporary_files_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    os.makedirs("temp", exist_ok=True)
    bad = os.path.join("temp", "bad.log")
    open(bad, "w").close()
    monkeypatch.setattr(os, "remove", Mock(side_effect=RuntimeError("denied")))
    cutoff = datetime.now() + timedelta(days=1)
    assert asyncio.run(dlo.cleanup_temporary_files(cutoff)) == 0


def _set_redis_mocks(monkeypatch, keys=None, raise_on_call=False):
    if keys is None:
        keys = [b"temp:a", b"temp:b"]
    fake_config = types.SimpleNamespace(
        REDIS_HOST="localhost", REDIS_PORT=6379, REDIS_DB=0
    )
    monkeypatch.setitem(sys.modules, "config", fake_config)

    class _FakeRedis:
        def __init__(self, *args, **kwargs):
            if raise_on_call:
                raise RuntimeError("redis down")

        def keys(self, pattern):
            assert pattern == "temp:*"
            return keys

        def delete(self, *key_list):
            return len(key_list)

    monkeypatch.setitem(sys.modules, "redis", types.SimpleNamespace(Redis=_FakeRedis))


def test_cleanup_temporary_cache_success(monkeypatch):
    _set_redis_mocks(monkeypatch, keys=[b"temp:x", b"temp:y"])
    assert asyncio.run(dlo.cleanup_temporary_cache(datetime.now())) is True


def test_cleanup_temporary_cache_empty(monkeypatch):
    _set_redis_mocks(monkeypatch, keys=[])
    assert asyncio.run(dlo.cleanup_temporary_cache(datetime.now())) is False


def test_cleanup_temporary_cache_failure(monkeypatch):
    _set_redis_mocks(monkeypatch, raise_on_call=True)
    assert asyncio.run(dlo.cleanup_temporary_cache(datetime.now())) is False


# ---------------------------------------------------------------------------
# core.compliance
# ---------------------------------------------------------------------------
def test_check_compliance_and_mask_sensitive():
    assert compliance.check_compliance({"anything": "goes"}) is True

    assert compliance.mask_sensitive("") == ""
    assert compliance.mask_sensitive("abcd") == "****"
    assert compliance.mask_sensitive("secretvalue") == "se*******ue"


def test_mask_sensitive_dict():
    data = {
        "username": "alice",
        "password": "supersecret",
        "api_key": "sk-1234567890",
        "token": "short",
        "public": "visible",
    }
    masked = compliance.mask_sensitive_dict(data)
    assert masked["username"] == "alice"
    assert masked["public"] == "visible"
    assert masked["password"] == "su*******et"
    assert masked["api_key"] == "sk*********90"
    assert masked["token"] == "sh*rt"
