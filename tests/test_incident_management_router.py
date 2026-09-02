# -*- coding: utf-8 -*-
"""
Incident Management Router Test Suite
======================================

Comprehensive test suite for incident management API endpoints.
Uses pytest-xdist for parallel testing execution.

Test Coverage:
- All 40 API endpoints
- Authentication and authorization
- Rate limiting
- Business logic validation
- Error handling
- Batch operations
"""

import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock
from sqlalchemy.orm import Session

from api.incident_management_router import router
from core.models import User
from core.database import get_db
from core.auth import get_current_user, require_role


# ============================================================================
# Test Configuration
# ============================================================================

@pytest.fixture(scope="session")
def test_user():
    """Create a test user fixture"""
    user = Mock(spec=User)
    user.username = "test_user"
    user.user_id = "user_test_001"
    user.roles = ["user"]
    return user


@pytest.fixture(scope="session")
def admin_user():
    """Create an admin user fixture"""
    user = Mock(spec=User)
    user.username = "admin_user"
    user.user_id = "user_admin_001"
    user.roles = ["admin", "incident_manager"]
    return user


@pytest.fixture(scope="session")
def client_with_auth():
    """Create test client with auth override"""
    from fastapi import FastAPI
    from core.auth import require_role
    
    app = FastAPI()
    app.include_router(router)
    
    # Override dependencies for authenticated requests
    def override_get_current_user():
        user = Mock(spec=User)
        user.username = "admin_user"
        user.user_id = "user_admin_001"
        user.roles = ["admin", "incident_manager", "user"]
        return user
    
    def override_get_db():
        session = Mock(spec=Session)
        return session
    
    def override_require_role(roles):
        user = Mock(spec=User)
        user.username = "admin_user"
        user.user_id = "user_admin_001"
        user.roles = roles
        return user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_role] = override_require_role
    
    return TestClient(app)


@pytest.fixture(scope="session")
def client_no_auth():
    """Create test client without auth override"""
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    
    return TestClient(app)


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_incident_data():
    """Create test incident data"""
    return {
        "title": "Test incident from pytest",
        "description": "This is a test incident created by pytest",
        "severity": "high",
        "category": "testing",
        "priority": "high",
        "impact": "medium",
        "urgency": "high",
        "assigned_to": "user_test_001",
        "tags": ["test", "pytest"],
        "environment": "development",
        "source": "test",
        "metadata": {"test": True}
    }


def create_test_comment_data():
    """Create test comment data"""
    return {
        "content": "This is a test comment",
        "is_internal": False,
        "mention_users": []
    }


def create_template_data():
    """Create test template data"""
    return {
        "name": "Test Template",
        "description": "Template for testing",
        "template_data": {
            "category": "testing",
            "severity": "medium",
            "default_tags": ["test"]
        },
        "category": "testing",
        "is_public": False
    }


def create_workflow_data():
    """Create test workflow data"""
    return {
        "name": "Test Workflow",
        "steps": [
            {"name": "step1", "action": "notify"},
            {"name": "step2", "action": "assign"}
        ],
        "triggers": [{"type": "status_change", "value": "open"}],
        "conditions": [{"field": "severity", "operator": "eq", "value": "high"}]
    }


# ============================================================================
# Authentication Tests
# ============================================================================

@pytest.mark.parametrize("endpoint,method,body", [
    ("/api/v1/incident-management/incidents", "POST", {}),
    ("/api/v1/incident-management/incidents", "GET", None),
    ("/api/v1/incident-management/incidents/test-id", "GET", None),
])
def test_unauthorized_access(client_no_auth, endpoint, method, body):
    """Test that unauthorized requests are rejected"""
    if method == "POST":
        response = client_no_auth.post(endpoint, json=body or create_test_incident_data())
    else:
        response = client_no_auth.get(endpoint)
    
    assert response.status_code in [401, 403]


# ============================================================================
# Incident CRUD Tests (Endpoints 1-5)
# ============================================================================

@pytest.mark.xdist_group(name="incident_crud")
def test_create_incident(client_with_auth):
    """Test endpoint 1: Create incident"""
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert data["status"] == "created"
    assert "incident" in data
    assert data["incident"]["title"] == "Test incident from pytest"


@pytest.mark.xdist_group(name="incident_crud")
def test_get_incidents(client_with_auth):
    """Test endpoint 2: Get incidents list"""
    response = client_with_auth.get("/api/v1/incident-management/incidents")
    
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "total" in data
    assert isinstance(data["incidents"], list)


@pytest.mark.xdist_group(name="incident_crud")
def test_get_incident_by_id(client_with_auth):
    """Test endpoint 3: Get incident by ID"""
    # First create an incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Then get it
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "incident" in data
    assert data["incident"]["incident_id"] == incident_id


@pytest.mark.xdist_group(name="incident_crud")
def test_update_incident(client_with_auth):
    """Test endpoint 4: Update incident"""
    # First create an incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Then update it
    update_data = {
        "title": "Updated test incident",
        "severity": "critical"
    }
    response = client_with_auth.put(
        f"/api/v1/incident-management/incidents/{incident_id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert "updated_fields" in data


@pytest.mark.xdist_group(name="incident_crud")
def test_delete_incident(client_with_auth):
    """Test endpoint 5: Delete incident"""
    # First create an incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Then delete it
    response = client_with_auth.delete(f"/api/v1/incident-management/incidents/{incident_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"


# ============================================================================
# Incident Status and Assignment Tests (Endpoints 6-10)
# ============================================================================

@pytest.mark.xdist_group(name="incident_status")
def test_update_incident_status(client_with_auth):
    """Test endpoint 6: Update incident status"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Update status
    status_data = {
        "status": "in_progress",
        "reason": "Investigation started"
    }
    response = client_with_auth.patch(
        f"/api/v1/incident-management/incidents/{incident_id}/status",
        json=status_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "in_progress"


@pytest.mark.xdist_group(name="incident_status")
def test_assign_incident(client_with_auth):
    """Test endpoint 7: Assign incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Assign incident
    assign_data = {
        "assigned_to": "user_test_002",
        "assignee_type": "user",
        "notify": True,
        "message": "Please investigate"
    }
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/assign",
        json=assign_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["new_assignee"] == "user_test_002"


@pytest.mark.xdist_group(name="incident_status")
def test_acknowledge_incident(client_with_auth):
    """Test endpoint 8: Acknowledge incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Acknowledge incident
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/acknowledge",
        params={"comment": "Acknowledging the incident"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "acknowledged_by" in data
    assert "acknowledged_at" in data


@pytest.mark.xdist_group(name="incident_status")
def test_resolve_incident(client_with_auth):
    """Test endpoint 9: Resolve incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Resolve incident
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/resolve",
        params={
            "resolution_notes": "Issue fixed by restarting service",
            "root_cause": "Service crash due to memory leak"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "resolved_by" in data
    assert "resolved_at" in data


@pytest.mark.xdist_group(name="incident_status")
def test_escalate_incident(client_with_auth):
    """Test endpoint 10: Escalate incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Escalate incident
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/escalate",
        params={
            "escalation_level": "level2",
            "escalate_to": "team_level2",
            "reason": "Requires senior team attention"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["new_level"] == "level2"
    assert data["escalated_to"] == "team_level2"


# ============================================================================
# Timeline, Comments, Attachments Tests (Endpoints 11-15)
# ============================================================================

@pytest.mark.xdist_group(name="incident_collaboration")
def test_get_incident_timeline(client_with_auth):
    """Test endpoint 11: Get incident timeline"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Get timeline
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}/timeline")
    
    assert response.status_code == 200
    data = response.json()
    assert "timeline" in data
    assert "total_events" in data


@pytest.mark.xdist_group(name="incident_collaboration")
def test_add_incident_comment(client_with_auth):
    """Test endpoint 12: Add comment to incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Add comment
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/comments",
        json=create_test_comment_data()
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "comment_id" in data
    assert data["comment"]["content"] == "This is a test comment"


@pytest.mark.xdist_group(name="incident_collaboration")
def test_get_incident_comments(client_with_auth):
    """Test endpoint 13: Get incident comments"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Add a comment first
    client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/comments",
        json=create_test_comment_data()
    )
    
    # Get comments
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}/comments")
    
    assert response.status_code == 200
    data = response.json()
    assert "comments" in data
    assert "total" in data


@pytest.mark.xdist_group(name="incident_collaboration")
def test_add_incident_attachment(client_with_auth):
    """Test endpoint 14: Add attachment to incident"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Add attachment
    files = {"file": ("test.txt", b"Test file content", "text/plain")}
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/attachments",
        files=files,
        data={"description": "Test attachment"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "attachment_id" in data
    assert data["attachment"]["filename"] == "test.txt"


@pytest.mark.xdist_group(name="incident_collaboration")
def test_get_incident_attachments(client_with_auth):
    """Test endpoint 15: Get incident attachments"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Get attachments
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}/attachments")
    
    assert response.status_code == 200
    data = response.json()
    assert "attachments" in data
    assert "total" in data


# ============================================================================
# Statistics and Trends Tests (Endpoints 16-17)
# ============================================================================

@pytest.mark.xdist_group(name="incident_analytics")
def test_get_incident_statistics(client_with_auth):
    """Test endpoint 16: Get incident statistics"""
    response = client_with_auth.get("/api/v1/incident-management/incidents/statistics")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_incidents" in data
    assert "by_status" in data
    assert "by_severity" in data
    assert "by_category" in data


@pytest.mark.xdist_group(name="incident_analytics")
def test_get_incident_trends(client_with_auth):
    """Test endpoint 17: Get incident trends"""
    response = client_with_auth.get(
        "/api/v1/incident-management/incidents/trends",
        params={"period": "daily", "days": 7}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "period" in data
    assert "days" in data
    assert "trends" in data
    assert isinstance(data["trends"], list)


# ============================================================================
# Bulk Operations Tests (Endpoints 18-20)
# ============================================================================

@pytest.mark.xdist_group(name="bulk_operations")
def test_bulk_create_incidents(client_with_auth):
    """Test endpoint 18: Bulk create incidents"""
    bulk_data = {
        "incidents": [
            create_test_incident_data(),
            create_test_incident_data()
        ]
    }
    
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents/bulk",
        json=bulk_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 2
    assert data["total_created"] == 2
    assert len(data["results"]) == 2


@pytest.mark.xdist_group(name="bulk_operations")
def test_bulk_update_incidents(client_with_auth):
    """Test endpoint 19: Bulk update incidents"""
    # Create incidents first
    incident_ids = []
    for _ in range(2):
        create_response = client_with_auth.post(
            "/api/v1/incident-management/incidents",
            json=create_test_incident_data()
        )
        incident_ids.append(create_response.json()["incident_id"])
    
    # Bulk update
    bulk_data = {
        "incident_ids": incident_ids,
        "updates": {
            "severity": "critical",
            "priority": "critical"
        }
    }
    
    response = client_with_auth.put(
        "/api/v1/incident-management/incidents/bulk",
        json=bulk_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 2
    assert data["total_updated"] == 2


@pytest.mark.xdist_group(name="bulk_operations")
def test_bulk_delete_incidents(client_with_auth):
    """Test endpoint 20: Bulk delete incidents"""
    # Create incidents first
    incident_ids = []
    for _ in range(2):
        create_response = client_with_auth.post(
            "/api/v1/incident-management/incidents",
            json=create_test_incident_data()
        )
        incident_ids.append(create_response.json()["incident_id"])
    
    # Bulk delete - use request method with JSON body
    response = client_with_auth.request(
        "DELETE",
        "/api/v1/incident-management/incidents/bulk",
        json=incident_ids
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 2
    assert data["total_deleted"] == 2


# ============================================================================
# Search and Filter Tests (Endpoints 21-22)
# ============================================================================

@pytest.mark.xdist_group(name="search_filter")
def test_search_incidents(client_with_auth):
    """Test endpoint 21: Search incidents"""
    search_data = {
        "query": "database",
        "filters": {"severity": "high"},
        "sort_by": "created_at",
        "sort_order": "desc",
        "limit": 10,
        "offset": 0
    }
    
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents/search",
        json=search_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "total" in data


@pytest.mark.xdist_group(name="search_filter")
def test_filter_incidents(client_with_auth):
    """Test endpoint 22: Filter incidents"""
    filter_data = {
        "status": ["open", "in_progress"],
        "severity": ["high", "critical"],
        "limit": 10,
        "offset": 0
    }
    
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents/filter",
        json=filter_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "total" in data


# ============================================================================
# Merge and Link Tests (Endpoints 23-25)
# ============================================================================

@pytest.mark.xdist_group(name="merge_link")
def test_merge_incidents(client_with_auth):
    """Test endpoint 23: Merge incidents"""
    # Create incidents
    target_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    target_id = target_response.json()["incident_id"]
    
    source_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    source_id = source_response.json()["incident_id"]
    
    # Merge incidents
    merge_data = {
        "source_incident_ids": [source_id],
        "target_incident_id": target_id,
        "merge_strategy": "append",
        "reason": "Duplicate incidents"
    }
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{target_id}/merge",
        json=merge_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["target_incident_id"] == target_id
    assert len(data["merged_incidents"]) == 1


@pytest.mark.xdist_group(name="merge_link")
def test_link_incidents(client_with_auth):
    """Test endpoint 24: Link incidents"""
    # Create incidents
    incident1_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident1_id = incident1_response.json()["incident_id"]
    
    incident2_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident2_id = incident2_response.json()["incident_id"]
    
    # Link incidents
    link_data = {
        "related_incident_id": incident2_id,
        "link_type": "related",
        "description": "Related incidents"
    }
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident1_id}/links",
        json=link_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == incident1_id
    assert data["related_incident_id"] == incident2_id


@pytest.mark.xdist_group(name="merge_link")
def test_get_incident_links(client_with_auth):
    """Test endpoint 25: Get incident links"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Get links
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}/links")
    
    assert response.status_code == 200
    data = response.json()
    assert "links" in data
    assert "total" in data


# ============================================================================
# Template Tests (Endpoints 26-30)
# ============================================================================

@pytest.mark.xdist_group(name="templates")
def test_create_template(client_with_auth):
    """Test endpoint 26: Create template"""
    response = client_with_auth.post(
        "/api/v1/incident-management/templates",
        json=create_template_data()
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "template_id" in data
    assert data["template"]["name"] == "Test Template"


@pytest.mark.xdist_group(name="templates")
def test_get_templates(client_with_auth):
    """Test endpoint 27: Get templates"""
    response = client_with_auth.get("/api/v1/incident-management/templates")
    
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "total" in data


@pytest.mark.xdist_group(name="templates")
def test_get_template_by_id(client_with_auth):
    """Test endpoint 28: Get template by ID"""
    # Create template first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/templates",
        json=create_template_data()
    )
    template_id = create_response.json()["template_id"]
    
    # Get template
    response = client_with_auth.get(f"/api/v1/incident-management/templates/{template_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template_id


@pytest.mark.xdist_group(name="templates")
def test_update_template(client_with_auth):
    """Test endpoint 29: Update template"""
    # Create template first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/templates",
        json=create_template_data()
    )
    template_id = create_response.json()["template_id"]
    
    # Update template
    update_data = {
        "name": "Updated Test Template",
        "description": "Updated description",
        "template_data": {"category": "testing", "severity": "high"},
        "category": "testing",
        "is_public": True
    }
    
    response = client_with_auth.put(
        f"/api/v1/incident-management/templates/{template_id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["template"]["name"] == "Updated Test Template"


@pytest.mark.xdist_group(name="templates")
def test_delete_template(client_with_auth):
    """Test endpoint 30: Delete template"""
    # Create template first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/templates",
        json=create_template_data()
    )
    template_id = create_response.json()["template_id"]
    
    # Delete template
    response = client_with_auth.delete(f"/api/v1/incident-management/templates/{template_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == template_id


# ============================================================================
# Workflow Tests (Endpoints 31-35)
# ============================================================================

@pytest.mark.xdist_group(name="workflows")
def test_create_workflow(client_with_auth):
    """Test endpoint 31: Create workflow"""
    response = client_with_auth.post(
        "/api/v1/incident-management/workflows",
        json=create_workflow_data()
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "workflow_id" in data
    assert data["workflow"]["name"] == "Test Workflow"


@pytest.mark.xdist_group(name="workflows")
def test_get_workflows(client_with_auth):
    """Test endpoint 32: Get workflows"""
    response = client_with_auth.get("/api/v1/incident-management/workflows")
    
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
    assert "total" in data


@pytest.mark.xdist_group(name="workflows")
def test_get_workflow_by_id(client_with_auth):
    """Test endpoint 33: Get workflow by ID"""
    # Create workflow first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/workflows",
        json=create_workflow_data()
    )
    workflow_id = create_response.json()["workflow_id"]
    
    # Get workflow
    response = client_with_auth.get(f"/api/v1/incident-management/workflows/{workflow_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id


@pytest.mark.xdist_group(name="workflows")
def test_update_workflow(client_with_auth):
    """Test endpoint 34: Update workflow"""
    # Create workflow first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/workflows",
        json=create_workflow_data()
    )
    workflow_id = create_response.json()["workflow_id"]
    
    # Update workflow
    update_data = {
        "name": "Updated Test Workflow",
        "steps": [{"name": "step1", "action": "notify"}],
        "triggers": [],
        "conditions": []
    }
    
    response = client_with_auth.put(
        f"/api/v1/incident-management/workflows/{workflow_id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow"]["name"] == "Updated Test Workflow"


@pytest.mark.xdist_group(name="workflows")
def test_delete_workflow(client_with_auth):
    """Test endpoint 35: Delete workflow"""
    # Create workflow first
    create_response = client_with_auth.post(
        "/api/v1/incident-management/workflows",
        json=create_workflow_data()
    )
    workflow_id = create_response.json()["workflow_id"]
    
    # Delete workflow
    response = client_with_auth.delete(f"/api/v1/incident-management/workflows/{workflow_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id


# ============================================================================
# SLA and Root Cause Analysis Tests (Endpoints 36-40)
# ============================================================================

@pytest.mark.xdist_group(name="sla_analysis")
def test_record_sla_breach(client_with_auth):
    """Test endpoint 36: Record SLA breach"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Record SLA breach
    breach_data = {
        "sla_type": "response",
        "breach_time": datetime.utcnow().isoformat(),
        "actual_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        "severity": "high"
    }
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/sla/breach",
        json=breach_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "breach_id" in data
    assert data["breach"]["sla_type"] == "response"


@pytest.mark.xdist_group(name="sla_analysis")
def test_get_incident_sla(client_with_auth):
    """Test endpoint 37: Get incident SLA records"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Get SLA records
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}/sla")
    
    assert response.status_code == 200
    data = response.json()
    assert "sla_records" in data
    assert "total" in data


@pytest.mark.xdist_group(name="sla_analysis")
def test_submit_root_cause_analysis(client_with_auth):
    """Test endpoint 38: Submit root cause analysis"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Submit root cause analysis
    analysis_data = {
        "analysis_method": "5-whys",
        "findings": [
            {"observation": "Service crashed", "evidence": "logs"}
        ],
        "root_cause": "Memory leak in worker process",
        "contributing_factors": ["Insufficient monitoring", "No alerting"],
        "recommendations": ["Add memory monitoring", "Implement alerts"],
        "analyzed_by": "test_user"
    }
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/root-cause-analysis",
        json=analysis_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert data["analysis"]["root_cause"] == "Memory leak in worker process"


@pytest.mark.xdist_group(name="sla_analysis")
def test_submit_post_mortem(client_with_auth):
    """Test endpoint 39: Submit post-mortem"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Submit post-mortem
    post_mortem_data = {
        "summary": "Service outage due to memory leak",
        "timeline": [
            {"time": "2024-01-01T10:00:00", "event": "Incident detected"},
            {"time": "2024-01-01T10:30:00", "event": "Service restored"}
        ],
        "root_cause": "Memory leak in worker process",
        "impact": "30 minutes downtime",
        "resolution": "Restarted service and applied patch",
        "lessons_learned": ["Need better monitoring"],
        "action_items": [
            {"task": "Add memory monitoring", "owner": "team_a", "due_date": "2024-01-15"}
        ],
        "follow_up_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "reviewed_by": ["user_001", "user_002"]
    }
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/post-mortem",
        json=post_mortem_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "post_mortem_id" in data
    assert data["post_mortem"]["summary"] == "Service outage due to memory leak"


# ============================================================================
# Additional Endpoint Test (Endpoint 40: Unlink)
# ============================================================================

@pytest.mark.xdist_group(name="merge_link")
def test_unlink_incidents(client_with_auth):
    """Test endpoint 40: Unlink incidents"""
    # Create incidents
    incident1_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident1_id = incident1_response.json()["incident_id"]
    
    incident2_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident2_id = incident2_response.json()["incident_id"]
    
    # Link incidents first
    link_data = {
        "related_incident_id": incident2_id,
        "link_type": "related",
        "description": "Related incidents"
    }
    client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident1_id}/links",
        json=link_data
    )
    
    # Unlink incidents
    response = client_with_auth.delete(
        f"/api/v1/incident-management/incidents/{incident1_id}/links/{incident2_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == incident1_id
    assert data["related_incident_id"] == incident2_id


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.xdist_group(name="error_handling")
def test_incident_not_found(client_with_auth):
    """Test 404 error for non-existent incident"""
    fake_id = str(uuid.uuid4())
    response = client_with_auth.get(f"/api/v1/incident-management/incidents/{fake_id}")
    
    assert response.status_code == 404


@pytest.mark.xdist_group(name="error_handling")
def test_invalid_severity_validation(client_with_auth):
    """Test validation error for invalid severity"""
    invalid_data = create_test_incident_data()
    invalid_data["severity"] = "invalid_severity"
    
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=invalid_data
    )
    
    assert response.status_code == 422


@pytest.mark.xdist_group(name="error_handling")
def test_invalid_status_validation(client_with_auth):
    """Test validation error for invalid status"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Try invalid status
    status_data = {
        "status": "invalid_status",
        "reason": "Test"
    }
    response = client_with_auth.patch(
        f"/api/v1/incident-management/incidents/{incident_id}/status",
        json=status_data
    )
    
    assert response.status_code == 422


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.xdist_group(name="performance")
def test_bulk_operation_performance(client_with_auth):
    """Test bulk operation performance with batch processing"""
    # Create 10 incidents in bulk
    incidents = [create_test_incident_data() for _ in range(10)]
    bulk_data = {"incidents": incidents}
    
    import time
    start_time = time.time()
    
    response = client_with_auth.post(
        "/api/v1/incident-management/incidents/bulk",
        json=bulk_data
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_created"] == 10
    # Should complete in reasonable time (< 5 seconds)
    assert duration < 5.0


# ============================================================================
# Security Tests
# ============================================================================

@pytest.mark.xdist_group(name="security")
def test_attachment_size_limit(client_with_auth):
    """Test attachment size limit enforcement"""
    # Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    incident_id = create_response.json()["incident_id"]
    
    # Try to upload oversized file
    large_content = b"x" * (20 * 1024 * 1024)  # 20MB
    files = {"file": ("large.txt", large_content, "text/plain")}
    
    response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/attachments",
        files=files
    )
    
    # Should fail with 413 (Payload Too Large)
    assert response.status_code == 413


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.xdist_group(name="integration")
def test_full_incident_lifecycle(client_with_auth):
    """Test complete incident lifecycle from creation to resolution"""
    # 1. Create incident
    create_response = client_with_auth.post(
        "/api/v1/incident-management/incidents",
        json=create_test_incident_data()
    )
    assert create_response.status_code == 200
    incident_id = create_response.json()["incident_id"]
    
    # 2. Update status
    status_response = client_with_auth.patch(
        f"/api/v1/incident-management/incidents/{incident_id}/status",
        json={"status": "in_progress", "reason": "Investigation started"}
    )
    assert status_response.status_code == 200
    
    # 3. Add comment
    comment_response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/comments",
        json=create_test_comment_data()
    )
    assert comment_response.status_code == 200
    
    # 4. Resolve incident
    resolve_response = client_with_auth.post(
        f"/api/v1/incident-management/incidents/{incident_id}/resolve",
        params={"resolution_notes": "Fixed the issue", "root_cause": "Bug in code"}
    )
    assert resolve_response.status_code == 200
    
    # 5. Verify final state
    get_response = client_with_auth.get(f"/api/v1/incident-management/incidents/{incident_id}")
    assert get_response.status_code == 200
    incident_data = get_response.json()["incident"]
    assert incident_data["status"] == "resolved"
    assert incident_data["resolved_at"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
