# -*- coding: utf-8 -*-
"""测试gRPC服务管理器模块"""

import pytest


class TestGrpcServiceManagerModule:
    """测试gRPC服务管理器模块"""

    def test_grpc_service_manager_module_exists(self):
        """测试gRPC服务管理器模块存在"""
        from core import grpc_service_manager

        assert grpc_service_manager is not None

    def test_grpc_service_manager_has_functions(self):
        """测试gRPC服务管理器模块有函数"""
        from core import grpc_service_manager

        # 检查模块有函数或类
        assert len(dir(grpc_service_manager)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
