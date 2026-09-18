# -*- coding: utf-8 -*-
"""
行为监控算法模块测试
Behavior Monitor Algorithms Module Tests

测试Welford统计算法、异常检测、混合切换逻辑、异常值过滤。
"""

import pytest
import math
from core.agent.monitoring_algorithms.stats import WelfordStats
from core.agent.monitoring_algorithms.anomaly import RobustAnomalyDetector
from core.agent.monitoring_algorithms.switcher import HybridSwitcher
from core.agent.monitoring_algorithms.filter import OutlierFilter


class TestWelfordStats:
    """Welford统计算法测试"""

    def test_welford_initial_state(self):
        """测试初始状态"""
        stats = WelfordStats()
        assert stats.count == 0
        assert stats.get_mean() == 0.0
        assert stats.get_variance() == 0.0
        assert stats.get_std() == 0.0

    def test_welford_single_update(self):
        """测试单次更新"""
        stats = WelfordStats()
        stats.update(10)
        assert stats.count == 1
        assert stats.get_mean() == 10.0
        assert stats.get_variance() == 0.0  # 单个样本方差为0

    def test_welford_multiple_updates(self):
        """测试多次更新"""
        stats = WelfordStats()
        values = [10, 12, 14, 16, 18]
        for value in values:
            stats.update(value)

        assert stats.count == 5
        assert abs(stats.get_mean() - 14.0) < 0.01  # 均值应为14
        assert stats.get_std() > 0  # 标准差应大于0

    def test_welford_z_score_calculation(self):
        """测试z-score计算"""
        stats = WelfordStats()

        # 建立基线
        for value in [8, 9, 10, 11, 12]:
            stats.update(value)

        # 测试正常值的z-score
        normal_z = stats.z_score(10)
        assert abs(normal_z) < 1.0  # 均值附近z-score应较小

        # 测试异常值的z-score
        abnormal_z = stats.z_score(20)
        assert abs(abnormal_z) > 2.0  # 异常值z-score应较大

    def test_welford_reset(self):
        """测试重置功能"""
        stats = WelfordStats()
        stats.update(10)
        stats.update(20)
        stats.reset()

        assert stats.count == 0
        assert stats.get_mean() == 0.0
        assert stats.get_variance() == 0.0

    def test_welford_summary(self):
        """测试统计摘要"""
        stats = WelfordStats()
        for value in [10, 12, 14, 16, 18]:
            stats.update(value)

        summary = stats.get_summary()
        assert "count" in summary
        assert "mean" in summary
        assert "variance" in summary
        assert "std" in summary


class TestRobustAnomalyDetector:
    """鲁棒异常检测器测试"""

    def test_insufficient_samples(self):
        """测试样本数不足的情况"""
        detector = RobustAnomalyDetector()
        stats = WelfordStats()

        # 样本数不足
        for _ in range(5):
            stats.update(10)

        result = detector.detect_with_confidence(100, stats)
        assert result["is_anomaly"] is False
        assert result["method"] == "insufficient_data"
        assert result["confidence"] == 0.0

    def test_sufficient_samples(self):
        """测试样本数充足的情况"""
        detector = RobustAnomalyDetector()
        stats = WelfordStats()

        # 建立基线
        for value in [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38]:
            stats.update(value)

        result = detector.detect_with_confidence(10, stats)
        assert result["method"] == "z_score"
        assert result["confidence"] > 0

    def test_fallback_mechanism(self):
        """测试回退机制"""
        detector = RobustAnomalyDetector()
        stats = WelfordStats()

        # 样本数不足
        for _ in range(5):
            stats.update(10)

        result = detector.detect_with_fallback(100, stats, fixed_threshold=50)
        assert result["method"] == "fixed_threshold"
        assert result["is_anomaly"] is True  # 100 > 50

    def test_confidence_calculation(self):
        """测试置信度计算"""
        detector = RobustAnomalyDetector()

        # 小样本
        confidence_small = detector._calculate_confidence(10)
        assert 0 < confidence_small < 0.5

        # 大样本
        confidence_large = detector._calculate_confidence(60)
        assert confidence_large >= 0.9

    def test_severity_from_z_score(self):
        """测试z-score到严重级别的映射"""
        detector = RobustAnomalyDetector()

        assert detector.get_severity_from_z_score(1.0) is None
        assert detector.get_severity_from_z_score(2.5) == "warning"
        assert detector.get_severity_from_z_score(3.5) == "critical"
        assert detector.get_severity_from_z_score(5.0) == "fatal"


class TestHybridSwitcher:
    """混合切换器测试"""

    def test_insufficient_samples(self):
        """测试样本数不足"""
        switcher = HybridSwitcher()
        should_switch, reason = switcher.should_use_z_score(sample_count=10, days_span=5.0)

        assert should_switch is False
        assert "样本数不足" in reason

    def test_insufficient_time_window(self):
        """测试时间跨度不足"""
        switcher = HybridSwitcher()
        should_switch, reason = switcher.should_use_z_score(sample_count=35, days_span=1.0)

        assert should_switch is False
        assert "时间跨度不足" in reason

    def test_both_conditions_met(self):
        """测试同时满足两个条件"""
        switcher = HybridSwitcher()
        should_switch, reason = switcher.should_use_z_score(sample_count=35, days_span=10.0)

        assert should_switch is True
        assert "满足切换条件" in reason

    def test_time_waiver(self):
        """测试时间窗口豁免"""
        switcher = HybridSwitcher()
        should_switch, reason = switcher.should_use_z_score(sample_count=60, days_span=1.0)

        assert should_switch is True
        assert "豁免时间窗口" in reason

    def test_switch_summary(self):
        """测试切换条件摘要"""
        switcher = HybridSwitcher()
        summary = switcher.get_switch_summary(sample_count=35, days_span=10.0)

        assert summary["sample_count"] == 35
        assert summary["days_span"] == 10.0
        assert summary["sample_check"] is True
        assert summary["time_check"] is True


class TestOutlierFilter:
    """异常值过滤器测试"""

    def test_insufficient_data(self):
        """测试数据不足"""
        filter = OutlierFilter()
        assert filter.is_outlier(100, [10, 20]) is False

    def test_normal_value(self):
        """测试正常值"""
        filter = OutlierFilter()
        data = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        assert filter.is_outlier(15, data) is False

    def test_outlier_value(self):
        """测试异常值"""
        filter = OutlierFilter()
        data = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
        assert filter.is_outlier(100, data) is True

    def test_filter_outliers(self):
        """测试过滤异常值"""
        filter = OutlierFilter()
        data = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 100]  # 100是异常值

        filtered = filter.filter_outliers(data)
        assert 100 not in filtered
        assert len(filtered) < len(data)

    def test_no_outliers(self):
        """测试无异常值的情况"""
        filter = OutlierFilter()
        data = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]

        filtered = filter.filter_outliers(data)
        assert len(filtered) == len(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
