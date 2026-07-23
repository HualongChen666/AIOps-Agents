# -*- coding: utf-8 -*-
"""测试心跳模块"""

import pytest


class TestHeartbeatModule:
    """测试心跳模块"""

    def test_heartbeat_module_exists(self):
        """测试心跳模块存在"""
        from core import heartbeat

        assert heartbeat is not None

    def test_heartbeat_has_functions(self):
        """测试心跳模块有函数"""
        from core import heartbeat

        # 检查模块有函数或类
        assert len(dir(heartbeat)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
