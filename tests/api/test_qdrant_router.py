# -*- coding: utf-8 -*-
"""Qdrant Router Tests"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].get_current_active_user = lambda: {
    "username": "testuser",
    "role": "user",
}
sys.modules["core.authentication"].role_required = lambda role: lambda: {
    "username": "testuser",
    "role": role,
}
sys.modules["core.qdrant_service"] = MagicMock()

from api.qdrant_router import router  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestQdrantRouter:
    def test_health(self, client):
        with patch(
            "api.qdrant_router.health_check", return_value={"status": "healthy", "version": "1.7.0"}
        ):
            response = client.get("/api/qdrant/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_get_collections(self, client):
        with patch(
            "api.qdrant_router.list_collections",
            return_value=[{"name": "test_collection", "vector_size": 768, "points_count": 1000}],
        ):
            response = client.get("/api/qdrant/collections")
            assert response.status_code == 200
            assert response.json()[0]["name"] == "test_collection"

    def test_create_collection(self, client):
        with patch(
            "api.qdrant_router.create_collection",
            return_value={"status": "success", "collection_name": "test_collection"},
        ):
            response = client.post(
                "/api/qdrant/collections",
                json={"name": "test_collection", "vector_size": 768, "distance": "Cosine"},
            )
            assert response.status_code == 200

    def test_delete_collection(self, client):
        with patch(
            "api.qdrant_router.delete_collection",
            return_value={"status": "success", "collection_name": "test_collection"},
        ):
            response = client.delete("/api/qdrant/collections/test_collection")
            assert response.status_code == 200

    def test_upsert_points(self, client):
        with patch(
            "api.qdrant_router.upsert_points",
            return_value={"status": "success", "upserted_count": 1},
        ):
            response = client.post(
                "/api/qdrant/points",
                json={
                    "collection": "test_collection",
                    "points": [{"id": 1, "vector": [1.0], "payload": {}}],
                },
            )
            assert response.status_code == 200

    def test_search(self, client):
        with patch(
            "api.qdrant_router.search",
            return_value=[{"id": 1, "score": 0.95, "payload": {}}],
        ):
            response = client.post(
                "/api/qdrant/search",
                json={"collection": "test_collection", "query_vector": [1.0], "top_k": 5},
            )
            assert response.status_code == 200

    def test_delete_points(self, client):
        with patch(
            "api.qdrant_router.delete_points",
            return_value={"status": "success"},
        ):
            response = client.request(
                "DELETE",
                "/api/qdrant/points",
                json={"collection": "test_collection", "ids": [1]},
            )
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
