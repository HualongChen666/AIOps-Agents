# -*- coding: utf-8 -*-
"""Pydantic schemas for the topology microservice."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of topology nodes."""

    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    LOAD_BALANCER = "load_balancer"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL = "external"


class EdgeType(str, Enum):
    """Types of topology edges."""

    CALLS = "calls"
    DEPENDS_ON = "depends_on"
    HOSTS = "hosts"
    PUBLISHES_TO = "publishes_to"
    CONSUMES_FROM = "consumes_from"


class TopologyStatus(str, Enum):
    """Lifecycle status of topology operations."""

    PENDING = "pending"
    DISCOVERING = "discovering"
    DISCOVERED = "discovered"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    VISUALIZED = "visualized"
    UPDATING = "updating"
    UPDATED = "updated"
    FAILED = "failed"


class TopologyNode(BaseModel):
    """A node in the service topology."""

    node_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    node_type: NodeType = NodeType.SERVICE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    health: str = "healthy"
    x: Optional[float] = None
    y: Optional[float] = None


class TopologyEdge(BaseModel):
    """An edge/relationship between two topology nodes."""

    source: str = Field(..., min_length=1, max_length=128)
    target: str = Field(..., min_length=1, max_length=128)
    edge_type: EdgeType = EdgeType.CALLS
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceTopology(BaseModel):
    """Complete service topology graph."""

    topology_id: str = Field(..., min_length=1, max_length=128)
    version: str = "1.0.0"
    nodes: List[TopologyNode] = Field(default_factory=list)
    edges: List[TopologyEdge] = Field(default_factory=list)
    status: TopologyStatus = TopologyStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryRequest(BaseModel):
    """Request to discover topology."""

    source: str = "config"
    scope: str = "all"
    filters: Dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "system"


class DiscoveryResult(BaseModel):
    """Result of topology discovery."""

    topology_id: str
    node_count: int
    edge_count: int
    duration_seconds: float
    discovered_nodes: List[str] = Field(default_factory=list)


class DependencyRequest(BaseModel):
    """Request to model dependencies."""

    service_name: str = Field(..., min_length=1, max_length=128)
    dependency_type: EdgeType = EdgeType.DEPENDS_ON
    depth: int = Field(2, ge=1, le=10)


class ImpactRequest(BaseModel):
    """Request to analyze impact of a change."""

    changed_nodes: List[str] = Field(default_factory=list)
    change_magnitude: float = 1.0
    direction: str = "both"  # inbound, outbound, both
    max_depth: int = Field(5, ge=1, le=20)


class ImpactResult(BaseModel):
    """Result of impact analysis."""

    changed_nodes: List[str]
    impacted_nodes: List[str]
    paths: List[List[str]]
    impact_score: float
    analysis_duration_seconds: float


class TopologyVersion(BaseModel):
    """Topology version snapshot."""

    version: str
    topology_id: str
    commit_hash: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TopologyAuditEvent(BaseModel):
    """Audit event for topology changes."""

    event_id: str
    topology_id: str
    event_type: str
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VisualizationConfig(BaseModel):
    """Configuration for D3.js topology visualization."""

    width: int = 800
    height: int = 600
    layout: str = "force"
    color_scheme: str = "category"


class D3Visualization(BaseModel):
    """D3.js compatible topology visualization output."""

    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    config: VisualizationConfig
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceHealth(BaseModel):
    """Service health response."""

    status: str
    service: str
    uptime_seconds: int = 0
    topology_count: int = 0


class SagaStep(BaseModel):
    """Single saga step."""

    step_id: str
    service: str
    action: str
    compensation: str
    status: str = "pending"
    result: Dict[str, Any] = Field(default_factory=dict)


class SagaTransaction(BaseModel):
    """Saga transaction aggregate."""

    saga_id: str
    task_id: str
    steps: List[SagaStep] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
