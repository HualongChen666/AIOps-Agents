# -*- coding: utf-8 -*-
"""Plugin Service Repository

Data access layer for Plugin management.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.models import Plugin, PluginConfig, PluginExecution, PluginStatus


class PluginRepository(ABC):
    """Abstract plugin repository."""

    @abstractmethod
    def create(self, plugin: Plugin) -> Plugin:
        """Create a new plugin."""
        ...

    @abstractmethod
    def get(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID."""
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        ...

    @abstractmethod
    def list(
        self,
        status: Optional[PluginStatus] = None,
        plugin_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Plugin]:
        """List plugins with optional filters."""
        ...

    @abstractmethod
    def update(self, plugin_id: str, data: Dict[str, Any]) -> Optional[Plugin]:
        """Update plugin."""
        ...

    @abstractmethod
    def delete(self, plugin_id: str) -> bool:
        """Delete plugin."""
        ...

    @abstractmethod
    def count(self, status: Optional[PluginStatus] = None) -> int:
        """Count plugins."""
        ...


class SQLAlchemyPluginRepository(PluginRepository):
    """SQLAlchemy implementation of plugin repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, plugin: Plugin) -> Plugin:
        """Create a new plugin."""
        try:
            self.db.add(plugin)
            self.db.commit()
            self.db.refresh(plugin)
            logger.info(f"Created plugin: {plugin.name}")
            return plugin
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create plugin: {e}")
            raise

    def get(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID."""
        return self.db.query(Plugin).filter(Plugin.id == plugin_id).first()

    def get_by_name(self, name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        return self.db.query(Plugin).filter(Plugin.name == name).first()

    def list(
        self,
        status: Optional[PluginStatus] = None,
        plugin_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Plugin]:
        """List plugins with optional filters."""
        query = self.db.query(Plugin)

        if status:
            query = query.filter(Plugin.status == status.value)
        if plugin_type:
            query = query.filter(Plugin.plugin_type == plugin_type)

        return query.order_by(Plugin.created_at.desc()).offset(offset).limit(limit).all()

    def update(self, plugin_id: str, data: Dict[str, Any]) -> Optional[Plugin]:
        """Update plugin."""
        plugin = self.get(plugin_id)
        if not plugin:
            return None

        try:
            for key, value in data.items():
                if hasattr(plugin, key):
                    setattr(plugin, key, value)
            
            plugin.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(plugin)
            logger.info(f"Updated plugin: {plugin.name}")
            return plugin
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update plugin: {e}")
            raise

    def delete(self, plugin_id: str) -> bool:
        """Delete plugin."""
        plugin = self.get(plugin_id)
        if not plugin:
            return False

        try:
            self.db.delete(plugin)
            self.db.commit()
            logger.info(f"Deleted plugin: {plugin.name}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete plugin: {e}")
            raise

    def count(self, status: Optional[PluginStatus] = None) -> int:
        """Count plugins."""
        query = self.db.query(Plugin)
        if status:
            query = query.filter(Plugin.status == status.value)
        return query.count()


class PluginExecutionRepository(ABC):
    """Abstract plugin execution repository."""

    @abstractmethod
    def create(self, execution: PluginExecution) -> PluginExecution:
        """Create a new plugin execution."""
        ...

    @abstractmethod
    def get(self, execution_id: str) -> Optional[PluginExecution]:
        """Get execution by ID."""
        ...

    @abstractmethod
    def list(
        self,
        plugin_id: Optional[str] = None,
        plugin_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginExecution]:
        """List executions with optional filters."""
        ...

    @abstractmethod
    def update(self, execution_id: str, data: Dict[str, Any]) -> Optional[PluginExecution]:
        """Update execution."""
        ...

    @abstractmethod
    def count(self, plugin_id: Optional[str] = None, success: Optional[bool] = None) -> int:
        """Count executions."""
        ...


class SQLAlchemyPluginExecutionRepository(PluginExecutionRepository):
    """SQLAlchemy implementation of plugin execution repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, execution: PluginExecution) -> PluginExecution:
        """Create a new plugin execution."""
        try:
            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)
            logger.info(f"Created plugin execution: {execution.id}")
            return execution
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create plugin execution: {e}")
            raise

    def get(self, execution_id: str) -> Optional[PluginExecution]:
        """Get execution by ID."""
        return self.db.query(PluginExecution).filter(PluginExecution.id == execution_id).first()

    def list(
        self,
        plugin_id: Optional[str] = None,
        plugin_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginExecution]:
        """List executions with optional filters."""
        query = self.db.query(PluginExecution)

        if plugin_id:
            query = query.filter(PluginExecution.plugin_id == plugin_id)
        if plugin_name:
            query = query.filter(PluginExecution.plugin_name == plugin_name)
        if success is not None:
            query = query.filter(PluginExecution.success == success)

        return query.order_by(PluginExecution.started_at.desc()).offset(offset).limit(limit).all()

    def update(self, execution_id: str, data: Dict[str, Any]) -> Optional[PluginExecution]:
        """Update execution."""
        execution = self.get(execution_id)
        if not execution:
            return None

        try:
            for key, value in data.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)
            
            self.db.commit()
            self.db.refresh(execution)
            logger.info(f"Updated plugin execution: {execution.id}")
            return execution
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update plugin execution: {e}")
            raise

    def count(self, plugin_id: Optional[str] = None, success: Optional[bool] = None) -> int:
        """Count executions."""
        query = self.db.query(PluginExecution)
        if plugin_id:
            query = query.filter(PluginExecution.plugin_id == plugin_id)
        if success is not None:
            query = query.filter(PluginExecution.success == success)
        return query.count()


class PluginConfigRepository(ABC):
    """Abstract plugin config repository."""

    @abstractmethod
    def create(self, config: PluginConfig) -> PluginConfig:
        """Create a new plugin config."""
        ...

    @abstractmethod
    def get(self, config_id: str) -> Optional[PluginConfig]:
        """Get config by ID."""
        ...

    @abstractmethod
    def get_by_plugin_id(self, plugin_id: str) -> Optional[PluginConfig]:
        """Get config by plugin ID."""
        ...

    @abstractmethod
    def list(
        self,
        plugin_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginConfig]:
        """List configs with optional filters."""
        ...

    @abstractmethod
    def update(self, config_id: str, data: Dict[str, Any]) -> Optional[PluginConfig]:
        """Update config."""
        ...

    @abstractmethod
    def delete(self, config_id: str) -> bool:
        """Delete config."""
        ...


class SQLAlchemyPluginConfigRepository(PluginConfigRepository):
    """SQLAlchemy implementation of plugin config repository."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, config: PluginConfig) -> PluginConfig:
        """Create a new plugin config."""
        try:
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Created plugin config: {config.id}")
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create plugin config: {e}")
            raise

    def get(self, config_id: str) -> Optional[PluginConfig]:
        """Get config by ID."""
        return self.db.query(PluginConfig).filter(PluginConfig.id == config_id).first()

    def get_by_plugin_id(self, plugin_id: str) -> Optional[PluginConfig]:
        """Get config by plugin ID."""
        return self.db.query(PluginConfig).filter(PluginConfig.plugin_id == plugin_id).first()

    def list(
        self,
        plugin_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginConfig]:
        """List configs with optional filters."""
        query = self.db.query(PluginConfig)

        if plugin_id:
            query = query.filter(PluginConfig.plugin_id == plugin_id)
        if is_active is not None:
            query = query.filter(PluginConfig.is_active == is_active)

        return query.order_by(PluginConfig.created_at.desc()).offset(offset).limit(limit).all()

    def update(self, config_id: str, data: Dict[str, Any]) -> Optional[PluginConfig]:
        """Update config."""
        config = self.get(config_id)
        if not config:
            return None

        try:
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            config.config_version += 1
            self.db.commit()
            self.db.refresh(config)
            logger.info(f"Updated plugin config: {config.id}")
            return config
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update plugin config: {e}")
            raise

    def delete(self, config_id: str) -> bool:
        """Delete config."""
        config = self.get(config_id)
        if not config:
            return False

        try:
            self.db.delete(config)
            self.db.commit()
            logger.info(f"Deleted plugin config: {config.id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete plugin config: {e}")
            raise
