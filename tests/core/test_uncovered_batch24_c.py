# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.metrics_converter,
core.data_lineage, core.processing.l3.causal_graph, core.macos_collector
and core.error_codes.manager.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config
import core.error_codes.manager as error_codes_manager
import core.macos_collector as macos_collector
import core.metrics_converter as metrics_converter
import core.processing.l3.causal_graph as causal_graph_module
from core.data_lineage import (
    DataLineageManager,
    EntityType,
    RelationshipType,
    create_data_lineage_manager,
)

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.metrics_converter
# -----------------------------------------------------------------------------

def test_sqlite_to_prometheus_basic_and_timestamp():
    line = metrics_converter.MetricsConverter.sqlite_to_prometheus(
        "cpu.usage", 42.0, {"host": "h1"}
    )
    assert line == 'cpu_usage{host="h1"} 42.0\n'

    line_ts = metrics_converter.MetricsConverter.sqlite_to_prometheus(
        "cpu.usage", 42.0, {"host": "h1"}, timestamp=1_700_000_000
    )
    parts = line_ts.split()
    assert parts[0] == 'cpu_usage{host="h1"}'
    assert parts[1] == "42.0"
    assert parts[2] == str(1_700_000_000_000)


def test_batch_sqlite_to_prometheus():
    metrics = [
        {"name": "a.b", "value": 1.0, "labels": {"x": "1"}, "timestamp": 1_000},
        {"name": "c-d", "value": 2.0, "labels": {}},
    ]
    result = metrics_converter.MetricsConverter.batch_sqlite_to_prometheus(metrics)
    assert "a_b" in result
    assert "c_d" in result
    assert result.count("\n") == 2


def test_sanitize_metric_name():
    assert metrics_converter.MetricsConverter.sanitize_metric_name("metric-name") == "metric_name"
    assert metrics_converter.MetricsConverter.sanitize_metric_name("123_metric") == "_123_metric"
    assert metrics_converter.MetricsConverter.sanitize_metric_name("valid_metric:1") == "valid_metric:1"
    assert metrics_converter.MetricsConverter.sanitize_metric_name("") == ""


def test_format_labels_and_escape():
    formatted = metrics_converter.MetricsConverter.format_labels({"host": "my-host", "path": 'a"b\\c'})
    assert 'host="my-host"' in formatted
    assert 'path="a\\"b\\\\c"' in formatted
    assert metrics_converter.MetricsConverter.format_labels({}) == ""


def test_system_snapshot_to_prometheus_all_sections():
    snapshot = {
        "cpu": {"usage_percent": 50.0, "per_core": [10.0, 20.0]},
        "memory": {"usage_percent": 60.0, "total_gb": 16.0, "used_gb": 8.0},
        "disk": {"usage_percent": 70.0, "total_gb": 512.0, "used_gb": 200.0},
        "network": {"rx_bytes": 1024, "tx_bytes": 2048},
    }
    result = metrics_converter.MetricsConverter.system_snapshot_to_prometheus(snapshot)
    assert "aiops_cpu_usage_percent" in result
    assert "aiops_cpu_core_usage_percent" in result
    assert "aiops_memory_usage_percent" in result
    assert "aiops_memory_total_gb" in result
    assert "aiops_memory_used_gb" in result
    assert "aiops_disk_usage_percent" in result
    assert "aiops_network_rx_bytes" in result
    assert "aiops_network_tx_bytes" in result


def test_system_snapshot_empty():
    assert metrics_converter.MetricsConverter.system_snapshot_to_prometheus({}) == ""


def test_prometheus_to_sqlite_parsing_and_errors():
    parsed = metrics_converter.MetricsConverter.prometheus_to_sqlite(
        'metric{host="h1"} 3.14 1700000000000'
    )
    assert parsed["name"] == "metric"
    assert parsed["value"] == 3.14
    assert parsed["labels"] == {"host": "h1"}
    assert parsed["timestamp"] == 1_700_000_000

    parsed_no_labels = metrics_converter.MetricsConverter.prometheus_to_sqlite("metric 2.5")
    assert parsed_no_labels["name"] == "metric"
    assert parsed_no_labels["labels"] == {}
    assert parsed_no_labels["timestamp"] is None

    assert metrics_converter.MetricsConverter.prometheus_to_sqlite("") is None
    assert metrics_converter.MetricsConverter.prometheus_to_sqlite("only_name") is None


# -----------------------------------------------------------------------------
# core.data_lineage
# -----------------------------------------------------------------------------

@pytest.fixture
def lineage_manager():
    return DataLineageManager(storage=None, config={"enabled": True})


@pytest.fixture
def lineage_manager_with_storage():
    storage = MagicMock()
    storage.load.return_value = {}
    storage.save.return_value = None
    return DataLineageManager(storage=storage, config={})


def test_entity_dataclass_and_to_dict():
    from core.data_lineage import Entity

    entity = Entity(
        id="e1",
        name="dataset",
        entity_type=EntityType.DATASET,
        description="desc",
        properties={"k": "v"},
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    d = entity.to_dict()
    assert d["id"] == "e1"
    assert d["entity_type"] == "dataset"
    assert d["owner"] is None
    assert d["tags"] == []


def test_relationship_and_event_to_dict():
    from core.data_lineage import LineageEvent, Relationship

    rel = Relationship(
        id="r1",
        source_id="a",
        target_id="b",
        relationship_type=RelationshipType.UPSTREAM,
        properties={},
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert rel.to_dict()["relationship_type"] == "upstream"

    event = LineageEvent(
        id="ev1",
        entity_id="a",
        event_type="created",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        properties={},
    )
    assert "created" == event.to_dict()["event_type"]


def test_register_and_get_entity(lineage_manager):
    entity = lineage_manager.register_entity(
        "sales_db",
        EntityType.DATASET,
        "Sales database",
        properties={"owner": "data-team"},
        owner="data-team",
        tags={"critical"},
    )
    assert entity.name == "sales_db"
    assert entity.tags == {"critical"}

    fetched = lineage_manager.get_entity(entity.id)
    assert fetched["name"] == "sales_db"

    by_name = lineage_manager.get_entity_by_name("sales_db")
    assert by_name["id"] == entity.id


def test_update_and_delete_entity(lineage_manager):
    entity = lineage_manager.register_entity("tmp", EntityType.JOB, "tmp job")
    assert lineage_manager.update_entity(
        entity.id, name="renamed", description="new desc", properties={"p": 1}, tags={"t"}
    )
    updated = lineage_manager.get_entity(entity.id)
    assert updated["name"] == "renamed"
    assert updated["tags"] == ["t"]

    assert lineage_manager.update_entity("missing", name="x") is False
    assert lineage_manager.delete_entity(entity.id) is True
    assert lineage_manager.delete_entity(entity.id) is False


def test_relationship_management(lineage_manager):
    a = lineage_manager.register_entity("a", EntityType.DATASET, "a")
    b = lineage_manager.register_entity("b", EntityType.DATASET, "b")
    rel = lineage_manager.add_relationship(a.id, b.id, RelationshipType.UPSTREAM)
    assert rel.source_id == a.id

    rels = lineage_manager.get_relationships(a.id)
    assert len(rels) == 1

    assert lineage_manager.get_upstream(b.id)[0]["id"] == a.id
    assert lineage_manager.get_downstream(a.id)[0]["id"] == b.id

    assert lineage_manager.remove_relationship(rel.id) is True
    assert lineage_manager.remove_relationship(rel.id) is False

    with pytest.raises(ValueError):
        lineage_manager.add_relationship("missing", b.id, RelationshipType.DOWNSTREAM)


def test_list_and_search_entities(lineage_manager):
    e1 = lineage_manager.register_entity("alpha", EntityType.DATASET, "alpha dataset", owner="o1")
    e2 = lineage_manager.register_entity("beta", EntityType.JOB, "beta job", owner="o2")
    _ = lineage_manager.register_entity("gamma", EntityType.SERVICE, "gamma service", owner="o1", tags={"t1"})

    all_entities = lineage_manager.list_entities()
    assert len(all_entities) == 3

    datasets = lineage_manager.list_entities(entity_type=EntityType.DATASET)
    assert len(datasets) == 1

    by_owner = lineage_manager.list_entities(owner="o1")
    assert len(by_owner) == 2

    by_tags = lineage_manager.list_entities(tags={"t1"})
    assert len(by_tags) == 1

    found = lineage_manager.search_entities("alpha")
    assert len(found) == 1
    assert lineage_manager.search_entities("xyz") == []


def test_analyze_impact_and_lineage(lineage_manager):
    a = lineage_manager.register_entity("a", EntityType.DATASET, "root")
    b = lineage_manager.register_entity("b", EntityType.JOB, "job")
    c = lineage_manager.register_entity("c", EntityType.PIPELINE, "pipeline")
    rel_ab = lineage_manager.add_relationship(a.id, b.id, RelationshipType.PRODUCES)
    _ = lineage_manager.add_relationship(b.id, c.id, RelationshipType.PRODUCES)

    impact = lineage_manager.analyze_impact(a.id)
    assert impact["direct_impact"] == 1
    assert len(impact["affected_entities"]) == 1

    graph = lineage_manager.get_lineage(a.id, depth=2)
    assert graph["entity"]["id"] == a.id
    assert len(graph["downstream"]) == 1

    events = lineage_manager.get_events(a.id)
    assert len(events) >= 1


def test_statistics_and_event_pruning(lineage_manager):
    for i in range(1002):
        lineage_manager._log_event("e", "tick", {"i": i})
    stats = lineage_manager.get_statistics()
    assert stats["total_entities"] == 0
    assert stats["total_relationships"] == 0
    assert stats["total_events"] == 1000
    assert lineage_manager._events[0].properties["i"] == 2


def test_storage_load_and_save(lineage_manager_with_storage):
    storage = lineage_manager_with_storage.storage
    now = datetime.now().isoformat()
    storage.load.side_effect = [
        {
            "e1": {
                "id": "e1",
                "name": "stored",
                "entity_type": "dataset",
                "description": "d",
                "properties": {},
                "created_at": now,
                "updated_at": now,
                "owner": None,
                "tags": [],
            }
        },
        {
            "r1": {
                "id": "r1",
                "source_id": "e1",
                "target_id": "e1",
                "relationship_type": "upstream",
                "properties": {},
                "created_at": now,
            }
        },
    ]
    assert lineage_manager_with_storage.initialize() is True
    assert len(lineage_manager_with_storage._entities) == 1
    assert len(lineage_manager_with_storage._relationships) == 1
    assert storage.save.called is False  # no save during load

    lineage_manager_with_storage.register_entity("new", EntityType.JOB, "new")
    assert storage.save.called is True


def test_initialize_storage_failure(monkeypatch):
    def _bad_load(self):
        raise RuntimeError("load failed")

    monkeypatch.setattr(DataLineageManager, "_load_from_storage", _bad_load)
    manager = DataLineageManager(storage=MagicMock(), config={})
    assert manager.initialize() is False


def test_create_data_lineage_manager_failure(monkeypatch):
    monkeypatch.setattr(
        "core.data_lineage.DataLineageManager.initialize", lambda self: False
    )
    assert create_data_lineage_manager() is None


# -----------------------------------------------------------------------------
# core.processing.l3.causal_graph
# -----------------------------------------------------------------------------

def test_causal_node_relationships():
    node = causal_graph_module.CausalNode("n1", "Node 1", "metric")
    node.add_child("n2")
    node.add_parent("n0")
    assert "n2" in node.children
    assert "n0" in node.parents


def test_causal_graph_add_and_query():
    graph = causal_graph_module.CausalGraph(config={"threshold": 0.2})
    n1 = causal_graph_module.CausalNode("n1", "CPU", "metric")
    n2 = causal_graph_module.CausalNode("n2", "Memory", "metric")
    graph.add_node(n1)
    graph.add_node(n2)
    assert graph.get_node("n1") is n1
    assert graph.get_children("n1") == []

    edge = causal_graph_module.CausalEdgeClass("n1", "n2", causal_graph_module.CausalStrength.STRONG)
    graph.add_edge(edge)
    children = graph.get_children("n1")
    assert len(children) == 1
    assert graph.get_parents("n2")[0].id == "n1"


def test_find_root_causes():
    graph = causal_graph_module.CausalGraph(config={})
    n1 = causal_graph_module.CausalNode("root", "Root", "metric")
    n2 = causal_graph_module.CausalNode("mid", "Mid", "metric")
    n3 = causal_graph_module.CausalNode("leaf", "Leaf", "metric")
    for n in (n1, n2, n3):
        graph.add_node(n)
    graph.add_edge(causal_graph_module.CausalEdgeClass("root", "mid", causal_graph_module.CausalStrength.STRONG))
    graph.add_edge(causal_graph_module.CausalEdgeClass("mid", "leaf", causal_graph_module.CausalStrength.MODERATE))
    n3.is_anomaly = True
    causes = graph.find_root_causes("leaf", max_depth=5)
    assert len(causes) >= 1


def test_propagate_anomaly():
    graph = causal_graph_module.CausalGraph(config={})
    n1 = causal_graph_module.CausalNode("src", "Source", "metric")
    n2 = causal_graph_module.CausalNode("dst", "Dest", "metric")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(causal_graph_module.CausalEdgeClass("src", "dst", 0.8))
    result = graph.propagate_anomaly("src", 0.9)
    assert result["source_node"] == "src"
    assert result["affected_count"] == 2


def test_analyze_impact():
    graph = causal_graph_module.CausalGraph(config={})
    n1 = causal_graph_module.CausalNode("db", "DB", "service")
    n2 = causal_graph_module.CausalNode("app", "App", "service")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(causal_graph_module.CausalEdgeClass("db", "app", causal_graph_module.CausalStrength.MODERATE))
    impact = graph.analyze_impact("db", impact_threshold=0.2)
    assert impact["impacted_count"] == 2


def test_build_system_topology(monkeypatch):
    monkeypatch.setattr(config, "LINUX_HOSTS", {"hosts": [{"host": "linux1"}, {"hostname": "linux2"}]})
    monkeypatch.setattr(config, "K8S_HOSTS", [{"host": "k8s1"}, {"name": "k8s2"}])
    monkeypatch.setattr(config, "DOCKER_HOSTS", [{"host": "docker1"}])
    monkeypatch.setattr(config, "WIN_HOSTS", [{"host": "win1"}])

    graph = causal_graph_module.CausalGraph(config={})
    graph.build_system_topology()
    status = graph.get_status()
    assert status["initialized"] is True
    assert status["node_count"] > 4
    assert status["edge_count"] >= 4


def test_get_causal_graph_singleton():
    graph = causal_graph_module.init_causal_graph({"test": True})
    assert causal_graph_module.get_causal_graph() is graph
    # Reset for other tests is not strictly necessary but avoids singleton leakage
    import core.processing.l3.causal_graph as mod
    mod._causal_graph = None


# -----------------------------------------------------------------------------
# core.macos_collector
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_subprocess_factory(monkeypatch):
    async def _factory(stdout=b"ok", stderr=b"", returncode=0, raise_=None):
        proc = AsyncMock()
        if raise_:
            proc.communicate = AsyncMock(side_effect=raise_)
        else:
            proc.communicate = AsyncMock(return_value=(stdout, stderr))
        proc.returncode = returncode
        monkeypatch.setattr(asyncio, "create_subprocess_shell", AsyncMock(return_value=proc))
    return _factory


@pytest.fixture
def mac_config(monkeypatch):
    monkeypatch.setattr(config, "MAC_HOSTS", [{"host": "localhost"}], raising=False)


def test_run_command_remote_not_supported():
    result = asyncio.run(macos_collector._run_command("remote-host", "whoami"))
    assert "not supported" in result["stderr"]
    assert result["stdout"] == ""


def test_run_command_success(mock_subprocess_factory):
    asyncio.run(mock_subprocess_factory(stdout=b"user\n", stderr=b""))
    result = asyncio.run(macos_collector._run_command("localhost", "whoami"))
    assert result["stdout"] == "user\n"
    assert result["stderr"] == ""


def test_run_command_failure_and_timeout(mock_subprocess_factory):
    asyncio.run(mock_subprocess_factory(raise_=asyncio.TimeoutError("timed out")))
    result = asyncio.run(macos_collector._run_command("localhost", "sleep 10"))
    assert "timed out" in result["stderr"]

    asyncio.run(mock_subprocess_factory(raise_=OSError("boom")))
    result = asyncio.run(macos_collector._run_command("localhost", "cmd"))
    assert "boom" in result["stderr"]


def test_collect_macos_metrics_not_darwin(monkeypatch, mac_config):
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(macos_collector, "psutil", None)
    result = asyncio.run(macos_collector.collect_macos_metrics(["localhost"]))
    assert "localhost" in result
    assert "Darwin" in result["localhost"]["error"]


def test_collect_macos_metrics_psutil_missing(monkeypatch, mac_config):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr(macos_collector, "psutil", None)
    result = asyncio.run(macos_collector.collect_macos_metrics(["localhost"]))
    assert "psutil is not installed" in result["localhost"]["error"]


def test_collect_macos_metrics_success(monkeypatch, mac_config):
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent = lambda interval=None: 12.5
    fake_psutil.virtual_memory = lambda: MagicMock(percent=45.0)
    fake_psutil.disk_usage = lambda path: MagicMock(percent=67.0)
    monkeypatch.setattr(macos_collector, "psutil", fake_psutil)

    result = asyncio.run(macos_collector.collect_macos_metrics(["localhost"]))
    assert result["localhost"]["status"] == "ok"
    assert result["localhost"]["cpu"] == 12.5
    assert result["localhost"]["mem"] == 45.0
    assert result["localhost"]["disk"] == 67.0


def test_collect_macos_metrics_remote_host_rejected(mac_config):
    result = asyncio.run(macos_collector.collect_macos_metrics(["remote"]))
    assert "only supported on localhost" in result["remote"]["error"]


# -----------------------------------------------------------------------------
# core.error_codes.manager
# -----------------------------------------------------------------------------

def test_error_code_manager_basic():
    manager = error_codes_manager.ErrorCodeManager()
    assert manager.get_message("01_01_0001") == "Parameter validation failed"
    assert manager.get_message("01_01_0001", language="zh") == "参数验证失败"
    assert manager.get_message("unknown") == "Unknown error"

    manager.add_message("99_99_0001", "en", "Custom error")
    manager.add_message("99_99_0001", "zh", "自定义错误")
    assert manager.get_message("99_99_0001", language="fr") == "Custom error"


def test_error_code_manager_get_methods():
    manager = error_codes_manager.ErrorCodeManager()
    all_codes = manager.get_all_error_codes()
    assert "01_01_0001" in all_codes
    assert "01_02_0001" in all_codes

    messages = manager.get_all_messages("01_01_0001")
    assert "en" in messages
    assert "zh" in messages
    assert manager.get_all_messages("missing") == {}


def test_error_code_helpers():
    assert error_codes_manager.get_error_message("01_01_0001", "zh") == "参数验证失败"
    assert error_codes_manager.get_error_code_manager() is error_codes_manager._error_code_manager
