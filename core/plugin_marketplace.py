# -*- coding: utf-8 -*-
"""
Plugin Marketplace with Version Signing for AIOps Platform
Provides a secure plugin marketplace with digital signatures for plugin verification
"""

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Plugin status enumeration"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class SecurityLevel(Enum):
    """Security level enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PluginSignature:
    """Represents a plugin digital signature"""

    plugin_id: str
    version: str
    signature: str
    algorithm: str
    public_key: str
    signed_at: datetime
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "plugin_id": self.plugin_id,
            "version": self.version,
            "signature": self.signature,
            "algorithm": self.algorithm,
            "public_key": self.public_key,
            "signed_at": self.signed_at.isoformat(),
            "verified": self.verified,
        }


@dataclass
class PluginPackage:
    """Represents a plugin package"""

    id: str
    name: str
    version: str
    description: str
    author: str
    status: PluginStatus
    security_level: SecurityLevel
    download_url: str
    checksum: str
    size_bytes: int
    dependencies: List[str]
    signature: Optional[PluginSignature]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "status": self.status.value,
            "security_level": self.security_level.value,
            "download_url": self.download_url,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "dependencies": self.dependencies,
            "signature": self.signature.to_dict() if self.signature else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class PluginMarketplace:
    """
    Plugin Marketplace with Version Signing

    Provides:
    - Plugin registration and management
    - Digital signature verification
    - Security level assessment
    - Plugin approval workflow
    - Version management
    - Dependency resolution
    """

    def __init__(self, storage=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Plugin Marketplace

        Args:
            storage: Storage backend for persistence
            config: Configuration dictionary containing:
                - private_key: Private key for signing (can be omitted if using env var)
                - public_key: Public key for verification (can be omitted if using env var)
                - signature_algorithm: Signature algorithm (default: SHA256)
        """
        self.storage = storage
        self.config = config or {}
        # Read from config dict or environment variables
        self.private_key = self.config.get("private_key") or os.getenv(
            "PLUGIN_MARKETPLACE_PRIVATE_KEY", ""
        )
        self.public_key = self.config.get("public_key") or os.getenv(
            "PLUGIN_MARKETPLACE_PUBLIC_KEY", ""
        )
        self.signature_algorithm = self.config.get("signature_algorithm", "SHA256")

        self._plugins: Dict[str, PluginPackage] = {}
        self._is_initialized = False

        logger.info("Plugin Marketplace initialized")

    def initialize(self) -> bool:
        """
        Initialize plugin marketplace

        Returns:
            True if initialization successful
        """
        try:
            if self.storage:
                self._load_from_storage()

            self._is_initialized = True
            logger.info("Plugin Marketplace initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize plugin marketplace: {e}")
            return False

    def _load_from_storage(self) -> None:
        """Load plugins from storage"""
        if self.storage:
            try:
                plugins_data = self.storage.load("plugin_packages", {})
                for plugin_id, plugin_dict in plugins_data.items():
                    signature_data = plugin_dict.get("signature")
                    signature = None
                    if signature_data:
                        signature = PluginSignature(
                            plugin_id=signature_data["plugin_id"],
                            version=signature_data["version"],
                            signature=signature_data["signature"],
                            algorithm=signature_data["algorithm"],
                            public_key=signature_data["public_key"],
                            signed_at=datetime.fromisoformat(signature_data["signed_at"]),
                            verified=signature_data["verified"],
                        )

                    self._plugins[plugin_id] = PluginPackage(
                        id=plugin_dict["id"],
                        name=plugin_dict["name"],
                        version=plugin_dict["version"],
                        description=plugin_dict["description"],
                        author=plugin_dict["author"],
                        status=PluginStatus(plugin_dict["status"]),
                        security_level=SecurityLevel(plugin_dict["security_level"]),
                        download_url=plugin_dict["download_url"],
                        checksum=plugin_dict["checksum"],
                        size_bytes=plugin_dict["size_bytes"],
                        dependencies=plugin_dict["dependencies"],
                        signature=signature,
                        created_at=datetime.fromisoformat(plugin_dict["created_at"]),
                        updated_at=datetime.fromisoformat(plugin_dict["updated_at"]),
                        metadata=plugin_dict["metadata"],
                    )

                logger.info(f"Loaded {len(self._plugins)} plugins from storage")
            except Exception as e:
                logger.error(f"Failed to load plugins from storage: {e}")

    def _save_to_storage(self) -> None:
        """Save plugins to storage"""
        if self.storage:
            try:
                plugins_data = {
                    plugin_id: plugin.to_dict() for plugin_id, plugin in self._plugins.items()
                }
                self.storage.save("plugin_packages", plugins_data)
                logger.debug(f"Saved {len(self._plugins)} plugins to storage")
            except Exception as e:
                logger.error(f"Failed to save plugins to storage: {e}")

    def register_plugin(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        download_url: str,
        package_data: bytes,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PluginPackage:
        """
        Register a new plugin

        Args:
            name: Plugin name
            version: Plugin version
            description: Plugin description
            author: Plugin author
            download_url: Download URL
            package_data: Plugin package data
            dependencies: Plugin dependencies
            metadata: Plugin metadata

        Returns:
            PluginPackage object
        """
        plugin_id = f"{name}-{version}"

        # Calculate checksum
        checksum = self._calculate_checksum(package_data)

        # Create signature
        signature = self._sign_plugin(plugin_id, version, package_data)

        # Assess security level
        security_level = self._assess_security_level(package_data, metadata or {})

        plugin = PluginPackage(
            id=plugin_id,
            name=name,
            version=version,
            description=description,
            author=author,
            status=PluginStatus.PENDING,
            security_level=security_level,
            download_url=download_url,
            checksum=checksum,
            size_bytes=len(package_data),
            dependencies=dependencies or [],
            signature=signature,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {},
        )

        self._plugins[plugin_id] = plugin

        if self.storage:
            self._save_to_storage()

        logger.info(f"Registered plugin: {name} v{version}")
        return plugin

    def _calculate_checksum(self, data: bytes) -> str:
        """
        Calculate SHA256 checksum

        Args:
            data: Data to checksum

        Returns:
            Hexadecimal checksum string
        """
        return hashlib.sha256(data).hexdigest()

    def _sign_plugin(self, plugin_id: str, version: str, data: bytes) -> PluginSignature:
        """
        Sign plugin with digital signature

        Args:
            plugin_id: Plugin ID
            version: Plugin version
            data: Plugin data

        Returns:
            PluginSignature object
        """
        if not self.private_key:
            raise ValueError(
                "Private key not configured. Set PLUGIN_MARKETPLACE_PRIVATE_KEY environment variable "
                "or provide private_key in config"
            )

        # Create signature using HMAC
        message = f"{plugin_id}:{version}:{self._calculate_checksum(data)}".encode()
        signature = hmac.new(self.private_key.encode(), message, hashlib.sha256).hexdigest()

        return PluginSignature(
            plugin_id=plugin_id,
            version=version,
            signature=signature,
            algorithm=self.signature_algorithm,
            public_key=self.public_key,
            signed_at=datetime.now(),
            verified=True,
        )

    def _assess_security_level(self, data: bytes, metadata: Dict[str, Any]) -> SecurityLevel:
        """
        Assess security level of plugin

        Args:
            data: Plugin data
            metadata: Plugin metadata

        Returns:
            SecurityLevel enum
        """
        # Basic security assessment
        # In production, this would include more sophisticated analysis
        security_level = SecurityLevel.MEDIUM

        # Check for potentially dangerous operations in metadata
        if metadata.get("requires_network", False):
            security_level = SecurityLevel.HIGH

        if metadata.get("requires_filesystem", False):
            security_level = SecurityLevel.HIGH

        if metadata.get("requires_privileged", False):
            security_level = SecurityLevel.CRITICAL

        return security_level

    def verify_plugin(self, plugin_id: str, package_data: bytes) -> bool:
        """
        Verify plugin signature

        Args:
            plugin_id: Plugin ID
            package_data: Plugin package data

        Returns:
            True if signature is valid
        """
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin = self._plugins[plugin_id]

        if not plugin.signature:
            logger.error(f"Plugin has no signature: {plugin_id}")
            return False

        if not self.private_key:
            logger.error("Private key not configured for signature verification")
            return False

        # Recalculate checksum
        checksum = self._calculate_checksum(package_data)

        # Verify checksum matches
        if checksum != plugin.checksum:
            logger.error(f"Checksum mismatch for plugin: {plugin_id}")
            return False

        # Verify signature
        message = f"{plugin_id}:{plugin.version}:{checksum}".encode()
        expected_signature = hmac.new(
            self.private_key.encode(), message, hashlib.sha256
        ).hexdigest()

        if expected_signature != plugin.signature.signature:
            logger.error(f"Signature verification failed for plugin: {plugin_id}")
            return False

        plugin.signature.verified = True
        logger.info(f"Plugin signature verified: {plugin_id}")
        return True

    def approve_plugin(self, plugin_id: str) -> bool:
        """
        Approve a plugin for marketplace

        Args:
            plugin_id: Plugin ID

        Returns:
            True if successful
        """
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin = self._plugins[plugin_id]

        # Verify signature before approval
        if plugin.signature and not plugin.signature.verified:
            logger.error(f"Cannot approve plugin with unverified signature: {plugin_id}")
            return False

        plugin.status = PluginStatus.APPROVED
        plugin.updated_at = datetime.now()

        if self.storage:
            self._save_to_storage()

        logger.info(f"Approved plugin: {plugin_id}")
        return True

    def reject_plugin(self, plugin_id: str, reason: str) -> bool:
        """
        Reject a plugin from marketplace

        Args:
            plugin_id: Plugin ID
            reason: Rejection reason

        Returns:
            True if successful
        """
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin = self._plugins[plugin_id]
        plugin.status = PluginStatus.REJECTED
        plugin.metadata["rejection_reason"] = reason
        plugin.updated_at = datetime.now()

        if self.storage:
            self._save_to_storage()

        logger.info(f"Rejected plugin: {plugin_id} - {reason}")
        return True

    def deprecate_plugin(self, plugin_id: str) -> bool:
        """
        Deprecate a plugin

        Args:
            plugin_id: Plugin ID

        Returns:
            True if successful
        """
        if plugin_id not in self._plugins:
            logger.error(f"Plugin not found: {plugin_id}")
            return False

        plugin = self._plugins[plugin_id]
        plugin.status = PluginStatus.DEPRECATED
        plugin.updated_at = datetime.now()

        if self.storage:
            self._save_to_storage()

        logger.info(f"Deprecated plugin: {plugin_id}")
        return True

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin details

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin dictionary or None
        """
        if plugin_id in self._plugins:
            return self._plugins[plugin_id].to_dict()
        return None

    def list_plugins(
        self,
        status: Optional[PluginStatus] = None,
        security_level: Optional[SecurityLevel] = None,
        author: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List plugins with optional filters

        Args:
            status: Filter by status
            security_level: Filter by security level
            author: Filter by author

        Returns:
            List of plugin dictionaries
        """
        plugins = list(self._plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]
        if security_level:
            plugins = [p for p in plugins if p.security_level == security_level]
        if author:
            plugins = [p for p in plugins if p.author == author]

        return [plugin.to_dict() for plugin in plugins]

    def search_plugins(self, query: str) -> List[Dict[str, Any]]:
        """
        Search plugins by name or description

        Args:
            query: Search query

        Returns:
            List of matching plugin dictionaries
        """
        query_lower = query.lower()

        results = [
            plugin
            for plugin in self._plugins.values()
            if query_lower in plugin.name.lower() or query_lower in plugin.description.lower()
        ]

        return [plugin.to_dict() for plugin in results]

    def get_plugin_versions(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a plugin

        Args:
            name: Plugin name

        Returns:
            List of plugin version dictionaries
        """
        versions = [plugin for plugin in self._plugins.values() if plugin.name == name]

        # Sort by version (simple string comparison)
        versions.sort(key=lambda p: p.version, reverse=True)

        return [plugin.to_dict() for plugin in versions]

    def check_dependencies(self, plugin_id: str) -> Dict[str, Any]:
        """
        Check plugin dependencies

        Args:
            plugin_id: Plugin ID

        Returns:
            Dependency check result dictionary
        """
        if plugin_id not in self._plugins:
            return {"valid": False, "error": "Plugin not found"}

        plugin = self._plugins[plugin_id]

        missing = []
        available = []

        for dep in plugin.dependencies:
            if dep in self._plugins:
                available.append(dep)
            else:
                missing.append(dep)

        return {
            "valid": len(missing) == 0,
            "dependencies": plugin.dependencies,
            "available": available,
            "missing": missing,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get marketplace statistics

        Returns:
            Statistics dictionary
        """
        status_counts: Dict[str, int] = {}
        security_counts: Dict[str, int] = {}

        for plugin in self._plugins.values():
            status = plugin.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

            security = plugin.security_level.value
            security_counts[security] = security_counts.get(security, 0) + 1

        return {
            "total_plugins": len(self._plugins),
            "status_counts": status_counts,
            "security_counts": security_counts,
            "signed_plugins": sum(1 for p in self._plugins.values() if p.signature),
            "verified_plugins": sum(
                1 for p in self._plugins.values() if p.signature and p.signature.verified
            ),
        }


def create_plugin_marketplace(
    storage=None, config: Optional[Dict[str, Any]] = None
) -> Optional[PluginMarketplace]:
    """
    Factory function to create Plugin Marketplace

    Args:
        storage: Storage backend
        config: Configuration dictionary

    Returns:
        PluginMarketplace instance or None if failed
    """
    try:
        marketplace = PluginMarketplace(storage, config)
        if marketplace.initialize():
            return marketplace
        return None
    except Exception as e:
        logger.error(f"Failed to create plugin marketplace: {e}")
        return None
