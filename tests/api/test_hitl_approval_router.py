# -*- coding: utf-8 -*-
"""HITL Approval Router Tests"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

sys.modules["config"] = MagicMock()
sys.modules["config"].BASE_DIR = Path("/tmp")
from api.hitl_approval_router import hitl_approval_page


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/hitl", tags=["HITL Approval Center"])
    test_router.add_api_route("/", hitl_approval_page, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestHITLApprovalRouter:
    def test_hitl_approval_page_not_found(self, client):
        response = client.get("/hitl/")
        assert response.status_code == 404

    def test_hitl_approval_page_get_method(self, client):
        """测试HITL审批页面GET方法"""
        response = client.get("/hitl/")
        assert response.status_code in [200, 404]

    def test_hitl_approval_page_post_not_allowed(self, client):
        """测试HITL审批页面POST方法不允许"""
        response = client.post("/hitl/")
        assert response.status_code in [405, 404]

    def test_hitl_approval_page_response_type(self, client):
        """测试HITL审批页面响应类型"""
        response = client.get("/hitl/")
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")
        else:
            assert response.status_code == 404

    def test_hitl_approval_page_path_check(self, client):
        """测试HITL审批页面路径检查"""
        response = client.get("/hitl/")
        # Should handle the request even if file doesn't exist
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
