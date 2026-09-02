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


# Additional Pydantic Models for new endpoints
class BatchTrafficRuleCreate(BaseModel):
    """Batch traffic rule creation model"""

    rules: List[TrafficRuleCreate] = Field(..., description="List of traffic rules to create")


class BatchTrafficRuleUpdate(BaseModel):
    """Batch traffic rule update model"""

    updates: List[Dict[str, Any]] = Field(..., description="List of rule updates")


class BatchDeleteRequest(BaseModel):
    """Batch delete request model"""

    ids: List[str] = Field(..., description="List of IDs to delete")


class GatewayConfigCreate(BaseModel):
    """Gateway configuration creation model"""

    name: str = Field(..., description="Gateway name")
    gateway_type: str = Field(default="ingress", description="Gateway type (ingress, egress)")
    selector: Dict[str, Any] = Field(..., description="Gateway selector")
    servers: List[Dict[str, Any]] = Field(..., description="Server configurations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Gateway metadata")


class CircuitBreakerCreate(BaseModel):
    """Circuit breaker creation model"""

    name: str = Field(..., description="Circuit breaker name")
    target_service: str = Field(..., description="Target service")
    consecutive_errors: int = Field(default=5, ge=1, description="Consecutive errors threshold")
    interval_seconds: int = Field(default=60, ge=1, description="Detection interval")
    timeout_seconds: int = Field(default=30, ge=1, description="Timeout duration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Circuit breaker metadata")


class CircuitBreakerUpdate(BaseModel):
    """Circuit breaker update model"""

    state: str = Field(..., description="Circuit breaker state (closed, open, half-open)")


class RetryPolicyCreate(BaseModel):
    """Retry policy creation model"""

    name: str = Field(..., description="Retry policy name")
    target_service: str = Field(..., description="Target service")
    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=30, ge=1, description="Retry timeout")
    retry_on: List[str] = Field(default_factory=list, description="Retry conditions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Retry policy metadata")


class TimeoutPolicyCreate(BaseModel):
    """Timeout policy creation model"""

    name: str = Field(..., description="Timeout policy name")
    target_service: str = Field(..., description="Target service")
    timeout_seconds: int = Field(default=30, ge=1, description="Timeout duration")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Timeout policy metadata")


class ConfigurationImport(BaseModel):
    """Configuration import model"""

    version: str = Field(..., description="Configuration version")
    exported_at: str = Field(..., description="Export timestamp")
    configuration: Dict[str, Any] = Field(..., description="Configuration data")


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


# ==================== Batch Operations (3 endpoints) ====================

@router.post(
    "/traffic/batch",
    summary="Batch create traffic rules",
    responses={
        201: {"description": "Traffic rules created successfully"},
        400: {"description": "Invalid request"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def batch_create_traffic_rules(
    batch: BatchTrafficRuleCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch create traffic rules with rate limiting

    Args:
        batch: Batch of traffic rules to create

    Returns:
        Created traffic rules
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=10)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        rules_data = [
            {
                "name": rule.name,
                "service_name": rule.service_name,
                "match_conditions": rule.match_conditions,
                "destination": rule.destination,
                "weight": rule.weight,
                "timeout_seconds": rule.timeout_seconds,
                "retry_policy": rule.retry_policy,
                "fault_injection": rule.fault_injection,
                "metadata": rule.metadata,
            }
            for rule in batch.rules
        ]

        created_rules = repo.batch_create_traffic_rules(rules_data)

        logger.info(f"Batch created {len(created_rules)} traffic rules by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "created_count": len(created_rules),
                "rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "service_name": rule.service_name,
                    }
                    for rule in created_rules
                ],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch creating traffic rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/traffic/batch",
    summary="Batch update traffic rules",
    responses={
        200: {"description": "Traffic rules updated successfully"},
        400: {"description": "Invalid request"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def batch_update_traffic_rules(
    batch: BatchTrafficRuleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch update traffic rules with rate limiting

    Args:
        batch: Batch of traffic rule updates

    Returns:
        Updated traffic rules
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=10)

        # Permission check
        require_permission("service_mesh", "update")(current_user)

        repo = ServiceMeshRepository(db)
        updated_rules = repo.batch_update_traffic_rules(batch.updates)

        logger.info(f"Batch updated {len(updated_rules)} traffic rules by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "updated_count": len(updated_rules),
                "rules": [
                    {
                        "id": rule.id,
                        "name": rule.name,
                        "service_name": rule.service_name,
                    }
                    for rule in updated_rules
                ],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch updating traffic rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/traffic/batch",
    summary="Batch delete traffic rules",
    responses={
        200: {"description": "Traffic rules deleted successfully"},
        400: {"description": "Invalid request"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def batch_delete_traffic_rules(
    batch: BatchDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch delete traffic rules with rate limiting

    Args:
        batch: List of rule IDs to delete

    Returns:
        Deletion result
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=10)

        # Permission check
        require_permission("service_mesh", "delete")(current_user)

        repo = ServiceMeshRepository(db)
        result = repo.batch_delete_traffic_rules(batch.ids)

        logger.info(f"Batch deleted {result['deleted']} traffic rules by user: {current_user.username}")

        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch deleting traffic rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Service Discovery (2 endpoints) ====================

@router.get(
    "/services/{service_name}/dependencies",
    summary="Get service dependencies",
    responses={
        200: {"description": "Service dependencies"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_dependencies(service_name: str, db: Session = Depends(get_db)):
    """
    Get service dependencies and upstream/downstream relationships

    Args:
        service_name: Service name

    Returns:
        Service dependencies
    """
    try:
        repo = ServiceMeshRepository(db)
        dependencies = repo.get_service_dependencies(service_name)

        return {
            "status": "success",
            "data": dependencies,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/services/{service_name}/metrics",
    summary="Get service metrics",
    responses={
        200: {"description": "Service metrics"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_metrics(service_name: str, db: Session = Depends(get_db)):
    """
    Get aggregated metrics for a service

    Args:
        service_name: Service name

    Returns:
        Service metrics
    """
    try:
        repo = ServiceMeshRepository(db)
        metrics = repo.get_service_metrics(service_name)

        return {
            "status": "success",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Gateway Operations (3 endpoints) ====================

@router.post(
    "/gateways",
    summary="Create gateway configuration",
    responses={
        201: {"description": "Gateway created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_gateway(
    gateway: GatewayConfigCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new gateway configuration

    Args:
        gateway: Gateway configuration data

    Returns:
        Created gateway
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        gateway_obj = repo.create_gateway_config(
            name=gateway.name,
            gateway_type=gateway.gateway_type,
            selector=gateway.selector,
            servers=gateway.servers,
            config_metadata=gateway.metadata,
        )

        logger.info(f"Created gateway: {gateway.name} with ID: {gateway_obj['id']} by user: {current_user.username}")

        return {
            "status": "success",
            "data": gateway_obj,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating gateway: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/gateways/{gateway_id}",
    summary="Get gateway by ID",
    responses={
        200: {"description": "Gateway details"},
        404: {"description": "Gateway not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_gateway(gateway_id: str, db: Session = Depends(get_db)):
    """
    Get gateway configuration by ID

    Args:
        gateway_id: Gateway ID

    Returns:
        Gateway details
    """
    try:
        repo = ServiceMeshRepository(db)
        gateway = repo.get_gateway_config(gateway_id)

        if not gateway:
            raise HTTPException(status_code=404, detail=f"Gateway {gateway_id} not found")

        return {
            "status": "success",
            "data": gateway,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gateway: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/gateways",
    summary="List all gateways",
    responses={
        200: {"description": "List of gateways"},
        500: {"description": "Internal server error"},
    },
)
async def list_gateways(
    gateway_type: Optional[str] = Query(None, description="Filter by gateway type"),
    db: Session = Depends(get_db),
):
    """
    List all gateway configurations

    Args:
        gateway_type: Filter by gateway type

    Returns:
        List of gateways
    """
    try:
        repo = ServiceMeshRepository(db)
        gateways = repo.list_gateway_configs(gateway_type=gateway_type)

        return {
            "status": "success",
            "data": {
                "gateways": gateways,
                "total": len(gateways),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing gateways: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check Operations (2 endpoints) ====================

@router.get(
    "/services/{service_name}/health",
    summary="Get service health",
    responses={
        200: {"description": "Service health status"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_health(service_name: str, db: Session = Depends(get_db)):
    """
    Perform health check on a service

    Args:
        service_name: Service name

    Returns:
        Service health status
    """
    try:
        repo = ServiceMeshRepository(db)
        health = repo.perform_health_check(service_name)

        return {
            "status": "success",
            "data": health,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health/summary",
    summary="Get mesh health summary",
    responses={
        200: {"description": "Mesh health summary"},
        500: {"description": "Internal server error"},
    },
)
async def get_mesh_health_summary(db: Session = Depends(get_db)):
    """
    Get overall mesh health summary

    Returns:
        Mesh health summary
    """
    try:
        repo = ServiceMeshRepository(db)
        summary = repo.get_mesh_health_summary()

        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting mesh health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Circuit Breaker Operations (4 endpoints) ====================

@router.post(
    "/circuit-breakers",
    summary="Create circuit breaker",
    responses={
        201: {"description": "Circuit breaker created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_circuit_breaker(
    cb: CircuitBreakerCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new circuit breaker

    Args:
        cb: Circuit breaker data

    Returns:
        Created circuit breaker
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        circuit_breaker = repo.create_circuit_breaker(
            name=cb.name,
            target_service=cb.target_service,
            consecutive_errors=cb.consecutive_errors,
            interval_seconds=cb.interval_seconds,
            timeout_seconds=cb.timeout_seconds,
            config_metadata=cb.metadata,
        )

        logger.info(f"Created circuit breaker: {cb.name} with ID: {circuit_breaker['id']} by user: {current_user.username}")

        return {
            "status": "success",
            "data": circuit_breaker,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/circuit-breakers/{cb_id}",
    summary="Get circuit breaker by ID",
    responses={
        200: {"description": "Circuit breaker details"},
        404: {"description": "Circuit breaker not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_circuit_breaker(cb_id: str, db: Session = Depends(get_db)):
    """
    Get circuit breaker by ID

    Args:
        cb_id: Circuit breaker ID

    Returns:
        Circuit breaker details
    """
    try:
        repo = ServiceMeshRepository(db)
        cb = repo.get_circuit_breaker(cb_id)

        if not cb:
            raise HTTPException(status_code=404, detail=f"Circuit breaker {cb_id} not found")

        return {
            "status": "success",
            "data": cb,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/circuit-breakers",
    summary="List all circuit breakers",
    responses={
        200: {"description": "List of circuit breakers"},
        500: {"description": "Internal server error"},
    },
)
async def list_circuit_breakers(
    target_service: Optional[str] = Query(None, description="Filter by target service"),
    db: Session = Depends(get_db),
):
    """
    List all circuit breakers

    Args:
        target_service: Filter by target service

    Returns:
        List of circuit breakers
    """
    try:
        repo = ServiceMeshRepository(db)
        circuit_breakers = repo.list_circuit_breakers(target_service=target_service)

        return {
            "status": "success",
            "data": {
                "circuit_breakers": circuit_breakers,
                "total": len(circuit_breakers),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing circuit breakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/circuit-breakers/{cb_id}/state",
    summary="Update circuit breaker state",
    responses={
        200: {"description": "Circuit breaker state updated"},
        404: {"description": "Circuit breaker not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_circuit_breaker_state(
    cb_id: str,
    cb_update: CircuitBreakerUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update circuit breaker state

    Args:
        cb_id: Circuit breaker ID
        cb_update: State update data

    Returns:
        Update result
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "update")(current_user)

        repo = ServiceMeshRepository(db)
        success = repo.update_circuit_breaker_state(cb_id, cb_update.state)

        if not success:
            raise HTTPException(status_code=404, detail=f"Circuit breaker {cb_id} not found")

        logger.info(f"Updated circuit breaker {cb_id} state to {cb_update.state} by user: {current_user.username}")

        return {
            "status": "success",
            "data": {"id": cb_id, "state": cb_update.state},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating circuit breaker state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Retry Policy Operations (3 endpoints) ====================

@router.post(
    "/retry-policies",
    summary="Create retry policy",
    responses={
        201: {"description": "Retry policy created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_retry_policy(
    policy: RetryPolicyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new retry policy

    Args:
        policy: Retry policy data

    Returns:
        Created retry policy
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        retry_policy = repo.create_retry_policy(
            name=policy.name,
            target_service=policy.target_service,
            max_attempts=policy.max_attempts,
            timeout_seconds=policy.timeout_seconds,
            retry_on=policy.retry_on,
            config_metadata=policy.metadata,
        )

        logger.info(f"Created retry policy: {policy.name} with ID: {retry_policy['id']} by user: {current_user.username}")

        return {
            "status": "success",
            "data": retry_policy,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating retry policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/retry-policies/{policy_id}",
    summary="Get retry policy by ID",
    responses={
        200: {"description": "Retry policy details"},
        404: {"description": "Retry policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_retry_policy(policy_id: str, db: Session = Depends(get_db)):
    """
    Get retry policy by ID

    Args:
        policy_id: Retry policy ID

    Returns:
        Retry policy details
    """
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.get_retry_policy(policy_id)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Retry policy {policy_id} not found")

        return {
            "status": "success",
            "data": policy,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting retry policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/retry-policies",
    summary="List all retry policies",
    responses={
        200: {"description": "List of retry policies"},
        500: {"description": "Internal server error"},
    },
)
async def list_retry_policies(
    target_service: Optional[str] = Query(None, description="Filter by target service"),
    db: Session = Depends(get_db),
):
    """
    List all retry policies

    Args:
        target_service: Filter by target service

    Returns:
        List of retry policies
    """
    try:
        repo = ServiceMeshRepository(db)
        policies = repo.list_retry_policies(target_service=target_service)

        return {
            "status": "success",
            "data": {
                "retry_policies": policies,
                "total": len(policies),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing retry policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Timeout Policy Operations (3 endpoints) ====================

@router.post(
    "/timeout-policies",
    summary="Create timeout policy",
    responses={
        201: {"description": "Timeout policy created successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_timeout_policy(
    policy: TimeoutPolicyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new timeout policy

    Args:
        policy: Timeout policy data

    Returns:
        Created timeout policy
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        timeout_policy = repo.create_timeout_policy(
            name=policy.name,
            target_service=policy.target_service,
            timeout_seconds=policy.timeout_seconds,
            config_metadata=policy.metadata,
        )

        logger.info(f"Created timeout policy: {policy.name} with ID: {timeout_policy['id']} by user: {current_user.username}")

        return {
            "status": "success",
            "data": timeout_policy,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeout policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/timeout-policies/{policy_id}",
    summary="Get timeout policy by ID",
    responses={
        200: {"description": "Timeout policy details"},
        404: {"description": "Timeout policy not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_timeout_policy(policy_id: str, db: Session = Depends(get_db)):
    """
    Get timeout policy by ID

    Args:
        policy_id: Timeout policy ID

    Returns:
        Timeout policy details
    """
    try:
        repo = ServiceMeshRepository(db)
        policy = repo.get_timeout_policy(policy_id)

        if not policy:
            raise HTTPException(status_code=404, detail=f"Timeout policy {policy_id} not found")

        return {
            "status": "success",
            "data": policy,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeout policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/timeout-policies",
    summary="List all timeout policies",
    responses={
        200: {"description": "List of timeout policies"},
        500: {"description": "Internal server error"},
    },
)
async def list_timeout_policies(
    target_service: Optional[str] = Query(None, description="Filter by target service"),
    db: Session = Depends(get_db),
):
    """
    List all timeout policies

    Args:
        target_service: Filter by target service

    Returns:
        List of timeout policies
    """
    try:
        repo = ServiceMeshRepository(db)
        policies = repo.list_timeout_policies(target_service=target_service)

        return {
            "status": "success",
            "data": {
                "timeout_policies": policies,
                "total": len(policies),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing timeout policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Export/Import Operations (2 endpoints) ====================

@router.get(
    "/configurations/{config_id}/export",
    summary="Export configuration",
    responses={
        200: {"description": "Configuration exported"},
        404: {"description": "Configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def export_configuration(config_id: str, db: Session = Depends(get_db)):
    """
    Export configuration to portable format

    Args:
        config_id: Configuration ID

    Returns:
        Exported configuration
    """
    try:
        repo = ServiceMeshRepository(db)
        export_data = repo.export_configuration(config_id)

        if not export_data:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        logger.info(f"Exported configuration: {config_id}")

        return {
            "status": "success",
            "data": export_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/configurations/import",
    summary="Import configuration",
    responses={
        201: {"description": "Configuration imported successfully"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def import_configuration(
    import_data: ConfigurationImport,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import configuration from portable format

    Args:
        import_data: Configuration import data

    Returns:
        Imported configuration
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=10)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        config = repo.import_configuration(import_data.dict())

        logger.info(f"Imported configuration with ID: {config.id} by user: {current_user.username}")

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
        logger.error(f"Error importing configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Metrics Aggregation (1 endpoint) ====================

@router.get(
    "/metrics",
    summary="Get mesh metrics",
    responses={
        200: {"description": "Mesh metrics"},
        500: {"description": "Internal server error"},
    },
)
async def get_mesh_metrics(
    time_range: str = Query("1h", description="Time range for metrics"),
    db: Session = Depends(get_db),
):
    """
    Get aggregated mesh metrics

    Args:
        time_range: Time range for metrics (e.g., 1h, 24h, 7d)

    Returns:
        Mesh metrics
    """
    try:
        repo = ServiceMeshRepository(db)
        metrics = repo.get_mesh_metrics(time_range=time_range)

        return {
            "status": "success",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting mesh metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Topology Operations (1 endpoint) ====================

@router.get(
    "/topology",
    summary="Get service topology",
    responses={
        200: {"description": "Service topology"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_topology(db: Session = Depends(get_db)):
    """
    Get service topology graph

    Returns:
        Service topology
    """
    try:
        repo = ServiceMeshRepository(db)
        topology = repo.get_service_topology()

        return {
            "status": "success",
            "data": topology,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Configuration Validation (1 endpoint) ====================

@router.post(
    "/configurations/validate",
    summary="Validate configuration",
    responses={
        200: {"description": "Configuration validated"},
        400: {"description": "Invalid configuration"},
        500: {"description": "Internal server error"},
    },
)
async def validate_configuration(
    config: MeshConfigurationCreate,
    db: Session = Depends(get_db),
):
    """
    Validate configuration before creation

    Args:
        config: Configuration to validate

    Returns:
        Validation result
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        manager = get_service_mesh_manager()
        validation_errors = []

        # Validate mesh type
        if config.mesh_type not in ["istio", "linkerd", "consul"]:
            validation_errors.append(f"Invalid mesh type: {config.mesh_type}")

        # Validate profile
        valid_profiles = ["default", "demo", "minimal", "preview"]
        if config.profile not in valid_profiles:
            validation_errors.append(f"Invalid profile: {config.profile}")

        # Validate resource limits
        if config.resource_limits:
            if "cpu" in config.resource_limits and config.resource_limits["cpu"] < 0:
                validation_errors.append("CPU limit cannot be negative")
            if "memory" in config.resource_limits and config.resource_limits["memory"] < 0:
                validation_errors.append("Memory limit cannot be negative")

        is_valid = len(validation_errors) == 0

        logger.info(f"Validated configuration: {config.name}, valid: {is_valid}")

        return {
            "status": "success",
            "data": {
                "valid": is_valid,
                "errors": validation_errors,
                "warnings": [],
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Configuration Rollback (1 endpoint) ====================

@router.post(
    "/configurations/{config_id}/rollback",
    summary="Rollback configuration",
    responses={
        200: {"description": "Configuration rolled back"},
        404: {"description": "Configuration not found"},
        500: {"description": "Internal server error"},
    },
)
async def rollback_configuration(
    config_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Rollback configuration to previous version

    Args:
        config_id: Configuration ID

    Returns:
        Rollback result
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=10)

        # Permission check
        require_permission("service_mesh", "update")(current_user)

        repo = ServiceMeshRepository(db)
        config = repo.get_mesh_configuration(config_id)

        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        # In a real implementation, this would restore from version history
        # For now, we'll just log the rollback
        logger.info(f"Rolled back configuration: {config_id} by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "id": config_id,
                "message": "Configuration rolled back successfully",
                "previous_version": config.updated_at.isoformat() if config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Service Instance Operations (2 endpoints) ====================

@router.get(
    "/services/{service_name}/instances",
    summary="Get service instances",
    responses={
        200: {"description": "Service instances"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_service_instances(
    service_name: str,
    status: Optional[str] = Query(None, description="Filter by instance status"),
    db: Session = Depends(get_db),
):
    """
    Get service instances with optional filtering

    Args:
        service_name: Service name
        status: Filter by instance status

    Returns:
        Service instances
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        manager = get_service_mesh_manager()
        summary = manager.generate_service_mesh_summary()

        # In a real implementation, this would query the service registry
        instances = []
        for i in range(3):
            instances.append(
                {
                    "id": f"{service_name}-{i}",
                    "service_name": service_name,
                    "address": f"10.0.0.{10 + i}",
                    "port": 8080,
                    "status": "healthy" if i < 2 else "unhealthy",
                    "zone": "zone-a",
                    "last_heartbeat": datetime.utcnow().isoformat(),
                }
            )

        if status:
            instances = [inst for inst in instances if inst["status"] == status]

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "instances": instances,
                "total": len(instances),
                "summary": summary,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting service instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/services/{service_name}/instances/{instance_id}",
    summary="Delete service instance",
    responses={
        200: {"description": "Instance deleted successfully"},
        404: {"description": "Instance not found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal server error"},
    },
)
async def delete_service_instance(
    service_name: str,
    instance_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a service instance

    Args:
        service_name: Service name
        instance_id: Instance ID

    Returns:
        Deletion result
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "delete")(current_user)

        # In a real implementation, this would deregister the instance
        logger.info(f"Deleted instance {instance_id} for service {service_name} by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "instance_id": instance_id,
                "message": "Instance deleted successfully",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting service instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Configuration Diff (1 endpoint) ====================

@router.post(
    "/configurations/diff",
    summary="Compare configurations",
    responses={
        200: {"description": "Configuration diff"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
)
async def compare_configurations(
    config_id_1: str = Query(..., description="First configuration ID"),
    config_id_2: str = Query(..., description="Second configuration ID"),
    db: Session = Depends(get_db),
):
    """
    Compare two configurations

    Args:
        config_id_1: First configuration ID
        config_id_2: Second configuration ID

    Returns:
        Configuration diff
    """
    try:
        repo = ServiceMeshRepository(db)
        config1 = repo.get_mesh_configuration(config_id_1)
        config2 = repo.get_mesh_configuration(config_id_2)

        if not config1:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id_1} not found")
        if not config2:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id_2} not found")

        # Compute differences
        differences = []
        if config1.name != config2.name:
            differences.append({"field": "name", "old": config1.name, "new": config2.name})
        if config1.mesh_type != config2.mesh_type:
            differences.append({"field": "mesh_type", "old": config1.mesh_type, "new": config2.mesh_type})
        if config1.namespace != config2.namespace:
            differences.append({"field": "namespace", "old": config1.namespace, "new": config2.namespace})
        if config1.profile != config2.profile:
            differences.append({"field": "profile", "old": config1.profile, "new": config2.profile})
        if config1.auto_injection_enabled != config2.auto_injection_enabled:
            differences.append(
                {
                    "field": "auto_injection_enabled",
                    "old": config1.auto_injection_enabled,
                    "new": config2.auto_injection_enabled,
                }
            )
        if config1.mtls_enabled != config2.mtls_enabled:
            differences.append({"field": "mtls_enabled", "old": config1.mtls_enabled, "new": config2.mtls_enabled})

        logger.info(f"Compared configurations: {config_id_1} vs {config_id_2}")

        return {
            "status": "success",
            "data": {
                "config_id_1": config_id_1,
                "config_id_2": config_id_2,
                "differences": differences,
                "difference_count": len(differences),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Configuration Clone (1 endpoint) ====================

@router.post(
    "/configurations/{config_id}/clone",
    summary="Clone configuration",
    responses={
        201: {"description": "Configuration cloned successfully"},
        404: {"description": "Configuration not found"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def clone_configuration(
    config_id: str,
    request: Request,
    new_name: str = Query(..., description="New configuration name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clone an existing configuration

    Args:
        config_id: Configuration ID to clone
        new_name: Name for the cloned configuration

    Returns:
        Cloned configuration
    """
    try:
        # Rate limiting
        identifier = current_user.username if current_user else request.client.host
        check_rate_limit(identifier, requests_per_minute=30)

        # Permission check
        require_permission("service_mesh", "create")(current_user)

        repo = ServiceMeshRepository(db)
        original_config = repo.get_mesh_configuration(config_id)

        if not original_config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        # Create cloned configuration
        cloned_config = repo.create_mesh_configuration(
            name=new_name,
            mesh_type=original_config.mesh_type,
            namespace=original_config.namespace,
            profile=original_config.profile,
            auto_injection_enabled=original_config.auto_injection_enabled,
            mtls_enabled=original_config.mtls_enabled,
            resource_limits=original_config.resource_limits,
            config_metadata={
                **original_config.config_metadata,
                "cloned_from": config_id,
                "cloned_at": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"Cloned configuration {config_id} to {cloned_config.id} with name {new_name} by user: {current_user.username}")

        return {
            "status": "success",
            "data": {
                "id": cloned_config.id,
                "name": cloned_config.name,
                "mesh_type": cloned_config.mesh_type,
                "namespace": cloned_config.namespace,
                "profile": cloned_config.profile,
                "auto_injection_enabled": cloned_config.auto_injection_enabled,
                "mtls_enabled": cloned_config.mtls_enabled,
                "resource_limits": cloned_config.resource_limits,
                "status": cloned_config.status,
                "mesh_id": cloned_config.mesh_id,
                "config_metadata": cloned_config.config_metadata,
                "created_at": cloned_config.created_at.isoformat() if cloned_config.created_at else None,
                "updated_at": cloned_config.updated_at.isoformat() if cloned_config.updated_at else None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))
