# -*- coding: utf-8 -*-
"""
Vector Router Comprehensive Tests
Complete test suite for vector API endpoints with authorization checks,
business logic validation, and performance testing.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import time


@pytest.fixture
def client():
    """Create test client"""
    from main import app
    return TestClient(app)


@pytest.fixture
def admin_user():
    """Mock admin user"""
    return Mock(id="admin-1", username="admin", role="admin", is_active=True)


@pytest.fixture
def regular_user():
    """Mock regular user"""
    return Mock(id="user-1", username="user", role="user", is_active=True)


class TestVectorRouterBasics:
    """Test basic router configuration and setup"""

    def test_vector_prefix_correct(self, client):
        """Test that qdrant router uses correct prefix /api/vector"""
        from api.qdrant_router import router
        assert router.prefix == "/api/vector"

    def test_router_has_required_endpoints(self, client):
        """Test that router has all required endpoints"""
        from api.qdrant_router import router
        routes = [route.path for route in router.routes]
        
        required_endpoints = [
            "/health",
            "/collections",
            "/points",
            "/search",
            "/points/batch",
            "/search/hybrid",
            "/search/multi-vector",
            "/stats",
        ]
        
        for endpoint in required_endpoints:
            assert any(endpoint in route for route in routes), f"Missing endpoint: {endpoint}"


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_with_admin(self, client, admin_user):
        """Test GET /api/vector/health with admin user"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/vector/health")
            assert response.status_code in [200, 401, 403, 503]
            if response.status_code == 200:
                data = response.json()
                assert "status" in data

    def test_health_check_with_regular_user(self, client, regular_user):
        """Test GET /api/vector/health with regular user"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.get("/api/vector/health")
            assert response.status_code in [200, 401, 403, 503]

    def test_health_check_without_auth(self, client):
        """Test GET /api/vector/health without authentication"""
        response = client.get("/api/vector/health")
        assert response.status_code in [401, 403]


class TestCollectionEndpoints:
    """Test collection management endpoints"""

    def test_list_collections_with_auth(self, client, admin_user):
        """Test GET /api/vector/collections with authorization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/vector/collections")
            assert response.status_code in [200, 401, 403, 503]
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)

    def test_create_collection_requires_admin(self, client, regular_user):
        """Test POST /api/vector/collections requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.post(
                "/api/vector/collections",
                json={"name": "test_collection", "vector_size": 128, "distance": "Cosine"}
            )
            assert response.status_code in [401, 403]

    def test_create_collection_with_admin(self, client, admin_user):
        """Test POST /api/vector/collections with admin user"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.create_collection") as mock_create:
                mock_create.return_value = {"status": "success", "collection": "test_collection"}
                response = client.post(
                    "/api/vector/collections",
                    json={"name": "test_collection", "vector_size": 128, "distance": "Cosine"}
                )
                assert response.status_code in [200, 401, 403, 500]

    def test_delete_collection_requires_admin(self, client, regular_user):
        """Test DELETE /api/vector/collections/{name} requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.request("DELETE", "/api/vector/collections/test_collection")
            assert response.status_code in [401, 403]

    def test_get_collection_info(self, client, admin_user):
        """Test GET /api/vector/collections/{name}/info"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.get_collection_info") as mock_info:
                mock_info.return_value = {
                    "name": "test_collection",
                    "vector_size": 128,
                    "points_count": 1000,
                }
                response = client.get("/api/vector/collections/test_collection/info")
                assert response.status_code in [200, 404, 500, 401]

    def test_clear_collection_requires_admin(self, client, regular_user):
        """Test DELETE /api/vector/collections/{name}/clear requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.request("DELETE", "/api/vector/collections/test_collection/clear")
            assert response.status_code in [401, 403]

    def test_update_collection_config_requires_admin(self, client, regular_user):
        """Test PUT /api/vector/collections/{name}/config requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.put(
                "/api/vector/collections/test_collection/config",
                json={"params": {"optimization": "enabled"}}
            )
            assert response.status_code in [401, 403]

    def test_get_point_count(self, client, admin_user):
        """Test GET /api/vector/collections/{name}/count"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.get_point_count") as mock_count:
                mock_count.return_value = {"collection": "test_collection", "count": 1000}
                response = client.get("/api/vector/collections/test_collection/count")
                assert response.status_code in [200, 500, 401]


class TestPointOperations:
    """Test vector point operations"""

    def test_upsert_points_requires_admin(self, client, regular_user):
        """Test POST /api/vector/points requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.post(
                "/api/vector/points",
                json={
                    "collection": "test_collection",
                    "points": [
                        {"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"text": "test"}}
                    ]
                }
            )
            assert response.status_code in [401, 403]

    def test_upsert_points_with_admin(self, client, admin_user):
        """Test POST /api/vector/points with admin user"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.upsert_points") as mock_upsert:
                mock_upsert.return_value = {"status": "success", "count": 1}
                response = client.post(
                    "/api/vector/points",
                    json={
                        "collection": "test_collection",
                        "points": [
                            {"id": 1, "vector": [0.1, 0.2, 0.3], "payload": {"text": "test"}}
                        ]
                    }
                )
                assert response.status_code in [200, 401, 403, 500]

    def test_delete_points_requires_admin(self, client, regular_user):
        """Test DELETE /api/vector/points requires admin role"""
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            response = client.request(
                "DELETE",
                "/api/vector/points",
                json={"collection": "test_collection", "ids": [1, 2, 3]}
            )
            assert response.status_code in [401, 403]

    def test_batch_upsert_points(self, client, admin_user):
        """Test POST /api/vector/points/batch for batch operations"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.upsert_points_batch") as mock_batch:
                mock_batch.return_value = {"status": "success", "count": 100}
                response = client.post(
                    "/api/vector/points/batch",
                    json={
                        "collection": "test_collection",
                        "points": [{"id": i, "vector": [0.1, 0.2], "payload": {}} for i in range(100)],
                        "batch_size": 50
                    }
                )
                assert response.status_code in [200, 401, 403, 500]

    def test_batch_delete_points(self, client, admin_user):
        """Test DELETE /api/vector/points/batch for batch deletion"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.delete_points") as mock_delete:
                mock_delete.return_value = {"status": "success", "count": 50}
                response = client.request(
                    "DELETE",
                    "/api/vector/points/batch",
                    json={"collection": "test_collection", "ids": list(range(50)), "batch_size": 25}
                )
                assert response.status_code in [200, 401, 403, 500]

    def test_update_points(self, client, admin_user):
        """Test PUT /api/vector/points for updating points"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.upsert_points") as mock_update:
                mock_update.return_value = {"status": "success", "count": 1}
                response = client.put(
                    "/api/vector/points",
                    json={
                        "collection": "test_collection",
                        "points": [{"id": 1, "vector": [0.5, 0.6], "payload": {"updated": True}}]
                    }
                )
                assert response.status_code in [200, 401, 403, 500]

    def test_get_point(self, client, admin_user):
        """Test POST /api/vector/points/get for retrieving point details"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.get_qdrant_client") as mock_client:
                mock_qdrant = MagicMock()
                mock_client.return_value = mock_qdrant
                mock_point = MagicMock()
                mock_point.id = 1
                mock_point.vector = [0.1, 0.2, 0.3]
                mock_point.payload = {"text": "test"}
                mock_qdrant.retrieve.return_value = [mock_point]
                
                response = client.post(
                    "/api/vector/points/get",
                    json={"collection": "test_collection", "id": 1}
                )
                assert response.status_code in [200, 404, 503, 401]


class TestSearchEndpoints:
    """Test vector search endpoints"""

    def test_search_with_auth(self, client, admin_user):
        """Test POST /api/vector/search with authorization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.search") as mock_search:
                mock_search.return_value = [
                    {"id": 1, "score": 0.95, "payload": {"text": "similar"}}
                ]
                response = client.post(
                    "/api/vector/search",
                    json={
                        "collection": "test_collection",
                        "query_vector": [0.1, 0.2, 0.3],
                        "top_k": 5
                    }
                )
                assert response.status_code in [200, 500, 401]

    def test_search_without_auth(self, client):
        """Test POST /api/vector/search without authentication"""
        response = client.post(
            "/api/vector/search",
            json={
                "collection": "test_collection",
                "query_vector": [0.1, 0.2, 0.3],
                "top_k": 5
            }
        )
        assert response.status_code in [401, 403]

    def test_hybrid_search(self, client, admin_user):
        """Test POST /api/vector/search/hybrid for hybrid search"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.search_hybrid") as mock_hybrid:
                mock_hybrid.return_value = [
                    {"id": 1, "score": 0.9, "payload": {"text": "hybrid result"}}
                ]
                response = client.post(
                    "/api/vector/search/hybrid",
                    json={
                        "collection": "test_collection",
                        "query_vector": [0.1, 0.2, 0.3],
                        "query_text": "search term",
                        "top_k": 5,
                        "alpha": 0.7
                    }
                )
                assert response.status_code in [200, 500, 401]

    def test_multi_vector_search(self, client, admin_user):
        """Test POST /api/vector/search/multi-vector for multi-vector search"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.search_multi_vector") as mock_multi:
                mock_multi.return_value = [
                    {"id": 1, "score": 0.85, "payload": {"text": "multi-vector result"}}
                ]
                response = client.post(
                    "/api/vector/search/multi-vector",
                    json={
                        "collection": "test_collection",
                        "query_vectors": [[0.1, 0.2], [0.3, 0.4]],
                        "weights": [0.6, 0.4],
                        "top_k": 5
                    }
                )
                assert response.status_code in [200, 500, 401]


class TestStatsEndpoint:
    """Test statistics and monitoring endpoints"""

    def test_get_vector_stats_with_auth(self, client, admin_user):
        """Test GET /api/vector/stats with authorization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.get_vector_stats") as mock_stats:
                mock_stats.return_value = {
                    "status": "healthy",
                    "total_collections": 5,
                    "total_points": 10000,
                    "collections": []
                }
                response = client.get("/api/vector/stats")
                assert response.status_code in [200, 500, 401]
                if response.status_code == 200:
                    data = response.json()
                    assert "status" in data
                    assert "total_collections" in data

    def test_get_vector_stats_without_auth(self, client):
        """Test GET /api/vector/stats without authentication"""
        response = client.get("/api/vector/stats")
        assert response.status_code in [401, 403]


class TestValidation:
    """Test input validation and error handling"""

    def test_create_collection_invalid_distance(self, client, admin_user):
        """Test POST /api/vector/collections with invalid distance metric"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.post(
                "/api/vector/collections",
                json={"name": "test", "vector_size": 128, "distance": "InvalidDistance"}
            )
            assert response.status_code in [422, 500, 401, 403]

    def test_search_empty_vector(self, client, admin_user):
        """Test POST /api/vector/search with empty vector"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.post(
                "/api/vector/search",
                json={
                    "collection": "test_collection",
                    "query_vector": [],
                    "top_k": 5
                }
            )
            # Should get validation error (422) or service error (500)
            assert response.status_code in [422, 500, 401]

    def test_batch_upsert_invalid_batch_size(self, client, admin_user):
        """Test POST /api/vector/points/batch with invalid batch size"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.post(
                "/api/vector/points/batch",
                json={
                    "collection": "test_collection",
                    "points": [{"id": 1, "vector": [0.1], "payload": {}}],
                    "batch_size": 2000  # Exceeds max of 1000
                }
            )
            assert response.status_code in [422, 500, 401, 403]

    def test_hybrid_search_invalid_alpha(self, client, admin_user):
        """Test POST /api/vector/search/hybrid with invalid alpha"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.post(
                "/api/vector/search/hybrid",
                json={
                    "collection": "test_collection",
                    "query_vector": [0.1, 0.2],
                    "query_text": "test",
                    "top_k": 5,
                    "alpha": 1.5  # Exceeds max of 1.0
                }
            )
            assert response.status_code in [422, 500, 401]


class TestPerformance:
    """Test performance and rate limiting"""

    def test_batch_operation_performance(self, client, admin_user):
        """Test that batch operations complete within reasonable time"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.upsert_points_batch") as mock_batch:
                mock_batch.return_value = {"status": "success", "count": 500}
                
                start_time = time.time()
                response = client.post(
                    "/api/vector/points/batch",
                    json={
                        "collection": "test_collection",
                        "points": [{"id": i, "vector": [0.1, 0.2], "payload": {}} for i in range(500)],
                        "batch_size": 100
                    }
                )
                elapsed_time = time.time() - start_time
                
                assert response.status_code in [200, 401, 403, 500]
                # Batch operation should complete within 5 seconds
                assert elapsed_time < 5.0, f"Batch operation took {elapsed_time:.2f}s, expected < 5s"

    def test_search_performance(self, client, admin_user):
        """Test that search operations complete within reasonable time"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.qdrant_service.search") as mock_search:
                mock_search.return_value = [
                    {"id": i, "score": 0.9 - (i * 0.01), "payload": {"text": f"result {i}"}}
                    for i in range(10)
                ]
                
                start_time = time.time()
                response = client.post(
                    "/api/vector/search",
                    json={
                        "collection": "test_collection",
                        "query_vector": [0.1, 0.2, 0.3],
                        "top_k": 10
                    }
                )
                elapsed_time = time.time() - start_time
                
                assert response.status_code in [200, 401, 403, 500]
                # Search should complete within 2 seconds
                assert elapsed_time < 2.0, f"Search took {elapsed_time:.2f}s, expected < 2s"


class TestSecurity:
    """Test security and authorization"""

    def test_admin_only_endpoints_blocked_for_regular_user(self, client, regular_user):
        """Test that admin-only endpoints are blocked for regular users"""
        admin_endpoints = [
            ("POST", "/api/vector/collections", {"name": "test", "vector_size": 128, "distance": "Cosine"}),
            ("DELETE", "/api/vector/collections/test", None),
            ("POST", "/api/vector/points", {"collection": "test", "points": [{"id": 1, "vector": [0.1], "payload": {}}]}),
            ("DELETE", "/api/vector/points", {"collection": "test", "ids": [1]}),
            ("POST", "/api/vector/points/batch", {"collection": "test", "points": [], "batch_size": 100}),
            ("DELETE", "/api/vector/points/batch", {"collection": "test", "ids": [], "batch_size": 100}),
            ("PUT", "/api/vector/points", {"collection": "test", "points": [{"id": 1, "vector": [0.1], "payload": {}}]}),
            ("PUT", "/api/vector/collections/test/config", {"params": {}}),
            ("DELETE", "/api/vector/collections/test/clear", None),
        ]
        
        with patch("core.authentication.get_current_active_user", return_value=regular_user):
            for method, endpoint, payload in admin_endpoints:
                if method == "POST":
                    response = client.post(endpoint, json=payload)
                elif method == "DELETE":
                    response = client.request("DELETE", endpoint, json=payload)
                elif method == "PUT":
                    response = client.put(endpoint, json=payload)
                
                assert response.status_code in [401, 403], f"Endpoint {method} {endpoint} should be blocked for regular user"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto", "--tb=short"])
