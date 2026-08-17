# -*- coding: utf-8 -*-
"""Real branch-coverage tests for modules/apm/dependency_analyzer.py.

These tests exercise the APM dependency analyzer using real class
instances and in-memory data. No mocks or monkeypatching are used.
"""

import json

import pytest

from modules.apm.dependency_analyzer import (
    DependencyAnalyzer,
    DependencyDiscoverer,
    DependencyEdge,
    DependencyHealthAssessor,
    DependencyTopology,
    DependencyType,
    HealthStatus,
    ServiceNode,
    TopologyVisualizer,
    create_dependency_analyzer,
)


def _build_cycle_topology() -> DependencyTopology:
    """Return a topology with a simple B<->C cycle."""
    topology = DependencyTopology()
    for node_id in ("A", "B", "C"):
        topology.add_node(ServiceNode(id=node_id, name=f"Service {node_id}"))
    topology.add_edge(DependencyEdge("A", "B", DependencyType.SYNC, weight=1.0))
    topology.add_edge(DependencyEdge("B", "C", DependencyType.SYNC, weight=1.0))
    topology.add_edge(DependencyEdge("C", "B", DependencyType.SYNC, weight=1.0))
    return topology


def test_trace_discovery_all_branches():
    """Trace discovery hits sync, async, external, and duplicate-node branches."""
    analyzer = DependencyAnalyzer()

    trace_data = [
        {
            "spans": [
                {"service_id": "svc1", "service_name": "Service 1"},
                {"service_id": "svc2", "service_name": "Service 2", "kind": "producer"},
                {"service_id": "svc1", "service_name": "Service 1 dup", "kind": "client"},
            ]
        },
        {
            "spans": [
                {"service_id": "svc3", "service_name": "Service 3"},
                {"service_id": "svc4", "service_name": "Service 4"},
            ]
        },
    ]

    topology = analyzer.discover_topology("trace", trace_data=trace_data)

    assert topology.nodes["svc1"].name == "Service 1"  # first add wins
    assert topology.nodes["svc2"].name == "Service 2"
    assert topology.nodes["svc3"].name == "Service 3"

    edges = {(e.source, e.target, e.dependency_type) for e in topology.edges}
    assert ("svc1", "svc2", DependencyType.ASYNC) in edges
    assert ("svc2", "svc1", DependencyType.EXTERNAL_API) in edges
    assert ("svc3", "svc4", DependencyType.SYNC) in edges

    analyzer.get_health_report()


def test_config_discovery_existing_dep_and_invalid_type():
    """Config discovery: duplicate dep node, invalid dep type falls back to sync."""
    analyzer = DependencyAnalyzer()
    config_data = {
        "services": [
            {
                "id": "web",
                "name": "Web",
                "dependencies": [
                    {"id": "api", "name": "API", "type": "sync"},
                    {"id": "db", "name": "Database", "type": "database"},
                    {"id": "api", "name": "API duplicate", "type": "message_queue"},
                    {"id": "cache", "name": "Cache", "type": "not_a_type"},
                ],
            },
            {
                "id": "api",
                "name": "API",
                "dependencies": [
                    {"id": "cache", "name": "Cache", "type": "cache"},
                ],
            },
        ],
    }

    topology = analyzer.discover_topology("config", config_data=config_data)

    assert topology.nodes["web"].name == "Web"
    assert topology.nodes["api"].name == "API"  # first add as explicit service
    assert topology.nodes["cache"].name == "Cache"  # first add from bad-type dep
    assert len(topology.edges) == 5  # duplicate dep still creates another edge

    web_api_types = {
        e.dependency_type for e in topology.edges if e.source == "web" and e.target == "api"
    }
    assert DependencyType.SYNC in web_api_types
    assert DependencyType.MESSAGE_QUEUE in web_api_types
    other = {(e.source, e.target): e.dependency_type for e in topology.edges}
    assert other[("web", "db")] == DependencyType.DATABASE
    assert other[("web", "cache")] == DependencyType.SYNC  # fallback
    assert other[("api", "cache")] == DependencyType.CACHE


def test_metrics_discovery_existing_nodes_and_zero_count():
    """Metrics discovery: zero-count skip and previously-added source/target."""
    discoverer = DependencyDiscoverer()
    metrics_data = {
        "call_relationships": [
            {"source": "a", "target": "b", "call_count": 0},
            {"source": "a", "target": "b", "call_count": 5},
            {"source": "a", "target": "c", "call_count": 3},
            {"source": "d", "target": "b", "call_count": 2},
        ],
    }

    topology = discoverer.discover("metrics", metrics_data=metrics_data)

    assert "a" in topology.nodes
    assert "b" in topology.nodes
    assert "c" in topology.nodes
    assert "d" in topology.nodes
    assert len(topology.edges) == 3


def test_graph_traversal_cycles_and_missing_nodes():
    """Recursive graph traversal handles cycles and missing node ids."""
    topology = _build_cycle_topology()

    assert topology.get_dependencies("missing") == set()
    assert topology.get_dependents("missing") == set()

    # Forward traversal: A -> B -> C, C -> B already seen
    all_deps = topology.get_all_dependencies("A")
    assert all_deps == {"B", "C"}

    # Reverse traversal: C -> B -> A; the B<->C cycle causes C to re-enter
    all_dependents = topology.get_all_dependents("C")
    assert all_dependents == {"B", "A", "C"}


def test_critical_path_branches():
    """Dijkstra critical path: visited neighbor, non-shortcut, same start/end, no path."""
    topology = DependencyTopology()
    for node_id in ("A", "B", "C", "D", "E"):
        topology.add_node(ServiceNode(id=node_id, name=f"Service {node_id}"))

    # Standard path A -> B -> C
    topology.add_edge(DependencyEdge("A", "B", DependencyType.SYNC, weight=1.0))
    topology.add_edge(DependencyEdge("B", "C", DependencyType.SYNC, weight=1.0))
    # Route A -> C via B should be selected, but include a longer A->D->C to hit the
    # `if new_distance < distances[neighbor]` false branch.
    topology.add_edge(DependencyEdge("A", "D", DependencyType.SYNC, weight=1.0))
    topology.add_edge(DependencyEdge("D", "C", DependencyType.SYNC, weight=1.0))
    # E is unreachable from A

    assert topology.find_critical_path("A", "C") == ["A", "B", "C"]
    assert topology.find_critical_path("A", "A") == ["A"]
    assert topology.find_critical_path("A", "E") == []

    # Visited-neighbor branch: D is selected before C, so C->D hits `continue`
    visited = DependencyTopology()
    for node_id in ("A", "B", "C", "D", "E"):
        visited.add_node(ServiceNode(id=node_id, name=f"Service {node_id}"))
    visited.add_edge(DependencyEdge("A", "B", DependencyType.SYNC, weight=1.0))
    visited.add_edge(DependencyEdge("A", "C", DependencyType.SYNC, weight=1.0))
    visited.add_edge(DependencyEdge("A", "D", DependencyType.SYNC, weight=0.0))
    visited.add_edge(DependencyEdge("C", "D", DependencyType.SYNC, weight=0.0))
    visited.add_edge(DependencyEdge("C", "E", DependencyType.SYNC, weight=1.0))
    assert visited.find_critical_path("A", "E") == ["A", "C", "E"]

    # No shortcut: A -> B (2), A -> C (1), C -> B (1); B first reached via A, not updated
    shortcut = DependencyTopology()
    for node_id in ("A", "B", "C"):
        shortcut.add_node(ServiceNode(id=node_id, name=f"Service {node_id}"))
    shortcut.add_edge(DependencyEdge("A", "B", DependencyType.SYNC, weight=2.0))
    shortcut.add_edge(DependencyEdge("A", "C", DependencyType.SYNC, weight=1.0))
    shortcut.add_edge(DependencyEdge("C", "B", DependencyType.SYNC, weight=1.0))
    assert shortcut.find_critical_path("A", "B") == ["A", "B"]

    # Empty topology: the Dijkstra loop is never entered
    assert DependencyTopology().find_critical_path("A", "B") == []


def test_health_assessor_all_branches():
    """Health assessment covers healthy, degraded, unhealthy and critical-node ranking."""
    topology = _build_cycle_topology()
    assessor = DependencyHealthAssessor(topology)

    assert assessor.assess_node_health("x", {"error_rate": 0.1}) == HealthStatus.UNHEALTHY
    assert assessor.assess_node_health("x", {"availability": 0.9}) == HealthStatus.UNHEALTHY
    assert (
        assessor.assess_node_health("x", {"error_rate": 0.02, "latency": 1200})
        == HealthStatus.DEGRADED
    )
    assert (
        assessor.assess_node_health("x", {"error_rate": 0.005, "latency": 500})
        == HealthStatus.HEALTHY
    )

    # Edge health: error_rate thresholds
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, error_rate=0.1)
        )
        == HealthStatus.UNHEALTHY
    )
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, error_rate=0.03)
        )
        == HealthStatus.DEGRADED
    )
    # Latency thresholds
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, latency=6000)
        )
        == HealthStatus.UNHEALTHY
    )
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, latency=2000)
        )
        == HealthStatus.DEGRADED
    )
    # Low error_rate falls through to latency checks, then both fall through to HEALTHY
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, error_rate=0.005, latency=100)
        )
        == HealthStatus.HEALTHY
    )
    # Low error_rate with no latency falls straight through to HEALTHY
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, error_rate=0.005)
        )
        == HealthStatus.HEALTHY
    )
    assert (
        assessor.assess_dependency_health(
            DependencyEdge("A", "B", DependencyType.SYNC, latency=100)
        )
        == HealthStatus.HEALTHY
    )

    # Critical-node ranking (root-cause-style most-dependent ordering)
    critical = assessor.identify_critical_nodes()
    assert critical[0] == "B"  # A and C both depend on B
    assert set(critical) == {"B", "A", "C"}


def test_analyzer_uninitialized_errors():
    """Calling analysis methods before discovery raises RuntimeError."""
    analyzer = DependencyAnalyzer()

    with pytest.raises(RuntimeError, match="Topology not discovered"):
        analyzer.analyze_dependencies("A")

    with pytest.raises(RuntimeError, match="Topology not discovered"):
        analyzer.get_critical_path("A", "B")

    with pytest.raises(RuntimeError, match="Topology not discovered"):
        analyzer.get_health_report()


def test_discoverer_unknown_method():
    """Unknown discovery method raises ValueError."""
    with pytest.raises(ValueError, match="Unknown discovery method"):
        DependencyDiscoverer().discover("unknown")


def test_topology_visualization_and_json():
    """NetworkX conversion, JSON roundtrip, and matplotlib fallback."""
    topology = _build_cycle_topology()

    # NetworkX conversion (real networkx, no mock)
    nx_graph = TopologyVisualizer.to_networkx(topology)
    assert set(nx_graph.nodes()) == {"A", "B", "C"}
    assert nx_graph.has_edge("A", "B")
    assert nx_graph.has_edge("B", "C")
    assert nx_graph.has_edge("C", "B")

    # JSON roundtrip
    json_str = TopologyVisualizer.to_json(topology)
    loaded = TopologyVisualizer.from_json(json_str)
    assert set(loaded.nodes.keys()) == {"A", "B", "C"}
    assert len(loaded.edges) == 3

    data = json.loads(json_str)
    assert data["nodes"][0]["health"] in {"healthy", "degraded", "unhealthy", "unknown"}

    # Plot gracefully falls back to an ImportError when matplotlib is missing
    with pytest.raises(ImportError, match="Matplotlib and NetworkX are required"):
        TopologyVisualizer.plot(topology)


def test_analyzer_factory_and_full_workflow():
    """Factory creates a real analyzer and the public API works end-to-end."""
    analyzer = create_dependency_analyzer()
    config_data = {
        "services": [
            {"id": "frontend", "name": "Frontend", "dependencies": []},
            {
                "id": "backend",
                "name": "Backend",
                "dependencies": [{"id": "frontend", "type": "sync"}],
            },
        ]
    }
    topology = analyzer.discover_topology("config", config_data=config_data)

    assert len(topology.nodes) == 2
    assert topology.nodes["backend"].name == "Backend"

    analysis = analyzer.analyze_dependencies("backend")
    assert analysis["direct_dependencies"] == ["frontend"]
    assert analysis["dependency_count"] == 1

    path = analyzer.get_critical_path("backend", "frontend")
    assert path == ["backend", "frontend"]

    report = analyzer.get_health_report()
    assert report["total_nodes"] == 2
    assert "frontend" in report["critical_nodes"]
