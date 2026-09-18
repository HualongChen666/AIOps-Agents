# -*- coding: utf-8 -*-
"""
异常值过滤算法
Outlier Filter Algorithm

基于IQR的异常值过滤，用于清洗监控数据。
"""

from typing import List
from loguru import logger


class OutlierFilter:
    """
    异常值过滤器

    基于四分位距（IQR）检测异常值，用于清洗监控数据。
    """

    def __init__(self, multiplier: float = 1.5):
        """
        初始化过滤器

        Args:
            multiplier: IQR倍数，默认1.5（标准异常值检测）
        """
        self.multiplier = multiplier

    def is_outlier(self, value: float, data: List[float]) -> bool:
        """
        判断是否为异常值

        基于IQR方法：Q1 - 1.5*IQR 和 Q3 + 1.5*IQR 之外的值视为异常值。

        Args:
            value: 待检测的值
            data: 历史数据列表

        Returns:
            是否为异常值
        """
        if len(data) < 4:
            # 数据太少不过滤
            return False

        # 计算四分位数
        sorted_data = sorted(data)
        n = len(sorted_data)

        q1_index = n // 4
        q3_index = (3 * n) // 4

        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]

        iqr = q3 - q1

        if iqr == 0:
            # IQR为0，说明数据过于集中，不进行过滤
            return False

        lower_bound = q1 - self.multiplier * iqr
        upper_bound = q3 + self.multiplier * iqr

        is_outlier = value < lower_bound or value > upper_bound

        if is_outlier:
            logger.debug(f"检测到异常值: {value} (范围: [{lower_bound:.2f}, {upper_bound:.2f}])")

        return is_outlier

    def filter_outliers(self, data: List[float]) -> List[float]:
        """
        过滤异常值

        Args:
            data: 原始数据列表

        Returns:
            过滤后的数据列表
        """
        if len(data) < 4:
            return data.copy()

        # 计算四分位数
        sorted_data = sorted(data)
        n = len(sorted_data)

        q1_index = n // 4
        q3_index = (3 * n) // 4

        q1 = sorted_data[q1_index]
        q3 = sorted_data[q3_index]

        iqr = q3 - q1

        if iqr == 0:
            return data.copy()

        lower_bound = q1 - self.multiplier * iqr
        upper_bound = q3 + self.multiplier * iqr

        # 过滤异常值
        filtered_data = [v for v in data if lower_bound <= v <= upper_bound]

        logger.debug(f"异常值过滤: {len(data)} -> {len(filtered_data)} (过滤了{len(data) - len(filtered_data)}个)")

        return filtered_data
