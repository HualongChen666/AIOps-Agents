# -*- coding: utf-8 -*-
"""Core service logic for the Service Mesh microservice."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.infra_executor import BaseInfraService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "evaluate_service_mesh",
    "select_service_mesh",
    "prepare_kubernetes",
    "install_service_mesh",
    "configure_control_plane",
    "configure_data_plane",
    "verify_installation",
    "configure_traffic_routing",
    "configure_load_balancing",
    "configure_circuit_breaker",
    "configure_timeout_and_retry",
    "configure_fault_injection",
    "configure_traffic_mirroring",
    "configure_canary_release",
    "configure_blue_green_deployment",
    "configure_mtls",
    "configure_identity_authorization",
    "configure_jwt",
    "configure_oauth2",
    "configure_rbac",
    "configure_network_policy",
    "configure_key_management",
    "configure_certificate_rotation",
    "integrate_prometheus",
    "integrate_grafana",
    "integrate_jaeger",
    "collect_metrics",
    "collect_logs",
    "correlate_traces",
    "analyze_performance",
    "define_sli_slo",
    "test_and_optimize_service_mesh",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "evaluate_service_mesh": {
        "executor": "k8s",
        "command": ["istioctl", "analyze"],
    },
    "select_service_mesh": {
        "executor": "k8s",
        "command": ["istioctl", "profile", "list"],
    },
    "prepare_kubernetes": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "istio-init.yaml"],
    },
    "install_service_mesh": {
        "executor": "k8s",
        "command": ["istioctl", "install", "--set", "profile=default"],
    },
    "configure_data_plane": {
        "executor": "k8s",
        "command": ["kubectl", "label", "namespace", "default", "istio-injection=enabled"],
    },
    "verify_installation": {
        "executor": "k8s",
        "command": ["istioctl", "verify-install"],
    },
    "configure_load_balancing": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "destinationrule.yaml"],
    },
    "configure_circuit_breaker": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "destinationrule-cb.yaml"],
    },
    "configure_timeout_and_retry": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "virtualservice-timeout.yaml"],
    },
    "configure_fault_injection": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "virtualservice-fault.yaml"],
    },
    "configure_traffic_mirroring": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "virtualservice-mirror.yaml"],
    },
    "configure_canary_release": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "virtualservice-canary.yaml"],
    },
    "configure_blue_green_deployment": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "virtualservice-bg.yaml"],
    },
    "configure_mtls": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "peerauthentication.yaml"],
    },
    "configure_identity_authorization": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "authorizationpolicy.yaml"],
    },
    "configure_jwt": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "requestauthentication.yaml"],
    },
    "configure_oauth2": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "authorizationpolicy-oauth2.yaml"],
    },
    "configure_network_policy": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "networkpolicy.yaml"],
    },
    "configure_key_management": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "secret.yaml"],
    },
    "configure_certificate_rotation": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "cert-manager.yaml"],
    },
    "integrate_prometheus": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "servicemonitor.yaml"],
    },
    "integrate_grafana": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "grafana-istio.yaml"],
    },
    "integrate_jaeger": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "jaeger.yaml"],
    },
    "collect_metrics": {
        "executor": "k8s",
        "command": ["kubectl", "get", "servicemonitor"],
    },
    "collect_logs": {
        "executor": "k8s",
        "command": ["kubectl", "logs", "istiod"],
    },
    "correlate_traces": {
        "executor": "k8s",
        "command": ["kubectl", "get", "jaeger"],
    },
    "analyze_performance": {
        "executor": "k8s",
        "command": ["kubectl", "get", "destinationrule"],
    },
    "define_sli_slo": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "slo.yaml"],
    },
    "test_and_optimize_service_mesh": {
        "executor": "k8s",
        "command": ["istioctl", "analyze"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["kubectl", "apply", "-f", f"{op}.yaml"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Service Mesh."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Service Mesh"
