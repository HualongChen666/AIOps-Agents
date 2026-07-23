# -*- coding: utf-8 -*-
"""
Plugin Manager Adapter for AIOps Platform

This module provides a compatibility layer for the plugin_router, adapting the
plugin_system.PluginManager to match the expected interface.
"""

from typing import Any, List, Optional

from core.plugin_system import PluginManager, create_plugin_manager

# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> Optional[PluginManager]:
    """Get or create the global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = create_plugin_manager()
    return _plugin_manager


def load_all() -> None:
    """Load all plugins from configured directories"""
    manager = get_plugin_manager()
    if manager:
        # Try to discover plugins if method exists
        if hasattr(manager, "discover_plugins"):
            manager.discover_plugins()
        # Load all plugins
        if hasattr(manager, "load_all_plugins"):
            manager.load_all_plugins()


def list_plugins() -> List[str]:
    """List all registered plugin names"""
    manager = get_plugin_manager()
    if manager:
        plugins = manager.list_plugins(plugin_type=None)
        return [plugin["metadata"]["name"] for plugin in plugins]
    return []


def get_plugin(name: str) -> Optional[Any]:
    """Get a plugin by name"""
    manager = get_plugin_manager()
    if manager:
        return manager.get_plugin(name)
    return None


__all__ = ["load_all", "list_plugins", "get_plugin", "get_plugin_manager"]
