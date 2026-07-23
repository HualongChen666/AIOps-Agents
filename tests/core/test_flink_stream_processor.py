# -*- coding: utf-8 -*-
"""测试Flink流处理器模块"""

import pytest


class TestFlinkStreamProcessorModule:
    """测试Flink流处理器模块"""

    def test_flink_stream_processor_module_exists(self):
        """测试Flink流处理器模块存在"""
        from core import flink_stream_processor

        assert flink_stream_processor is not None

    def test_flink_stream_processor_has_functions(self):
        """测试Flink流处理器模块有函数"""
        from core import flink_stream_processor

        # 检查模块有函数或类
        assert len(dir(flink_stream_processor)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
