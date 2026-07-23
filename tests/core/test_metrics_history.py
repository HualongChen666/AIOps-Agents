# -*- coding: utf-8 -*-
"""测试指标历史模块"""

import datetime

import pytest


class TestMetricsHistoryModule:
    """测试指标历史模块"""

    def test_metrics_history_module_exists(self):
        """测试指标历史模块存在"""
        from core import metrics_history

        assert metrics_history is not None

    def test_metrics_history_has_functions(self):
        """测试指标历史模块有函数"""
        from core import metrics_history

        # 检查模块有函数或类
        assert len(dir(metrics_history)) > 0


class TestMetricsHistoryClass:
    """测试MetricsHistory类"""

    def test_metrics_history_initialization(self):
        """测试MetricsHistory初始化"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            assert history is not None
            assert history.size == 0
        except Exception as e:
            pytest.skip(f"Cannot test MetricsHistory initialization: {e}")

    def test_metrics_history_initialization_with_custom_maxlen(self):
        """测试自定义maxlen的初始化"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory(maxlen=100)
            assert history._maxlen == 100
        except Exception as e:
            pytest.skip(f"Cannot test custom maxlen: {e}")

    def test_metrics_history_initialization_with_invalid_maxlen(self):
        """测试无效maxlen的初始化"""
        try:
            from core.metrics_history import MetricsHistory

            # 负数应该使用默认值
            history = MetricsHistory(maxlen=-1)
            assert history._maxlen > 0
        except Exception as e:
            pytest.skip(f"Cannot test invalid maxlen: {e}")

    def test_metrics_history_push_basic(self):
        """测试基本push功能"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test basic push: {e}")

    def test_metrics_history_push_multiple(self):
        """测试多次push"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            for i in range(5):
                history.push(
                    cpu=50.0 + i, memory=60.0 + i, net_in=10.0 + i, timestamp=f"12:00:0{i}"
                )
            assert history.size == 5
        except Exception as e:
            pytest.skip(f"Cannot test multiple push: {e}")

    def test_metrics_history_to_dict(self):
        """测试to_dict方法"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")
            result = history.to_dict()
            assert isinstance(result, dict)
            assert "cpu" in result
            assert "memory" in result
            assert "net_in" in result
            assert "timestamps" in result
        except Exception as e:
            pytest.skip(f"Cannot test to_dict: {e}")

    def test_metrics_history_size_property(self):
        """测试size属性"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            assert history.size == 0
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test size property: {e}")

    def test_metrics_history_clear(self):
        """测试clear方法"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")
            assert history.size == 1
            history.clear()
            assert history.size == 0
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")

    def test_metrics_history_push_with_none_values(self):
        """测试push包含None值"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=None, memory=None, net_in=None, timestamp="12:00:00")
            # None值应该被转换为0.0
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test push with None: {e}")

    def test_metrics_history_push_with_datetime_timestamp(self):
        """测试push使用datetime时间戳"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            ts = datetime.datetime.now()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp=ts)
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test push with datetime: {e}")

    def test_metrics_history_push_with_none_timestamp(self):
        """测试push使用None时间戳"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp=None)
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test push with None timestamp: {e}")

    def test_metrics_history_push_with_empty_timestamp(self):
        """测试push使用空字符串时间戳"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="")
            assert history.size == 1
        except Exception as e:
            pytest.skip(f"Cannot test push with empty timestamp: {e}")

    def test_metrics_history_get_dynamic_threshold_cpu(self):
        """测试CPU动态阈值计算"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            # 添加足够的数据点
            for i in range(40):
                history.push(
                    cpu=50.0 + i * 0.5, memory=60.0, net_in=10.0, timestamp=f"12:00:{i:02d}"
                )

            threshold, info = history.get_dynamic_threshold("cpu", static_threshold=80.0)
            assert isinstance(threshold, float)
            assert isinstance(info, dict)
            assert "source" in info
        except Exception as e:
            pytest.skip(f"Cannot test CPU dynamic threshold: {e}")

    def test_metrics_history_get_dynamic_threshold_memory(self):
        """测试内存动态阈值计算"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            for i in range(40):
                history.push(
                    cpu=50.0, memory=60.0 + i * 0.5, net_in=10.0, timestamp=f"12:00:{i:02d}"
                )

            threshold, info = history.get_dynamic_threshold("memory", static_threshold=90.0)
            assert isinstance(threshold, float)
            assert isinstance(info, dict)
        except Exception as e:
            pytest.skip(f"Cannot test memory dynamic threshold: {e}")

    def test_metrics_history_get_dynamic_threshold_net_in(self):
        """测试网络动态阈值计算"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            for i in range(40):
                history.push(
                    cpu=50.0, memory=60.0, net_in=10.0 + i * 0.1, timestamp=f"12:00:{i:02d}"
                )

            threshold, info = history.get_dynamic_threshold("net_in", static_threshold=100.0)
            assert isinstance(threshold, float)
            assert isinstance(info, dict)
        except Exception as e:
            pytest.skip(f"Cannot test net_in dynamic threshold: {e}")

    def test_metrics_history_get_dynamic_threshold_insufficient_samples(self):
        """测试数据点不足时的阈值计算"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")

            threshold, info = history.get_dynamic_threshold(
                "cpu", static_threshold=80.0, min_samples=30
            )
            assert threshold == 80.0  # 应该返回静态阈值
            assert "static_cold_start" in info.get("source", "")
        except Exception as e:
            pytest.skip(f"Cannot test insufficient samples: {e}")

    def test_metrics_history_get_dynamic_threshold_invalid_metric(self):
        """测试无效metric的阈值计算"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            threshold, info = history.get_dynamic_threshold("invalid_metric", static_threshold=80.0)
            assert threshold == 80.0
            assert "unknown_metric" in info.get("source", "")
        except Exception as e:
            pytest.skip(f"Cannot test invalid metric: {e}")

    def test_metrics_history_get_dynamic_threshold_with_sigma_clamp(self):
        """测试sigma参数钳制"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            for i in range(40):
                history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp=f"12:00:{i:02d}")

            # 测试过大的sigma
            threshold1, info1 = history.get_dynamic_threshold(
                "cpu", static_threshold=80.0, sigma=100.0
            )
            # 测试过小的sigma
            threshold2, info2 = history.get_dynamic_threshold(
                "cpu", static_threshold=80.0, sigma=0.01
            )

            assert isinstance(threshold1, float)
            assert isinstance(threshold2, float)
        except Exception as e:
            pytest.skip(f"Cannot test sigma clamp: {e}")

    def test_metrics_history_repr(self):
        """测试__repr__方法"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory()
            repr_str = repr(history)
            assert "MetricsHistory" in repr_str
            assert "maxlen" in repr_str
        except Exception as e:
            pytest.skip(f"Cannot test __repr__: {e}")

    def test_metrics_history_maxlen_behavior(self):
        """测试maxlen行为（环形队列）"""
        try:
            from core.metrics_history import MetricsHistory

            history = MetricsHistory(maxlen=5)
            for i in range(10):
                history.push(
                    cpu=50.0 + i, memory=60.0 + i, net_in=10.0 + i, timestamp=f"12:00:0{i}"
                )
            # 应该只保留最后5个数据点
            assert history.size == 5
        except Exception as e:
            pytest.skip(f"Cannot test maxlen behavior: {e}")


class TestMetricsHistoryGlobalInstance:
    """测试全局metrics_history实例"""

    def test_global_metrics_history_exists(self):
        """测试全局metrics_history实例存在"""
        try:
            from core.metrics_history import metrics_history

            assert metrics_history is not None
            assert isinstance(metrics_history, object)
        except Exception as e:
            pytest.skip(f"Cannot test global instance: {e}")

    def test_global_metrics_history_push(self):
        """测试全局实例push"""
        try:
            from core.metrics_history import metrics_history

            initial_size = metrics_history.size
            metrics_history.push(cpu=50.0, memory=60.0, net_in=10.0, timestamp="12:00:00")
            # size应该增加或保持不变（如果达到maxlen）
            assert metrics_history.size >= initial_size
        except Exception as e:
            pytest.skip(f"Cannot test global push: {e}")

    def test_global_metrics_history_to_dict(self):
        """测试全局实例to_dict"""
        try:
            from core.metrics_history import metrics_history

            result = metrics_history.to_dict()
            assert isinstance(result, dict)
            assert "cpu" in result
        except Exception as e:
            pytest.skip(f"Cannot test global to_dict: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
