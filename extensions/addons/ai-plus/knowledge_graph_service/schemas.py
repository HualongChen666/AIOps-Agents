# -*- coding: utf-8 -*-
"""Pydantic schemas for the Knowledge Graph microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Supported graph node types."""

    ENTITY = "entity"
    SERVICE = "service"
    INFRASTRUCTURE = "infrastructure"
    FAULT = "fault"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    environment: str


class StatsResponse(BaseModel):
    """Service statistics response."""

    service: str
    request_counts: Dict[str, int]
    graph_entries: Dict[str, int]
    cache_size: int
    retry_policies: List[str]


class GraphNode(BaseModel):
    """A generic graph node."""

    node_id: str
    label: str
    node_type: str = "entity"
    properties: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GraphEdge(BaseModel):
    """A generic graph edge."""

    edge_id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class Graph(BaseModel):
    """A graph representation."""

    graph_id: str
    name: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EntityModelingRequest(BaseModel):
    """Request to model an entity."""

    entity_name: str
    entity_type: str = "generic"
    properties: Dict[str, Any] = Field(default_factory=dict)


class EntityModelingResponse(BaseModel):
    """Response from entity modeling."""

    node_id: str
    entity_name: str
    entity_type: str
    modeled: bool


class RelationModelingRequest(BaseModel):
    """Request to model a relation."""

    source_name: str
    target_name: str
    relation_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationModelingResponse(BaseModel):
    """Response from relation modeling."""

    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    modeled: bool


class GraphBuildRequest(BaseModel):
    """Request to build a graph."""

    graph_name: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    source: str = "manual"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphBuildResponse(BaseModel):
    """Response from graph building."""

    graph_id: str
    nodes_count: int
    edges_count: int
    built: bool


class GraphQueryRequest(BaseModel):
    """Request to query a graph."""

    graph_id: str
    entity_id: Optional[str] = None
    relation: Optional[str] = None
    depth: int = 2
    top_k: int = 10


class GraphQueryResponse(BaseModel):
    """Response from graph querying."""

    graph_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total: int


class GraphReasonRequest(BaseModel):
    """Request for graph reasoning."""

    graph_id: str
    node_id: str
    reason_type: str = "neighbors"
    relation: Optional[str] = None
    max_depth: int = 3


class GraphReasonResponse(BaseModel):
    """Response from graph reasoning."""

    graph_id: str
    node_id: str
    reason_type: str
    results: List[Dict[str, Any]]
    total: int


class NodeLayout(BaseModel):
    """Position for a node in a visualization."""

    node_id: str
    x: float
    y: float


class GraphVisualizationRequest(BaseModel):
    """Request to visualize a graph."""

    graph_id: str
    width: int = 800
    height: int = 600


class GraphVisualizationResponse(BaseModel):
    """Response from graph visualization."""

    graph_id: str
    nodes: List[NodeLayout]
    edges: List[GraphEdge]


class ServiceDependency(BaseModel):
    """A service dependency entry."""

    service: str
    depends_on: List[str] = Field(default_factory=list)
    properties: Dict[str, Any] = Field(default_factory=dict)


class ServiceDependencyGraphRequest(BaseModel):
    """Request to build a service dependency graph."""

    services: List[ServiceDependency]


class ServiceDependencyGraphResponse(BaseModel):
    """Response from building a service dependency graph."""

    graph_id: str
    services_count: int
    dependencies_count: int
    built: bool


class InfrastructureComponent(BaseModel):
    """An infrastructure component."""

    component_id: str
    component_type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    connections: List[str] = Field(default_factory=list)


class InfrastructureGraphRequest(BaseModel):
    """Request to build an infrastructure graph."""

    components: List[InfrastructureComponent]
    connection_type: str = "CONNECTS_TO"


class InfrastructureGraphResponse(BaseModel):
    """Response from building an infrastructure graph."""

    graph_id: str
    components_count: int
    connections_count: int
    built: bool


class FaultRule(BaseModel):
    """A fault propagation rule."""

    source: str
    target: str
    condition: str
    impact: str


class FaultState(BaseModel):
    """A component fault state."""

    component_id: str
    fault_type: str
    severity: float = 1.0


class FaultPropagationGraphRequest(BaseModel):
    """Request to build a fault propagation graph."""

    states: List[FaultState]
    rules: List[FaultRule]
    propagation_depth: int = 3


class FaultPropagationGraphResponse(BaseModel):
    """Response from building a fault propagation graph."""

    graph_id: str
    states_count: int
    rules_count: int
    impacted_count: int
    built: bool
