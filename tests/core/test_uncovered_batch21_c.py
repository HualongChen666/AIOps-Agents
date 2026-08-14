# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for batch21_c core modules."""

import asyncio
import json
import threading
import types
from unittest.mock import MagicMock

import pytest

import core.base.storage as storage
import core.config_center as config_center
import core.error_logging.logger as logger_module
import core.prometheus_metrics as metrics
import core.priority_engine as priority_engine
from core.exceptions import AIOpsBaseException
from core.exceptions.base import ErrorCategory, ErrorSeverity

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.config_center
# -----------------------------------------------------------------------------

@pytest.fixture
def fallback_center():
    """ConsulConfigCenter in fallback mode."""
    return config_center.ConsulConfigCenter()


@pytest.fixture
def consul_center(monkeypatch):
    """ConsulConfigCenter backed by a fake consul client."""

    class FakeKV:
        def __init__(self):
            self.data = {}

        def put(self, key, value):
            self.data[key] = value.encode("utf-8")

        def get(self, key, index=None, recurse=False):
            if recurse:
                return None, [
                    {"Key": k, "Value": v} for k, v in self.data.items()
                ]
            raw = self.data.get(key)
            return (None, {"Value": raw}) if raw is not None else (None, None)

        def delete(self, key):
            return key in self.data and self.data.pop(key, None) is not None

    class FakeAgent:
        def self(self):
            return {"Config": {}}

    class FakeConsul:
        def __init__(self, host=None, port=None):
            self.kv = FakeKV()
            self.agent = FakeAgent()

    fake_consul = types.ModuleType("consul")
    fake_consul.Consul = FakeConsul

    monkeypatch.setattr(config_center, "CONSUL_AVAILABLE", True)
    monkeypatch.setattr(config_center, "consul", fake_consul)

    # Prevent real daemon threads from leaking out of watch_config.
    class FakeThread:
        def __init__(self, target=None, daemon=None, args=None, kwargs=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            pass

    monkeypatch.setattr(config_center.threading, "Thread", FakeThread)

    return config_center.ConsulConfigCenter()


def test_fallback_config_lifecycle(fallback_center):
    assert fallback_center.fallback_enabled is True
    assert fallback_center.set_config("app/name", "aiops") is True
    assert fallback_center.get_config("app/name") == "aiops"
    assert fallback_center.get_config("missing", "default") == "default"

    item = fallback_center.get_config_item("app/name")
    assert item.value == "aiops"
    assert item.key == "app/name"

    assert fallback_center.set_config("app/name", "aiops2", metadata={"owner": "sre"}) is True
    assert fallback_center.get_config("app/name") == "aiops2"

    assert fallback_center.delete_config("app/name") is True
    assert fallback_center.get_config("app/name") is None
    assert fallback_center.delete_config("app/name") is False


def test_fallback_listeners_and_all_configs(fallback_center):
    events = []

    def listener(event):
        events.append(event)

    def bad_listener(event):
        raise RuntimeError("listener boom")

    fallback_center.register_change_listener(listener)
    fallback_center.register_change_listener(bad_listener)

    fallback_center.set_config("a", 1)
    fallback_center.set_config("b", 2, metadata={"x": "y"})
    assert len(events) == 2

    assert fallback_center.get_all_configs() == {"a": 1, "b": 2}
    fb = fallback_center.get_fallback_configs()
    assert set(fb.keys()) == {"a", "b"}
    assert fb["b"].metadata == {"x": "y"}

    fallback_center.delete_config("a")
    assert len(events) == 3


def test_fallback_watch_config(fallback_center):
    fallback_center.watch_config("k", lambda v: None)
    assert "k" not in fallback_center.watch_threads


def test_consul_config_lifecycle(consul_center):
    assert consul_center.fallback_enabled is False
    assert consul_center.set_config("app/name", "aiops", metadata={"env": "test"}) is True
    assert consul_center.get_config("app/name") == "aiops"

    item = consul_center.get_config_item("app/name")
    assert item.value == "aiops"
    assert item.metadata == {"env": "test"}

    assert consul_center.delete_config("app/name") is True
    assert consul_center.get_config("app/name", "missing") == "missing"


def test_consul_get_all_configs(consul_center):
    consul_center.set_config("svc/a", 1)
    consul_center.set_config("svc/b", 2)
    consul_center.consul_client.kv.data["raw/key"] = b"not-json"

    all_cfg = consul_center.get_all_configs()
    assert all_cfg["svc/a"] == 1
    assert all_cfg["svc/b"] == 2
    assert all_cfg["raw/key"] == "not-json"


def test_consul_config_errors(consul_center, monkeypatch):
    monkeypatch.setattr(
        consul_center.consul_client.kv, "put", MagicMock(side_effect=RuntimeError("kv down"))
    )
    assert consul_center.set_config("k", "v") is False

    monkeypatch.setattr(
        consul_center.consul_client.kv, "get", MagicMock(side_effect=RuntimeError("kv down"))
    )
    assert consul_center.get_config("k", "d") == "d"
    assert consul_center.get_config_item("k") is None
    assert consul_center.get_all_configs() == {}

    monkeypatch.setattr(
        consul_center.consul_client.kv, "delete", MagicMock(side_effect=RuntimeError("kv down"))
    )
    assert consul_center.delete_config("k") is False


def test_consul_watch_callback(consul_center, monkeypatch):
    consul_center.consul_client.kv.data["svc/a"] = json.dumps(
        {"value": {"ok": True}}
    ).encode("utf-8")

    called = []
    consul_center.watch_config("svc/a", lambda value: called.append(value))
    assert "svc/a" in consul_center.watch_threads
    thread = consul_center.watch_threads["svc/a"]
    assert thread.daemon is True

    # Stop the watch loop after one iteration.
    def raising_sleep(_):
        raise RuntimeError("stop watch")

    monkeypatch.setattr(config_center, "time", types.SimpleNamespace(sleep=raising_sleep))
    with pytest.raises(RuntimeError, match="stop watch"):
        thread.target()

    assert len(called) == 1
    assert called[0]["value"] == {"ok": True}


def test_service_discovery(fallback_center):
    sd = config_center.ServiceDiscovery(fallback_center)
    sd.register_service("api", "api-1", "10.0.0.1", 8080, tags=["v1"])
    sd.register_service("api", "api-2", "10.0.0.2", 8080)
    # Replace api-1 with a new address.
    sd.register_service("api", "api-1", "10.0.0.3", 9090, tags=["v2"])

    instances = sd.discover_service("api")
    assert len(instances) == 2
    assert any(i["address"] == "10.0.0.3" for i in instances)

    sd.deregister_service("api-2")
    assert len(sd.discover_service("api")) == 1

    assert sd.discover_service("missing") == []


def test_config_center_global_instances():
    assert isinstance(config_center.get_config_center(), config_center.ConsulConfigCenter)
    assert isinstance(config_center.get_service_discovery(), config_center.ServiceDiscovery)


# -----------------------------------------------------------------------------
# core.error_logging.logger
# -----------------------------------------------------------------------------

def test_structured_error_logger_lifecycle(tmp_path):
    log_file = str(tmp_path / "error.log")
    el = logger_module.StructuredErrorLogger(log_file=log_file)
    el.log_error("01_01_0001", "debug message", severity="debug")
    el.log_error("01_01_0002", "info message", severity="info")
    el.log_error("01_01_0003", "warning message", severity="warning")
    el.log_error("01_01_0004", "error message", severity="error")
    el.log_error("01_01_0005", "critical message", severity="critical")
    el.log_error("01_01_0006", "fatal message", severity="fatal")
    el.log_error("01_01_0007", "unknown message", severity="unknown")
    el.log_error(
        "01_01_0008",
        "context message",
        context={"service": "test"},
        error_id="err-123",
        stack_trace="frame\nline",
    )

    base_exc = AIOpsBaseException(
        "base error",
        error_code="B01",
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.SYSTEM,
        context={"x": 1},
    )
    el.log_exception(base_exc)

    plain_exc = RuntimeError("plain error")
    el.log_exception(plain_exc, context={"a": 1})

    logger_module.log_error("01_01_0009", "convenience error")
    logger_module.log_exception(plain_exc)

    assert logger_module.get_structured_error_logger() is logger_module._structured_error_logger


# -----------------------------------------------------------------------------
# core.priority_engine
# -----------------------------------------------------------------------------

def test_compute_sla_score(monkeypatch):
    monkeypatch.setattr(priority_engine, "BUSINESS_SLA", {
        "core": 0,
        "high": 1,
        "med": 2,
    })
    monkeypatch.setattr(priority_engine, "DEFAULT_SLA", 3)

    assert priority_engine.compute_sla_score({"business_name": "core"}) == 0
    assert priority_engine.compute_sla_score({"business_name": "high"}) == 1
    assert priority_engine.compute_sla_score({"business_name": "med"}) == 2
    assert priority_engine.compute_sla_score({"business_name": "unknown"}) == 3
    assert priority_engine.compute_sla_score({"business_name": ""}) == 3
    assert priority_engine.compute_sla_score({}) == 3

    monkeypatch.setattr(priority_engine, "BUSINESS_SLA", {"bad_str": "x"})
    assert priority_engine.compute_sla_score({"business_name": "bad_str"}) == 3

    monkeypatch.setattr(priority_engine, "BUSINESS_SLA", {"bad_int": 5})
    assert priority_engine.compute_sla_score({"business_name": "bad_int"}) == 3


# -----------------------------------------------------------------------------
# core.base.storage
# -----------------------------------------------------------------------------

def test_base_storage_lifecycle():
    class DummyStorage(storage.BaseStorage):
        def __init__(self, name, config=None):
            super().__init__(name, config)

        def initialize(self):
            self._is_initialized = True
            return True

        def close(self):
            self._is_initialized = False

        async def store(self, key, value, metadata=None):
            return True

        async def retrieve(self, key):
            return "value"

        async def delete(self, key):
            return True

        async def query(self, query):
            return [{"key": "value"}]

    s = DummyStorage("dummy", {"host": "localhost"})
    assert s.validate_config(["host"]) is True
    assert s.validate_config(["host", "missing"]) is False

    status = s.get_status()
    assert status["name"] == "dummy"
    assert status["initialized"] is False
    assert status["connected"] is False
    assert status["config"] == {"host": "localhost"}

    with s:
        assert s._is_initialized is True
    assert s._is_initialized is False

    assert asyncio.run(s.store("k", "v")) is True
    assert asyncio.run(s.retrieve("k")) == "value"
    assert asyncio.run(s.delete("k")) is True
    assert asyncio.run(s.query({})) == [{"key": "value"}]


# -----------------------------------------------------------------------------
# core.prometheus_metrics
# -----------------------------------------------------------------------------

def test_prometheus_metrics_exporter(monkeypatch):
    exporter = metrics.get_metrics_exporter()

    exporter.record_api_request("/api", "GET", 0.12, 200)
    exporter.record_api_request("/api", "POST", 0.23, 500)

    exporter.record_db_query("users", "select", 0.05)
    exporter.record_db_query("users", "insert", 0.05, success=False)
    exporter.record_db_pool_stats(3, 7)

    exporter.record_llm_inference("gpt-4", "openai", 1.2, 10, 20, 0.05)

    exporter.record_rag_retrieval("kb", 0.3)
    exporter.record_rag_generation("gpt-4", 0.5)
    exporter.record_rag_e2e("kb", "gpt-4", 1.0)

    exporter.record_vector_search("kb", 768, 0.1)
    exporter.record_agent_execution("sre", "sync", 0.2)

    exporter.update_performance_regressions("high", "open", 2)
    exporter.record_system_resources("host-1", 45.0, 60.0)
    exporter.record_queue_depth("q1", 5)
    exporter.record_active_sessions("web", 12)
    exporter.record_websocket_connections("alerts", 3)

    exporter.set_app_info({"version": "1.0.0"})

    fake_start = MagicMock()
    monkeypatch.setattr(metrics, "start_http_server", fake_start)
    exporter.start_metrics_server(9099)
    fake_start.assert_called_once_with(9099)

    failing_start = MagicMock(side_effect=RuntimeError("port in use"))
    monkeypatch.setattr(metrics, "start_http_server", failing_start)
    exporter.start_metrics_server(9099)  # logs and swallows the exception
