# -*- coding: utf-8 -*-
"""Plugin Service Schemas

Pydantic schemas for Plugin API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class PluginStatus(str, Enum):
    """插件状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"


class PluginType(str, Enum):
    """插件类型枚举"""

    COLLECTOR = "collector"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    STORAGE = "storage"
    NOTIFIER = "notifier"


class PluginBase(BaseModel):
    """插件基础模型"""

    name: str = Field(..., description="插件名称", min_length=1, max_length=200)
    version: str = Field(..., description="插件版本", min_length=1, max_length=50)
    description: Optional[str] = Field(None, description="插件描述")
    author: Optional[str] = Field(None, description="插件作者", max_length=200)
    plugin_type: PluginType = Field(..., description="插件类型")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="配置模式定义")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")
    dependencies: Optional[List[str]] = Field(None, description="依赖的其他插件")
    file_path: Optional[str] = Field(None, description="插件文件路径", max_length=500)
    entry_point: Optional[str] = Field(None, description="入口函数", max_length=200)
    plugin_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class PluginCreate(PluginBase):
    """创建插件请求模型"""

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Plugin name cannot be empty")
        return v.strip()

    @validator('version')
    def validate_version(cls, v):
        if not v or not v.strip():
            raise ValueError("Plugin version cannot be empty")
        return v.strip()


class PluginUpdate(BaseModel):
    """更新插件请求模型"""

    version: Optional[str] = Field(None, description="插件版本", max_length=50)
    description: Optional[str] = Field(None, description="插件描述")
    author: Optional[str] = Field(None, description="插件作者", max_length=200)
    status: Optional[PluginStatus] = Field(None, description="插件状态")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="配置模式定义")
    default_config: Optional[Dict[str, Any]] = Field(None, description="默认配置")
    dependencies: Optional[List[str]] = Field(None, description="依赖的其他插件")
    file_path: Optional[str] = Field(None, description="插件文件路径", max_length=500)
    entry_point: Optional[str] = Field(None, description="入口函数", max_length=200)
    plugin_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class PluginResponse(PluginBase):
    """插件响应模型"""

    id: str = Field(..., description="插件ID")
    status: PluginStatus = Field(..., description="插件状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    installed_at: Optional[datetime] = Field(None, description="安装时间")
    last_loaded_at: Optional[datetime] = Field(None, description="最后加载时间")
    created_by: Optional[str] = Field(None, description="创建者")

    class Config:
        from_attributes = True


class PluginListResponse(BaseModel):
    """插件列表响应模型"""

    total: int = Field(..., description="总数")
    plugins: List[PluginResponse] = Field(..., description="插件列表")


class PluginExecutionType(str, Enum):
    """插件执行类型枚举"""

    COLLECT = "collect"
    EXECUTE = "execute"
    ANALYZE = "analyze"


class PluginTriggerType(str, Enum):
    """插件触发类型枚举"""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"


class PluginExecutionCreate(BaseModel):
    """创建插件执行请求模型"""

    plugin_id: str = Field(..., description="插件ID")
    plugin_name: str = Field(..., description="插件名称")
    execution_type: PluginExecutionType = Field(..., description="执行类型")
    trigger_type: PluginTriggerType = Field(..., description="触发类型")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    config: Optional[Dict[str, Any]] = Field(None, description="执行配置")


class PluginExecutionResponse(BaseModel):
    """插件执行响应模型"""

    id: str = Field(..., description="执行ID")
    plugin_id: str = Field(..., description="插件ID")
    plugin_name: str = Field(..., description="插件名称")
    execution_type: PluginExecutionType = Field(..., description="执行类型")
    trigger_type: PluginTriggerType = Field(..., description="触发类型")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误消息")
    error_traceback: Optional[str] = Field(None, description="错误堆栈")
    duration_ms: Optional[float] = Field(None, description="执行时长(毫秒)")
    memory_usage_mb: Optional[float] = Field(None, description="内存使用(MB)")
    started_at: datetime = Field(..., description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")
    executed_by: Optional[str] = Field(None, description="执行者")
    execution_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

    class Config:
        from_attributes = True


class PluginExecutionListResponse(BaseModel):
    """插件执行列表响应模型"""

    total: int = Field(..., description="总数")
    executions: List[PluginExecutionResponse] = Field(..., description="执行列表")


class PluginConfigCreate(BaseModel):
    """创建插件配置请求模型"""

    plugin_id: str = Field(..., description="插件ID")
    plugin_name: str = Field(..., description="插件名称")
    config_data: Dict[str, Any] = Field(..., description="配置数据")
    description: Optional[str] = Field(None, description="配置描述")


class PluginConfigUpdate(BaseModel):
    """更新插件配置请求模型"""

    config_data: Optional[Dict[str, Any]] = Field(None, description="配置数据")
    is_active: Optional[bool] = Field(None, description="是否激活")
    description: Optional[str] = Field(None, description="配置描述")


class PluginConfigResponse(BaseModel):
    """插件配置响应模型"""

    id: str = Field(..., description="配置ID")
    plugin_id: str = Field(..., description="插件ID")
    plugin_name: str = Field(..., description="插件名称")
    config_data: Dict[str, Any] = Field(..., description="配置数据")
    config_version: int = Field(..., description="配置版本")
    is_active: bool = Field(..., description="是否激活")
    description: Optional[str] = Field(None, description="配置描述")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    updated_by: Optional[str] = Field(None, description="更新者")
    config_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

    class Config:
        from_attributes = True


class PluginRunRequest(BaseModel):
    """运行插件请求模型"""

    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    config: Optional[Dict[str, Any]] = Field(None, description="执行配置")


class PluginRunResponse(BaseModel):
    """运行插件响应模型"""

    plugin: str = Field(..., description="插件名称")
    result: Any = Field(..., description="执行结果")
    execution_id: str = Field(..., description="执行ID")
    success: bool = Field(..., description="是否成功")
    duration_ms: Optional[float] = Field(None, description="执行时长(毫秒)")
    error_message: Optional[str] = Field(None, description="错误消息")


class PluginStatsResponse(BaseModel):
    """插件统计响应模型"""

    total_plugins: int = Field(..., description="总插件数")
    active_plugins: int = Field(..., description="活跃插件数")
    inactive_plugins: int = Field(..., description="非活跃插件数")
    error_plugins: int = Field(..., description="错误插件数")
    total_executions: int = Field(..., description="总执行次数")
    successful_executions: int = Field(..., description="成功执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
