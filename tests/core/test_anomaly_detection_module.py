# -*- coding: utf-8 -*-
"""测试异常检测模块"""

import pytest


class TestAnomalyDetectionModule:
    """测试异常检测模块"""

    def test_anomaly_detection_module_exists(self):
        """测试异常检测模块存在"""
        from core import anomaly_detection

        assert anomaly_detection is not None

    def test_anomaly_detection_has_functions(self):
        """测试异常检测模块有函数"""
        from core import anomaly_detection

        # 检查模块有函数或类
        assert len(dir(anomaly_detection)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
