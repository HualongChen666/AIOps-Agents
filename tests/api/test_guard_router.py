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
    _safe_record_audit,
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

    def test_check_command_missing_field(self, client):
        """测试缺少command字段"""
        response = client.post("/api/guard/check", json={})
        assert response.status_code == 422

    def test_check_allowed_false(self, client):
        """测试命令不被允许"""
        with patch("api.guard_router.is_command_allowed") as mock_allowed:
            mock_allowed.return_value = False
            response = client.post("/api/guard/allowed", json={"command": "rm -rf /"})
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is False

    def test_rewrite_command_no_alternative(self, client):
        """测试无安全替代方案"""
        with patch("api.guard_router.rewrite_to_safe") as mock_rewrite:
            mock_rewrite.return_value = ""
            response = client.post("/api/guard/rewrite", json={"command": "rm -rf /"})
            assert response.status_code == 200
            data = response.json()
            assert data["rewritten"] == ""

    def test_dryrun_command_error(self, client):
        """测试dry-run生成失败"""
        with patch("api.guard_router.dry_run_preview") as mock_dryrun:
            mock_dryrun.side_effect = RuntimeError("dry-run error")
            response = client.post("/api/guard/dryrun", json={"command": "rm -rf /"})
            assert response.status_code == 500

    def test_get_audit_empty(self, client):
        """测试空审计日志"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = []
                response = client.get("/api/guard/audit")
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 0

    def test_get_audit_stats_empty(self, client):
        """测试空审计统计"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.return_value = []
                response = client.get("/api/guard/stats")
                assert response.status_code == 200
                data = response.json()
                assert data["total"] == 0

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
                assert len(data["logs"]) == 1

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

    def test_safe_record_audit_exception(self):
        """测试审计写入异常"""
        with patch("api.guard_router.record_audit") as mock_record:
            mock_record.side_effect = RuntimeError("Database error")
            result = _safe_record_audit("localhost", "ls", "low", "local_caller", "checked")
            assert result is False

    def test_check_command_exception(self, client):
        """测试check_command异常"""
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.side_effect = RuntimeError("Analysis error")
            response = client.post("/api/guard/check", json={"command": "ls"})
            assert response.status_code == 500

    def test_check_allowed_exception(self, client):
        """测试check_allowed异常"""
        with patch("api.guard_router.is_command_allowed") as mock_allowed:
            mock_allowed.side_effect = RuntimeError("Check error")
            response = client.post("/api/guard/allowed", json={"command": "ls"})
            assert response.status_code == 500

    def test_rewrite_command_exception(self, client):
        """测试rewrite_command异常"""
        with patch("api.guard_router.rewrite_to_safe") as mock_rewrite:
            mock_rewrite.side_effect = RuntimeError("Rewrite error")
            response = client.post("/api/guard/rewrite", json={"command": "rm -rf /"})
            assert response.status_code == 500

    def test_get_audit_exception(self, client):
        """测试get_audit异常"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.side_effect = RuntimeError("Database error")
                response = client.get("/api/guard/audit")
                assert response.status_code == 500

    def test_get_audit_stats_exception(self, client):
        """测试get_audit_stats异常"""
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.side_effect = RuntimeError("Database error")
                response = client.get("/api/guard/stats")
                assert response.status_code == 500

    def test_mask_sensitive_long_command(self):
        """测试脱敏处理长命令"""
        from api.guard_router import mask_sensitive
        log = {"command": "a" * 100}
        result = mask_sensitive(log)
        assert len(result["command"]) == 53  # 50 + "..."

    def test_mask_sensitive_short_command(self):
        """测试脱敏处理短命令"""
        from api.guard_router import mask_sensitive
        log = {"command": "ls -la"}
        result = mask_sensitive(log)
        assert result["command"] == "ls -la"

    def test_mask_sensitive_no_command(self):
        """测试脱敏处理无命令"""
        from api.guard_router import mask_sensitive
        log = {"risk_level": "high"}
        result = mask_sensitive(log)
        assert "command" not in result

    def test_verify_audit_access_with_internal_key_mismatch(self):
        """测试审计接口访问权限（密钥不匹配）"""
        from api.guard_router import _verify_audit_access
        from fastapi import HTTPException, Request
        with patch("config.INTERNAL_API_KEY", "test-key"):
            request = Request(scope={"type": "http", "client": ("127.0.0.1", 1234)})
            try:
                _verify_audit_access(request, "wrong-key")
                assert False, "Should have raised HTTPException"
            except HTTPException as e:
                assert e.status_code == 403

    def test_verify_audit_access_with_internal_key_match(self):
        """测试审计接口访问权限（密钥匹配）"""
        from api.guard_router import _verify_audit_access
        from fastapi import Request
        with patch("config.INTERNAL_API_KEY", "test-key"):
            request = Request(scope={"type": "http", "client": ("127.0.0.1", 1234)})
            _verify_audit_access(request, "test-key")  # Should not raise

    def test_verify_audit_access_trust_proxy_without_key(self):
        """测试审计接口访问权限（代理场景无密钥）"""
        from api.guard_router import _verify_audit_access
        from fastapi import HTTPException, Request
        with patch("config.INTERNAL_API_KEY", ""):
            with patch("config.TRUST_PROXY_HEADER", "X-Forwarded-For"):
                request = Request(scope={"type": "http", "client": ("127.0.0.1", 1234)})
                try:
                    _verify_audit_access(request, None)
                    assert False, "Should have raised HTTPException"
                except HTTPException as e:
                    assert e.status_code == 403

    def test_verify_audit_access_remote_ip(self):
        """测试审计接口访问权限（远程IP）"""
        from api.guard_router import _verify_audit_access
        from fastapi import HTTPException, Request
        with patch("config.INTERNAL_API_KEY", ""):
            with patch("config.TRUST_PROXY_HEADER", ""):
                with patch("config.ALLOWED_LOCAL_IPS", ["127.0.0.1"]):
                    request = Request(scope={"type": "http", "client": ("192.168.1.1", 1234)})
                    try:
                        _verify_audit_access(request, None)
                        assert False, "Should have raised HTTPException"
                    except HTTPException as e:
                        assert e.status_code == 403

    def test_get_executor_info_remote_ip(self):
        """测试远程IP执行者信息提取"""
        from api.guard_router import _get_executor_info
        from fastapi import Request
        with patch("config.ALLOWED_LOCAL_IPS", ["127.0.0.1"]):
            request = Request(scope={"type": "http", "client": ("192.168.1.1", 1234)})
            executor, source_ip = _get_executor_info(request)
            assert executor == "remote@192.168.1.1"
            assert source_ip == "192.168.1.1"

    def test_check_command_with_invalid_target_host(self, client):
        """测试检查命令（无效target_host）"""
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
                response = client.post("/api/guard/check", json={"command": "ls -la", "target_host": "invalid@host#123"})
                assert response.status_code == 200

    def test_check_command_http_exception(self, client):
        """测试check_command HTTPException"""
        from fastapi import HTTPException
        with patch("api.guard_router.analyze_command") as mock_analyze:
            mock_analyze.side_effect = HTTPException(status_code=400, detail="Bad command")
            response = client.post("/api/guard/check", json={"command": "ls -la"})
            assert response.status_code == 400

    def test_get_audit_http_exception(self, client):
        """测试get_audit HTTPException"""
        from fastapi import HTTPException
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.side_effect = HTTPException(status_code=404, detail="Not found")
                response = client.get("/api/guard/audit")
                assert response.status_code == 404

    def test_get_audit_stats_http_exception(self, client):
        """测试get_audit_stats HTTPException"""
        from fastapi import HTTPException
        with patch("api.guard_router._verify_audit_access"):
            with patch("api.guard_router.get_audit_log") as mock_audit:
                mock_audit.side_effect = HTTPException(status_code=404, detail="Not found")
                response = client.get("/api/guard/stats")
                assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
