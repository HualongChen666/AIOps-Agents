# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for batch 23a core modules."""

import datetime
import json  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.approval_store as approval_store
import core.collector as collector
import core.database_query_optimizer as dqo
import core.docker_repair as docker_repair
import core.monitoring_infrastructure as mi

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.docker_repair
# ---------------------------------------------------------------------------
def test_get_docker_repair_scripts():
    scripts = docker_repair.get_docker_repair_scripts()
    assert "restart_container" in scripts
    assert "ps" in scripts
    assert scripts["prune_images"]["read_only"] is False


async def test_execute_repair_unknown_script():
    result = await docker_repair.execute_repair_sync(
        "h1", "missing", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "Unknown" in result["error"]


async def test_execute_repair_missing_required_param():
    result = await docker_repair.execute_repair_sync(
        "h1", "restart_container", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "Missing required params" in result["error"]


async def test_execute_repair_dry_run_no_docker(monkeypatch):
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: None)
    result = await docker_repair.execute_repair_sync(
        "h1", "ps", {}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["docker_available"] is False


async def test_execute_repair_force_subprocess_success(monkeypatch):
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: "/bin/docker")
    fake_proc = MagicMock(returncode=0, stdout="ok output", stderr="")
    monkeypatch.setattr("core.docker_repair.subprocess.run", lambda *a, **k: fake_proc)
    result = await docker_repair.execute_repair_sync(
        "h1", "prune_images", {"force": "true"}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["returncode"] == 0
    assert "stdout" in result


async def test_execute_repair_force_subprocess_failure(monkeypatch):
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: "/bin/docker")
    fake_proc = MagicMock(returncode=1, stdout="", stderr="error")
    monkeypatch.setattr("core.docker_repair.subprocess.run", lambda *a, **k: fake_proc)
    result = await docker_repair.execute_repair_sync(
        "h1", "prune_images", {"force": "true"}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["returncode"] == 1


async def test_execute_repair_subprocess_exception(monkeypatch, tmp_path):
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: "/bin/docker")
    monkeypatch.setattr(
        "core.docker_repair.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    hist = tmp_path / "hist.json"
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", hist)
    result = await docker_repair.execute_repair_sync(
        "h1", "prune_images", {"force": "true"}
    )  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "boom" in result["error"]


def test_load_history_invalid_json(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", bad)
    assert docker_repair.get_docker_repair_history() == []


def test_save_history_failure(monkeypatch, tmp_path):
    # Use a directory as the target so write_text raises IsADirectoryError.
    target = tmp_path / "history_dir"
    target.mkdir()
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", target)
    # _save_history should swallow the exception.
    docker_repair._save_history([{"x": 1}])


def test_get_docker_repair_history_limits(monkeypatch, tmp_path):
    hist = tmp_path / "hist.json"
    hist.write_text(json.dumps([{"i": i} for i in range(5)]), encoding="utf-8")
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", hist)
    assert len(docker_repair.get_docker_repair_history(limit=2)) == 2
    assert len(docker_repair.get_docker_repair_history(limit=0)) == 5


async def test_history_recorded_after_execution(monkeypatch, tmp_path):
    hist = tmp_path / "hist.json"
    monkeypatch.setattr("core.docker_repair._HISTORY_FILE", hist)
    monkeypatch.setattr("core.docker_repair.shutil.which", lambda x: None)
    await docker_repair.execute_repair_sync("h1", "ps", {})
    history = docker_repair.get_docker_repair_history()
    assert len(history) >= 1
    assert history[-1]["script"] == "ps"


# ---------------------------------------------------------------------------
# core.approval_store
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_approvals():
    approval_store.clear_all_approvals()
    yield
    approval_store.clear_all_approvals()


def test_upsert_and_get_approval():
    assert approval_store.upsert_approval("a1", {"status": "pending", "x": [1]}) is True
    got = approval_store.get_approval("a1")
    assert got["status"] == "pending"
    # returned copy should be independent
    got["x"].append(2)
    assert approval_store.get_approval("a1")["x"] == [1]


def test_upsert_invalid():
    assert approval_store.upsert_approval("", {"status": "pending"}) is False
    assert approval_store.upsert_approval("a2", None) is False
    assert approval_store.upsert_approval("a2", "notdict") is False


def test_is_pending_and_count():
    approval_store.upsert_approval("p1", {"status": "pending"})
    approval_store.upsert_approval("p2", {"status": "approved_no_script"})
    assert approval_store.is_pending("p1") is True
    assert approval_store.is_pending("p2") is False
    assert approval_store.is_pending(123) is False
    assert approval_store.approval_count() == 2


def test_update_approval_field_and_status():
    approval_store.upsert_approval("u1", {"status": "pending", "proposal": "x"})
    assert approval_store.update_approval_field("u1", "proposal", "new") is True
    assert approval_store.get_approval("u1")["proposal"] == "new"
    assert approval_store.update_approval_status("u1", "approved_no_script") is True
    assert approval_store.get_approval("u1")["status"] == "approved_no_script"
    # invalid status via field update
    assert approval_store.update_approval_field("u1", "status", "bad") is False
    # whitelist rejection
    assert approval_store.update_approval_field("u1", "alert", {}) is False
    # non-existent record
    assert approval_store.update_approval_field("missing", "status", "pending") is False


def test_update_approval_status_invalid():
    assert approval_store.update_approval_status("any", "not-a-status") is False


def test_remove_approval():
    approval_store.upsert_approval("r1", {"status": "pending"})
    assert approval_store.remove_approval("r1") is True
    assert approval_store.remove_approval("r1") is False
    assert approval_store.remove_approval(123) is False


def test_snapshots():
    approval_store.upsert_approval("s1", {"status": "pending", "k": 1})
    approval_store.upsert_approval("s2", {"status": "executed_success", "k": 2})
    all_snap = approval_store.get_all_approvals_snapshot()
    assert set(all_snap.keys()) == {"s1", "s2"}
    pending = (
        approval_store.get_pending_only_snapshot()
    )  # noqa: F841  # Variable for test verification
    assert list(pending.keys()) == ["s1"]


def test_clear_all_approvals():
    approval_store.upsert_approval("c1", {"status": "pending"})
    count = approval_store.clear_all_approvals()
    assert count == 1
    assert approval_store.approval_count() == 0
    # clearing empty store returns 0 and no warning
    assert approval_store.clear_all_approvals() == 0


# ---------------------------------------------------------------------------
# core.monitoring_infrastructure
# ---------------------------------------------------------------------------
def test_metric_data_defaults():
    m = mi.MetricData(name="m1", value=1.0, metric_type=mi.MetricType.COUNTER)
    assert m.labels == {}
    assert m.timestamp.tzinfo is not None


def test_enhanced_metrics_collector():
    c = mi.EnhancedMetricsCollector()
    c.record_metric(mi.MetricData("m", 1.0, mi.MetricType.GAUGE))
    c.increment_counter("hits")
    c.set_gauge("temp", 22.5)
    c.record_timing("op", 12.3)
    assert c.get_stub_metrics() == {}


def test_enhanced_log_collector():
    c = mi.EnhancedLogCollector()
    c.info("msg", "svc")
    c.warning("msg", "svc", {"x": "1"})
    c.error("msg", "svc")
    assert c.get_stub_logs() == []


def test_enhanced_trace_collector():
    c = mi.EnhancedTraceCollector()
    span = c.start_span("op")
    assert span == ""
    c.end_span(span)
    c.record_trace(
        mi.TraceData(
            trace_id="t",
            span_id="s",
            parent_span_id=None,
            operation_name="op",
            start_time=datetime.datetime.now(datetime.timezone.utc),
            end_time=None,
            status="ok",
        )
    )
    assert c.get_stub_traces() == {}


def test_monitoring_infrastructure_record_methods():
    infra = mi.MonitoringInfrastructure()
    infra.record_api_metric("/api", "GET", 200, 45.0)
    infra.record_database_metric("read", "users", 12.0, True)
    infra.record_cache_metric("get", True)
    infra.record_system_metric(10.0, 50.0, 70.0)
    assert infra.get_monitoring_status() == {}
    assert infra.prometheus_config["enabled"] is True
    assert isinstance(mi.get_monitoring_infrastructure(), mi.MonitoringInfrastructure)


# ---------------------------------------------------------------------------
# core.database_query_optimizer
# ---------------------------------------------------------------------------
def _fresh_optimizer(**kwargs):
    cfg = {"cache_l2_enabled": False, "cache_enabled": True, **kwargs}
    return dqo.get_database_query_optimizer(cfg)


def test_get_database_query_optimizer():
    opt = _fresh_optimizer()
    assert isinstance(opt, dqo.DatabaseQueryOptimizer)


def test_analyze_query_performance():
    opt = _fresh_optimizer()
    result = opt.analyze_query_performance(
        "SELECT * FROM users", duration_ms=1500
    )  # noqa: F841  # Variable for test verification
    assert result["pattern"] == "select_star"
    assert "recommendations" in result


def test_classify_query_patterns():
    opt = _fresh_optimizer()
    assert opt.classify_query_pattern("SELECT * FROM t") == "select_star"
    assert opt.identify_n_plus_one_pattern("select x, (select y from z) from a join b") is True
    assert opt.identify_missing_index_pattern("SELECT id FROM t WHERE name LIKE '%x%'") is True
    assert opt.identify_inefficient_join_pattern("SELECT id FROM a JOIN b ORDER BY x") is True
    assert (
        opt.identify_n_plus_one_pattern("SELECT id FROM t WHERE id IN (SELECT id FROM u)") is False
    )
    assert opt.classify_query_pattern("SELECT id FROM t") == "unknown"


def test_generate_optimizations_for_patterns():
    opt = _fresh_optimizer(slow_query_threshold_ms=500)
    cases = [
        (
            "n1",
            "SELECT a, (SELECT b FROM c) FROM d JOIN e",
            dqo.QueryOptimizationType.NPLUS_ONE_FIX,
        ),
        ("n2", "SELECT id FROM t WHERE name LIKE '%x%'", dqo.QueryOptimizationType.INDEX_ADDITION),
        ("n3", "SELECT id FROM a JOIN b ORDER BY x", dqo.QueryOptimizationType.JOIN_OPTIMIZATION),
        ("n4", "SELECT * FROM t", dqo.QueryOptimizationType.QUERY_REWRITE),
        (
            "n5",
            "SELECT id FROM t WHERE EXISTS (SELECT 1 FROM u)",
            dqo.QueryOptimizationType.SUBQUERY_OPTIMIZATION,
        ),
    ]
    for qid, qtext, expected_type in cases:
        opt.record_query_execution(qid, qtext, "db", "t", 2000.0)
    opts = opt.generate_optimizations()
    types = {o.optimization_type for o in opts}
    assert all(expected_type in types for _, _, expected_type in cases)


def test_record_query_execution_update():
    opt = _fresh_optimizer()
    opt.record_query_execution("q", "SELECT 1", "db", "t", 1000.0)
    opt.record_query_execution("q", "SELECT 1", "db", "t", 1000.0)
    opt.record_query_execution("q", "SELECT 1", "db", "t", 1000.0)
    sq = opt.slow_queries["q"]
    assert sq.execution_count == 2
    assert sq.total_duration_ms == 3000.0
    assert sq.avg_duration_ms == 1500.0
    assert sq.max_duration_ms == 1000.0


def test_analyze_slow_queries_and_get_query_analysis():
    opt = _fresh_optimizer(slow_query_threshold_ms=100)
    opt.record_query_execution("slow", "SELECT * FROM t", "db", "t", 500.0)
    slow = opt.analyze_slow_queries()
    assert len(slow) == 1
    analysis = opt.get_query_analysis("slow")
    assert analysis is not None
    assert analysis["query_id"] == "slow"
    assert analysis["performance_history"]["total_executions"] == 1


def test_get_query_analysis_p95():
    opt = _fresh_optimizer()
    for i in range(20):
        opt.record_query_execution("p95", "SELECT x", "db", "t", float(i))
    analysis = opt.get_query_analysis("p95")
    assert analysis["performance_history"]["p95_duration_ms"] >= 0


def test_get_query_analysis_missing():
    opt = _fresh_optimizer()
    assert opt.get_query_analysis("missing") is None


def test_cache_disabled():
    opt = _fresh_optimizer(cache_enabled=False)
    opt.cache_result("q", [1])
    assert opt.get_cached_result("q") is None
    assert opt.get_cache_statistics()["enabled"] is False


def test_l1_and_query_cache():
    opt = _fresh_optimizer()
    opt.cache_query_result("SELECT 1", [1, 2, 3])
    assert opt.get_cached_query_result("SELECT 1") == [1, 2, 3]
    stats = opt.get_cache_statistics()
    assert stats["hits"] >= 1
    opt.invalidate_query_cache("SELECT 1")
    assert opt.get_cached_query_result("SELECT 1") is None


def test_l1_cache_eviction_handling(monkeypatch):
    opt = _fresh_optimizer()

    class FakeL1Cache:
        def __setitem__(self, key, value):
            raise RuntimeError("full")

        def __contains__(self, key):
            return False

        def clear(self):
            pass

        def __len__(self):
            return 0

    monkeypatch.setattr(opt, "l1_cache", FakeL1Cache())
    opt.cache_result("q", [1])
    assert opt.cache_evictions == 1


def test_l2_redis_cache(monkeypatch):
    opt = _fresh_optimizer()
    fake_redis = MagicMock()
    fake_redis.get = MagicMock(return_value=json.dumps({"rows": [1, 2]}))
    fake_redis.setex = MagicMock()
    fake_redis.keys = MagicMock(return_value=["db_query:k1"])
    fake_redis.delete = MagicMock(return_value=1)
    opt.l2_redis_client = fake_redis
    # cache result into L2
    opt.cache_result("q", {"rows": [1, 2]}, ttl=60)
    fake_redis.setex.assert_called_once()
    # get from L2
    assert opt.get_cached_result("q") == {"rows": [1, 2]}
    # invalidate by query text
    assert opt.invalidate_cache("q") >= 1
    # invalidate by pattern
    assert opt.invalidate_cache(pattern="db_query:*") == 1


def test_l2_redis_exceptions(monkeypatch):
    opt = _fresh_optimizer()
    # Ensure only the in-memory query cache is used for the manual entry.
    opt.l1_cache = None
    opt.l2_redis_client = None
    opt.cache_result("manual", "fallback")

    fake_redis = MagicMock()
    fake_redis.get = MagicMock(side_effect=RuntimeError("redis down"))
    fake_redis.setex = MagicMock(side_effect=RuntimeError("redis down"))
    fake_redis.keys = MagicMock(side_effect=RuntimeError("redis down"))
    fake_redis.delete = MagicMock(side_effect=RuntimeError("redis down"))
    opt.l2_redis_client = fake_redis
    # should fall back to in-memory query cache
    assert opt.get_cached_result("manual") == "fallback"
    # cache_result should not raise
    opt.cache_result("q", [1])
    # invalidate should not raise
    assert opt.invalidate_cache("q") == 0


def test_clear_query_cache():
    opt = _fresh_optimizer()
    opt.cache_query_result("q", 1)
    opt.cache_hits = 5
    opt.clear_query_cache()
    assert opt.get_cached_query_result("q") is None
    assert opt.cache_hits == 0


def test_identify_indexable_columns():
    opt = _fresh_optimizer()
    cols = opt._identify_indexable_columns(
        "SELECT * FROM users WHERE id = 1 AND name = 'x' ORDER BY created_at LIMIT 10"
    )
    assert "id" in cols
    assert "name" in cols
    assert "created_at" in cols


def test_rewrite_subquery():
    opt = _fresh_optimizer()
    rewritten = opt._rewrite_subquery(
        "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE active = 1)"
    )
    assert "EXISTS" in rewritten
    assert "users.id = user_id" in rewritten


def test_generate_optimization_recommendations_with_query():
    opt = _fresh_optimizer()
    recs = opt.generate_optimization_recommendations("SELECT * FROM users")
    assert isinstance(recs, list)


def test_get_statistics():
    opt = _fresh_optimizer()
    opt.record_query_execution("q", "SELECT 1", "db", "t", 10.0)
    opt.generate_optimizations()
    stats = opt.get_statistics()
    assert stats["total_queries_analyzed"] >= 1
    assert "total_slow_queries" in stats


# ---------------------------------------------------------------------------
# core.collector
# ---------------------------------------------------------------------------
class _NoSuchProcess(Exception):
    pass


class _AccessDenied(Exception):
    pass


def _make_fake_psutil():
    class _FakeCPU:
        current = 2400.0

    class _FakeVM:
        total = 8 * (1024**3)
        used = 4 * (1024**3)
        available = 4 * (1024**3)
        percent = 50.0

    class _FakeSwap:
        total = 2 * (1024**3)
        used = 1 * (1024**3)
        percent = 50.0

    class _FakeNetIO:
        bytes_recv = 1024
        bytes_sent = 512
        packets_recv = 10
        packets_sent = 5
        errin = 0
        errout = 0

    class _FakeUsage:
        total = 100 * (1024**3)
        used = 50 * (1024**3)
        free = 50 * (1024**3)
        percent = 50.0

    class _FakePartition:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class _FakeProcess:
        def __init__(self, pid, name, status, username, cpu_seq=None, mem_seq=None):
            self.pid = pid
            self.info = {"pid": pid, "name": name, "status": status, "username": username}
            self._cpu_iter = iter(cpu_seq or [5.0, 5.0])
            self._mem_iter = iter(mem_seq or [3.0, 3.0])

        def cpu_percent(self):
            try:
                return next(self._cpu_iter)
            except StopIteration:
                return 0.0

        def memory_percent(self):
            try:
                return next(self._mem_iter)
            except StopIteration:
                return 0.0

    class _FakePsutil:
        NoSuchProcess = _NoSuchProcess
        AccessDenied = _AccessDenied
        PermissionError = PermissionError
        OSError = OSError

        def cpu_freq(self):
            return _FakeCPU()

        def cpu_percent(self, interval=None, percpu=False):
            if percpu:
                return [10.0, 20.0]
            return 15.0

        def cpu_count(self, logical=False):
            return 2 if logical else 1

        def virtual_memory(self):
            return _FakeVM()

        def swap_memory(self):
            return _FakeSwap()

        def boot_time(self):
            return 1_000_000_000

        def net_io_counters(self):
            return _FakeNetIO()

        def disk_partitions(self, all=False):
            return [
                _FakePartition(device="C:", mountpoint="C:\\", fstype="ntfs", opts=""),
                _FakePartition(device="D:", mountpoint="D:\\", fstype="ntfs", opts="cdrom"),
                _FakePartition(device="E:", mountpoint="E:\\", fstype="", opts=""),
                _FakePartition(device="F:", mountpoint="F:\\", fstype="ntfs", opts=""),
                _FakePartition(device="G:", mountpoint="G:\\", fstype="ntfs", opts=""),
            ]

        def disk_usage(self, mountpoint):
            if mountpoint in ("C:\\", "F:\\"):
                return _FakeUsage()
            raise PermissionError("denied")

        def process_iter(self, attrs=None):
            return [
                _FakeProcess(1, "a.exe", "running", "user"),
                _FakeProcess(
                    2,
                    "b.exe",
                    "running",
                    "user",
                    cpu_seq=[1.0, _NoSuchProcess],
                    mem_seq=[2.0, _AccessDenied],
                ),
                _FakeProcess(3, "c.exe", "running", "domain\\user"),
                _FakeProcess(
                    4, "d.exe", "running", "user", cpu_seq=[_NoSuchProcess], mem_seq=[_AccessDenied]
                ),
            ]

    return _FakePsutil()


@pytest.fixture
def collector_fakes(monkeypatch):
    monkeypatch.setattr("core.collector.psutil", _make_fake_psutil())
    monkeypatch.setattr("core.collector.time.sleep", lambda x: None)
    monkeypatch.setattr("core.collector._tracer", None)
    monkeypatch.setattr("core.collector._collect_all_counter", None)
    monkeypatch.setattr("core.collector._collect_all_histogram", None)
    collector.invalidate_collect_cache()


def test_get_cpu_metrics(collector_fakes, monkeypatch):
    cpu = collector.get_cpu_metrics()
    assert "usage_percent" in cpu
    assert cpu["core_count"] >= 1
    assert isinstance(cpu["per_core"], list)


def test_get_cpu_metrics_none_values(collector_fakes, monkeypatch):
    monkeypatch.setattr(
        "core.collector.psutil.cpu_percent",
        lambda interval=None, percpu=False: [10.0, None] if percpu else None,
    )
    cpu = collector.get_cpu_metrics()
    assert cpu["usage_percent"] == 0.0
    assert cpu["per_core"] == [10.0, 0.0]


def test_get_cpu_metrics_freq_exception(collector_fakes, monkeypatch):
    monkeypatch.setattr(
        "core.collector.psutil.cpu_freq",
        lambda: (_ for _ in ()).throw(RuntimeError("freq fail")),
    )
    cpu = collector.get_cpu_metrics()
    assert cpu["frequency_mhz"] == 0.0


def test_get_memory_metrics(collector_fakes):
    mem = collector.get_memory_metrics()
    assert mem["total_gb"] > 0
    assert "swap_total_gb" in mem


def test_get_memory_metrics_swap_exception(collector_fakes, monkeypatch):
    monkeypatch.setattr(
        "core.collector.psutil.swap_memory",
        lambda: (_ for _ in ()).throw(RuntimeError("swap fail")),
    )
    mem = collector.get_memory_metrics()
    assert mem["swap_total_gb"] == 0.0


def test_get_disk_metrics(collector_fakes):
    disks = collector.get_disk_metrics()
    # C: and F: succeed; D: skipped (cdrom), E: skipped (empty fstype), G: raises PermissionError
    assert any(d["mountpoint"] == "C:\\" for d in disks)
    assert not any(d["mountpoint"] == "D:\\" for d in disks)


def test_get_disk_metrics_partition_limit(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector._DISK_PARTITION_MAX", 1)
    disks = collector.get_disk_metrics()
    assert len(disks) == 1


def test_get_disk_metrics_partitions_exception(collector_fakes, monkeypatch):
    monkeypatch.setattr(
        "core.collector.psutil.disk_partitions",
        lambda all=False: (_ for _ in ()).throw(RuntimeError("partitions fail")),
    )
    assert collector.get_disk_metrics() == []


def test_get_network_metrics_first_call(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector._is_first_net_call", True)
    net = collector.get_network_metrics()
    assert net["recv_speed_mb"] == 0.0
    assert net["packets_recv"] == 10


def test_get_network_metrics_negative_diff(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector._is_first_net_call", True)
    collector.get_network_metrics()

    class _LowerNet:
        bytes_recv = 512
        bytes_sent = 1024
        packets_recv = 11
        packets_sent = 6
        errin = 0
        errout = 0

    monkeypatch.setattr("core.collector.psutil.net_io_counters", lambda: _LowerNet())
    net = collector.get_network_metrics()
    assert net["recv_speed_mb"] == 0.0
    assert net["sent_speed_mb"] == 0.0


def test_get_network_metrics_exception(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector._is_first_net_call", True)
    monkeypatch.setattr(
        "core.collector.psutil.net_io_counters",
        lambda: (_ for _ in ()).throw(RuntimeError("net fail")),
    )
    net = collector.get_network_metrics()
    assert net["recv_speed_mb"] == 0.0


def test_get_top_processes(collector_fakes):
    procs = collector.get_top_processes(limit=10)
    assert len(procs) >= 1
    assert all("cpu_percent" in p and "memory_percent" in p for p in procs)
    # invalid limit handling
    assert collector.get_top_processes(limit=0)


def test_get_system_info(collector_fakes):
    info = collector.get_system_info()
    assert "hostname" in info
    assert "uptime_hours" in info


def test_get_system_info_boot_exception(collector_fakes, monkeypatch):
    monkeypatch.setattr(
        "core.collector.psutil.boot_time",
        lambda: (_ for _ in ()).raise_(),
    )

    def _raise(*args, **kwargs):
        raise OSError("boot fail")

    monkeypatch.setattr("core.collector.psutil", type("x", (), {"boot_time": _raise})())
    info = collector.get_system_info()
    assert info["boot_time"] == "Unknown"


def test_get_collect_metrics_and_record(collector_fakes):
    before = collector.get_collect_metrics()["total_calls"]
    collector._record_collect_metric(cache_hit=True)
    collector._record_collect_metric(cache_hit=False, collect_ms=12.3)
    after = collector.get_collect_metrics()
    assert after["total_calls"] == before + 2
    assert after["cache_hits"] >= 1
    assert after["cache_misses"] >= 1
    assert after["cache_hit_rate"] >= 0


def test_cache_validity_and_snapshot(collector_fakes, monkeypatch):
    collector.invalidate_collect_cache()
    assert collector.get_cached_snapshot() is None
    snap = {"cpu": 1.0}
    now = 1000.0
    monkeypatch.setattr("core.collector.time.monotonic", lambda: now)
    monkeypatch.setattr(
        "core.collector._collect_cache",
        {"data": snap, "ts": now},
    )
    assert collector.get_cached_snapshot() == snap
    # negative elapsed invalidates cache
    monkeypatch.setattr("core.collector.time.monotonic", lambda: now - 1)
    assert collector.get_cached_snapshot() is None


def test_get_cached_snapshot_host_filter(collector_fakes, monkeypatch):
    now = 5000.0
    monkeypatch.setattr("core.collector.time.monotonic", lambda: now)
    monkeypatch.setattr(
        "core.collector._collect_cache",
        {"data": {"hosts": {"h1": {"x": 1}}}, "ts": now},
    )
    assert collector.get_cached_snapshot(host_id="h1") == {"x": 1}
    assert collector.get_cached_snapshot(host_id="missing") == {}


def test_collect_cpu_and_processes(collector_fakes):
    cpu, procs = collector._collect_cpu_and_processes(proc_limit=10)
    assert "usage_percent" in cpu
    assert isinstance(procs, list)


def _fake_thread_pool(exc_cpu=None, exc_io=None):
    class _FakeFuture:
        def __init__(self, fn, args, kwargs):
            self.fn = fn
            self.args = args
            self.kwargs = kwargs

        def result(self, timeout=None):
            if exc_cpu and self.fn.__name__ == "_collect_cpu_and_processes":
                raise exc_cpu
            if exc_io and self.fn.__name__ != "_collect_cpu_and_processes":
                raise exc_io
            return self.fn(*self.args, **self.kwargs)

    class _FakeTPE:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, fn, *args, **kwargs):
            return _FakeFuture(fn, args, kwargs)

        def shutdown(self, wait=False):
            pass

    return _FakeTPE


def test_collect_all_normal(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector.ThreadPoolExecutor", _fake_thread_pool())
    snapshot = collector.collect_all()
    assert "timestamp" in snapshot
    assert "cpu" in snapshot
    assert "top_processes" in snapshot
    # second call should hit cache
    cached = collector.collect_all()
    assert cached["timestamp"] == snapshot["timestamp"]


def test_collect_all_cpu_timeout(collector_fakes, monkeypatch):
    collector.invalidate_collect_cache()
    monkeypatch.setattr(
        "core.collector.ThreadPoolExecutor",
        _fake_thread_pool(exc_cpu=TimeoutError("cpu timeout")),
    )
    before = collector.get_collect_metrics()["timeout_count"]
    snapshot = collector.collect_all()
    assert "cpu" in snapshot
    assert collector.get_collect_metrics()["timeout_count"] > before


def test_collect_all_io_timeout(collector_fakes, monkeypatch):
    collector.invalidate_collect_cache()
    monkeypatch.setattr(
        "core.collector.ThreadPoolExecutor",
        _fake_thread_pool(exc_io=TimeoutError("io timeout")),
    )
    before = collector.get_collect_metrics()["timeout_count"]
    snapshot = collector.collect_all()
    assert "memory" in snapshot
    assert collector.get_collect_metrics()["timeout_count"] > before


def test_collect_all_io_exception(collector_fakes, monkeypatch):
    collector.invalidate_collect_cache()
    monkeypatch.setattr(
        "core.collector.ThreadPoolExecutor",
        _fake_thread_pool(exc_io=RuntimeError("io err")),
    )
    snapshot = collector.collect_all()
    assert "network" in snapshot


def test_collect_aliases(collector_fakes, monkeypatch):
    monkeypatch.setattr("core.collector.ThreadPoolExecutor", _fake_thread_pool())
    assert "timestamp" in collector.collect_host_metrics()
    assert "timestamp" in collector.collect_system_metrics()
    assert "timestamp" in collector.collect_process_metrics()
    assert "timestamp" in collector.collect_network_metrics()
