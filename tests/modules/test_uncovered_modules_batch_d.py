# -*- coding: utf-8 -*-
"""Batch D module tests - raise coverage for assigned modules above 80%."""

import asyncio
import datetime
import statistics
import sys
import time
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest
import torch

from modules.analyze.anomaly import transformer_service
from modules.analyze.anomaly.data_preprocessing import (
    TimeSeriesPreprocessingPipeline,
)
from modules.analyze.anomaly.transformer_service import (
    TransformerAnomalyDetectorCompat,
    TransformerAnomalyService,
    TransformerModelManager,
    create_router,
    get_model_manager,
    get_service,
    initialize_service,
    shutdown_service,
)
from modules.apm.code_profiler import (
    APMProfiler,
    CallStack,
    CodeProfiler,
    MemoryProfiler,
    PerformanceMetric,
    SQLQueryAnalyzer,
    create_apm_profiler,
)
from modules.execute.saga.participants import (
    APICallParticipant,
    CompensationAction,
    DatabaseParticipant,
    MessageQueueParticipant,
    NotificationParticipant,
    Participant,
    ResourceAllocationParticipant,
    create_compensation_action,
)
from modules.high_availability.multi_region import (
    DataSyncManager,
    MultiRegionManager,
    Region,
    RegionStatus,
    RoutingStrategy,
    create_data_sync_manager,
    create_multi_region_manager,
)
from modules.observability.auto_discovery import (
    AutoDiscoveryEngine,
    DiscoveredResource,
)
from modules.observability.auto_discovery import ResourceType as ADResourceType
from modules.observability.auto_discovery import (
    ServiceRelation,
    create_auto_discovery_engine,
)
from modules.optimization.cache_optimizer import (
    CacheEntry,
    CacheManager,
    CacheOptimizer,
    CacheStatistics,
    CacheStrategy,
    DistributedCacheManager,
    create_cache_manager,
    create_cache_optimizer,
    create_distributed_cache_manager,
)
from modules.optimization.query_optimizer import (
    QueryOptimizer,
    SlowQueryAnalyzer,
    create_query_optimizer,
    create_slow_query_analyzer,
)
from modules.optimization.resource_optimizer import (
    CostAnalyzer,
    OptimizationSuggestion,
    ResourceMetric,
    ResourceMonitor,
    ResourceOptimizer,
)
from modules.optimization.resource_optimizer import ResourceType as ResResourceType
from modules.optimization.resource_optimizer import (
    create_cost_analyzer,
    create_resource_monitor,
    create_resource_optimizer,
)
from modules.optimization.storage_optimizer import (
    DataCompressor,
    DataLifecycleManager,
    DataObject,
    StorageManager,
    StorageOptimizer,
    StorageStatistics,
    StorageType,
    create_data_compressor,
    create_data_lifecycle_manager,
    create_storage_manager,
    create_storage_optimizer,
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _create_model_state_dict():
    """Return a tiny real state dict for mocking torch.load."""
    from modules.analyze.anomaly.transformer_model import create_transformer_model

    m = create_transformer_model(
        input_dim=1,
        d_model=8,
        n_heads=2,
        n_layers=1,
        d_ff=16,
        dropout=0.0,
    )
    return m.state_dict()


# ==============================================================================
# modules/observability/auto_discovery.py
# ==============================================================================
def test_auto_discovery_basic_config_and_topology(tmp_path, monkeypatch):
    engine = create_auto_discovery_engine()
    config_data = {
        "services": [
            {
                "id": "web-service",
                "name": "Web Service",
                "host": "localhost",
                "port": 8080,
                "metadata": {"namespace": "production"},
            },
            {
                "id": "db-service",
                "name": "DB Service",
                "host": "db",
                "port": 5432,
                "metadata": {"namespace": "production"},
            },
        ],
    }
    result = engine.discover(methods=["config"], config_data=config_data)
    assert result["_truncated"] is False
    assert len(result["resources"]) == 2
    assert "topology" in result
    assert not result["critical_flows"]  # no DB/cache yet

    # manually inject a database in the same namespace to exercise topology building
    engine.discovered_resources["db-1"] = DiscoveredResource(
        id="db-1",
        name="DB",
        type=ADResourceType.DATABASE,
        host="db",
        port=5432,
        metadata={"namespace": "production"},
    )
    engine._build_topology()
    assert len(engine.service_relations) == 2
    critical_ids = {f["service_id"] for f in engine._identify_critical_flows()}
    assert "web-service" in critical_ids
    cfg = engine.generate_monitoring_config()
    assert cfg["services"]
    assert cfg["databases"]

    # missing config branch
    empty_engine = create_auto_discovery_engine()
    empty_result = empty_engine.discover(methods=["config"])
    assert empty_result["resources"] == []

    # port inference
    assert engine._infer_resource_type(6379) == ADResourceType.CACHE
    assert engine._infer_resource_type(1234) == ADResourceType.SERVICE

    # truncation path
    small_engine = AutoDiscoveryEngine(max_resources=1)
    small_engine.discover(methods=["config"], config_data=config_data)

    # network discovery with missing nmap uses fallback
    network_engine = create_auto_discovery_engine()
    network_engine.discover(methods=["network"], subnet="10.0.0.0/24")

    # kubernetes / docker import failures
    k8s_engine = create_auto_discovery_engine()
    k8s_engine.discover(methods=["kubernetes"])
    docker_engine = create_auto_discovery_engine()
    docker_engine.discover(methods=["docker"])


def test_auto_discovery_mocked_plugins(monkeypatch):
    # Fake kubernetes
    fake_k8s = types.ModuleType("kubernetes")

    class _FakeCoreV1Api:
        def list_service_for_all_namespaces(self, limit, timeout_seconds):
            svc = types.SimpleNamespace(
                metadata=types.SimpleNamespace(namespace="prod", name="svc1"),
                spec=types.SimpleNamespace(
                    cluster_ip="10.0.0.1",
                    type="ClusterIP",
                    ports=[types.SimpleNamespace(port=80)],
                ),
            )
            return types.SimpleNamespace(items=[svc])

        def list_pod_for_all_namespaces(self, limit, timeout_seconds):
            pod = types.SimpleNamespace(
                metadata=types.SimpleNamespace(namespace="prod", name="pod1"),
                status=types.SimpleNamespace(host_ip="10.0.0.2", phase="Running"),
                spec=types.SimpleNamespace(node_name="node1"),
            )
            return types.SimpleNamespace(items=[pod])

    fake_k8s.config = types.SimpleNamespace(load_kube_config=lambda: None)
    fake_k8s.client = types.SimpleNamespace(CoreV1Api=_FakeCoreV1Api)

    # Fake docker
    fake_docker = types.ModuleType("docker")

    class _FakeContainers:
        def list(self, all=True):
            return [
                types.SimpleNamespace(
                    id="abc1234567890",
                    name="c1",
                    image=types.SimpleNamespace(tags=["img:latest"], id="imgid"),
                    status="running",
                    ports={},
                )
            ]

    class _FakeDockerClient:
        containers = _FakeContainers()

    fake_docker.from_env = lambda: _FakeDockerClient()

    # Fake nmap
    fake_nmap = types.ModuleType("nmap")

    class _FakeProto:
        def __init__(self, ports):
            self._ports = ports

        def keys(self):
            return list(self._ports.keys())

        def __getitem__(self, port):
            return self._ports[port]

    class _FakeHost:
        def __init__(self, proto_data):
            self._data = proto_data

        def all_protocols(self):
            return list(self._data.keys())

        def __getitem__(self, proto):
            return _FakeProto(self._data[proto])

    class _FakePortScanner:
        def __init__(self):
            self._hosts = {}

        def scan(self, subnet, arguments):
            self._hosts = {
                "10.0.0.5": {
                    "tcp": {
                        80: {"state": "open"},
                        3306: {"state": "open"},
                        6379: {"state": "open"},
                    }
                }
            }

        def all_hosts(self):
            return list(self._hosts.keys())

        def __getitem__(self, host):
            return _FakeHost(self._hosts[host])

    fake_nmap.PortScanner = _FakePortScanner

    monkeypatch.setitem(sys.modules, "kubernetes", fake_k8s)
    monkeypatch.setitem(sys.modules, "docker", fake_docker)
    monkeypatch.setitem(sys.modules, "nmap", fake_nmap)

    engine = create_auto_discovery_engine()
    engine.discovery_plugins["bad"] = lambda **kwargs: (_ for _ in ()).throw(ValueError("boom"))

    # discover with default methods (None) covers line 140 and all mocked plugins
    result = engine.discover(read_only=False)
    assert any(r["type"] == "cache" for r in result["resources"])
    cfg = engine.generate_monitoring_config()
    assert cfg["caches"]
    assert cfg["services"]
    assert cfg["databases"]

    # explicit exception-handling path
    result2 = engine.discover(methods=["bad"])
    assert isinstance(result2, dict)


def test_auto_discovery_dataclasses():
    r = DiscoveredResource(
        id="x",
        name="X",
        type=ADResourceType.SERVICE,
        host="h",
        port=80,
    )
    d = r.to_dict()
    assert d["type"] == "service"
    assert d["host"] == "h"

    s = ServiceRelation(source="a", target="b", relation_type="calls")
    assert s.to_dict()["target"] == "b"


# ==============================================================================
# modules/optimization/resource_optimizer.py
# ==============================================================================
def test_resource_optimizer_lifecycle():
    monitor = create_resource_monitor()
    now = datetime.datetime.now()

    # low utilization -> scale_down
    for i in range(20):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResResourceType.CPU,
                usage=20.0,
                capacity=100.0,
                unit="cores",
                timestamp=now,
            )
        )
    # high utilization -> scale_up
    for i in range(20):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResResourceType.MEMORY,
                usage=90.0,
                capacity=100.0,
                unit="GB",
                timestamp=now,
            )
        )
    # volatile -> auto_scaling (large swings)
    for i in range(20):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResResourceType.STORAGE,
                usage=10.0 if i % 2 == 0 else 90.0,
                capacity=100.0,
                unit="GB",
                timestamp=now,
            )
        )

    optimizer = create_resource_optimizer(monitor)
    suggestions = optimizer.analyze_optimization_opportunities()
    assert any(s.suggestion_type == "scale_down" for s in suggestions)
    assert any(s.suggestion_type == "scale_up" for s in suggestions)
    assert any(s.suggestion_type == "auto_scaling" for s in suggestions)

    costs = optimizer.estimate_monthly_cost()
    assert "total" in costs

    for s in suggestions:
        assert optimizer.apply_optimization(s) is True

    metric = ResourceMetric(
        resource_type=ResResourceType.CPU,
        usage=0,
        capacity=0,
        unit="cores",
    )
    assert metric.utilization == 0.0
    assert metric.to_dict()["utilization"] == 0.0

    # empty utilization returns
    empty_optimizer = create_resource_optimizer(create_resource_monitor())
    assert empty_optimizer.analyze_optimization_opportunities() == []
    assert empty_optimizer.estimate_monthly_cost() == {"total": 0.0}


def test_resource_optimizer_volatile_exception(monkeypatch):
    monitor = create_resource_monitor()
    now = datetime.datetime.now()
    # low utilization CPU -> scale_down (not volatile)
    for i in range(20):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResResourceType.CPU,
                usage=20.0,
                capacity=100.0,
                unit="cores",
                timestamp=now,
            )
        )
    # medium utilization NETWORK -> hits _is_volatile which now raises
    for i in range(20):
        monitor.record_metric(
            ResourceMetric(
                resource_type=ResResourceType.NETWORK,
                usage=50.0,
                capacity=100.0,
                unit="GB",
                timestamp=now,
            )
        )
    monkeypatch.setattr(statistics, "stdev", lambda *a, **k: (_ for _ in ()).throw(ValueError("x")))
    optimizer = create_resource_optimizer(monitor)
    result = optimizer.analyze_optimization_opportunities()
    # CPU still yields a suggestion despite NETWORK branch crashing internally
    assert any(r.resource_type == ResResourceType.CPU for r in result)
    assert not any(r.resource_type == ResResourceType.NETWORK for r in result)


def test_cost_analyzer():
    analyzer = create_cost_analyzer()
    for i in range(12):
        analyzer.record_cost(
            "r1",
            100.0 + i * 5,
            {"cpu": 50.0, "memory": 30.0, "storage": 20.0},
        )
    # anomaly record
    analyzer.record_cost("r1", 1000.0, {"cpu": 500.0})

    assert analyzer.get_cost_trend("r1") != {}
    assert analyzer.get_cost_trend("missing") == {}

    anomalies = analyzer.identify_cost_anomalies(threshold=1.5)
    assert any(a["resource_id"] == "r1" for a in anomalies)


# ==============================================================================
# modules/optimization/storage_optimizer.py
# ==============================================================================
def test_storage_optimizer_lifecycle():
    storage = create_storage_manager()
    for i in range(20):
        obj = DataObject(
            id=f"obj-{i}",
            name=f"data-{i}.log",
            size=1024 * 1024 * ((i % 5) + 1),
            storage_type=StorageType.HOT,
            created_at=datetime.datetime.now() - datetime.timedelta(days=i % 120),
            last_accessed=datetime.datetime.now() - datetime.timedelta(days=i % 60),
            access_count=i % 20,
        )
        storage.add_object(obj)
        if i == 0:
            storage.access_object(obj.id)

    assert storage.get_object("obj-0") is not None
    assert storage.get_object("missing") is None
    assert storage.get_statistics().total_objects == 20
    assert storage.estimate_monthly_cost() >= 0.0

    optimizer = create_storage_optimizer(storage)
    recommendations = optimizer.analyze_storage_tiering()
    results = optimizer.apply_tiering(recommendations)
    assert sum(results.values()) > 0

    savings = optimizer.estimate_savings(recommendations)
    assert isinstance(savings, dict)

    unused = optimizer.identify_unused_data(days_threshold=30)
    assert isinstance(unused, list)

    delete_candidates = optimizer.suggest_deletion(size_threshold=1024, days_threshold=0)
    assert isinstance(delete_candidates, list)

    storage.remove_object("obj-1")
    assert storage.get_object("obj-1") is None


def test_data_compressor_and_lifecycle(tmp_path):
    compressor = create_data_compressor()
    raw = b"hello world " * 1000

    gzip_data, gzip_ratio = compressor.compress_data(raw, "gzip")
    zlib_data, zlib_ratio = compressor.compress_data(raw, "zlib")
    plain_data, plain_ratio = compressor.compress_data(raw, "unknown")

    assert len(gzip_data) < len(raw)
    assert len(zlib_data) < len(raw)
    assert len(plain_data) == len(raw)

    objects = [
        DataObject(id="1", name="a", size=1024 * 1024),
        DataObject(id="2", name="b", size=2 * 1024 * 1024),
    ]
    est = compressor.estimate_compression_savings(objects, estimated_ratio=2.0)
    assert est["savings"] > 0

    storage = create_storage_manager()
    storage.add_object(objects[0])
    storage.add_object(objects[1])
    lifecycle = create_data_lifecycle_manager(storage)
    lifecycle.add_lifecycle_policy(
        "policy-1",
        ".log",
        {
            "transition_after_days": 7,
            "transition_to": "cold",
            "delete_after_days": 30,
        },
    )
    actions = lifecycle.apply_lifecycle_policies()
    assert isinstance(actions, list)


def test_storage_statistics_to_dict():
    stats = StorageStatistics(total_objects=1, total_size=1024**3)
    d = stats.to_dict()
    assert d["total_size_gb"] == 1.0


# ==============================================================================
# modules/optimization/cache_optimizer.py
# ==============================================================================
@pytest.mark.parametrize(
    "strategy",
    [
        CacheStrategy.LRU,
        CacheStrategy.LFU,
        CacheStrategy.FIFO,
        CacheStrategy.TTL,
    ],
)
def test_cache_manager_eviction(strategy):
    cache = create_cache_manager(max_size=2, strategy=strategy)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.get("a")
    cache.set("c", "3")  # evict one
    # after eviction there are exactly 2 entries
    assert cache.get_statistics().size == 2

    if strategy == CacheStrategy.TTL:
        cache.cache["d"] = CacheEntry(
            key="d",
            value="4",
            ttl=0,
            created_at=datetime.datetime.now() - datetime.timedelta(seconds=1),
        )
        assert cache.get("d") is None  # expired immediately


def test_cache_manager_loader_and_distributed():
    cache = create_cache_manager(max_size=5)
    cache.register_loader("users:", lambda k: f"value_for_{k}")
    assert cache.get_or_load("users:alice") == "value_for_users:alice"
    assert cache.get_or_load("unknown") is None

    cache.warm_up(["users:bob", "users:carol"])
    assert cache.get("users:bob") is not None

    stats = cache.get_statistics()
    assert stats.to_dict()["hit_rate"] >= 0.0

    # distributed
    dist = create_distributed_cache_manager()
    dist.add_local_cache("node1", cache)
    dist.set("k", "v")
    assert dist.get("k") == "v"
    assert dist.get("missing_key") is None
    dist.invalidate("k")
    assert cache.get("k") is None
    assert "node1" in dist.get_global_statistics()


def test_cache_optimizer_suggestions():
    cache = create_cache_manager(max_size=10)
    optimizer = create_cache_optimizer(cache)

    for _ in range(5):
        optimizer.record_access("hotkey")
        time.sleep(0.01)

    patterns = optimizer.analyze_access_patterns()
    assert "hotkey" in patterns
    assert optimizer.suggest_ttl("hotkey") is not None
    assert optimizer.suggest_ttl("missing") is None

    cache.set("x", 1)
    cache.get("y")  # miss
    optimizer.optimize_cache()


def test_cache_entry_expiry():
    entry = CacheEntry(key="k", value="v", ttl=0)
    time.sleep(0.01)
    assert entry.is_expired() is True


# ==============================================================================
# modules/optimization/query_optimizer.py
# ==============================================================================
@pytest.mark.parametrize(
    "query,expected_type",
    [
        ("SELECT * FROM users", "select"),
        ("INSERT INTO t VALUES (1)", "insert"),
        ("UPDATE t SET a=1", "update"),
        ("DELETE FROM t WHERE id=1", "delete"),
        ("CREATE TABLE t (id INT)", "create"),
        ("ALTER TABLE t ADD c INT", "alter"),
        ("DROP TABLE t", "drop"),
        ("Mystery query", "select"),  # default
    ],
)
def test_query_optimizer_types(query, expected_type):
    opt = create_query_optimizer()
    result = opt.analyze_query(query)
    assert result.query_type.value == expected_type
    assert result.to_dict()["query_type"] == expected_type


def test_query_optimizer_issues():
    opt = create_query_optimizer()
    queries = [
        "SELECT * FROM users WHERE name LIKE '%john%'",
        "SELECT DISTINCT name FROM orders WHERE status='pending' OR status='failed'",
        "SELECT * FROM orders JOIN products ON 1=1",
        "SELECT (SELECT id FROM t) FROM outer_t",
    ]
    for q in queries:
        res = opt.analyze_query(q)
        assert res.issues

    good = opt.analyze_query("SELECT id FROM users WHERE id = 1 ORDER BY id")
    assert good.optimized_query is None


def test_slow_query_analyzer():
    analyzer = create_slow_query_analyzer()
    queries = [
        {"query": "SELECT * FROM large_table", "duration": 2.5},
        {"query": "SELECT id FROM small_table", "duration": 0.1},
    ]
    results = analyzer.analyze_slow_queries(queries)
    assert len(results) == 1
    analyzer.set_slow_query_threshold(0.05)
    results2 = analyzer.analyze_slow_queries(queries)
    assert len(results2) == 2


# ==============================================================================
# modules/high_availability/multi_region.py
# ==============================================================================
def test_multi_region_routing():
    manager = create_multi_region_manager()
    manager.add_region(
        Region(
            id="us-east-1",
            name="US East",
            location="us-east",
            endpoint="https://us-east.example.com",
            priority=1,
            capacity=0.5,
            latency=50,
        )
    )
    manager.add_region(
        Region(
            id="us-west-2",
            name="US West",
            location="us-west",
            endpoint="https://us-west.example.com",
            priority=2,
            capacity=0.3,
            latency=80,
        )
    )

    # weighted default
    assert manager.route_request() is not None

    for strategy in RoutingStrategy:
        manager.set_routing_strategy(strategy)
        region = manager.route_request(
            request_context=(
                {"location": "us-east"} if strategy == RoutingStrategy.GEOGRAPHIC else None
            )
        )
        assert region is not None

    manager.remove_region("us-west-2")
    assert manager.route_request() is not None

    # empty active
    manager.update_region_status("us-east-1", RegionStatus.DOWN)
    assert manager.route_request() is None


def test_multi_region_health_and_failover():
    manager = create_multi_region_manager()
    manager.add_region(Region(id="r1", name="R1", location="l1", priority=1, capacity=1.0))
    manager.add_region(Region(id="r2", name="R2", location="l2", priority=2, capacity=1.0))

    health = manager.perform_health_check()
    assert all(health.values())

    assert manager.trigger_failover("r1") is True
    assert manager.get_active_regions() == [manager.regions["r2"]]

    assert manager.trigger_failover("missing") is False
    manager.update_region_status("r2", RegionStatus.DOWN)
    assert manager.trigger_failover("r2") is False  # no active left

    stats = manager.get_region_statistics()
    assert stats["total_regions"] == 2


def test_data_sync_manager():
    sync = create_data_sync_manager()
    assert sync.sync_data("missing", {"x": 1}) == {}
    sync.configure_sync("us-east-1", ["us-west-2", "eu-west-1"], "async")
    results = sync.sync_data("us-east-1", {"x": 1})
    assert all(results.values())
    assert sync.get_sync_status()


def test_region_to_dict():
    r = Region(id="x", name="X", location="L")
    assert r.to_dict()["id"] == "x"


# ==============================================================================
# modules/apm/code_profiler.py
# ==============================================================================
def test_code_profiler_basic():
    profiler = CodeProfiler()

    @profiler.profile("hot_func")
    def hot_func(x):
        return x * x

    hot_func(2)
    hot_func(3)

    hotspots = profiler.get_hotspots(by="total_time")
    assert hotspots[0].function_name == "hot_func"
    assert len(profiler.get_call_tree()) == 2

    total = profiler.get_hotspots(by="avg_time")
    count = profiler.get_hotspots(by="call_count")
    assert total and count

    d = profiler.metrics["hot_func"].to_dict()
    assert d["call_count"] == 2
    assert d["min_time"] >= 0.0

    # disabled
    profiler.disable()
    assert hot_func(4) == 16
    profiler.reset()
    assert not profiler.metrics


def test_apm_profiler_and_memory_sql():
    apm = create_apm_profiler()
    apm.enable_all()

    @apm.code_profiler.profile()
    def sample():
        return 1

    sample()

    # memory profiler
    apm.memory_profiler.take_snapshot("s1")
    apm.memory_profiler.take_snapshot("s2")
    trend = apm.memory_profiler.get_memory_trend()
    assert trend.get("snapshots", 0) >= 2
    leaks = apm.memory_profiler.detect_leaks(threshold=-1.0)
    assert isinstance(leaks, list)

    # sql analyzer
    apm.sql_analyzer.record_query("SELECT * FROM users WHERE id = 1", 0.05, 1)
    apm.sql_analyzer.record_query("SELECT * FROM orders WHERE user_id = 2", 2.0, 10)
    assert apm.sql_analyzer.get_slow_queries(threshold=1.0)
    assert apm.sql_analyzer.get_query_statistics()
    apm.sql_analyzer.disable()
    apm.sql_analyzer.record_query("SELECT 1", 0.0, 0)  # ignored

    report = apm.get_performance_report()
    assert "code_hotspots" in report
    assert "slow_queries" in report

    apm.reset()


def test_call_stack_duration():
    stack = CallStack(function_name="f", start_time=time.time())
    assert stack.duration >= 0.0
    stack.end_time = time.time() + 1.0
    assert stack.duration == 1.0
    assert stack.to_dict()["function_name"] == "f"


# ==============================================================================
# modules/execute/saga/participants.py
# ==============================================================================
def test_participant_abstract():
    with pytest.raises(TypeError):
        Participant("p")


async def _run(coro):
    return await coro


def test_compensation_action():
    action = create_compensation_action("a", lambda: 1, lambda: None)
    assert isinstance(action, CompensationAction)
    assert action.execute() == 1


def test_database_participant():
    session = MagicMock()
    session.begin = AsyncMock(return_value=MagicMock(rollback=AsyncMock()))
    participant = DatabaseParticipant("db", session)

    async def op(sess, ctx):
        return {"ok": True}

    result = asyncio.run(participant.execute({"db_operation": op}))
    assert result["ok"] is True

    asyncio.run(participant.compensate({}))
    assert session.begin.return_value.rollback.called


def test_api_call_participant():
    response = MagicMock()
    response.json.return_value = {"transaction_id": "t1"}
    client = MagicMock()
    client.post = AsyncMock(return_value=response)

    participant = APICallParticipant("api", "http://e", "http://c", client)
    result = asyncio.run(participant.execute({"api_payload": {"x": 1}}))
    assert result["transaction_id"] == "t1"
    asyncio.run(participant.compensate({}))
    assert client.post.call_count == 2


def test_message_queue_participant():
    client = MagicMock()
    client.publish = AsyncMock(return_value="msg-1")
    participant = MessageQueueParticipant("mq", client, "orders")
    result = asyncio.run(participant.execute({"mq_message": {"x": 1}}))
    assert result["message_id"] == "msg-1"
    asyncio.run(participant.compensate({}))
    assert client.publish.call_count == 2


def test_resource_allocation_participant():
    manager = MagicMock()
    manager.allocate = AsyncMock(return_value=["r1", "r2"])
    manager.release = AsyncMock()
    participant = ResourceAllocationParticipant("res", manager)
    result = asyncio.run(participant.execute({"res_spec": {"cpu": 1}}))
    assert result["allocated"] == ["r1", "r2"]
    asyncio.run(participant.compensate({}))
    assert manager.release.call_count == 2


def test_notification_participant():
    service = MagicMock()
    service.send = AsyncMock(return_value="n1")
    service.cancel = AsyncMock()
    participant = NotificationParticipant("notify", service)
    assert participant.should_compensate({}) is False
    result = asyncio.run(participant.execute({"notify_notification": {"msg": "hi"}}))
    assert result["notification_id"] == "n1"
    asyncio.run(participant.compensate({}))
    assert service.cancel.called


# ==============================================================================
# modules/analyze/anomaly/transformer_service.py
# ==============================================================================
def test_transformer_model_manager_load_and_errors(tmp_path, monkeypatch):
    state_dict = _create_model_state_dict()
    monkeypatch.setattr(
        torch,
        "load",
        lambda *args, map_location=None, weights_only=False, **kwargs: state_dict,
    )

    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model_path = model_dir / "model.pth"
    model_path.write_text("")  # existence only, content mocked

    manager = TransformerModelManager(model_dir=str(model_dir), model_name="model.pth")

    # invalid threshold
    assert manager.load_model(str(model_path), threshold=2.0) is False
    # path traversal
    assert manager.load_model("/etc/passwd", threshold=0.5) is False
    # missing file
    assert manager.load_model(str(tmp_path / "missing.pth"), threshold=0.5) is False
    # valid load
    assert (
        manager.load_model(
            str(model_path), threshold=0.5, input_dim=1, d_model=8, n_heads=2, n_layers=1, d_ff=16
        )
        is True
    )
    assert manager.is_loaded
    assert manager.model is not None
    assert manager.wrapper is not None

    manager.unload_model()
    assert not manager.is_loaded
    assert (
        manager.reload_model(
            model_path=str(model_path),
            input_dim=1,
            d_model=8,
            n_heads=2,
            n_layers=1,
            d_ff=16,
        )
        is True
    )


def test_transformer_service_detect(tmp_path, monkeypatch):
    state_dict = _create_model_state_dict()
    monkeypatch.setattr(
        torch,
        "load",
        lambda *args, map_location=None, weights_only=False, **kwargs: state_dict,
    )

    model_dir = tmp_path / "m"
    model_dir.mkdir()
    model_path = model_dir / "model.pth"
    model_path.write_text("")

    manager = TransformerModelManager(model_dir=str(model_dir))
    assert manager.load_model(
        str(model_path), input_dim=1, d_model=8, n_heads=2, n_layers=1, d_ff=16
    )

    # use only the raw value column so tensor shape matches input_dim=1
    manager.preprocessor = TimeSeriesPreprocessingPipeline(
        clean_missing=True,
        clean_outliers=False,
        add_features=False,
        scale=True,
        scale_method="standard",
    )

    service = TransformerAnomalyService(manager)
    result = service.detect_single([1.0, 2.0, 3.0, 4.0, 5.0])
    assert "is_anomaly" in result
    assert isinstance(result["anomaly_count"], int)

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="1min"),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
    )
    df_result = service.detect_from_dataframe(df)
    assert "is_anomaly" in df_result.columns
    assert "anomaly_score" in df_result.columns

    batch = service.detect_batch([[1.0, 2.0, 3.0, 4.0, 5.0], [5.0, 4.0, 3.0, 2.0, 1.0]])
    assert len(batch) == 2

    manager.unload_model()
    with pytest.raises(Exception):
        service.detect_single([1.0])


def test_transformer_service_global_and_router(tmp_path, monkeypatch):
    state_dict = _create_model_state_dict()
    monkeypatch.setattr(
        torch,
        "load",
        lambda *args, map_location=None, weights_only=False, **kwargs: state_dict,
    )

    model_dir = tmp_path / "global"
    model_dir.mkdir()
    model_path = model_dir / "model.pth"
    model_path.write_text("")

    manager = get_model_manager()
    manager.model_dir = model_dir
    manager.model_name = "model.pth"
    assert (
        initialize_service(
            model_path=str(model_path),
            input_dim=1,
            d_model=8,
            n_heads=2,
            n_layers=1,
            d_ff=16,
        )
        is True
    )

    svc = get_service()
    assert svc is not None

    shutdown_service()
    assert not manager.is_loaded

    router = create_router()
    assert router is not None


def test_transformer_compat_not_loaded():
    with pytest.raises(Exception):
        compat = TransformerAnomalyDetectorCompat(model_path="/nonexistent", threshold=0.5)
        compat.train(pd.DataFrame())
        compat.detect(pd.DataFrame())
