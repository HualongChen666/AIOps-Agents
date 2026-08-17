# -*- coding: utf-8 -*-
"""Functional tests for core.performance_report_generator, core.k8s_collector
and the L4 storage adapters (tempo, loki, victoriametrics).
"""

import asyncio  # noqa: F401  # Imported for test setup
import concurrent.futures
import sys  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401  # Imported for test setup
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _ensure_kubernetes_mock():
    """Stub the kubernetes package so core.k8s_collector can be imported."""
    if "kubernetes" in sys.modules:
        return
    k8s_mod = types.ModuleType("kubernetes")
    client_mod = types.ModuleType("kubernetes.client")
    config_mod = types.ModuleType("kubernetes.config")

    class ApiException(Exception):
        pass

    client_mod.ApiException = ApiException
    client_mod.CoreV1Api = lambda *a, **k: None

    def load_kube_config(*args, **kwargs):
        return None

    config_mod.load_kube_config = load_kube_config
    k8s_mod.client = client_mod
    k8s_mod.config = config_mod
    sys.modules["kubernetes"] = k8s_mod
    sys.modules["kubernetes.client"] = client_mod
    sys.modules["kubernetes.config"] = config_mod


_ensure_kubernetes_mock()

import core.db_engine as db_engine
import core.k8s_collector as k8s_collector
import core.performance_report_generator as perf_report
import core.storage.l4.loki as loki_mod
import core.storage.l4.tempo as tempo_mod
import core.storage.l4.victoriametrics as vm_mod
from core.database import Base

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


def _make_pod(name, namespace, node, phase, container_statuses=None):
    if container_statuses is None:
        container_statuses = [types.SimpleNamespace(restart_count=0)]
    return types.SimpleNamespace(
        metadata=types.SimpleNamespace(name=name, namespace=namespace),
        spec=types.SimpleNamespace(node_name=node),
        status=types.SimpleNamespace(
            phase=phase,
            container_statuses=container_statuses,
        ),
    )


def _fake_k8s_api(pods, raise_api=False, raise_other=False):
    class FakeCoreV1Api:
        def list_pod_for_all_namespaces(self, **kwargs):
            if raise_api:
                raise k8s_collector.client.ApiException("api boom")
            if raise_other:
                raise RuntimeError("other boom")
            return types.SimpleNamespace(items=pods)

    return FakeCoreV1Api


def _make_fake_httpx(response_handler):
    fake = types.ModuleType("httpx")

    class FakeAsyncClient:
        def __init__(self, base_url=None, timeout=None, **kwargs):
            self.base_url = base_url
            self.timeout = timeout
            self._handler = response_handler

        async def get(self, url, *, params=None, headers=None, **kwargs):
            return await self._handler("get", url, params, None, headers)

        async def post(self, url, *, content=None, json=None, headers=None, **kwargs):
            return await self._handler("post", url, None, content or json, headers)

        async def aclose(self):
            pass

    fake.AsyncClient = FakeAsyncClient
    fake.FakeResponse = FakeResponse
    return fake


async def _init_memory_db():
    """Set core.db_engine to a fresh in-memory SQLite async engine."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)
    db_engine._ENGINE = engine
    db_engine._AsyncSessionLocal = AsyncSession
    return AsyncSession


# ---------------------------------------------------------------------------
# core.performance_report_generator
# ---------------------------------------------------------------------------
def test_perf_report_generator_daily_and_trend():
    async def _run():
        AsyncSession = await _init_memory_db()
        session = AsyncSession()
        now = datetime.now()

        metric1 = perf_report.PerformanceMetric(
            test_id="t1",
            test_name="test-1",
            test_type="api",
            component="checkout",
            operation="POST",
            mean_time_ms=50.0,
            min_time_ms=20.0,
            max_time_ms=120.0,
            p95_time_ms=100.0,
            p99_time_ms=150.0,
            throughput_ops=10.0,
            error_count=2,
            total_requests=100,
            environment="dev",
            timestamp=now,
        )
        metric2 = perf_report.PerformanceMetric(
            test_id="t2",
            test_name="test-2",
            test_type="api",
            component="checkout",
            operation="POST",
            mean_time_ms=60.0,
            min_time_ms=25.0,
            max_time_ms=130.0,
            p95_time_ms=120.0,
            p99_time_ms=None,
            throughput_ops=15.0,
            error_count=None,
            total_requests=80,
            environment="dev",
            timestamp=now + timedelta(minutes=1),
        )
        regression = perf_report.PerformanceRegression(
            regression_id="r1",
            component="checkout",
            operation="POST",
            baseline_value=80.0,
            current_value=100.0,
            deviation=0.25,
            severity="warning",
            detected_at=now,
            environment="dev",
        )
        session.add_all([metric1, metric2, regression])
        await session.commit()
        await session.close()

        async with perf_report.PerformanceReportGenerator() as gen:
            daily = await gen.generate_daily_report("dev", now)

        assert daily["report_type"] == "daily"
        assert daily["summary"]["total_tests"] == 2
        assert daily["summary"]["total_regressions"] == 1
        assert "checkout" in daily["component_stats"]
        assert daily["component_stats"]["checkout"]["count"] == 2
        assert daily["component_stats"]["checkout"]["avg_p95"] == 110.0

        trend = await perf_report.PerformanceReportGenerator().generate_trend_analysis(
            "checkout", "p95_time_ms", days=30, environment="dev"
        )
        assert trend["trend_direction"] == "up"
        assert trend["data_points"] == 2

        wrapped = await perf_report.generate_performance_report("daily", "dev")
        assert wrapped["report_type"] == "daily"

    asyncio.run(_run())


def test_perf_report_generator_weekly_and_monthly():
    async def _run():
        AsyncSession = await _init_memory_db()
        session = AsyncSession()
        now = datetime.now()
        d1 = now - timedelta(days=2)
        d2 = now - timedelta(days=1)

        session.add_all(
            [
                perf_report.PerformanceMetric(
                    test_id="w1",
                    test_name="w1",
                    test_type="api",
                    component="search",
                    operation="GET",
                    mean_time_ms=20.0,
                    min_time_ms=10.0,
                    max_time_ms=30.0,
                    p95_time_ms=25.0,
                    total_requests=10,
                    environment="dev",
                    timestamp=d1,
                ),
                perf_report.PerformanceMetric(
                    test_id="w2",
                    test_name="w2",
                    test_type="api",
                    component="search",
                    operation="GET",
                    mean_time_ms=22.0,
                    min_time_ms=11.0,
                    max_time_ms=33.0,
                    p95_time_ms=28.0,
                    total_requests=10,
                    environment="dev",
                    timestamp=d2,
                ),
            ]
        )
        await session.commit()
        await session.close()

        start_week = now - timedelta(days=2)
        weekly = await perf_report.PerformanceReportGenerator().generate_weekly_report(
            "dev", start_week
        )
        assert weekly["report_type"] == "weekly"
        assert weekly["summary"]["total_tests"] == 2

        # cover default year/month branches
        monthly = await perf_report.PerformanceReportGenerator().generate_monthly_report("dev")
        assert monthly["report_type"] == "monthly"
        assert monthly["summary"]["total_tests"] == 2

        wrapped_weekly = await perf_report.generate_performance_report("weekly", "dev")
        assert wrapped_weekly["report_type"] == "weekly"
        wrapped_monthly = await perf_report.generate_performance_report("monthly", "dev")
        assert wrapped_monthly["report_type"] == "monthly"

    asyncio.run(_run())


def test_perf_report_generator_invalid_and_exception(monkeypatch):
    async def _run():
        _ = await _init_memory_db()

        out = await perf_report.generate_performance_report("yearly", "dev")
        assert out == {}

        class BadSession:
            async def __aenter__(self):
                raise RuntimeError("db down")

            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr(db_engine, "_AsyncSessionLocal", BadSession)
        generator = perf_report.PerformanceReportGenerator()
        assert await generator.generate_daily_report("dev") == {}
        assert await generator.generate_weekly_report("dev") == {}
        assert await generator.generate_monthly_report("dev") == {}
        assert await generator.generate_trend_analysis("checkout") == {}

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# core.k8s_collector
# ---------------------------------------------------------------------------
def test_k8s_load_api_branches(monkeypatch):
    calls = []

    def fake_load(*args, **kwargs):
        calls.append((args, kwargs))
        if kwargs.get("config_file") == "/boom":
            raise RuntimeError("boom")

    monkeypatch.setattr(k8s_collector.config, "load_kube_config", fake_load)
    monkeypatch.setattr(k8s_collector.client, "CoreV1Api", lambda *a, **k: None)

    k8s_collector._load_api({"host": "h", "context": "ctx"})
    k8s_collector._load_api({"host": "h", "kubeconfig": "/tmp/k"})
    k8s_collector._load_api({"host": "h"})
    k8s_collector._load_api({"host": "h", "read_only": False})

    assert any(c[1].get("context") == "ctx" for c in calls)
    assert any(c[1].get("config_file") == "/tmp/k" for c in calls)
    assert any(not c[1] and not c[0] for c in calls)

    with pytest.raises(ConnectionError):
        k8s_collector._load_api({"host": "h", "kubeconfig": "/boom"})


def test_k8s_collect_pods_success_and_truncation(monkeypatch):
    k8s_collector._host_status.clear()
    k8s_collector._collect_history.clear()

    pod1 = _make_pod(
        "pod-1", "default", "node-1", "Running", [types.SimpleNamespace(restart_count=2)]
    )
    pod2 = _make_pod(
        "pod-2", "kube-system", "node-2", "Pending", [types.SimpleNamespace(restart_count=0)]
    )
    pod3 = _make_pod("pod-3", "default", "node-1", "Running", None)

    fake_api = _fake_k8s_api([pod1, pod2, pod3])
    monkeypatch.setattr(k8s_collector.client, "CoreV1Api", fake_api)
    monkeypatch.setattr(k8s_collector.config, "load_kube_config", lambda *a, **k: None)

    api = k8s_collector.client.CoreV1Api()
    pods = k8s_collector._collect_pods(api)
    assert len(pods) == 3
    assert pods[0]["restart_count"] == 2
    assert pods[2]["restart_count"] == 0

    # truncation branch
    pods2 = k8s_collector._collect_pods(api, max_pods=2)
    assert any(p.get("_truncated") for p in pods2)


def test_k8s_collect_pods_api_and_generic_exceptions(monkeypatch):
    monkeypatch.setattr(k8s_collector.config, "load_kube_config", lambda *a, **k: None)

    api1 = _fake_k8s_api([], raise_api=True)()
    assert k8s_collector._collect_pods(api1) == []

    api2 = _fake_k8s_api([], raise_other=True)()
    assert k8s_collector._collect_pods(api2) == []


def test_k8s_cooldown_and_failure(monkeypatch):
    k8s_collector._host_status.clear()
    k8s_collector._collect_history.clear()

    monkeypatch.setattr(k8s_collector, "K8S_HOST_MAX_FAILURES", 1)
    monkeypatch.setattr(k8s_collector, "K8S_HOST_COOLDOWN_SEC", 10)

    class BoomCoreV1Api:
        def __init__(self, *a, **k):
            raise RuntimeError("fail")

    monkeypatch.setattr(k8s_collector.client, "CoreV1Api", BoomCoreV1Api)
    monkeypatch.setattr(k8s_collector.config, "load_kube_config", lambda *a, **k: None)

    host = "cluster-fail"
    out1 = k8s_collector.collect_k8s({"host": host, "kubeconfig": "/tmp/k"})
    assert out1["_data_completeness"] == "failed"
    assert k8s_collector._host_status[host]["failures"] == 1

    out2 = k8s_collector.collect_k8s({"host": host})
    assert out2["_data_completeness"] == "cooldown"
    assert out2.get("_cooldown") is True

    # reset cooldown and test success -> _record_success
    k8s_collector._host_status[host]["cooldown_until"] = 0.0
    monkeypatch.setattr(k8s_collector.client, "CoreV1Api", _fake_k8s_api([]))
    out3 = k8s_collector.collect_k8s({"host": host})
    assert out3["_data_completeness"] == "complete"
    assert k8s_collector._host_status[host]["failures"] == 0

    history = k8s_collector.get_k8s_collect_history(limit=5)
    assert len(history) >= 1


def test_k8s_collect_all(monkeypatch):
    k8s_collector._host_status.clear()
    k8s_collector._collect_history.clear()

    class FakeCoreV1Api:
        def __init__(self, *a, **k):
            pass

        def list_pod_for_all_namespaces(self, **kwargs):
            return types.SimpleNamespace(items=[_make_pod("pod", "default", "node", "Running")])

    monkeypatch.setattr(k8s_collector.client, "CoreV1Api", FakeCoreV1Api)
    monkeypatch.setattr(k8s_collector.config, "load_kube_config", lambda *a, **k: None)
    monkeypatch.setattr(
        k8s_collector,
        "K8S_HOSTS",
        [{"host": "ok-1"}, {"host": "ok-2"}],
    )

    class FakeFuture:
        def __init__(self, exc=None, timeout=False):
            self._exc = exc
            self._timeout = timeout

        def result(self, timeout=None):
            if self._timeout:
                raise concurrent.futures.TimeoutError()
            if self._exc:
                raise self._exc
            return {"host": "ok", "_data_completeness": "complete"}

    class FakeExecutor:
        def __init__(self, max_workers=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def submit(self, fn, *args, **kwargs):
            host = args[0].get("host", "unknown")
            if host == "slow":
                return FakeFuture(timeout=True)
            if host == "bad":
                return FakeFuture(exc=RuntimeError("boom"))
            return FakeFuture()

    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", FakeExecutor)

    all_hosts = [
        {"host": "ok-1"},
        {"host": "slow"},
        {"host": "bad"},
    ]
    monkeypatch.setattr(k8s_collector, "K8S_HOSTS", all_hosts)

    results = k8s_collector.collect_all_k8s(max_workers=1, timeout=1.0)
    assert len(results) == 3
    assert any(r.get("_timeout") for r in results)
    assert any(r.get("_error") for r in results)


# ---------------------------------------------------------------------------
# core.storage.l4.tempo
# ---------------------------------------------------------------------------
async def _tempo_handler(method, url, params, data, headers):
    if method == "get":
        if url.startswith("/api/traces/"):
            if "missing" in url:
                return FakeResponse(404)
            if "error" in url:
                return FakeResponse(503, text="tempo down")
            return FakeResponse(200, {"traceID": "abc"})
        if url == "/api/search":
            return FakeResponse(200, {"traces": [{"traceID": "1"}]})
        if url == "/api/services":
            return FakeResponse(200, {"data": ["checkout"]})
        if url == "/api/services/checkout/operations":
            return FakeResponse(200, {"data": ["place_order"]})
    if method == "post":
        return FakeResponse(204)
    return FakeResponse(500, text="unknown")


def test_tempo_storage_full_flow(monkeypatch):
    async def _run():
        fake_httpx = _make_fake_httpx(_tempo_handler)
        monkeypatch.setattr(tempo_mod, "httpx", fake_httpx)

        storage = tempo_mod.TempoStorage({"base_url": "http://tempo:3200"})
        assert storage.initialize() is True

        not_ready = tempo_mod.TempoStorage()
        assert await not_ready.store("k", "v") is False
        assert await not_ready.retrieve("k") is None
        assert await not_ready.query({"query": "{}"}) == []
        assert await not_ready.get_services() == []

        storage._is_initialized = True
        storage.read_only = True
        assert await storage.store("k", "v") is False
        storage.read_only = False
        assert await storage.store("k", "v") is False

        assert await storage.retrieve("abc") == {"traceID": "abc"}
        assert await storage.retrieve("missing") is None
        assert await storage.retrieve("error") is None

        assert await storage.query({}) == []
        assert await storage.query({"query": "{"}) == []  # invalid
        found = await storage.query({"query": "{}", "start": 1, "end": 2, "limit": 50000})
        assert isinstance(found, list)

        traces = await storage.search_traces(
            service_name="checkout",
            operation="place_order",
            tags={"error": "true"},
            min_duration=1.0,
            max_duration=5.0,
            limit=5,
        )
        assert isinstance(traces, list)

        assert await storage.get_services() == ["checkout"]
        assert await storage.get_operations("checkout") == ["place_order"]
        assert await storage.delete("x") is False

        storage.close()

    asyncio.run(_run())


def test_tempo_initialize_failure(monkeypatch):
    class BoomClient:
        def __init__(self, *a, **k):
            raise RuntimeError("init boom")

    fake = types.ModuleType("httpx")
    fake.AsyncClient = BoomClient
    monkeypatch.setattr(tempo_mod, "httpx", fake)

    storage = tempo_mod.TempoStorage()
    assert storage.initialize() is False


# ---------------------------------------------------------------------------
# core.storage.l4.loki
# ---------------------------------------------------------------------------
async def _loki_handler(method, url, params, data, headers):
    if method == "get":
        if url == "/loki/api/v1/query":
            if params and params.get("query") == '{stream="{bad"}':
                return FakeResponse(200, {"status": "success", "data": {"result": []}})
            return FakeResponse(
                200,
                {
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "stream": {"app": "web"},
                                "values": [["1234567890000000000", "log line"]],
                            }
                        ]
                    },
                },
            )
        if url == "/loki/api/v1/query_range":
            return FakeResponse(
                200,
                {
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "stream": {"app": "web"},
                                "values": [
                                    ["1234567890000000000", "range log"],
                                    ["1234567891000000000", "range log 2"],
                                ],
                            }
                        ]
                    },
                },
            )
        if url == "/loki/api/v1/labels":
            return FakeResponse(200, {"status": "success", "data": ["app", "host"]})
    if method == "post":
        if url == "/loki/api/v1/push":
            if isinstance(data, dict) and data.get("streams"):
                return FakeResponse(204)
    return FakeResponse(500, text="loki error")


def test_loki_storage_full_flow(monkeypatch):
    async def _run():
        fake_httpx = _make_fake_httpx(_loki_handler)
        monkeypatch.setattr(loki_mod, "httpx", fake_httpx)

        storage = loki_mod.LokiStorage({"base_url": "http://loki:3100", "read_only": False})
        assert storage.initialize() is True

        not_ready = loki_mod.LokiStorage()
        assert await not_ready.store("k", "v") is False
        assert await not_ready.retrieve("k") is None
        assert await not_ready.get_labels() == []
        not_ready.close()

        assert await storage.store("app", "hello", metadata={"labels": {"app": "web"}}) is True

        async def fail_post(method, url, params, data, headers):
            if method == "post":
                return FakeResponse(500, text="push failed")
            return _loki_handler(method, url, params, data, headers)

        storage._client._handler = fail_post
        assert await storage.store("app", "hello") is False
        storage._client._handler = _loki_handler

        # store with no metadata and with an exception
        assert await storage.store("no-md", "hello") is True

        async def boom_post(method, url, params, data, headers):
            if method == "post" and url == "/loki/api/v1/push":
                raise RuntimeError("network")
            return _loki_handler(method, url, params, data, headers)

        storage._client._handler = boom_post
        assert await storage.store("boom", "hello") is False
        storage._client._handler = _loki_handler

        # read_only store path
        ro = loki_mod.LokiStorage({"base_url": "http://loki:3100", "read_only": True})
        ro.initialize()
        assert await ro.store("x", "y") is False

        assert await storage.retrieve("app") is not None
        assert await storage.retrieve("{bad") is None

        assert await storage.query({}) == []
        assert await storage.query({"query": "{"}) == []

        instant = await storage.query({"query": '{stream="app"}'})
        assert instant

        ranged = await storage.query(
            {
                "query": '{stream="app"}',
                "start": 1,
                "end": 2,
            }
        )
        assert ranged

        # query exception and not-initialized get_labels exception
        storage._query_cache.clear()

        async def boom_query(method, url, params, data, headers):
            raise RuntimeError("query boom")

        storage._client._handler = boom_query
        assert await storage.retrieve("app") is None
        assert await storage.query({"query": '{stream="app"}'}) == []
        storage._client._handler = _loki_handler

        assert await storage.query_range(
            '{stream="app"}',
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            limit=100,
        )

        # invalid query_range
        assert (
            await storage.query_range(
                "{",
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
            )
            == []
        )

        assert await storage.get_labels() == ["app", "host"]
        assert await storage.get_labels(stream="app") == ["app", "host"]

        # get_labels exception
        storage._query_cache.clear()
        storage._client._handler = boom_query
        assert await storage.get_labels() == []

        assert await storage.delete("x") is False

        storage.close()

    asyncio.run(_run())


def test_loki_initialize_failure(monkeypatch):
    class BoomClient:
        def __init__(self, *a, **k):
            raise RuntimeError("init boom")

    fake = types.ModuleType("httpx")
    fake.AsyncClient = BoomClient
    monkeypatch.setattr(loki_mod, "httpx", fake)

    storage = loki_mod.LokiStorage()
    assert storage.initialize() is False


# ---------------------------------------------------------------------------
# core.storage.l4.victoriametrics
# ---------------------------------------------------------------------------
async def _vm_handler(method, url, params, data, headers):
    if method == "get":
        if url == "/api/v1/query":
            if params and params.get("query") == "up;bad":
                return FakeResponse(200, {"status": "success", "data": {"result": []}})
            return FakeResponse(
                200,
                {
                    "status": "success",
                    "data": {"result": [{"value": [1700000000, "12.5"]}]},
                },
            )
        if url == "/api/v1/query_range":
            return FakeResponse(
                200,
                {
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "metric": {"job": "web"},
                                "values": [[1700000000, "1.0"], [1700000060, "2.0"]],
                            }
                        ]
                    },
                },
            )
    if method == "post":
        if url == "/api/v1/import/prometheus":
            payload = data if isinstance(data, (bytes, str)) else ""
            if isinstance(payload, bytes):
                payload = payload.decode()
            if "cpu_usage" in payload:
                return FakeResponse(204)
    return FakeResponse(500, text="vm error")


def test_victoriametrics_storage_full_flow(monkeypatch):
    async def _run():
        fake_httpx = _make_fake_httpx(_vm_handler)
        monkeypatch.setattr(vm_mod, "httpx", fake_httpx)

        storage = vm_mod.VictoriaMetricsStorage({"base_url": "http://vm:8428", "read_only": False})
        assert storage.initialize() is True

        not_ready = vm_mod.VictoriaMetricsStorage()
        assert await not_ready.store("m", 1.0) is False
        assert await not_ready.retrieve("m") is None
        assert await not_ready.query({"query": "up"}) == []

        storage.read_only = True
        assert await storage.store("m", 1.0) is False
        storage.read_only = False

        assert await storage.store("cpu_usage", 12.5, metadata={"labels": {"job": "web"}}) is True

        async def fail_post(method, url, params, data, headers):
            if method == "post":
                return FakeResponse(500, text="import failed")
            return _vm_handler(method, url, params, data, headers)

        storage._client._handler = fail_post
        assert await storage.store("mem", 8.0) is False
        storage._client._handler = _vm_handler

        assert await storage.retrieve("up") == 12.5
        assert await storage.retrieve("up;bad") is None

        instant = await storage.query({"query": "up", "time": 1700000000})
        assert instant

        start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 8, 0, 0, tzinfo=timezone.utc)
        ranged = await storage.query(
            {
                "query": "cpu_usage",
                "start": start,
                "end": end,
                "step": 1,
            }
        )
        assert ranged

        assert await storage.query_range("cpu_usage", start, end, step=60)
        assert await storage.delete("x") is False

        storage.close()

    asyncio.run(_run())


def test_victoriametrics_initialize_failure(monkeypatch):
    class BoomClient:
        def __init__(self, *a, **k):
            raise RuntimeError("init boom")

    fake = types.ModuleType("httpx")
    fake.AsyncClient = BoomClient
    monkeypatch.setattr(vm_mod, "httpx", fake)

    storage = vm_mod.VictoriaMetricsStorage()
    assert storage.initialize() is False
