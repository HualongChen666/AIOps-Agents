# -*- coding: utf-8 -*-
"""Linux Router Tests
Linux路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].LINUX_HOSTS = [
    {"name": "linux-server-01", "host": "192.168.1.10", "role": "app", "layer": "backend"}
]
sys.modules["config"].LINUX_SSH_TIMEOUT = 30
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.api_helpers"] = MagicMock()
sys.modules["core.api_helpers"].find_host_config = Mock(
    return_value={"name": "linux-server-01", "host": "192.168.1.10"}
)
sys.modules["core.api_helpers"].get_operator_ip = Mock(return_value="127.0.0.1")
sys.modules["core.api_helpers"].hostname_field_validator = Mock(return_value="linux-server-01")
sys.modules["core.linux_collector"] = MagicMock()
sys.modules["core.linux_repair"] = MagicMock()

from api.linux_router import (
    collect_all_hosts_endpoint,
    collect_single_host,
    list_available_metrics,
    list_hosts,
    list_repair_scripts,
    run_repair,
)


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/platforms/linux", tags=["Linux 监控"])
    test_router.add_api_route("/hosts", list_hosts, methods=["GET"])
    test_router.add_api_route("/metrics/available", list_available_metrics, methods=["GET"])
    test_router.add_api_route("/collect/all", collect_all_hosts_endpoint, methods=["GET"])
    test_router.add_api_route("/collect/host", collect_single_host, methods=["POST"])
    test_router.add_api_route("/repair/scripts", list_repair_scripts, methods=["GET"])
    test_router.add_api_route("/repair/execute", run_repair, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestLinuxRouter:
    """测试Linux路由"""

    def test_list_hosts(self, client):
        """测试获取已配置的Linux主机列表"""
        with patch("api.linux_router.get_configured_hosts") as mock_hosts:
            mock_hosts.return_value = [
                {
                    "name": "linux-server-01",
                    "host": "192.168.1.10",
                    "role": "app",
                    "layer": "backend",
                }
            ]
            response = client.get("/api/v1/platforms/linux/hosts")
            assert response.status_code == 200
            data = response.json()
            assert "hosts" in data

    def test_list_available_metrics(self, client):
        """测试获取可采集的指标维度列表"""
        with patch("api.linux_router.get_available_metrics") as mock_metrics:
            mock_metrics.return_value = [{"key": "cpu", "name": "CPU使用率", "unit": "%"}]
            response = client.get("/api/v1/platforms/linux/metrics/available")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data

    def test_collect_all_hosts(self, client):
        """测试采集所有Linux主机指标"""
        with patch("api.linux_router.collect_all_linux") as mock_collect:

            async def mock_collect_func():
                return [{"host": "linux-server-01", "cpu": {"usage_percent": 45.2}}]

            mock_collect.side_effect = mock_collect_func
            response = client.get("/api/v1/platforms/linux/collect/all")
            assert response.status_code == 200
            data = response.json()
            assert "hosts" in data

    def test_collect_single_host(self, client):
        """测试采集指定Linux主机指标"""
        with patch("api.linux_router.collect_linux_host") as mock_collect:

            async def mock_collect_func(host_config, metrics):
                return {"host": "linux-server-01", "cpu": {"usage_percent": 45.2}}

            mock_collect.side_effect = mock_collect_func
            response = client.post(
                "/api/v1/platforms/linux/collect/host", json={"host_name": "linux-server-01"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "host" in data

    def test_list_repair_scripts(self, client):
        """测试获取Linux修复脚本列表"""
        with patch("api.linux_router.get_linux_repair_scripts") as mock_scripts:
            mock_scripts.return_value = [{"key": "clear_tmp", "name": "清理临时文件", "params": {}}]
            response = client.get("/api/v1/platforms/linux/repair/scripts")
            assert response.status_code == 200
            data = response.json()
            assert "scripts" in data

    def test_run_repair_success(self, client):
        """测试成功执行Linux修复脚本"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def mock_repair_func(host_name, script_key, params):
                return {"success": True, "output": "Command executed successfully", "exit_code": 0}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "linux-server-01", "script_key": "clear_tmp", "params": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_run_repair_blocked(self, client):
        """测试修复脚本被护栏拦截"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def mock_repair_func(host_name, script_key, params):
                return {"blocked": True, "reason": "高危指令"}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "linux-server-01", "script_key": "dangerous_cmd", "params": {}},
            )
            assert response.status_code == 403

    def test_run_repair_pending_approval(self, client):
        """测试修复脚本转入审批队列"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def mock_repair_func(host_name, script_key, params):
                return {
                    "pending_approval": True,
                    "alert_id": "alert_123",
                    "reason": "高风险操作",
                    "approve_url": "http://approve",
                }

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={
                    "host_name": "linux-server-01",
                    "script_key": "risky_operation",
                    "params": {},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending_approval"

    def test_run_repair_host_not_found(self, client):
        """测试修复脚本主机不存在"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def mock_repair_func(host_name, script_key, params):
                return {"success": False, "error": "未找到主机"}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "nonexistent", "script_key": "clear_tmp", "params": {}},
            )
            assert response.status_code == 404

    def test_run_repair_parameter_error(self, client):
        """测试修复脚本参数错误"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def mock_repair_func(host_name, script_key, params):
                return {"success": False, "error": "pid参数必须为数字"}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={
                    "host_name": "linux-server-01",
                    "script_key": "kill_process",
                    "params": {"pid": "invalid"},
                },
            )
            assert response.status_code == 422

    def test_collect_single_host_not_found(self, client):
        """测试采集不存在的主机"""
        with patch("api.linux_router.find_linux_host_config") as mock_find:
            mock_find.return_value = None
            response = client.post(
                "/api/v1/platforms/linux/collect/host", json={"host_name": "nonexistent"}
            )
            assert response.status_code == 404

    def test_collect_single_host_with_metrics(self, client):
        """测试采集指定指标"""
        with patch("api.linux_router.collect_linux_host") as mock_collect:

            async def mock_collect_func(host_config, metrics):
                return {"host": "linux-server-01", "cpu": {"usage_percent": 45.2}}

            mock_collect.side_effect = mock_collect_func
            response = client.post(
                "/api/v1/platforms/linux/collect/host",
                json={"host_name": "linux-server-01", "metrics": ["cpu", "memory"]},
            )
            assert response.status_code == 200

    def test_collect_all_hosts_timeout(self, client):
        """测试采集所有主机超时"""
        import asyncio

        with patch("api.linux_router.collect_all_linux") as mock_collect:

            async def mock_collect_func():
                raise asyncio.TimeoutError("采集超时")

            mock_collect.side_effect = mock_collect_func
            response = client.get("/api/v1/platforms/linux/collect/all")
            assert response.status_code == 504

    def test_collect_single_host_timeout(self, client):
        """测试采集单个主机超时"""
        import asyncio

        with patch("api.linux_router.collect_linux_host") as mock_collect:

            async def mock_collect_func(host_config, metrics):
                raise asyncio.TimeoutError("采集超时")

            mock_collect.side_effect = mock_collect_func
            response = client.post(
                "/api/v1/platforms/linux/collect/host", json={"host_name": "linux-server-01"}
            )
            assert response.status_code == 504

    def test_list_hosts_empty(self, client):
        """测试空主机列表"""
        with patch("api.linux_router.get_configured_hosts") as mock_hosts:
            mock_hosts.return_value = []
            response = client.get("/api/v1/platforms/linux/hosts")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_collect_all_hosts_no_hosts(self, client):
        """测试未配置Linux主机时采集所有主机"""
        with patch("api.linux_router.LINUX_HOSTS", []):
            response = client.get("/api/v1/platforms/linux/collect/all")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0

    def test_list_hosts_error(self, client):
        """测试获取主机列表异常"""
        with patch("api.linux_router.get_configured_hosts") as mock_hosts:
            mock_hosts.side_effect = RuntimeError("db error")
            response = client.get("/api/v1/platforms/linux/hosts")
            assert response.status_code == 500

    def test_list_available_metrics_error(self, client):
        """测试获取可用指标异常"""
        with patch("api.linux_router.get_available_metrics") as mock_metrics:
            mock_metrics.side_effect = RuntimeError("db error")
            response = client.get("/api/v1/platforms/linux/metrics/available")
            assert response.status_code == 500

    def test_collect_all_hosts_error(self, client):
        """测试全量采集通用异常"""
        with patch("api.linux_router.collect_all_linux") as mock_collect:

            async def fail():
                raise RuntimeError("collect error")

            mock_collect.side_effect = fail
            response = client.get("/api/v1/platforms/linux/collect/all")
            assert response.status_code == 500

    def test_collect_single_host_error(self, client):
        """测试单主机采集通用异常"""
        with patch("api.linux_router.collect_linux_host") as mock_collect:

            async def fail(host_config, metrics):
                raise RuntimeError("collect error")

            mock_collect.side_effect = fail
            response = client.post(
                "/api/v1/platforms/linux/collect/host", json={"host_name": "linux-server-01"}
            )
            assert response.status_code == 500

    def test_list_repair_scripts_error(self, client):
        """测试获取修复脚本列表异常"""
        with patch("api.linux_router.get_linux_repair_scripts") as mock_scripts:
            mock_scripts.side_effect = RuntimeError("script error")
            response = client.get("/api/v1/platforms/linux/repair/scripts")
            assert response.status_code == 500

    def test_run_repair_none_result(self, client):
        """测试修复返回None"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def none_result(*args, **kwargs):
                return None

            mock_repair.side_effect = none_result
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "linux-server-01", "script_key": "clear_tmp", "params": {}},
            )
            assert response.status_code == 500

    def test_run_repair_non_dict_result(self, client):
        """测试修复返回非dict"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def bad_result(*args, **kwargs):
                return "bad"

            mock_repair.side_effect = bad_result
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "linux-server-01", "script_key": "clear_tmp", "params": {}},
            )
            assert response.status_code == 500

    def test_run_repair_generic_error(self, client):
        """测试修复返回通用错误500"""
        with patch("api.linux_router.execute_linux_repair") as mock_repair:

            async def generic_error(*args, **kwargs):
                return {"success": False, "error": "generic failure"}

            mock_repair.side_effect = generic_error
            response = client.post(
                "/api/v1/platforms/linux/repair/execute",
                json={"host_name": "linux-server-01", "script_key": "clear_tmp", "params": {}},
            )
            assert response.status_code == 500

    def test_find_linux_host_config_with_dict_hosts(self, client):
        """测试LINUX_HOSTS为dict时查找主机"""
        with patch("api.linux_router.LINUX_HOSTS", {"srv": {"name": "srv", "host": "10.0.0.1"}}):
            with patch("api.linux_router.find_host_config") as mock_find:
                mock_find.return_value = {"name": "srv"}
                with patch("api.linux_router.collect_linux_host") as mock_collect:

                    async def ok(host_config, metrics):
                        return {"host": "srv"}

                    mock_collect.side_effect = ok
                    response = client.post(
                        "/api/v1/platforms/linux/collect/host", json={"host_name": "srv"}
                    )
                    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
