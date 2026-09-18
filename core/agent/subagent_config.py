# -*- coding: utf-8 -*-
"""
环境变量配置
Environment Configuration

提供环境变量配置支持，用于控制超时、并发等参数。
"""

import os
from typing import Optional


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    获取布尔类型环境变量
    
    Args:
        key: 环境变量键
        default: 默认值
    
    Returns:
        布尔值
    """
    value = os.getenv(key, str(default)).lower()
    return value in ["true", "1", "yes", "on"]


def get_env_int(key: str, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """
    获取整数类型环境变量
    
    Args:
        key: 环境变量键
        default: 默认值
        min_val: 最小值
        max_val: 最大值
    
    Returns:
        整数值
    """
    try:
        value = int(os.getenv(key, str(default)))
        if min_val is not None and value < min_val:
            return min_val
        if max_val is not None and value > max_val:
            return max_val
        return value
    except (ValueError, TypeError):
        return default


def get_env_str(key: str, default: str = "") -> str:
    """
    获取字符串类型环境变量
    
    Args:
        key: 环境变量键
        default: 默认值
    
    Returns:
        字符串值
    """
    return os.getenv(key, default)


# 超时配置
SUBAGENT_TIMEOUT_SECONDS = get_env_int("SUBAGENT_TIMEOUT_SECONDS", 60, min_val=1, max_val=600)
SUBAGENT_STALL_TIMEOUT_SECONDS = get_env_int("SUBAGENT_STALL_TIMEOUT_SECONDS", 120, min_val=10, max_val=600)
API_TIMEOUT_MS = get_env_int("API_TIMEOUT_MS", 120000, min_val=1000, max_val=600000)

# 并发配置
MAX_CONCURRENT_SUBAGENTS = get_env_int("MAX_CONCURRENT_SUBAGENTS", 5, min_val=1, max_val=20)
MAX_CONCURRENT_TOOL_EXECUTIONS = get_env_int("MAX_CONCURRENT_TOOL_EXECUTIONS", 10, min_val=1, max_val=50)

# 功能开关
ENABLE_TIMEOUT = get_env_bool("ENABLE_TIMEOUT", True)
ENABLE_VALIDATION = get_env_bool("ENABLE_VALIDATION", True)
ENABLE_WHITELIST = get_env_bool("ENABLE_WHITELIST", True)
ENABLE_PROGRESS = get_env_bool("ENABLE_PROGRESS", False)
ENABLE_STALL_DETECTION = get_env_bool("ENABLE_STALL_DETECTION", False)

# 工具白名单
ALLOWED_TOOLS = get_env_str("ALLOWED_TOOLS", "bash,read_file,write_to_file,edit").split(",")
ALLOWED_TOOLS = [tool.strip() for tool in ALLOWED_TOOLS if tool.strip()]