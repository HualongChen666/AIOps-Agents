# -*- coding: utf-8 -*-
"""
Service Mesh Repository
Provides database operations for service mesh entities
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger
from sqlalchemy.orm import Session

from core.models import (
    MeshConfiguration,
    ObservabilityConfig,
    Policy,
    SecurityPolicy,
    TrafficRule,
)


class ServiceMeshRepository:
    """Repository for service mesh database operations"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Mesh Configuration Operations ====================

    def create_mesh_configuration(
        self,
        name: str,
        mesh_type: str,
        namespace: str,
        profile: str,
        auto_injection_enabled: bool,
        mtls_enabled: bool,
        resource_limits: Optional[Dict[str, Any]],
        config_metadata: Optional[Dict[str, Any]],
    ) -> MeshConfiguration:
        """Create a new mesh configuration"""
        config_id = str(uuid4())
        mesh_id = f"mesh-{config_id[:8]}"

        config = MeshConfiguration(
            id=config_id,
            name=name,
            mesh_type=mesh_type,
            namespace=namespace,
            profile=profile,
            auto_injection_enabled=auto_injection_enabled,
            mtls_enabled=mtls_enabled,
            resource_limits=resource_limits,
            status="active",
            mesh_id=mesh_id,
            config_metadata=config_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Created mesh configuration: {name} with ID: {config_id}")
        return config

    def get_mesh_configuration(self, config_id: str) -> Optional[MeshConfiguration]:
        """Get mesh configuration by ID"""
        return self.db.query(MeshConfiguration).filter(MeshConfiguration.id == config_id).first()

    def list_mesh_configurations(
        self,
        mesh_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MeshConfiguration]:
        """List mesh configurations with optional filtering"""
        query = self.db.query(MeshConfiguration)

        if mesh_type:
            query = query.filter(MeshConfiguration.mesh_type == mesh_type)
        if status:
            query = query.filter(MeshConfiguration.status == status)

        return query.offset(offset).limit(limit).all()

    def update_mesh_configuration(
        self,
        config_id: str,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        profile: Optional[str] = None,
        auto_injection_enabled: Optional[bool] = None,
        mtls_enabled: Optional[bool] = None,
        resource_limits: Optional[Dict[str, Any]] = None,
        config_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MeshConfiguration]:
        """Update mesh configuration"""
        config = self.get_mesh_configuration(config_id)
        if not config:
            return None

        if name is not None:
            config.name = name
        if namespace is not None:
            config.namespace = namespace
        if profile is not None:
            config.profile = profile
        if auto_injection_enabled is not None:
            config.auto_injection_enabled = auto_injection_enabled
        if mtls_enabled is not None:
            config.mtls_enabled = mtls_enabled
        if resource_limits is not None:
            config.resource_limits = resource_limits
        if config_metadata is not None:
            config.config_metadata = config_metadata

        config.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Updated mesh configuration: {config_id}")
        return config

    def delete_mesh_configuration(self, config_id: str) -> bool:
        """Delete mesh configuration"""
        config = self.get_mesh_configuration(config_id)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()

        logger.info(f"Deleted mesh configuration: {config_id}")
        return True

    # ==================== Traffic Rule Operations ====================

    def create_traffic_rule(
        self,
        name: str,
        service_name: str,
        match_conditions: Dict[str, Any],
        destination: Dict[str, Any],
        weight: int,
        timeout_seconds: int,
        retry_policy: Optional[Dict[str, Any]],
        fault_injection: Optional[Dict[str, Any]],
        rule_metadata: Optional[Dict[str, Any]],
    ) -> TrafficRule:
        """Create a new traffic rule"""
        rule_id = str(uuid4())

        rule = TrafficRule(
            id=rule_id,
            name=name,
            service_name=service_name,
            match_conditions=match_conditions,
            destination=destination,
            weight=weight,
            timeout_seconds=timeout_seconds,
            retry_policy=retry_policy,
            fault_injection=fault_injection,
            enabled=True,
            rule_metadata=rule_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Created traffic rule: {name} with ID: {rule_id}")
        return rule

    def get_traffic_rule(self, rule_id: str) -> Optional[TrafficRule]:
        """Get traffic rule by ID"""
        return self.db.query(TrafficRule).filter(TrafficRule.id == rule_id).first()

    def list_traffic_rules(
        self,
        service_name: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[TrafficRule]:
        """List traffic rules with optional filtering"""
        query = self.db.query(TrafficRule)

        if service_name:
            query = query.filter(TrafficRule.service_name == service_name)
        if enabled_only:
            query = query.filter(TrafficRule.enabled == True)

        return query.all()

    def update_traffic_rule(
        self,
        rule_id: str,
        name: Optional[str] = None,
        match_conditions: Optional[Dict[str, Any]] = None,
        destination: Optional[Dict[str, Any]] = None,
        weight: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        retry_policy: Optional[Dict[str, Any]] = None,
        fault_injection: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        rule_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TrafficRule]:
        """Update traffic rule"""
        rule = self.get_traffic_rule(rule_id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if match_conditions is not None:
            rule.match_conditions = match_conditions
        if destination is not None:
            rule.destination = destination
        if weight is not None:
            rule.weight = weight
        if timeout_seconds is not None:
            rule.timeout_seconds = timeout_seconds
        if retry_policy is not None:
            rule.retry_policy = retry_policy
        if fault_injection is not None:
            rule.fault_injection = fault_injection
        if enabled is not None:
            rule.enabled = enabled
        if rule_metadata is not None:
            rule.rule_metadata = rule_metadata

        rule.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)

        logger.info(f"Updated traffic rule: {rule_id}")
        return rule

    def delete_traffic_rule(self, rule_id: str) -> bool:
        """Delete traffic rule"""
        rule = self.get_traffic_rule(rule_id)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.commit()

        logger.info(f"Deleted traffic rule: {rule_id}")
        return True

    # ==================== Security Policy Operations ====================

    def create_security_policy(
        self,
        name: str,
        policy_type: str,
        target_service: str,
        mtls_mode: str,
        allowed_principals: List[str],
        denied_principals: List[str],
        jwt_validation: Optional[Dict[str, Any]],
        policy_metadata: Optional[Dict[str, Any]],
    ) -> SecurityPolicy:
        """Create a new security policy"""
        policy_id = str(uuid4())

        policy = SecurityPolicy(
            id=policy_id,
            name=name,
            policy_type=policy_type,
            target_service=target_service,
            mtls_mode=mtls_mode,
            allowed_principals=allowed_principals,
            denied_principals=denied_principals,
            jwt_validation=jwt_validation,
            enabled=True,
            policy_metadata=policy_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Created security policy: {name} with ID: {policy_id}")
        return policy

    def get_security_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """Get security policy by ID"""
        return self.db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    def list_security_policies(
        self,
        policy_type: Optional[str] = None,
        target_service: Optional[str] = None,
    ) -> List[SecurityPolicy]:
        """List security policies with optional filtering"""
        query = self.db.query(SecurityPolicy)

        if policy_type:
            query = query.filter(SecurityPolicy.policy_type == policy_type)
        if target_service:
            query = query.filter(SecurityPolicy.target_service == target_service)

        return query.all()

    def update_security_policy(
        self,
        policy_id: str,
        name: Optional[str] = None,
        mtls_mode: Optional[str] = None,
        allowed_principals: Optional[List[str]] = None,
        denied_principals: Optional[List[str]] = None,
        jwt_validation: Optional[Dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        policy_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[SecurityPolicy]:
        """Update security policy"""
        policy = self.get_security_policy(policy_id)
        if not policy:
            return None

        if name is not None:
            policy.name = name
        if mtls_mode is not None:
            policy.mtls_mode = mtls_mode
        if allowed_principals is not None:
            policy.allowed_principals = allowed_principals
        if denied_principals is not None:
            policy.denied_principals = denied_principals
        if jwt_validation is not None:
            policy.jwt_validation = jwt_validation
        if enabled is not None:
            policy.enabled = enabled
        if policy_metadata is not None:
            policy.policy_metadata = policy_metadata

        policy.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Updated security policy: {policy_id}")
        return policy

    def delete_security_policy(self, policy_id: str) -> bool:
        """Delete security policy"""
        policy = self.get_security_policy(policy_id)
        if not policy:
            return False

        self.db.delete(policy)
        self.db.commit()

        logger.info(f"Deleted security policy: {policy_id}")
        return True

    # ==================== Observability Config Operations ====================

    def create_observability_config(
        self,
        name: str,
        tracing_enabled: bool,
        metrics_enabled: bool,
        access_logging_enabled: bool,
        sampling_rate: float,
        prometheus_enabled: bool,
        grafana_enabled: bool,
        config_metadata: Optional[Dict[str, Any]],
    ) -> ObservabilityConfig:
        """Create a new observability configuration"""
        config_id = str(uuid4())

        config = ObservabilityConfig(
            id=config_id,
            name=name,
            tracing_enabled=tracing_enabled,
            metrics_enabled=metrics_enabled,
            access_logging_enabled=access_logging_enabled,
            sampling_rate=sampling_rate,
            prometheus_enabled=prometheus_enabled,
            grafana_enabled=grafana_enabled,
            enabled=True,
            config_metadata=config_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Created observability config: {name} with ID: {config_id}")
        return config

    def get_observability_config(self, config_id: str) -> Optional[ObservabilityConfig]:
        """Get observability configuration by ID"""
        return self.db.query(ObservabilityConfig).filter(ObservabilityConfig.id == config_id).first()

    def list_observability_configs(self, enabled_only: bool = False) -> List[ObservabilityConfig]:
        """List observability configurations with optional filtering"""
        query = self.db.query(ObservabilityConfig)

        if enabled_only:
            query = query.filter(ObservabilityConfig.enabled == True)

        return query.all()

    def update_observability_config(
        self,
        config_id: str,
        name: Optional[str] = None,
        tracing_enabled: Optional[bool] = None,
        metrics_enabled: Optional[bool] = None,
        access_logging_enabled: Optional[bool] = None,
        sampling_rate: Optional[float] = None,
        prometheus_enabled: Optional[bool] = None,
        grafana_enabled: Optional[bool] = None,
        enabled: Optional[bool] = None,
        config_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ObservabilityConfig]:
        """Update observability configuration"""
        config = self.get_observability_config(config_id)
        if not config:
            return None

        if name is not None:
            config.name = name
        if tracing_enabled is not None:
            config.tracing_enabled = tracing_enabled
        if metrics_enabled is not None:
            config.metrics_enabled = metrics_enabled
        if access_logging_enabled is not None:
            config.access_logging_enabled = access_logging_enabled
        if sampling_rate is not None:
            config.sampling_rate = sampling_rate
        if prometheus_enabled is not None:
            config.prometheus_enabled = prometheus_enabled
        if grafana_enabled is not None:
            config.grafana_enabled = grafana_enabled
        if enabled is not None:
            config.enabled = enabled
        if config_metadata is not None:
            config.config_metadata = config_metadata

        config.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(config)

        logger.info(f"Updated observability config: {config_id}")
        return config

    def delete_observability_config(self, config_id: str) -> bool:
        """Delete observability configuration"""
        config = self.get_observability_config(config_id)
        if not config:
            return False

        self.db.delete(config)
        self.db.commit()

        logger.info(f"Deleted observability config: {config_id}")
        return True

    # ==================== Policy Operations ====================

    def create_policy(
        self,
        name: str,
        policy_type: str,
        target_service: str,
        rules: List[Dict[str, Any]],
        enabled: bool,
        policy_metadata: Optional[Dict[str, Any]],
    ) -> Policy:
        """Create a new policy"""
        policy_id = str(uuid4())

        policy = Policy(
            id=policy_id,
            name=name,
            policy_type=policy_type,
            target_service=target_service,
            rules=rules,
            enabled=enabled,
            policy_metadata=policy_metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        self.db.add(policy)
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Created policy: {name} with ID: {policy_id}")
        return policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID"""
        return self.db.query(Policy).filter(Policy.id == policy_id).first()

    def list_policies(
        self,
        policy_type: Optional[str] = None,
        target_service: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[Policy]:
        """List policies with optional filtering"""
        query = self.db.query(Policy)

        if policy_type:
            query = query.filter(Policy.policy_type == policy_type)
        if target_service:
            query = query.filter(Policy.target_service == target_service)
        if enabled_only:
            query = query.filter(Policy.enabled == True)

        return query.all()

    def update_policy(
        self,
        policy_id: str,
        name: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        enabled: Optional[bool] = None,
        policy_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Policy]:
        """Update policy"""
        policy = self.get_policy(policy_id)
        if not policy:
            return None

        if name is not None:
            policy.name = name
        if rules is not None:
            policy.rules = rules
        if enabled is not None:
            policy.enabled = enabled
        if policy_metadata is not None:
            policy.policy_metadata = policy_metadata

        policy.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(policy)

        logger.info(f"Updated policy: {policy_id}")
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        """Delete policy"""
        policy = self.get_policy(policy_id)
        if not policy:
            return False

        self.db.delete(policy)
        self.db.commit()

        logger.info(f"Deleted policy: {policy_id}")
        return True
