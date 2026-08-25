# -*- coding: utf-8 -*-
"""
Test suite for Business Impact Advanced Router
业务影响高级路由测试套件
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.business_impact_advanced_router import (
    AnalysisStatusEnum,
    CreateAnalysisRequest,
    CreateDependencyRequest,
    CreateReportRequest,
    ImpactSeverityEnum,
    UpdateAnalysisRequest,
    _generate_id,
    _load_json_file,
    _now,
    _save_json_file,
    router,
)
from core.api_response_standard import ErrorCode, create_error_response, create_success_response


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for testing"""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def mock_business_impact_engine():
    """Mock the business impact engine"""
    engine = Mock()
    engine.assess_business_impact = AsyncMock(
        return_value={
            "name": "test-service",
            "impactScore": 7.5,
            "revenueImpact": 10000,
            "affectedUsers": 500,
            "status": "degraded",
        }
    )
    engine.list_business_impact_services = AsyncMock(
        return_value=[
            {
                "id": "svc-001",
                "name": "payment-service",
                "impactScore": 8.5,
                "revenueImpact": 50000,
                "affectedUsers": 1000,
                "status": "degraded",
                "category": "critical",
            },
            {
                "id": "svc-002",
                "name": "api-service",
                "impactScore": 3.2,
                "revenueImpact": 1000,
                "affectedUsers": 100,
                "status": "healthy",
                "category": "normal",
            },
        ]
    )
    engine.list_business_impact_ux_metrics = AsyncMock(
        return_value=[
            {
                "metric": "page_load_time",
                "value": 2.5,
                "threshold": 3.0,
                "status": "ok",
            },
            {
                "metric": "error_rate",
                "value": 0.01,
                "threshold": 0.05,
                "status": "ok",
            },
        ]
    )
    return engine


@pytest.fixture
def sample_analysis():
    """Sample analysis data"""
    return {
        "id": "BIA-12345678",
        "service_name": "payment-service",
        "analysis_type": "full",
        "time_range": "1h",
        "include_dependencies": True,
        "include_ux_metrics": True,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": {
            "impact_assessment": {
                "impactScore": 8.5,
                "revenueImpact": 50000,
            },
            "dependencies": [],
            "ux_metrics": [],
        },
    }


@pytest.fixture
def sample_dependency():
    """Sample dependency data"""
    return {
        "id": "DEP-12345678",
        "source_service": "api-service",
        "target_service": "database-service",
        "dependency_type": "api_call",
        "criticality": "high",
        "description": "API service depends on database",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_report():
    """Sample report data"""
    return {
        "id": "RPT-12345678",
        "title": "Weekly Business Impact Report",
        "service_names": ["payment-service", "api-service"],
        "time_range": "24h",
        "include_recommendations": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_services": 2,
            "total_revenue_impact": 51000,
            "total_affected_users": 1100,
            "avg_impact_score": 5.85,
        },
        "service_data": [],
        "recommendations": [],
    }


# Helper function tests
class TestHelperFunctions:
    """Test helper functions"""

    def test_generate_id(self):
        """Test ID generation"""
        id1 = _generate_id("BIA")
        id2 = _generate_id("BIA")
        assert id1.startswith("BIA-")
        assert id2.startswith("BIA-")
        assert id1 != id2
        assert len(id1) == 12

    def test_now(self):
        """Test timestamp generation"""
        timestamp = _now()
        assert isinstance(timestamp, str)
        assert "T" in timestamp or " " in timestamp

    def test_load_json_file_not_exists(self, tmp_path):
        """Test loading non-existent file"""
        non_existent = tmp_path / "non_existent.json"
        result = _load_json_file(non_existent)
        assert result == []

    def test_load_json_file_valid(self, tmp_path):
        """Test loading valid JSON file"""
        test_file = tmp_path / "test.json"
        test_data = [{"id": "1"}, {"id": "2"}]
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
        result = _load_json_file(test_file)
        assert result == test_data

    def test_load_json_file_invalid(self, tmp_path):
        """Test loading invalid JSON file"""
        test_file = tmp_path / "invalid.json"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("invalid json")
        result = _load_json_file(test_file)
        assert result == []

    def test_save_json_file(self, tmp_path):
        """Test saving JSON file"""
        test_file = tmp_path / "test.json"
        test_data = [{"id": "1"}, {"id": "2"}]
        _save_json_file(test_file, test_data)
        assert test_file.exists()
        with open(test_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == test_data


# Analysis endpoints tests
class TestAnalysisEndpoints:
    """Test analysis-related endpoints"""

    def test_get_analysis_list_empty(self, client, tmp_path):
        """Test getting analysis list when none exist"""
        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", tmp_path / "analysis.json"):
            response = client.get("/api/v1/business-impact/analysis")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []
            assert data["data"]["total"] == 0

    def test_get_analysis_list_with_data(self, client, tmp_path, sample_analysis):
        """Test getting analysis list with data"""
        analysis_file = tmp_path / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump([sample_analysis], f)

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            response = client.get("/api/v1/business-impact/analysis")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1
            assert data["data"]["total"] == 1

    def test_get_analysis_list_with_service_filter(self, client, tmp_path, sample_analysis):
        """Test getting analysis list with service name filter"""
        sample_analysis["service_name"] = "payment-service"
        analysis_file = tmp_path / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump([sample_analysis], f)

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            response = client.get("/api/v1/business-impact/analysis?service_name=payment-service")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_analysis_list_with_status_filter(self, client, tmp_path, sample_analysis):
        """Test getting analysis list with status filter"""
        sample_analysis["status"] = "completed"
        analysis_file = tmp_path / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump([sample_analysis], f)

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            response = client.get("/api/v1/business-impact/analysis?status=completed")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_analysis_list_pagination(self, client, tmp_path):
        """Test getting analysis list with pagination"""
        analyses = []
        for i in range(25):
            analyses.append(
                {
                    "id": f"BIA-{i:08d}",
                    "service_name": f"service-{i}",
                    "status": "completed",
                }
            )
        analysis_file = tmp_path / "analysis.json"
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analyses, f)

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            response = client.get("/api/v1/business-impact/analysis?limit=10&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 10
            assert data["data"]["total"] == 25

    def test_create_analysis_success(self, client, tmp_path, mock_business_impact_engine):
        """Test creating an analysis successfully"""
        analysis_file = tmp_path / "analysis.json"
        dependencies_file = tmp_path / "dependencies.json"

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
                with patch(
                    "api.business_impact_advanced_router.assess_business_impact",
                    mock_business_impact_engine.assess_business_impact,
                ):
                    with patch(
                        "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                        mock_business_impact_engine.list_business_impact_ux_metrics,
                    ):
                        response = client.post(
                            "/api/v1/business-impact/analysis",
                            json={
                                "service_name": "payment-service",
                                "analysis_type": "full",
                                "time_range": "1h",
                                "include_dependencies": True,
                                "include_ux_metrics": True,
                            },
                        )
                        # API returns 201 for successful creation
                        assert response.status_code == 201
                        data = response.json()
                        assert data["success"] is True
                        assert data["data"]["service_name"] == "payment-service"
                        assert data["data"]["status"] == "completed"

    def test_create_analysis_minimal(self, client, tmp_path, mock_business_impact_engine):
        """Test creating an analysis with minimal parameters"""
        analysis_file = tmp_path / "analysis.json"
        dependencies_file = tmp_path / "dependencies.json"

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
                with patch(
                    "api.business_impact_advanced_router.assess_business_impact",
                    mock_business_impact_engine.assess_business_impact,
                ):
                    with patch(
                        "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                        mock_business_impact_engine.list_business_impact_ux_metrics,
                    ):
                        response = client.post(
                            "/api/v1/business-impact/analysis",
                            json={
                                "service_name": "api-service",
                            },
                        )
                        # API returns 201 for successful creation
                        assert response.status_code == 201
                        data = response.json()
                        assert data["success"] is True

    def test_create_analysis_validation_error(self, client, tmp_path):
        """Test creating an analysis with validation error"""
        analysis_file = tmp_path / "analysis.json"
        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            response = client.post(
                "/api/v1/business-impact/analysis",
                json={
                    "service_name": "",  # Empty name should fail
                },
            )
            # FastAPI validation returns 422
            assert response.status_code == 422  # Validation error

    def test_create_analysis_engine_failure(self, client, tmp_path):
        """Test creating an analysis when engine fails"""
        analysis_file = tmp_path / "analysis.json"
        dependencies_file = tmp_path / "dependencies.json"

        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
                with patch(
                    "api.business_impact_advanced_router.assess_business_impact",
                    side_effect=Exception("Engine error"),
                ):
                    response = client.post(
                        "/api/v1/business-impact/analysis",
                        json={
                            "service_name": "payment-service",
                        },
                    )
                    # API returns 201 even for error responses
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is False


# Metrics endpoint tests
class TestMetricsEndpoint:
    """Test metrics endpoint"""

    def test_get_business_impact_metrics(self, client, mock_business_impact_engine):
        """Test getting business impact metrics"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            with patch(
                "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                mock_business_impact_engine.list_business_impact_ux_metrics,
            ):
                response = client.get("/api/v1/business-impact/metrics")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "summary" in data["data"]
                assert "services" in data["data"]
                assert "ux_metrics" in data["data"]

    def test_get_business_impact_metrics_with_service_filter(
        self, client, mock_business_impact_engine
    ):
        """Test getting metrics for specific service"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            with patch(
                "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                mock_business_impact_engine.list_business_impact_ux_metrics,
            ):
                response = client.get(
                    "/api/v1/business-impact/metrics?service_name=payment-service"
                )
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                # Should only return payment-service
                assert len(data["data"]["services"]) == 1
                assert data["data"]["services"][0]["name"] == "payment-service"

    def test_get_business_impact_metrics_service_not_found(
        self, client, mock_business_impact_engine
    ):
        """Test getting metrics for non-existent service"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            with patch(
                "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                mock_business_impact_engine.list_business_impact_ux_metrics,
            ):
                response = client.get(
                    "/api/v1/business-impact/metrics?service_name=non-existent-service"
                )
                # API returns 200 even for error responses
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert "服务不存在" in data["message"]

    def test_get_business_impact_metrics_with_time_range(self, client, mock_business_impact_engine):
        """Test getting metrics with time range"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            with patch(
                "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                mock_business_impact_engine.list_business_impact_ux_metrics,
            ):
                response = client.get("/api/v1/business-impact/metrics?time_range=24h")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["time_range"] == "24h"

    def test_get_business_impact_metrics_engine_failure(self, client):
        """Test getting metrics when engine fails"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            side_effect=Exception("Engine error"),
        ):
            response = client.get("/api/v1/business-impact/metrics")
            # API returns 200 even for error responses
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


# Dependencies endpoints tests
class TestDependenciesEndpoints:
    """Test dependency-related endpoints"""

    def test_get_dependencies_empty(self, client, tmp_path):
        """Test getting dependencies when none exist"""
        with patch(
            "api.business_impact_advanced_router.DEPENDENCIES_FILE", tmp_path / "dependencies.json"
        ):
            response = client.get("/api/v1/business-impact/dependencies")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_get_dependencies_with_data(self, client, tmp_path, sample_dependency):
        """Test getting dependencies with data"""
        dependencies_file = tmp_path / "dependencies.json"
        with open(dependencies_file, "w", encoding="utf-8") as f:
            json.dump([sample_dependency], f)

        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.get("/api/v1/business-impact/dependencies")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_dependencies_with_source_filter(self, client, tmp_path, sample_dependency):
        """Test getting dependencies with source service filter"""
        sample_dependency["source_service"] = "api-service"
        dependencies_file = tmp_path / "dependencies.json"
        with open(dependencies_file, "w", encoding="utf-8") as f:
            json.dump([sample_dependency], f)

        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.get("/api/v1/business-impact/dependencies?source_service=api-service")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_dependencies_with_target_filter(self, client, tmp_path, sample_dependency):
        """Test getting dependencies with target service filter"""
        sample_dependency["target_service"] = "database-service"
        dependencies_file = tmp_path / "dependencies.json"
        with open(dependencies_file, "w", encoding="utf-8") as f:
            json.dump([sample_dependency], f)

        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.get(
                "/api/v1/business-impact/dependencies?target_service=database-service"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_dependencies_with_criticality_filter(self, client, tmp_path, sample_dependency):
        """Test getting dependencies with criticality filter"""
        sample_dependency["criticality"] = "high"
        dependencies_file = tmp_path / "dependencies.json"
        with open(dependencies_file, "w", encoding="utf-8") as f:
            json.dump([sample_dependency], f)

        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.get("/api/v1/business-impact/dependencies?criticality=high")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_create_dependency_success(self, client, tmp_path):
        """Test creating a dependency successfully"""
        dependencies_file = tmp_path / "dependencies.json"
        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.post(
                "/api/v1/business-impact/dependencies",
                json={
                    "source_service": "api-service",
                    "target_service": "database-service",
                    "dependency_type": "api_call",
                    "criticality": "high",
                    "description": "API depends on database",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert data["data"]["source_service"] == "api-service"
            assert data["data"]["target_service"] == "database-service"

    def test_create_dependency_duplicate(self, client, tmp_path, sample_dependency):
        """Test creating a duplicate dependency"""
        dependencies_file = tmp_path / "dependencies.json"
        with open(dependencies_file, "w", encoding="utf-8") as f:
            json.dump([sample_dependency], f)

        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.post(
                "/api/v1/business-impact/dependencies",
                json={
                    "source_service": sample_dependency["source_service"],
                    "target_service": sample_dependency["target_service"],
                    "dependency_type": "api_call",
                    "criticality": "high",
                },
            )
            # API returns 201 even for error responses
            assert response.status_code == 201
            data = response.json()
            assert data["success"] is False
            assert "依赖关系已存在" in data["message"]

    def test_create_dependency_validation_error(self, client, tmp_path):
        """Test creating a dependency with validation error"""
        dependencies_file = tmp_path / "dependencies.json"
        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            response = client.post(
                "/api/v1/business-impact/dependencies",
                json={
                    "source_service": "",  # Empty name
                    "target_service": "",  # Empty name
                },
            )
            assert response.status_code == 422  # Validation error


# Reports endpoints tests
class TestReportsEndpoints:
    """Test report-related endpoints"""

    def test_get_reports_empty(self, client, tmp_path):
        """Test getting reports when none exist"""
        with patch("api.business_impact_advanced_router.REPORTS_FILE", tmp_path / "reports.json"):
            response = client.get("/api/v1/business-impact/reports")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_get_reports_with_data(self, client, tmp_path, sample_report):
        """Test getting reports with data"""
        reports_file = tmp_path / "reports.json"
        with open(reports_file, "w", encoding="utf-8") as f:
            json.dump([sample_report], f)

        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            response = client.get("/api/v1/business-impact/reports")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_reports_pagination(self, client, tmp_path):
        """Test getting reports with pagination"""
        reports = []
        for i in range(25):
            reports.append(
                {
                    "id": f"RPT-{i:08d}",
                    "title": f"Report {i}",
                }
            )
        reports_file = tmp_path / "reports.json"
        with open(reports_file, "w", encoding="utf-8") as f:
            json.dump(reports, f)

        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            response = client.get("/api/v1/business-impact/reports?limit=10&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 10
            assert data["data"]["total"] == 25

    def test_create_report_success(self, client, tmp_path, mock_business_impact_engine):
        """Test creating a report successfully"""
        reports_file = tmp_path / "reports.json"

        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            with patch(
                "api.business_impact_advanced_router.assess_business_impact",
                mock_business_impact_engine.assess_business_impact,
            ):
                response = client.post(
                    "/api/v1/business-impact/reports",
                    json={
                        "title": "Weekly Report",
                        "service_names": ["payment-service", "api-service"],
                        "time_range": "24h",
                        "include_recommendations": True,
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["title"] == "Weekly Report"
                assert len(data["data"]["service_names"]) == 2

    def test_create_report_without_recommendations(
        self, client, tmp_path, mock_business_impact_engine
    ):
        """Test creating a report without recommendations"""
        reports_file = tmp_path / "reports.json"

        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            with patch(
                "api.business_impact_advanced_router.assess_business_impact",
                mock_business_impact_engine.assess_business_impact,
            ):
                response = client.post(
                    "/api/v1/business-impact/reports",
                    json={
                        "title": "Simple Report",
                        "service_names": ["api-service"],
                        "include_recommendations": False,
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["include_recommendations"] is False
                assert data["data"]["recommendations"] == []

    def test_create_report_validation_error(self, client, tmp_path):
        """Test creating a report with validation error"""
        reports_file = tmp_path / "reports.json"
        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            response = client.post(
                "/api/v1/business-impact/reports",
                json={
                    "title": "",  # Empty title
                    "service_names": [],  # Empty list
                },
            )
            assert response.status_code == 422  # Validation error

    def test_create_report_with_failed_service(self, client, tmp_path, mock_business_impact_engine):
        """Test creating a report when one service assessment fails"""
        reports_file = tmp_path / "reports.json"

        # Make the second call fail
        mock_business_impact_engine.assess_business_impact = AsyncMock(
            side_effect=[
                {"name": "service-1", "impactScore": 5.0},
                Exception("Service not found"),
            ]
        )

        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            with patch(
                "api.business_impact_advanced_router.assess_business_impact",
                mock_business_impact_engine.assess_business_impact,
            ):
                response = client.post(
                    "/api/v1/business-impact/reports",
                    json={
                        "title": "Partial Report",
                        "service_names": ["service-1", "service-2"],
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                # Should only include successful service
                assert len(data["data"]["service_data"]) == 1


# Impact scores endpoint tests
class TestImpactScoresEndpoint:
    """Test impact scores endpoint"""

    def test_get_impact_scores(self, client, mock_business_impact_engine):
        """Test getting impact scores"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            response = client.get("/api/v1/business-impact/impact-scores")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "impact_scores" in data["data"]
            assert "statistics" in data["data"]

    def test_get_impact_scores_with_service_filter(self, client, mock_business_impact_engine):
        """Test getting impact scores for specific service"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            response = client.get(
                "/api/v1/business-impact/impact-scores?service_name=payment-service"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["impact_scores"]) == 1
            assert data["data"]["impact_scores"][0]["service_name"] == "payment-service"

    def test_get_impact_scores_with_threshold(self, client, mock_business_impact_engine):
        """Test getting impact scores with threshold filter"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            response = client.get("/api/v1/business-impact/impact-scores?threshold=5.0")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Should only return scores >= 5.0
            for score in data["data"]["impact_scores"]:
                assert score["impact_score"] >= 5.0

    def test_get_impact_scores_sorted(self, client, mock_business_impact_engine):
        """Test that impact scores are sorted by score descending"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            response = client.get("/api/v1/business-impact/impact-scores")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            scores = data["data"]["impact_scores"]
            # Check if sorted descending
            for i in range(len(scores) - 1):
                assert scores[i]["impact_score"] >= scores[i + 1]["impact_score"]

    def test_get_impact_scores_statistics(self, client, mock_business_impact_engine):
        """Test impact scores statistics calculation"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            response = client.get("/api/v1/business-impact/impact-scores")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            stats = data["data"]["statistics"]
            assert "count" in stats
            assert "average" in stats
            assert "max" in stats
            assert "min" in stats

    def test_get_impact_scores_engine_failure(self, client):
        """Test getting impact scores when engine fails"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            side_effect=Exception("Engine error"),
        ):
            response = client.get("/api/v1/business-impact/impact-scores")
            # API returns 200 even for error responses
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


# Data validation tests
class TestDataValidation:
    """Test data validation"""

    def test_create_analysis_request_valid(self):
        """Test valid CreateAnalysisRequest"""
        request = CreateAnalysisRequest(
            service_name="payment-service",
            analysis_type="full",
            time_range="1h",
            include_dependencies=True,
            include_ux_metrics=True,
        )
        assert request.service_name == "payment-service"
        assert request.include_dependencies is True

    def test_create_analysis_request_defaults(self):
        """Test CreateAnalysisRequest with defaults"""
        request = CreateAnalysisRequest(
            service_name="api-service",
        )
        assert request.analysis_type == "full"
        assert request.time_range == "1h"
        assert request.include_dependencies is True
        assert request.include_ux_metrics is True

    def test_create_analysis_request_invalid_name(self):
        """Test CreateAnalysisRequest with invalid name"""
        with pytest.raises(ValueError):
            CreateAnalysisRequest(
                service_name="",  # Empty name
            )

    def test_update_analysis_request_valid(self):
        """Test valid UpdateAnalysisRequest"""
        request = UpdateAnalysisRequest(
            status=AnalysisStatusEnum.COMPLETED,
            result={"impact_score": 8.5},
        )
        assert request.status == AnalysisStatusEnum.COMPLETED

    def test_create_dependency_request_valid(self):
        """Test valid CreateDependencyRequest"""
        request = CreateDependencyRequest(
            source_service="api-service",
            target_service="database-service",
            dependency_type="api_call",
            criticality=ImpactSeverityEnum.HIGH,
            description="API depends on database",
        )
        assert request.source_service == "api-service"
        assert request.criticality == ImpactSeverityEnum.HIGH

    def test_create_dependency_request_defaults(self):
        """Test CreateDependencyRequest with defaults"""
        request = CreateDependencyRequest(
            source_service="api-service",
            target_service="database-service",
        )
        assert request.dependency_type == "api_call"
        assert request.criticality == ImpactSeverityEnum.MEDIUM

    def test_create_report_request_valid(self):
        """Test valid CreateReportRequest"""
        request = CreateReportRequest(
            title="Weekly Report",
            service_names=["service-1", "service-2"],
            time_range="24h",
            include_recommendations=True,
        )
        assert request.title == "Weekly Report"
        assert len(request.service_names) == 2

    def test_create_report_request_defaults(self):
        """Test CreateReportRequest with defaults"""
        request = CreateReportRequest(
            title="Daily Report",
            service_names=["service-1"],
        )
        assert request.time_range == "24h"
        assert request.include_recommendations is True

    def test_create_report_request_empty_services(self):
        """Test CreateReportRequest with empty services list"""
        with pytest.raises(ValueError):
            CreateReportRequest(
                title="Report",
                service_names=[],  # Empty list
            )


# Error handling tests
class TestErrorHandling:
    """Test error handling"""

    def test_exception_handling_in_get_analysis_list(self, client, tmp_path):
        """Test exception handling in get_analysis_list"""
        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", tmp_path / "analysis.json"):
            with patch(
                "api.business_impact_advanced_router._load_json_file",
                side_effect=Exception("Test error"),
            ):
                response = client.get("/api/v1/business-impact/analysis")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False

    def test_exception_handling_in_create_analysis(self, client, tmp_path):
        """Test exception handling in create_analysis"""
        analysis_file = tmp_path / "analysis.json"
        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            with patch(
                "api.business_impact_advanced_router._save_json_file",
                side_effect=Exception("Save error"),
            ):
                response = client.post(
                    "/api/v1/business-impact/analysis",
                    json={"service_name": "test-service"},
                )
                # API returns 201 even for error responses
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is False

    def test_exception_handling_in_get_metrics(self, client):
        """Test exception handling in get_metrics"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            side_effect=Exception("Engine error"),
        ):
            response = client.get("/api/v1/business-impact/metrics")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


# Permission and access control tests
class TestPermissions:
    """Test permission and access control (placeholder for future implementation)"""

    def test_api_accessible_without_auth(self, client):
        """Test that API is accessible without authentication (current state)"""
        response = client.get("/api/v1/business-impact/analysis")
        assert response.status_code in [200, 500]


# Integration tests
class TestIntegration:
    """Integration tests"""

    def test_full_analysis_workflow(self, client, tmp_path, mock_business_impact_engine):
        """Test full analysis workflow: create, list, filter"""
        analysis_file = tmp_path / "analysis.json"
        dependencies_file = tmp_path / "dependencies.json"

        # Create analysis
        with patch("api.business_impact_advanced_router.ANALYSIS_FILE", analysis_file):
            with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
                with patch(
                    "api.business_impact_advanced_router.assess_business_impact",
                    mock_business_impact_engine.assess_business_impact,
                ):
                    with patch(
                        "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                        mock_business_impact_engine.list_business_impact_ux_metrics,
                    ):
                        create_response = client.post(
                            "/api/v1/business-impact/analysis",
                            json={
                                "service_name": "payment-service",
                            },
                        )
                        # API returns 201 for successful creation
                        assert create_response.status_code == 201
                        assert create_response.json()["success"] is True

                        # List all
                        list_response = client.get("/api/v1/business-impact/analysis")
                        assert list_response.status_code == 200
                        assert len(list_response.json()["data"]["items"]) == 1

                        # Filter by service
                        filter_response = client.get(
                            "/api/v1/business-impact/analysis?service_name=payment-service"
                        )
                        assert filter_response.status_code == 200
                        assert len(filter_response.json()["data"]["items"]) == 1

    def test_dependency_and_report_workflow(self, client, tmp_path, mock_business_impact_engine):
        """Test creating dependencies and then a report"""
        dependencies_file = tmp_path / "dependencies.json"
        reports_file = tmp_path / "reports.json"

        # Create dependency
        with patch("api.business_impact_advanced_router.DEPENDENCIES_FILE", dependencies_file):
            dep_response = client.post(
                "/api/v1/business-impact/dependencies",
                json={
                    "source_service": "api-service",
                    "target_service": "database-service",
                },
            )
            assert dep_response.status_code == 201

        # Create report
        with patch("api.business_impact_advanced_router.REPORTS_FILE", reports_file):
            with patch(
                "api.business_impact_advanced_router.assess_business_impact",
                mock_business_impact_engine.assess_business_impact,
            ):
                report_response = client.post(
                    "/api/v1/business-impact/reports",
                    json={
                        "title": "Dependency Report",
                        "service_names": ["api-service", "database-service"],
                    },
                )
                assert report_response.status_code == 201
                assert report_response.json()["success"] is True

    def test_metrics_and_impact_scores_workflow(self, client, mock_business_impact_engine):
        """Test getting metrics and impact scores"""
        with patch(
            "api.business_impact_advanced_router.list_business_impact_services",
            mock_business_impact_engine.list_business_impact_services,
        ):
            with patch(
                "api.business_impact_advanced_router.list_business_impact_ux_metrics",
                mock_business_impact_engine.list_business_impact_ux_metrics,
            ):
                # Get metrics
                metrics_response = client.get("/api/v1/business-impact/metrics")
                assert metrics_response.status_code == 200
                assert metrics_response.json()["success"] is True

                # Get impact scores
                scores_response = client.get("/api/v1/business-impact/impact-scores")
                assert scores_response.status_code == 200
                assert scores_response.json()["success"] is True

                # Verify data consistency
                metrics_data = metrics_response.json()["data"]
                scores_data = scores_response.json()["data"]
                assert (
                    metrics_data["summary"]["total_services"] == scores_data["statistics"]["count"]
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
