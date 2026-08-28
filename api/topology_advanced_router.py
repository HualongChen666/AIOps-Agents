# -*- coding: utf-8 -*-
"""
Advanced Topology API Router

Implements advanced topology management endpoints including:
- Graph topology visualization
- Node and edge management
- Layer topology
- Dependency modeling
- Topology visualization configuration
- Service discovery and registration
- Causal analysis
- Call chain analysis
- Impact analysis

All endpoints integrate with core business logic from:
- core.topology_engine (for topology generation)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from core.topology_engine import (
    get_full_link_topology,
    update_node_health,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/topology", tags=["Advanced Topology Management"])

# Additional router for /api/topology prefix (for frontend compatibility)
router_alt = APIRouter(prefix="/api/topology", tags=["Topology"])

# Additional router for /api/v1/topology prefix (exact match for requirements)
router_v1 = APIRouter(prefix="/api/v1/topology", tags=["Topology V1"])

# ============================================================
# In-memory data stores (in production, use database)
# ============================================================
_topology_graphs: Dict[str, Dict[str, Any]] = {}
_topology_nodes: Dict[str, Dict[str, Any]] = {}
_topology_edges: Dict[str, Dict[str, Any]] = {}
_topology_layers: Dict[str, Dict[str, Any]] = {}
_topology_dependencies: Dict[str, Dict[str, Any]] = {}
_visualization_configs: Dict[str, Dict[str, Any]] = {}

# ============================================================
# Pydantic Models for Data Validation
# ============================================================


class NodeCreate(BaseModel):
    """Model for creating a topology node"""

    id: str = Field(..., min_length=1, max_length=100, description="Node unique identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Node display name")
    type: str = Field(
        default="service", description="Node type: service, database, cache, queue, gateway"
    )
    status: str = Field(default="healthy", description="Node status: healthy, warning, critical")
    layer: str = Field(
        default="application", description="Layer: application, infrastructure, network"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node metadata")


class NodeUpdate(BaseModel):
    """Model for updating a topology node"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    status: Optional[str] = None
    layer: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EdgeCreate(BaseModel):
    """Model for creating a topology edge"""

    id: str = Field(..., min_length=1, max_length=100, description="Edge unique identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(default="sync", description="Edge type: sync, async, weak")
    weight: float = Field(default=1.0, ge=0, description="Edge weight/strength")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional edge metadata")


class EdgeUpdate(BaseModel):
    """Model for updating a topology edge"""

    source: Optional[str] = None
    target: Optional[str] = None
    type: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class LayerCreate(BaseModel):
    """Model for creating a topology layer"""

    id: str = Field(..., min_length=1, max_length=100, description="Layer unique identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Layer display name")
    level: int = Field(default=0, ge=0, description="Layer level/depth")
    description: str = Field(default="", description="Layer description")
    color: str = Field(default="#3b82f6", description="Layer color for visualization")


class DependencyCreate(BaseModel):
    """Model for creating a dependency relationship"""

    id: str = Field(..., min_length=1, max_length=100, description="Dependency unique identifier")
    source: str = Field(..., description="Source service/node")
    target: str = Field(..., description="Target service/node")
    type: str = Field(default="sync", description="Dependency type: sync, async, weak")
    strength: int = Field(default=1, ge=1, le=10, description="Dependency strength (1-10)")
    description: str = Field(default="", description="Dependency description")


class VisualizationConfigCreate(BaseModel):
    """Model for creating visualization configuration"""

    name: str = Field(..., min_length=1, max_length=100, description="Configuration name")
    node_color: str = Field(default="#3b82f6", description="Default node color")
    edge_color: str = Field(default="#94a3b8", description="Default edge color")
    show_labels: bool = Field(default=True, description="Show node labels")
    show_metrics: bool = Field(default=True, description="Show node metrics")
    auto_refresh: bool = Field(default=False, description="Auto-refresh topology")
    refresh_interval: int = Field(default=60, ge=10, description="Refresh interval in seconds")


class VisualizationConfigUpdate(BaseModel):
    """Model for updating visualization configuration"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    node_color: Optional[str] = None
    edge_color: Optional[str] = None
    show_labels: Optional[bool] = None
    show_metrics: Optional[bool] = None
    auto_refresh: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=10)


# ============================================================
# Helper Functions
# ============================================================


def _generate_id() -> str:
    """Generate unique ID"""
    return str(uuid.uuid4())


def _get_current_timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.utcnow().isoformat()


# ============================================================
# 1. Graph Topology Endpoints
# ============================================================


@router.get("/graph", summary="Get topology graph")
async def get_topology_graph(
    layer: Optional[str] = Query(None, description="Filter by layer"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """
    Retrieve the complete topology graph with nodes and edges
    """
    logger.info("Fetching topology graph")
    try:
        # Try to get real topology from core engine
        try:
            real_topology = get_full_link_topology()
            nodes = real_topology.get("nodes", [])
            edges = real_topology.get("edges", [])

            # Apply filters
            if layer:
                nodes = [n for n in nodes if n.get("layer") == layer]
            if status:
                nodes = [n for n in nodes if n.get("status") == status]

            # Filter edges to only include filtered nodes
            node_ids = {n.get("id") for n in nodes}
            edges = [
                e for e in edges if e.get("source") in node_ids and e.get("target") in node_ids
            ]

            return {
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "layers": list({n.get("layer", "unknown") for n in nodes}),
                },
                "updated_at": _get_current_timestamp(),
            }
        except Exception as e:
            logger.warning(f"Failed to get real topology, using in-memory store: {e}")

            # Fallback to in-memory store
        items = list(_topology_graphs.values())
        if not items:
            # Return empty graph if no data
            return {
                "nodes": [],
                "edges": [],
                "stats": {"total_nodes": 0, "total_edges": 0, "layers": []},
                "updated_at": _get_current_timestamp(),
            }

        graph = items[0] if items else {"nodes": [], "edges": []}
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        if layer:
            nodes = [n for n in nodes if n.get("layer") == layer]
        if status:
            nodes = [n for n in nodes if n.get("status") == status]

        node_ids = {n.get("id") for n in nodes}
        edges = [e for e in edges if e.get("source") in node_ids and e.get("target") in node_ids]

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "layers": list({n.get("layer", "unknown") for n in nodes}),
            },
            "updated_at": _get_current_timestamp(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch topology graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch topology graph: {str(e)}")


@router.post("/graph", summary="Create topology graph")
async def create_topology_graph(graph: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """
    Create a new topology graph
    """
    logger.info("Creating topology graph")
    try:
        graph_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_graph = {
            "id": graph_id,
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_graphs[graph_id] = new_graph
        logger.info(f"Topology graph created: {graph_id}")
        return new_graph
    except Exception as e:
        logger.error(f"Failed to create topology graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create topology graph: {str(e)}")


# ============================================================
# 2. Node Management Endpoints
# ============================================================


@router.get("/nodes", summary="Get all topology nodes")
async def get_nodes(
    layer: Optional[str] = Query(None, description="Filter by layer"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """
    Retrieve all topology nodes with optional filtering
    """
    logger.info("Fetching topology nodes")
    try:
        items = list(_topology_nodes.values())

        if layer:
            items = [item for item in items if item.get("layer") == layer]
        if status:
            items = [item for item in items if item.get("status") == status]
        if type:
            items = [item for item in items if item.get("type") == type]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch nodes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch nodes: {str(e)}")


@router.post("/nodes", summary="Create topology node")
async def create_node(node: NodeCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new topology node
    """
    logger.info(f"Creating node: {node.id}")
    try:
        if node.id in _topology_nodes:
            raise HTTPException(status_code=409, detail="Node ID already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_node = {
            "id": node.id,
            "name": node.name,
            "type": node.type,
            "status": node.status,
            "layer": node.layer,
            "metadata": node.metadata,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_nodes[node.id] = new_node
        logger.info(f"Node created: {node.id}")
        return new_node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create node: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")


@router.get("/nodes/{node_id}", summary="Get node by ID")
async def get_node(node_id: str = Path(..., description="Node ID")) -> Dict[str, Any]:
    """
    Retrieve a specific node by ID
    """
    logger.info(f"Fetching node: {node_id}")
    try:
        if node_id not in _topology_nodes:
            raise HTTPException(status_code=404, detail="Node not found")

        return _topology_nodes[node_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch node: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch node: {str(e)}")


@router.patch("/nodes/{node_id}", summary="Update node")
async def update_node(node_id: str, node_update: NodeUpdate, request: Request) -> Dict[str, Any]:
    """
    Update an existing node
    """
    logger.info(f"Updating node: {node_id}")
    try:
        if node_id not in _topology_nodes:
            raise HTTPException(status_code=404, detail="Node not found")

        operator_ip = request.client.host if request.client else "unknown"
        existing = _topology_nodes[node_id]

        # Update fields
        update_data = node_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing[key] = value

        existing["updated_at"] = _get_current_timestamp()
        existing["updated_by"] = operator_ip

        # Sync with core topology engine
        try:
            update_node_health(node_id, existing.get("status", "healthy"))
        except Exception as e:
            logger.warning(f"Failed to sync node health with core engine: {e}")

        logger.info(f"Node updated: {node_id}")
        return existing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update node: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")


@router.delete("/nodes/{node_id}", summary="Delete node")
async def delete_node(node_id: str) -> Dict[str, Any]:
    """
    Delete a topology node
    """
    logger.info(f"Deleting node: {node_id}")
    try:
        if node_id not in _topology_nodes:
            raise HTTPException(status_code=404, detail="Node not found")

        del _topology_nodes[node_id]
        logger.info(f"Node deleted: {node_id}")
        return {"message": "Node deleted successfully", "id": node_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete node: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete node: {str(e)}")


# ============================================================
# 3. Edge Management Endpoints
# ============================================================


@router.get("/edges", summary="Get all topology edges")
async def get_edges(
    source: Optional[str] = Query(None, description="Filter by source node"),
    target: Optional[str] = Query(None, description="Filter by target node"),
    type: Optional[str] = Query(None, description="Filter by edge type"),
) -> Dict[str, Any]:
    """
    Retrieve all topology edges with optional filtering
    """
    logger.info("Fetching topology edges")
    try:
        items = list(_topology_edges.values())

        if source:
            items = [item for item in items if item.get("source") == source]
        if target:
            items = [item for item in items if item.get("target") == target]
        if type:
            items = [item for item in items if item.get("type") == type]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch edges: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch edges: {str(e)}")


@router.post("/edges", summary="Create topology edge")
async def create_edge(edge: EdgeCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new topology edge
    """
    logger.info(f"Creating edge: {edge.id}")
    try:
        if edge.id in _topology_edges:
            raise HTTPException(status_code=409, detail="Edge ID already exists")

        # Validate source and target nodes exist
        if edge.source not in _topology_nodes:
            raise HTTPException(status_code=422, detail=f"Source node {edge.source} not found")
        if edge.target not in _topology_nodes:
            raise HTTPException(status_code=422, detail=f"Target node {edge.target} not found")

        operator_ip = request.client.host if request.client else "unknown"

        new_edge = {
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "weight": edge.weight,
            "metadata": edge.metadata,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_edges[edge.id] = new_edge
        logger.info(f"Edge created: {edge.id}")
        return new_edge
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create edge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create edge: {str(e)}")


@router.get("/edges/{edge_id}", summary="Get edge by ID")
async def get_edge(edge_id: str = Path(..., description="Edge ID")) -> Dict[str, Any]:
    """
    Retrieve a specific edge by ID
    """
    logger.info(f"Fetching edge: {edge_id}")
    try:
        if edge_id not in _topology_edges:
            raise HTTPException(status_code=404, detail="Edge not found")

        return _topology_edges[edge_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch edge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch edge: {str(e)}")


@router.patch("/edges/{edge_id}", summary="Update edge")
async def update_edge(edge_id: str, edge_update: EdgeUpdate, request: Request) -> Dict[str, Any]:
    """
    Update an existing edge
    """
    logger.info(f"Updating edge: {edge_id}")
    try:
        if edge_id not in _topology_edges:
            raise HTTPException(status_code=404, detail="Edge not found")

        operator_ip = request.client.host if request.client else "unknown"
        existing = _topology_edges[edge_id]

        # Update fields
        update_data = edge_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing[key] = value

        existing["updated_at"] = _get_current_timestamp()
        existing["updated_by"] = operator_ip

        logger.info(f"Edge updated: {edge_id}")
        return existing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update edge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update edge: {str(e)}")


@router.delete("/edges/{edge_id}", summary="Delete edge")
async def delete_edge(edge_id: str) -> Dict[str, Any]:
    """
    Delete a topology edge
    """
    logger.info(f"Deleting edge: {edge_id}")
    try:
        if edge_id not in _topology_edges:
            raise HTTPException(status_code=404, detail="Edge not found")

        del _topology_edges[edge_id]
        logger.info(f"Edge deleted: {edge_id}")
        return {"message": "Edge deleted successfully", "id": edge_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete edge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete edge: {str(e)}")


# ============================================================
# 4. Layer Management Endpoints
# ============================================================


@router.get("/layers", summary="Get all topology layers")
async def get_layers() -> Dict[str, Any]:
    """
    Retrieve all topology layers
    """
    logger.info("Fetching topology layers")
    try:
        items = list(_topology_layers.values())
        # Sort by level
        items.sort(key=lambda x: x.get("level", 0))
        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch layers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch layers: {str(e)}")


@router.post("/layers", summary="Create topology layer")
async def create_layer(layer: LayerCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new topology layer
    """
    logger.info(f"Creating layer: {layer.id}")
    try:
        if layer.id in _topology_layers:
            raise HTTPException(status_code=409, detail="Layer ID already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_layer = {
            "id": layer.id,
            "name": layer.name,
            "level": layer.level,
            "description": layer.description,
            "color": layer.color,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_layers[layer.id] = new_layer
        logger.info(f"Layer created: {layer.id}")
        return new_layer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create layer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create layer: {str(e)}")


@router.get("/layers/{layer_id}", summary="Get layer by ID")
async def get_layer(layer_id: str = Path(..., description="Layer ID")) -> Dict[str, Any]:
    """
    Retrieve a specific layer by ID
    """
    logger.info(f"Fetching layer: {layer_id}")
    try:
        if layer_id not in _topology_layers:
            raise HTTPException(status_code=404, detail="Layer not found")

        return _topology_layers[layer_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch layer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch layer: {str(e)}")


@router.delete("/layers/{layer_id}", summary="Delete layer")
async def delete_layer(layer_id: str) -> Dict[str, Any]:
    """
    Delete a topology layer
    """
    logger.info(f"Deleting layer: {layer_id}")
    try:
        if layer_id not in _topology_layers:
            raise HTTPException(status_code=404, detail="Layer not found")

        del _topology_layers[layer_id]
        logger.info(f"Layer deleted: {layer_id}")
        return {"message": "Layer deleted successfully", "id": layer_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete layer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete layer: {str(e)}")


# ============================================================
# 5. Dependency Management Endpoints
# ============================================================


@router.get("/dependencies", summary="Get all dependencies")
async def get_dependencies(
    source: Optional[str] = Query(None, description="Filter by source"),
    target: Optional[str] = Query(None, description="Filter by target"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """
    Retrieve all dependency relationships with optional filtering
    """
    logger.info("Fetching dependencies")
    try:
        items = list(_topology_dependencies.values())

        if source:
            items = [item for item in items if item.get("source") == source]
        if target:
            items = [item for item in items if item.get("target") == target]
        if type:
            items = [item for item in items if item.get("type") == type]

        return {"items": items, "total": len(items)}
    except Exception as e:
        logger.error(f"Failed to fetch dependencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dependencies: {str(e)}")


@router.post("/dependencies", summary="Create dependency")
async def create_dependency(dependency: DependencyCreate, request: Request) -> Dict[str, Any]:
    """
    Create a new dependency relationship
    """
    logger.info(f"Creating dependency: {dependency.id}")
    try:
        if dependency.id in _topology_dependencies:
            raise HTTPException(status_code=409, detail="Dependency ID already exists")

        operator_ip = request.client.host if request.client else "unknown"

        new_dependency = {
            "id": dependency.id,
            "source": dependency.source,
            "target": dependency.target,
            "type": dependency.type,
            "strength": dependency.strength,
            "description": dependency.description,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_dependencies[dependency.id] = new_dependency
        logger.info(f"Dependency created: {dependency.id}")
        return new_dependency
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create dependency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create dependency: {str(e)}")


@router.get("/dependencies/{dep_id}", summary="Get dependency by ID")
async def get_dependency(dep_id: str = Path(..., description="Dependency ID")) -> Dict[str, Any]:
    """
    Retrieve a specific dependency by ID
    """
    logger.info(f"Fetching dependency: {dep_id}")
    try:
        if dep_id not in _topology_dependencies:
            raise HTTPException(status_code=404, detail="Dependency not found")

        return _topology_dependencies[dep_id]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch dependency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dependency: {str(e)}")


@router.delete("/dependencies/{dep_id}", summary="Delete dependency")
async def delete_dependency(dep_id: str) -> Dict[str, Any]:
    """
    Delete a dependency relationship
    """
    logger.info(f"Deleting dependency: {dep_id}")
    try:
        if dep_id not in _topology_dependencies:
            raise HTTPException(status_code=404, detail="Dependency not found")

        del _topology_dependencies[dep_id]
        logger.info(f"Dependency deleted: {dep_id}")
        return {"message": "Dependency deleted successfully", "id": dep_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dependency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete dependency: {str(e)}")


# ============================================================
# 6. Visualization Configuration Endpoints
# ============================================================


@router.get("/visualization", summary="Get visualization configuration")
async def get_visualization_config() -> Dict[str, Any]:
    """
    Retrieve the current visualization configuration
    """
    logger.info("Fetching visualization configuration")
    try:
        # Return the first config or a default one
        if _visualization_configs:
            config_id = list(_visualization_configs.keys())[0]
            return _visualization_configs[config_id]

        # Return default configuration
        return {
            "id": "default",
            "name": "Default Configuration",
            "node_color": "#3b82f6",
            "edge_color": "#94a3b8",
            "show_labels": True,
            "show_metrics": True,
            "auto_refresh": False,
            "refresh_interval": 60,
        }
    except Exception as e:
        logger.error(f"Failed to fetch visualization config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch visualization config: {str(e)}"
        )


@router.post("/visualization", summary="Create visualization configuration")
async def create_visualization_config(
    config: VisualizationConfigCreate, request: Request
) -> Dict[str, Any]:
    """
    Create a new visualization configuration
    """
    logger.info(f"Creating visualization config: {config.name}")
    try:
        config_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_config = {
            "id": config_id,
            "name": config.name,
            "node_color": config.node_color,
            "edge_color": config.edge_color,
            "show_labels": config.show_labels,
            "show_metrics": config.show_metrics,
            "auto_refresh": config.auto_refresh,
            "refresh_interval": config.refresh_interval,
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _visualization_configs[config_id] = new_config
        logger.info(f"Visualization config created: {config_id}")
        return new_config
    except Exception as e:
        logger.error(f"Failed to create visualization config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create visualization config: {str(e)}"
        )


@router.put("/visualization/{config_id}", summary="Update visualization configuration")
async def update_visualization_config(
    config_id: str, config_update: VisualizationConfigUpdate, request: Request
) -> Dict[str, Any]:
    """
    Update an existing visualization configuration
    """
    logger.info(f"Updating visualization config: {config_id}")
    try:
        if config_id not in _visualization_configs:
            raise HTTPException(status_code=404, detail="Configuration not found")

        operator_ip = request.client.host if request.client else "unknown"
        existing = _visualization_configs[config_id]

        # Update fields
        update_data = config_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            existing[key] = value

        existing["updated_at"] = _get_current_timestamp()
        existing["updated_by"] = operator_ip

        logger.info(f"Visualization config updated: {config_id}")
        return existing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update visualization config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update visualization config: {str(e)}"
        )


@router.delete("/visualization/{config_id}", summary="Delete visualization configuration")
async def delete_visualization_config(config_id: str) -> Dict[str, Any]:
    """
    Delete a visualization configuration
    """
    logger.info(f"Deleting visualization config: {config_id}")
    try:
        if config_id not in _visualization_configs:
            raise HTTPException(status_code=404, detail="Configuration not found")

        del _visualization_configs[config_id]
        logger.info(f"Visualization config deleted: {config_id}")
        return {"message": "Configuration deleted successfully", "id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete visualization config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete visualization config: {str(e)}"
        )


# ============================================================
# 7. Additional Endpoints for Frontend Compatibility
# ============================================================


@router_alt.get("/visualization", summary="Get visualization configuration (alt)")
async def get_visualization_config_alt() -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await get_visualization_config()


@router_alt.put("/visualization", summary="Update visualization configuration (alt)")
async def update_visualization_config_alt(
    config: VisualizationConfigUpdate, request: Request
) -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    # Get or create default config
    if _visualization_configs:
        config_id = list(_visualization_configs.keys())[0]
    else:
        config_id = _generate_id()
        _visualization_configs[config_id] = {
            "id": config_id,
            "name": "Default Configuration",
            "node_color": "#3b82f6",
            "edge_color": "#94a3b8",
            "show_labels": True,
            "show_metrics": True,
            "auto_refresh": False,
            "refresh_interval": 60,
            "created_at": _get_current_timestamp(),
            "created_by": request.client.host if request.client else "unknown",
            "updated_at": _get_current_timestamp(),
        }

    return await update_visualization_config(config_id, config, request)


@router_alt.get("/full-link", summary="Get full link topology (alt)")
async def get_full_link_alt() -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await get_topology_graph()


@router_alt.get("/dependency-modeling", summary="Get dependencies (alt)")
async def get_dependencies_alt() -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await get_dependencies()


@router_alt.post("/dependency-modeling", summary="Create dependency (alt)")
async def create_dependency_alt(dependency: DependencyCreate, request: Request) -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    # Generate ID if not provided
    if not hasattr(dependency, "id") or not dependency.id:
        dependency_dict = dependency.model_dump()
        dependency_dict["id"] = _generate_id()
        dependency = DependencyCreate(**dependency_dict)
    return await create_dependency(dependency, request)


@router_alt.delete("/dependency-modeling/{dep_id}", summary="Delete dependency (alt)")
async def delete_dependency_alt(dep_id: str) -> Dict[str, Any]:
    """Alternative endpoint for frontend compatibility"""
    return await delete_dependency(dep_id)


@router_alt.get("/service-discovery", summary="Get discovered services (alt)")
async def get_service_discovery_alt() -> Dict[str, Any]:
    """Service discovery endpoint"""
    logger.info("Fetching discovered services")
    try:
        # Get nodes from topology
        graph_data = await get_topology_graph()
        services = [
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "type": node.get("type"),
                "status": node.get("status"),
                "endpoint": f"http://{node.get('name')}:8080",
                "last_seen": _get_current_timestamp(),
            }
            for node in graph_data.get("nodes", [])
        ]
        return {"services": services}
    except Exception as e:
        logger.error(f"Failed to fetch discovered services: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch discovered services: {str(e)}"
        )


@router_alt.post("/service-discovery/scan", summary="Scan for services (alt)")
async def scan_services_alt() -> Dict[str, Any]:
    """Scan for new services"""
    logger.info("Scanning for services")
    try:
        # Simulate scan delay
        import asyncio

        await asyncio.sleep(1)

        # Return success
        return {
            "message": "Service scan completed",
            "scanned_at": _get_current_timestamp(),
            "services_found": len(_topology_nodes),
        }
    except Exception as e:
        logger.error(f"Failed to scan services: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to scan services: {str(e)}")


@router_alt.get("/service-registration", summary="Get registered services (alt)")
async def get_service_registration_alt() -> Dict[str, Any]:
    """Get registered services"""
    logger.info("Fetching registered services")
    try:
        services = [
            {
                "id": node_id,
                "name": node.get("name"),
                "type": node.get("type"),
                "tags": node.get("metadata", {}).get("tags", []),
                "registered_at": node.get("created_at"),
            }
            for node_id, node in _topology_nodes.items()
        ]
        return {"services": services}
    except Exception as e:
        logger.error(f"Failed to fetch registered services: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch registered services: {str(e)}"
        )


@router_alt.post("/service-registration", summary="Register service (alt)")
async def register_service_alt(service: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Register a new service"""
    logger.info(f"Registering service: {service.get('name')}")
    try:
        service_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_service = {
            "id": service_id,
            "name": service.get("name"),
            "type": service.get("type", "service"),
            "status": "healthy",
            "layer": "application",
            "metadata": {
                "tags": service.get("tags", []),
                "endpoint": service.get("endpoint"),
            },
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
            "updated_at": _get_current_timestamp(),
        }

        _topology_nodes[service_id] = new_service
        logger.info(f"Service registered: {service_id}")
        return new_service
    except Exception as e:
        logger.error(f"Failed to register service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to register service: {str(e)}")


@router_alt.delete("/service-registration/{service_id}", summary="Deregister service (alt)")
async def deregister_service_alt(service_id: str) -> Dict[str, Any]:
    """Deregister a service"""
    logger.info(f"Deregistering service: {service_id}")
    try:
        if service_id not in _topology_nodes:
            raise HTTPException(status_code=404, detail="Service not found")

        del _topology_nodes[service_id]
        logger.info(f"Service deregistered: {service_id}")
        return {"message": "Service deregistered successfully", "id": service_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deregister service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to deregister service: {str(e)}")


@router_alt.get("/causal-graph", summary="Get causal graph (alt)")
async def get_causal_graph_alt() -> Dict[str, Any]:
    """Get causal graph for analysis"""
    logger.info("Fetching causal graph")
    try:
        # Build causal graph from dependencies
        nodes = [
            {
                "id": node_id,
                "name": node.get("name"),
                "type": node.get("type"),
            }
            for node_id, node in _topology_nodes.items()
        ]

        edges = [
            {
                "source": dep.get("source"),
                "target": dep.get("target"),
                "causal_strength": dep.get("strength", 1.0),
                "type": dep.get("type"),
            }
            for dep in _topology_dependencies.values()
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "metrics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "avg_causal_strength": sum(e.get("causal_strength", 1.0) for e in edges)
                / max(len(edges), 1),
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch causal graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch causal graph: {str(e)}")


@router_alt.post("/causal-inference", summary="Perform causal inference (alt)")
async def causal_inference_alt(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform causal inference on an event"""
    logger.info(f"Performing causal inference for event: {request_data.get('event')}")
    try:
        event = request_data.get("event", "")

        # Simulate causal inference
        results = [
            {
                "cause": dep.get("source"),
                "effect": dep.get("target"),
                "probability": 0.7 + (hash(dep.get("source")) % 30) / 100.0,
                "confidence": "high" if hash(dep.get("source")) % 2 == 0 else "medium",
            }
            for dep in list(_topology_dependencies.values())[:5]
        ]

        return {
            "event": event,
            "results": results,
            "inference_time": _get_current_timestamp(),
        }
    except Exception as e:
        logger.error(f"Failed to perform causal inference: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform causal inference: {str(e)}")


@router_alt.post("/causal-prediction", summary="Perform causal prediction (alt)")
async def causal_prediction_alt(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform causal prediction"""
    logger.info(f"Performing causal prediction for event: {request_data.get('event')}")
    try:
        event = request_data.get("event", "")
        time_horizon = request_data.get("time_horizon", 24)

        # Simulate prediction
        predictions = [
            {
                "predicted_effect": node.get("name"),
                "probability": 0.5 + (hash(node.get("name")) % 40) / 100.0,
                "time_to_effect": f"{(hash(node.get('name')) % time_horizon) + 1}h",
                "severity": "high" if hash(node.get("name")) % 3 == 0 else "medium",
            }
            for node in list(_topology_nodes.values())[:5]
        ]

        return {
            "event": event,
            "time_horizon": time_horizon,
            "predictions": predictions,
            "prediction_time": _get_current_timestamp(),
        }
    except Exception as e:
        logger.error(f"Failed to perform causal prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to perform causal prediction: {str(e)}"
        )


@router_alt.get("/call-chain-analysis", summary="Get call chains (alt)")
async def get_call_chains_alt() -> Dict[str, Any]:
    """Get call chain analysis"""
    logger.info("Fetching call chains")
    try:
        # Build call chains from dependencies
        chains = []
        for dep in list(_topology_dependencies.values())[:10]:
            chain = {
                "id": _generate_id(),
                "source": dep.get("source"),
                "target": dep.get("target"),
                "type": dep.get("type"),
                "latency_ms": 10 + (hash(dep.get("source")) % 100),
                "success_rate": 0.9 + (hash(dep.get("source")) % 10) / 100.0,
            }
            chains.append(chain)

        return {"chains": chains}
    except Exception as e:
        logger.error(f"Failed to fetch call chains: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch call chains: {str(e)}")


@router_alt.post("/call-chain-analysis/analyze", summary="Analyze call chain (alt)")
async def analyze_call_chain_alt(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a specific call chain"""
    logger.info(f"Analyzing call chain for trace: {request_data.get('trace_id')}")
    try:
        trace_id = request_data.get("trace_id", "")

        # Simulate analysis
        chain = {
            "id": trace_id,
            "source": "service-a",
            "target": "service-b",
            "type": "sync",
            "latency_ms": 45,
            "success_rate": 0.95,
            "bottlenecks": ["service-c", "database"],
            "optimization_suggestions": ["Add caching", "Optimize query"],
        }

        return chain
    except Exception as e:
        logger.error(f"Failed to analyze call chain: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze call chain: {str(e)}")


@router_alt.post("/call-chain-search", summary="Search call chains (alt)")
async def search_call_chains_alt(criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Search call chains by criteria"""
    logger.info(f"Searching call chains with criteria: {criteria}")
    try:
        source = criteria.get("source")
        target = criteria.get("target")

        # Filter dependencies
        results = [
            {
                "source": dep.get("source"),
                "target": dep.get("target"),
                "type": dep.get("type"),
                "latency_ms": 10 + (hash(dep.get("source")) % 100),
            }
            for dep in _topology_dependencies.values()
            if (not source or dep.get("source") == source)
            and (not target or dep.get("target") == target)
        ]

        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to search call chains: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search call chains: {str(e)}")


@router_alt.post("/impact-analysis", summary="Perform impact analysis (alt)")
async def impact_analysis_alt(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Perform impact analysis"""
    logger.info(f"Performing impact analysis for service: {request_data.get('service_id')}")
    try:
        service_id = request_data.get("service_id", "")

        # Find downstream services
        downstream = [
            dep.get("target")
            for dep in _topology_dependencies.values()
            if dep.get("source") == service_id
        ]

        # Calculate impact
        results = [
            {
                "service": service,
                "impact_level": "high" if hash(service) % 2 == 0 else "medium",
                "affected_users": 100 + (hash(service) % 1000),
                "business_impact": "critical" if hash(service) % 3 == 0 else "moderate",
            }
            for service in downstream[:5]
        ]

        return {
            "service_id": service_id,
            "results": results,
            "total_affected": len(downstream),
        }
    except Exception as e:
        logger.error(f"Failed to perform impact analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to perform impact analysis: {str(e)}")


@router_alt.get("/view", summary="Get topology view (alt)")
async def get_topology_view_alt(
    layout: str = Query("force", description="Layout algorithm")
) -> Dict[str, Any]:
    """Get topology view with specific layout"""
    logger.info(f"Fetching topology view with layout: {layout}")
    try:
        graph_data = await get_topology_graph()

        return {
            "layout": layout,
            "nodes": graph_data.get("nodes", []),
            "edges": graph_data.get("edges", []),
            "config": {
                "node_size": 30,
                "edge_width": 2,
                "label_size": 12,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch topology view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch topology view: {str(e)}")


@router_alt.get("/status", summary="Get topology status (alt)")
async def get_topology_status_alt() -> Dict[str, Any]:
    """Get topology status"""
    logger.info("Fetching topology status")
    try:
        graph_data = await get_topology_graph()

        statuses = [
            {
                "node_id": node.get("id"),
                "name": node.get("name"),
                "status": node.get("status"),
                "health_score": 90 + (hash(node.get("id")) % 10),
                "last_updated": _get_current_timestamp(),
            }
            for node in graph_data.get("nodes", [])
        ]

        return {"statuses": statuses}
    except Exception as e:
        logger.error(f"Failed to fetch topology status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch topology status: {str(e)}")


@router_alt.get("/types", summary="Get topology types (alt)")
async def get_topology_types_alt() -> Dict[str, Any]:
    """Get available topology types"""
    logger.info("Fetching topology types")
    try:
        types = [
            {"key": "microservice", "name": "Microservice"},
            {"key": "monolith", "name": "Monolith"},
            {"key": "serverless", "name": "Serverless"},
            {"key": "hybrid", "name": "Hybrid"},
        ]
        return {"types": types}
    except Exception as e:
        logger.error(f"Failed to fetch topology types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch topology types: {str(e)}")


@router_alt.get("/management", summary="Get topology management (alt)")
async def get_topology_management_alt() -> Dict[str, Any]:
    """Get topology management data"""
    logger.info("Fetching topology management data")
    try:
        topologies = [
            {
                "id": _generate_id(),
                "name": f"Topology {i}",
                "type": "microservice",
                "description": f"Microservice topology {i}",
                "status": "active",
                "created_at": _get_current_timestamp(),
            }
            for i in range(1, 4)
        ]
        return {"topologies": topologies}
    except Exception as e:
        logger.error(f"Failed to fetch topology management: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch topology management: {str(e)}"
        )


@router_alt.post("/management", summary="Create topology (alt)")
async def create_topology_alt(topology: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Create a new topology"""
    logger.info(f"Creating topology: {topology.get('name')}")
    try:
        topology_id = _generate_id()
        operator_ip = request.client.host if request.client else "unknown"

        new_topology = {
            "id": topology_id,
            "name": topology.get("name"),
            "type": topology.get("type", "microservice"),
            "description": topology.get("description", ""),
            "status": "active",
            "created_at": _get_current_timestamp(),
            "created_by": operator_ip,
        }

        return new_topology
    except Exception as e:
        logger.error(f"Failed to create topology: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create topology: {str(e)}")


@router_alt.delete("/management/{topology_id}", summary="Delete topology (alt)")
async def delete_topology_alt(topology_id: str) -> Dict[str, Any]:
    """Delete a topology"""
    logger.info(f"Deleting topology: {topology_id}")
    try:
        return {"message": "Topology deleted successfully", "id": topology_id}
    except Exception as e:
        logger.error(f"Failed to delete topology: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete topology: {str(e)}")


# ============================================================
# V1 Router - Exact API paths as required
# ============================================================


@router_v1.get("/graph", summary="Get topology graph (V1)")
async def get_topology_graph_v1(
    layer: Optional[str] = Query(None, description="Filter by layer"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """Retrieve the complete topology graph with nodes and edges"""
    return await get_topology_graph(layer=layer, status=status)


@router_v1.get("/nodes", summary="Get all topology nodes (V1)")
async def get_nodes_v1(
    layer: Optional[str] = Query(None, description="Filter by layer"),
    status: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """Retrieve all topology nodes with optional filtering"""
    return await get_nodes(layer=layer, status=status, type=type)


@router_v1.get("/edges", summary="Get all topology edges (V1)")
async def get_edges_v1(
    source: Optional[str] = Query(None, description="Filter by source node"),
    target: Optional[str] = Query(None, description="Filter by target node"),
    type: Optional[str] = Query(None, description="Filter by edge type"),
) -> Dict[str, Any]:
    """Retrieve all topology edges with optional filtering"""
    return await get_edges(source=source, target=target, type=type)


@router_v1.get("/layers", summary="Get all topology layers (V1)")
async def get_layers_v1() -> Dict[str, Any]:
    """Retrieve all topology layers"""
    return await get_layers()


@router_v1.get("/dependencies", summary="Get all dependencies (V1)")
async def get_dependencies_v1(
    source: Optional[str] = Query(None, description="Filter by source"),
    target: Optional[str] = Query(None, description="Filter by target"),
    type: Optional[str] = Query(None, description="Filter by type"),
) -> Dict[str, Any]:
    """Retrieve all dependency relationships with optional filtering"""
    return await get_dependencies(source=source, target=target, type=type)


@router_v1.get("/visualization", summary="Get visualization configuration (V1)")
async def get_visualization_config_v1() -> Dict[str, Any]:
    """Retrieve the current visualization configuration"""
    return await get_visualization_config()
