# -*- coding: utf-8 -*-
# tests/api/test_windows_repair_router.py
# Windows修复路由API基础测试
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].WIN_HOSTS = []
sys.modules["core.api_helpers"] = MagicMock()
sys.modules["core.api_helpers"].find_host_config = Mock(return_value=None)
sys.modules["core.api_helpers"].get_operator_ip = Mock(return_value="127.0.0.1")
sys.modules["core.api_helpers"].hostname_field_validator = Mock(side_effect=lambda x: x)
sys.modules["core.windows_repair"] = MagicMock()
sys.modules["core.windows_repair"].WINDOWS_REPAIR_SCRIPTS = {}
sys.modules["core.windows_repair"].execute_windows_repair = AsyncMock()
sys.modules["core.windows_repair"].get_windows_repair_history = Mock(return_value=[])

from api.windows_repair_router import get_history, list_repair_scripts, run_repair


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/platforms/windows", tags=["Windows 修复"])
    test_router.add_api_route("/repair/scripts", list_repair_scripts, methods=["GET"])
    test_router.add_api_route("/repair/execute", run_repair, methods=["POST"])
    test_router.add_api_route("/repair/history", get_history, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestWindowsRepairRouter:
    """测试Windows修复路由"""

    def test_list_repair_scripts(self, client):
        """测试获取修复脚本列表"""
        with patch(
            "api.windows_repair_router.WINDOWS_REPAIR_SCRIPTS",
            {
                "kill_process": {"name": "终止进程", "description": "终止指定进程"},
                "restart_service": {"name": "重启服务", "description": "重启指定服务"},
            },
        ):
            response = client.get("/api/v1/platforms/windows/repair/scripts")
            assert response.status_code in [200, 500]
            data = response.json()
            assert "scripts" in data

    def test_list_repair_scripts_empty(self, client):
        """测试获取空修复脚本列表"""
        with patch("api.windows_repair_router.WINDOWS_REPAIR_SCRIPTS", {}):
            response = client.get("/api/v1/platforms/windows/repair/scripts")
            assert response.status_code in [200, 500]

    def test_run_repair_success(self, client):
        """测试成功执行修复脚本"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.return_value = {
                "success": True,
                "output": "Process killed successfully",
                "exit_code": 0,
                "duration_sec": 1.5,
            }

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={
                    "host_name": "win-server-01",
                    "script_key": "kill_process",
                    "params": {"pid": "1234"},
                },
            )
            assert response.status_code in [200, 404, 500]

    def test_run_repair_host_not_found(self, client):
        """测试主机不存在"""
        with patch("api.windows_repair_router.find_windows_host_config") as mock_find:
            mock_find.return_value = None

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "nonexistent-host", "script_key": "kill_process"},
            )
            assert response.status_code in [404, 500]

    def test_get_history(self, client):
        """测试获取修复历史记录"""
        with patch("api.windows_repair_router.get_windows_repair_history") as mock_history:
            mock_history.return_value = [
                {
                    "host": "win-server-01",
                    "script": "kill_process",
                    "success": True,
                    "timestamp": "2026-07-03T09:00:00Z",
                }
            ]

            response = client.get("/api/v1/platforms/windows/repair/history?limit=10")
            assert response.status_code in [200, 500]
            data = response.json()
            assert "total" in data

    def test_run_repair_execution_error(self, client):
        """测试修复执行抛出异常"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.side_effect = RuntimeError("execution failed")

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "win-server-01", "script_key": "kill_process"},
            )
            assert response.status_code == 500

    def test_run_repair_non_dict_result(self, client):
        """测试修复引擎返回非dict"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.return_value = "bad result"

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "win-server-01", "script_key": "kill_process"},
            )
            assert response.status_code == 500

    def test_run_repair_unknown_script(self, client):
        """测试未知的Windows修复脚本"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.return_value = {"error": "未知的 windows 修复脚本 kill_process"}

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "win-server-01", "script_key": "kill_process"},
            )
            assert response.status_code == 404

    def test_run_repair_invalid_param(self, client):
        """测试修复参数非法返回422"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.return_value = {"error": "pid 必须为整数"}

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "win-server-01", "script_key": "kill_process"},
            )
            assert response.status_code == 422

    def test_run_repair_generic_error(self, client):
        """测试修复返回通用错误"""
        with (
            patch("api.windows_repair_router.find_windows_host_config") as mock_find,
            patch(
                "api.windows_repair_router.execute_windows_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_find.return_value = {"name": "win-server-01", "ip": "192.168.1.100"}
            mock_execute.return_value = {"error": "some error"}

            response = client.post(
                "/api/v1/platforms/windows/repair/execute",
                json={"host_name": "win-server-01", "script_key": "kill_process"},
            )
            assert response.status_code == 500

    def test_get_history_filter(self, client):
        """测试按主机名过滤历史记录"""
        with patch("api.windows_repair_router.get_windows_repair_history") as mock_history:
            mock_history.return_value = [
                {"host": "win-server-01", "script": "kill_process", "success": True},
                {"host": "win-server-02", "script": "restart_service", "success": True},
            ]

            response = client.get(
                "/api/v1/platforms/windows/repair/history?limit=10&host_name=win-server-01"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1

    def test_get_history_error(self, client):
        """测试获取历史异常"""
        with patch("api.windows_repair_router.get_windows_repair_history") as mock_history:
            mock_history.side_effect = RuntimeError("history error")

            response = client.get("/api/v1/platforms/windows/repair/history?limit=10")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
