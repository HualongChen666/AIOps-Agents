# -*- coding: utf-8 -*-
"""gRPC client for Dependency Management Service."""

import logging
from typing import Any, Dict, Optional

import httpx

from ..config import Config

logger = logging.getLogger(Config.SERVICE_NAME)


class DependencyManagementRPCClient:
    """HTTP client for dependency management service RPC calls."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
    ) -> None:
        """Initialize the RPC client.

        Args:
            host: Service host
            port: Service port
        """
        self._host = host or Config.HOST
        self._port = port or Config.PORT
        self._base_url = f"http://{self._host}:{self._port}"
        self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def call(self, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        """Call an RPC method.

        Args:
            method: Name of the method to call
            payload: Arguments to pass to the method

        Returns:
            Result from the method

        Raises:
            ValueError: If method call fails
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self._client.post(
                f"{self._base_url}/rpc/{method}",
                json=payload or {},
            )
            response.raise_for_status()

            data = response.json()
            if data.get("success"):
                return data.get("result")
            else:
                raise ValueError(data.get("error", "RPC call failed"))

        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling {method}: {e}")
            raise ValueError(f"RPC call failed: {e}")
        except Exception as e:
            logger.error(f"Error calling {method}: {e}", exc_info=True)
            raise

    async def scan_dependencies(
        self, project_path: str, scan_types: Optional[list] = None
    ) -> Dict[str, Any]:
        """Scan dependencies from a project.

        Args:
            project_path: Path to the project directory
            scan_types: List of file types to scan

        Returns:
            Scan result with dependencies and metadata
        """
        return await self.call(
            "scan_dependencies",
            {"project_path": project_path, "scan_types": scan_types},
        )

    async def check_outdated(
        self, project_path: str, package_names: Optional[list] = None
    ) -> Dict[str, Any]:
        """Check for outdated dependencies.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to check

        Returns:
            List of outdated packages
        """
        return await self.call(
            "check_outdated",
            {"project_path": project_path, "package_names": package_names},
        )

    async def check_vulnerabilities(
        self,
        project_path: str,
        package_names: Optional[list] = None,
        severity_level: str = "medium",
    ) -> Dict[str, Any]:
        """Check for security vulnerabilities.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to check
            severity_level: Minimum severity level

        Returns:
            List of vulnerabilities
        """
        return await self.call(
            "check_vulnerabilities",
            {
                "project_path": project_path,
                "package_names": package_names,
                "severity_level": severity_level,
            },
        )

    async def update_dependencies(
        self,
        project_path: str,
        package_names: Optional[list] = None,
        update_type: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Update dependencies.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to update
            update_type: Type of update (all, specific, security)
            dry_run: If True, only simulate the update

        Returns:
            Update results
        """
        return await self.call(
            "update_dependencies",
            {
                "project_path": project_path,
                "package_names": package_names,
                "update_type": update_type,
                "dry_run": dry_run,
            },
        )

    async def detect_conflicts(
        self, project_path: str, package_names: Optional[list] = None
    ) -> Dict[str, Any]:
        """Detect dependency conflicts.

        Args:
            project_path: Path to the project directory
            package_names: Specific packages to check

        Returns:
            List of conflicts
        """
        return await self.call(
            "detect_conflicts",
            {"project_path": project_path, "package_names": package_names},
        )

    async def generate_lock_file(
        self, project_path: str, lock_file_type: str = "requirements.lock"
    ) -> Dict[str, Any]:
        """Generate a lock file.

        Args:
            project_path: Path to the project directory
            lock_file_type: Type of lock file to generate

        Returns:
            Lock file generation result
        """
        return await self.call(
            "generate_lock_file",
            {"project_path": project_path, "lock_file_type": lock_file_type},
        )

    async def get_dependency_tree(
        self, project_path: str, package_name: str, depth: int = 3
    ) -> Dict[str, Any]:
        """Get dependency tree for a package.

        Args:
            project_path: Path to the project directory
            package_name: Name of the package
            depth: Maximum depth to traverse

        Returns:
            Dependency tree
        """
        return await self.call(
            "get_dependency_tree",
            {"project_path": project_path, "package_name": package_name, "depth": depth},
        )

    async def resolve_dependencies(
        self, project_path: str, requirements: list
    ) -> Dict[str, Any]:
        """Resolve dependencies.

        Args:
            project_path: Path to the project directory
            requirements: List of requirement strings

        Returns:
            Resolved dependencies
        """
        return await self.call(
            "resolve_dependencies",
            {"project_path": project_path, "requirements": requirements},
        )

    async def list_methods(self) -> list:
        """List available RPC methods.

        Returns:
            List of method names
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self._client.get(f"{self._base_url}/rpc")
            response.raise_for_status()
            data = response.json()
            return data.get("methods", [])
        except Exception as e:
            logger.error(f"Error listing methods: {e}")
            return []


# Synchronous wrapper for convenience
class SyncDependencyManagementRPCClient:
    """Synchronous wrapper for the RPC client."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
    ) -> None:
        """Initialize the sync RPC client.

        Args:
            host: Service host
            port: Service port
        """
        self._async_client = DependencyManagementRPCClient(host, port)

    def scan_dependencies(
        self, project_path: str, scan_types: Optional[list] = None
    ) -> Dict[str, Any]:
        """Scan dependencies from a project (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.scan_dependencies(project_path, scan_types)

        return asyncio.run(_call())

    def check_outdated(
        self, project_path: str, package_names: Optional[list] = None
    ) -> Dict[str, Any]:
        """Check for outdated dependencies (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.check_outdated(project_path, package_names)

        return asyncio.run(_call())

    def check_vulnerabilities(
        self,
        project_path: str,
        package_names: Optional[list] = None,
        severity_level: str = "medium",
    ) -> Dict[str, Any]:
        """Check for security vulnerabilities (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.check_vulnerabilities(
                    project_path, package_names, severity_level
                )

        return asyncio.run(_call())

    def update_dependencies(
        self,
        project_path: str,
        package_names: Optional[list] = None,
        update_type: str = "all",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Update dependencies (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.update_dependencies(
                    project_path, package_names, update_type, dry_run
                )

        return asyncio.run(_call())

    def detect_conflicts(
        self, project_path: str, package_names: Optional[list] = None
    ) -> Dict[str, Any]:
        """Detect dependency conflicts (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.detect_conflicts(project_path, package_names)

        return asyncio.run(_call())

    def generate_lock_file(
        self, project_path: str, lock_file_type: str = "requirements.lock"
    ) -> Dict[str, Any]:
        """Generate a lock file (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.generate_lock_file(project_path, lock_file_type)

        return asyncio.run(_call())

    def get_dependency_tree(
        self, project_path: str, package_name: str, depth: int = 3
    ) -> Dict[str, Any]:
        """Get dependency tree (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.get_dependency_tree(project_path, package_name, depth)

        return asyncio.run(_call())

    def resolve_dependencies(
        self, project_path: str, requirements: list
    ) -> Dict[str, Any]:
        """Resolve dependencies (synchronous)."""
        import asyncio

        async def _call():
            async with self._async_client as client:
                return await client.resolve_dependencies(project_path, requirements)

        return asyncio.run(_call())
