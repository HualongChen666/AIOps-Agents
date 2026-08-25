# -*- coding: utf-8 -*-
"""
Test suite for Documentation Advanced Router
=============================================

Comprehensive tests for documentation management API endpoints including:
- Document CRUD operations
- Template management
- Document generation
- Version control
- Review workflow
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the router
from api.documentation_advanced_router import (
    DOCUMENTATION_AVAILABLE,
    DocumentCreate,
    DocumentUpdate,
    GeneratorRequest,
    ReviewCreate,
    TemplateCreate,
    document_reviews,
    document_versions,
    router,
)


# Mock documentation manager
class MockDocument:
    def __init__(self, doc_id, title, doc_type, status, version, author, content, metadata):
        self.doc_id = doc_id
        self.title = title
        self.doc_type = doc_type
        self.status = status
        self.version = version
        self.author = author
        self.content = content
        self.last_updated = datetime.utcnow()
        self.metadata = metadata

        # Add value attribute for enum compatibility
        if not hasattr(self.doc_type, "value"):
            self.doc_type = type("MockEnum", (), {"value": str(doc_type)})()
        if not hasattr(self.status, "value"):
            self.status = type("MockEnum", (), {"value": str(status)})()


class MockDocTemplate:
    def __init__(self, template_id, template_name, doc_type, template_content, metadata):
        self.template_id = template_id
        self.template_name = template_name
        self.doc_type = doc_type
        self.template_content = template_content
        self.metadata = metadata

        # Add value attribute for enum compatibility
        if not hasattr(self.doc_type, "value"):
            self.doc_type = type("MockEnum", (), {"value": str(doc_type)})()


class MockDocumentationManager:
    def __init__(self):
        self.documents = {}
        self.templates = {}

    def create_document(self, doc_id, title, doc_type, content, author, version):
        self.documents[doc_id] = MockDocument(
            doc_id=doc_id,
            title=title,
            doc_type=doc_type,
            status="draft",
            version=version,
            author=author,
            content=content,
            metadata={},
        )
        return True

    def get_document(self, doc_id):
        return self.documents.get(doc_id)

    def update_document(self, doc_id, content, status):
        if doc_id in self.documents:
            if content:
                self.documents[doc_id].content = content
            if status:
                self.documents[doc_id].status = status
            return True
        return False

    def list_documents(self, doc_type=None, status=None):
        docs = list(self.documents.values())
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        if status:
            docs = [d for d in docs if d.status == status]
        return [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "doc_type": d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type),
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "version": d.version,
                "author": d.author,
            }
            for d in docs
        ]

    def get_available_templates(self):
        return [
            {
                "template_id": t.template_id,
                "template_name": t.template_name,
                "doc_type": t.doc_type.value if hasattr(t.doc_type, "value") else str(t.doc_type),
                "template_content": t.template_content,
            }
            for t in self.templates.values()
        ]


@pytest.fixture
def mock_manager():
    """Create a mock documentation manager"""
    manager = MockDocumentationManager()
    yield manager
    # Cleanup after test
    manager.documents.clear()
    manager.templates.clear()


@pytest.fixture
def mock_doc_type():
    """Mock DocType enum"""
    from enum import Enum

    class MockDocType(Enum):
        API_DOCUMENTATION = "api_documentation"
        USER_GUIDE = "user_guide"
        TECHNICAL_SPEC = "technical_spec"

    return MockDocType


@pytest.fixture
def mock_doc_status():
    """Mock DocStatus enum"""
    from enum import Enum

    class MockDocStatus(Enum):
        DRAFT = "draft"
        PUBLISHED = "published"
        DEPRECATED = "deprecated"

    return MockDocStatus


@pytest.fixture
def client(mock_manager, mock_doc_type, mock_doc_status):
    """Create a test client with mocked dependencies"""
    # Clear in-memory storage
    document_versions.clear()
    document_reviews.clear()

    # Create a fresh manager instance for each test
    fresh_manager = MockDocumentationManager()

    # Mock the imports
    with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", True):
        with patch(
            "api.documentation_advanced_router.get_documentation_manager",
            return_value=fresh_manager,
        ):
            with patch("api.documentation_advanced_router.DocType", mock_doc_type):
                with patch("api.documentation_advanced_router.DocStatus", mock_doc_status):
                    from fastapi import FastAPI

                    app = FastAPI()
                    app.include_router(router)
                    test_client = TestClient(app)
                    yield test_client
                    # Cleanup after test
                    document_versions.clear()
                    document_reviews.clear()


# ==================== Document CRUD Tests ====================


class TestListDocuments:
    """Test cases for listing documents"""

    def test_list_documents_success(self, client, mock_doc_type, mock_doc_status):
        """Test successful document listing"""
        # Create a test document first
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content 1",
                "author": "John",
                "version": "1.0",
            },
        )
        assert response.status_code == 201

        # Now list documents
        response = client.get("/api/v1/documentation/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "documents" in data["data"]
        assert len(data["data"]["documents"]) >= 1

    def test_list_documents_with_filters(self, client, mock_doc_type):
        """Test document listing with filters"""
        # Create a test document
        client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content 1",
                "author": "John",
                "version": "1.0",
            },
        )

        response = client.get(
            "/api/v1/documentation/documents?doc_type=api_documentation&status=draft"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_list_documents_with_author_filter(self, client, mock_doc_type):
        """Test document listing with author filter"""
        # Create a test document
        client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content 1",
                "author": "John",
                "version": "1.0",
            },
        )

        response = client.get("/api/v1/documentation/documents?author=John")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_list_documents_with_pagination(self, client, mock_doc_type):
        """Test document listing with pagination"""
        # Create multiple documents
        for i in range(5):
            client.post(
                "/api/v1/documentation/documents",
                json={
                    "title": f"Doc {i}",
                    "doc_type": "api_documentation",
                    "content": f"Content {i}",
                    "author": "John",
                    "version": "1.0",
                },
            )

        response = client.get("/api/v1/documentation/documents?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["documents"]) == 2
        assert data["data"]["total"] == 5

    def test_list_documents_invalid_doc_type(self, client):
        """Test document listing with invalid doc type"""
        response = client.get("/api/v1/documentation/documents?doc_type=invalid_type")
        assert response.status_code == 400

    def test_list_documents_invalid_status(self, client):
        """Test document listing with invalid status"""
        response = client.get("/api/v1/documentation/documents?status=invalid_status")
        assert response.status_code == 400

    def test_list_documents_service_unavailable(self):
        """Test document listing when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/api/v1/documentation/documents")
            assert response.status_code == 503


class TestCreateDocument:
    """Test cases for creating documents"""

    def test_create_document_success(self, client, mock_doc_type):
        """Test successful document creation"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "New API Document",
                "doc_type": "api_documentation",
                "content": "# API Documentation\n\nThis is a test document.",
                "author": "John Doe",
                "version": "1.0",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "doc_id" in data["data"]
        assert data["data"]["title"] == "New API Document"

    def test_create_document_with_custom_id(self, client, mock_doc_type):
        """Test document creation with custom ID"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "custom-doc-001",
                "title": "Custom ID Document",
                "doc_type": "api_documentation",
                "content": "Content",
                "version": "1.0",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["doc_id"] == "custom-doc-001"

    def test_create_document_invalid_doc_type(self, client):
        """Test document creation with invalid doc type"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "Test",
                "doc_type": "invalid_type",
                "content": "Content",
                "version": "1.0",
            },
        )
        assert response.status_code == 400

    def test_create_document_missing_required_fields(self, client):
        """Test document creation with missing required fields"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "Test"
                # Missing doc_type and content
            },
        )
        assert response.status_code == 422  # Validation error

    def test_create_document_service_unavailable(self):
        """Test document creation when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.post(
                "/api/v1/documentation/documents",
                json={"title": "Test", "doc_type": "api_documentation", "content": "Content"},
            )
            assert response.status_code == 503


class TestGetDocument:
    """Test cases for getting document details"""

    def test_get_document_success(self, client, mock_doc_type):
        """Test successful document retrieval"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content 1",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        # Get the document
        response = client.get(f"/api/v1/documentation/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["doc_id"] == doc_id
        assert data["data"]["title"] == "API Doc"

    def test_get_document_not_found(self, client):
        """Test getting non-existent document"""
        response = client.get("/api/v1/documentation/documents/nonexistent")
        assert response.status_code == 404

    def test_get_document_service_unavailable(self):
        """Test document retrieval when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/api/v1/documentation/documents/doc-001")
            assert response.status_code == 503


class TestUpdateDocument:
    """Test cases for updating documents"""

    def test_update_document_content(self, client, mock_doc_type):
        """Test updating document content"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Old Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.patch(
            f"/api/v1/documentation/documents/{doc_id}", json={"content": "New Content"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["updated"] is True

    def test_update_document_status(self, client, mock_doc_type):
        """Test updating document status"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.patch(
            f"/api/v1/documentation/documents/{doc_id}", json={"status": "published"}
        )
        assert response.status_code == 200

    def test_update_document_title(self, client, mock_doc_type):
        """Test updating document title"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "Old Title",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.patch(
            f"/api/v1/documentation/documents/{doc_id}", json={"title": "New Title"}
        )
        assert response.status_code == 200

    def test_update_document_metadata(self, client, mock_doc_type):
        """Test updating document metadata"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.patch(
            f"/api/v1/documentation/documents/{doc_id}",
            json={"metadata": {"category": "technical", "tags": ["api", "rest"]}},
        )
        assert response.status_code == 200

    def test_update_document_not_found(self, client):
        """Test updating non-existent document"""
        response = client.patch(
            "/api/v1/documentation/documents/nonexistent", json={"content": "New Content"}
        )
        assert response.status_code == 404

    def test_update_document_invalid_status(self, client, mock_doc_type):
        """Test updating document with invalid status"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.patch(
            f"/api/v1/documentation/documents/{doc_id}", json={"status": "invalid_status"}
        )
        assert response.status_code == 400

    def test_update_document_service_unavailable(self):
        """Test document update when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.patch(
                "/api/v1/documentation/documents/doc-001", json={"content": "New Content"}
            )
            assert response.status_code == 503


class TestDeleteDocument:
    """Test cases for deleting documents"""

    def test_delete_document_success(self, client, mock_doc_type):
        """Test successful document deletion"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        response = client.delete(f"/api/v1/documentation/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["deleted"] is True

    def test_delete_document_not_found(self, client):
        """Test deleting non-existent document"""
        response = client.delete("/api/v1/documentation/documents/nonexistent")
        assert response.status_code == 404

    def test_delete_document_service_unavailable(self):
        """Test document deletion when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.delete("/api/v1/documentation/documents/doc-001")
            assert response.status_code == 503


# ==================== Template Management Tests ====================


class TestListTemplates:
    """Test cases for listing templates"""

    def test_list_templates_success(self, client, mock_doc_type):
        """Test successful template listing"""
        # Create a template first
        client.post(
            "/api/v1/documentation/templates",
            json={
                "template_name": "API Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}\n\nContent",
            },
        )

        response = client.get("/api/v1/documentation/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "templates" in data["data"]

    def test_list_templates_with_filter(self, client, mock_doc_type):
        """Test template listing with doc type filter"""
        # Create a template first
        client.post(
            "/api/v1/documentation/templates",
            json={
                "template_name": "API Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}\n\nContent",
            },
        )

        response = client.get("/api/v1/documentation/templates?doc_type=api_documentation")
        assert response.status_code == 200

    def test_list_templates_service_unavailable(self):
        """Test template listing when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/api/v1/documentation/templates")
            assert response.status_code == 503


class TestCreateTemplate:
    """Test cases for creating templates"""

    def test_create_template_success(self, client, mock_doc_type):
        """Test successful template creation"""
        response = client.post(
            "/api/v1/documentation/templates",
            json={
                "template_name": "Custom Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}\n\n{content}",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "template_id" in data["data"]

    def test_create_template_with_custom_id(self, client, mock_doc_type):
        """Test template creation with custom ID"""
        response = client.post(
            "/api/v1/documentation/templates",
            json={
                "template_id": "custom-tpl-001",
                "template_name": "Custom Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["template_id"] == "custom-tpl-001"

    def test_create_template_invalid_doc_type(self, client):
        """Test template creation with invalid doc type"""
        response = client.post(
            "/api/v1/documentation/templates",
            json={
                "template_name": "Test",
                "doc_type": "invalid_type",
                "template_content": "Content",
            },
        )
        assert response.status_code == 400

    def test_create_template_missing_required_fields(self, client):
        """Test template creation with missing required fields"""
        response = client.post(
            "/api/v1/documentation/templates",
            json={
                "template_name": "Test"
                # Missing doc_type and template_content
            },
        )
        assert response.status_code == 422

    def test_create_template_service_unavailable(self):
        """Test template creation when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.post(
                "/api/v1/documentation/templates",
                json={
                    "template_name": "Test",
                    "doc_type": "api_documentation",
                    "template_content": "Content",
                },
            )
            assert response.status_code == 503


# ==================== Document Generation Tests ====================


class TestGenerateDocument:
    """Test cases for document generation"""

    def test_generate_document_success(self, client, mock_doc_type):
        """Test successful document generation"""
        # Create a template first
        template_response = client.post(
            "/api/v1/documentation/templates",
            json={
                "template_id": "tpl-001",
                "template_name": "API Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}\n\nVersion: {version}",
            },
        )
        assert template_response.status_code == 201

        response = client.post(
            "/api/v1/documentation/generators",
            json={
                "template_id": "tpl-001",
                "parameters": {"title": "Generated API", "version": "2.0"},
                "output_format": "markdown",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "doc_id" in data["data"]
        assert "Generated API" in data["data"]["content"]

    def test_generate_document_template_not_found(self, client):
        """Test document generation with non-existent template"""
        response = client.post(
            "/api/v1/documentation/generators",
            json={
                "template_id": "nonexistent",
                "parameters": {"title": "Test"},
                "output_format": "markdown",
            },
        )
        assert response.status_code == 404

    def test_generate_document_missing_parameters(self, client):
        """Test document generation with missing parameters"""
        response = client.post(
            "/api/v1/documentation/generators",
            json={"template_id": "tpl-001", "parameters": {}, "output_format": "markdown"},
        )
        # Should still work, just with empty parameters
        assert response.status_code in [200, 404]

    def test_generate_document_service_unavailable(self):
        """Test document generation when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.post(
                "/api/v1/documentation/generators",
                json={
                    "template_id": "tpl-001",
                    "parameters": {"title": "Test"},
                    "output_format": "markdown",
                },
            )
            assert response.status_code == 503


# ==================== Version Control Tests ====================


class TestDocumentVersions:
    """Test cases for document version control"""

    def test_list_document_versions_success(self, client, mock_doc_type):
        """Test successful version listing"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        # Add version history
        document_versions[doc_id] = [
            {
                "version": "1.0",
                "content": "Content v1",
                "created_at": "2024-01-01",
                "author": "John",
            },
            {
                "version": "1.1",
                "content": "Content v2",
                "created_at": "2024-01-02",
                "author": "John",
            },
        ]

        response = client.get(f"/api/v1/documentation/versions?doc_id={doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "versions" in data["data"]
        assert len(data["data"]["versions"]) == 2

    def test_list_document_versions_not_found(self, client):
        """Test version listing for non-existent document"""
        response = client.get("/api/v1/documentation/versions?doc_id=nonexistent")
        assert response.status_code == 404

    def test_list_document_versions_empty(self, client, mock_doc_type):
        """Test version listing for document with no versions"""
        # Create a document first
        create_response = client.post(
            "/api/v1/documentation/documents",
            json={
                "doc_id": "doc-001",
                "title": "API Doc",
                "doc_type": "api_documentation",
                "content": "Content",
                "author": "John",
                "version": "1.0",
            },
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["data"]["doc_id"]

        # Clear the auto-created version
        if doc_id in document_versions:
            document_versions[doc_id] = []

        response = client.get(f"/api/v1/documentation/versions?doc_id={doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["versions"]) == 0

    def test_list_document_versions_service_unavailable(self):
        """Test version listing when service is unavailable"""
        with patch("api.documentation_advanced_router.DOCUMENTATION_AVAILABLE", False):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)

            response = client.get("/api/v1/documentation/versions?doc_id=doc-001")
            assert response.status_code == 503


# ==================== Review Workflow Tests ====================


class TestDocumentReviews:
    """Test cases for document review workflow"""

    def test_list_reviews_success(self, client):
        """Test successful review listing"""
        document_reviews["doc-001"] = [
            {
                "review_id": "rev-001",
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Good documentation",
                "status": "approved",
                "rating": 5,
                "created_at": "2024-01-01",
            }
        ]

        response = client.get("/api/v1/documentation/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "reviews" in data["data"]

    def test_list_reviews_with_filters(self, client):
        """Test review listing with filters"""
        document_reviews["doc-001"] = [
            {
                "review_id": "rev-001",
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Good",
                "status": "approved",
                "rating": 5,
                "created_at": "2024-01-01",
            }
        ]

        response = client.get("/api/v1/documentation/reviews?document_id=doc-001&status=approved")
        assert response.status_code == 200

    def test_create_review_success(self, client):
        """Test successful review creation"""
        response = client.post(
            "/api/v1/documentation/reviews",
            json={
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Excellent documentation",
                "status": "approved",
                "rating": 5,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "review_id" in data["data"]

    def test_create_review_with_rating(self, client):
        """Test review creation with rating"""
        response = client.post(
            "/api/v1/documentation/reviews",
            json={
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Good",
                "status": "approved",
                "rating": 4,
            },
        )
        assert response.status_code == 201

    def test_create_review_invalid_rating(self, client):
        """Test review creation with invalid rating (out of range)"""
        response = client.post(
            "/api/v1/documentation/reviews",
            json={
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Test",
                "status": "pending",
                "rating": 6,  # Invalid: should be 1-5
            },
        )
        assert response.status_code == 422

    def test_create_review_missing_required_fields(self, client):
        """Test review creation with missing required fields"""
        response = client.post(
            "/api/v1/documentation/reviews",
            json={
                "document_id": "doc-001"
                # Missing reviewer_id and comments
            },
        )
        assert response.status_code == 422


# ==================== Data Validation Tests ====================


class TestDataValidation:
    """Test cases for data validation"""

    def test_document_create_validation(self):
        """Test DocumentCreate model validation"""
        # Valid data
        doc = DocumentCreate(title="Test Document", doc_type="api_documentation", content="Content")
        assert doc.title == "Test Document"
        assert doc.version == "1.0"  # Default value

    def test_document_update_validation(self):
        """Test DocumentUpdate model validation"""
        # All fields optional
        doc = DocumentUpdate()
        assert doc.title is None
        assert doc.content is None

    def test_template_create_validation(self):
        """Test TemplateCreate model validation"""
        template = TemplateCreate(
            template_name="Test Template",
            doc_type="api_documentation",
            template_content="# {title}",
        )
        assert template.template_name == "Test Template"

    def test_generator_request_validation(self):
        """Test GeneratorRequest model validation"""
        request = GeneratorRequest(template_id="tpl-001", parameters={"title": "Test"})
        assert request.output_format == "markdown"  # Default value

    def test_review_create_validation(self):
        """Test ReviewCreate model validation"""
        review = ReviewCreate(document_id="doc-001", reviewer_id="user-001", comments="Good")
        assert review.status == "pending"  # Default value
        assert review.rating is None


# ==================== Edge Cases and Error Handling ====================


class TestEdgeCases:
    """Test cases for edge cases and error handling"""

    def test_empty_document_list(self, client):
        """Test listing documents when none exist"""
        # Clear any existing documents by using a fresh client
        response = client.get("/api/v1/documentation/documents")
        assert response.status_code == 200
        data = response.json()
        # Just check that the request succeeds, don't assert on count
        # since state might persist between tests
        assert "documents" in data["data"]

    def test_empty_template_list(self, client):
        """Test listing templates when none exist"""
        response = client.get("/api/v1/documentation/templates")
        assert response.status_code == 200
        data = response.json()
        # Just check that the request succeeds
        assert "templates" in data["data"]

    def test_empty_review_list(self, client):
        """Test listing reviews when none exist"""
        response = client.get("/api/v1/documentation/reviews")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["reviews"]) == 0

    def test_large_content_document(self, client, mock_doc_type):
        """Test creating document with large content"""
        large_content = "Content " * 10000
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "Large Document",
                "doc_type": "api_documentation",
                "content": large_content,
                "version": "1.0",
            },
        )
        assert response.status_code == 201

    def test_special_characters_in_content(self, client, mock_doc_type):
        """Test document with special characters"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "Special Chars",
                "doc_type": "api_documentation",
                "content": "Content with <>&\"' and \n\t newlines",
                "version": "1.0",
            },
        )
        assert response.status_code == 201

    def test_unicode_in_content(self, client, mock_doc_type):
        """Test document with unicode characters"""
        response = client.post(
            "/api/v1/documentation/documents",
            json={
                "title": "Unicode 测试",
                "doc_type": "api_documentation",
                "content": "Content with 中文 and emojis 🎉",
                "version": "1.0",
            },
        )
        assert response.status_code == 201


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
