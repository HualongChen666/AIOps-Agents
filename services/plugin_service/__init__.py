# -*- coding: utf-8 -*-
"""Plugin Service Package

Provides plugin management functionality including:
- Plugin CRUD operations
- Plugin execution tracking
- Plugin configuration management
"""

from services.plugin_service.repository import (
    PluginConfigRepository,
    PluginExecutionRepository,
    PluginRepository,
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
    PluginExecutionListResponse,
    PluginExecutionResponse,
    PluginExecutionType,
    PluginListResponse,
    PluginResponse,
    PluginRunRequest,
    PluginRunResponse,
    PluginStatsResponse,
    PluginStatus,
    PluginTriggerType,
    PluginType,
    PluginUpdate,
)
from services.plugin_service.service import PluginService

__all__ = [
    # Schemas
    "PluginStatus",
    "PluginType",
    "PluginExecutionType",
    "PluginTriggerType",
    "PluginCreate",
    "PluginUpdate",
    "PluginResponse",
    "PluginListResponse",
    "PluginRunRequest",
    "PluginRunResponse",
    "PluginExecutionCreate",
    "PluginExecutionResponse",
    "PluginExecutionListResponse",
    "PluginConfigCreate",
    "PluginConfigUpdate",
    "PluginConfigResponse",
    "PluginStatsResponse",
    # Repository
    "PluginRepository",
    "PluginExecutionRepository",
    "PluginConfigRepository",
    "SQLAlchemyPluginRepository",
    "SQLAlchemyPluginExecutionRepository",
    "SQLAlchemyPluginConfigRepository",
    # Service
    "PluginService",
]
