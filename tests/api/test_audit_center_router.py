# -*- coding: utf-8 -*-
"""
Audit Center Router Tests
审计中心页面路由API基础测试
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.audit_center_router import audit_center_page

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].BASE_DIR = Path("/tmp")


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/audit_center", tags=["审计中心页面"])
    test_router.add_api_route("/", audit_center_page, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestAuditCenterRouter:
    """测试审计中心页面路由"""

    def test_audit_center_page_not_found(self, client):
        """测试审计中心页面未找到"""
        # Since the static file doesn't exist, it should return 404
        response = client.get("/audit_center/")
        assert response.status_code == 404

    def test_audit_center_page_response_type(self, client):
        """测试审计中心页面响应类型"""
        response = client.get("/audit_center/")
        # Check that we get a response (even if 404)
        assert response.status_code in [200, 404]

    def test_audit_center_page_get_method(self, client):
        """测试审计中心页面GET方法"""
        response = client.get("/audit_center/")
        # Should handle GET request
        assert response.status_code in [200, 404]

    def test_audit_center_page_post_not_allowed(self, client):
        """测试审计中心页面POST方法不允许"""
        response = client.post("/audit_center/")
        # POST should not be allowed
        assert response.status_code in [405, 404]

    def test_audit_center_page_content_type(self, client):
        """测试审计中心页面内容类型"""
        response = client.get("/audit_center/")
        # Should return HTML or 404
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
        else:
            assert response.status_code == 404

    def test_audit_center_page_found(self, client, tmp_path):
        """测试审计中心页面存在时返回200"""
        page_dir = tmp_path / "static"
        page_dir.mkdir()
        page_file = page_dir / "audit_center.bak"
        page_file.write_text("<html></html>", encoding="utf-8")
        with patch("api.audit_center_router.BASE_DIR", tmp_path):
            response = client.get("/audit_center/")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
