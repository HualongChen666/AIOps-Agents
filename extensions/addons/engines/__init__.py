"""Shared addon engine package.

The seven engines below are the only execution surfaces used by all 57 addons.
Each engine is responsible for real business logic in its domain; addon
``service.py`` modules are thin, stateless wrappers that delegate here.
"""

from __future__ import annotations

from extensions.addons.engines.connector_bus import ConnectorBus
from extensions.addons.engines.doc_policy_engine import DocEngine, PolicyEngine
from extensions.addons.engines.infra_executor import (
    AnsibleExecutor,
    BaseInfraService,
    CliExecutor,
    HelmExecutor,
    K8sExecutor,
    TerraformExecutor,
)
from extensions.addons.engines.monitoring_provider import (
    BaseObservabilityService,
    MonitoringProvider,
)
from extensions.addons.engines.security_scanner import (
    BaseSecurityService,
    SecurityScanner,
)
from extensions.addons.engines.storage_driver import StorageDriver
from extensions.addons.engines.workflow_engine import (
    RunbookRunner,
    WorkflowEngine,
)

__all__ = [
    "ConnectorBus",
    "DocEngine",
    "PolicyEngine",
    "AnsibleExecutor",
    "BaseInfraService",
    "CliExecutor",
    "HelmExecutor",
    "K8sExecutor",
    "TerraformExecutor",
    "BaseObservabilityService",
    "MonitoringProvider",
    "BaseSecurityService",
    "SecurityScanner",
    "StorageDriver",
    "RunbookRunner",
    "WorkflowEngine",
]
