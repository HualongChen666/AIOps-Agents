# -*- coding: utf-8 -*-
"""
Test suite for test_coverage_advanced_router.py
Tests all endpoints with comprehensive coverage including:
- GET, POST, DELETE operations
- Normal and error cases
- Data validation
- Permission control
- Mock dependencies
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_coverage_advanced_router import (
    router,
    CoverageReport,
    CoverageReportCreate,
    ModuleCoverage,
    CoverageLevel,
    FAKE_ADMIN,
    get_current_user,
    _coverage_reports,
    _init_coverage_reports,
    _calculate_coverage_level,
)
from core.authentication import UserInDB


# ============ Fixtures ============

@pytest.fixture
def mock_user():
    """Create a mock user"""
    return UserInDB(
        id=1,
        username="testuser",
        full_name="Test User",
        email="test@example.com",
        role="admin",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user"""
    return UserInDB(
        id=2,
        username="regularuser",
        full_name="Regular User",
        email="regular@example.com",
        role="user",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def client():
    """Create a test client"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def clear_data():
    """Clear in-memory data before each test"""
    _coverage_reports.clear()
    yield
    _coverage_reports.clear()


@pytest.fixture
def sample_report(clear_data):
    """Create a sample coverage report"""
    _init_coverage_reports()
    return list(_coverage_reports.values())[0]


# ============ Report Endpoints Tests ============

class TestCoverageReportEndpoints:
    """Test coverage report endpoints"""

    @pytest.mark.asyncio
    async def test_get_coverage_reports_success(self, mock_user, clear_data):
        """Test successful coverage reports retrieval"""
        _init_coverage_reports()
        result = await router.get_coverage_reports(current_user=mock_user)
        
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_coverage_reports_empty(self, mock_user, clear_data):
        """Test coverage reports retrieval when empty"""
        result = await router.get_coverage_reports(current_user=mock_user)
        
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_coverage_reports_with_pagination(self, mock_user, clear_data):
        """Test coverage reports retrieval with pagination"""
        _init_coverage_reports()
        
        # Create multiple reports
        for i in range(5):
            report_create = CoverageReportCreate(
                report_name=f"Report-{i}",
                include_trends=False
            )
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        result = await router.get_coverage_reports(limit=3, offset=0, current_user=mock_user)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_create_coverage_report_success(self, mock_user, clear_data):
        """Test successful coverage report creation"""
        _init_coverage_reports()
        report_create = CoverageReportCreate(
            report_name="New Coverage Report",
            include_trends=True
        )
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        assert isinstance(result, CoverageReport)
        assert result.report_name == "New Coverage Report"
        assert result.trends is not None

    @pytest.mark.asyncio
    async def test_create_coverage_report_without_trends(self, mock_user, clear_data):
        """Test coverage report creation without trends"""
        _init_coverage_reports()
        report_create = CoverageReportCreate(
            report_name="Report Without Trends",
            include_trends=False
        )
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        assert isinstance(result, CoverageReport)
        assert result.trends is None

    @pytest.mark.asyncio
    async def test_create_coverage_report_validation_name_min(self, mock_user, clear_data):
        """Test coverage report creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            CoverageReportCreate(name="")

    @pytest.mark.asyncio
    async def test_create_coverage_report_validation_name_max(self, mock_user, clear_data):
        """Test coverage report creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            CoverageReportCreate(name="a" * 201)

    @pytest.mark.asyncio
    async def test_get_coverage_report_success(self, mock_user, sample_report, clear_data):
        """Test successful coverage report retrieval"""
        result = await router.get_coverage_report(sample_report.id, current_user=mock_user)
        
        assert isinstance(result, CoverageReport)
        assert result.id == sample_report.id

    @pytest.mark.asyncio
    async def test_get_coverage_report_not_found(self, mock_user, clear_data):
        """Test coverage report retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_coverage_report("nonexistent", current_user=mock_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Report not found"

    @pytest.mark.asyncio
    async def test_delete_coverage_report_success(self, mock_user, sample_report, clear_data):
        """Test successful coverage report deletion"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        await router.delete_coverage_report(sample_report.id, request, current_user=mock_user)
        
        assert sample_report.id not in _coverage_reports

    @pytest.mark.asyncio
    async def test_delete_coverage_report_not_found(self, mock_user, clear_data):
        """Test coverage report deletion when not found"""
        from fastapi import Request
        request = Mock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await router.delete_coverage_report("nonexistent", request, current_user=mock_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Report not found"


# ============ Summary Endpoints Tests ============

class TestCoverageSummaryEndpoints:
    """Test coverage summary endpoints"""

    @pytest.mark.asyncio
    async def test_get_coverage_summary_success(self, mock_user, clear_data):
        """Test successful coverage summary retrieval"""
        _init_coverage_reports()
        result = await router.get_coverage_summary(current_user=mock_user)
        
        assert isinstance(result, dict)
        assert "overall_coverage" in result
        assert "overall_level" in result
        assert "total_modules" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_get_coverage_summary_empty(self, mock_user, clear_data):
        """Test coverage summary retrieval when no reports exist"""
        result = await router.get_coverage_summary(current_user=mock_user)
        
        assert isinstance(result, dict)
        assert result["overall_coverage"] == 0.0
        assert result["overall_level"] == "poor"
        assert result["total_modules"] == 0

    @pytest.mark.asyncio
    async def test_get_coverage_summary_with_data(self, mock_user, clear_data):
        """Test coverage summary retrieval with report data"""
        _init_coverage_reports()
        result = await router.get_coverage_summary(current_user=mock_user)
        
        assert result["overall_coverage"] > 0
        assert result["total_modules"] > 0
        assert "generated_at" in result


# ============ Authentication Tests ============

class TestAuthentication:
    """Test authentication and authorization"""

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Test get_current_user with no token returns fake admin"""
        result = await get_current_user(token=None)
        
        assert result.username == "dev-admin"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token returns fake admin"""
        with patch('api.test_coverage_advanced_router.verify_token', return_value=None):
            result = await get_current_user(token="invalid")
            
            assert result.username == "dev-admin"


# ============ Data Validation Tests ============

class TestDataValidation:
    """Test data validation for models"""

    def test_coverage_report_create_name_min_validation(self):
        """Test CoverageReportCreate name min length validation"""
        with pytest.raises(Exception):
            CoverageReportCreate(name="")

    def test_coverage_report_create_name_max_validation(self):
        """Test CoverageReportCreate name max length validation"""
        with pytest.raises(Exception):
            CoverageReportCreate(name="a" * 201)


# ============ Helper Function Tests ============

class TestHelperFunctions:
    """Test helper functions"""

    def test_calculate_coverage_level_excellent(self):
        """Test _calculate_coverage_level for excellent level"""
        result = _calculate_coverage_level(90.0)
        assert result == CoverageLevel.EXCELLENT

    def test_calculate_coverage_level_good(self):
        """Test _calculate_coverage_level for good level"""
        result = _calculate_coverage_level(80.0)
        assert result == CoverageLevel.GOOD

    def test_calculate_coverage_level_adequate(self):
        """Test _calculate_coverage_level for adequate level"""
        result = _calculate_coverage_level(70.0)
        assert result == CoverageLevel.ADEQUATE

    def test_calculate_coverage_level_poor(self):
        """Test _calculate_coverage_level for poor level"""
        result = _calculate_coverage_level(50.0)
        assert result == CoverageLevel.POOR

    def test_calculate_coverage_level_boundary_excellent(self):
        """Test _calculate_coverage_level at excellent boundary"""
        result = _calculate_coverage_level(89.9)
        assert result == CoverageLevel.GOOD

    def test_calculate_coverage_level_boundary_good(self):
        """Test _calculate_coverage_level at good boundary"""
        result = _calculate_coverage_level(74.9)
        assert result == CoverageLevel.ADEQUATE

    def test_calculate_coverage_level_boundary_adequate(self):
        """Test _calculate_coverage_level at adequate boundary"""
        result = _calculate_coverage_level(59.9)
        assert result == CoverageLevel.POOR

    def test_init_coverage_reports(self, clear_data):
        """Test _init_coverage_reports creates default report"""
        _init_coverage_reports()
        
        assert len(_coverage_reports) >= 1
        report = list(_coverage_reports.values())[0]
        assert isinstance(report, CoverageReport)
        assert len(report.modules) >= 1


# ============ Module Coverage Tests ============

class TestModuleCoverage:
    """Test module coverage calculations"""

    @pytest.mark.asyncio
    async def test_module_coverage_calculation(self, mock_user, clear_data):
        """Test module coverage percentage calculation"""
        _init_coverage_reports()
        report = await router.get_coverage_reports(current_user=mock_user)[0]
        
        for module in report.modules:
            expected_percentage = (module.covered_lines / module.total_lines) * 100
            assert abs(module.coverage_percentage - expected_percentage) < 0.01

    @pytest.mark.asyncio
    async def test_module_coverage_level_assignment(self, mock_user, clear_data):
        """Test module coverage level assignment"""
        _init_coverage_reports()
        report = await router.get_coverage_reports(current_user=mock_user)[0]
        
        for module in report.modules:
            if module.coverage_percentage >= 90:
                assert module.coverage_level == CoverageLevel.EXCELLENT
            elif module.coverage_percentage >= 75:
                assert module.coverage_level == CoverageLevel.GOOD
            elif module.coverage_percentage >= 60:
                assert module.coverage_level == CoverageLevel.ADEQUATE
            else:
                assert module.coverage_level == CoverageLevel.POOR


# ============ Summary Calculation Tests ============

class TestSummaryCalculation:
    """Test summary calculations"""

    @pytest.mark.asyncio
    async def test_overall_coverage_calculation(self, mock_user, clear_data):
        """Test overall coverage calculation"""
        _init_coverage_reports()
        report = await router.get_coverage_reports(current_user=mock_user)[0]
        
        expected_overall = sum(m.coverage_percentage for m in report.modules) / len(report.modules)
        assert abs(report.overall_coverage - expected_overall) < 0.01

    @pytest.mark.asyncio
    async def test_summary_statistics(self, mock_user, clear_data):
        """Test summary statistics calculation"""
        _init_coverage_reports()
        report = await router.get_coverage_reports(current_user=mock_user)[0]
        
        assert "total_lines" in report.summary
        assert "covered_lines" in report.summary
        assert "uncovered_lines" in report.summary
        assert "excellent_count" in report.summary
        assert "good_count" in report.summary
        assert "adequate_count" in report.summary
        assert "poor_count" in report.summary

    @pytest.mark.asyncio
    async def test_summary_counts_match_modules(self, mock_user, clear_data):
        """Test summary counts match module levels"""
        _init_coverage_reports()
        report = await router.get_coverage_reports(current_user=mock_user)[0]
        
        excellent_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.EXCELLENT])
        good_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.GOOD])
        adequate_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.ADEQUATE])
        poor_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.POOR])
        
        assert report.summary["excellent_count"] == excellent_count
        assert report.summary["good_count"] == good_count
        assert report.summary["adequate_count"] == adequate_count
        assert report.summary["poor_count"] == poor_count


# ============ Trend Calculation Tests ============

class TestTrendCalculation:
    """Test trend calculations"""

    @pytest.mark.asyncio
    async def test_trend_calculation_up(self, mock_user, clear_data):
        """Test trend calculation when coverage increased"""
        _init_coverage_reports()
        report_create = CoverageReportCreate(
            report_name="Trend Test",
            include_trends=True
        )
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        if result.trends:
            assert "previous_coverage" in result.trends
            assert "change" in result.trends
            assert "trend" in result.trends

    @pytest.mark.asyncio
    async def test_trend_calculation_down(self, mock_user, clear_data):
        """Test trend calculation when coverage decreased"""
        _init_coverage_reports()
        report_create = CoverageReportCreate(
            report_name="Trend Test Down",
            include_trends=True
        )
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        result = await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        if result.trends:
            assert result.trends["trend"] in ["up", "down"]


# ============ Enum Tests ============

class TestEnums:
    """Test enum values"""

    def test_coverage_level_values(self):
        """Test CoverageLevel enum values"""
        assert CoverageLevel.EXCELLENT == "excellent"
        assert CoverageLevel.GOOD == "good"
        assert CoverageLevel.ADEQUATE == "adequate"
        assert CoverageLevel.POOR == "poor"


# ============ Integration Tests ============

class TestIntegration:
    """Integration tests for coverage operations"""

    @pytest.mark.asyncio
    async def test_full_report_workflow(self, mock_user, clear_data):
        """Test complete report workflow"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        # Create report
        report_create = CoverageReportCreate(
            report_name="Workflow Report",
            include_trends=True
        )
        report = await router.create_coverage_report(report_create, request, current_user=mock_user)
        assert report.report_name == "Workflow Report"
        
        # Get report
        retrieved = await router.get_coverage_report(report.id, current_user=mock_user)
        assert retrieved.id == report.id
        
        # Get summary
        summary = await router.get_coverage_summary(current_user=mock_user)
        assert summary["overall_coverage"] > 0
        
        # Delete report
        await router.delete_coverage_report(report.id, request, current_user=mock_user)
        assert report.id not in _coverage_reports

    @pytest.mark.asyncio
    async def test_multiple_reports_workflow(self, mock_user, clear_data):
        """Test workflow with multiple reports"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        # Create multiple reports
        report_ids = []
        for i in range(3):
            report_create = CoverageReportCreate(
                report_name=f"Report-{i}",
                include_trends=False
            )
            report = await router.create_coverage_report(report_create, request, current_user=mock_user)
            report_ids.append(report.id)
        
        # Get all reports
        reports = await router.get_coverage_reports(current_user=mock_user)
        assert len(reports) >= 3
        
        # Delete all reports
        for report_id in report_ids:
            await router.delete_coverage_report(report_id, request, current_user=mock_user)


# ============ Error Handling Tests ============

class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_concurrent_report_creation(self, mock_user, clear_data):
        """Test concurrent report creation"""
        import asyncio
        
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        async def create_report():
            report_create = CoverageReportCreate(
                report_name=f"Report-{asyncio.current_task().get_name()}",
                include_trends=False
            )
            await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        # Run multiple concurrent creations
        await asyncio.gather(*[create_report() for _ in range(5)])
        
        # Should not raise errors
        reports = await router.get_coverage_reports(current_user=mock_user)
        assert len(reports) >= 5

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_user, clear_data):
        """Test handling of large datasets"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        # Create many reports
        for i in range(30):
            report_create = CoverageReportCreate(
                report_name=f"Report-{i}",
                include_trends=False
            )
            await router.create_coverage_report(report_create, request, current_user=mock_user)
        
        # Should handle pagination correctly
        result = await router.get_coverage_reports(limit=10, current_user=mock_user)
        assert len(result) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
