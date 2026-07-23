# -*- coding: utf-8 -*-
"""
Doc Generator Router Tests
文档生成器路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.documentation_generator"] = MagicMock()

from api.doc_generator_router import (
    generate_document,
    get_generated_document,
    get_generator_status,
    get_generator_templates,
    list_generated_documents,
    save_generated_document,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/doc-generator", tags=["Documentation Generator"])
    test_router.add_api_route("/status", get_generator_status, methods=["GET"])
    test_router.add_api_route("/templates", get_generator_templates, methods=["GET"])
    test_router.add_api_route("/document/generate", generate_document, methods=["POST"])
    test_router.add_api_route("/document/{doc_id}", get_generated_document, methods=["GET"])
    test_router.add_api_route("/document/{doc_id}/save", save_generated_document, methods=["POST"])
    test_router.add_api_route("/documents", list_generated_documents, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestDocGeneratorRouter:
    """测试文档生成器路由"""

    def test_get_generator_status(self, client):
        """测试获取文档生成器状态"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.get_generator_summary.return_value = {
                "available": True,
                "total_templates": 5,
            }
            mock_generator.return_value = mock_instance

            response = client.get("/api/doc-generator/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_generator_status_error(self, client):
        """测试获取文档生成器状态失败"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("Doc generator error")

            response = client.get("/api/doc-generator/status")
            assert response.status_code == 500

    def test_get_generator_templates(self, client):
        """测试获取可用模板"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.get_available_templates.return_value = ["api-doc", "user-guide"]
            mock_generator.return_value = mock_instance
            response = client.get("/api/doc-generator/templates")
            assert response.status_code == 200

    def test_generate_document(self, client):
        """测试生成文档"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.doc_id = "doc-123"
            mock_doc.title = "Test Doc"
            mock_doc.generator_type.value = "markdown"
            mock_doc.generated_at.isoformat.return_value = "2026-07-03T09:00:00Z"
            mock_instance.generate_document.return_value = mock_doc
            mock_generator.return_value = mock_instance
            response = client.post(
                "/api/doc-generator/document/generate",
                params={"doc_id": "doc-123", "title": "Test", "template_name": "api-doc"},
                json={"content_vars": {}},
            )
            assert response.status_code == 200

    def test_get_generated_document(self, client):
        """测试获取生成的文档"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_doc = Mock()
            mock_doc.doc_id = "doc-123"
            mock_doc.title = "Test Doc"
            mock_doc.generator_type.value = "markdown"
            mock_doc.content = "Test content"
            mock_doc.generated_at.isoformat.return_value = "2026-07-03T09:00:00Z"
            mock_instance.get_generated_document.return_value = mock_doc
            mock_generator.return_value = mock_instance
            response = client.get("/api/doc-generator/document/doc-123")
            assert response.status_code == 200

    def test_get_generated_document_not_found(self, client):
        """测试获取不存在的文档"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.get_generated_document.return_value = None
            mock_generator.return_value = mock_instance
            response = client.get("/api/doc-generator/document/doc-404")
            assert response.status_code == 404

    def test_save_generated_document(self, client):
        """测试保存生成的文档"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.save_generated_document.return_value = True
            mock_generator.return_value = mock_instance
            response = client.post(
                "/api/doc-generator/document/doc-123/save?output_path=/tmp/doc.md"
            )
            assert response.status_code == 200

    def test_list_generated_documents(self, client):
        """测试列出所有生成的文档"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.list_generated_documents.return_value = [
                {"doc_id": "doc-123", "title": "Test"}
            ]
            mock_generator.return_value = mock_instance
            response = client.get("/api/doc-generator/documents")
            assert response.status_code == 200

    def test_get_generator_templates_error(self, client):
        """测试获取模板失败"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("template error")
            response = client.get("/api/doc-generator/templates")
            assert response.status_code == 500

    def test_generate_document_not_found(self, client):
        """测试生成文档返回空"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_instance = Mock()
            mock_instance.generate_document.return_value = None
            mock_generator.return_value = mock_instance
            response = client.post(
                "/api/doc-generator/document/generate",
                params={"doc_id": "doc-123", "title": "Test", "template_name": "api-doc"},
                json={"content_vars": {}},
            )
            assert response.status_code == 404

    def test_generate_document_error(self, client):
        """测试生成文档异常"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("generate error")
            response = client.post(
                "/api/doc-generator/document/generate",
                params={"doc_id": "doc-123", "title": "Test", "template_name": "api-doc"},
                json={"content_vars": {}},
            )
            assert response.status_code == 500

    def test_get_generated_document_error(self, client):
        """测试获取生成文档异常"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("get error")
            response = client.get("/api/doc-generator/document/doc-123")
            assert response.status_code == 500

    def test_save_generated_document_error(self, client):
        """测试保存文档异常"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("save error")
            response = client.post(
                "/api/doc-generator/document/doc-123/save?output_path=/tmp/doc.md"
            )
            assert response.status_code == 500

    def test_list_generated_documents_error(self, client):
        """测试列出文档异常"""
        with patch("core.documentation_generator.get_documentation_generator") as mock_generator:
            mock_generator.side_effect = Exception("list error")
            response = client.get("/api/doc-generator/documents")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
