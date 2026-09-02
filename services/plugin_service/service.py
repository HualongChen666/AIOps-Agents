# -*- coding: utf-8 -*-
"""Plugin Service

Business logic layer for Plugin management.
"""

import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.models import Plugin, PluginConfig, PluginExecution, PluginStatus
from core.plugin_manager import get_plugin, list_plugins as list_plugin_manager_plugins
from services.plugin_service.repository import (
    SQLAlchemyPluginConfigRepository,
    SQLAlchemyPluginExecutionRepository,
    SQLAlchemyPluginRepository,
)
from services.plugin_service.schemas import (
    PluginConfigCreate,
    PluginConfigResponse,
    PluginConfigUpdate,
    PluginCreate,
    PluginExecutionCreate,
    PluginExecutionResponse,
    PluginExecutionType,
    PluginResponse,
    PluginRunRequest,
    PluginRunResponse,
    PluginStatsResponse,
    PluginTriggerType,
    PluginUpdate,
)


class PluginService:
    """Plugin service for business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.plugin_repo = SQLAlchemyPluginRepository(db)
        self.execution_repo = SQLAlchemyPluginExecutionRepository(db)
        self.config_repo = SQLAlchemyPluginConfigRepository(db)

    def create_plugin(self, plugin_data: PluginCreate, created_by: Optional[str] = None) -> PluginResponse:
        """Create a new plugin."""
        plugin_id = str(uuid.uuid4())
        
        plugin = Plugin(
            id=plugin_id,
            name=plugin_data.name,
            version=plugin_data.version,
            description=plugin_data.description,
            author=plugin_data.author,
            plugin_type=plugin_data.plugin_type.value,
            status=PluginStatus.INACTIVE.value,
            config_schema=plugin_data.config_schema,
            default_config=plugin_data.default_config,
            dependencies=plugin_data.dependencies,
            file_path=plugin_data.file_path,
            entry_point=plugin_data.entry_point,
            plugin_metadata=plugin_data.plugin_metadata,
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        created_plugin = self.plugin_repo.create(plugin)
        return PluginResponse.from_orm(created_plugin)

    def get_plugin(self, plugin_id: str) -> Optional[PluginResponse]:
        """Get plugin by ID."""
        plugin = self.plugin_repo.get(plugin_id)
        if not plugin:
            return None
        return PluginResponse.from_orm(plugin)

    def get_plugin_by_name(self, name: str) -> Optional[PluginResponse]:
        """Get plugin by name."""
        plugin = self.plugin_repo.get_by_name(name)
        if not plugin:
            return None
        return PluginResponse.from_orm(plugin)

    def list_plugins(
        self,
        status: Optional[PluginStatus] = None,
        plugin_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginResponse]:
        """List plugins with optional filters."""
        plugins = self.plugin_repo.list(status=status, plugin_type=plugin_type, limit=limit, offset=offset)
        return [PluginResponse.from_orm(p) for p in plugins]

    def update_plugin(self, plugin_id: str, plugin_data: PluginUpdate) -> Optional[PluginResponse]:
        """Update plugin."""
        update_data = plugin_data.dict(exclude_unset=True)
        if plugin_data.status:
            update_data['status'] = plugin_data.status.value
        
        plugin = self.plugin_repo.update(plugin_id, update_data)
        if not plugin:
            return None
        return PluginResponse.from_orm(plugin)

    def delete_plugin(self, plugin_id: str) -> bool:
        """Delete plugin."""
        return self.plugin_repo.delete(plugin_id)

    def count_plugins(self, status: Optional[PluginStatus] = None) -> int:
        """Count plugins."""
        return self.plugin_repo.count(status=status)

    def run_plugin(
        self,
        name: str,
        run_request: PluginRunRequest,
        executed_by: Optional[str] = None,
    ) -> PluginRunResponse:
        """Run a plugin and record execution."""
        # Get plugin from database
        plugin = self.plugin_repo.get_by_name(name)
        if not plugin:
            # Try to get from plugin manager (for backward compatibility)
            plugin_instance = get_plugin(name)
            if not plugin_instance:
                raise ValueError(f"Plugin '{name}' not found")
            
            # Create plugin record if it doesn't exist
            plugin_id = str(uuid.uuid4())
            plugin = Plugin(
                id=plugin_id,
                name=name,
                version="1.0.0",
                description="Auto-created from plugin manager",
                plugin_type="collector",
                status=PluginStatus.ACTIVE.value,
                plugin_metadata={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                installed_at=datetime.utcnow(),
                last_loaded_at=datetime.utcnow(),
            )
            self.plugin_repo.create(plugin)
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution = PluginExecution(
            id=execution_id,
            plugin_id=plugin.id,
            plugin_name=plugin.name,
            execution_type=PluginExecutionType.COLLECT.value,
            trigger_type=PluginTriggerType.MANUAL.value,
            input_data=run_request.input_data,
            config=run_request.config,
            success=False,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            executed_by=executed_by,
            execution_metadata={},
        )
        
        try:
            # Execute plugin
            start_time = time.time()
            plugin_instance = get_plugin(name)
            
            if plugin_instance is None:
                raise ValueError(f"Plugin instance '{name}' not found")
            
            if not hasattr(plugin_instance, "collect"):
                raise AttributeError("Plugin does not implement 'collect' method")
            
            result = plugin_instance.collect()
            duration_ms = (time.time() - start_time) * 1000
            
            # Update execution record
            execution.output_data = result
            execution.success = True
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = duration_ms
            
            self.execution_repo.create(execution)
            
            return PluginRunResponse(
                plugin=name,
                result=result,
                execution_id=execution_id,
                success=True,
                duration_ms=duration_ms,
            )
        except Exception as e:
            # Update execution record with error
            execution.success = False
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = (time.time() - time.time()) * 1000
            
            self.execution_repo.create(execution)
            
            logger.error(f"Failed to run plugin '{name}': {e}")
            return PluginRunResponse(
                plugin=name,
                result=None,
                execution_id=execution_id,
                success=False,
                error_message=str(e),
            )

    def create_execution(self, execution_data: PluginExecutionCreate, executed_by: Optional[str] = None) -> PluginExecutionResponse:
        """Create a plugin execution record."""
        execution_id = str(uuid.uuid4())
        
        execution = PluginExecution(
            id=execution_id,
            plugin_id=execution_data.plugin_id,
            plugin_name=execution_data.plugin_name,
            execution_type=execution_data.execution_type.value,
            trigger_type=execution_data.trigger_type.value,
            input_data=execution_data.input_data,
            config=execution_data.config,
            success=False,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            executed_by=executed_by,
            execution_metadata={},
        )
        
        created_execution = self.execution_repo.create(execution)
        return PluginExecutionResponse.from_orm(created_execution)

    def get_execution(self, execution_id: str) -> Optional[PluginExecutionResponse]:
        """Get execution by ID."""
        execution = self.execution_repo.get(execution_id)
        if not execution:
            return None
        return PluginExecutionResponse.from_orm(execution)

    def list_executions(
        self,
        plugin_id: Optional[str] = None,
        plugin_name: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PluginExecutionResponse]:
        """List executions with optional filters."""
        executions = self.execution_repo.list(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            success=success,
            limit=limit,
            offset=offset,
        )
        return [PluginExecutionResponse.from_orm(e) for e in executions]

    def count_executions(self, plugin_id: Optional[str] = None, success: Optional[bool] = None) -> int:
        """Count executions."""
        return self.execution_repo.count(plugin_id=plugin_id, success=success)

    def create_config(self, config_data: PluginConfigCreate, updated_by: Optional[str] = None) -> PluginConfigResponse:
        """Create a plugin config."""
        config_id = str(uuid.uuid4())
        
        config = PluginConfig(
            id=config_id,
            plugin_id=config_data.plugin_id,
            plugin_name=config_data.plugin_name,
            config_data=config_data.config_data,
            config_version=1,
            is_active=True,
            description=config_data.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            updated_by=updated_by,
            config_metadata={},
        )
        
        created_config = self.config_repo.create(config)
        return PluginConfigResponse.from_orm(created_config)

    def get_config(self, config_id: str) -> Optional[PluginConfigResponse]:
        """Get config by ID."""
        config = self.config_repo.get(config_id)
        if not config:
            return None
        return PluginConfigResponse.from_orm(config)

    def get_config_by_plugin_id(self, plugin_id: str) -> Optional[PluginConfigResponse]:
        """Get config by plugin ID."""
        config = self.config_repo.get_by_plugin_id(plugin_id)
        if not config:
            return None
        return PluginConfigResponse.from_orm(config)

    def update_config(self, config_id: str, config_data: PluginConfigUpdate, updated_by: Optional[str] = None) -> Optional[PluginConfigResponse]:
        """Update config."""
        update_data = config_data.dict(exclude_unset=True)
        if updated_by:
            update_data['updated_by'] = updated_by
        
        config = self.config_repo.update(config_id, update_data)
        if not config:
            return None
        return PluginConfigResponse.from_orm(config)

    def delete_config(self, config_id: str) -> bool:
        """Delete config."""
        return self.config_repo.delete(config_id)

    def get_stats(self) -> PluginStatsResponse:
        """Get plugin statistics."""
        total_plugins = self.plugin_repo.count()
        active_plugins = self.plugin_repo.count(status=PluginStatus.ACTIVE)
        inactive_plugins = self.plugin_repo.count(status=PluginStatus.INACTIVE)
        error_plugins = self.plugin_repo.count(status=PluginStatus.ERROR)
        
        total_executions = self.execution_repo.count()
        successful_executions = self.execution_repo.count(success=True)
        failed_executions = self.execution_repo.count(success=False)
        
        return PluginStatsResponse(
            total_plugins=total_plugins,
            active_plugins=active_plugins,
            inactive_plugins=inactive_plugins,
            error_plugins=error_plugins,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
        )
