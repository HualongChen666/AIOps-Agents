# -*- coding: utf-8 -*-
"""
行为监控配置模块
Behavior Monitor Configuration Module

提供行为监控系统的参数配置，支持环境特定默认值和环境变量覆盖。
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Environment(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class BehaviorMonitorConfig:
    """行为监控配置数据类"""

    # === LRU缓存参数 ===
    max_agents: int = 50  # 最多保留的agent基线数量
    ttl_days: int = 7  # 数据过期时间（天）
    cleanup_interval_seconds: int = 1800  # 清理间隔（秒），默认30分钟
    access_cooldown_seconds: int = 300  # 访问时间更新冷却期（秒），默认5分钟

    # === 混合切换参数 ===
    min_samples_for_z_score: int = 30  # 启用z-score的最小样本数
    min_days_for_time_window: int = 7  # 时间窗口要求（天）
    min_samples_for_time_waiver: int = 50  # 豁免时间窗口的样本数阈值

    # === z-score参数 ===
    z_score_warning_threshold: float = 2.5  # WARNING级别z-score阈值
    z_score_critical_threshold: float = 3.5  # CRITICAL级别z-score阈值
    z_score_fatal_threshold: float = 5.0  # FATAL级别z-score阈值

    # === 小样本保护参数 ===
    min_samples_for_confidence: int = 10  # 计算置信度的最小样本数
    confidence_threshold: float = 0.5  # 回退到固定阈值的置信度阈值
    max_samples_for_full_confidence: int = 50  # 达到满置信度的样本数

    # === 监控指标配置 ===
    monitored_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # === 回退参数 ===
    fallback_to_fixed_threshold: bool = True  # 是否启用回退机制

    def __post_init__(self):
        """初始化后处理"""
        if not self.monitored_metrics:
            self.monitored_metrics = self._get_default_monitored_metrics()

    def _get_default_monitored_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取默认监控指标配置"""
        return {
            "iterations": {
                "enabled": True,
                "priority": "high",
                "z_score_thresholds": {
                    "warning": 2.5,
                    "critical": 3.5,
                    "fatal": 5.0
                },
                "fallback_threshold": 50  # 对应MAX_ITERATIONS
            },
            "tool_calls": {
                "enabled": True,
                "priority": "high",
                "z_score_thresholds": {
                    "warning": 2.5,
                    "critical": 3.5,
                    "fatal": 5.0
                },
                "fallback_threshold": 100  # 对应MAX_TOTAL_TOOL_CALLS
            },
            "errors": {
                "enabled": True,
                "priority": "high",
                "z_score_thresholds": {
                    "warning": 2.0,  # 错误更敏感
                    "critical": 3.0,
                    "fatal": 4.0
                },
                "fallback_threshold": 10  # 对应MAX_ERRORS
            },
            "execution_time": {
                "enabled": False,  # 默认关闭，可配置开启
                "priority": "medium",
                "z_score_thresholds": {
                    "warning": 2.5,
                    "critical": 3.5,
                    "fatal": 5.0
                },
                "fallback_threshold": 300  # 对应MAX_EXECUTION_TIME_SECONDS
            }
        }


def load_config(env: Environment = Environment.DEVELOPMENT) -> BehaviorMonitorConfig:
    """
    加载配置，支持环境变量覆盖

    Args:
        env: 环境类型

    Returns:
        BehaviorMonitorConfig: 配置对象
    """
    # 基础配置
    config = BehaviorMonitorConfig()

    # 环境特定默认值
    env_defaults = {
        Environment.DEVELOPMENT: {
            "max_agents": 20,
            "ttl_days": 1,  # 开发环境1天过期
            "min_samples_for_z_score": 5,  # 开发环境降低样本要求
            "min_days_for_time_window": 0,  # 开发环境忽略时间窗口
        },
        Environment.STAGING: {
            "max_agents": 50,
            "ttl_days": 3,
            "min_samples_for_z_score": 20,
            "min_days_for_time_window": 3,
        },
        Environment.PRODUCTION: {
            "max_agents": 100,
            "ttl_days": 7,
            "min_samples_for_z_score": 30,
            "min_days_for_time_window": 7,
        }
    }

    # 应用环境特定默认值
    if env in env_defaults:
        for key, value in env_defaults[env].items():
            setattr(config, key, value)

    # 环境变量覆盖
    config.max_agents = int(os.getenv("BEHAVIOR_MONITOR_MAX_AGENTS", str(config.max_agents)))
    config.ttl_days = int(os.getenv("BEHAVIOR_MONITOR_TTL_DAYS", str(config.ttl_days)))
    config.cleanup_interval_seconds = int(os.getenv("BEHAVIOR_MONITOR_CLEANUP_INTERVAL", str(config.cleanup_interval_seconds)))
    config.min_samples_for_z_score = int(os.getenv("BEHAVIOR_MONITOR_MIN_SAMPLES", str(config.min_samples_for_z_score)))
    config.min_days_for_time_window = int(os.getenv("BEHAVIOR_MONITOR_TIME_WINDOW_DAYS", str(config.min_days_for_time_window)))

    return config


def get_current_environment() -> Environment:
    """获取当前环境类型"""
    env_str = os.getenv("ENVIRONMENT", "development").lower()
    try:
        return Environment(env_str)
    except ValueError:
        return Environment.DEVELOPMENT
