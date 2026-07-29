# -*- coding: utf-8 -*-
"""Guard Router Tests
高危指令管控路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.guard_router import (
    check_allowed,
    check_command,
    dryrun_command,
    get_audit,
    get_audit_stats,
    rewrite_command,
)

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].ALLOWED_LOCAL_IPS = ["127.0.0.1"]
sys.modules["config"].GUARD_DEFAULT_HOST = "localhost"
sys.modules["config"].INTERNAL_API_KEY = ""
sys.modules["config"].TRUST_PROXY_HEADER = ""
sys.modules["core.command_guard"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/guard", tags=["高危指令管控"])
    test_router.add_api_route("/check", check_command, methods=["POST"])
    test_router.add_api_route("/allowed", check_allowed, methods=["POST"])
    test_router.add_api_route("/rewrite", rewrite_command, methods=["POST"])
    test_router.add_api_route("/dryrun", dryrun_command, methods=["POST"])
    test_router.add_api_route("/audit", get_audit, methods=["GET"])
    test_router.add_api_route("/stats", get_audit_stats, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestGuardRouter:
    """测试高危指令管控路由"""

    def test_check_command(self, client):
        """测试检查命令风险等级"""
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.return_value = {
                "command": "ls -la",
                "risk_level": Mock(value="low"),
                "risk_name": "低风险",
                "reason": "安全命令",
                "action": "execute",
                "safe_alternative": "",
                "is_chained": False,
                "chain_count": 1,
            }
            with patch("api.guard_router._safe_record_audit") as mock_audit:
                mock_audit.return_value = True
                response = client.post("/api/guard/check", json={"command": "ls -la"})
                assert response.status_code == 200
                data = response.json()
                assert "risk_level" in data

    def test_check_allowed(self, client):
        """测试快速判断命令是否允许执行"""
        with patch("api.guard_router.is_command_allowed") as mock_allowed:
            mock_allowed.return_value = True
            response = client.post("/api/guard/allowed", json={"command": "ls -la"})
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is True

    def test_rewrite_command(self, client):
        """测试将高危命令改写为安全版本"""
        with patch("api.guard_router.rewrite_to_safe") as mock_rewrite:
            mock_rewrite.return_value = "mv /tmp/old_data /tmp/trash/old_data"
            response = client.post("/api/guard/rewrite", json={"command": "rm -rf /tmp/old_data"})
            assert response.status_code == 200
            data = response.json()
            assert "rewritten" in data

    def test_dryrun_command(self, client):
        """测试生成命令的Dry-run预览"""
        with patch("api.guard_router.dry_run_preview") as mock_dryrun:
            mock_dryrun.return_value = "Would delete: /tmp/cache/file1.txt"
            response = client.post("/api/guard/dryrun", json={"command": "rm -rf /tmp/cache"})
            assert response.status_code == 200
            data = response.json()
            assert "preview" in data

    def test_get_audit(self, client):
        """测试获取审计日志"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = [
                    {"command": "ls", "risk_level": "low", "executor": "local_caller"}
                ]
                response = client.get("/api/guard/audit")
                assert response.status_code == 200
                data = response.json()
                assert "logs" in data

    def test_get_audit_stats(self, client):
        """测试获取审计统计摘要"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = [
                    {"risk_level": "low"},
                    {"risk_level": "high"},
                    {"risk_level": "blocked"},
                ]
                response = client.get("/api/guard/stats")
                assert response.status_code == 200
                data = response.json()
                assert "total" in data

    def test_check_command_high_risk(self, client):
        """测试检查高危命令"""
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.return_value = {
                "command": "rm -rf /",
                "risk_level": Mock(value="critical"),
                "risk_name": "极高风险",
                "reason": "删除根目录",
                "action": "block",
                "safe_alternative": "rm -rf /tmp/trash",
                "is_chained": False,
                "chain_count": 1,
            }
            with patch("api.guard_router._safe_record_audit") as mock_audit:
                mock_audit.return_value = True
                response = client.post("/api/guard/check", json={"command": "rm -rf /"})
                assert response.status_code == 200
                data = response.json()
                assert data["risk_level"] == "critical"

    def test_check_command_blocked(self, client):
        """测试检查被拦截的命令"""
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.return_value = {
                "command": "shutdown -h now",
                "risk_level": Mock(value="critical"),
                "risk_name": "系统关机",
                "reason": "关机命令",
                "action": "block",
                "safe_alternative": "",
                "is_chained": False,
                "chain_count": 1,
            }
            with patch("api.guard_router._safe_record_audit") as mock_audit:
                mock_audit.return_value = True
                response = client.post("/api/guard/check", json={"command": "shutdown -h now"})
                assert response.status_code == 200
                data = response.json()
                assert data["action"] == "block"

    def test_check_command_chained(self, client):
        """测试检查链式命令"""
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.return_value = {
                "command": "cmd1 && cmd2 && cmd3",
                "risk_level": Mock(value="high"),
                "risk_name": "链式命令",
                "reason": "多个命令链",
                "action": "block",
                "safe_alternative": "",
                "is_chained": True,
                "chain_count": 3,
            }
            with patch("api.guard_router._safe_record_audit") as mock_audit:
                mock_audit.return_value = True
                response = client.post("/api/guard/check", json={"command": "cmd1 && cmd2 && cmd3"})
                assert response.status_code == 200
                data = response.json()
                assert data["is_chained"] is True

    def test_check_allowed_false(self, client):
        """测试不允许执行的命令"""
        with patch("api.guard_router.is_command_allowed") as mock_allowed:
            mock_allowed.return_value = False
            response = client.post("/api/guard/allowed", json={"command": "rm -rf /"})
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is False

    def test_rewrite_command_no_alternative(self, client):
        """测试无法改写的命令"""
        with patch("api.guard_router.rewrite_to_safe") as mock_rewrite:
            mock_rewrite.return_value = ""
            response = client.post("/api/guard/rewrite", json={"command": "dangerous_cmd"})
            assert response.status_code == 200
            data = response.json()
            assert data["rewritten"] == ""

    def test_dryrun_command_no_preview(self, client):
        """测试无法生成预览的命令"""
        with patch("api.guard_router.dry_run_preview") as mock_dryrun:
            mock_dryrun.return_value = ""
            response = client.post("/api/guard/dryrun", json={"command": "complex_cmd"})
            assert response.status_code == 200
            data = response.json()
            assert data["preview"] == ""

    def test_get_audit_with_filters(self, client):
        """测试带过滤条件的审计日志查询"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = [
                    {"command": "ls", "risk_level": "low", "executor": "user1"}
                ]
                response = client.get("/api/guard/audit?risk_level=low&limit=10")
                assert response.status_code == 200
                data = response.json()
                assert "logs" in data

    def test_get_audit_empty(self, client):
        """测试空审计日志"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = []
                response = client.get("/api/guard/audit")
                assert response.status_code == 200
                data = response.json()
                assert data["logs"] == []

    def test_check_command_missing_command(self, client):
        """测试缺少command参数"""
        response = client.post("/api/guard/check", json={})
        assert response.status_code == 422

    def test_check_allowed_missing_command(self, client):
        """测试检查允许时缺少command参数"""
        response = client.post("/api/guard/allowed", json={})
        assert response.status_code == 422

    def test_rewrite_command_missing_command(self, client):
        """测试改写时缺少command参数"""
        response = client.post("/api/guard/rewrite", json={})
        assert response.status_code == 422

    def test_dryrun_command_missing_command(self, client):
        """测试dryrun时缺少command参数"""
        response = client.post("/api/guard/dryrun", json={})
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
