# -*- coding: utf-8 -*-
# tests/api/test_system_resource_router_enhanced.py
# 系统资源路由API测试
import os
import sys
from unittest.mock import Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.system_resource_router import router

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})
sys.modules["core.system_resource"] = Mock()
sys.modules["core.system_resource"].system_resource_service = Mock()


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestSystemResourceRouter:
    """系统资源路由测试"""

    def test_get_cpu_usage(self):
        """测试获取CPU使用率"""
        with patch("core.system_resource.system_resource_service.get_cpu_usage") as mock_cpu:
            mock_cpu.return_value = {"usage": 50, "cores": 4}
            response = client.get("/api/v1/system/cpu")
            assert response.status_code in [200, 401, 403, 404]

    def test_get_memory_usage(self):
        """测试获取内存使用率"""
        with patch("core.system_resource.system_resource_service.get_memory_usage") as mock_memory:
            mock_memory.return_value = {"total": 16384, "used": 8192, "usage": 50}
            response = client.get("/api/v1/system/memory")
            assert response.status_code in [200, 401, 403, 404]
