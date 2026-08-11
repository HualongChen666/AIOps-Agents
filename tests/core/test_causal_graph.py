# -*- coding: utf-8 -*-
"""Tests for core/processing/l3/causal_graph.py."""

from core.processing.l3.causal_graph import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalStrength,
    get_causal_graph,
    init_causal_graph,
)


def test_node_and_edge():
    graph = CausalGraph()
    node_a = CausalNode("a", "A")
    node_b = CausalNode("b", "B")
    graph.add_node(node_a)
    graph.add_node(node_b)
    edge = CausalEdge("a", "b", CausalStrength.STRONG)
    graph.add_edge(edge)
    assert graph.get_node("a").id == "a"
    assert graph.get_children("a")[0].id == "b"
    assert graph.get_parents("b")[0].id == "a"


def test_find_root_causes_and_propagate():
    graph = CausalGraph()
    a = CausalNode("a", "A")
    b = CausalNode("b", "B")
    c = CausalNode("c", "C")
    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(c)
    graph.add_edge(CausalEdge("a", "b", 0.9))
    graph.add_edge(CausalEdge("b", "c", 0.8))
    roots = graph.find_root_causes("c")
    assert any(r["node_id"] == "a" for r in roots)
    impact = graph.propagate_anomaly("a", 1.0)
    assert "affected_nodes" in impact
    analysis = graph.analyze_impact("a")
    assert "impacted_nodes" in analysis


def test_build_system_topology_and_status():
    graph = CausalGraph()
    graph.build_system_topology()
    assert len(graph.nodes) > 0
    status = graph.get_status()
    assert "node_count" in status
    assert status["initialized"] is True


def test_factory_functions():
    init_causal_graph({})
    graph = get_causal_graph()
    assert isinstance(graph, CausalGraph)
