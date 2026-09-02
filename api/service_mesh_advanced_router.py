# -*- coding: utf-8 -*-
"""
Service Mesh Advanced API Router
Provides advanced API endpoints for service mesh management with full CRUD operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel, Field

from core.auth import (
    check_rate_limit,
    get_current_user,
    require_permission,
    rate_limiter,
    verify_token,
)
from core.database import get_db
from core.models import User
from core.service_mesh_repository import ServiceMeshRepository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/service-mesh", tags=["Service Mesh Advanced"])


# Pydantic Models
class MeshConfigurationCreate(BaseModel):
    """Mesh configuration creation model"""

    name: str = Field(..., description="Configuration name")
    mesh_type: str = Field(default="istio", description="Mesh type (istio, linkerd, consul)")
    namespace: str = Field(default="istio-system", description="Kubernetes namespace")
    profile: str = Field(default="default", description="Mesh profile")
    auto_injection_enabled: bool = Field(default=True, description="Enable auto-injection")
    mtls_enabled: bool = Field(default=True, description="Enable mTLS")
    resource_limits: Dict[str, Any] = Field(default_factory=dict, description="Resource limits")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Configuration metadata")


class MeshConfigurationUpdate(BaseModel):
    """Mesh configuration update model"""

    name: Optional[str] = Field(None, description="Configuration name")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace")
    profile: Optional[str] = Field(None, description="Mesh profile")
    auto_injection_enabled: Optional[bool] = Field(None, description="Enable auto-injection")
    mtls_enabled: Optional[bool] = Field(None, description="Enable mTLS")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Configuration metadata")


class TrafficRuleCreate(BaseModel):
    """Traffic rule creation model"""

    name: str = Field(..., description="Rule name")
    service_name: str = Field(..., description="Target service name")
    match_conditions: Dict[str, Any] = Field(..., description="Match conditions")
    destination: Dict[str, Any] = Field(..., description="Destination configuration")
    weight: int = Field(default=100, ge=0, le=100, description="Traffic weight")
    timeout_seconds: int = Field(default=30, ge=1, description="Request timeout")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry policy")
    fault_injection: Optional[Dict[str, Any]] = Field(None, description="Fault injection config")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Rule metadata")


class SecurityPolicyCreate(BaseModel):
    """Security policy creation model"""

    name: str = Field(..., description="Policy name")
    policy_type: str = Field(
        ..., description="Policy type (authentication, authorization, security)"
    )
    target_service: str = Field(..., description="Target service")
    mtls_mode: str = Field(default="STRICT", description="mTLS mode (STRICT, PERMISSIVE, DISABLE)")
    allowed_principals: List[str] = Field(default_factory=list, description="Allowed principals")
    denied_principals: List[str] = Field(default_factory=list, description="Denied principals")
    jwt_validation: Optional[Dict[str, Any]] = Field(None, description="JWT validation config")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Policy metadata")


class ObservabilityConfigCreate(BaseModel):
    """Observability configuration creation model"""

    name: str = Field(..., description="Configuration name")
    tracing_enabled: bool = Field(default=True, description="Enable tracing")
    metrics_enabled: bool = Field(default=True, description="Enable metrics")
    access_logging_enabled: bool = Field(default=True, description="Enable access logging")
    sampling_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Sampling rate")
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus")
    grafana_enabled: bool = Field(default=False, description="Enable Grafana")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Configuration metadata")


class PolicyCreate(BaseModel):
    """Policy creation model"""

    name: str = Field(..., description="Policy name")
    policy_type: str = Field(..., description="Policy type")
    target_service: str = Field(..., description="Target service")
    rules: List[Dict[str, Any]] = Field(..., description="Policy rules")
    enabled: bool = Field(default=True, description="Policy enabled status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Policy metadata")


# Update models for PATCH operations
class MeshConfigurationUpdate(BaseModel):
    """Mesh configuration update model"""

    name: Optional[str] = Field(None, description="Configuration name")
    namespace: Optional[str] = Field(None, description="Kubernetes namespace")
    profile: Optional[str] = Field(None, description="Mesh profile")
    auto_injection_enabled: Optional[bool] = Field(None, description="Enable auto-injection")
    mtls_enabled: Optional[bool] = Field(None, description="Enable mTLS")
    resource_limits: Optional[Dict[str, Any]] = Field(None, description="Resource limits")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Configuration metadata")


class TrafficRuleUpdate(BaseModel):
    """Traffic rule update model"""

    name: Optional[str] = Field(None, description="Rule name")
    match_conditions: Optional[Dict[str, Any]] = Field(None, description="Match conditions")
    destination: Optional[Dict[str, Any]] = Field(None, description="Destination configuration")
    weight: Optional[int] = Field(None, ge=0, le=100, description="Traffic weight")
    timeout_seconds: Optional[int] = Field(None, ge=1, description="Request timeout")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="Retry policy")
    fault_injection: Optional[Dict[str, Any]] = Field(None, description="Fault injection config")
    enabled: Optional[bool] = Field(None, description="Rule enabled status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Rule metadata")


class SecurityPolicyUpdate(BaseModel):
    """Security policy update model"""

    name: Optional[str] = Field(None, description="Policy name")
    mtls_mode: Optional[str] = Field(None, description="mTLS mode (STRICT, PERMISSIVE, DISABLE)")
    allowed_principals: Optional[List[str]] = Field(None, description="Allowed principals")
    denied_principals: Optional[List[str]] = Field(None, description="Denied principals")
    jwt_validation: Optional[Dict[str, Any]] = Field(None, description="JWT validation config")
    enabled: Optional[bool] = Field(None, description="Policy enabled status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Policy metadata")


class ObservabilityConfigUpdate(BaseModel):
    """Observability configuration update model"""

    name: Optional[str] = Field(None, description="Configuration name")
    tracing_enabled: Optional[bool] = Field(None, description="Enable tracing")
    metrics_enabled: Optional[bool] = Field(None, description="Enable metrics")
    access_logging_enabled: Optional[bool] = Field(None, description="Enable access logging")
    sampling_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sampling rate")
    prometheus_enabled: Optional[bool] = Field(None, description="Enable Prometheus")
    grafana_enabled: Optional[bool] = Field(None, description="Enable Grafana")
    enabled: Optional[bool] = Field(None, description="Configuration enabled status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Configuration metadata")


class PolicyUpdate(BaseModel):
    """Policy update model"""

    name: Optional[str] = Field(None, description="Policy name")
    rules: Optional[List[Dict[str, Any]]] = Field(None, description="Policy rules")
    enabled: Optional[bool] = Field(None, description="Policy enabled status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Policy metadata")


@router.get(
    "/services",
    summary="List all mesh services",
    responses={
        200: {"description": "List of mesh services"},
        500: {"description": "Internal server error"},
    },
)
async def list_mesh_services(
    mesh_type: Optional[str] = Query(None, description="Filter by mesh type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List all mesh services with optional filtering

    Args:
        mesh_type: Filter by mesh type
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of mesh services
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        manager = get_service_mesh_manager()
        summary = manager.generate_service_mesh_summary()

        repo = ServiceMeshRepository(db)
        configs = repo.list_mesh_configurations(
            mesh_type=mesh_type, status=status, limit=limit, offset=offset
        )

        # Convert to response format
        services = []
        for config in configs:
            services.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "mesh_type": config.mesh_type,
                    "namespace": config.namespace,
                    "status": config.status,
                    "mesh_id": config.mesh_id,
                    "auto_injection_enabled": config.auto_injection_enabled,
                    "mtls_enabled": config.mtls_enabled,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            )

        total = len(services)

        return {
            "status": "success",
            "data": {
                "services": services,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing mesh services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/configurations",
    summary="List all mesh configurations",
    responses={
        200: {"description": "List of configurations"},
        500: {"description": "Internal server error"},
    },
)
async def list_configurations(
    mesh_type: Optional[str] = Query(None, description="Filter by mesh type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    List all mesh configurations with optional filtering

    Args:
        mesh_type: Filter by mesh type
        status: Filter by status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of configurations
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        manager = get_service_mesh_manager()
        summary = manager.generate_service_mesh_summary()

        repo = ServiceMeshRepository(db)
        configs = repo.list_mesh_configurations(
            mesh_type=mesh_type, status=status, limit=limit, offset=offset
        )

        # Convert to response format
        filtered_configs = []
        for config in configs:
            filtered_configs.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "mesh_type": config.mesh_type,
                    "namespace": config.namespace,
                    "profile": config.profile,
                    "auto_injection_enabled": config.auto_injection_enabled,
                    "mtls_enabled": config.mtls_enabled,
                    "resource_limits": config.resource_limits,
                    "status": config.status,
                    "mesh_id": config.mesh_id,
                    "config_metadata": config.config_metadata,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            )

        total = len(filtered_configs)

        return {
            "status": "success",
            "data": {
                "configurations": filtered_configs,
                "total": total,
                "limit": limit,
                "offset": offset,
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/configurations",
    summary="Create a mesh configuration",
    responses={
        201: {"description": "Configuration created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_configuration(
    config: MeshConfigurationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new mesh configuration

    Args:
        config: Configuration creation data

    Returns:
        Created configuration
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        from core.service_mesh_manager import get_service_mesh_manager

        repo = ServiceMeshRepository(db)
        config_obj = repo.create_mesh_configuration(
            name=config.name,
            mesh_type=config.mesh_type,
            namespace=config.namespace,
            profile=config.profile,
            auto_injection_enabled=config.auto_injection_enabled,
            mtls_enabled=config.mtls_enabled,
            resource_limits=config.resource_limits,
            config_metadata=config.metadata,
        )

        # Generate Istio configuration if applicable
        if config.mesh_type == "istio":
            manager = get_service_mesh_manager()
            manager.generate_istio_control_plane_config(
                mesh_id=config_obj.mesh_id,
                namespace=config.namespace,
                profile=config.profile,
                resource_limits=config.resource_limits,
            )

            if config.mtls_enabled:
                manager.generate_mtls_config(
                    mesh_id=config_obj.mesh_id, namespace=config.namespace, strict_mode=True
                )

        logger.info(f"Created mesh configuration: {config.name} with ID: {config_obj.id} by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "id": config_obj.id,
                "mesh_id": config_obj.mesh_id,
                "name": config_obj.name,
                "mesh_type": config_obj.mesh_type,
                "namespace": config_obj.namespace,
                "profile": config_obj.profile,
                "auto_injection_enabled": config_obj.auto_injection_enabled,
                "mtls_enabled": config_obj.mtls_enabled,
                "resource_limits": config_obj.resource_limits,
                "status": config_obj.status,
                "config_metadata": config_obj.config_metadata,
                "created_at": config_obj.created_at.isoformat() if config_obj.created_at else None,
                "updated_at": config_obj.updated_at.isoformat() if config_obj.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/configurations/{config_id}",
    summary="Get configuration by ID",
    responses={
        200: {"description": "Configuration details"},
        404: {"description": "Configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_configuration(config_id: str, db: Session = Depends(get_db)):
    """
    Get configuration details by ID

    Args:
        config_id: Configuration ID

    Returns:
        Configuration details
    """
    try:
        repo = ServiceMeshRepository(db)
        config = repo.get_mesh_configuration(config_id)

        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        return {
            "status": "success",
            "data": {
                "id": config.id,
                "name": config.name,
                "mesh_type": config.mesh_type,
                "namespace": config.namespace,
                "profile": config.profile,
                "auto_injection_enabled": config.auto_injection_enabled,
                "mtls_enabled": config.mtls_enabled,
                "resource_limits": config.resource_limits,
                "status": config.status,
                "mesh_id": config.mesh_id,
                "config_metadata": config.config_metadata,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/configurations/{config_id}",
    summary="Update configuration",
    responses={
        200: {"description": "Configuration updated successfully"},
        404: {"description": "Configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_configuration(
    config_id: str, config_update: MeshConfigurationUpdate, db: Session = Depends(get_db)
):
    """
    Update configuration details

    Args:
        config_id: Configuration ID
        config_update: Configuration update data

    Returns:
        Updated configuration
    """
    try:
        repo = ServiceMeshRepository(db)
        config = repo.update_mesh_configuration(
            config_id=config_id,
            name=config_update.name,
            namespace=config_update.namespace,
            profile=config_update.profile,
            auto_injection_enabled=config_update.auto_injection_enabled,
            mtls_enabled=config_update.mtls_enabled,
            resource_limits=config_update.resource_limits,
            config_metadata=config_update.metadata,
        )

        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        logger.info(f"Updated configuration: {config_id}")

        return {
            "status": "success",
            "data": {
                "id": config.id,
                "name": config.name,
                "mesh_type": config.mesh_type,
                "namespace": config.namespace,
                "profile": config.profile,
                "auto_injection_enabled": config.auto_injection_enabled,
                "mtls_enabled": config.mtls_enabled,
                "resource_limits": config.resource_limits,
                "status": config.status,
                "mesh_id": config.mesh_id,
                "config_metadata": config.config_metadata,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/configurations/{config_id}",
    summary="Delete configuration",
    responses={
        200: {"description": "Configuration deleted successfully"},
        404: {"description": "Configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_configuration(config_id: str, db: Session = Depends(get_db)):
    """
    Delete configuration by ID

    Args:
        config_id: Configuration ID

    Returns:
        Deletion result
    """
    try:
        repo = ServiceMeshRepository(db)
        success = repo.delete_mesh_configuration(config_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        logger.info(f"Deleted configuration: {config_id}")

        return {
            "status": "success",
            "data": {"id": config_id, "message": "Configuration deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/traffic",
    summary="List all traffic rules",
    responses={
        200: {"description": "List of traffic rules"},
        500: {"description": "Internal server error"},
    },
)
async def list_traffic_rules(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    enabled_only: bool = Query(False, description="Only return enabled rules"),
    db: Session = Depends(get_db),
):
    """
    List all traffic rules with optional filtering

    Args:
        service_name: Filter by service name
        enabled_only: Only return enabled rules

    Returns:
        List of traffic rules
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        manager = get_service_mesh_manager()
        summary = manager.generate_service_mesh_summary()

        repo = ServiceMeshRepository(db)
        rules = repo.list_traffic_rules(service_name=service_name, enabled_only=enabled_only)

        # Convert to response format
        filtered_rules = []
        for rule in rules:
            filtered_rules.append(
                {
                    "id": rule.id,
                    "name": rule.name,
                    "service_name": rule.service_name,
                    "match_conditions": rule.match_conditions,
                    "destination": rule.destination,
                    "weight": rule.weight,
                    "timeout_seconds": rule.timeout_seconds,
                    "retry_policy": rule.retry_policy,
                    "fault_injection": rule.fault_injection,
                    "enabled": rule.enabled,
                    "rule_metadata": rule.rule_metadata,
                    "created_at": rule.created_at.isoformat() if rule.created_at else None,
                    "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "traffic_rules": filtered_rules,
                "total": len(filtered_rules),
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing traffic rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/traffic",
    summary="Create a traffic rule",
    responses={
        201: {"description": "Traffic rule created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_traffic_rule(rule: TrafficRuleCreate, db: Session = Depends(get_db)):
    """
    Create a new traffic rule

    Args:
        rule: Traffic rule creation data

    Returns:
        Created traffic rule
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        repo = ServiceMeshRepository(db)
        rule_obj = repo.create_traffic_rule(
            name=rule.name,
            service_name=rule.service_name,
            match_conditions=rule.match_conditions,
            destination=rule.destination,
            weight=rule.weight,
            timeout_seconds=rule.timeout_seconds,
            retry_policy=rule.retry_policy,
            fault_injection=rule.fault_injection,
            rule_metadata=rule.metadata,
        )

        # Generate virtual service configuration
        manager = get_service_mesh_manager()
        routing_rules = [
            {
                "match": rule.match_conditions,
                "route": [
                    {
                        "destination": rule.destination,
                        "weight": rule.weight,
                    }
                ],
                "timeout": f"{rule.timeout_seconds}s",
            }
        ]

        if rule.retry_policy:
            routing_rules[0]["retries"] = rule.retry_policy

        if rule.fault_injection:
            routing_rules[0]["fault"] = rule.fault_injection

        manager.generate_virtual_service_config(
            service_name=rule.service_name, routing_rules=routing_rules
        )

        logger.info(f"Created traffic rule: {rule.name} with ID: {rule_obj.id}")

        return {
            "status": "success",
            "data": {
                "id": rule_obj.id,
                "name": rule_obj.name,
                "service_name": rule_obj.service_name,
                "match_conditions": rule_obj.match_conditions,
                "destination": rule_obj.destination,
                "weight": rule_obj.weight,
                "timeout_seconds": rule_obj.timeout_seconds,
                "retry_policy": rule_obj.retry_policy,
                "fault_injection": rule_obj.fault_injection,
                "enabled": rule_obj.enabled,
                "rule_metadata": rule_obj.rule_metadata,
                "created_at": rule_obj.created_at.isoformat() if rule_obj.created_at else None,
                "updated_at": rule_obj.updated_at.isoformat() if rule_obj.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating traffic rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/traffic/{rule_id}",
    summary="Get traffic rule by ID",
    responses={
        200: {"description": "Traffic rule details"},
        404: {"description": "Traffic rule not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_traffic_rule(rule_id: str, db: Session = Depends(get_db)):
    """Get traffic rule by ID"""
    try:
        repo = ServiceMeshRepository(db)
        rule = repo.get_traffic_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail=f"Traffic rule {rule_id} not found")

        return {
            "status": "success",
            "data": {
                "id": rule.id,
                "name": rule.name,
                "service_name": rule.service_name,
                "match_conditions": rule.match_conditions,
                "destination": rule.destination,
                "weight": rule.weight,
                "timeout_seconds": rule.timeout_seconds,
                "retry_policy": rule.retry_policy,
                "fault_injection": rule.fault_injection,
                "enabled": rule.enabled,
                "rule_metadata": rule.rule_metadata,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting traffic rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/traffic/{rule_id}",
    summary="Update traffic rule",
    responses={
        200: {"description": "Traffic rule updated successfully"},
        404: {"description": "Traffic rule not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_traffic_rule(
    rule_id: str, rule_update: TrafficRuleUpdate, db: Session = Depends(get_db)
):
    """Update traffic rule"""
    try:
        repo = ServiceMeshRepository(db)
        rule = repo.update_traffic_rule(
            rule_id=rule_id,
            name=rule_update.name,
            match_conditions=rule_update.match_conditions,
            destination=rule_update.destination,
            weight=rule_update.weight,
            timeout_seconds=rule_update.timeout_seconds,
            retry_policy=rule_update.retry_policy,
            fault_injection=rule_update.fault_injection,
            enabled=rule_update.enabled,
            rule_metadata=rule_update.metadata,
        )

        if not rule:
            raise HTTPException(status_code=404, detail=f"Traffic rule {rule_id} not found")

        logger.info(f"Updated traffic rule: {rule_id}")

        return {
            "status": "success",
            "data": {
                "id": rule.id,
                "name": rule.name,
                "service_name": rule.service_name,
                "match_conditions": rule.match_conditions,
                "destination": rule.destination,
                "weight": rule.weight,
                "timeout_seconds": rule.timeout_seconds,
                "retry_policy": rule.retry_policy,
                "fault_injection": rule.fault_injection,
                "enabled": rule.enabled,
                "rule_metadata": rule.rule_metadata,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating traffic rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/traffic/{rule_id}",
    summary="Delete traffic rule",
    responses={
        200: {"description": "Traffic rule deleted successfully"},
        404: {"description": "Traffic rule not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_traffic_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete traffic rule"""
    try:
        repo = ServiceMeshRepository(db)
        success = repo.delete_traffic_rule(rule_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Traffic rule {rule_id} not found")

        logger.info(f"Deleted traffic rule: {rule_id}")

        return {
            "status": "success",
            "data": {"id": rule_id, "message": "Traffic rule deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting traffic rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/security",
    summary="List all security policies",
    responses={
        200: {"description": "List of security policies"},
        500: {"description": "Internal server error"},
    },
)
async def list_security_policies(
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    target_service: Optional[str] = Query(None, description="Filter by target service"),
    db: Session = Depends(get_db),
):
    """
    List all security policies with optional filtering

    Args:
        policy_type: Filter by policy type
        target_service: Filter by target service

    Returns:
        List of security policies
    """
    try:
        repo = ServiceMeshRepository(db)
        policies = repo.list_security_policies(
            policy_type=policy_type, target_service=target_service
        )

        # Convert to response format
        filtered_policies = []
        for policy in policies:
            filtered_policies.append(
                {
                    "id": policy.id,
                    "name": policy.name,
                    "policy_type": policy.policy_type,
                    "target_service": policy.target_service,
                    "mtls_mode": policy.mtls_mode,
                    "allowed_principals": policy.allowed_principals,
                    "denied_principals": policy.denied_principals,
                    "jwt_validation": policy.jwt_validation,
                    "enabled": policy.enabled,
                    "policy_metadata": policy.policy_metadata,
                    "created_at": policy.created_at.isoformat() if policy.created_at else None,
                    "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "security_policies": filtered_policies,
                "total": len(filtered_policies),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing security policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/security",
    summary="Create a security policy",
    responses={
        201: {"description": "Security policy created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_security_policy(
    policy: SecurityPolicyCreate, db: Session = Depends(get_db)
):
    """
    Create a new security policy

    Args:
        policy: Security policy creation data

    Returns:
        Created security policy
    """
    try:
        repo = ServiceMeshRepository(db)
        policy_obj = repo.create_security_policy(
            name=policy.name,
            policy_type=policy.policy_type,
            target_service=policy.target_service,
            mtls_mode=policy.mtls_mode,
            allowed_principals=policy.allowed_principals,
            denied_principals=policy.denied_principals,
            jwt_validation=policy.jwt_validation,
            policy_metadata=policy.metadata,
        )

        logger.info(f"Created security policy: {policy.name} with ID: {policy_obj.id}")

        return {
            "status": "success",
            "data": {
                "id": policy_obj.id,
                "name": policy_obj.name,
                "policy_type": policy_obj.policy_type,
                "target_service": policy_obj.target_service,
                "mtls_mode": policy_obj.mtls_mode,
                "allowed_principals": policy_obj.allowed_principals,
                "denied_principals": policy_obj.denied_principals,
                "jwt_validation": policy_obj.jwt_validation,
                "enabled": policy_obj.enabled,
                "policy_metadata": policy_obj.policy_metadata,
                "created_at": policy_obj.created_at.isoformat() if policy_obj.created_at else None,
                "updated_at": policy_obj.updated_at.isoformat() if policy_obj.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating security policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/security/{policy_id}",
    summary="Get security policy by ID",
    responses={
        200: {"description": "Security policy details"},
        404: {"description": "Security policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_security_policy(policy_id: str, db: Session = Depends(get_db)):
    """Get security policy by ID"""
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.get_security_policy(policy_id)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Security policy {policy_id} not found")

        return {
            "status": "success",
            "data": {
                "id": policy.id,
                "name": policy.name,
                "policy_type": policy.policy_type,
                "target_service": policy.target_service,
                "mtls_mode": policy.mtls_mode,
                "allowed_principals": policy.allowed_principals,
                "denied_principals": policy.denied_principals,
                "jwt_validation": policy.jwt_validation,
                "enabled": policy.enabled,
                "policy_metadata": policy.policy_metadata,
                "created_at": policy.created_at.isoformat() if policy.created_at else None,
                "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting security policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/security/{policy_id}",
    summary="Update security policy",
    responses={
        200: {"description": "Security policy updated successfully"},
        404: {"description": "Security policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_security_policy(
    policy_id: str, policy_update: SecurityPolicyUpdate, db: Session = Depends(get_db)
):
    """Update security policy"""
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.update_security_policy(
            policy_id=policy_id,
            name=policy_update.name,
            mtls_mode=policy_update.mtls_mode,
            allowed_principals=policy_update.allowed_principals,
            denied_principals=policy_update.denied_principals,
            jwt_validation=policy_update.jwt_validation,
            enabled=policy_update.enabled,
            policy_metadata=policy_update.metadata,
        )

        if not policy:
            raise HTTPException(status_code=404, detail=f"Security policy {policy_id} not found")

        logger.info(f"Updated security policy: {policy_id}")

        return {
            "status": "success",
            "data": {
                "id": policy.id,
                "name": policy.name,
                "policy_type": policy.policy_type,
                "target_service": policy.target_service,
                "mtls_mode": policy.mtls_mode,
                "allowed_principals": policy.allowed_principals,
                "denied_principals": policy.denied_principals,
                "jwt_validation": policy.jwt_validation,
                "enabled": policy.enabled,
                "policy_metadata": policy.policy_metadata,
                "created_at": policy.created_at.isoformat() if policy.created_at else None,
                "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating security policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/security/{policy_id}",
    summary="Delete security policy",
    responses={
        200: {"description": "Security policy deleted successfully"},
        404: {"description": "Security policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_security_policy(policy_id: str, db: Session = Depends(get_db)):
    """Delete security policy"""
    try:
        repo = ServiceMeshRepository(db)
        success = repo.delete_security_policy(policy_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Security policy {policy_id} not found")

        logger.info(f"Deleted security policy: {policy_id}")

        return {
            "status": "success",
            "data": {"id": policy_id, "message": "Security policy deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting security policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/observability",
    summary="List all observability configurations",
    responses={
        200: {"description": "List of observability configurations"},
        500: {"description": "Internal server error"},
    },
)
async def list_observability_configs(
    enabled_only: bool = Query(False, description="Only return enabled configurations"),
    db: Session = Depends(get_db),
):
    """
    List all observability configurations

    Args:
        enabled_only: Only return enabled configurations

    Returns:
        List of observability configurations
    """
    try:
        repo = ServiceMeshRepository(db)
        configs = repo.list_observability_configs(enabled_only=enabled_only)

        # Convert to response format
        filtered_configs = []
        for config in configs:
            filtered_configs.append(
                {
                    "id": config.id,
                    "name": config.name,
                    "tracing_enabled": config.tracing_enabled,
                    "metrics_enabled": config.metrics_enabled,
                    "access_logging_enabled": config.access_logging_enabled,
                    "sampling_rate": config.sampling_rate,
                    "prometheus_enabled": config.prometheus_enabled,
                    "grafana_enabled": config.grafana_enabled,
                    "enabled": config.enabled,
                    "config_metadata": config.config_metadata,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "observability_configs": filtered_configs,
                "total": len(filtered_configs),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing observability configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/observability",
    summary="Create an observability configuration",
    responses={
        201: {"description": "Observability configuration created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_observability_config(
    config: ObservabilityConfigCreate, db: Session = Depends(get_db)
):
    """
    Create a new observability configuration

    Args:
        config: Observability configuration creation data

    Returns:
        Created observability configuration
    """
    try:
        repo = ServiceMeshRepository(db)
        config_obj = repo.create_observability_config(
            name=config.name,
            tracing_enabled=config.tracing_enabled,
            metrics_enabled=config.metrics_enabled,
            access_logging_enabled=config.access_logging_enabled,
            sampling_rate=config.sampling_rate,
            prometheus_enabled=config.prometheus_enabled,
            grafana_enabled=config.grafana_enabled,
            config_metadata=config.metadata,
        )

        logger.info(f"Created observability config: {config.name} with ID: {config_obj.id}")

        return {
            "status": "success",
            "data": {
                "id": config_obj.id,
                "name": config_obj.name,
                "tracing_enabled": config_obj.tracing_enabled,
                "metrics_enabled": config_obj.metrics_enabled,
                "access_logging_enabled": config_obj.access_logging_enabled,
                "sampling_rate": config_obj.sampling_rate,
                "prometheus_enabled": config_obj.prometheus_enabled,
                "grafana_enabled": config_obj.grafana_enabled,
                "enabled": config_obj.enabled,
                "config_metadata": config_obj.config_metadata,
                "created_at": config_obj.created_at.isoformat() if config_obj.created_at else None,
                "updated_at": config_obj.updated_at.isoformat() if config_obj.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating observability config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/observability/{config_id}",
    summary="Get observability configuration by ID",
    responses={
        200: {"description": "Observability configuration details"},
        404: {"description": "Observability configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_observability_config(config_id: str, db: Session = Depends(get_db)):
    """Get observability configuration by ID"""
    try:
        repo = ServiceMeshRepository(db)
        config = repo.get_observability_config(config_id)

        if not config:
            raise HTTPException(status_code=404, detail=f"Observability configuration {config_id} not found")

        return {
            "status": "success",
            "data": {
                "id": config.id,
                "name": config.name,
                "tracing_enabled": config.tracing_enabled,
                "metrics_enabled": config.metrics_enabled,
                "access_logging_enabled": config.access_logging_enabled,
                "sampling_rate": config.sampling_rate,
                "prometheus_enabled": config.prometheus_enabled,
                "grafana_enabled": config.grafana_enabled,
                "enabled": config.enabled,
                "config_metadata": config.config_metadata,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting observability config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/observability/{config_id}",
    summary="Update observability configuration",
    responses={
        200: {"description": "Observability configuration updated successfully"},
        404: {"description": "Observability configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_observability_config(
    config_id: str, config_update: ObservabilityConfigUpdate, db: Session = Depends(get_db)
):
    """Update observability configuration"""
    try:
        repo = ServiceMeshRepository(db)
        config = repo.update_observability_config(
            config_id=config_id,
            name=config_update.name,
            tracing_enabled=config_update.tracing_enabled,
            metrics_enabled=config_update.metrics_enabled,
            access_logging_enabled=config_update.access_logging_enabled,
            sampling_rate=config_update.sampling_rate,
            prometheus_enabled=config_update.prometheus_enabled,
            grafana_enabled=config_update.grafana_enabled,
            enabled=config_update.enabled,
            config_metadata=config_update.metadata,
        )

        if not config:
            raise HTTPException(status_code=404, detail=f"Observability configuration {config_id} not found")

        logger.info(f"Updated observability config: {config_id}")

        return {
            "status": "success",
            "data": {
                "id": config.id,
                "name": config.name,
                "tracing_enabled": config.tracing_enabled,
                "metrics_enabled": config.metrics_enabled,
                "access_logging_enabled": config.access_logging_enabled,
                "sampling_rate": config.sampling_rate,
                "prometheus_enabled": config.prometheus_enabled,
                "grafana_enabled": config.grafana_enabled,
                "enabled": config.enabled,
                "config_metadata": config.config_metadata,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating observability config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/observability/{config_id}",
    summary="Delete observability configuration",
    responses={
        200: {"description": "Observability configuration deleted successfully"},
        404: {"description": "Observability configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_observability_config(config_id: str, db: Session = Depends(get_db)):
    """Delete observability configuration"""
    try:
        repo = ServiceMeshRepository(db)
        success = repo.delete_observability_config(config_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Observability configuration {config_id} not found")

        logger.info(f"Deleted observability config: {config_id}")

        return {
            "status": "success",
            "data": {"id": config_id, "message": "Observability configuration deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting observability config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/policies",
    summary="List all policies",
    responses={
        200: {"description": "List of policies"},
        500: {"description": "Internal server error"},
    },
)
async def list_policies(
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    target_service: Optional[str] = Query(None, description="Filter by target service"),
    enabled_only: bool = Query(False, description="Only return enabled policies"),
    db: Session = Depends(get_db),
):
    """
    List all policies with optional filtering

    Args:
        policy_type: Filter by policy type
        target_service: Filter by target service
        enabled_only: Only return enabled policies

    Returns:
        List of policies
    """
    try:
        repo = ServiceMeshRepository(db)
        policies = repo.list_policies(
            policy_type=policy_type, target_service=target_service, enabled_only=enabled_only
        )

        # Convert to response format
        filtered_policies = []
        for policy in policies:
            filtered_policies.append(
                {
                    "id": policy.id,
                    "name": policy.name,
                    "policy_type": policy.policy_type,
                    "target_service": policy.target_service,
                    "rules": policy.rules,
                    "enabled": policy.enabled,
                    "policy_metadata": policy.policy_metadata,
                    "created_at": policy.created_at.isoformat() if policy.created_at else None,
                    "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "policies": filtered_policies,
                "total": len(filtered_policies),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/policies",
    summary="Create a policy",
    responses={
        201: {"description": "Policy created successfully"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    """
    Create a new policy

    Args:
        policy: Policy creation data

    Returns:
        Created policy
    """
    try:
        repo = ServiceMeshRepository(db)
        policy_obj = repo.create_policy(
            name=policy.name,
            policy_type=policy.policy_type,
            target_service=policy.target_service,
            rules=policy.rules,
            enabled=policy.enabled,
            policy_metadata=policy.metadata,
        )

        logger.info(f"Created policy: {policy.name} with ID: {policy_obj.id}")

        return {
            "status": "success",
            "data": {
                "id": policy_obj.id,
                "name": policy_obj.name,
                "policy_type": policy_obj.policy_type,
                "target_service": policy_obj.target_service,
                "rules": policy_obj.rules,
                "enabled": policy_obj.enabled,
                "policy_metadata": policy_obj.policy_metadata,
                "created_at": policy_obj.created_at.isoformat() if policy_obj.created_at else None,
                "updated_at": policy_obj.updated_at.isoformat() if policy_obj.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/policies/{policy_id}",
    summary="Get policy by ID",
    responses={
        200: {"description": "Policy details"},
        404: {"description": "Policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_policy(policy_id: str, db: Session = Depends(get_db)):
    """Get policy by ID"""
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.get_policy(policy_id)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

        return {
            "status": "success",
            "data": {
                "id": policy.id,
                "name": policy.name,
                "policy_type": policy.policy_type,
                "target_service": policy.target_service,
                "rules": policy.rules,
                "enabled": policy.enabled,
                "policy_metadata": policy.policy_metadata,
                "created_at": policy.created_at.isoformat() if policy.created_at else None,
                "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/policies/{policy_id}",
    summary="Update policy",
    responses={
        200: {"description": "Policy updated successfully"},
        404: {"description": "Policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_policy(
    policy_id: str, policy_update: PolicyUpdate, db: Session = Depends(get_db)
):
    """Update policy"""
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.update_policy(
            policy_id=policy_id,
            name=policy_update.name,
            rules=policy_update.rules,
            enabled=policy_update.enabled,
            policy_metadata=policy_update.metadata,
        )

        if not policy:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

        logger.info(f"Updated policy: {policy_id}")

        return {
            "status": "success",
            "data": {
                "id": policy.id,
                "name": policy.name,
                "policy_type": policy.policy_type,
                "target_service": policy.target_service,
                "rules": policy.rules,
                "enabled": policy.enabled,
                "policy_metadata": policy.policy_metadata,
                "created_at": policy.created_at.isoformat() if policy.created_at else None,
                "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/policies/{policy_id}",
    summary="Delete policy",
    responses={
        200: {"description": "Policy deleted successfully"},
        404: {"description": "Policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_policy(policy_id: str, db: Session = Depends(get_db)):
    """Delete policy"""
    try:
        repo = ServiceMeshRepository(db)
        success = repo.delete_policy(policy_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

        logger.info(f"Deleted policy: {policy_id}")

        return {
            "status": "success",
            "data": {"id": policy_id, "message": "Policy deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
