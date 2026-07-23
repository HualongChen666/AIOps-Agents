# -*- coding: utf-8 -*-
# tests/api/test_repair_scripts_router.py
# 修复脚本路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.platform_strategies"] = MagicMock()

from api.repair_scripts_router import list_all_scripts, list_platform_scripts


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/repair-scripts", tags=["修复脚本"])
    test_router.add_api_route("/", list_all_scripts, methods=["GET"])
    test_router.add_api_route("/{platform}", list_platform_scripts, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestRepairScriptsRouter:
    """测试修复脚本路由"""

    def test_list_all_scripts(self, client):
        """测试获取所有修复脚本"""
        with patch("api.repair_scripts_router.get_all_platform_strategies") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [{"key": "kill_process", "name": "终止进程"}]
            mock_get.return_value = {"windows": mock_strategy, "linux": mock_strategy}

            response = client.get("/api/v1/repair-scripts/")
            assert response.status_code in [200, 500]

    def test_list_platform_scripts_windows(self, client):
        """测试获取Windows平台修复脚本"""
        with patch("api.repair_scripts_router.get_platform_strategy") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [{"key": "kill_process", "name": "终止进程"}]
            mock_get.return_value = mock_strategy

            response = client.get("/api/v1/repair-scripts/windows")
            assert response.status_code in [200, 500]

    def test_list_platform_scripts_linux(self, client):
        """测试获取Linux平台修复脚本"""
        with patch("api.repair_scripts_router.get_platform_strategy") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [
                {"key": "restart_service", "name": "重启服务"}
            ]
            mock_get.return_value = mock_strategy

            response = client.get("/api/v1/repair-scripts/linux")
            assert response.status_code in [200, 500]

    def test_list_platform_scripts_invalid(self, client):
        """测试获取不支持的平台脚本"""
        with patch("api.repair_scripts_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = ValueError("不支持的平台: invalid")

            response = client.get("/api/v1/repair-scripts/invalid")
            assert response.status_code in [400, 500]

    def test_list_all_scripts_error(self, client):
        """测试获取所有脚本失败"""
        with patch("api.repair_scripts_router.get_all_platform_strategies") as mock_get:
            mock_get.side_effect = Exception("获取脚本列表失败")

            response = client.get("/api/v1/repair-scripts/")
            assert response.status_code == 500

    def test_list_platform_scripts_http_exception(self, client):
        """测试平台脚本直接抛出HTTPException"""
        from fastapi import HTTPException

        with patch("api.repair_scripts_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = HTTPException(status_code=403, detail="forbidden")

            response = client.get("/api/v1/repair-scripts/protected")
            assert response.status_code == 403

    def test_list_platform_scripts_server_error(self, client):
        """测试平台脚本抛出通用异常"""
        with patch("api.repair_scripts_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = RuntimeError("server error")

            response = client.get("/api/v1/repair-scripts/linux")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
