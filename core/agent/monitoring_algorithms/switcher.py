# -*- coding: utf-8 -*-
"""
混合切换逻辑
Hybrid Switching Logic

提供固定阈值到z-score的混合切换条件判断。
"""

from typing import Tuple
from loguru import logger


class HybridSwitcher:
    """
    混合切换器

    根据样本数量和时间窗口判断是否应该使用z-score检测。
    支持样本数豁免机制，当样本数足够多时可以豁免时间窗口要求。
    """

    def __init__(self):
        """初始化切换器"""
        self.min_samples_for_z_score: int = 30  # 启用z-score的最小样本数
        self.min_days_for_time_window: int = 7  # 时间窗口要求（天）
        self.min_samples_for_time_waiver: int = 50  # 豁免时间窗口的样本数阈值

    def should_use_z_score(
        self,
        sample_count: int,
        days_span: float
    ) -> Tuple[bool, str]:
        """
        判断是否应该使用z-score

        Args:
            sample_count: 样本数量
            days_span: 时间跨度（天）

        Returns:
            (是否切换, 原因)
        """
        # 检查样本数量
        if sample_count < self.min_samples_for_z_score:
            return False, f"样本数不足 ({sample_count} < {self.min_samples_for_z_score})"

        # 检查时间跨度豁免条件
        if sample_count >= self.min_samples_for_time_waiver:
            # 样本数足够多，豁免时间窗口要求
            logger.debug(f"样本数充足，豁免时间窗口 ({sample_count} >= {self.min_samples_for_time_waiver})")
            return True, f"样本数充足，豁免时间窗口 ({sample_count} >= {self.min_samples_for_time_waiver})"

        # 样本数适中，需要检查时间窗口
        if days_span < self.min_days_for_time_window:
            return False, f"时间跨度不足 ({days_span:.1f}天 < {self.min_days_for_time_window}天)"

        return True, "满足切换条件"

    def get_switch_summary(self, sample_count: int, days_span: float) -> dict:
        """
        获取切换条件摘要

        Args:
            sample_count: 样本数量
            days_span: 时间跨度（天）

        Returns:
            包含各项检查结果的字典
        """
        return {
            "sample_count": sample_count,
            "min_samples_required": self.min_samples_for_z_score,
            "days_span": days_span,
            "min_days_required": self.min_days_for_time_window,
            "waiver_threshold": self.min_samples_for_time_waiver,
            "sample_check": sample_count >= self.min_samples_for_z_score,
            "time_check": days_span >= self.min_days_for_time_window,
            "waiver_check": sample_count >= self.min_samples_for_time_waiver
        }
