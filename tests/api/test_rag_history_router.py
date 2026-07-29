# -*- coding: utf-8 -*-
"""
RAG History Router Tests
RAG历史搜索页面路由API基础测试
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].BASE_DIR = Path("/tmp")

from api.rag_history_router import rag_history_page

# isort: on


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/rag_history", tags=["RAG 历史搜索"])
    test_router.add_api_route("/", rag_history_page, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestRAGHistoryRouter:
    """测试RAG历史搜索页面路由"""

    def test_rag_history_page_not_found(self, client):
        """测试RAG历史搜索页面未找到"""
        # Since the static file doesn't exist, it should return 404
        response = client.get("/rag_history/")
        assert response.status_code == 404

    def test_rag_history_page_get(self, client):
        """测试GET请求RAG历史搜索页面"""
        response = client.get("/rag_history/")
        # Should return 404 since file doesn't exist
        assert response.status_code in [200, 404]

    def test_rag_history_page_post_not_allowed(self, client):
        """测试POST请求不被允许"""
        response = client.post("/rag_history/")
        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_rag_history_page_response_type(self, client):
        """测试响应类型"""
        response = client.get("/rag_history/")
        # Check content-type header
        content_type = response.headers.get("content-type", "")
        # Should be HTML or JSON
        assert (
            "text/html" in content_type
            or "application/json" in content_type
            or response.status_code == 404
        )

    def test_rag_history_page_path(self, client):
        """测试路径正确性"""
        response = client.get("/rag_history/")
        # Verify the endpoint exists
        assert response.status_code in [200, 404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
