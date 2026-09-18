# -*- coding: utf-8 -*-
"""
行为监控配置分析器
Behavior Monitor Configuration Analyzer

分析配置参数的合理性，提供内存需求、时间窗口对齐性、z-score阈值合理性分析。
"""

import math
from typing import Dict, Any
from loguru import logger


class ConfigAnalyzer:
    """配置参数合理性分析器"""

    @staticmethod
    def analyze_memory_requirements(config) -> Dict[str, Any]:
        """
        分析内存需求

        Args:
            config: BehaviorMonitorConfig配置对象

        Returns:
            内存需求分析结果
        """
        # 估算每个agent的内存占用
        # WelfordStats对象: ~100 bytes
        # AgentData: ~1 KB
        # 历史数据: ~100 KB (100条记录)
        estimated_per_agent_kb = 101.1  # KB

        total_memory_mb = (config.max_agents * estimated_per_agent_kb) / 1024

        return {
            "estimated_per_agent_kb": estimated_per_agent_kb,
            "total_memory_mb": total_memory_mb,
            "recommendation": "合理" if total_memory_mb < 50 else "可能过高"
        }

    @staticmethod
    def analyze_time_window_reasonableness(config) -> Dict[str, Any]:
        """
        分析时间窗口合理性

        Args:
            config: BehaviorMonitorConfig配置对象

        Returns:
            时间窗口合理性分析结果
        """
        # 基于业务周期分析
        business_cycles = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30
        }

        closest_cycle = min(
            business_cycles.keys(),
            key=lambda x: abs(business_cycles[x] - config.min_days_for_time_window)
        )

        return {
            "configured_days": config.min_days_for_time_window,
            "closest_business_cycle": closest_cycle,
            "is_aligned": abs(business_cycles[closest_cycle] - config.min_days_for_time_window) == 0,
            "recommendation": f"建议对齐到{closest_cycle}周期"
        }

    @staticmethod
    def analyze_z_score_thresholds(config) -> Dict[str, Any]:
        """
        分析z-score阈值合理性

        Args:
            config: BehaviorMonitorConfig配置对象

        Returns:
            z-score阈值合理性分析结果
        """
        # 基于统计学标准
        standard_thresholds = {
            "1_sigma": 1.0,  # 68%置信度
            "2_sigma": 2.0,  # 95%置信度
            "3_sigma": 3.0  # 99.7%置信度
        }

        return {
            "warning_threshold": config.z_score_warning_threshold,
            "warning_confidence": ConfigAnalyzer._estimate_confidence(config.z_score_warning_threshold),
            "critical_threshold": config.z_score_critical_threshold,
            "critical_confidence": ConfigAnalyzer._estimate_confidence(config.z_score_critical_threshold),
            "fatal_threshold": config.z_score_fatal_threshold,
            "fatal_confidence": ConfigAnalyzer._estimate_confidence(config.z_score_fatal_threshold)
        }

    @staticmethod
    def _estimate_confidence(z_score: float) -> str:
        """
        估算z-score对应的置信度

        Args:
            z_score: z-score值

        Returns:
            置信度描述
        """
        if z_score < 1:
            return "~68%"
        elif z_score < 2:
            return "~95%"
        elif z_score < 3:
            return "~99.7%"
        else:
            return ">99.9%"
