# -*- coding: utf-8 -*-
"""
Service Mesh Advanced API Router
Provides advanced API endpoints for service mesh management with full CRUD operations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, Field

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


# In-memory storage (in production, use a database)
_configurations_db: Dict[str, Dict[str, Any]] = {}
_traffic_rules_db: Dict[str, Dict[str, Any]] = {}
_security_policies_db: Dict[str, Dict[str, Any]] = {}
_observability_configs_db: Dict[str, Dict[str, Any]] = {}
_policies_db: Dict[str, Dict[str, Any]] = {}


def _generate_config_id() -> str:
    """Generate unique configuration ID"""
    return str(uuid4())


def _generate_rule_id() -> str:
    """Generate unique rule ID"""
    return str(uuid4())


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

        # Get services from configurations
        services = []
        for config_id, config in _configurations_db.items():
            if mesh_type and config.get("mesh_type") != mesh_type:
                continue
            if status and config.get("status") != status:
                continue

            services.append(
                {
                    "id": config_id,
                    "name": config.get("name"),
                    "mesh_type": config.get("mesh_type"),
                    "namespace": config.get("namespace"),
                    "status": config.get("status"),
                    "mesh_id": config.get("mesh_id"),
                    "auto_injection_enabled": config.get("auto_injection_enabled"),
                    "mtls_enabled": config.get("mtls_enabled"),
                    "created_at": config.get("created_at"),
                    "updated_at": config.get("updated_at"),
                }
            )

        # Apply pagination
        total = len(services)
        paginated_services = services[offset : offset + limit]

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

        # Filter configurations
        filtered_configs = []
        for config_id, config in _configurations_db.items():
            if mesh_type and config.get("mesh_type") != mesh_type:
                continue
            if status and config.get("status") != status:
                continue
            filtered_configs.append({"id": config_id, **config})

        # Apply pagination
        total = len(filtered_configs)
        paginated_configs = filtered_configs[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "configurations": paginated_configs,
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
        500: {"description": "Internal server error"},
    },
    status_code=201,
)
async def create_configuration(config: MeshConfigurationCreate):
    """
    Create a new mesh configuration

    Args:
        config: Configuration creation data

    Returns:
        Created configuration
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        config_id = _generate_config_id()
        mesh_id = f"mesh-{config_id[:8]}"

        # Create configuration in database
        _configurations_db[config_id] = {
            "name": config.name,
            "mesh_type": config.mesh_type,
            "namespace": config.namespace,
            "profile": config.profile,
            "auto_injection_enabled": config.auto_injection_enabled,
            "mtls_enabled": config.mtls_enabled,
            "resource_limits": config.resource_limits,
            "metadata": config.metadata,
            "status": "active",
            "mesh_id": mesh_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Generate Istio configuration if applicable
        if config.mesh_type == "istio":
            manager = get_service_mesh_manager()
            manager.generate_istio_control_plane_config(
                mesh_id=mesh_id,
                namespace=config.namespace,
                profile=config.profile,
                resource_limits=config.resource_limits,
            )

            if config.mtls_enabled:
                manager.generate_mtls_config(
                    mesh_id=mesh_id, namespace=config.namespace, strict_mode=True
                )

        logger.info(f"Created mesh configuration: {config.name} with ID: {config_id}")

        return {
            "status": "success",
            "data": {"id": config_id, "mesh_id": mesh_id, **_configurations_db[config_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
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
async def get_configuration(config_id: str):
    """
    Get configuration details by ID

    Args:
        config_id: Configuration ID

    Returns:
        Configuration details
    """
    try:
        if config_id not in _configurations_db:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        config = _configurations_db[config_id]

        return {
            "status": "success",
            "data": {"id": config_id, **config},
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
async def update_configuration(config_id: str, config_update: MeshConfigurationUpdate):
    """
    Update configuration details

    Args:
        config_id: Configuration ID
        config_update: Configuration update data

    Returns:
        Updated configuration
    """
    try:
        if config_id not in _configurations_db:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        config = _configurations_db[config_id]

        # Update fields
        if config_update.name is not None:
            config["name"] = config_update.name
        if config_update.namespace is not None:
            config["namespace"] = config_update.namespace
        if config_update.profile is not None:
            config["profile"] = config_update.profile
        if config_update.auto_injection_enabled is not None:
            config["auto_injection_enabled"] = config_update.auto_injection_enabled
        if config_update.mtls_enabled is not None:
            config["mtls_enabled"] = config_update.mtls_enabled
        if config_update.resource_limits is not None:
            config["resource_limits"] = config_update.resource_limits
        if config_update.metadata is not None:
            config["metadata"] = config_update.metadata

        config["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Updated configuration: {config_id}")

        return {
            "status": "success",
            "data": {"id": config_id, **config},
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
async def delete_configuration(config_id: str):
    """
    Delete configuration by ID

    Args:
        config_id: Configuration ID

    Returns:
        Deletion result
    """
    try:
        if config_id not in _configurations_db:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")

        del _configurations_db[config_id]

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

        filtered_rules = []
        for rule_id, rule in _traffic_rules_db.items():
            if service_name and rule.get("service_name") != service_name:
                continue
            if enabled_only and not rule.get("enabled", True):
                continue
            filtered_rules.append({"id": rule_id, **rule})

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
async def create_traffic_rule(rule: TrafficRuleCreate):
    """
    Create a new traffic rule

    Args:
        rule: Traffic rule creation data

    Returns:
        Created traffic rule
    """
    try:
        from core.service_mesh_manager import get_service_mesh_manager

        rule_id = _generate_rule_id()

        # Create traffic rule
        _traffic_rules_db[rule_id] = {
            "name": rule.name,
            "service_name": rule.service_name,
            "match_conditions": rule.match_conditions,
            "destination": rule.destination,
            "weight": rule.weight,
            "timeout_seconds": rule.timeout_seconds,
            "retry_policy": rule.retry_policy,
            "fault_injection": rule.fault_injection,
            "metadata": rule.metadata,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

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

        logger.info(f"Created traffic rule: {rule.name} with ID: {rule_id}")

        return {
            "status": "success",
            "data": {"id": rule_id, **_traffic_rules_db[rule_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating traffic rule: {e}")
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
        filtered_policies = []
        for policy_id, policy in _security_policies_db.items():
            if policy_type and policy.get("policy_type") != policy_type:
                continue
            if target_service and policy.get("target_service") != target_service:
                continue
            filtered_policies.append({"id": policy_id, **policy})

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
async def create_security_policy(policy: SecurityPolicyCreate):
    """
    Create a new security policy

    Args:
        policy: Security policy creation data

    Returns:
        Created security policy
    """
    try:
        policy_id = _generate_rule_id()

        # Create security policy
        _security_policies_db[policy_id] = {
            "name": policy.name,
            "policy_type": policy.policy_type,
            "target_service": policy.target_service,
            "mtls_mode": policy.mtls_mode,
            "allowed_principals": policy.allowed_principals,
            "denied_principals": policy.denied_principals,
            "jwt_validation": policy.jwt_validation,
            "metadata": policy.metadata,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created security policy: {policy.name} with ID: {policy_id}")

        return {
            "status": "success",
            "data": {"id": policy_id, **_security_policies_db[policy_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating security policy: {e}")
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
):
    """
    List all observability configurations

    Args:
        enabled_only: Only return enabled configurations

    Returns:
        List of observability configurations
    """
    try:
        filtered_configs = []
        for config_id, config in _observability_configs_db.items():
            if enabled_only and not config.get("enabled", True):
                continue
            filtered_configs.append({"id": config_id, **config})

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
async def create_observability_config(config: ObservabilityConfigCreate):
    """
    Create a new observability configuration

    Args:
        config: Observability configuration creation data

    Returns:
        Created observability configuration
    """
    try:
        config_id = _generate_config_id()

        # Create observability configuration
        _observability_configs_db[config_id] = {
            "name": config.name,
            "tracing_enabled": config.tracing_enabled,
            "metrics_enabled": config.metrics_enabled,
            "access_logging_enabled": config.access_logging_enabled,
            "sampling_rate": config.sampling_rate,
            "prometheus_enabled": config.prometheus_enabled,
            "grafana_enabled": config.grafana_enabled,
            "metadata": config.metadata,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created observability config: {config.name} with ID: {config_id}")

        return {
            "status": "success",
            "data": {"id": config_id, **_observability_configs_db[config_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating observability config: {e}")
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
        filtered_policies = []
        for policy_id, policy in _policies_db.items():
            if policy_type and policy.get("policy_type") != policy_type:
                continue
            if target_service and policy.get("target_service") != target_service:
                continue
            if enabled_only and not policy.get("enabled", True):
                continue
            filtered_policies.append({"id": policy_id, **policy})

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
async def create_policy(policy: PolicyCreate):
    """
    Create a new policy

    Args:
        policy: Policy creation data

    Returns:
        Created policy
    """
    try:
        policy_id = _generate_rule_id()

        # Create policy
        _policies_db[policy_id] = {
            "name": policy.name,
            "policy_type": policy.policy_type,
            "target_service": policy.target_service,
            "rules": policy.rules,
            "enabled": policy.enabled,
            "metadata": policy.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created policy: {policy.name} with ID: {policy_id}")

        return {
            "status": "success",
            "data": {"id": policy_id, **_policies_db[policy_id]},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
