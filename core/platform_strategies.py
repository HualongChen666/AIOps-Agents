# -*- coding: utf-8 -*-
# core/platform_strategies.py
"""Platform Strategy Pattern Implementation

Provides strategy pattern for platform-specific repair operations,
eliminating if/elif chains and enabling easy addition of new platforms.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PlatformStrategy(ABC):
    """Abstract base class for platform-specific repair strategies."""

    @abstractmethod
    def get_scripts(self) -> Dict[str, Any]:
        """Get available repair scripts for this platform.

        Returns:
            Dictionary of repair scripts
        """

    @abstractmethod
    async def execute_repair(
        self, script_key: str, host_name: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Execute a repair script on this platform.

        Args:
            script_key: Repair script key
            host_name: Target host name (may be None for some platforms)
            params: Repair script parameters

        Returns:
            Repair execution result
        """

    @abstractmethod
    def get_history(self, limit: int) -> List[Dict[str, Any]]:
        """Get repair history for this platform.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of repair history records
        """

    @abstractmethod
    def requires_host_name(self) -> bool:
        """Check if this platform requires host_name parameter.

        Returns:
            True if host_name is required
        """


class WindowsStrategy(PlatformStrategy):
    """Windows platform repair strategy."""

    def __init__(self):
        from core.windows_repair import (
            WINDOWS_REPAIR_SCRIPTS,
            execute_windows_repair,
            get_windows_repair_history,
        )

        self._execute_repair = execute_windows_repair
        self._get_history = get_windows_repair_history
        self._scripts = WINDOWS_REPAIR_SCRIPTS

    def get_scripts(self) -> Dict[str, Any]:
        return self._scripts

    async def execute_repair(
        self, script_key: str, host_name: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        return await self._execute_repair(script_key, params)

    def get_history(self, limit: int) -> List[Dict[str, Any]]:
        return self._get_history(limit)

    def requires_host_name(self) -> bool:
        return False


class LinuxStrategy(PlatformStrategy):
    """Linux platform repair strategy."""

    def __init__(self):
        from core.linux_repair import (
            execute_linux_repair,
            get_linux_repair_history,
            get_linux_repair_scripts,
        )

        self._execute_repair = execute_linux_repair
        self._get_scripts = get_linux_repair_scripts
        self._get_history = get_linux_repair_history

    def get_scripts(self) -> Dict[str, Any]:
        scripts = self._get_scripts()
        if isinstance(scripts, dict):
            return scripts
        # Convert list to dict for consistency with other platforms
        return {script.get("key", str(i)): script for i, script in enumerate(scripts)}

    async def execute_repair(
        self, script_key: str, host_name: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        return await self._execute_repair(host_name, script_key, params)

    def get_history(self, limit: int) -> List[Dict[str, Any]]:
        return self._get_history(limit)

    def requires_host_name(self) -> bool:
        return True


class DockerStrategy(PlatformStrategy):
    """Docker platform repair strategy."""

    def __init__(self):
        from core.docker_repair import (
            execute_repair_sync,
            get_docker_repair_history,
            get_docker_repair_scripts,
        )

        self._execute_repair = execute_repair_sync
        self._get_scripts = get_docker_repair_scripts
        self._get_history = get_docker_repair_history

    def get_scripts(self) -> Dict[str, Any]:
        return self._get_scripts()

    async def execute_repair(
        self, script_key: str, host_name: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        return await self._execute_repair(host_name, script_key, params)

    def get_history(self, limit: int) -> List[Dict[str, Any]]:
        return self._get_history(limit)

    def requires_host_name(self) -> bool:
        return True


class KubernetesStrategy(PlatformStrategy):
    """Kubernetes platform repair strategy."""

    def __init__(self):
        from core.k8s_repair import execute_repair as k8s_execute_repair
        from core.k8s_repair import (
            get_k8s_repair_history,
        )

        self._execute_repair = k8s_execute_repair
        self._get_history = get_k8s_repair_history

    def get_scripts(self) -> Dict[str, Any]:
        # K8s scripts are not centrally managed like Windows/Linux
        return {}

    async def execute_repair(
        self, script_key: str, host_name: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        # Find host config by host_name
        from config import K8S_HOSTS

        host_cfg = None
        for cfg in K8S_HOSTS:
            if cfg.get("host") == host_name:
                host_cfg = cfg
                break

        if not host_cfg:
            return {"success": False, "error": f"Host not found: {host_name}"}

        return await self._execute_repair(host_cfg, script_key, params)

    def get_history(self, limit: int) -> List[Dict[str, Any]]:
        return self._get_history(limit)

    def requires_host_name(self) -> bool:
        return True


# Strategy registry
PLATFORM_STRATEGIES: Dict[str, PlatformStrategy] = {
    "windows": WindowsStrategy(),
    "linux": LinuxStrategy(),
    "docker": DockerStrategy(),
    "kubernetes": KubernetesStrategy(),
}


def get_platform_strategy(platform: str) -> PlatformStrategy:
    """Get platform strategy by platform name.

    Args:
        platform: Platform name (windows, linux, docker, kubernetes)

    Returns:
        Platform strategy instance

    Raises:
        ValueError: If platform is not supported
    """
    strategy = PLATFORM_STRATEGIES.get(platform)
    if not strategy:
        raise ValueError(f"Unsupported platform: {platform}")
    return strategy


def get_all_platform_strategies() -> Dict[str, PlatformStrategy]:
    """Get all registered platform strategies.

    Returns:
        Dictionary of platform name to strategy
    """
    return PLATFORM_STRATEGIES.copy()
