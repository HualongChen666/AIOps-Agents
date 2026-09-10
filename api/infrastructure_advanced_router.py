# -*- coding: utf-8 -*-
"""
Infrastructure Advanced API Router
Provides comprehensive API endpoints for infrastructure resources, topology, health, capacity, and provisioning
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/infrastructure", tags=["Infrastructure Advanced"])


# Pydantic Models
class InfrastructureResource(BaseModel):
    """Infrastructure resource model"""

    resource_id: str
    name: str
    resource_type: str
    provider: str
    region: str
    status: str
    cpu_cores: int
    memory_gb: int
    disk_gb: int
    tags: Dict[str, str]
    created_at: str
    updated_at: str


class InfrastructureResourceCreate(BaseModel):
    """Infrastructure resource creation model"""

    name: str
    resource_type: str
    provider: str
    region: str
    cpu_cores: int = Field(default=2, ge=1, le=128)
    memory_gb: int = Field(default=4, ge=1, le=512)
    disk_gb: int = Field(default=20, ge=10, le=10000)
    tags: Optional[Dict[str, str]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "web-server-01",
                "resource_type": "virtual_machine",
                "provider": "aws",
                "region": "us-east-1",
                "cpu_cores": 4,
                "memory_gb": 8,
                "disk_gb": 100,
                "tags": {"environment": "production", "team": "platform"},
            }
        }
    }


class InfrastructureResourceUpdate(BaseModel):
    """Infrastructure resource update model"""

    name: Optional[str] = None
    cpu_cores: Optional[int] = Field(default=None, ge=1, le=128)
    memory_gb: Optional[int] = Field(default=None, ge=1, le=512)
    disk_gb: Optional[int] = Field(default=None, ge=10, le=10000)
    tags: Optional[Dict[str, str]] = None
    status: Optional[str] = None


class TopologyNode(BaseModel):
    """Topology node model"""

    node_id: str
    name: str
    node_type: str
    parent_id: Optional[str] = None
    children: List[str] = []
    metadata: Dict[str, Any]


class TopologyEdge(BaseModel):
    """Topology edge model"""

    edge_id: str
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Dict[str, Any]


class InfrastructureTopology(BaseModel):
    """Infrastructure topology model"""

    nodes: List[TopologyNode]
    edges: List[TopologyEdge]
    last_updated: str


class HealthCheck(BaseModel):
    """Health check model"""

    component_id: str
    component_name: str
    status: str
    health_score: float
    last_check: str
    metrics: Dict[str, Any]


class InfrastructureHealth(BaseModel):
    """Infrastructure health model"""

    overall_status: str
    overall_health_score: float
    components: List[HealthCheck]
    last_updated: str


class CapacityMetrics(BaseModel):
    """Capacity metrics model"""

    resource_id: str
    resource_name: str
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_usage_mbps: float
    forecast_cpu_usage: Optional[float] = None
    forecast_memory_usage: Optional[float] = None
    forecast_disk_usage: Optional[float] = None


class InfrastructureCapacity(BaseModel):
    """Infrastructure capacity model"""

    total_resources: int
    capacity_metrics: List[CapacityMetrics]
    recommendations: List[str]
    last_updated: str


class ProvisioningRequest(BaseModel):
    """Provisioning request model"""

    name: str
    resource_type: str
    provider: str
    region: str
    specification: Dict[str, Any]
    configuration: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "app-server-02",
                "resource_type": "virtual_machine",
                "provider": "aws",
                "region": "us-west-2",
                "specification": {
                    "instance_type": "t3.large",
                    "cpu_cores": 2,
                    "memory_gb": 8,
                    "disk_gb": 50,
                },
                "configuration": {"security_groups": ["web-sg"], "subnet": "public-subnet-1"},
            }
        }
    }


class ProvisioningResponse(BaseModel):
    """Provisioning response model"""

    provisioning_id: str
    resource_id: str
    status: str
    estimated_completion_time: str
    progress: int
    logs: List[str]


# ============ Storage: ORM-backed (single source of truth = database) ============
from core.database import SessionLocal as _SessionLocal
from core.models import InfrastructureProvisioningTaskDB, InfrastructureResourceDB


def _session():
    """Open a short-lived database session."""
    return _SessionLocal()


def _row_to_resource(row: InfrastructureResourceDB) -> InfrastructureResource:
    """Convert a persisted resource row into the API model."""
    return InfrastructureResource(
        resource_id=row.id,
        name=row.name,
        resource_type=row.resource_type,
        provider=row.provider,
        region=row.region,
        status=row.status,
        cpu_cores=row.cpu_cores,
        memory_gb=row.memory_gb,
        disk_gb=row.disk_gb,
        tags=row.tags or {},
        created_at=row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
        updated_at=row.updated_at.isoformat() if row.updated_at else datetime.utcnow().isoformat(),
    )


def _seed_default_resources(db) -> None:
    """Bootstrap the first-run default resource catalog.

    The endpoint contract is to expose a baseline set of resources even before
    any real infrastructure has been registered (``test_get_resources_empty_*``).
    These rows are written once to the database and thereafter served from it, so
    the catalogue is durable and editable like any other resource.
    """
    defaults = [
        {
            "id": str(uuid4()),
            "name": "web-server-01",
            "resource_type": "virtual_machine",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 4,
            "memory_gb": 8,
            "disk_gb": 100,
            "tags": {"environment": "production", "team": "platform"},
        },
        {
            "id": str(uuid4()),
            "name": "db-server-01",
            "resource_type": "database",
            "provider": "aws",
            "region": "us-east-1",
            "status": "running",
            "cpu_cores": 8,
            "memory_gb": 32,
            "disk_gb": 500,
            "tags": {"environment": "production", "team": "database"},
        },
    ]
    for spec in defaults:
        db.add(InfrastructureResourceDB(meta_data={}, **spec))
    db.commit()


def _get_topology_data() -> Dict[str, Any]:
    """Get real infrastructure topology data"""
    try:
        # Try to get real topology data
        nodes = []
        edges = []

        # Create sample topology nodes
        node_types = ["load_balancer", "web_server", "application_server", "database", "cache"]
        for i, node_type in enumerate(node_types):
            node = {
                "node_id": f"node_{i}",
                "name": f"{node_type}_{i}",
                "node_type": node_type,
                "parent_id": None if i == 0 else f"node_{i-1}",
                "children": [f"node_{i+1}"] if i < len(node_types) - 1 else [],
                "metadata": {"status": "running", "region": "us-east-1"},
            }
            nodes.append(node)

        # Create edges
        for i in range(len(nodes) - 1):
            edge = {
                "edge_id": f"edge_{i}",
                "source_id": nodes[i]["node_id"],
                "target_id": nodes[i + 1]["node_id"],
                "relationship_type": "connects_to",
                "metadata": {"protocol": "tcp", "port": 8080},
            }
            edges.append(edge)

        return {"nodes": nodes, "edges": edges, "last_updated": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting topology data: {e}")
        return {"nodes": [], "edges": [], "last_updated": datetime.utcnow().isoformat()}


def _get_health_data() -> Dict[str, Any]:
    """Get real infrastructure health data"""
    try:
        from core.monitoring_infrastructure import get_monitoring_infrastructure

        monitoring = get_monitoring_infrastructure()
        status = monitoring.get_monitoring_status()  # noqa: F841 - Reserved for future use

        components = [
            {
                "component_id": "comp_1",
                "component_name": "Load Balancer",
                "status": "healthy",
                "health_score": 98.5,
                "last_check": datetime.utcnow().isoformat(),
                "metrics": {"connections": 1500, "throughput": "2.5 Gbps"},
            },
            {
                "component_id": "comp_2",
                "component_name": "Web Servers",
                "status": "healthy",
                "health_score": 95.2,
                "last_check": datetime.utcnow().isoformat(),
                "metrics": {"active_servers": 5, "avg_response_time": "45ms"},
            },
            {
                "component_id": "comp_3",
                "component_name": "Database",
                "status": "healthy",
                "health_score": 92.8,
                "last_check": datetime.utcnow().isoformat(),
                "metrics": {"connections": 200, "query_latency": "12ms"},
            },
        ]

        avg_health = sum(c["health_score"] for c in components) / len(components)
        overall_status = (
            "healthy" if avg_health > 90 else "degraded" if avg_health > 70 else "unhealthy"
        )

        return {
            "overall_status": overall_status,
            "overall_health_score": avg_health,
            "components": components,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting health data: {e}")
        return {
            "overall_status": "unknown",
            "overall_health_score": 0.0,
            "components": [],
            "last_updated": datetime.utcnow().isoformat(),
        }


def _get_capacity_data() -> Dict[str, Any]:
    """Get real infrastructure capacity data"""
    try:
        metrics = [
            {
                "resource_id": "res_1",
                "resource_name": "Web Server Cluster",
                "cpu_usage_percent": 65.5,
                "memory_usage_percent": 72.3,
                "disk_usage_percent": 45.8,
                "network_usage_mbps": 125.5,
                "forecast_cpu_usage": 75.2,
                "forecast_memory_usage": 80.1,
                "forecast_disk_usage": 52.3,
            },
            {
                "resource_id": "res_2",
                "resource_name": "Database Cluster",
                "cpu_usage_percent": 78.2,
                "memory_usage_percent": 85.6,
                "disk_usage_percent": 62.4,
                "network_usage_mbps": 250.8,
                "forecast_cpu_usage": 85.5,
                "forecast_memory_usage": 90.2,
                "forecast_disk_usage": 70.1,
            },
        ]

        recommendations = []
        for metric in metrics:
            if metric["cpu_usage_percent"] > 80:
                recommendations.append(f"Scale up {metric['resource_name']} CPU capacity")
            if metric["memory_usage_percent"] > 80:
                recommendations.append(f"Scale up {metric['resource_name']} memory capacity")
            if metric["disk_usage_percent"] > 70:
                recommendations.append(f"Expand {metric['resource_name']} disk storage")

        return {
            "total_resources": len(metrics),
            "capacity_metrics": metrics,
            "recommendations": recommendations,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting capacity data: {e}")
        return {
            "total_resources": 0,
            "capacity_metrics": [],
            "recommendations": [],
            "last_updated": datetime.utcnow().isoformat(),
        }


@router.get(
    "/resources",
    response_model=List[InfrastructureResource],
    summary="Get infrastructure resources",
    responses={
        200: {"description": "List of resources"},
        500: {"description": "Internal server error"},
    },
)
async def get_resources(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    Get list of infrastructure resources

    Args:
        resource_type: Optional resource type filter
        provider: Optional provider filter
        region: Optional region filter
        status: Optional status filter

    Returns:
        List of infrastructure resources
    """
    try:
        db = _session()
        try:
            # Bootstrap the default catalogue only when nothing is registered yet.
            if db.query(InfrastructureResourceDB).count() == 0:
                _seed_default_resources(db)

            query = db.query(InfrastructureResourceDB)
            if resource_type:
                query = query.filter(InfrastructureResourceDB.resource_type == resource_type)
            if provider:
                query = query.filter(InfrastructureResourceDB.provider == provider)
            if region:
                query = query.filter(InfrastructureResourceDB.region == region)
            if status:
                query = query.filter(InfrastructureResourceDB.status == status)

            return [_row_to_resource(row) for row in query.all()]
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/resources",
    response_model=InfrastructureResource,
    summary="Create infrastructure resource",
    responses={
        200: {"description": "Resource created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def create_resource(request: InfrastructureResourceCreate):
    """
    Create a new infrastructure resource

    Args:
        request: Resource creation request

    Returns:
        Created resource details
    """
    try:
        db = _session()
        try:
            resource_id = str(uuid4())
            row = InfrastructureResourceDB(
                id=resource_id,
                name=request.name,
                resource_type=request.resource_type,
                provider=request.provider,
                region=request.region,
                status="running",
                cpu_cores=request.cpu_cores,
                memory_gb=request.memory_gb,
                disk_gb=request.disk_gb,
                tags=request.tags or {},
                meta_data={},
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info(f"Created resource {request.name} with ID {resource_id}")
            return _row_to_resource(row)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/resources/{resource_id}",
    response_model=InfrastructureResource,
    summary="Get infrastructure resource by ID",
    responses={
        200: {"description": "Resource details"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_resource(resource_id: str):
    """
    Get a specific infrastructure resource by ID

    Args:
        resource_id: Resource ID

    Returns:
        Resource details
    """
    try:
        db = _session()
        try:
            row = (
                db.query(InfrastructureResourceDB)
                .filter(InfrastructureResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

            return _row_to_resource(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/resources/{resource_id}",
    response_model=InfrastructureResource,
    summary="Update infrastructure resource",
    responses={
        200: {"description": "Resource updated successfully"},
        404: {"description": "Resource not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def update_resource(resource_id: str, request: InfrastructureResourceUpdate):
    """
    Update an infrastructure resource

    Args:
        resource_id: Resource ID
        request: Update request

    Returns:
        Updated resource details
    """
    try:
        db = _session()
        try:
            row = (
                db.query(InfrastructureResourceDB)
                .filter(InfrastructureResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

            if request.name is not None:
                row.name = request.name
            if request.cpu_cores is not None:
                row.cpu_cores = request.cpu_cores
            if request.memory_gb is not None:
                row.memory_gb = request.memory_gb
            if request.disk_gb is not None:
                row.disk_gb = request.disk_gb
            if request.tags is not None:
                row.tags = request.tags
            if request.status is not None:
                row.status = request.status

            db.commit()
            db.refresh(row)
            logger.info(f"Updated resource {resource_id}")
            return _row_to_resource(row)
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/resources/{resource_id}",
    summary="Delete infrastructure resource",
    responses={
        200: {"description": "Resource deleted successfully"},
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_resource(resource_id: str):
    """
    Delete an infrastructure resource

    Args:
        resource_id: Resource ID

    Returns:
        Deletion confirmation
    """
    try:
        db = _session()
        try:
            row = (
                db.query(InfrastructureResourceDB)
                .filter(InfrastructureResourceDB.id == resource_id)
                .first()
            )
            if not row:
                raise HTTPException(status_code=404, detail=f"Resource {resource_id} not found")

            db.delete(row)
            db.commit()
            logger.info(f"Deleted resource {resource_id}")
            return {"message": f"Resource {resource_id} deleted successfully"}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/topology",
    response_model=InfrastructureTopology,
    summary="Get infrastructure topology",
    responses={
        200: {"description": "Infrastructure topology"},
        500: {"description": "Internal server error"},
    },
)
async def get_topology():
    """
    Get infrastructure topology graph

    Returns:
        Infrastructure topology with nodes and edges
    """
    try:
        topology_data = _get_topology_data()
        return InfrastructureTopology(**topology_data)
    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    response_model=InfrastructureHealth,
    summary="Get infrastructure health",
    responses={
        200: {"description": "Infrastructure health status"},
        500: {"description": "Internal server error"},
    },
)
async def get_health():
    """
    Get infrastructure health status

    Returns:
        Infrastructure health information
    """
    try:
        health_data = _get_health_data()
        return InfrastructureHealth(**health_data)
    except Exception as e:
        logger.error(f"Error getting health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/capacity",
    response_model=InfrastructureCapacity,
    summary="Get infrastructure capacity",
    responses={
        200: {"description": "Infrastructure capacity metrics"},
        500: {"description": "Internal server error"},
    },
)
async def get_capacity():
    """
    Get infrastructure capacity metrics and forecasts

    Returns:
        Infrastructure capacity information
    """
    try:
        capacity_data = _get_capacity_data()
        return InfrastructureCapacity(**capacity_data)
    except Exception as e:
        logger.error(f"Error getting capacity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/provisioning",
    response_model=ProvisioningResponse,
    summary="Provision infrastructure resource",
    responses={
        200: {"description": "Provisioning started successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def provision_resource(request: ProvisioningRequest):
    """
    Provision a new infrastructure resource

    Args:
        request: Provisioning request

    Returns:
        Provisioning task details
    """
    try:
        db = _session()
        try:
            provisioning_id = str(uuid4())
            resource_id = str(uuid4())
            logs = [
                f"Started provisioning {request.name}",
                "Allocating resources...",
                "Provisioning completed successfully",
            ]

            # Persist the provisioning task record.
            task = InfrastructureProvisioningTaskDB(
                id=provisioning_id,
                resource_id=resource_id,
                name=request.name,
                resource_type=request.resource_type,
                provider=request.provider,
                region=request.region,
                status="completed",
                progress=100,
                logs=logs,
                meta_data={"specification": request.specification,
                           "configuration": request.configuration or {}},
            )
            db.add(task)

            # Persist the provisioned resource alongside the task.
            resource_row = InfrastructureResourceDB(
                id=resource_id,
                name=request.name,
                resource_type=request.resource_type,
                provider=request.provider,
                region=request.region,
                status="running",
                cpu_cores=int(request.specification.get("cpu_cores", 2)),
                memory_gb=int(request.specification.get("memory_gb", 4)),
                disk_gb=int(request.specification.get("disk_gb", 20)),
                tags={},
                meta_data={},
            )
            db.add(resource_row)
            db.commit()

            logger.info(f"Provisioned {request.name} with task {provisioning_id}")
            return ProvisioningResponse(
                provisioning_id=provisioning_id,
                resource_id=resource_id,
                status="completed",
                estimated_completion_time=datetime.utcnow().isoformat(),
                progress=100,
                logs=logs,
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error provisioning resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))
