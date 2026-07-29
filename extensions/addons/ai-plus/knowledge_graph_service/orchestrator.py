# -*- coding: utf-8 -*-
"""Knowledge Graph orchestrator for the microservice."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from loguru import logger

from . import metrics
from .builder import GraphBuilder
from .cache import CacheManager
from .config import settings
from .dependency_graph import ServiceDependencyGraphBuilder
from .fault_graph import FaultPropagationGraphBuilder
from .graph_store import GraphStore
from .infrastructure_graph import InfrastructureGraphBuilder
from .modeler import EntityModeler, RelationModeler
from .query import GraphQueryEngine
from .reasoning import GraphReasoningEngine
from .retry import KnowledgeGraphRetryEngine
from .schemas import (
    EntityModelingRequest,
    EntityModelingResponse,
    FaultPropagationGraphRequest,
    FaultPropagationGraphResponse,
    Graph,
    GraphBuildRequest,
    GraphBuildResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphReasonRequest,
    GraphReasonResponse,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    InfrastructureGraphRequest,
    InfrastructureGraphResponse,
    RelationModelingRequest,
    RelationModelingResponse,
    ServiceDependencyGraphRequest,
    ServiceDependencyGraphResponse,
    StatsResponse,
)
from .visualizer import GraphVisualizer


class KnowledgeGraphOrchestrator:
    """Orchestrator implementing task 35 (knowledge graph service)."""

    def __init__(
        self,
        cache: Optional[CacheManager] = None,
        retry_engine: Optional[KnowledgeGraphRetryEngine] = None,
        store: Optional[GraphStore] = None,
    ) -> None:
        self.settings = settings
        self.cache = cache or CacheManager(settings.redis_url)
        self.retry_engine = retry_engine or KnowledgeGraphRetryEngine()
        self.store = store or GraphStore(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
        )

        self.entity_modeler = EntityModeler()
        self.relation_modeler = RelationModeler(self.entity_modeler)
        self.graph_builder = GraphBuilder(self.store)
        self.query_engine = GraphQueryEngine()
        self.reasoning_engine = GraphReasoningEngine()
        self.visualizer = GraphVisualizer()
        self.dependency_builder = ServiceDependencyGraphBuilder(self.graph_builder)
        self.infrastructure_builder = InfrastructureGraphBuilder(self.graph_builder)
        self.fault_builder = FaultPropagationGraphBuilder(self.graph_builder)

        self._request_counts: Dict[str, int] = defaultdict(int)
        self._graphs: Dict[str, Graph] = {}

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    def _increment_count(self, operation: str) -> None:
        self._request_counts[operation] += 1
        metrics.request_counter.labels(operation=operation).inc()

    def list_methods(self) -> List[str]:
        """Return the list of exposed orchestrator methods."""
        return [
            "model_entity",
            "model_relation",
            "build_graph",
            "query_graph",
            "infer_graph",
            "visualize_graph",
            "build_service_dependency_graph",
            "build_infrastructure_graph",
            "build_fault_propagation_graph",
            "get_stats",
        ]

    async def get_stats(self) -> StatsResponse:
        """Return service statistics."""
        return StatsResponse(
            service=self.settings.service_name,
            request_counts=dict(self._request_counts),
            graph_entries={
                "graphs": len(self._graphs),
                "nodes": sum(len(g.nodes) for g in self._graphs.values()),
                "edges": sum(len(g.edges) for g in self._graphs.values()),
            },
            cache_size=len(self.cache._memory),
            retry_policies=self.retry_engine.list_policies(),
        )

    # ------------------------------------------------------------------
    # 35.3 Entity/Relation modeling
    # ------------------------------------------------------------------
    async def model_entity(self, request: EntityModelingRequest) -> EntityModelingResponse:
        self._increment_count("model_entity")
        node = self.entity_modeler.build_node(request)
        await self.cache.set(
            f"entity:{node.node_id}",
            node.model_dump(mode="json"),
            ttl=self.settings.default_cache_ttl,
        )
        metrics.graph_size_gauge.labels(entry_type="entity").inc()
        logger.info(f"Modeled entity {node.node_id}")
        return EntityModelingResponse(
            node_id=node.node_id,
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            modeled=True,
        )

    async def model_relation(self, request: RelationModelingRequest) -> RelationModelingResponse:
        self._increment_count("model_relation")
        edge = self.relation_modeler.build_edge(request)
        await self.cache.set(
            f"relation:{edge.edge_id}",
            edge.model_dump(mode="json"),
            ttl=self.settings.default_cache_ttl,
        )
        metrics.graph_size_gauge.labels(entry_type="relation").inc()
        logger.info(f"Modeled relation {edge.edge_id}")
        return RelationModelingResponse(
            edge_id=edge.edge_id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            relation_type=request.relation_type,
            modeled=True,
        )

    # ------------------------------------------------------------------
    # 35.4 Graph construction
    # ------------------------------------------------------------------
    async def build_graph(self, request: GraphBuildRequest) -> GraphBuildResponse:
        self._increment_count("build_graph")

        async def _build() -> Graph:
            return await self.graph_builder.build_graph(request)

        graph = await self.retry_engine.execute(_build, operation="build_graph")
        response = GraphBuildResponse(
            graph_id=graph.graph_id,
            nodes_count=len(graph.nodes),
            edges_count=len(graph.edges),
            built=True,
        )
        await self._cache_graph_response(graph.graph_id)
        metrics.graph_size_gauge.labels(entry_type="node").inc(len(graph.nodes))
        metrics.graph_size_gauge.labels(entry_type="edge").inc(len(graph.edges))
        logger.info(f"Built graph {graph.graph_id} with {len(graph.nodes)} nodes")
        return response

    # ------------------------------------------------------------------
    # 35.5 Graph query
    # ------------------------------------------------------------------
    async def query_graph(self, request: GraphQueryRequest) -> GraphQueryResponse:
        self._increment_count("query_graph")
        graph = self._get_graph(request.graph_id)
        return self.query_engine.query(
            graph.graph_id,
            graph.nodes,
            graph.edges,
            request,
        )

    # ------------------------------------------------------------------
    # 35.6 Graph reasoning
    # ------------------------------------------------------------------
    async def infer_graph(self, request: GraphReasonRequest) -> GraphReasonResponse:
        self._increment_count("infer_graph")
        graph = self._get_graph(request.graph_id)
        return self.reasoning_engine.reason(
            graph.graph_id,
            graph.nodes,
            graph.edges,
            request,
        )

    # ------------------------------------------------------------------
    # 35.7 Graph visualization
    # ------------------------------------------------------------------
    async def visualize_graph(
        self, request: GraphVisualizationRequest
    ) -> GraphVisualizationResponse:
        self._increment_count("visualize_graph")
        graph = self._get_graph(request.graph_id)
        return self.visualizer.visualize(graph, request)

    # ------------------------------------------------------------------
    # 35.8 Service dependency graph
    # ------------------------------------------------------------------
    async def build_service_dependency_graph(
        self, request: ServiceDependencyGraphRequest
    ) -> ServiceDependencyGraphResponse:
        self._increment_count("build_service_dependency_graph")

        response = await self.dependency_builder.build(request)
        await self._cache_graph_response(response.graph_id)
        logger.info(f"Built service dependency graph {response.graph_id}")
        return response

    # ------------------------------------------------------------------
    # 35.9 Infrastructure graph
    # ------------------------------------------------------------------
    async def build_infrastructure_graph(
        self, request: InfrastructureGraphRequest
    ) -> InfrastructureGraphResponse:
        self._increment_count("build_infrastructure_graph")

        response = await self.infrastructure_builder.build(request)
        await self._cache_graph_response(response.graph_id)
        logger.info(f"Built infrastructure graph {response.graph_id}")
        return response

    # ------------------------------------------------------------------
    # 35.10 Fault propagation graph
    # ------------------------------------------------------------------
    async def build_fault_propagation_graph(
        self, request: FaultPropagationGraphRequest
    ) -> FaultPropagationGraphResponse:
        self._increment_count("build_fault_propagation_graph")

        response = await self.fault_builder.build(request)
        await self._cache_graph_response(response.graph_id)
        logger.info(f"Built fault propagation graph {response.graph_id}")
        return response

    def _get_graph(self, graph_id: str) -> Graph:
        if graph_id not in self._graphs:
            raise KeyError(f"Graph not found: {graph_id}")
        return self._graphs[graph_id]

    async def _cache_graph_response(self, graph_id: str) -> None:
        graph = await self.store.as_graph(graph_id)
        self._graphs[graph_id] = graph
        await self.cache.set(
            f"graph:{graph_id}",
            graph.model_dump(mode="json"),
            ttl=self.settings.default_cache_ttl * 2,
        )
