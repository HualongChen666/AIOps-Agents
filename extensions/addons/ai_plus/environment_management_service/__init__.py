"""
Environment Management Service

A microservice for managing multiple environments (dev, staging, prod) with
configuration synchronization, deployment orchestration, and health monitoring.
"""

from .environment_manager import (
    EnvironmentManager,
    Environment
)
from .config_sync import (
    ConfigSync,
    SyncStrategy,
    SyncResult
)
from .deployment_orchestrator import (
    DeploymentOrchestrator,
    Deployment,
    DeploymentStatus,
    DeploymentType
)

__version__ = '1.0.0'
__all__ = [
    'EnvironmentManager',
    'Environment',
    'ConfigSync',
    'SyncStrategy',
    'SyncResult',
    'DeploymentOrchestrator',
    'Deployment',
    'DeploymentStatus',
    'DeploymentType',
]
