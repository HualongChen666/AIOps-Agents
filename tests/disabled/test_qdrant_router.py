# -*- coding: utf-8 -*-
"""
Qdrant Router Tests
测试Qdrant向量数据库路由API
"""

import os
import sys
from datetime import datetime  # noqa: F401
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.qdrant_router import router

# 完全禁用配置加载
os.environ.setdefault("AIOPS_SKIP_CONFIG", "true")

# Mock依赖模块以避免导入问题（必须在导入路由之前）
sys.modules["core.config"] = MagicMock()
sys.modules["core.qdrant_service"] = MagicMock()
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.key_management_service"] = MagicMock()


class TestQdrantRouter:
    """测试Qdrant路由"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_auth(self):
        """模拟认证"""
        with patch("core.authentication.get_current_active_user") as mock:
            mock.return_value = Mock(username="test_user", role="admin")
            yield mock

    def test_list_collections_success(self, client, mock_auth):
        """测试获取集合列表成功"""
        with patch("core.qdrant_service.list_collections") as mock_list:
            mock_list.return_value = {
                "collections": [{"name": "test_collection", "vectors_count": 1000}],
                "total": 1,
            }

            response = client.get(
                "/api/qdrant/collections", headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "collections" in data

    def test_create_collection_success(self, client, mock_auth):
        """测试创建集合成功"""
        collection_data = {"name": "test_collection", "vector_size": 1536, "distance": "Cosine"}

        with patch("core.qdrant_service.create_collection") as mock_create:
            mock_create.return_value = {"name": "test_collection", "status": "created"}

            response = client.post(
                "/api/qdrant/collections",
                json=collection_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "created"

    def test_delete_collection_success(self, client, mock_auth):
        """测试删除集合成功"""
        collection_name = "test_collection"
        with patch("core.qdrant_service.delete_collection") as mock_delete:
            mock_delete.return_value = {"name": collection_name, "deleted": True}

            response = client.delete(
                f"/api/qdrant/collections/{collection_name}",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True

    def test_upsert_points_success(self, client, mock_auth):
        """测试插入向量点成功"""
        points_data = {
            "collection": "test_collection",
            "points": [{"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"text": "test"}}],
        }

        with patch("core.qdrant_service.upsert_points") as mock_upsert:
            mock_upsert.return_value = {"upserted_count": 1, "status": "completed"}

            response = client.post(
                "/api/qdrant/points/upsert",
                json=points_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["upserted_count"] == 1

    def test_search_points_success(self, client, mock_auth):
        """测试向量搜索成功"""
        search_data = {
            "collection": "test_collection",
            "query_vector": [0.1, 0.2, 0.3],
            "limit": 10,
        }

        with patch("core.qdrant_service.search") as mock_search:
            mock_search.return_value = {
                "results": [{"id": 1, "score": 0.95, "payload": {"text": "test"}}],
                "total": 1,
            }

            response = client.post(
                "/api/qdrant/search",
                json=search_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    def test_delete_points_success(self, client, mock_auth):
        """测试删除向量点成功"""
        points_data = {"collection": "test_collection", "points": [1, 2, 3]}

        with patch("core.qdrant_service.delete_points") as mock_delete:
            mock_delete.return_value = {"deleted_count": 3, "status": "completed"}

            response = client.post(
                "/api/qdrant/points/delete",
                json=points_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["deleted_count"] == 3

    def test_collection_info_success(self, client, mock_auth):
        """测试获取集合信息成功"""
        collection_name = "test_collection"
        with patch("core.qdrant_service.get_collection_info") as mock_info:
            mock_info.return_value = {
                "name": collection_name,
                "vectors_count": 1000,
                "status": "green",
            }

            response = client.get(
                f"/api/qdrant/collections/{collection_name}",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["vectors_count"] == 1000

    def test_health_check_success(self, client, mock_auth):
        """测试健康检查成功"""
        with patch("core.qdrant_service.health_check") as mock_health:
            mock_health.return_value = {"status": "healthy", "version": "1.0.0"}

            response = client.get(
                "/api/qdrant/health", headers={"Authorization": "Bearer test_token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_batch_search_success(self, client, mock_auth):
        """测试批量搜索成功"""
        batch_data = {
            "collection": "test_collection",
            "query_vectors": [[0.1, 0.2], [0.3, 0.4]],
            "limit": 5,
        }

        with patch("core.qdrant_service.batch_search") as mock_batch:
            mock_batch.return_value = {
                "results": [[{"id": 1, "score": 0.9}], [{"id": 2, "score": 0.8}]],
                "total": 2,
            }

            response = client.post(
                "/api/qdrant/batch-search",
                json=batch_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2

    def test_scroll_points_success(self, client, mock_auth):
        """测试滚动获取向量点成功"""
        scroll_data = {"collection": "test_collection", "limit": 100, "offset": None}

        with patch("core.qdrant_service.scroll_points") as mock_scroll:
            mock_scroll.return_value = {
                "points": [{"id": 1, "vector": [0.1, 0.2]}],
                "total": 1,
                "next_page_offset": None,
            }

            response = client.post(
                "/api/qdrant/scroll",
                json=scroll_data,
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "points" in data

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/qdrant/collections")
        assert response.status_code == 401

    def test_invalid_vector_data(self, client, mock_auth):
        """测试无效向量数据"""
        invalid_data = {
            "collection": "test_collection",
            "points": [{"id": 1, "vector": "not_a_vector"}],
        }

        response = client.post(
            "/api/qdrant/points/upsert",
            json=invalid_data,
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422  # Validation error

    def test_collection_not_found(self, client, mock_auth):
        """测试集合不存在"""
        with patch("core.qdrant_service.get_collection_info") as mock_info:
            mock_info.return_value = None

            response = client.get(
                "/api/qdrant/collections/nonexistent",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 404
