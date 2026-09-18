# -*- coding: utf-8 -*-
"""
Welford增量统计算法
Welford Online Statistics Algorithm

提供O(1)时间复杂度的增量统计量更新，适用于实时监控场景。
"""

import math
from typing import Optional


class WelfordStats:
    """
    Welford增量统计算法

    使用Welford算法在线计算均值、方差和标准差，时间复杂度为O(1)。
    适用于需要增量更新统计量的实时监控场景。

    算法原理：
    - 增量更新均值和方差，避免存储所有历史数据
    - 数值稳定性好，适合浮点数计算
    - 内存占用恒定，不随数据量增长
    """

    def __init__(self):
        """初始化统计量"""
        self.count: int = 0  # 样本数量
        self.mean: float = 0.0  # 均值
        self.M2: float = 0.0  # 用于计算方差的中间变量

    def update(self, value: float) -> None:
        """
        增量更新统计量

        Args:
            value: 新的观测值

        算法步骤：
        1. 增加样本计数
        2. 计算当前值与均值的差值
        3. 更新均值
        4. 更新M2（用于计算方差）
        """
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        self.M2 += delta * (value - self.mean)

    def get_mean(self) -> float:
        """
        获取均值

        Returns:
            当前均值，如果没有样本则返回0.0
        """
        return self.mean if self.count > 0 else 0.0

    def get_variance(self) -> float:
        """
        获取方差

        Returns:
            当前方差，如果样本数<2则返回0.0
        """
        return self.M2 / self.count if self.count > 1 else 0.0

    def get_std(self) -> float:
        """
        获取标准差

        Returns:
            当前标准差，如果样本数<2则返回0.0
        """
        return math.sqrt(self.get_variance())

    def z_score(self, value: float) -> float:
        """
        计算z-score

        z-score表示当前值距离均值的标准差倍数，用于异常检测。

        Args:
            value: 待计算z-score的值

        Returns:
            z-score值，如果标准差为0则返回0.0
        """
        std = self.get_std()
        return (value - self.mean) / std if std > 0 else 0.0

    def reset(self) -> None:
        """重置所有统计量"""
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0

    def get_summary(self) -> dict:
        """
        获取统计摘要

        Returns:
            包含count, mean, variance, std的字典
        """
        return {
            "count": self.count,
            "mean": self.get_mean(),
            "variance": self.get_variance(),
            "std": self.get_std()
        }
