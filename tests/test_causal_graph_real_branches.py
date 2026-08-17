# -*- coding: utf-8 -*-
"""Real-data branch tests for core/processing/l3/causal_graph.py.

These tests build real causal graphs from sample alert/metric data and exercise
all branch paths in CausalGraph without using mocks.
"""

import json
import tempfile

import pytest

import config as config_module
from core.processing.l3.causal_graph import (
    CAUSAL_ANALYSIS_AVAILABLE,
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalStrength,
    _FallbackCausalEdge,
    _FallbackCausalStrength,
    get_causal_graph,
    init_causal_graph,
)


def _sample_metric_alert_graph():
    """Build a realistic causal graph from sample alert/metric data."""
    graph = CausalGraph(config={"disable_full_causal": True})
    nodes = [
        CausalNode("cpu", "CPU Usage", "metric"),
        CausalNode("memory", "Memory Usage", "metric"),
        CausalNode("disk", "Disk I/O", "metric"),
        CausalNode("network", "Network I/O", "metric"),
        CausalNode("db", "Database", "service"),
        CausalNode("cache", "Cache", "service"),
        CausalNode("api", "API Gateway", "service"),
        CausalNode("app", "Application", "service"),
    ]
    for node in nodes:
        graph.add_node(node)

    # Causal links: infrastructure -> backend -> frontend
    edges = [
        CausalEdge("cpu", "db", CausalStrength.STRONG),
        CausalEdge("memory", "db", CausalStrength.MODERATE),
        CausalEdge("disk", "db", CausalStrength.STRONG),
        CausalEdge("network", "api", CausalStrength.STRONG),
        CausalEdge("db", "app", CausalStrength.STRONG),
        CausalEdge("cache", "app", CausalStrength.MODERATE),
        CausalEdge("api", "app", CausalStrength.STRONG),
    ]
    for edge in edges:
        graph.add_edge(edge)
    return graph


def test_fallback_causal_edge_strength_conversion():
    """_FallbackCausalEdge converts numeric strengths into the fallback enum."""
    strong = _FallbackCausalEdge("a", "b", 0.8)
    moderate = _FallbackCausalEdge("a", "c", 0.5)
    weak = _FallbackCausalEdge("a", "d", 0.1)
    enum_edge = _FallbackCausalEdge("a", "e", _FallbackCausalStrength.MODERATE)

    assert strong.strength is _FallbackCausalStrength.STRONG
    assert moderate.strength is _FallbackCausalStrength.MODERATE
    assert weak.strength is _FallbackCausalStrength.WEAK
    assert enum_edge.strength is _FallbackCausalStrength.MODERATE


def test_graph_construction_and_node_relationships():
    """Real graph built from metric/alert data has correct topology."""
    graph = _sample_metric_alert_graph()
    assert graph.get_node("app").name == "Application"
    assert {c.id for c in graph.get_children("db")} == {"app"}
    assert {p.id for p in graph.get_parents("app")} == {"db", "cache", "api"}
    assert {p.id for p in graph.get_parents("api")} == {"network"}


def test_add_edge_missing_node_branches():
    """Adding edges for missing source and/or target nodes updates only present ends."""
    graph = CausalGraph(config={"disable_full_causal": True})
    graph.add_node(CausalNode("a", "A"))

    # Source exists, target missing -> child added, parent update skipped.
    graph.add_edge(CausalEdge("a", "missing_target"))
    assert "missing_target" in graph.get_node("a").children

    # Source missing, target exists -> child update skipped, parent added.
    graph.add_edge(CausalEdge("missing_source", "a"))
    assert "missing_source" in graph.get_node("a").parents

    # Both missing -> both updates skipped safely.
    graph.add_edge(CausalEdge("missing_both", "missing_both2"))


def test_get_children_and_parents_for_unknown_nodes():
    """get_children/get_parents return empty lists for unknown node ids."""
    graph = CausalGraph(config={"disable_full_causal": True})
    assert graph.get_children("does_not_exist") == []
    assert graph.get_parents("does_not_exist") == []


def test_find_root_causes_with_depth_limit():
    """find_root_causes stops when max_depth is exceeded."""
    graph = CausalGraph(config={"disable_full_causal": True})
    for nid in ("a", "b", "c"):
        graph.add_node(CausalNode(nid, nid.upper()))
    graph.add_edge(CausalEdge("a", "b"))
    graph.add_edge(CausalEdge("b", "c"))

    # With max_depth=1 the traversal cannot reach the real root.
    results = graph.find_root_causes("c", max_depth=1)
    assert results == []


def test_find_root_causes_with_cycle():
    """find_root_causes avoids infinite loops when a cycle is present."""
    graph = CausalGraph(config={"disable_full_causal": True})
    for nid in ("a", "b", "c"):
        graph.add_node(CausalNode(nid, nid.upper()))
    graph.add_edge(CausalEdge("a", "b"))
    graph.add_edge(CausalEdge("b", "c"))
    graph.add_edge(CausalEdge("c", "b"))

    results = graph.find_root_causes("c")
    # 'a' is the only node without parents (root cause).
    assert any(r["node_id"] == "a" for r in results)


def test_find_root_causes_unknown_and_anomaly():
    """find_root_causes handles unknown nodes and anomalous root nodes."""
    graph = _sample_metric_alert_graph()
    assert graph.find_root_causes("not_there") == []

    node = graph.get_node("cpu")
    node.is_anomaly = True
    roots = graph.find_root_causes("cpu")
    assert any(r["node_id"] == "cpu" for r in roots)


def test_edge_strength_mappings_and_invalid_strength():
    """_get_edge_strength maps enums, converts floats, and defaults on errors."""
    graph = CausalGraph(config={"disable_full_causal": True})
    graph.add_node(CausalNode("x", "X"))
    graph.add_node(CausalNode("y", "Y"))

    graph.add_edge(CausalEdge("x", "y", CausalStrength.STRONG))
    assert graph._get_edge_strength("x", "y") == 0.75

    graph.add_edge(CausalEdge("x", "z", CausalStrength.MODERATE))
    assert graph._get_edge_strength("x", "z") == 0.5

    graph.add_edge(CausalEdge("x", "w", 0.25))
    assert graph._get_edge_strength("x", "w") == 0.25

    # Invalid string strength triggers the TypeError/ValueError fallback.
    graph.add_edge(CausalEdge("x", "bad", "not-a-number"))
    assert graph._get_edge_strength("x", "bad") == 0.5

    # Missing edge defaults to 0.5.
    assert graph._get_edge_strength("none", "none") == 0.5


def test_propagate_anomaly_normal_and_low_score():
    """propagate_anomaly tracks downstream impact and stops on weak signals."""
    graph = _sample_metric_alert_graph()
    result = graph.propagate_anomaly("db", 1.0)
    assert result["source_node"] == "db"
    assert any(n["node_id"] == "app" for n in result["affected_nodes"])

    low = graph.propagate_anomaly("db", 0.05)
    assert low["affected_count"] == 0


def test_propagate_anomaly_unknown_and_cycle():
    """propagate_anomaly handles unknown nodes and cycles without looping."""
    graph = CausalGraph(config={"disable_full_causal": True})
    for nid in ("a", "b"):
        graph.add_node(CausalNode(nid, nid.upper()))
    graph.add_edge(CausalEdge("a", "b"))
    graph.add_edge(CausalEdge("b", "a"))

    assert graph.propagate_anomaly("not_there", 1.0)["affected_count"] == 0

    result = graph.propagate_anomaly("a", 1.0)
    assert result["affected_count"] == 2
    # The cycle should not produce a third visit.
    assert len(result["affected_nodes"]) == 2


def test_analyze_impact_threshold_and_unknown():
    """analyze_impact respects threshold and handles missing/weak paths."""
    graph = _sample_metric_alert_graph()
    full = graph.analyze_impact("db", impact_threshold=0.01)
    assert any(n["node_id"] == "app" for n in full["impacted_nodes"])

    # With a high threshold downstream propagation beyond the first hop
    # should be suppressed.
    high = graph.analyze_impact("db", impact_threshold=0.95)
    assert high["impacted_count"] <= 2

    missing = graph.analyze_impact("not_there")
    assert missing["impacted_count"] == 0


def test_analyze_impact_with_cycle():
    """analyze_impact stops when revisiting nodes in cyclic graphs."""
    graph = CausalGraph(config={"disable_full_causal": True})
    for nid in ("a", "b"):
        graph.add_node(CausalNode(nid, nid.upper()))
    graph.add_edge(CausalEdge("a", "b"))
    graph.add_edge(CausalEdge("b", "a"))

    result = graph.analyze_impact("a", impact_threshold=0.1)
    assert result["impacted_count"] == 2


def test_build_system_topology_with_bad_host_entries():
    """build_system_topology skips non-dict host entries and empty host ids."""
    original = {
        "LINUX_HOSTS": getattr(config_module, "LINUX_HOSTS", None),
        "K8S_HOSTS": getattr(config_module, "K8S_HOSTS", None),
        "DOCKER_HOSTS": getattr(config_module, "DOCKER_HOSTS", None),
        "WIN_HOSTS": getattr(config_module, "WIN_HOSTS", None),
    }
    try:
        # LINUX_HOSTS is expected to be a dict with a "hosts" list.
        config_module.LINUX_HOSTS = {
            "hosts": [
                {"host": "linux-01"},
                {"name": ""},  # empty host_id branch
                "not-a-dict",  # non-dict branch
            ]
        }
        config_module.K8S_HOSTS = [
            {"hostname": "k8s-01"},
            "not-a-dict",
        ]
        config_module.DOCKER_HOSTS = [
            {"name": "docker-01"},
            {"host": None},
        ]
        config_module.WIN_HOSTS = [
            {"host": "win-01"},
            {"name": ""},
        ]

        graph = CausalGraph(config={"disable_full_causal": True})
        graph.build_system_topology()

        assert graph.get_node("host:linux-01") is not None
        assert graph.get_node("host:k8s-01") is not None
        assert graph.get_node("host:docker-01") is not None
        assert graph.get_node("host:win-01") is not None
        # Empty-id hosts and non-dict entries were skipped.
        assert "host:" not in graph.nodes
    finally:
        for key, value in original.items():
            setattr(config_module, key, value)


def test_full_causal_initialization_and_disable():
    """CausalGraph initializes full causal components by default and can skip them."""
    if not CAUSAL_ANALYSIS_AVAILABLE:
        pytest.skip("core.causal components are not available in this environment")

    full = CausalGraph()
    assert full._full_causal_graph is not None

    disabled = CausalGraph(config={"disable_full_causal": True})
    assert disabled._full_causal_graph is None


def test_export_import_roundtrip():
    """Export a real graph to JSON and reconstruct it without mocks."""
    graph = _sample_metric_alert_graph()

    data = {
        "nodes": {
            nid: {
                "name": node.name,
                "node_type": node.node_type,
                "value": node.value,
                "timestamp": node.timestamp.isoformat() if node.timestamp else None,
                "anomaly_score": node.anomaly_score,
                "is_anomaly": node.is_anomaly,
                "children": list(node.children),
                "parents": list(node.parents),
            }
            for nid, node in graph.nodes.items()
        },
        "edges": [
            {
                "from": edge.from_var,
                "to": edge.to_var,
                "strength": graph._get_edge_strength(edge.from_var, edge.to_var),
                "lag": getattr(edge, "lag", 0),
                "confidence": getattr(edge, "confidence", 0.5),
            }
            for edge in graph.edges
        ],
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    with open(path) as f:
        loaded = json.load(f)

    restored = CausalGraph(config={"disable_full_causal": True})
    for nid, n in loaded["nodes"].items():
        node = CausalNode(nid, n["name"], n["node_type"])
        node.value = n["value"]
        node.anomaly_score = n["anomaly_score"]
        node.is_anomaly = n["is_anomaly"]
        restored.add_node(node)
    for e in loaded["edges"]:
        restored.add_edge(CausalEdge(e["from"], e["to"], e["strength"]))

    assert set(restored.nodes) == set(graph.nodes)
    assert {e.from_var for e in restored.edges} == {e.from_var for e in graph.edges}


def test_prune_weak_edges():
    """Prune edges below a strength threshold and update node relationship sets."""
    graph = CausalGraph(config={"disable_full_causal": True})
    for nid in ("cpu", "memory", "app"):
        graph.add_node(CausalNode(nid, nid))
    graph.add_edge(CausalEdge("cpu", "app", CausalStrength.STRONG))
    graph.add_edge(CausalEdge("memory", "app", CausalStrength.WEAK))

    threshold = 0.3
    keep = [
        edge
        for edge in graph.edges
        if graph._get_edge_strength(edge.from_var, edge.to_var) >= threshold
    ]
    graph.edges.clear()
    for node in graph.nodes.values():
        node.children.clear()
        node.parents.clear()
    for edge in keep:
        graph.add_edge(edge)

    assert len(graph.edges) == 1
    assert graph.get_node("cpu").id in graph.get_node("app").parents
    assert graph.get_node("memory").id not in graph.get_node("app").parents


def test_factory_functions():
    """init_causal_graph/get_causal_graph form the global singleton correctly."""
    graph = init_causal_graph({"disable_full_causal": True})
    assert get_causal_graph() is graph
