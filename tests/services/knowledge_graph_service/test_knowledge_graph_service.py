# -*- coding: utf-8 -*-
"""Tests for the Knowledge Graph microservice."""

from __future__ import annotations

import httpx
import pytest

from services.knowledge_graph_service.cache import CacheManager
from services.knowledge_graph_service.graph_store import GraphStore
from services.knowledge_graph_service.grpc.client import KnowledgeGraphRPCClient
from services.knowledge_graph_service.grpc.server import KnowledgeGraphRPCServer
from services.knowledge_graph_service.main_app import app
from services.knowledge_graph_service.orchestrator import KnowledgeGraphOrchestrator
from services.knowledge_graph_service.query import GraphQueryEngine
from services.knowledge_graph_service.reasoning import GraphReasoningEngine
from services.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    FaultPropagationGraphRequest,
    FaultRule,
    FaultState,
    Graph,
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
    GraphQueryRequest,
    GraphReasonRequest,
    GraphVisualizationRequest,
    InfrastructureComponent,
    InfrastructureGraphRequest,
    RelationModelingRequest,
    ServiceDependency,
    ServiceDependencyGraphRequest,
)


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset the orchestrator to a deterministic fallback for tests."""
    from services.knowledge_graph_service import config, main_app

    config.settings.redis_url = ""
    config.settings.neo4j_uri = ""
    main_app._orchestrator = KnowledgeGraphOrchestrator(cache=CacheManager())
    yield


@pytest.fixture
def orchestrator():
    return KnowledgeGraphOrchestrator(cache=CacheManager())


@pytest.fixture
def sample_graph_request():
    return GraphBuildRequest(
        graph_name="test-graph",
        nodes=[
            GraphNode(node_id="a", label="A"),
            GraphNode(node_id="b", label="B"),
            GraphNode(node_id="c", label="C"),
        ],
        edges=[
            GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="relates"),
            GraphEdge(edge_id="bc", source_id="b", target_id="c", relation="relates"),
        ],
    )


async def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ------------------------------------------------------------------
# API tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health():
    async with await _client() as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "knowledge-graph-service"


@pytest.mark.asyncio
async def test_metrics():
    async with await _client() as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert "knowledge_graph" in response.text


@pytest.mark.asyncio
async def test_stats():
    async with await _client() as client:
        response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["service"]


@pytest.mark.asyncio
async def test_model_entity():
    async with await _client() as client:
        response = await client.post(
            "/entity/model",
            json={"entity_name": "Server", "entity_type": "service"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["modeled"]
    assert data["node_id"]


@pytest.mark.asyncio
async def test_model_relation():
    async with await _client() as client:
        response = await client.post(
            "/relation/model",
            json={
                "source_name": "Server",
                "target_name": "Database",
                "relation_type": "connects_to",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["modeled"]
    assert data["edge_id"]


@pytest.mark.asyncio
async def test_build_graph(sample_graph_request):
    async with await _client() as client:
        response = await client.post(
            "/graph/build", json=sample_graph_request.model_dump(mode="json")
        )
    assert response.status_code == 200
    data = response.json()
    assert data["built"]
    assert data["graph_id"]
    assert data["nodes_count"] == 3


@pytest.mark.asyncio
async def test_query_graph(sample_graph_request):
    async with await _client() as client:
        build_response = await client.post(
            "/graph/build", json=sample_graph_request.model_dump(mode="json")
        )
        graph_id = build_response.json()["graph_id"]

        query = GraphQueryRequest(graph_id=graph_id, entity_id="a", depth=2)
        response = await client.post("/graph/query", json=query.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) >= 2


@pytest.mark.asyncio
async def test_query_graph_not_found():
    async with await _client() as client:
        query = GraphQueryRequest(graph_id="missing", entity_id="x")
        response = await client.post("/graph/query", json=query.model_dump(mode="json"))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reason_graph(sample_graph_request):
    async with await _client() as client:
        build_response = await client.post(
            "/graph/build", json=sample_graph_request.model_dump(mode="json")
        )
        graph_id = build_response.json()["graph_id"]

        reason = GraphReasonRequest(graph_id=graph_id, node_id="a", reason_type="neighbors")
        response = await client.post("/graph/reason", json=reason.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert data["reason_type"] == "neighbors"
    assert len(data["results"]) >= 1


@pytest.mark.asyncio
async def test_reason_pagerank(sample_graph_request):
    async with await _client() as client:
        build_response = await client.post(
            "/graph/build", json=sample_graph_request.model_dump(mode="json")
        )
        graph_id = build_response.json()["graph_id"]

        reason = GraphReasonRequest(graph_id=graph_id, node_id="a", reason_type="pagerank")
        response = await client.post("/graph/reason", json=reason.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert data["reason_type"] == "pagerank"
    assert len(data["results"]) == 3


@pytest.mark.asyncio
async def test_visualize_graph(sample_graph_request):
    async with await _client() as client:
        build_response = await client.post(
            "/graph/build", json=sample_graph_request.model_dump(mode="json")
        )
        graph_id = build_response.json()["graph_id"]

        viz = GraphVisualizationRequest(graph_id=graph_id, width=400, height=400)
        response = await client.post("/graph/visualize", json=viz.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 3
    assert "x" in data["nodes"][0]


@pytest.mark.asyncio
async def test_service_dependency_graph():
    request = ServiceDependencyGraphRequest(
        services=[
            ServiceDependency(service="api", depends_on=["db"]),
            ServiceDependency(service="web", depends_on=["api"]),
        ]
    )
    async with await _client() as client:
        response = await client.post(
            "/service-dependency/build", json=request.model_dump(mode="json")
        )
    assert response.status_code == 200
    data = response.json()
    assert data["built"]
    assert data["dependencies_count"] == 2


@pytest.mark.asyncio
async def test_infrastructure_graph():
    request = InfrastructureGraphRequest(
        components=[
            InfrastructureComponent(component_id="host-1", component_type="host"),
            InfrastructureComponent(
                component_id="vm-1", component_type="vm", connections=["host-1"]
            ),
        ]
    )
    async with await _client() as client:
        response = await client.post("/infrastructure/build", json=request.model_dump(mode="json"))
    assert response.status_code == 200
    data = response.json()
    assert data["built"]
    assert data["components_count"] == 2


@pytest.mark.asyncio
async def test_fault_propagation_graph():
    request = FaultPropagationGraphRequest(
        states=[FaultState(component_id="switch-1", fault_type="down")],
        rules=[FaultRule(source="switch-1", target="server-1", condition="down", impact="high")],
    )
    async with await _client() as client:
        response = await client.post(
            "/fault-propagation/build", json=request.model_dump(mode="json")
        )
    assert response.status_code == 200
    data = response.json()
    assert data["built"]
    assert data["impacted_count"] == 1


@pytest.mark.asyncio
async def test_rpc_methods():
    async with await _client() as client:
        response = await client.post("/rpc/list_methods", json={})
    assert response.status_code == 200
    assert "build_graph" in response.json()


# ------------------------------------------------------------------
# Core tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_model_entity_core(orchestrator):
    response = await orchestrator.model_entity(
        EntityModelingRequest(entity_name="Database", entity_type="service")
    )
    assert response.modeled
    assert response.node_id == "database"


@pytest.mark.asyncio
async def test_model_relation_core(orchestrator):
    response = await orchestrator.model_relation(
        RelationModelingRequest(
            source_name="Api",
            target_name="Database",
            relation_type="uses",
        )
    )
    assert response.modeled
    assert "uses" in response.edge_id


@pytest.mark.asyncio
async def test_build_and_query_graph_core(orchestrator, sample_graph_request):
    build_response = await orchestrator.build_graph(sample_graph_request)
    assert build_response.built
    graph_id = build_response.graph_id

    query_response = await orchestrator.query_graph(
        GraphQueryRequest(graph_id=graph_id, entity_id="a", depth=2)
    )
    assert query_response.total >= 2


@pytest.mark.asyncio
async def test_reason_neighbors_core(orchestrator, sample_graph_request):
    build_response = await orchestrator.build_graph(sample_graph_request)
    response = await orchestrator.infer_graph(
        GraphReasonRequest(
            graph_id=build_response.graph_id,
            node_id="a",
            reason_type="neighbors",
        )
    )
    assert response.total == 1


@pytest.mark.asyncio
async def test_reason_transitive_core(orchestrator, sample_graph_request):
    build_response = await orchestrator.build_graph(sample_graph_request)
    response = await orchestrator.infer_graph(
        GraphReasonRequest(
            graph_id=build_response.graph_id,
            node_id="a",
            reason_type="transitive",
            relation="relates",
            max_depth=3,
        )
    )
    assert response.total >= 1


@pytest.mark.asyncio
async def test_reason_paths_core(orchestrator, sample_graph_request):
    build_response = await orchestrator.build_graph(sample_graph_request)
    response = await orchestrator.infer_graph(
        GraphReasonRequest(
            graph_id=build_response.graph_id,
            node_id="a",
            reason_type="paths",
            max_depth=3,
        )
    )
    assert response.total >= 1


@pytest.mark.asyncio
async def test_visualize_core(orchestrator, sample_graph_request):
    build_response = await orchestrator.build_graph(sample_graph_request)
    response = await orchestrator.visualize_graph(
        GraphVisualizationRequest(graph_id=build_response.graph_id, width=400, height=400)
    )
    assert len(response.nodes) == 3
    assert response.nodes[0].x >= 0


@pytest.mark.asyncio
async def test_service_dependency_core(orchestrator):
    request = ServiceDependencyGraphRequest(
        services=[
            ServiceDependency(service="svc-a", depends_on=["svc-b"]),
            ServiceDependency(service="svc-b", depends_on=["svc-c"]),
        ]
    )
    response = await orchestrator.build_service_dependency_graph(request)
    assert response.built
    assert response.dependencies_count == 2


@pytest.mark.asyncio
async def test_infrastructure_core(orchestrator):
    request = InfrastructureGraphRequest(
        components=[
            InfrastructureComponent(component_id="host", component_type="host"),
            InfrastructureComponent(
                component_id="db", component_type="database", connections=["host"]
            ),
        ]
    )
    response = await orchestrator.build_infrastructure_graph(request)
    assert response.built
    assert response.connections_count == 1


@pytest.mark.asyncio
async def test_fault_propagation_core(orchestrator):
    request = FaultPropagationGraphRequest(
        states=[FaultState(component_id="router-1", fault_type="down")],
        rules=[
            FaultRule(
                source="router-1",
                target="server-1",
                condition="down",
                impact="critical",
            )
        ],
    )
    response = await orchestrator.build_fault_propagation_graph(request)
    assert response.built
    assert response.impacted_count == 1


@pytest.mark.asyncio
async def test_get_stats(orchestrator):
    await orchestrator.build_graph(
        GraphBuildRequest(
            graph_name="stats-test",
            nodes=[GraphNode(node_id="x", label="X")],
            edges=[],
        )
    )
    stats = await orchestrator.get_stats()
    assert stats.service == "knowledge-graph-service"
    assert stats.graph_entries["graphs"] == 1


def test_list_methods(orchestrator):
    methods = orchestrator.list_methods()
    assert "build_graph" in methods
    assert "query_graph" in methods


# ------------------------------------------------------------------
# Cache / retry / grpc unit tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cache_operations():
    cache = CacheManager()
    await cache.set("key", {"value": 1}, ttl=60)
    assert await cache.get("key") == {"value": 1}
    await cache.delete("key")
    assert await cache.get("key") is None


@pytest.mark.asyncio
async def test_cache_redis_path():
    from unittest.mock import AsyncMock

    fake_redis = AsyncMock()
    fake_redis.get.return_value = '{"value": 42}'

    cache = CacheManager("redis://localhost:6379")
    await cache.connect()
    cache._redis = fake_redis

    value = await cache.get("key")
    await cache.set("key", {"value": 1})
    await cache.delete("key")
    await cache.clear()

    assert value == {"value": 42}
    fake_redis.setex.assert_called_once()
    fake_redis.delete.assert_called_once()
    fake_redis.flushdb.assert_called_once()


@pytest.mark.asyncio
async def test_retry_engine_success():
    from services.knowledge_graph_service.retry import KnowledgeGraphRetryEngine

    engine = KnowledgeGraphRetryEngine()

    async def ok():
        return "ok"

    assert await engine.execute(ok, operation="test") == "ok"


@pytest.mark.asyncio
async def test_retry_engine_failure():
    from unittest.mock import patch

    from services.knowledge_graph_service.retry import KnowledgeGraphRetryEngine

    engine = KnowledgeGraphRetryEngine("exponential_fast")
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("retryable")
        return "ok"

    with patch("services.knowledge_graph_service.retry.asyncio.sleep"):
        result = await engine.execute(flaky, operation="flaky")
    assert result == "ok"
    assert calls == 2


def test_grpc_server():
    server = KnowledgeGraphRPCServer()
    server.register("echo", lambda x: x)
    assert "echo" in server.list_methods()


@pytest.mark.asyncio
async def test_grpc_server_async_call():
    server = KnowledgeGraphRPCServer()

    async def echo(x):
        return x

    server.register("echo", echo)
    result = await server.call("echo", x="hello")
    assert result == "hello"


@pytest.mark.asyncio
async def test_rpc_client(mocker):
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.return_value = mock_response

    with patch(
        "services.knowledge_graph_service.grpc.client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        client = KnowledgeGraphRPCClient()
        result = await client.call("echo", {"x": "hello"})
    assert result == {"ok": True}


# ------------------------------------------------------------------
# Query / reasoning unit tests
# ------------------------------------------------------------------
def test_query_engine_shortest_path():
    nodes = [
        GraphNode(node_id="a", label="A"),
        GraphNode(node_id="b", label="B"),
        GraphNode(node_id="c", label="C"),
    ]
    edges = [
        GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="r"),
        GraphEdge(edge_id="bc", source_id="b", target_id="c", relation="r"),
    ]
    engine = GraphQueryEngine()
    path = engine.find_shortest_path(nodes, edges, "a", "c")
    assert path == ["a", "b", "c"]


def test_reasoning_engine_pagerank():
    nodes = [
        GraphNode(node_id="a", label="A"),
        GraphNode(node_id="b", label="B"),
        GraphNode(node_id="c", label="C"),
    ]
    edges = [
        GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="r"),
        GraphEdge(edge_id="bc", source_id="b", target_id="c", relation="r"),
    ]
    engine = GraphReasoningEngine()
    result = engine._page_rank(nodes, edges, iterations=5)
    assert len(result) == 3


def test_reasoning_engine_all_paths():
    nodes = [
        GraphNode(node_id="a", label="A"),
        GraphNode(node_id="b", label="B"),
    ]
    edges = [GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="r")]
    engine = GraphReasoningEngine()
    result = engine._all_paths("a", nodes, edges, max_depth=3)
    assert len(result) == 1
    assert result[0]["path"] == ["a", "b"]


# ------------------------------------------------------------------
# Graph store unit tests
# ------------------------------------------------------------------
@pytest.mark.asyncio
async def test_graph_store_in_memory():
    store = GraphStore()
    await store.connect()

    node = GraphNode(node_id="node-1", label="Node 1")
    await store.add_node(node)
    assert (await store.get_node("node-1")).label == "Node 1"

    edge = GraphEdge(edge_id="e1", source_id="node-1", target_id="node-2", relation="links")
    await store.add_edge(edge)

    neighbors = await store.get_neighbors("node-1")
    assert len(neighbors) == 1
    assert neighbors[0].target_id == "node-2"

    queried_edges = await store.query_edges(relation="links")
    assert len(queried_edges) == 1

    queried_nodes = await store.query_nodes(label="Node 1")
    assert len(queried_nodes) == 1


@pytest.mark.asyncio
async def test_graph_store_load_and_clear():
    store = GraphStore()
    graph = Graph(
        graph_id="g1",
        name="sample",
        nodes=[GraphNode(node_id="a", label="A")],
        edges=[GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="r")],
    )
    await store.load_graph(graph)
    snapshot = await store.as_graph("g1")
    assert len(snapshot.nodes) == 1
    assert len(snapshot.edges) == 1

    await store.clear()
    assert (await store.get_node("a")) is None
    assert await store.query_edges() == []


@pytest.mark.asyncio
async def test_graph_store_find_paths():
    store = GraphStore()
    graph = Graph(
        graph_id="g1",
        name="paths",
        nodes=[
            GraphNode(node_id="a", label="A"),
            GraphNode(node_id="b", label="B"),
            GraphNode(node_id="c", label="C"),
        ],
        edges=[
            GraphEdge(edge_id="ab", source_id="a", target_id="b", relation="r"),
            GraphEdge(edge_id="bc", source_id="b", target_id="c", relation="r"),
            GraphEdge(edge_id="ac", source_id="a", target_id="c", relation="r"),
        ],
    )
    await store.load_graph(graph)
    paths = await store.find_paths("a", "c", max_depth=3)
    assert any(path == ["a", "c"] for path in paths)
    assert any(path == ["a", "b", "c"] for path in paths)
