# -*- coding: utf-8 -*-
"""
Service Mesh Manager
Enterprise-grade service mesh configuration management for Istio integration
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger


class ServiceMeshType(Enum):
    """Service mesh type"""

    ISTIO = "istio"
    LINKERD = "linkerd"
    CONSUL = "consul"


class MeshStatus(Enum):
    """Service mesh status"""

    NOT_CONFIGURED = "not_configured"
    CONFIGURED = "configured"
    DEPLOYED = "deployed"
    ERROR = "error"


@dataclass
class IstioConfig:
    """Istio configuration"""

    mesh_id: str
    control_plane_config: Dict[str, Any]
    data_plane_config: Dict[str, Any]
    auto_injection_enabled: bool = True
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrafficConfig:
    """Traffic management configuration"""

    service_name: str
    routing_rules: List[Dict[str, Any]]
    mirroring_config: Optional[Dict[str, Any]] = None
    fault_injection_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Security configuration"""

    mesh_id: str
    mtls_enabled: bool = True
    authentication_policies: List[Dict[str, Any]] = field(default_factory=list)
    authorization_policies: List[Dict[str, Any]] = field(default_factory=list)
    security_policies: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceMeshManager:
    """
    Enterprise-grade service mesh manager
    Provides Istio configuration management and preparation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize service mesh manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Service mesh configurations
        self.istio_configs: Dict[str, IstioConfig] = {}
        self.traffic_configs: Dict[str, TrafficConfig] = {}
        self.security_configs: Dict[str, SecurityConfig] = {}

        # Mesh status
        self.mesh_status: MeshStatus = MeshStatus.NOT_CONFIGURED
        self.mesh_type: ServiceMeshType = ServiceMeshType.ISTIO

        # Configuration templates
        self.config_templates = self._load_config_templates()

        # Statistics
        self.total_configs_generated = 0
        self.configs_applied = 0

        logger.info("Service mesh manager initialized")

    def _load_config_templates(self) -> Dict[str, Any]:
        """
        Load configuration templates

        Returns:
            Configuration templates
        """
        return {
            "istio_control_plane": {
                "apiVersion": "install.istio.io/v1alpha1",
                "kind": "IstioOperator",
                "metadata": {"name": "istio-control-plane", "namespace": "istio-system"},
                "spec": {
                    "profile": "default",
                    "components": {
                        "pilot": {
                            "enabled": True,
                            "k8s": {
                                "resources": {
                                    "requests": {"cpu": "500m", "memory": "2048Mi"},
                                    "limits": {"cpu": "2000m", "memory": "4096Mi"},
                                }
                            },
                        }
                    },
                },
            },
            "istio_auto_injection": {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": "default", "labels": {"istio-injection": "enabled"}},
            },
            "virtual_service": {
                "apiVersion": "networking.istio.io/v1beta1",
                "kind": "VirtualService",
                "metadata": {"name": "service-name", "namespace": "default"},
                "spec": {
                    "hosts": ["service"],
                    "http": [
                        {
                            "route": [
                                {"destination": {"host": "service", "subset": "v1"}, "weight": 100}
                            ]
                        }
                    ],
                },
            },
            "destination_rule": {
                "apiVersion": "networking.istio.io/v1beta1",
                "kind": "DestinationRule",
                "metadata": {"name": "service-name", "namespace": "default"},
                "spec": {
                    "host": "service",
                    "subsets": [{"name": "v1", "labels": {"version": "v1"}}],
                },
            },
        }

    def generate_istio_control_plane_config(
        self,
        mesh_id: str,
        namespace: str = "istio-system",
        profile: str = "default",
        resource_limits: Optional[Dict[str, Any]] = None,
    ) -> IstioConfig:
        """
        Generate Istio control plane configuration

        Args:
            mesh_id: Mesh ID
            namespace: Kubernetes namespace
            profile: Istio profile
            resource_limits: Resource limits

        Returns:
            Istio configuration
        """
        template = self.config_templates["istio_control_plane"].copy()
        template["metadata"]["name"] = f"istio-{mesh_id}"
        template["metadata"]["namespace"] = namespace
        template["spec"]["profile"] = profile

        if resource_limits:
            template["spec"]["components"]["pilot"]["k8s"]["resources"] = resource_limits

        config = IstioConfig(
            mesh_id=mesh_id,
            control_plane_config=template,
            data_plane_config={},
            auto_injection_enabled=True,
            resource_limits=resource_limits or {},
        )

        self.istio_configs[mesh_id] = config
        self.total_configs_generated += 1

        logger.info(f"Generated Istio control plane config for mesh: {mesh_id}")

        return config

    def generate_auto_injection_config(
        self, namespace: str = "default", enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Generate auto-injection configuration

        Args:
            namespace: Kubernetes namespace
            enabled: Enable auto-injection

        Returns:
            Auto-injection configuration
        """
        template: Dict[str, Any] = self.config_templates["istio_auto_injection"].copy()
        template["metadata"]["name"] = namespace
        template["metadata"]["labels"]["istio-injection"] = "enabled" if enabled else "disabled"

        logger.info(f"Generated auto-injection config for namespace: {namespace}")

        return template

    def generate_virtual_service_config(
        self, service_name: str, routing_rules: List[Dict[str, Any]], namespace: str = "default"
    ) -> TrafficConfig:
        """
        Generate virtual service configuration for traffic management

        Args:
            service_name: Service name
            routing_rules: Routing rules
            namespace: Kubernetes namespace

        Returns:
            Traffic configuration
        """
        template = self.config_templates["virtual_service"].copy()
        template["metadata"]["name"] = f"{service_name}-vs"
        template["metadata"]["namespace"] = namespace
        template["spec"]["hosts"] = [service_name]
        template["spec"]["http"] = routing_rules

        config = TrafficConfig(
            service_name=service_name,
            routing_rules=routing_rules,
            metadata={"namespace": namespace},
        )

        self.traffic_configs[service_name] = config
        self.total_configs_generated += 1

        logger.info(f"Generated virtual service config for service: {service_name}")

        return config

    def generate_destination_rule_config(
        self, service_name: str, subsets: List[Dict[str, Any]], namespace: str = "default"
    ) -> Dict[str, Any]:
        """
        Generate destination rule configuration

        Args:
            service_name: Service name
            subsets: Service subsets
            namespace: Kubernetes namespace

        Returns:
            Destination rule configuration
        """
        template: Dict[str, Any] = self.config_templates["destination_rule"].copy()
        template["metadata"]["name"] = f"{service_name}-dr"
        template["metadata"]["namespace"] = namespace
        template["spec"]["host"] = service_name
        template["spec"]["subsets"] = subsets

        logger.info(f"Generated destination rule config for service: {service_name}")

        return template

    def generate_mtls_config(
        self, mesh_id: str, namespace: str = "istio-system", strict_mode: bool = True
    ) -> SecurityConfig:
        """
        Generate mTLS configuration

        Args:
            mesh_id: Mesh ID
            namespace: Kubernetes namespace
            strict_mode: Strict mTLS mode

        Returns:
            Security configuration
        """
        peer_authentication = {
            "apiVersion": "security.istio.io/v1beta1",
            "kind": "PeerAuthentication",
            "metadata": {"name": f"mtls-{mesh_id}", "namespace": namespace},
            "spec": {"mtls": {"mode": "STRICT" if strict_mode else "PERMISSIVE"}},
        }

        config = SecurityConfig(
            mesh_id=mesh_id,
            mtls_enabled=True,
            authentication_policies=[peer_authentication],
            metadata={"namespace": namespace},
        )

        self.security_configs[mesh_id] = config
        self.total_configs_generated += 1

        logger.info(f"Generated mTLS config for mesh: {mesh_id}")

        return config

    def generate_service_mesh_summary(self) -> Dict[str, Any]:
        """
        Generate service mesh summary

        Returns:
            Service mesh summary
        """
        return {
            "mesh_type": self.mesh_type.value,
            "mesh_status": self.mesh_status.value,
            "istio_configs_count": len(self.istio_configs),
            "traffic_configs_count": len(self.traffic_configs),
            "security_configs_count": len(self.security_configs),
            "total_configs_generated": self.total_configs_generated,
            "configs_applied": self.configs_applied,
            "supported_features": [
                "istio_control_plane_config",
                "auto_injection_config",
                "virtual_service_config",
                "destination_rule_config",
                "mtls_config",
                "traffic_mirroring",
                "fault_injection",
            ],
        }

    def export_config_to_yaml(self, config: Dict[str, Any], filename: str) -> None:
        """
        Export configuration to YAML file

        Args:
            config: Configuration dictionary
            filename: Output filename
        """
        try:
            with open(filename, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
            logger.info(f"Exported configuration to {filename}")
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            raise

    def export_config_to_json(self, config: Dict[str, Any], filename: str) -> None:
        """
        Export configuration to JSON file

        Args:
            config: Configuration dictionary
            filename: Output filename
        """
        try:
            with open(filename, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Exported configuration to {filename}")
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            raise

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic validation
            if not config:
                return False

            if "apiVersion" not in config or "kind" not in config:
                return False

            return True
        except Exception as e:
            logger.error(f"Error validating configuration: {e}")
            return False


# Global instance
_service_mesh_manager: Optional[ServiceMeshManager] = None


def get_service_mesh_manager() -> ServiceMeshManager:
    """
    Get the global service mesh manager instance

    Returns:
        ServiceMeshManager instance
    """
    global _service_mesh_manager
    if _service_mesh_manager is None:
        _service_mesh_manager = ServiceMeshManager()
    return _service_mesh_manager
