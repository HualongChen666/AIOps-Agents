# -*- coding: utf-8 -*-
"""
Documentation Router Tests
文档管理路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.documentation_router import (
    create_document,
    get_document,
    get_documentation_status,
    get_templates,
    list_documents,
    update_document,
)

# Mock problematic imports before importing router
sys.modules["core.documentation_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/documentation", tags=["Documentation"])
    test_router.add_api_route("/status", get_documentation_status, methods=["GET"])
    test_router.add_api_route("/documents", list_documents, methods=["GET"])
    test_router.add_api_route("/document/create", create_document, methods=["POST"])
    test_router.add_api_route("/document/{doc_id}", get_document, methods=["GET"])
    test_router.add_api_route("/document/{doc_id}/update", update_document, methods=["POST"])
    test_router.add_api_route("/templates", get_templates, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestDocumentationRouter:
    """测试文档管理路由"""

    def test_get_documentation_status(self, client):
        """测试获取文档状态"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_doc_summary.return_value = {
                "total_documents": 50,
                "published_documents": 40,
            }
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_documentation_status_error(self, client):
        """测试获取文档状态失败"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_manager.side_effect = Exception("Documentation error")

            response = client.get("/api/documentation/status")
            assert response.status_code == 500

    def test_list_documents(self, client):
        """测试列出文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.list_documents.return_value = [
                {"doc_id": "doc-123", "title": "API Guide", "status": "published"}
            ]
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/documents")
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data["data"]

    def test_list_documents_with_filters(self, client):
        """测试带过滤条件列出文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.list_documents.return_value = []
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/documents?doc_type=api&status=published")
            assert response.status_code == 200

    def test_list_documents_error(self, client):
        """测试列出文档失败"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_manager.side_effect = Exception("List error")

            response = client.get("/api/documentation/documents")
            assert response.status_code == 500

    def test_create_document(self, client):
        """测试创建文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.create_document.return_value = True
            mock_manager.return_value = mock_instance

            response = client.post(
                "/api/documentation/document/create?doc_id=doc-123&title=Test"
                " Doc&doc_type=api&content=Test content"
            )
            assert response.status_code == 200

    def test_get_document(self, client):
        """测试获取文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.doc_id = "doc-123"
            mock_doc.title = "Test Doc"
            mock_doc.doc_type.value = "api"
            mock_doc.status.value = "published"
            mock_doc.version = "1.0"
            mock_doc.author = "test"
            mock_doc.content = "Test content"
            mock_doc.last_updated.isoformat.return_value = "2026-07-03T09:00:00Z"
            mock_instance.get_document.return_value = mock_doc
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/document/doc-123")
            assert response.status_code == 200

    def test_get_document_not_found(self, client):
        """测试获取不存在的文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_document.return_value = None
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/document/doc-404")
            assert response.status_code == 404

    def test_update_document(self, client):
        """测试更新文档"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.update_document.return_value = True
            mock_manager.return_value = mock_instance

            response = client.post(
                "/api/documentation/document/doc-123/update",
                json={"content": "Updated content", "status": "published"},
            )
            assert response.status_code == 200

    def test_get_templates(self, client):
        """测试获取模板"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_available_templates.return_value = ["template1", "template2"]
            mock_manager.return_value = mock_instance

            response = client.get("/api/documentation/templates")
            assert response.status_code == 200
            data = response.json()
            assert "templates" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
