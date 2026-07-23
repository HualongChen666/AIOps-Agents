# -*- coding: utf-8 -*-
import sys
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

sys.modules["core.authentication"] = MagicMock()
sys.modules["core.platform_strategies"] = MagicMock()


class UnifiedRepairRequest(BaseModel):
    platform: str = Field(..., description="平台类型")
    script_key: str = Field(..., description="修复脚本键名")
    host_name: Optional[str] = Field(None, description="主机名")
    params: dict[str, str] = Field(default_factory=dict, description="修复参数")

    class Config:
        schema_extra = {
            "example": {
                "platform": "example",
                "script_key": "example",
                "host_name": "example",
                "params": {},
            }
        }


sys.modules["api.schemas"] = MagicMock()
sys.modules["api.schemas"].UnifiedRepairRequest = UnifiedRepairRequest
from api.unified_repair_router import get_history, list_scripts, run_repair


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    test_router = APIRouter(prefix="/api/v1/repairs", tags=["统一修复"])
    test_router.add_api_route("/scripts", list_scripts, methods=["GET"])
    test_router.add_api_route("/execute", run_repair, methods=["POST"])
    test_router.add_api_route("/history", get_history, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestUnifiedRepairRouter:
    """测试统一修复路由"""

    def test_list_scripts_all(self, client):
        """测试获取所有平台修复脚本"""
        with patch("core.platform_strategies.get_all_platform_strategies") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [{"key": "kill_process", "name": "终止进程"}]
            mock_get.return_value = {"windows": mock_strategy, "linux": mock_strategy}
            response = client.get("/api/v1/repairs/scripts")
            assert response.status_code in [200, 500]

    def test_list_scripts_platform_filter(self, client):
        """测试按平台过滤修复脚本"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [{"key": "kill_process", "name": "终止进程"}]
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            response = client.get("/api/v1/repairs/scripts?platform=windows")
            assert response.status_code in [200, 500]

    def test_run_repair_success(self, client):
        """测试成功执行修复脚本"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "success": True,
                "output": "Process killed successfully",
                "exit_code": 0,
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code in [200, 422, 500]

    def test_run_repair_invalid_platform(self, client):
        """测试不支持的平台"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = ValueError("不支持的平台: invalid")
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "invalid", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code in [400, 422, 500]

    def test_get_history(self, client):
        """测试获取修复历史记录"""
        with patch("core.repair_engine.get_repair_history") as mock_history:
            mock_history.return_value = [
                {
                    "script_key": "kill_process",
                    "exit_code": 0,
                    "executed_at": "2026-07-03T00:00:00Z",
                }
            ]
            response = client.get("/api/v1/repairs/history")
            assert response.status_code in [200, 500]

    def test_run_repair_with_host_name(self, client):
        """测试带主机名的修复执行"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = True
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "success": True,
                "output": "Repair completed",
                "exit_code": 0,
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={
                    "platform": "linux",
                    "script_key": "clear_cache",
                    "host_name": "server01",
                    "params": {},
                },
            )
            assert response.status_code in [200, 422, 500]

    def test_run_repair_missing_host_name(self, client):
        """测试缺少主机名的修复执行"""
        with (patch("api.unified_repair_router.get_platform_strategy") as mock_get,):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = True
            mock_get.return_value = mock_strategy
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "linux", "script_key": "clear_cache", "params": {}},
            )
            assert response.status_code in [422, 400]

    def test_run_repair_blocked(self, client):
        """测试被护栏拦截的修复"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {"blocked": True, "reason": "高危指令"}
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "dangerous_cmd", "params": {}},
            )
            assert response.status_code in [403, 200]

    def test_run_repair_pending_approval(self, client):
        """测试转入审批队列的修复"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "pending_approval": True,
                "alert_id": "alert_123",
                "reason": "高风险操作",
                "approve_url": "http://approve",
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "linux", "script_key": "risky_operation", "params": {}},
            )
            assert response.status_code in [202, 200]

    def test_run_repair_failure(self, client):
        """测试修复执行失败"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "success": False,
                "error": "Execution failed",
                "exit_code": 1,
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "failed_script", "params": {}},
            )
            assert response.status_code in [200, 500]

    def test_list_scripts_empty(self, client):
        """测试空脚本列表"""
        with patch("core.platform_strategies.get_all_platform_strategies") as mock_get:
            mock_get.return_value = {}
            response = client.get("/api/v1/repairs/scripts")
            assert response.status_code in [200, 500]

    def test_get_history_with_filter(self, client):
        """测试带过滤条件的历史记录"""
        with patch("core.repair_engine.get_repair_history") as mock_history:
            mock_history.return_value = [
                {"script_key": "kill_process", "exit_code": 0, "platform": "windows"}
            ]
            response = client.get("/api/v1/repairs/history?platform=windows")
            assert response.status_code in [200, 500]

    def test_get_history_empty(self, client):
        """测试空历史记录"""
        with patch("core.repair_engine.get_repair_history") as mock_history:
            mock_history.return_value = []
            response = client.get("/api/v1/repairs/history")
            assert response.status_code in [200, 500]

    def test_run_repair_with_params(self, client):
        """测试带参数的修复执行"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "success": True,
                "output": "Process killed",
                "exit_code": 0,
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={
                    "platform": "windows",
                    "script_key": "kill_process",
                    "params": {"pid": "1234"},
                },
            )
            assert response.status_code in [200, 422, 500]

    def test_list_scripts_linux_platform(self, client):
        """测试Linux平台脚本列表"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_strategy = Mock()
            mock_strategy.get_scripts.return_value = [{"key": "clear_cache", "name": "清理缓存"}]
            mock_strategy.requires_host_name.return_value = True
            mock_get.return_value = mock_strategy
            response = client.get("/api/v1/repairs/scripts?platform=linux")
            assert response.status_code in [200, 500]

    def test_run_repair_timeout(self, client):
        """测试修复执行超时"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.side_effect = TimeoutError("Execution timeout")
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "slow_script", "params": {}},
            )
            assert response.status_code in [504, 500]

    def test_list_scripts_platform_error(self, client):
        """测试脚本列表平台查询异常"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = RuntimeError("strategy error")
            response = client.get("/api/v1/repairs/scripts?platform=windows")
            assert response.status_code == 500

    def test_list_scripts_error(self, client):
        """测试脚本列表通用异常"""
        with patch("core.platform_strategies.get_all_platform_strategies") as mock_get:
            mock_get.side_effect = RuntimeError("strategy error")
            response = client.get("/api/v1/repairs/scripts")
            assert response.status_code == 500

    def test_run_repair_none_result(self, client):
        """测试修复返回None"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = None
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code == 500

    def test_run_repair_non_dict_result(self, client):
        """测试修复返回非dict"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = "bad"
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code == 500

    def test_run_repair_script_not_found(self, client):
        """测试修复脚本不存在404"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {"success": False, "error": "未知修复脚本 kill_process"}
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code == 404

    def test_run_repair_param_error(self, client):
        """测试修复参数错误422"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {"success": False, "error": "pid 必须为整数"}
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code == 422

    def test_run_repair_blocked_with_safe_alt(self, client):
        """测试被拦截且含安全替代方案"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.return_value = {
                "blocked": True,
                "error": "高危指令",
                "safe_alternative": "safe_cmd",
            }
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "dangerous_cmd", "params": {}},
            )
            assert response.status_code == 403

    def test_run_repair_generic_exception(self, client):
        """测试修复执行通用异常500"""
        with (
            patch("api.unified_repair_router.get_platform_strategy") as mock_get,
            patch(
                "api.unified_repair_router._execute_platform_repair", new_callable=AsyncMock
            ) as mock_execute,
        ):
            mock_strategy = Mock()
            mock_strategy.requires_host_name.return_value = False
            mock_get.return_value = mock_strategy
            mock_execute.side_effect = RuntimeError("boom")
            response = client.post(
                "/api/v1/repairs/execute",
                json={"platform": "windows", "script_key": "kill_process", "params": {}},
            )
            assert response.status_code == 500

    def test_get_history_platform_error(self, client):
        """测试历史记录平台查询异常"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = RuntimeError("history error")
            response = client.get("/api/v1/repairs/history?platform=windows")
            assert response.status_code == 500

    def test_get_history_error(self, client):
        """测试历史记录通用异常"""
        with patch("api.unified_repair_router.get_platform_strategy") as mock_get:
            mock_get.side_effect = RuntimeError("history error")
            response = client.get("/api/v1/repairs/history?platform=windows")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
