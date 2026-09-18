# -*- coding: utf-8 -*-
"""
功能开关
Feature Flags

提供功能开关控制，支持按需启用不同功能模块。
"""

from core.agent.subagent_config import (
    ENABLE_TIMEOUT,
    ENABLE_VALIDATION,
    ENABLE_WHITELIST,
    ENABLE_PROGRESS,
    ENABLE_STALL_DETECTION
)


class FeatureFlags:
    """
    功能开关
    
    控制不同功能模块的启用状态，支持按需加载。
    """
    
    def __init__(self):
        """初始化功能开关"""
        self.enable_timeout = ENABLE_TIMEOUT
        self.enable_validation = ENABLE_VALIDATION
        self.enable_whitelist = ENABLE_WHITELIST
        self.enable_progress = ENABLE_PROGRESS
        self.enable_stall_detection = ENABLE_STALL_DETECTION
    
    def is_timeout_enabled(self) -> bool:
        """检查超时功能是否启用"""
        return self.enable_timeout
    
    def is_validation_enabled(self) -> bool:
        """检查参数验证功能是否启用"""
        return self.enable_validation
    
    def is_whitelist_enabled(self) -> bool:
        """检查白名单功能是否启用"""
        return self.enable_whitelist
    
    def is_progress_enabled(self) -> bool:
        """检查进度显示功能是否启用"""
        return self.enable_progress
    
    def is_stall_detection_enabled(self) -> bool:
        """检查停滞检测功能是否启用"""
        return self.enable_stall_detection
    
    def get_enabled_features(self) -> list:
        """
        获取所有启用的功能
        
        Returns:
            启用的功能列表
        """
        enabled = []
        if self.enable_timeout:
            enabled.append("timeout")
        if self.enable_validation:
            enabled.append("validation")
        if self.enable_whitelist:
            enabled.append("whitelist")
        if self.enable_progress:
            enabled.append("progress")
        if self.enable_stall_detection:
            enabled.append("stall_detection")
        return enabled
    
    def get_disabled_features(self) -> list:
        """
        获取所有禁用的功能
        
        Returns:
            禁用的功能列表
        """
        disabled = []
        if not self.enable_timeout:
            disabled.append("timeout")
        if not self.enable_validation:
            disabled.append("validation")
        if not self.enable_whitelist:
            disabled.append("whitelist")
        if not self.enable_progress:
            disabled.append("progress")
        if not self.enable_stall_detection:
            disabled.append("stall_detection")
        return disabled