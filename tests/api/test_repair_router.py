# -*- coding: utf-8 -*-
# tests/api/test_repair_router.py
# 修复路由API测试
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock authentication模块
sys.modules["core.authentication"] = Mock()
sys.modules["core.authentication"].get_current_active_user = Mock()
sys.modules["core.authentication"].role_required = Mock()

# Mock repair相关模块
sys.modules["core.repair_engine"] = Mock()
sys.modules["core.repair_engine"].get_repair_scripts = Mock(return_value={})
sys.modules["core.repair_engine"].execute_repair = AsyncMock(return_value={"success": True})
sys.modules["core.repair_engine"].get_repair_history = Mock(return_value=[])

from api.repair_router import router  # isort: skip


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestRepairRouter:
    """修复路由测试类"""

    def test_list_scripts_success(self):
        """测试获取修复脚本列表成功"""
        with patch("api.repair_router.get_repair_scripts") as mock_scripts:
            mock_scripts.return_value = {
                "clear_temp": {"name": "清理临时文件", "risk": "low"},
                "restart_service": {"name": "重启服务", "risk": "medium"},
            }
            response = client.get("/api/v1/repairs/scripts")
            assert response.status_code == 200
            data = response.json()
            assert "scripts" in data
            assert "clear_temp" in data["scripts"]

    def test_list_scripts_exception(self):
        """测试获取修复脚本列表异常"""
        with patch("api.repair_router.get_repair_scripts") as mock_scripts:
            mock_scripts.side_effect = RuntimeError("Database error")
            response = client.get("/api/v1/repairs/scripts")
            assert response.status_code == 500

    def test_run_repair_success(self):
        """测试执行修复脚本成功"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "script_key": "clear_temp",
                "exit_code": 0,
                "output": "清理完成",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_run_repair_exception(self):
        """测试执行修复脚本异常"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.side_effect = RuntimeError("Engine error")
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 500

    def test_run_repair_none_result(self):
        """测试执行修复脚本返回None"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = None
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 500

    def test_run_repair_invalid_result_type(self):
        """测试执行修复脚本返回非dict类型"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = "invalid"
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 500

    def test_run_repair_blocked(self):
        """测试执行修复脚本被护栏拦截"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "指令被护栏拦截",
                "blocked": True,
                "safe_alternative": "安全替代方案",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 403

    def test_run_repair_blocked_no_alternative(self):
        """测试执行修复脚本被拦截无替代方案"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "指令被护栏拦截",
                "blocked": True,
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 403

    def test_run_repair_script_not_found(self):
        """测试修复脚本不存在"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "未知修复脚本",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "unknown", "params": {}}
            )
            assert response.status_code == 404

    def test_run_repair_script_not_found_english(self):
        """测试修复脚本不存在英文错误"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "script not found",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "unknown", "params": {}}
            )
            assert response.status_code == 404

    def test_run_repair_param_error(self):
        """测试修复参数校验失败"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "pid必须为数字",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "kill_process", "params": {"pid": "abc"}}
            )
            assert response.status_code == 422

    def test_run_repair_param_error_service_name(self):
        """测试修复参数错误service_name"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "缺少必要参数service_name",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "restart_service", "params": {}}
            )
            assert response.status_code == 422

    def test_run_repair_param_error_forbidden(self):
        """测试修复参数错误禁止操作"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "禁止操作",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "dangerous", "params": {}}
            )
            assert response.status_code == 422

    def test_run_repair_param_error_not_allowed(self):
        """测试修复参数错误不允许"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "不允许",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "dangerous", "params": {}}
            )
            assert response.status_code == 422

    def test_run_repair_execution_failure(self):
        """测试修复脚本执行失败"""
        with patch("api.repair_router.execute_repair") as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "error": "执行失败",
            }
            response = client.post(
                "/api/v1/repairs/execute", json={"script_key": "clear_temp", "params": {}}
            )
            assert response.status_code == 500

    def test_run_repair_missing_script_key(self):
        """测试缺少script_key参数"""
        response = client.post("/api/v1/repairs/execute", json={"params": {}})
        assert response.status_code == 422

    def test_run_repair_empty_script_key(self):
        """测试空script_key"""
        response = client.post("/api/v1/repairs/execute", json={"script_key": "", "params": {}})
        assert response.status_code == 422

    def test_run_repair_too_long_script_key(self):
        """测试超长script_key"""
        response = client.post(
            "/api/v1/repairs/execute", json={"script_key": "a" * 100, "params": {}}
        )
        assert response.status_code == 422

    def test_get_history_success(self):
        """测试获取修复历史成功"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.return_value = [
                {
                    "script_key": "clear_temp",
                    "exit_code": 0,
                    "executed_at": "2026-07-03T09:00:00Z",
                },
                {
                    "script_key": "restart_service",
                    "exit_code": 0,
                    "executed_at": "2026-07-03T10:00:00Z",
                },
            ]
            response = client.get("/api/v1/repairs/history?limit=20")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["records"]) == 2

    def test_get_history_exception(self):
        """测试获取修复历史异常"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.side_effect = RuntimeError("Database error")
            response = client.get("/api/v1/repairs/history?limit=20")
            assert response.status_code == 500

    def test_get_history_limit_below_min(self):
        """测试limit低于最小值"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.return_value = []
            response = client.get("/api/v1/repairs/history?limit=0")
            # Query validation should handle this
            assert response.status_code in [200, 422]

    def test_get_history_limit_above_max(self):
        """测试limit高于最大值"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.return_value = []
            response = client.get("/api/v1/repairs/history?limit=1000")
            # Query validation should reject limit > 500
            assert response.status_code == 422

    def test_get_history_default_limit(self):
        """测试默认limit"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.return_value = []
            response = client.get("/api/v1/repairs/history")
            assert response.status_code == 200

    def test_get_history_empty(self):
        """测试空历史记录"""
        with patch("api.repair_router.get_repair_history") as mock_history:
            mock_history.return_value = []
            response = client.get("/api/v1/repairs/history?limit=20")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["records"]) == 0
