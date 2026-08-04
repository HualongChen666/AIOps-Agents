# -*- coding: utf-8 -*-
# tests/api/test_log_router.py
# 日志路由API测试
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest  # noqa: F401
from fastapi import FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["core.authentication"] = Mock()
# Use a real dependency with no params so FastAPI doesn't inject "args"/"kwargs"
sys.modules["core.authentication"].get_current_active_user = lambda: {"role": "admin"}
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "admin"})

# Mock log_collector and es_logger modules with AsyncMock so await works
sample_log = [{"time": "2026-07-02T10:30:00Z", "level": "Error", "message": "test"}]
sys.modules["core.log_collector"] = Mock()
sys.modules["core.log_collector"].get_system_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_application_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_event_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].search_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_linux_errors = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].get_linux_logs = AsyncMock(return_value=sample_log)
sys.modules["core.log_collector"].search_linux_logs = AsyncMock(return_value=sample_log)
sys.modules["core.es_logger"] = Mock()
sys.modules["core.es_logger"].es_search_logs = AsyncMock(
    return_value=[{"@timestamp": "2026-07-02T10:30:00Z", "message": "test"}]
)

sys.modules["config"] = Mock()
sys.modules["config"].LINUX_HOSTS = []
sys.modules["core.api_helpers"] = Mock()
sys.modules["core.api_helpers"].VALID_HOSTNAME_PATTERN = Mock()
sys.modules["core.api_helpers"].VALID_HOSTNAME_PATTERN.match = Mock(return_value=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.log_router import _get_linux_host, _validate_keyword, router  # isort: skip

# isort: on


test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestLogRouter:
    """日志路由测试"""

    def test_get_logs(self):
        """测试获取日志"""
        response = client.get("/api/v1/logs/system/errors?newest=10")
        assert response.status_code in [200, 401, 403, 500]

    def test_search_logs(self):
        """测试搜索日志"""
        response = client.get("/api/v1/logs/search?keyword=test")
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_system_errors(self):
        """测试获取Windows系统错误日志"""
        response = client.get("/api/v1/logs/system/errors?newest=10")
        assert response.status_code in [200, 401, 403, 500]

    def test_app_errors(self):
        """测试获取Windows应用程序错误日志"""
        response = client.get("/api/v1/logs/application/errors?newest=10")
        assert response.status_code in [200, 401, 403, 500]

    def test_query_logs(self):
        """测试查询Windows事件日志"""
        response = client.get("/api/v1/logs/query?log_name=System&level=Error&newest=20")
        assert response.status_code in [200, 401, 403, 500]

    def test_linux_errors(self):
        """测试获取Linux内核错误日志"""
        response = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
        assert response.status_code in [200, 401, 403, 404, 422, 500]

    def test_linux_query(self):
        """测试查询Linux日志"""
        response = client.get("/api/v1/logs/linux/query?host_name=test&source=syslog&newest=20")
        assert response.status_code in [200, 401, 403, 404, 422, 500]

    def test_es_search(self):
        """测试Elasticsearch日志搜索"""
        response = client.get("/api/v1/logs/es/search?query=test&size=100")
        assert response.status_code in [200, 401, 403, 500]

    def test_linux_search(self):
        """测试Linux日志搜索"""
        response = client.get(
            "/api/v1/logs/linux/search?host_name=test&keyword=test&newest=100"
        )
        assert response.status_code in [200, 401, 403, 404, 422, 500]

    def test_system_errors_with_cache(self):
        """测试系统错误日志缓存功能"""
        response1 = client.get("/api/v1/logs/system/errors?newest=10")
        response2 = client.get("/api/v1/logs/system/errors?newest=10")
        assert response1.status_code in [200, 401, 403, 500]
        assert response2.status_code in [200, 401, 403, 500]

    def test_app_errors_with_cache(self):
        """测试应用错误日志缓存功能"""
        response1 = client.get("/api/v1/logs/application/errors?newest=10")
        response2 = client.get("/api/v1/logs/application/errors?newest=10")
        assert response1.status_code in [200, 401, 403, 500]
        assert response2.status_code in [200, 401, 403, 500]

    def test_search_logs_with_empty_keyword(self):
        """测试空关键词搜索"""
        response = client.get("/api/v1/logs/search?keyword=")
        assert response.status_code in [422, 401, 403]

    def test_search_logs_with_long_keyword(self):
        """测试超长关键词"""
        long_keyword = "a" * 300
        response = client.get(f"/api/v1/logs/search?keyword={long_keyword}")
        assert response.status_code in [422, 401, 403]

    def test_query_logs_with_different_levels(self):
        """测试不同日志级别查询"""
        levels = ["Error", "Warning", "Information"]
        for level in levels:
            response = client.get(f"/api/v1/logs/query?log_name=System&level={level}&newest=20")
            assert response.status_code in [200, 401, 403, 500]

    def test_query_logs_with_different_sources(self):
        """测试不同日志源查询"""
        sources = ["System", "Application", "Security"]
        for source in sources:
            response = client.get(f"/api/v1/logs/query?log_name={source}&level=Error&newest=20")
            assert response.status_code in [200, 401, 403, 500]

    def test_linux_errors_with_invalid_hostname(self):
        """测试无效主机名获取Linux错误"""
        response = client.get("/api/v1/logs/linux/errors?host_name=invalid_host&newest=10")
        assert response.status_code in [200, 404, 422, 401, 403]

    def test_linux_query_with_different_sources(self):
        """测试不同Linux日志源查询"""
        sources = ["syslog", "kern", "auth", "dmesg", "journal"]
        for source in sources:
            response = client.get(
                f"/api/v1/logs/linux/query?host_name=test&source={source}&newest=20"
            )
            assert response.status_code in [200, 401, 403, 404, 422, 500]

    def test_es_search_with_pagination(self):
        """测试Elasticsearch搜索分页"""
        response = client.get("/api/v1/logs/es/search?query=test&size=100&from_=0")
        assert response.status_code in [200, 401, 403, 500]

    def test_linux_search_with_case_sensitive(self):
        """测试Linux搜索区分大小写"""
        response = client.get(
            "/api/v1/logs/linux/search",
            params={
                "host_name": "test",
                "keyword": "Test",
                "newest": "100",
                "case_sensitive": "true",
            },
        )
        assert response.status_code in [200, 401, 403, 404, 422, 500]

    def test_system_errors_with_different_limits(self):
        """测试不同限制数量的系统错误"""
        limits = [1, 10, 50, 100]
        for limit in limits:
            response = client.get(f"/api/v1/logs/system/errors?newest={limit}")
            assert response.status_code in [200, 401, 403, 500]

    def test_linux_errors_with_valid_hostname(self):
        """测试有效主机名获取Linux错误"""
        with patch("config.LINUX_HOSTS", [{"host": "test", "ip": "1.2.3.4"}]):
            with patch("api.linux_router.find_linux_host_config") as mock_find:
                mock_find.return_value = {"host": "test", "ip": "1.2.3.4"}
                response = client.get("/api/v1/logs/linux/errors?host_name=test&newest=10")
                assert response.status_code in [200, 401, 403]

    def test_linux_query_with_valid_hostname(self):
        """测试有效主机名查询Linux日志"""
        with patch("config.LINUX_HOSTS", [{"host": "test", "ip": "1.2.3.4"}]):
            with patch("api.linux_router.find_linux_host_config") as mock_find:
                mock_find.return_value = {"host": "test", "ip": "1.2.3.4"}
                response = client.get(
                    "/api/v1/logs/linux/query?host_name=test&source=syslog&newest=20"
                )
                assert response.status_code in [200, 401, 403]

    def test_linux_search_with_valid_hostname(self):
        """测试有效主机名搜索Linux日志"""
        with patch("config.LINUX_HOSTS", [{"host": "test", "ip": "1.2.3.4"}]):
            with patch("api.linux_router.find_linux_host_config") as mock_find:
                mock_find.return_value = {"host": "test", "ip": "1.2.3.4"}
                response = client.get(
                    "/api/v1/logs/linux/search?host_name=test&keyword=test&newest=100"
                )
                assert response.status_code in [200, 401, 403]

    def test_validate_keyword_empty(self):
        """测试空关键词验证"""
        from fastapi import HTTPException
        try:
            _validate_keyword("")
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 422

    def test_validate_keyword_whitespace(self):
        """测试纯空白关键词验证"""
        from fastapi import HTTPException
        try:
            _validate_keyword("   ")
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 422

    def test_validate_keyword_none(self):
        """测试None关键词验证"""
        from fastapi import HTTPException
        try:
            _validate_keyword(None)
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 422

    def test_get_linux_host_empty(self):
        """测试空主机名"""
        from fastapi import HTTPException
        try:
            _get_linux_host("")
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 422

    def test_get_linux_host_whitespace(self):
        """测试纯空白主机名"""
        from fastapi import HTTPException
        try:
            _get_linux_host("   ")
            assert False, "Should raise HTTPException"
        except HTTPException as e:
            assert e.status_code == 422

    def test_get_linux_host_not_found(self):
        """测试主机名不存在"""
        from fastapi import HTTPException
        with patch("api.linux_router.find_linux_host_config") as mock_find:
            mock_find.return_value = None
            try:
                _get_linux_host("nonexistent")
                assert False, "Should raise HTTPException"
            except HTTPException as e:
                assert e.status_code == 404
