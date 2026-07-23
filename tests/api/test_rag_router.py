# -*- coding: utf-8 -*-
"""
RAG Router Tests
RAG语义搜索路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].role_required = Mock(return_value=lambda: {"role": "user"})
sys.modules["core.rag_engine"] = MagicMock()

from api.rag_router import rag_search


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])
    test_router.add_api_route("/search", rag_search, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestRAGRouter:
    """测试RAG语义搜索路由"""

    def test_rag_search_success(self, client):
        """测试成功进行RAG搜索"""
        with patch("api.rag_router.search_similar") as mock_search:
            mock_search.return_value = [
                {"content": "test result 1", "score": 0.95},
                {"content": "test result 2", "score": 0.85},
            ]

            response = client.post("/api/v1/rag/search", json={"query": "test query", "top_k": 5})
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_rag_search_empty_query(self, client):
        """测试空查询"""
        response = client.post("/api/v1/rag/search", json={"query": "   ", "top_k": 5})
        assert response.status_code == 400

    def test_rag_search_with_default_top_k(self, client):
        """测试使用默认top_k值"""
        with patch("api.rag_router.search_similar") as mock_search:
            mock_search.return_value = [{"content": "test result", "score": 0.9}]
            response = client.post("/api/v1/rag/search", json={"query": "test query"})
            assert response.status_code == 200

    def test_rag_search_no_results(self, client):
        """测试无搜索结果"""
        with patch("api.rag_router.search_similar") as mock_search:
            mock_search.return_value = []
            response = client.post("/api/v1/rag/search", json={"query": "test query", "top_k": 5})
            assert response.status_code == 200
            data = response.json()
            assert data == []

    def test_rag_search_large_top_k(self, client):
        """测试大top_k值"""
        with patch("api.rag_router.search_similar") as mock_search:
            mock_search.return_value = [{"content": f"result {i}", "score": 0.9} for i in range(20)]
            response = client.post("/api/v1/rag/search", json={"query": "test query", "top_k": 20})
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 20

    def test_rag_search_special_characters(self, client):
        """测试特殊字符查询"""
        with patch("api.rag_router.search_similar") as mock_search:
            mock_search.return_value = [{"content": "test result", "score": 0.9}]
            response = client.post(
                "/api/v1/rag/search", json={"query": "test @#$%^&*() query", "top_k": 5}
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
