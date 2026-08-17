# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.mfa_service, core.otel_exporter,
core.heartbeat, core.slo_metrics_client and core.slo_incident_store."""

import asyncio
import importlib
import json
import logging
import sys
import types
from contextlib import AbstractContextManager
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import MagicMock

import pyotp
import pytest

import core.heartbeat as heartbeat
import core.mfa_service as mfa_service
import core.otel_exporter as otel
import core.slo_incident_store as sis
import core.slo_metrics_client as smc

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.mfa_service
# ---------------------------------------------------------------------------
class FakeUserService:
    """Deterministic stand-in for core.user_service.UserService."""

    def __init__(self):
        self.users = {}
        self.fail_enable = False
        self.fail_disable = False
        self.last_enable_args = None

    async def enable_mfa(self, username, secret, recovery_codes):
        if self.fail_enable:
            return False
        self.last_enable_args = (username, secret, recovery_codes)
        return True

    async def disable_mfa(self, username):
        if self.fail_disable:
            return False
        return True

    async def get_user_by_username(self, username):
        return self.users.get(username)


@pytest.fixture
def fake_user_svc(monkeypatch):
    fake = FakeUserService()
    monkeypatch.setattr(mfa_service, "user_service", fake)
    return fake


def _make_user(**kwargs):
    defaults = {
        "mfa_enabled": False,
        "mfa_secret": None,
        "recovery_codes": None,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_generate_secret_and_totp():
    secret = mfa_service.MFAService.generate_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16
    totp = mfa_service.MFAService.generate_totp(secret)
    assert isinstance(totp, pyotp.TOTP)


def test_generate_qr_code():
    secret = mfa_service.MFAService.generate_secret()
    url = mfa_service.MFAService.generate_qr_code(secret, "alice")
    assert url.startswith("data:image/png;base64,")


def test_verify_totp():
    secret = mfa_service.MFAService.generate_secret()
    totp = pyotp.TOTP(secret)
    token = totp.now()
    assert mfa_service.MFAService.verify_totp(secret, token) is True
    assert mfa_service.MFAService.verify_totp(secret, "000000") is False


def test_generate_recovery_codes():
    codes = mfa_service.MFAService.generate_recovery_codes()
    assert len(codes) == 10
    for code in codes:
        assert code.count("-") == 2
        assert all(c in "0123456789ABCDEF-" for c in code)

    codes = mfa_service.MFAService.generate_recovery_codes(count=3)
    assert len(codes) == 3


def test_enable_and_disable_mfa(fake_user_svc):
    secret, qr, codes = asyncio.run(mfa_service.MFAService.enable_mfa_for_user("alice"))
    assert secret and qr and codes
    assert fake_user_svc.last_enable_args[0] == "alice"

    assert asyncio.run(mfa_service.MFAService.disable_mfa_for_user("alice")) is True


def test_enable_mfa_failure(fake_user_svc):
    fake_user_svc.fail_enable = True
    with pytest.raises(Exception, match="启用MFA失败"):
        asyncio.run(mfa_service.MFAService.enable_mfa_for_user("bob"))


def test_verify_user_mfa_totp_success_and_recovery(fake_user_svc):
    secret = mfa_service.MFAService.generate_secret()
    codes = mfa_service.MFAService.generate_recovery_codes(count=2)
    user = _make_user(
        mfa_enabled=True,
        mfa_secret=secret,
        recovery_codes=json.dumps(codes),
    )
    fake_user_svc.users["alice"] = user

    totp = pyotp.TOTP(secret)
    assert asyncio.run(mfa_service.MFAService.verify_user_mfa("alice", totp.now())) is True
    assert asyncio.run(mfa_service.MFAService.verify_user_mfa("alice", "000000")) is False

    assert asyncio.run(mfa_service.MFAService.verify_user_mfa("alice", codes[0])) is True
    assert codes[0] not in fake_user_svc.last_enable_args[2]
    assert (
        asyncio.run(mfa_service.MFAService.verify_user_mfa("alice", "ABCDEF-ABCDEF-ABCDEF"))
        is False
    )


def test_verify_user_mfa_not_enabled_or_missing(fake_user_svc):
    assert asyncio.run(mfa_service.MFAService.verify_user_mfa("nobody", "123456")) is False
    fake_user_svc.users["bob"] = _make_user(mfa_enabled=False)
    assert asyncio.run(mfa_service.MFAService.verify_user_mfa("bob", "123456")) is False


def test_is_mfa_enabled(fake_user_svc):
    assert asyncio.run(mfa_service.MFAService.is_mfa_enabled("nobody")) is False
    fake_user_svc.users["carol"] = _make_user(mfa_enabled=True)
    assert asyncio.run(mfa_service.MFAService.is_mfa_enabled("carol")) is True


def test_get_mfa_status(fake_user_svc):
    assert asyncio.run(mfa_service.MFAService.get_mfa_status("nobody")) == {"enabled": False}
    fake_user_svc.users["dave"] = _make_user(
        mfa_enabled=True,
        mfa_secret="secret",
        recovery_codes=json.dumps(["A"]),
    )
    status = asyncio.run(mfa_service.MFAService.get_mfa_status("dave"))
    assert status == {
        "enabled": True,
        "has_secret": True,
        "has_recovery_codes": True,
    }


# ---------------------------------------------------------------------------
# core.otel_exporter
# ---------------------------------------------------------------------------
class FakeObservable:
    def __init__(self):
        self.observations = []

    def observe(self, value, attrs=None):
        self.observations.append((value, attrs))


class FakeMeter:
    def __init__(self):
        self.gauges = []

    def create_observable_gauge(self, name, callbacks, description="", unit=""):
        self.gauges.append((name, description, unit))
        gauge = FakeObservable()
        for cb in callbacks:
            cb(gauge)
        return gauge


class FakeSpan:
    def __init__(self):
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *exc):
        self.exited = True
        return False


class FakeTracer:
    def start_as_current_span(self, name):
        return FakeSpan()


class FakeExporter:
    def __init__(self, endpoint=None, timeout=None, insecure=None):
        self.endpoint = endpoint
        self.timeout = timeout
        self.insecure = insecure


class FakeMetricReader:
    def __init__(self, exporter, export_interval_millis=None):
        self.exporter = exporter
        self.export_interval_millis = export_interval_millis


class FakeMeterProvider:
    def __init__(self, metric_readers=None):
        self.metric_readers = metric_readers or []

    def shutdown(self):
        return True


class FakeSpanExporter:
    def __init__(self, endpoint=None, timeout=None, insecure=None):
        self.endpoint = endpoint
        self.timeout = timeout
        self.insecure = insecure


class FakeSpanProcessor:
    def __init__(self, exporter):
        self.exporter = exporter


class FakeTracerProvider:
    def __init__(self):
        self.processors = []

    def add_span_processor(self, processor):
        self.processors.append(processor)

    def shutdown(self):
        return True


@pytest.fixture(autouse=True)
def reset_otel_exporters(monkeypatch):
    otel._meter_provider = None
    otel._meter = None
    otel._tracer_provider = None
    otel._tracer = None

    monkeypatch.setattr(otel.metrics, "set_meter_provider", lambda p: None)
    monkeypatch.setattr(otel.metrics, "get_meter", lambda name: FakeMeter())
    monkeypatch.setattr(otel.trace, "set_tracer_provider", lambda p: None)
    monkeypatch.setattr(otel.trace, "get_tracer", lambda name: FakeTracer())

    monkeypatch.setattr(otel, "OTLPMetricExporter", FakeExporter)
    monkeypatch.setattr(otel, "PeriodicExportingMetricReader", FakeMetricReader)
    monkeypatch.setattr(otel, "MeterProvider", FakeMeterProvider)
    monkeypatch.setattr(otel, "OTLPSpanExporter", FakeSpanExporter)
    monkeypatch.setattr(otel, "BatchSpanProcessor", FakeSpanProcessor)
    monkeypatch.setattr(otel, "TracerProvider", FakeTracerProvider)


def test_create_meter_provider_singleton():
    p1 = otel._create_meter_provider()
    p2 = otel._create_meter_provider()
    assert p1 is p2


def test_create_tracer_provider_singleton():
    p1 = otel._create_tracer_provider()
    p2 = otel._create_tracer_provider()
    assert p1 is p2


def test_init_otel_initializes_both():
    otel.init_otel()
    assert otel._meter is not None
    assert otel._tracer is not None


def test_export_snapshot_empty():
    assert otel.export_snapshot({}) is None
    assert otel.export_snapshot(None) is None


def test_export_snapshot_without_initialization(caplog):
    snapshot = {
        "cpu": {"usage_percent": 12.0, "per_core": [5.0, 6.0]},
        "memory": {
            "total_gb": 16.0,
            "used_gb": 8.0,
            "swap_total_gb": 2.0,
            "swap_used_gb": 0.5,
        },
        "disk": [{"total_gb": 100.0, "used_gb": 40.0}],
        "network": {"recv_speed_mb": 1.0, "sent_speed_mb": 0.5},
        "processes": [
            {
                "pid": 1,
                "name": "python",
                "username": "root",
                "cpu_percent": 2.5,
                "memory_percent": 3.0,
            }
        ],
        "system": {"uptime_seconds": 3600.0},
    }
    with caplog.at_level(logging.WARNING):
        otel.export_snapshot(snapshot)
    assert "not initialized" in caplog.text


def test_export_snapshot_full_success():
    otel.init_otel()
    snapshot = {
        "cpu": {"usage_percent": 12.0, "per_core": [5.0, 6.0]},
        "memory": {
            "total_gb": 16.0,
            "used_gb": 8.0,
            "swap_total_gb": 2.0,
            "swap_used_gb": 0.5,
        },
        "disk": [
            {"total_gb": 100.0, "used_gb": 40.0},
            {"total_gb": 50.0, "used_gb": 10.0},
        ],
        "network": {"recv_speed_mb": 1.0, "sent_speed_mb": 0.5},
        "processes": [
            {
                "pid": 1,
                "name": "python",
                "username": "root",
                "cpu_percent": 2.5,
                "memory_percent": 3.0,
            }
        ],
        "system": {"uptime_seconds": 3600.0},
    }
    otel.export_snapshot(snapshot)
    gauge_names = [g[0] for g in otel._meter.gauges]
    assert "cpu.usage_percent" in gauge_names
    assert "memory.used_gb" in gauge_names
    assert "process.cpu_percent" in gauge_names
    assert "system.uptime_seconds" in gauge_names


def test_shutdown_providers():
    meter = MagicMock()
    tracer = types.SimpleNamespace()
    otel._meter_provider = meter
    otel._tracer_provider = tracer
    otel.shutdown()
    meter.shutdown.assert_called_once()


def test_shutdown_exception_handled(monkeypatch):
    bad_meter = MagicMock()
    bad_meter.shutdown.side_effect = RuntimeError("boom")
    monkeypatch.setattr(otel, "_meter_provider", bad_meter)
    monkeypatch.setattr(otel, "_tracer_provider", None)
    otel.shutdown()
    bad_meter.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# core.heartbeat
# ---------------------------------------------------------------------------
class FakeGauge:
    def __init__(self):
        self.sets = []

    def labels(self, *args, **kwargs):
        return self

    def set(self, value):
        self.sets.append(value)


class BrokenGauge:
    def labels(self, *args, **kwargs):
        raise RuntimeError("gauge broken")


def test_heartbeat_start_stop(monkeypatch):
    monkeypatch.setattr(heartbeat, "_heartbeat_gauge", FakeGauge())
    monkeypatch.setattr(heartbeat, "INTERVAL", 0.01)

    async def _run():
        await heartbeat.heartbeat.start()
        assert heartbeat.heartbeat._task is not None
        await asyncio.sleep(0.05)
        await heartbeat.heartbeat.stop()
        assert heartbeat.heartbeat._task is None
        assert heartbeat.heartbeat._stopped.is_set()

    asyncio.run(_run())
    assert 1 in heartbeat._heartbeat_gauge.sets


def test_heartbeat_run_exception_logged(monkeypatch):
    monkeypatch.setattr(heartbeat, "_heartbeat_gauge", BrokenGauge())
    monkeypatch.setattr(heartbeat, "INTERVAL", 0.01)

    async def _run():
        hb = heartbeat._HeartBeat()
        hb._stopped.clear()
        task = asyncio.create_task(hb._run())
        await asyncio.sleep(0.05)
        hb._stopped.set()
        await task

    asyncio.run(_run())


def test_heartbeat_stop_without_task():
    async def _run():
        await heartbeat._HeartBeat().stop()

    asyncio.run(_run())


def test_heartbeat_dummy_gauge_fallback(monkeypatch):
    class BrokenGaugeForImport:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("prometheus unavailable")

    monkeypatch.setattr("prometheus_client.Gauge", BrokenGaugeForImport)
    importlib.reload(heartbeat)
    assert heartbeat._heartbeat_gauge is not None
    heartbeat._heartbeat_gauge.labels(service="test").set(1)


# ---------------------------------------------------------------------------
# core.slo_metrics_client
# ---------------------------------------------------------------------------
def test_to_naive():
    aware = datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc)
    naive = smc._to_naive(aware)
    assert naive.tzinfo is None
    assert naive == datetime(2024, 6, 15, 10, 30)
    assert smc._to_naive(naive) is naive


def test_escape_label():
    assert smc._escape_label('a\\b"c') == 'a\\\\b\\"c'
    assert smc._escape_label("plain") == "plain"


def test_parse_local_timestamp():
    now_aware = datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc)
    assert smc._parse_local_timestamp(now_aware) == datetime(2024, 6, 15, 10, 30)
    t = smc._parse_local_timestamp("12:34:56")
    assert t == datetime.combine(date.today(), time(12, 34, 56))
    assert smc._parse_local_timestamp("2024-06-15T08:00:00") == datetime(2024, 6, 15, 8, 0)
    assert smc._parse_local_timestamp("2024-06-15 08:00:00") == datetime(2024, 6, 15, 8, 0)
    assert smc._parse_local_timestamp("") is None
    assert smc._parse_local_timestamp("not-a-time") is None
    assert smc._parse_local_timestamp(123) is None


def test_local_metrics_history_adapter(monkeypatch):
    class FakeHistory:
        def to_dict(self):
            return {
                "cpu": [10.0, 20.0, "bad", 30.0],
                "timestamps": ["08:00:00", "09:00:00", "not-a-time", "10:00:00"],
            }

    adapter = smc.LocalMetricsHistoryAdapter(FakeHistory())
    start = datetime.combine(date.today(), time(7, 0))
    end = datetime.combine(date.today(), time(11, 0))
    points = adapter.query_time_series("cpu", "global", start, end)
    assert len(points) == 3
    assert all(isinstance(p, smc.MetricPoint) for p in points)
    assert points[0].value == 10.0
    assert points[1].value == 20.0
    assert points[2].value == 30.0

    class MismatchHistory:
        def to_dict(self):
            return {"cpu": [10.0], "timestamps": []}

    adapter2 = smc.LocalMetricsHistoryAdapter(MismatchHistory())
    assert adapter2.query_time_series("cpu", "global", start, end) == []

    class EmptyHistory:
        def to_dict(self):
            return {}

    adapter3 = smc.LocalMetricsHistoryAdapter(EmptyHistory())
    assert adapter3.query_time_series("cpu", "global", start, end) == []


class FakeResponse:
    def __init__(self, data, raise_exc=None):
        self._data = data
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._data


def test_victoria_metrics_client(monkeypatch):
    hits = []

    def fake_get(url, params=None, timeout=None):
        hits.append((url, params, timeout))
        if "fail" in str(params):
            raise ConnectionError("network down")
        return FakeResponse(
            {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {"service": "web"},
                            "values": [
                                [1704067200, "12.5"],
                                [1704067260, "bad"],
                                [1704067320, "7.0"],
                            ],
                        },
                        {
                            "metric": {"service": "web"},
                            "value": [1704067380, "9.0"],
                        },
                    ]
                },
            }
        )

    monkeypatch.setattr("requests.get", fake_get)

    client = smc.VictoriaMetricsClient(base_url="http://vm-test/", timeout=15, step=120)
    assert client.base_url == "http://vm-test"
    assert client.timeout == 15
    assert client.step == 120

    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    points = client.query_time_series("cpu", 'web"svc', start, end)
    assert len(points) == 3
    assert all(isinstance(p, smc.MetricPoint) for p in points)
    assert hits[0][1]["query"] == 'cpu{service="web\\"svc"}'

    # non-success response
    def fake_get_error(url, params=None, timeout=None):
        return FakeResponse({"status": "error"})

    monkeypatch.setattr("requests.get", fake_get_error)
    assert client.query_time_series("cpu", "web", start, end) == []

    # request exception
    def fake_get_exception(url, params=None, timeout=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("requests.get", fake_get_exception)
    assert client.query_time_series("cpu", "web", start, end) == []


def test_victoria_metrics_client_defaults():
    client = smc.VictoriaMetricsClient()
    assert client.base_url == "http://localhost:8428"
    assert client.timeout == 30
    assert client.step == 60


def test_parse_matrix():
    matrix = [
        {"values": [[1704067200, "1.0"], [1704067260, "2.0"]]},
        {"value": [1704067320, "3.0"]},
        {"values": [["bad", "1.0"]]},
        {"values": [1704067380]},
        {"values": None},
    ]
    points = smc._parse_matrix(matrix)
    assert len(points) == 3
    assert points[0].value == 1.0
    assert points[1].value == 2.0
    assert points[2].value == 3.0


def test_metric_point_dataclass():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    p = smc.MetricPoint(timestamp=ts, value=1.0)
    assert p.timestamp == ts
    assert p.value == 1.0


# ---------------------------------------------------------------------------
# core.slo_incident_store
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_incident_store():
    sis._incidents.clear()
    yield
    sis._incidents.clear()


def test_add_and_list_incidents():
    i1 = sis.add_incident(
        "svc1", datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 1, 0), "critical"
    )
    i2 = sis.add_incident("svc2", datetime(2024, 1, 1, 2, 0), datetime(2024, 1, 1, 3, 0), "warning")
    assert len(sis.list_incidents()) == 2
    assert sis.list_incidents("svc1") == [i1]
    assert sis.list_incidents("missing") == []


def test_to_naive_utc_and_overlapping_interval():
    aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    naive = sis._to_naive_utc(aware)
    assert naive.tzinfo is None
    assert naive == datetime(2024, 1, 1, 12, 0)
    assert sis._to_naive_utc(naive) is naive

    inc = sis.Incident("svc1", datetime(2024, 1, 1, 9, 0), datetime(2024, 1, 1, 11, 0), "critical")
    assert (
        sis._overlapping_interval(inc, datetime(2024, 1, 1, 11, 0), datetime(2024, 1, 1, 13, 0))
        is None
    )
    assert (
        sis._overlapping_interval(inc, datetime(2024, 1, 1, 7, 0), datetime(2024, 1, 1, 9, 0))
        is None
    )
    overlap = sis._overlapping_interval(
        inc, datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 12, 0)
    )
    assert overlap == (datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 11, 0))


def test_compute_downtime_empty_or_invalid_window():
    start = datetime(2024, 1, 1, 0, 0)
    assert sis.compute_downtime("svc1", start, start) == 0.0
    assert sis.compute_downtime("svc1", start, start + timedelta(hours=1)) == 0.0


def test_compute_downtime_single_and_merged():
    start = datetime(2024, 1, 1, 0, 0)
    sis.add_incident("svc1", start + timedelta(hours=1), start + timedelta(hours=2), "critical")
    sis.add_incident(
        "svc1", start + timedelta(hours=1, minutes=30), start + timedelta(hours=3), "critical"
    )
    sis.add_incident("svc2", start + timedelta(hours=1), start + timedelta(hours=2), "critical")
    assert sis.compute_downtime("svc1", start, start + timedelta(hours=5)) == 7200.0
    assert sis.compute_downtime("svc2", start, start + timedelta(hours=5)) == 3600.0
    assert (
        sis.compute_downtime("svc1", start + timedelta(hours=4), start + timedelta(hours=5)) == 0.0
    )
