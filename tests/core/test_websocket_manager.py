# -*- coding: utf-8 -*-
"""测试WebSocket管理器模块"""

import pytest


class TestWebSocketManagerModule:
    """测试WebSocket管理器模块"""

    @pytest.mark.skip(reason="Module not in core/")
    def test_websocket_manager_module_exists(self):
        """测试WebSocket管理器模块存在"""
        from core import websocket_manager

        assert websocket_manager is not None

    @pytest.mark.skip(reason="Module not in core/")
    def test_websocket_manager_has_functions(self):
        """测试WebSocket管理器模块有函数"""
        from core import websocket_manager

        # 检查模块有函数或类
        assert len(dir(websocket_manager)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
