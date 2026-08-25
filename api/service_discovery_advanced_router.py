# -*- coding: utf-8 -*-
"""
Service Discovery Advanced API Router
Provides advanced API endpoints for service discovery with full CRUD operations
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/service-discovery", tags=["Service Discovery Advanced"])


# Pydantic Models
class ServiceCreate(BaseModel):
    """Service creation model"""

    name: str = Field(..., description="Service name")
    host: str = Field(..., description="Service host address")
    port: int = Field(..., ge=1, le=65535, description="Service port")
    protocol: str = Field(default="http", description="Service protocol")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Service metadata")
    weight: int = Field(default=1, ge=1, le=100, description="Load balancing weight")


class ServiceUpdate(BaseModel):
    """Service update model"""

    name: Optional[str] = Field(None, description="Service name")
    host: Optional[str] = Field(None, description="Service host address")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Service port")
    protocol: Optional[str] = Field(None, description="Service protocol")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Service metadata")
    weight: Optional[int] = Field(None, ge=1, le=100, description="Load balancing weight")


class HealthCheckCreate(BaseModel):
    """Health check creation model"""

    service_id: str = Field(..., description="Service ID")
    check_type: str = Field(default="http", description="Health check type")
    endpoint: str = Field(default="/health", description="Health check endpoint")
    interval_seconds: int = Field(default=30, ge=5, description="Check interval in seconds")
    timeout_seconds: int = Field(default=5, ge=1, description="Check timeout in seconds")
    healthy_threshold: int = Field(default=2, ge=1, description="Healthy threshold")
    unhealthy_threshold: int = Field(default=3, ge=1, description="Unhealthy threshold")


class ServiceRegistration(BaseModel):
    """Service registration model"""

    service_name: str = Field(..., description="Service name")
    instance_id: str = Field(..., description="Instance ID")
    host: str = Field(..., description="Host address")
    port: int = Field(..., ge=1, le=65535, description="Port number")
    weight: int = Field(default=1, ge=1, le=100, description="Instance weight")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Instance metadata")


class ServiceDeregistration(BaseModel):
    """Service deregistration model"""

    service_name: str = Field(..., description="Service name")
    instance_id: str = Field(..., description="Instance ID")


# In-memory storage (in production, use a database)
_services_db: Dict[str, Dict[str, Any]] = {}
_health_checks_db: Dict[str, Dict[str, Any]] = {}


def _generate_service_id() -> str:
    """Generate unique service ID"""
    return str(uuid4())


def _generate_health_check_id() -> str:
    """Generate unique health check ID"""
    return str(uuid4())


@router.get(
    "/services",
    summary="List all services",
    responses={
        200: {"description": "List of services"},
        500: {"description": "Internal server error"},
    },
)
async def list_services(
    status: Optional[str] = Query(None, description="Filter by status"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all registered services with optional filtering

    Args:
        status: Filter by service status
        protocol: Filter by protocol
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of services
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        summary = manager.get_service_summary()

        # Filter services
        filtered_services = []
        for service_id, service in _services_db.items():
            if status and service.get("status") != status:
                continue
            if protocol and service.get("protocol") != protocol:
                continue
            filtered_services.append({"id": service_id, **service})

        # Apply pagination
        total = len(filtered_services)
        paginated_services = filtered_services[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "services": paginated_services,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/services",
    summary="Create a new service",
    responses={
        201: {"description": "Service created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_service(service: ServiceCreate):
    """
    Create a new service

    Args:
        service: Service creation data

    Returns:
        Created service
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        service_id = _generate_service_id()
        instance_id = f"{service.name}-{service_id[:8]}"

        # Create service in database
        _services_db[service_id] = {
            "name": service.name,
            "host": service.host,
            "port": service.port,
            "protocol": service.protocol,
            "metadata": service.metadata,
            "weight": service.weight,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Register with service discovery manager
        manager = get_service_discovery_manager()
        manager.register_service(
            service_name=service.name,
            instance_id=instance_id,
            host=service.host,
            port=service.port,
            metadata=service.metadata,
            weight=service.weight,
        )

        logger.info(f"Created service: {service.name} with ID: {service_id}")

        return {
            "status": "success",
            "data": {"id": service_id, "instance_id": instance_id, **_services_db[service_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/services/{service_id}",
    summary="Get service by ID",
    responses={
        200: {"description": "Service details"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_service(service_id: str):
    """
    Get service details by ID

    Args:
        service_id: Service ID

    Returns:
        Service details
    """
    try:
        if service_id not in _services_db:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

        service = _services_db[service_id]

        # Get additional details from service discovery manager
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        details = manager.get_service_details(service["name"])

        return {
            "status": "success",
            "data": {"id": service_id, **service, "discovery_details": details},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/services/{service_id}",
    summary="Update service",
    responses={
        200: {"description": "Service updated successfully"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_service(service_id: str, service_update: ServiceUpdate):
    """
    Update service details

    Args:
        service_id: Service ID
        service_update: Service update data

    Returns:
        Updated service
    """
    try:
        if service_id not in _services_db:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

        service = _services_db[service_id]

        # Update fields
        if service_update.name is not None:
            service["name"] = service_update.name
        if service_update.host is not None:
            service["host"] = service_update.host
        if service_update.port is not None:
            service["port"] = service_update.port
        if service_update.protocol is not None:
            service["protocol"] = service_update.protocol
        if service_update.metadata is not None:
            service["metadata"] = service_update.metadata
        if service_update.weight is not None:
            service["weight"] = service_update.weight

        service["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Updated service: {service_id}")

        return {
            "status": "success",
            "data": {"id": service_id, **service},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/services/{service_id}",
    summary="Delete service",
    responses={
        200: {"description": "Service deleted successfully"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_service(service_id: str):
    """
    Delete service by ID

    Args:
        service_id: Service ID

    Returns:
        Deletion result
    """
    try:
        if service_id not in _services_db:
            raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

        service = _services_db[service_id]
        service_name = service["name"]

        # Deregister from service discovery manager
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        instance_id = f"{service_name}-{service_id[:8]}"
        manager.deregister_service(service_name, instance_id)

        # Remove from database
        del _services_db[service_id]

        logger.info(f"Deleted service: {service_id}")

        return {
            "status": "success",
            "data": {"id": service_id, "message": "Service deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health-checks",
    summary="List all health checks",
    responses={
        200: {"description": "List of health checks"},
        500: {"description": "Internal server error"},
    },
)
async def list_health_checks(
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """
    List all health checks with optional filtering

    Args:
        service_id: Filter by service ID
        status: Filter by status

    Returns:
        List of health checks
    """
    try:
        filtered_checks = []
        for check_id, check in _health_checks_db.items():
            if service_id and check.get("service_id") != service_id:
                continue
            if status and check.get("status") != status:
                continue
            filtered_checks.append({"id": check_id, **check})

        return {
            "status": "success",
            "data": {
                "health_checks": filtered_checks,
                "total": len(filtered_checks),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing health checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/health-checks",
    summary="Create a health check",
    responses={
        201: {"description": "Health check created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_health_check(health_check: HealthCheckCreate):
    """
    Create a new health check

    Args:
        health_check: Health check creation data

    Returns:
        Created health check
    """
    try:
        check_id = _generate_health_check_id()

        # Validate service exists
        if health_check.service_id not in _services_db:
            raise HTTPException(
                status_code=404, detail=f"Service {health_check.service_id} not found"
            )

        # Create health check
        _health_checks_db[check_id] = {
            "service_id": health_check.service_id,
            "check_type": health_check.check_type,
            "endpoint": health_check.endpoint,
            "interval_seconds": health_check.interval_seconds,
            "timeout_seconds": health_check.timeout_seconds,
            "healthy_threshold": health_check.healthy_threshold,
            "unhealthy_threshold": health_check.unhealthy_threshold,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created health check: {check_id} for service: {health_check.service_id}")

        return {
            "status": "success",
            "data": {"id": check_id, **_health_checks_db[check_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/endpoints",
    summary="List all service endpoints",
    responses={
        200: {"description": "List of endpoints"},
        500: {"description": "Internal server error"},
    },
)
async def list_endpoints(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    healthy_only: bool = Query(False, description="Only return healthy endpoints"),
):
    """
    List all service endpoints

    Args:
        service_name: Filter by service name
        healthy_only: Only return healthy endpoints

    Returns:
        List of endpoints
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        summary = manager.get_service_summary()

        endpoints = []
        for service_id, service in _services_db.items():
            if service_name and service["name"] != service_name:
                continue
            if healthy_only and service.get("status") != "active":
                continue

            endpoints.append(
                {
                    "id": service_id,
                    "service_name": service["name"],
                    "host": service["host"],
                    "port": service["port"],
                    "protocol": service["protocol"],
                    "status": service.get("status", "unknown"),
                    "url": f"{service['protocol']}://{service['host']}:{service['port']}",
                }
            )

        return {
            "status": "success",
            "data": {
                "endpoints": endpoints,
                "total": len(endpoints),
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/registrations",
    summary="List all service registrations",
    responses={
        200: {"description": "List of service registrations"},
        500: {"description": "Internal server error"},
    },
)
async def list_registrations(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all service registrations with optional filtering

    Args:
        service_name: Filter by service name
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of service registrations
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        summary = manager.get_service_summary()

        registrations = []
        for service_id, service in _services_db.items():
            if service_name and service["name"] != service_name:
                continue
            if status and service.get("status") != status:
                continue

            instance_id = f"{service['name']}-{service_id[:8]}"
            registrations.append(
                {
                    "id": service_id,
                    "instance_id": instance_id,
                    "service_name": service["name"],
                    "host": service["host"],
                    "port": service["port"],
                    "status": service.get("status", "unknown"),
                    "weight": service.get("weight", 1),
                    "registered_at": service.get("created_at"),
                }
            )

        # Apply pagination
        total = len(registrations)
        paginated_registrations = registrations[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "registrations": paginated_registrations,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing registrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/registrations",
    summary="Register a service instance",
    responses={
        201: {"description": "Service registered successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def register_service(registration: ServiceRegistration):
    """
    Register a service instance

    Args:
        registration: Service registration data

    Returns:
        Registration result
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        instance = manager.register_service(
            service_name=registration.service_name,
            instance_id=registration.instance_id,
            host=registration.host,
            port=registration.port,
            metadata=registration.metadata,
            weight=registration.weight,
        )

        logger.info(
            f"Registered service instance: {registration.service_name}/{registration.instance_id}"
        )

        return {
            "status": "success",
            "data": {
                "instance_id": instance.instance_id,
                "service_name": instance.service_name,
                "host": instance.host,
                "port": instance.port,
                "status": instance.status.value,
                "weight": instance.weight,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/deregistration",
    summary="Deregister a service instance",
    responses={
        200: {"description": "Service deregistered successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def deregister_service(deregistration: ServiceDeregistration):
    """
    Deregister a service instance

    Args:
        deregistration: Service deregistration data

    Returns:
        Deregistration result
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        success = manager.deregister_service(
            deregistration.service_name, deregistration.instance_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Service instance {deregistration.service_name}/"
                    f"{deregistration.instance_id} not found"
                ),
            )

        logger.info(
            f"Deregistered service instance: {deregistration.service_name}/"
            f"{deregistration.instance_id}"
        )

        return {
            "status": "success",
            "data": {
                "success": success,
                "service_name": deregistration.service_name,
                "instance_id": deregistration.instance_id,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deregistering service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/instances",
    summary="List all service instances",
    responses={
        200: {"description": "List of service instances"},
        500: {"description": "Internal server error"},
    },
)
async def list_instances(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List all service instances with optional filtering

    Args:
        service_name: Filter by service name
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of service instances
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        summary = manager.get_service_summary()

        instances = []
        for service_id, service in _services_db.items():
            if service_name and service["name"] != service_name:
                continue
            if status and service.get("status") != status:
                continue

            instance_id = f"{service['name']}-{service_id[:8]}"
            instances.append(
                {
                    "id": service_id,
                    "instance_id": instance_id,
                    "service_name": service["name"],
                    "host": service["host"],
                    "port": service["port"],
                    "protocol": service.get("protocol", "http"),
                    "status": service.get("status", "unknown"),
                    "weight": service.get("weight", 1),
                    "metadata": service.get("metadata", {}),
                    "created_at": service.get("created_at"),
                    "updated_at": service.get("updated_at"),
                }
            )

        # Apply pagination
        total = len(instances)
        paginated_instances = instances[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "instances": paginated_instances,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))
