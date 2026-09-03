# -*- coding: utf-8 -*-
"""
Test suite for Documentation Router
文档管理路由测试套件
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.documentation_router import router
from core.authentication import get_current_active_user


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the documentation router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def authenticated_client():
    """Create a test client with authentication bypassed"""
    from fastapi import FastAPI
    from unittest.mock import MagicMock

    app = FastAPI()
    app.include_router(router)

    # Create mock user
    mock_user = MagicMock()
    mock_user.id = "user-001"
    mock_user.username = "testuser"
    mock_user.is_active = True

    # Override authentication dependency
    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    client = TestClient(app)

    yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_manager():
    """Create a mock documentation manager"""
    manager = MagicMock()
    manager.get_doc_summary.return_value = {
        "total_documents": 50,
        "published_documents": 40,
    }
    manager.list_documents.return_value = [
        {
            "doc_id": "doc-123",
            "title": "API Guide",
            "status": "published",
            "doc_type": "api_documentation",
            "version": "1.0",
            "author": "John Doe",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    ]
    manager.get_document.return_value = MagicMock(
        doc_id="doc-123",
        title="API Guide",
        doc_type=MagicMock(value="api_documentation"),
        status=MagicMock(value="published"),
        version="1.0",
        author="John Doe",
        content="# API Guide",
        last_updated=datetime.now(timezone.utc),
    )
    manager.create_document.return_value = True
    manager.update_document.return_value = True
    manager.get_available_templates.return_value = [
        {
            "template_id": "user_manual",
            "template_name": "User Manual Template",
            "doc_type": "user_manual",
            "description": "Template for user manuals",
        }
    ]
    return manager


@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    user = MagicMock()
    user.id = "user-001"
    user.username = "testuser"
    user.is_active = True
    return user


# Status endpoint tests
class TestStatusEndpoint:
    """Test documentation status endpoint"""

    def test_get_status_success(self, authenticated_client):
        """Test successful status retrieval"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_doc_summary.return_value = {
                "total_documents": 50,
                "published_documents": 40,
            }
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/status")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "timestamp" in data
            assert data["data"]["total_documents"] == 50
            assert data["data"]["published_documents"] == 40

    def test_get_status_error(self, authenticated_client):
        """Test status retrieval with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = authenticated_client.get("/api/docs/status")

            assert response.status_code == 500


# Documents list endpoint tests
class TestListDocumentsEndpoint:
    """Test documents list endpoint"""

    def test_list_documents_success(self, authenticated_client):
        """Test successful document listing"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_documents.return_value = [
                {
                    "doc_id": "doc-123",
                    "title": "API Guide",
                    "status": "published",
                    "doc_type": "api_documentation",
                    "version": "1.0",
                    "author": "John Doe",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            ]
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/documents")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "documents" in data["data"]
            assert "count" in data["data"]
            assert data["data"]["count"] == 1

    def test_list_documents_with_filters(self, authenticated_client):
        """Test document listing with filters"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_documents.return_value = []
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/documents?doc_type=api_documentation&status=published")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_list_documents_error(self, authenticated_client):
        """Test document listing with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = authenticated_client.get("/api/docs/documents")

            assert response.status_code == 500


# Create document endpoint tests
class TestCreateDocumentEndpoint:
    """Test create document endpoint"""

    def test_create_document_success(self, authenticated_client):
        """Test successful document creation"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.create_document.return_value = True
            mock_get_manager.return_value = mock_manager

            request_data = {
                "doc_id": "doc-001",
                "title": "New API Document",
                "doc_type": "api_documentation",
                "content": "# API Documentation\n\nThis is a test document.",
                "author": "John Doe",
                "version": "1.0",
            }

            response = authenticated_client.post("/api/docs/document/create", params=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["doc_id"] == "doc-001"
            assert data["data"]["created"] is True

    def test_create_document_error(self, authenticated_client):
        """Test document creation with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            request_data = {
                "doc_id": "doc-001",
                "title": "New API Document",
                "doc_type": "api_documentation",
                "content": "# API Documentation",
            }

            response = authenticated_client.post("/api/docs/document/create", params=request_data)

            assert response.status_code == 500


# Get document endpoint tests
class TestGetDocumentEndpoint:
    """Test get document endpoint"""

    def test_get_document_success(self, authenticated_client):
        """Test successful document retrieval"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_document.return_value = MagicMock(
                doc_id="doc-123",
                title="API Guide",
                doc_type=MagicMock(value="api_documentation"),
                status=MagicMock(value="published"),
                version="1.0",
                author="John Doe",
                content="# API Guide",
                last_updated=datetime.now(timezone.utc),
            )
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/document/doc-123")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert data["data"]["doc_id"] == "doc-123"
            assert data["data"]["title"] == "API Guide"

    def test_get_document_not_found(self, authenticated_client):
        """Test getting non-existent document"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_document.return_value = None
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/document/nonexistent")

            assert response.status_code == 404

    def test_get_document_error(self, authenticated_client):
        """Test document retrieval with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = authenticated_client.get("/api/docs/document/doc-123")

            assert response.status_code == 500


# Update document endpoint tests
class TestUpdateDocumentEndpoint:
    """Test update document endpoint"""

    def test_update_document_content(self, authenticated_client):
        """Test updating document content"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.update_document.return_value = True
            mock_get_manager.return_value = mock_manager

            request_data = {
                "content": "Updated content",
            }

            response = authenticated_client.post("/api/docs/document/doc-123/update", params=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["updated"] is True

    def test_update_document_status(self, authenticated_client):
        """Test updating document status"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.update_document.return_value = True
            mock_get_manager.return_value = mock_manager

            request_data = {
                "status": "published",
            }

            response = authenticated_client.post("/api/docs/document/doc-123/update", params=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_update_document_error(self, authenticated_client):
        """Test document update with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            request_data = {
                "content": "Updated content",
            }

            response = authenticated_client.post("/api/docs/document/doc-123/update", params=request_data)

            assert response.status_code == 500


# Templates endpoint tests
class TestTemplatesEndpoint:
    """Test templates endpoint"""

    def test_get_templates_success(self, authenticated_client):
        """Test successful template listing"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_available_templates.return_value = [
                {
                    "template_id": "user_manual",
                    "template_name": "User Manual Template",
                    "doc_type": "user_manual",
                    "description": "Template for user manuals",
                }
            ]
            mock_get_manager.return_value = mock_manager

            response = authenticated_client.get("/api/docs/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "templates" in data["data"]
            assert "count" in data["data"]
            assert data["data"]["count"] == 1

    def test_get_templates_error(self, authenticated_client):
        """Test template listing with error"""
        with patch("core.documentation_manager.get_documentation_manager") as mock_get_manager:
            mock_get_manager.side_effect = Exception("Manager error")

            response = authenticated_client.get("/api/docs/templates")

            assert response.status_code == 500


# Authentication tests
class TestAuthentication:
    """Test authentication requirements"""

    def test_unauthorized_access(self, client):
        """Test unauthorized access"""
        response = client.get("/api/docs/status")

        assert response.status_code == 401
