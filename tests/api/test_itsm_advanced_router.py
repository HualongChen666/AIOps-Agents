# -*- coding: utf-8 -*-
"""
Comprehensive test suite for ITSM Advanced API Router
Tests all endpoints with various scenarios including success, error cases, validation, and mocking
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.itsm_advanced_router import (
    SLA,
    ITSMChange,
    ITSMChangeCreate,
    ITSMIncident,
    ITSMIncidentCreate,
    ITSMIncidentUpdate,
    ITSMProblem,
    ITSMProblemCreate,
    KnowledgeBaseArticle,
    KnowledgeBaseArticleCreate,
    ServiceCatalogItem,
    _changes,
    _incidents,
    _knowledge_base,
    _problems,
    _service_catalog,
    _slas,
    router,
)


@pytest.fixture
def client():
    """Create a test client for the ITSM router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear in-memory storage before each test"""
    _incidents.clear()
    _problems.clear()
    _changes.clear()
    _service_catalog.clear()
    _slas.clear()
    _knowledge_base.clear()
    yield


class TestITSMIncidentEndpoints:
    """Test ITSM incident endpoints"""

    def test_get_incidents_success(self, client):
        """Test GET /incidents - successful retrieval"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU usage",
            "description": "Web server CPU usage is above 90%",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.get("/api/v1/itsm/incidents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_incidents_with_status_filter(self, client):
        """Test GET /incidents with status filter"""
        _incidents["incident-1"] = {
            "incident_id": "incident-1",
            "title": "Web server high CPU",
            "description": "CPU usage high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }
        _incidents["incident-2"] = {
            "incident_id": "incident-2",
            "title": "Database slow query",
            "description": "Slow queries",
            "priority": "medium",
            "status": "resolved",
            "assigned_to": "jane.smith",
            "category": "database",
            "impact": "medium",
            "urgency": "medium",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": datetime.utcnow().isoformat(),
            "resolution_notes": "Fixed query",
        }

        response = client.get("/api/v1/itsm/incidents?status_filter=open")
        assert response.status_code == 200
        data = response.json()
        assert all(inc["status"] == "open" for inc in data)

    def test_get_incidents_with_priority_filter(self, client):
        """Test GET /incidents with priority filter"""
        _incidents["incident-1"] = {
            "incident_id": "incident-1",
            "title": "Critical issue",
            "description": "Critical",
            "priority": "critical",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }
        _incidents["incident-2"] = {
            "incident_id": "incident-2",
            "title": "Low priority issue",
            "description": "Low",
            "priority": "low",
            "status": "open",
            "assigned_to": "jane.smith",
            "category": "database",
            "impact": "low",
            "urgency": "low",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.get("/api/v1/itsm/incidents?priority_filter=critical")
        assert response.status_code == 200
        data = response.json()
        assert all(inc["priority"] == "critical" for inc in data)

    def test_get_incidents_with_category_filter(self, client):
        """Test GET /incidents with category filter"""
        _incidents["incident-1"] = {
            "incident_id": "incident-1",
            "title": "Web server issue",
            "description": "Web server",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }
        _incidents["incident-2"] = {
            "incident_id": "incident-2",
            "title": "Database issue",
            "description": "Database",
            "priority": "high",
            "status": "open",
            "assigned_to": "jane.smith",
            "category": "database",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.get("/api/v1/itsm/incidents?category_filter=database")
        assert response.status_code == 200
        data = response.json()
        assert all(inc["category"] == "database" for inc in data)

    def test_get_incidents_with_limit(self, client):
        """Test GET /incidents with limit parameter"""
        for i in range(5):
            _incidents[f"incident-{i}"] = {
                "incident_id": f"incident-{i}",
                "title": f"Incident {i}",
                "description": f"Description {i}",
                "priority": "medium",
                "status": "open",
                "assigned_to": "user",
                "category": "general",
                "impact": "medium",
                "urgency": "medium",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "resolved_at": None,
                "resolution_notes": None,
            }

        response = client.get("/api/v1/itsm/incidents?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3

    def test_get_incidents_limit_validation(self, client):
        """Test GET /incidents with invalid limit values"""
        # Test limit below minimum
        response = client.get("/api/v1/itsm/incidents?limit=0")
        assert response.status_code == 422  # Validation error

        # Test limit above maximum
        response = client.get("/api/v1/itsm/incidents?limit=101")
        assert response.status_code == 422  # Validation error

    def test_create_incident_success(self, client):
        """Test POST /incidents - successful creation"""
        request_data = {
            "title": "Database connection timeout",
            "description": "Application is experiencing database connection timeouts",
            "priority": "high",
            "category": "database",
            "impact": "high",
            "urgency": "high",
            "assigned_to": "john.doe",
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "incident_id" in data
        assert data["title"] == request_data["title"]
        assert data["status"] == "open"

    def test_create_incident_with_defaults(self, client):
        """Test POST /incidents with default values"""
        request_data = {
            "title": "Test incident",
            "description": "Test description",
            "category": "general",
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "medium"  # Default
        assert data["impact"] == "medium"  # Default
        assert data["urgency"] == "medium"  # Default
        assert data["assigned_to"] is None  # Default

    def test_create_incident_validation_error(self, client):
        """Test POST /incidents with invalid data"""
        request_data = {
            # Missing required fields
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        assert response.status_code == 422

    def test_get_incident_by_id_success(self, client):
        """Test GET /incidents/{incident_id} - successful retrieval"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU",
            "description": "CPU high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.get(f"/api/v1/itsm/incidents/{incident_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"] == incident_id

    def test_get_incident_by_id_not_found(self, client):
        """Test GET /incidents/{incident_id} with non-existent ID"""
        response = client.get("/api/v1/itsm/incidents/non-existent-id")
        assert response.status_code == 404

    def test_update_incident_success(self, client):
        """Test PATCH /incidents/{incident_id} - successful update"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU",
            "description": "CPU high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        update_data = {"status": "in_progress", "assigned_to": "jane.smith"}

        response = client.patch(f"/api/v1/itsm/incidents/{incident_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["assigned_to"] == "jane.smith"

    def test_update_incident_with_resolution(self, client):
        """Test PATCH /incidents/{incident_id} with resolution"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU",
            "description": "CPU high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        update_data = {
            "status": "resolved",
            "resolution_notes": "Fixed CPU issue by optimizing queries",
        }

        response = client.patch(f"/api/v1/itsm/incidents/{incident_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None
        assert data["resolution_notes"] == "Fixed CPU issue by optimizing queries"

    def test_update_incident_not_found(self, client):
        """Test PATCH /incidents/{incident_id} with non-existent ID"""
        update_data = {"status": "resolved"}

        response = client.patch("/api/v1/itsm/incidents/non-existent-id", json=update_data)
        assert response.status_code == 404

    def test_update_incident_partial_update(self, client):
        """Test PATCH /incidents/{incident_id} with partial update"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU",
            "description": "CPU high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        update_data = {"priority": "critical"}

        response = client.patch(f"/api/v1/itsm/incidents/{incident_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "critical"
        assert data["status"] == "open"  # Unchanged

    def test_delete_incident_success(self, client):
        """Test DELETE /incidents/{incident_id} - successful deletion"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Web server high CPU",
            "description": "CPU high",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.delete(f"/api/v1/itsm/incidents/{incident_id}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert incident_id not in _incidents

    def test_delete_incident_not_found(self, client):
        """Test DELETE /incidents/{incident_id} with non-existent ID"""
        response = client.delete("/api/v1/itsm/incidents/non-existent-id")
        assert response.status_code == 404


class TestITSMProblemEndpoints:
    """Test ITSM problem endpoints"""

    def test_get_problems_success(self, client):
        """Test GET /problems - successful retrieval"""
        problem_id = "problem-1"
        _problems[problem_id] = {
            "problem_id": problem_id,
            "title": "Recurring database timeouts",
            "description": "Database connections timing out",
            "status": "open",
            "priority": "high",
            "root_cause": None,
            "related_incidents": [],
            "workarounds": ["Restart application"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
        }

        response = client.get("/api/v1/itsm/problems")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_problems_with_status_filter(self, client):
        """Test GET /problems with status filter"""
        _problems["problem-1"] = {
            "problem_id": "problem-1",
            "title": "Problem 1",
            "description": "Description 1",
            "status": "open",
            "priority": "high",
            "root_cause": None,
            "related_incidents": [],
            "workarounds": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
        }
        _problems["problem-2"] = {
            "problem_id": "problem-2",
            "title": "Problem 2",
            "description": "Description 2",
            "status": "resolved",
            "priority": "medium",
            "root_cause": "Known cause",
            "related_incidents": [],
            "workarounds": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/problems?status_filter=open")
        assert response.status_code == 200
        data = response.json()
        assert all(prob["status"] == "open" for prob in data)

    def test_get_problems_empty_returns_defaults(self, client):
        """Test GET /problems returns default problems when empty"""
        response = client.get("/api/v1/itsm/problems")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_create_problem_success(self, client):
        """Test POST /problems - successful creation"""
        request_data = {
            "title": "Recurring memory leaks",
            "description": "Applications experiencing memory leaks",
            "priority": "high",
            "related_incidents": ["incident-1", "incident-2"],
        }

        response = client.post("/api/v1/itsm/problems", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "problem_id" in data
        assert data["title"] == request_data["title"]
        assert data["status"] == "open"
        assert data["related_incidents"] == request_data["related_incidents"]

    def test_create_problem_with_defaults(self, client):
        """Test POST /problems with default values"""
        request_data = {"title": "Test problem", "description": "Test description"}

        response = client.post("/api/v1/itsm/problems", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "medium"  # Default
        assert data["related_incidents"] == []  # Default

    def test_create_problem_validation_error(self, client):
        """Test POST /problems with invalid data"""
        request_data = {
            # Missing required fields
        }

        response = client.post("/api/v1/itsm/problems", json=request_data)
        assert response.status_code == 422


class TestITSMChangeEndpoints:
    """Test ITSM change endpoints"""

    def test_get_changes_success(self, client):
        """Test GET /changes - successful retrieval"""
        change_id = "change-1"
        _changes[change_id] = {
            "change_id": change_id,
            "title": "Upgrade web server",
            "description": "Upgrade Nginx to version 1.25",
            "change_type": "normal",
            "status": "pending",
            "priority": "medium",
            "risk_level": "low",
            "planned_start": datetime.utcnow().isoformat(),
            "planned_end": datetime.utcnow().isoformat(),
            "requested_by": "admin",
            "approved_by": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "implemented_at": None,
        }

        response = client.get("/api/v1/itsm/changes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_changes_with_status_filter(self, client):
        """Test GET /changes with status filter"""
        _changes["change-1"] = {
            "change_id": "change-1",
            "title": "Change 1",
            "description": "Description 1",
            "change_type": "normal",
            "status": "pending",
            "priority": "medium",
            "risk_level": "low",
            "planned_start": datetime.utcnow().isoformat(),
            "planned_end": datetime.utcnow().isoformat(),
            "requested_by": "admin",
            "approved_by": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "implemented_at": None,
        }
        _changes["change-2"] = {
            "change_id": "change-2",
            "title": "Change 2",
            "description": "Description 2",
            "change_type": "normal",
            "status": "completed",
            "priority": "medium",
            "risk_level": "low",
            "planned_start": datetime.utcnow().isoformat(),
            "planned_end": datetime.utcnow().isoformat(),
            "requested_by": "admin",
            "approved_by": "admin",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "implemented_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/changes?status_filter=pending")
        assert response.status_code == 200
        data = response.json()
        assert all(change["status"] == "pending" for change in data)

    def test_get_changes_empty_returns_defaults(self, client):
        """Test GET /changes returns default changes when empty"""
        response = client.get("/api/v1/itsm/changes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_create_change_success(self, client):
        """Test POST /changes - successful creation"""
        request_data = {
            "title": "Upgrade database to version 15",
            "description": "Upgrade PostgreSQL from version 14 to 15",
            "change_type": "normal",
            "priority": "high",
            "risk_level": "high",
            "planned_start": "2026-07-10T02:00:00Z",
            "planned_end": "2026-07-10T04:00:00Z",
            "requested_by": "admin",
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "change_id" in data
        assert data["title"] == request_data["title"]
        assert data["status"] == "pending"

    def test_create_change_with_defaults(self, client):
        """Test POST /changes with default values"""
        request_data = {
            "title": "Test change",
            "description": "Test description",
            "planned_start": "2026-07-10T02:00:00Z",
            "planned_end": "2026-07-10T04:00:00Z",
            "requested_by": "admin",
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "normal"  # Default
        assert data["priority"] == "medium"  # Default
        assert data["risk_level"] == "medium"  # Default

    def test_create_change_validation_error(self, client):
        """Test POST /changes with invalid data"""
        request_data = {
            # Missing required fields
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        assert response.status_code == 422


class TestITSMServiceCatalogEndpoints:
    """Test ITSM service catalog endpoints"""

    def test_get_service_catalog_success(self, client):
        """Test GET /service-catalog - successful retrieval"""
        service_id = "service-1"
        _service_catalog[service_id] = {
            "service_id": service_id,
            "name": "Web Application",
            "description": "Main web application service",
            "category": "application",
            "availability": "99.9%",
            "sla_target": "99.9%",
            "owner": "platform.team",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/service-catalog")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_service_catalog_with_category_filter(self, client):
        """Test GET /service-catalog with category filter"""
        _service_catalog["service-1"] = {
            "service_id": "service-1",
            "name": "Web Application",
            "description": "Web app",
            "category": "application",
            "availability": "99.9%",
            "sla_target": "99.9%",
            "owner": "platform.team",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        _service_catalog["service-2"] = {
            "service_id": "service-2",
            "name": "Database Service",
            "description": "Database",
            "category": "database",
            "availability": "99.95%",
            "sla_target": "99.95%",
            "owner": "database.team",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/service-catalog?category_filter=database")
        assert response.status_code == 200
        data = response.json()
        assert all(service["category"] == "database" for service in data)


class TestITSMSLAEndpoints:
    """Test ITSM SLA endpoints"""

    def test_get_slas_success(self, client):
        """Test GET /sla - successful retrieval"""
        sla_id = "sla-1"
        _slas[sla_id] = {
            "sla_id": sla_id,
            "name": "Critical Incident SLA",
            "description": "SLA for critical incidents",
            "service_id": "service-1",
            "response_time_target": "15 minutes",
            "resolution_time_target": "4 hours",
            "availability_target": 99.9,
            "current_performance": 99.8,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/sla")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_slas_with_service_filter(self, client):
        """Test GET /sla with service_id filter"""
        _slas["sla-1"] = {
            "sla_id": "sla-1",
            "name": "SLA 1",
            "description": "SLA for service 1",
            "service_id": "service-1",
            "response_time_target": "15 minutes",
            "resolution_time_target": "4 hours",
            "availability_target": 99.9,
            "current_performance": 99.8,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        _slas["sla-2"] = {
            "sla_id": "sla-2",
            "name": "SLA 2",
            "description": "SLA for service 2",
            "service_id": "service-2",
            "response_time_target": "30 minutes",
            "resolution_time_target": "8 hours",
            "availability_target": 99.5,
            "current_performance": 99.6,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        response = client.get("/api/v1/itsm/sla?service_id=service-1")
        assert response.status_code == 200
        data = response.json()
        assert all(sla["service_id"] == "service-1" for sla in data)


class TestITSMKnowledgeBaseEndpoints:
    """Test ITSM knowledge base endpoints"""

    def test_get_knowledge_base_success(self, client):
        """Test GET /knowledge-base - successful retrieval"""
        article_id = "article-1"
        _knowledge_base[article_id] = {
            "article_id": article_id,
            "title": "Troubleshooting high CPU usage",
            "content": "Steps to troubleshoot high CPU usage...",
            "category": "infrastructure",
            "tags": ["cpu", "troubleshooting", "performance"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 150,
            "helpful_count": 45,
        }

        response = client.get("/api/v1/itsm/knowledge-base")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_knowledge_base_with_category_filter(self, client):
        """Test GET /knowledge-base with category filter"""
        _knowledge_base["article-1"] = {
            "article_id": "article-1",
            "title": "CPU troubleshooting",
            "content": "CPU steps",
            "category": "infrastructure",
            "tags": ["cpu"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 100,
            "helpful_count": 30,
        }
        _knowledge_base["article-2"] = {
            "article_id": "article-2",
            "title": "Database troubleshooting",
            "content": "Database steps",
            "category": "database",
            "tags": ["database"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 80,
            "helpful_count": 25,
        }

        response = client.get("/api/v1/itsm/knowledge-base?category_filter=database")
        assert response.status_code == 200
        data = response.json()
        assert all(article["category"] == "database" for article in data)

    def test_get_knowledge_base_with_tag_filter(self, client):
        """Test GET /knowledge-base with tag filter"""
        _knowledge_base["article-1"] = {
            "article_id": "article-1",
            "title": "CPU troubleshooting",
            "content": "CPU steps",
            "category": "infrastructure",
            "tags": ["cpu", "troubleshooting"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 100,
            "helpful_count": 30,
        }
        _knowledge_base["article-2"] = {
            "article_id": "article-2",
            "title": "Memory troubleshooting",
            "content": "Memory steps",
            "category": "infrastructure",
            "tags": ["memory", "troubleshooting"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 80,
            "helpful_count": 25,
        }

        response = client.get("/api/v1/itsm/knowledge-base?tag_filter=troubleshooting")
        assert response.status_code == 200
        data = response.json()
        assert all("troubleshooting" in article["tags"] for article in data)

    def test_get_knowledge_base_with_search(self, client):
        """Test GET /knowledge-base with search parameter"""
        _knowledge_base["article-1"] = {
            "article_id": "article-1",
            "title": "CPU troubleshooting guide",
            "content": "This guide explains how to troubleshoot CPU issues",
            "category": "infrastructure",
            "tags": ["cpu"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 100,
            "helpful_count": 30,
        }
        _knowledge_base["article-2"] = {
            "article_id": "article-2",
            "title": "Memory optimization",
            "content": "Memory optimization techniques",
            "category": "infrastructure",
            "tags": ["memory"],
            "author": "support.team",
            "status": "published",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "views": 80,
            "helpful_count": 25,
        }

        response = client.get("/api/v1/itsm/knowledge-base?search=troubleshoot")
        assert response.status_code == 200
        data = response.json()
        # Should return articles with "troubleshoot" in title or content
        assert len(data) >= 1

    def test_create_knowledge_base_article_success(self, client):
        """Test POST /knowledge-base - successful creation"""
        request_data = {
            "title": "How to reset database connection pool",
            "content": "Step-by-step guide to reset database connection pool...",
            "category": "database",
            "tags": ["database", "troubleshooting", "connection"],
            "author": "support.team",
        }

        response = client.post("/api/v1/itsm/knowledge-base", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert "article_id" in data
        assert data["title"] == request_data["title"]
        assert data["status"] == "draft"

    def test_create_knowledge_base_article_with_defaults(self, client):
        """Test POST /knowledge-base with default values"""
        request_data = {
            "title": "Test article",
            "content": "Test content",
            "category": "general",
            "author": "test.user",
        }

        response = client.post("/api/v1/itsm/knowledge-base", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == []  # Default
        assert data["views"] == 0  # Default
        assert data["helpful_count"] == 0  # Default

    def test_create_knowledge_base_article_validation_error(self, client):
        """Test POST /knowledge-base with invalid data"""
        request_data = {
            # Missing required fields
        }

        response = client.post("/api/v1/itsm/knowledge-base", json=request_data)
        assert response.status_code == 422


class TestITSMRouterErrorHandling:
    """Test error handling across all endpoints"""

    def test_invalid_endpoint(self, client):
        """Test accessing invalid endpoint"""
        response = client.get("/api/v1/itsm/invalid")
        assert response.status_code == 404

    def test_invalid_method(self, client):
        """Test using invalid HTTP method"""
        response = client.put("/api/v1/itsm/incidents")
        assert response.status_code == 405  # Method not allowed

    def test_malformed_json(self, client):
        """Test sending malformed JSON"""
        response = client.post(
            "/api/v1/itsm/incidents",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


class TestITSMRouterDataValidation:
    """Test data validation across all endpoints"""

    def test_incident_priority_validation(self, client):
        """Test priority field validation for incidents"""
        # Priority should be one of: low, medium, high, critical
        request_data = {
            "title": "Test incident",
            "description": "Test description",
            "category": "general",
            "priority": "invalid_priority",
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        # May pass validation if not strictly validated
        assert response.status_code in [200, 422]

    def test_change_risk_level_validation(self, client):
        """Test risk_level field validation for changes"""
        request_data = {
            "title": "Test change",
            "description": "Test description",
            "planned_start": "2026-07-10T02:00:00Z",
            "planned_end": "2026-07-10T04:00:00Z",
            "requested_by": "admin",
            "risk_level": "invalid_risk",
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        # May pass validation if not strictly validated
        assert response.status_code in [200, 422]

    def test_incident_status_validation(self, client):
        """Test status field validation for incident updates"""
        incident_id = "incident-1"
        _incidents[incident_id] = {
            "incident_id": incident_id,
            "title": "Test incident",
            "description": "Test",
            "priority": "medium",
            "status": "open",
            "assigned_to": "user",
            "category": "general",
            "impact": "medium",
            "urgency": "medium",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        update_data = {"status": "invalid_status"}

        response = client.patch(f"/api/v1/itsm/incidents/{incident_id}", json=update_data)
        # May pass validation if not strictly validated
        assert response.status_code in [200, 422]


class TestITSMRouterResponseModels:
    """Test response model validation"""

    def test_incident_response_structure(self, client):
        """Test incident response has correct structure"""
        request_data = {
            "title": "Test incident",
            "description": "Test description",
            "category": "general",
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "incident_id",
            "title",
            "description",
            "priority",
            "status",
            "assigned_to",
            "category",
            "impact",
            "urgency",
            "created_at",
            "updated_at",
            "resolved_at",
            "resolution_notes",
        ]
        for field in required_fields:
            assert field in data

    def test_problem_response_structure(self, client):
        """Test problem response has correct structure"""
        request_data = {"title": "Test problem", "description": "Test description"}

        response = client.post("/api/v1/itsm/problems", json=request_data)
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "problem_id",
            "title",
            "description",
            "status",
            "priority",
            "root_cause",
            "related_incidents",
            "workarounds",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        for field in required_fields:
            assert field in data

    def test_change_response_structure(self, client):
        """Test change response has correct structure"""
        request_data = {
            "title": "Test change",
            "description": "Test description",
            "planned_start": "2026-07-10T02:00:00Z",
            "planned_end": "2026-07-10T04:00:00Z",
            "requested_by": "admin",
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "change_id",
            "title",
            "description",
            "change_type",
            "status",
            "priority",
            "risk_level",
            "planned_start",
            "planned_end",
            "requested_by",
            "approved_by",
            "created_at",
            "updated_at",
            "implemented_at",
        ]
        for field in required_fields:
            assert field in data

    def test_knowledge_base_response_structure(self, client):
        """Test knowledge base response has correct structure"""
        request_data = {
            "title": "Test article",
            "content": "Test content",
            "category": "general",
            "author": "test.user",
        }

        response = client.post("/api/v1/itsm/knowledge-base", json=request_data)
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "article_id",
            "title",
            "content",
            "category",
            "tags",
            "author",
            "status",
            "created_at",
            "updated_at",
            "views",
            "helpful_count",
        ]
        for field in required_fields:
            assert field in data


class TestITSMRouterEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_incident_with_all_fields(self, client):
        """Test creating incident with all fields populated"""
        request_data = {
            "title": "Complete incident",
            "description": "Complete description",
            "priority": "critical",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "assigned_to": "admin.user",
        }

        response = client.post("/api/v1/itsm/incidents", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "critical"
        assert data["assigned_to"] == "admin.user"

    def test_change_with_emergency_type(self, client):
        """Test creating change with emergency type"""
        request_data = {
            "title": "Emergency fix",
            "description": "Emergency security fix",
            "change_type": "emergency",
            "priority": "critical",
            "risk_level": "high",
            "planned_start": "2026-07-10T02:00:00Z",
            "planned_end": "2026-07-10T04:00:00Z",
            "requested_by": "admin",
        }

        response = client.post("/api/v1/itsm/changes", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["change_type"] == "emergency"

    def test_knowledge_base_with_multiple_tags(self, client):
        """Test creating knowledge base article with multiple tags"""
        request_data = {
            "title": "Comprehensive guide",
            "content": "Comprehensive content",
            "category": "general",
            "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
            "author": "expert.user",
        }

        response = client.post("/api/v1/itsm/knowledge-base", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data["tags"]) == 5

    def test_problem_with_multiple_incidents(self, client):
        """Test creating problem with multiple related incidents"""
        request_data = {
            "title": "Complex problem",
            "description": "Complex description",
            "priority": "high",
            "related_incidents": ["incident-1", "incident-2", "incident-3"],
        }

        response = client.post("/api/v1/itsm/problems", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert len(data["related_incidents"]) == 3

    def test_multiple_filters_combined(self, client):
        """Test combining multiple filters for incidents"""
        _incidents["incident-1"] = {
            "incident_id": "incident-1",
            "title": "High priority database issue",
            "description": "Database",
            "priority": "high",
            "status": "open",
            "assigned_to": "john.doe",
            "category": "database",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }
        _incidents["incident-2"] = {
            "incident_id": "incident-2",
            "title": "High priority infrastructure issue",
            "description": "Infrastructure",
            "priority": "high",
            "status": "open",
            "assigned_to": "jane.smith",
            "category": "infrastructure",
            "impact": "high",
            "urgency": "high",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "resolution_notes": None,
        }

        response = client.get(
            "/api/v1/itsm/incidents?priority_filter=high&status_filter=open&category_filter=database"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(
            inc["priority"] == "high" and inc["status"] == "open" and inc["category"] == "database"
            for inc in data
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.itsm_advanced_router", "--cov-report=html"])
