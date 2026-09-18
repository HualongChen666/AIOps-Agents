# -*- coding: utf-8 -*-
"""
鲁棒的异常检测算法
Robust Anomaly Detection Algorithm

提供带置信度的异常检测，支持小样本保护和回退机制。
"""

import math
from typing import Dict, Any, Optional
from loguru import logger
from .stats import WelfordStats


class RobustAnomalyDetector:
    """
    鲁棒的异常检测器

    基于z-score进行异常检测，包含置信度计算和回退机制。
    针对小样本情况提供保护，避免误报。
    """

    def __init__(self):
        """初始化异常检测器"""
        self.min_samples_for_confidence: int = 10  # 计算置信度的最小样本数
        self.confidence_threshold: float = 0.5  # 回退到固定阈值的置信度阈值
        self.max_samples_for_full_confidence: int = 50  # 达到满置信度的样本数

    def detect_with_confidence(self, value: float, stats: WelfordStats) -> Dict[str, Any]:
        """
        带置信度的异常检测

        Args:
            value: 待检测的值
            stats: WelfordStats统计对象

        Returns:
            包含is_anomaly, method, z_score, confidence, sample_size, reason的字典
        """
        if stats.count < self.min_samples_for_confidence:
            # 样本不足，使用固定阈值或返回低置信度
            return {
                "is_anomaly": False,
                "method": "insufficient_data",
                "z_score": None,
                "confidence": 0.0,
                "sample_size": stats.count,
                "reason": f"样本数不足 ({stats.count} < {self.min_samples_for_confidence})"
            }

        # 计算z-score
        z_score = stats.z_score(value)

        # 计算置信度（基于样本量）
        confidence = self._calculate_confidence(stats.count)

        # 判断异常（使用2.5作为默认阈值）
        is_anomaly = abs(z_score) >= 2.5

        return {
            "is_anomaly": is_anomaly,
            "method": "z_score",
            "z_score": z_score,
            "confidence": confidence,
            "sample_size": stats.count,
            "reason": f"z-score={z_score:.2f}, 置信度={confidence:.2f}"
        }

    def detect_with_fallback(
        self,
        value: float,
        stats: WelfordStats,
        fixed_threshold: float
    ) -> Dict[str, Any]:
        """
        带回退机制的异常检测

        当置信度低或样本不足时，回退到固定阈值检测。

        Args:
            value: 待检测的值
            stats: WelfordStats统计对象
            fixed_threshold: 固定阈值

        Returns:
            包含检测结果的字典
        """
        result = self.detect_with_confidence(value, stats)

        # 如果置信度低或样本不足，回退到固定阈值
        if result["confidence"] < self.confidence_threshold or result["method"] == "insufficient_data":
            is_anomaly = value > fixed_threshold
            result["is_anomaly"] = is_anomaly
            result["method"] = "fixed_threshold"
            result["reason"] = f"回退到固定阈值 (置信度低: {result['confidence']})"
            logger.debug(f"异常检测回退到固定阈值: value={value}, threshold={fixed_threshold}")

        return result

    def _calculate_confidence(self, sample_size: int) -> float:
        """
        基于样本量的置信度计算

        使用logistic函数平滑过渡，样本量越大置信度越高。

        Args:
            sample_size: 样本数量

        Returns:
            置信度（0-1之间）
        """
        if sample_size >= self.max_samples_for_full_confidence:
            return 0.95

        # 使用logistic函数
        k = 0.1  # 陡度参数
        x0 = 25  # 中点参数
        confidence = 0.95 / (1 + math.exp(-k * (sample_size - x0)))

        return max(0.0, min(confidence, 0.95))

    def get_severity_from_z_score(self, z_score: float) -> Optional[str]:
        """
        根据z-score获取严重级别

        Args:
            z_score: z-score值

        Returns:
            严重级别：warning, critical, fatal 或 None
        """
        abs_z = abs(z_score)

        if abs_z >= 5.0:
            return "fatal"
        elif abs_z >= 3.5:
            return "critical"
        elif abs_z >= 2.5:
            return "warning"
        else:
            return None
