# -*- coding: utf-8 -*-
"""Plugin Marketplace Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.plugin_marketplace_router import (
    add_plugin_review,
    approve_plugin,
    download_plugin,
    get_marketplace_status,
    get_plugin_listings,
    publish_plugin,
    reject_plugin,
)

sys.modules["core.plugin_marketplace_manager"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/plugin-marketplace", tags=["Plugin Marketplace"])
    test_router.add_api_route("/status", get_marketplace_status, methods=["GET"])
    test_router.add_api_route("/publish", publish_plugin, methods=["POST"])
    test_router.add_api_route("/plugin/{plugin_id}/approve", approve_plugin, methods=["POST"])
    test_router.add_api_route("/plugin/{plugin_id}/reject", reject_plugin, methods=["POST"])
    test_router.add_api_route("/plugin/{plugin_id}/download", download_plugin, methods=["POST"])
    test_router.add_api_route("/listings", get_plugin_listings, methods=["GET"])
    test_router.add_api_route("/plugin/{plugin_id}/review", add_plugin_review, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestPluginMarketplaceRouter:
    def test_get_marketplace_status(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_marketplace_summary.return_value = {
                "total_plugins": 50,
                "published_plugins": 40,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-marketplace/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_marketplace_status_error(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_manager.side_effect = Exception("plugin marketplace error")
            response = client.get("/api/plugin-marketplace/status")
            assert response.status_code == 500

    def test_publish_plugin(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.publish_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/publish",
                params={
                    "plugin_id": "plugin-123",
                    "plugin_name": "TestPlugin",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "TestAuthor",
                    "plugin_code": "code",
                    "quality": "community",
                },
                json={"config": {}},
            )
            assert response.status_code == 200

    def test_approve_plugin(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.approve_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/approve?reviewer=admin"
            )
            assert response.status_code == 200

    def test_reject_plugin(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.reject_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/reject?reason=quality"
            )
            assert response.status_code == 200

    def test_download_plugin(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.download_plugin.return_value = {
                "plugin_id": "plugin-123",
                "code": "test code",
            }
            mock_manager.return_value = mock_instance
            response = client.post("/api/plugin-marketplace/plugin/plugin-123/download")
            assert response.status_code == 200

    def test_download_plugin_not_found(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.download_plugin.return_value = None
            mock_manager.return_value = mock_instance
            response = client.post("/api/plugin-marketplace/plugin/plugin-404/download")
            assert response.status_code == 404

    def test_get_plugin_listings(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_plugin_listings.return_value = [
                {"plugin_id": "plugin-123", "name": "Test"}
            ]
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-marketplace/listings")
            assert response.status_code == 200

    def test_add_plugin_review(self, client):
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.add_review.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/review",
                params={"reviewer": "user", "rating": "5", "comment": "good"},
            )
            assert response.status_code == 200

    def test_publish_plugin_error(self, client):
        """测试发布插件失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.publish_plugin.side_effect = Exception("Publish failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/publish",
                params={
                    "plugin_id": "plugin-123",
                    "plugin_name": "TestPlugin",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "TestAuthor",
                    "plugin_code": "code",
                    "quality": "community",
                },
                json={"config": {}},
            )
            assert response.status_code == 500

    def test_approve_plugin_error(self, client):
        """测试审批插件失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.approve_plugin.side_effect = Exception("Approve failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/approve?reviewer=admin"
            )
            assert response.status_code == 500

    def test_reject_plugin_error(self, client):
        """测试拒绝插件失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.reject_plugin.side_effect = Exception("Reject failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/reject?reason=quality"
            )
            assert response.status_code == 500

    def test_download_plugin_error(self, client):
        """测试下载插件失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.download_plugin.side_effect = Exception("Download failed")
            mock_manager.return_value = mock_instance
            response = client.post("/api/plugin-marketplace/plugin/plugin-123/download")
            assert response.status_code == 500

    def test_get_plugin_listings_error(self, client):
        """测试获取插件列表失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_plugin_listings.side_effect = Exception("Listings failed")
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-marketplace/listings")
            assert response.status_code == 500

    def test_add_plugin_review_error(self, client):
        """测试添加评论失败"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.add_review.side_effect = Exception("Review failed")
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-marketplace/plugin/plugin-123/review",
                params={"reviewer": "user", "rating": "5", "comment": "good"},
            )
            assert response.status_code == 500

    def test_get_marketplace_status_response_structure(self, client):
        """测试状态响应结构"""
        with patch("core.plugin_marketplace_manager.get_marketplace_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_marketplace_summary.return_value = {
                "total_plugins": 50,
                "published_plugins": 40,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-marketplace/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "data" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
