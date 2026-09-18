# -*- coding: utf-8 -*-
"""
行为监控配置验证器
Behavior Monitor Configuration Validator

验证配置参数的合理性，提供详细的错误信息。
"""

from typing import List, Tuple
from loguru import logger


class ConfigValidator:
    """配置参数验证器"""

    @staticmethod
    def validate_config(config) -> Tuple[bool, List[str]]:
        """
        验证配置参数的合理性

        Args:
            config: BehaviorMonitorConfig配置对象

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 验证LRU参数
        if config.max_agents <= 0:
            errors.append("max_agents必须大于0")
        if config.max_agents > 1000:
            errors.append("max_agents过大，可能导致内存问题")
        if config.ttl_days <= 0:
            errors.append("ttl_days必须大于0")
        if config.ttl_days > 90:
            errors.append("ttl_days过大，可能导致数据堆积")
        if config.cleanup_interval_seconds < 60:
            errors.append("cleanup_interval_seconds过小，可能影响性能")

        # 验证切换参数
        if config.min_samples_for_z_score < 5:
            errors.append("min_samples_for_z_score过小，z-score可能不准确")
        if config.min_samples_for_z_score > 100:
            errors.append("min_samples_for_z_score过大，切换条件过于严格")
        if config.min_days_for_time_window < 0:
            errors.append("min_days_for_time_window不能为负数")
        if config.min_samples_for_time_waiver <= config.min_samples_for_z_score:
            errors.append("min_samples_for_time_waiver应该大于min_samples_for_z_score")

        # 验证z-score阈值
        if not (0 < config.z_score_warning_threshold < config.z_score_critical_threshold < config.z_score_fatal_threshold):
            errors.append("z-score阈值必须递增: warning < critical < fatal")
        if config.z_score_warning_threshold < 1.0:
            errors.append("z_score_warning_threshold过小，可能产生大量误报")
        if config.z_score_fatal_threshold > 10.0:
            errors.append("z_score_fatal_threshold过大，可能漏报严重异常")

        # 验证小样本保护参数
        if config.min_samples_for_confidence < 5:
            errors.append("min_samples_for_confidence过小")
        if not (0 < config.confidence_threshold < 1):
            errors.append("confidence_threshold必须在0-1之间")
        if config.max_samples_for_full_confidence < config.min_samples_for_confidence:
            errors.append("max_samples_for_full_confidence应该大于min_samples_for_confidence")

        # 验证监控指标配置
        enabled_metrics = [k for k, v in config.monitored_metrics.items() if v.get("enabled", False)]
        if not enabled_metrics:
            errors.append("至少需要启用一个监控指标")

        for metric_name, metric_config in config.monitored_metrics.items():
            if metric_config.get("enabled", False):
                thresholds = metric_config.get("z_score_thresholds", {})
                if not thresholds:
                    errors.append(f"指标{metric_name}启用了但没有配置z-score阈值")

        return len(errors) == 0, errors

    @staticmethod
    def log_config_summary(config):
        """记录配置摘要"""
        logger.info("=== 行为监控配置摘要 ===")
        logger.info(f"环境: {config.__class__.__name__}")
        logger.info(f"最大agent数量: {config.max_agents}")
        logger.info(f"数据过期时间: {config.ttl_days}天")
        logger.info(f"清理间隔: {config.cleanup_interval_seconds}秒")
        logger.info(f"z-score样本阈值: {config.min_samples_for_z_score}")
        logger.info(f"时间窗口要求: {config.min_days_for_time_window}天")
        logger.info(f"启用的监控指标: {[k for k, v in config.monitored_metrics.items() if v.get('enabled')]}")
        logger.info("========================")
