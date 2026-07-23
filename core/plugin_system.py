# -*- coding: utf-8 -*-
"""
Custom Event SDK Plugin System for AIOps Platform
Provides a plugin framework for custom event collectors and processors
"""

import importlib
import inspect
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Plugin type enumeration"""

    COLLECTOR = "collector"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    STORAGE = "storage"
    NOTIFIER = "notifier"


class PluginStatus(Enum):
    """Plugin status enumeration"""

    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Represents plugin metadata"""

    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str]
    config_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "dependencies": self.dependencies,
            "config_schema": self.config_schema,
        }


class BasePlugin(ABC):
    """
    Abstract base class for all plugins

    All plugins must implement the initialize, execute, and close methods.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base plugin

        Args:
            config: Plugin configuration
        """
        self.config = config or {}
        self._is_initialized = False
        self._is_running = False

        logger.info("BasePlugin initialized")

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata

        Returns:
            PluginMetadata object
        """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin logic

        Args:
            data: Input data

        Returns:
            Output data
        """

    @abstractmethod
    def close(self) -> None:
        """Close the plugin and release resources"""

    def validate_config(self, required_keys: List[str]) -> bool:
        """
        Validate configuration has required keys

        Args:
            required_keys: List of required configuration keys

        Returns:
            True if configuration is valid
        """
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error(f"Missing required config keys: {missing_keys}")
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get plugin status

        Returns:
            Status dictionary
        """
        return {
            "initialized": self._is_initialized,
            "running": self._is_running,
            "config": self.config,
        }

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


@dataclass
class PluginInfo:
    """Represents loaded plugin information"""

    plugin_class: Type[BasePlugin]
    metadata: PluginMetadata
    instance: Optional[BasePlugin] = None
    status: PluginStatus = PluginStatus.UNLOADED
    error: Optional[str] = None
    loaded_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "status": self.status.value,
            "error": self.error,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
        }


class PluginManager:
    """
    Plugin Manager

    Manages plugin discovery, loading, execution, and lifecycle.
    Supports dynamic plugin loading from directories and Python packages.
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Initialize Plugin Manager

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or []
        self._plugins: Dict[str, PluginInfo] = {}
        self._is_initialized = False

        logger.info("Plugin Manager initialized")

    def initialize(self) -> bool:
        """
        Initialize plugin manager

        Returns:
            True if initialization successful
        """
        try:
            # Add plugin directories to Python path
            for plugin_dir in self.plugin_dirs:
                if plugin_dir not in sys.path:
                    sys.path.insert(0, plugin_dir)

            # Discover plugins
            self._discover_plugins()

            self._is_initialized = True
            logger.info("Plugin Manager initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize plugin manager: {e}")
            return False

    def _discover_plugins(self) -> None:
        """Discover plugins from plugin directories"""
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue

            # Walk through directory structure
            for root, dirs, files in os.walk(plugin_dir):
                for file in files:
                    if file.endswith(".py") and not file.startswith("_"):
                        module_path = os.path.join(root, file)
                        self._load_plugin_from_file(module_path)

    def _load_plugin_from_file(self, file_path: str) -> None:
        """
        Load plugin from Python file

        Args:
            file_path: Path to Python file
        """
        try:
            # Convert file path to module name
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            dir_name = os.path.dirname(file_path)

            # Add directory to path if not already there
            if dir_name not in sys.path:
                sys.path.insert(0, dir_name)

            # Import module
            module = importlib.import_module(module_name)

            # Find plugin classes
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj != BasePlugin:

                    # Instantiate to get metadata
                    try:
                        instance = obj()
                        metadata = instance.get_metadata()

                        plugin_info = PluginInfo(
                            plugin_class=obj,
                            metadata=metadata,
                            status=PluginStatus.LOADED,
                            loaded_at=datetime.now(),
                        )

                        self._plugins[metadata.name] = plugin_info
                        logger.info(f"Loaded plugin: {metadata.name} v{metadata.version}")

                    except Exception as e:
                        logger.error(f"Failed to instantiate plugin {name}: {e}")

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")

    def register_plugin(self, plugin_class: Type[BasePlugin]) -> bool:
        """
        Register a plugin class

        Args:
            plugin_class: Plugin class to register

        Returns:
            True if successful
        """
        try:
            # Instantiate to get metadata
            instance = plugin_class()
            metadata = instance.get_metadata()

            if metadata.name in self._plugins:
                logger.warning(f"Plugin already registered: {metadata.name}")
                return False

            plugin_info = PluginInfo(
                plugin_class=plugin_class,
                metadata=metadata,
                status=PluginStatus.LOADED,
                loaded_at=datetime.now(),
            )

            self._plugins[metadata.name] = plugin_info
            logger.info(f"Registered plugin: {metadata.name} v{metadata.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False

    def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Load and initialize a plugin

        Args:
            name: Plugin name
            config: Plugin configuration

        Returns:
            True if successful
        """
        if name not in self._plugins:
            logger.error(f"Plugin not found: {name}")
            return False

        plugin_info = self._plugins[name]

        if plugin_info.status == PluginStatus.ERROR:
            logger.error(f"Plugin in error state: {name}")
            return False

        try:
            # Create instance
            instance = plugin_info.plugin_class(config)

            # Initialize
            if instance.initialize():
                plugin_info.instance = instance
                plugin_info.status = PluginStatus.LOADED
                plugin_info.loaded_at = datetime.now()
                logger.info(f"Loaded plugin instance: {name}")
                return True
            else:
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error = "Initialization failed"
                logger.error(f"Failed to initialize plugin: {name}")
                return False

        except Exception as e:
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error = str(e)
            logger.error(f"Failed to load plugin {name}: {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """
        Unload a plugin

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        if name not in self._plugins:
            logger.error(f"Plugin not found: {name}")
            return False

        plugin_info = self._plugins[name]

        if plugin_info.instance:
            try:
                plugin_info.instance.close()
            except Exception as e:
                logger.error(f"Error closing plugin {name}: {e}")

        plugin_info.instance = None
        plugin_info.status = PluginStatus.UNLOADED
        logger.info(f"Unloaded plugin: {name}")
        return True

    async def execute_plugin(self, name: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a plugin

        Args:
            name: Plugin name
            data: Input data

        Returns:
            Output data or None if failed
        """
        if name not in self._plugins:
            logger.error(f"Plugin not found: {name}")
            return None

        plugin_info = self._plugins[name]

        if not plugin_info.instance:
            logger.error(f"Plugin not loaded: {name}")
            return None

        if plugin_info.status != PluginStatus.LOADED:
            logger.error(f"Plugin not in loaded state: {name}")
            return None

        try:
            return await plugin_info.instance.execute(data)
        except Exception as e:
            logger.error(f"Error executing plugin {name}: {e}")
            return None

    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin information

        Args:
            name: Plugin name

        Returns:
            Plugin information dictionary or None
        """
        if name in self._plugins:
            return self._plugins[name].to_dict()
        return None

    def list_plugins(self, plugin_type: Optional[PluginType] = None) -> List[Dict[str, Any]]:
        """
        List all plugins

        Args:
            plugin_type: Optional plugin type filter

        Returns:
            List of plugin information dictionaries
        """
        plugins = list(self._plugins.values())

        if plugin_type:
            plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]

        return [plugin.to_dict() for plugin in plugins]

    def get_plugin_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get plugin status

        Args:
            name: Plugin name

        Returns:
            Status dictionary or None
        """
        if name in self._plugins:
            plugin = self._plugins[name]
            if plugin.instance is not None:
                return plugin.instance.get_status()
        return None

    def reload_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Reload a plugin

        Args:
            name: Plugin name
            config: New configuration

        Returns:
            True if successful
        """
        # Unload first
        if not self.unload_plugin(name):
            return False

        # Reload
        return self.load_plugin(name, config)

    def close(self) -> None:
        """Close plugin manager and unload all plugins"""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

        logger.info("Plugin Manager closed")


def create_plugin_manager(plugin_dirs: Optional[List[str]] = None) -> Optional[PluginManager]:
    """
    Factory function to create Plugin Manager

    Args:
        plugin_dirs: List of plugin directories

    Returns:
        PluginManager instance or None if failed
    """
    try:
        manager = PluginManager(plugin_dirs)
        if manager.initialize():
            return manager
        return None
    except Exception as e:
        logger.error(f"Failed to create plugin manager: {e}")
        return None


PluginSystem = PluginManager
