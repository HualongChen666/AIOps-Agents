# -*- coding: utf-8 -*-
"""Core tests for topology microservice."""

from __future__ import annotations

import pytest

from services.topology_service.audit import TopologyAuditStore
from services.topology_service.dependency import DependencyGraph, DependencyModelingEngine
from services.topology_service.discovery import TopologyDiscoveryEngine
from services.topology_service.grpc.client import TopologyRPCClient
from services.topology_service.grpc.server import TopologyRPCServer
from services.topology_service.impact import ImpactAnalyzer
from services.topology_service.realtime import RealtimeTopologyManager
from services.topology_service.saga import TopologySagaOrchestrator
from services.topology_service.schemas import (
    DependencyRequest,
    DiscoveryRequest,
    EdgeType,
    ImpactRequest,
    NodeType,
    ServiceTopology,
    TopologyEdge,
    TopologyNode,
    VisualizationConfig,
)
from services.topology_service.versioning import TopologyVersionManager
from services.topology_service.visualization import TopologyVisualizer


@pytest.mark.asyncio
class TestDiscovery:
    async def test_discover_from_config(self):
        engine = TopologyDiscoveryEngine()
        request = DiscoveryRequest(source="config", scope="all")
        topology = await engine.discover(request)
        assert topology.status.value == "discovered"
        assert len(topology.nodes) > 0
        assert len(topology.edges) > 0

    async def test_discover_specific_scope(self):
        engine = TopologyDiscoveryEngine()
        request = DiscoveryRequest(source="config", scope="ai")
        topology = await engine.discover(request)
        node_ids = {n.node_id for n in topology.nodes}
        assert "ai-router" in node_ids
        assert all(edge.source in node_ids and edge.target in node_ids for edge in topology.edges)

    async def test_batch_discover(self):
        engine = TopologyDiscoveryEngine()
        requests = [
            DiscoveryRequest(source="config", scope="core"),
            DiscoveryRequest(source="config", scope="api"),
        ]
        results = await engine.batch_discover(requests)
        assert len(results) == 2


@pytest.mark.asyncio
class TestDependency:
    async def test_dependency_graph(self):
        topology = ServiceTopology(
            topology_id="test-topo",
            nodes=[
                TopologyNode(node_id="a", name="A", node_type=NodeType.SERVICE),
                TopologyNode(node_id="b", name="B", node_type=NodeType.SERVICE),
            ],
            edges=[TopologyEdge(source="a", target="b", edge_type=EdgeType.CALLS)],
        )
        graph = DependencyGraph()
        graph.load_topology(topology)
        deps = graph.get_dependencies("a")
        assert len(deps) == 1
        dependents = graph.get_dependents("b")
        assert len(dependents) == 1

    async def test_find_all_paths(self):
        topology = ServiceTopology(
            topology_id="test-topo",
            nodes=[
                TopologyNode(node_id="a", name="A"),
                TopologyNode(node_id="b", name="B"),
                TopologyNode(node_id="c", name="C"),
            ],
            edges=[
                TopologyEdge(source="a", target="b"),
                TopologyEdge(source="b", target="c"),
            ],
        )
        graph = DependencyGraph()
        graph.load_topology(topology)
        paths = graph.find_all_paths("a", "c")
        assert ["a", "b", "c"] in paths

    async def test_modeling_engine(self):
        engine = DependencyModelingEngine()
        topology = ServiceTopology(
            topology_id="model-topo",
            nodes=[TopologyNode(node_id="x", name="X"), TopologyNode(node_id="y", name="Y")],
            edges=[TopologyEdge(source="x", target="y")],
        )
        graph = await engine.model_dependencies(topology)
        assert graph is not None
        result = await engine.query_dependencies(
            DependencyRequest(service_name="x", dependency_type=EdgeType.CALLS)
        )
        assert len(result) == 1


@pytest.mark.asyncio
class TestImpact:
    async def test_impact_analysis(self):
        topology = ServiceTopology(
            topology_id="impact-topo",
            nodes=[
                TopologyNode(node_id="a", name="A"),
                TopologyNode(node_id="b", name="B"),
                TopologyNode(node_id="c", name="C"),
            ],
            edges=[
                TopologyEdge(source="a", target="b"),
                TopologyEdge(source="b", target="c"),
            ],
        )
        graph = DependencyGraph()
        graph.load_topology(topology)
        analyzer = ImpactAnalyzer(graph)
        request = ImpactRequest(changed_nodes=["a"], direction="outbound", max_depth=3)
        result = await analyzer.analyze(request)
        assert "b" in result.impacted_nodes
        assert result.impact_score > 0


@pytest.mark.asyncio
class TestVisualization:
    async def test_generate_d3(self):
        topology = ServiceTopology(
            topology_id="viz-topo",
            nodes=[TopologyNode(node_id="n1", name="N1")],
            edges=[],
        )
        visualizer = TopologyVisualizer()
        result = await visualizer.generate(topology, VisualizationConfig())
        assert len(result.nodes) == 1


@pytest.mark.asyncio
class TestRealtime:
    async def test_broadcast(self):
        manager = RealtimeTopologyManager()
        queue = await manager.connect()
        await manager.broadcast({"type": "test"})
        message = await queue.get()
        assert message["type"] == "test"
        await manager.disconnect(queue)

    async def test_update_topology(self):
        manager = RealtimeTopologyManager()
        queue = await manager.connect()
        await manager.update_topology("topo-1", {"nodes": []})
        message = await queue.get()
        assert message["topology_id"] == "topo-1"
        await manager.disconnect(queue)


@pytest.mark.asyncio
class TestVersioning:
    async def test_commit_and_list(self):
        manager = TopologyVersionManager()
        topology = ServiceTopology(topology_id="ver-topo")
        version = await manager.commit(topology)
        assert version.version == "v1.0.0"
        versions = await manager.list_versions("ver-topo")
        assert len(versions) == 1

    async def test_compare(self):
        manager = TopologyVersionManager()
        topology = ServiceTopology(topology_id="ver-topo")
        await manager.commit(topology)
        await manager.commit(topology)
        result = await manager.compare("ver-topo", "v1.0.0", "v2.0.0")
        assert result["from_version"] == "v1.0.0"


@pytest.mark.asyncio
class TestAudit:
    async def test_record_event(self):
        store = TopologyAuditStore()
        event = await store.record("topo-1", "created", "user", {"detail": "test"})
        assert event.event_type == "created"
        events = await store.get_events("topo-1")
        assert len(events) == 1


@pytest.mark.asyncio
class TestGRPC:
    async def test_server_client(self):
        server = TopologyRPCServer()

        async def add(x: int, y: int) -> dict:
            return {"result": x + y}

        server.register("add", add)
        client = TopologyRPCClient(server=server)
        result = await client.call("add", x=1, y=2)
        assert result["result"] == 3


@pytest.mark.asyncio
class TestSaga:
    async def test_successful_saga(self):
        saga = TopologySagaOrchestrator()
        from services.topology_service.schemas import SagaStep

        steps = [SagaStep(step_id="s1", service="svc", action="do", compensation="undo")]
        saga.register("s1", steps, {"do": lambda: {"ok": True}}, {"undo": lambda: {"ok": True}})
        result = await saga.execute("s1")
        assert result["success"] is True

    async def test_failed_saga_compensates(self):
        saga = TopologySagaOrchestrator()
        from services.topology_service.schemas import SagaStep

        steps = [
            SagaStep(step_id="s1", service="svc", action="ok", compensation="undo"),
            SagaStep(step_id="s2", service="svc", action="fail", compensation="undo"),
        ]
        saga.register(
            "s2",
            steps,
            {
                "ok": lambda: {"ok": True},
                "fail": lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            },
            {"undo": lambda: {"ok": True}},
        )
        result = await saga.execute("s2")
        assert result["success"] is False
