# -*- coding: utf-8 -*-
"""
Plugin System Manager
Enterprise-grade plugin system architecture and lifecycle management
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class PluginStatus(Enum):
    """Plugin status"""

    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"
    UNLOADED = "unloaded"


class PluginType(Enum):
    """Plugin type"""

    MONITORING = "monitoring"
    INTEGRATION = "integration"
    AI = "ai"
    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    """Plugin metadata"""

    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    api_version: str = "1.0"
    min_system_version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginInterface:
    """Plugin interface specification"""

    interface_id: str
    interface_name: str
    methods: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    configuration: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginDependency:
    """Plugin dependency"""

    plugin_id: str
    version_constraint: str
    optional: bool = False


class PluginSystemManager:
    """
    Enterprise-grade plugin system manager
    Provides plugin architecture, interface specifications, and lifecycle management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin system manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Plugin registry
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}

        # Interface specifications
        self.interfaces: Dict[str, PluginInterface] = {}

        # Plugin lifecycle
        self.plugin_status: Dict[str, PluginStatus] = {}

        # Dependency graph
        self.dependency_graph: Dict[str, List[PluginDependency]] = {}

        # Configuration
        self.system_version = self.config.get("system_version", "1.0")
        self.plugin_directory = self.config.get("plugin_directory", "plugins")

        # Statistics
        self.total_plugins_registered = 0
        self.total_plugins_enabled = 0

        logger.info("Plugin system manager initialized")

    def define_plugin_interface(
        self,
        interface_id: str,
        interface_name: str,
        methods: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        configuration: Optional[Dict[str, Any]] = None,
    ) -> PluginInterface:
        """
        Define plugin interface specification

        Args:
            interface_id: Interface ID
            interface_name: Interface name
            methods: Interface methods
            events: Interface events
            configuration: Interface configuration

        Returns:
            Plugin interface
        """
        interface = PluginInterface(
            interface_id=interface_id,
            interface_name=interface_name,
            methods=methods,
            events=events,
            configuration=configuration or {},
            metadata={"created_at": datetime.now(timezone.utc).isoformat()},
        )

        self.interfaces[interface_id] = interface

        logger.info(f"Defined plugin interface: {interface_id}")

        return interface

    def generate_plugin_interface_spec(self, interface_type: str) -> Dict[str, Any]:
        """
        Generate plugin interface specification for a given type

        Args:
            interface_type: Interface type (monitoring, integration, ai)

        Returns:
            Interface specification
        """
        if interface_type == "monitoring":
            return {
                "interface_type": "monitoring",
                "required_methods": [
                    {
                        "name": "initialize",
                        "parameters": [{"name": "config", "type": "dict"}],
                        "returns": "bool",
                    },
                    {
                        "name": "collect_metrics",
                        "parameters": [{"name": "target", "type": "str"}],
                        "returns": "dict",
                    },
                    {"name": "cleanup", "parameters": [], "returns": "bool"},
                ],
                "required_events": [
                    {"name": "metric_collected", "data": "metric_data"},
                    {"name": "error_occurred", "data": "error_info"},
                ],
                "configuration_schema": {
                    "interval": {"type": "int", "default": 60},
                    "timeout": {"type": "int", "default": 30},
                    "retry_count": {"type": "int", "default": 3},
                },
            }
        elif interface_type == "integration":
            return {
                "interface_type": "integration",
                "required_methods": [
                    {
                        "name": "connect",
                        "parameters": [{"name": "credentials", "type": "dict"}],
                        "returns": "bool",
                    },
                    {
                        "name": "execute_action",
                        "parameters": [
                            {"name": "action", "type": "str"},
                            {"name": "params", "type": "dict"},
                        ],
                        "returns": "dict",
                    },
                    {"name": "disconnect", "parameters": [], "returns": "bool"},
                ],
                "required_events": [
                    {"name": "action_completed", "data": "action_result"},
                    {"name": "action_failed", "data": "error_info"},
                ],
                "configuration_schema": {
                    "endpoint": {"type": "str", "required": True},
                    "auth_method": {"type": "str", "default": "token"},
                    "timeout": {"type": "int", "default": 30},
                },
            }
        elif interface_type == "ai":
            return {
                "interface_type": "ai",
                "required_methods": [
                    {
                        "name": "initialize_model",
                        "parameters": [{"name": "model_config", "type": "dict"}],
                        "returns": "bool",
                    },
                    {
                        "name": "process_input",
                        "parameters": [{"name": "input_data", "type": "dict"}],
                        "returns": "dict",
                    },
                    {"name": "get_model_info", "parameters": [], "returns": "dict"},
                ],
                "required_events": [
                    {"name": "model_loaded", "data": "model_info"},
                    {"name": "processing_completed", "data": "processing_result"},
                ],
                "configuration_schema": {
                    "model_type": {"type": "str", "required": True},
                    "model_path": {"type": "str", "required": True},
                    "max_tokens": {"type": "int", "default": 2048},
                },
            }
        else:
            return {
                "interface_type": "custom",
                "required_methods": [],
                "required_events": [],
                "configuration_schema": {},
            }

    def register_plugin(self, plugin_id: str, metadata: PluginMetadata) -> bool:
        """
        Register plugin metadata

        Args:
            plugin_id: Plugin ID
            metadata: Plugin metadata

        Returns:
            True if registered, False otherwise
        """
        # Validate metadata
        if not self._validate_metadata(metadata):
            logger.error(f"Invalid metadata for plugin: {plugin_id}")
            return False

        # Check for duplicates
        if plugin_id in self.plugin_metadata:
            logger.warning(f"Plugin {plugin_id} already registered")
            return False

        # Register plugin
        self.plugin_metadata[plugin_id] = metadata
        self.plugin_status[plugin_id] = PluginStatus.INSTALLED

        # Build dependency graph
        self.dependency_graph[plugin_id] = [
            PluginDependency(dep_id, version)
            for dep_id, version in [
                (
                    dep.split(">=")[0].strip(),
                    dep.split(">=")[1].strip() if ">=" in dep else ">=0.0.0",
                )
                for dep in metadata.dependencies
            ]
        ]

        self.total_plugins_registered += 1

        logger.info(f"Registered plugin: {plugin_id}")

        return True

    def _validate_metadata(self, metadata: PluginMetadata) -> bool:
        """
        Validate plugin metadata

        Args:
            metadata: Plugin metadata

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not all([metadata.plugin_id, metadata.name, metadata.version, metadata.author]):
            return False

        # Check version compatibility
        if not self._check_version_compatibility(metadata.min_system_version, self.system_version):
            return False

        return True

    def _check_version_compatibility(self, required_version: str, system_version: str) -> bool:
        """
        Check version compatibility

        Args:
            required_version: Required version
            system_version: System version

        Returns:
            True if compatible, False otherwise
        """
        # Simple version comparison (can be enhanced)
        required_parts = required_version.split(".")
        system_parts = system_version.split(".")

        for i in range(min(len(required_parts), len(system_parts))):
            try:
                required = int(required_parts[i])
                system = int(system_parts[i])
                if system < required:
                    return False
            except (ValueError, IndexError):
                pass

        return True

    def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable plugin

        Args:
            plugin_id: Plugin ID

        Returns:
            True if enabled, False otherwise
        """
        if plugin_id not in self.plugin_metadata:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        # Check dependencies
        if not self._check_dependencies(plugin_id):
            logger.error(f"Dependencies not satisfied for plugin: {plugin_id}")
            return False

        self.plugin_status[plugin_id] = PluginStatus.ENABLED
        self.total_plugins_enabled += 1

        logger.info(f"Enabled plugin: {plugin_id}")

        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable plugin

        Args:
            plugin_id: Plugin ID

        Returns:
            True if disabled, False otherwise
        """
        if plugin_id not in self.plugin_metadata:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        if self.plugin_status[plugin_id] == PluginStatus.ENABLED:
            self.total_plugins_enabled -= 1

        self.plugin_status[plugin_id] = PluginStatus.DISABLED

        logger.info(f"Disabled plugin: {plugin_id}")

        return True

    def _check_dependencies(self, plugin_id: str) -> bool:
        """
        Check if plugin dependencies are satisfied

        Args:
            plugin_id: Plugin ID

        Returns:
            True if dependencies satisfied, False otherwise
        """
        dependencies = self.dependency_graph.get(plugin_id, [])

        for dep in dependencies:
            if dep.plugin_id not in self.plugin_metadata:
                if not dep.optional:
                    logger.error(f"Required dependency not found: {dep.plugin_id}")
                    return False
            else:
                dep_status = self.plugin_status.get(dep.plugin_id)
                if dep_status != PluginStatus.ENABLED:
                    if not dep.optional:
                        logger.error(f"Required dependency not enabled: {dep.plugin_id}")
                        return False

        return True

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin information

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin information or None
        """
        if plugin_id not in self.plugin_metadata:
            return None

        metadata = self.plugin_metadata[plugin_id]
        status = self.plugin_status.get(plugin_id, PluginStatus.UNLOADED)

        return {
            "plugin_id": metadata.plugin_id,
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "author": metadata.author,
            "plugin_type": metadata.plugin_type.value,
            "status": status.value,
            "dependencies": metadata.dependencies,
            "api_version": metadata.api_version,
        }

    def list_plugins(
        self, plugin_type: Optional[PluginType] = None, status: Optional[PluginStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        List plugins

        Args:
            plugin_type: Filter by plugin type
            status: Filter by status

        Returns:
            List of plugin information
        """
        plugins = []

        for plugin_id, metadata in self.plugin_metadata.items():
            plugin_status = self.plugin_status.get(plugin_id, PluginStatus.UNLOADED)

            # Apply filters
            if plugin_type and metadata.plugin_type != plugin_type:
                continue
            if status and plugin_status != status:
                continue

            plugin_info = self.get_plugin_info(plugin_id)
            if plugin_info is not None:
                plugins.append(plugin_info)

        return plugins

    def get_system_summary(self) -> Dict[str, Any]:
        """
        Get plugin system summary

        Returns:
            System summary
        """
        return {
            "total_plugins_registered": self.total_plugins_registered,
            "total_plugins_enabled": self.total_plugins_enabled,
            "total_interfaces_defined": len(self.interfaces),
            "system_version": self.system_version,
            "plugins_by_type": {
                plugin_type.value: len(
                    [p for p in self.plugin_metadata.values() if p.plugin_type == plugin_type]
                )
                for plugin_type in PluginType
            },
            "plugins_by_status": {
                status.value: len([s for s in self.plugin_status.values() if s == status])
                for status in PluginStatus
            },
        }


# Global instance
_plugin_system_manager: Optional[PluginSystemManager] = None


def get_plugin_system_manager() -> PluginSystemManager:
    """
    Get the global plugin system manager instance

    Returns:
        PluginSystemManager instance
    """
    global _plugin_system_manager
    if _plugin_system_manager is None:
        _plugin_system_manager = PluginSystemManager()
    return _plugin_system_manager
