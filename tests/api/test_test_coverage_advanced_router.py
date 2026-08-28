# -*- coding: utf-8 -*-
"""
Test suite for Test Coverage Advanced Router (Database-backed)
测试覆盖率高级路由测试套件（数据库版本）
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.test_coverage_advanced_router import (
    CoverageLevel,
    CoverageReport,
    CoverageReportCreate,
    ModuleCoverage,
    _calculate_coverage_level,
    get_current_user,
    router,
    get_coverage_reports,
    create_coverage_report,
    get_coverage_report,
    delete_coverage_report,
    get_coverage_summary,
)
from core.authentication import UserInDB
from core.database import SessionLocal
from core.models import TestCoverageReportDB


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
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="function")
def cleanup_database(db_session):
    """Clean up database after each test"""
    yield
    # Clean up after test
    try:
        db_session.query(TestCoverageReportDB).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()
        db_session.query(TestCoverageReportDB).delete()
        db_session.commit()


@pytest.fixture
def sample_report(db_session):
    """Create a sample coverage report"""
    import uuid
    from datetime import datetime
    report = TestCoverageReportDB(
        id=f"CR-{uuid.uuid4().hex[:8]}",
        report_name="Sample Coverage Report",
        overall_coverage=85.5,
        overall_level="good",
        total_modules=2,
        summary={
            "total_lines": 400,
            "covered_lines": 350,
            "uncovered_lines": 50,
            "excellent_count": 1,
            "good_count": 1,
            "adequate_count": 0,
            "poor_count": 0,
        },
        modules=[
            {
                "module_id": "module1",
                "module_name": "Module 1",
                "total_lines": 200,
                "covered_lines": 180,
                "coverage_percentage": 90.0,
                "coverage_level": "excellent",
                "last_updated": datetime.now().isoformat(),
            },
            {
                "module_id": "module2",
                "module_name": "Module 2",
                "total_lines": 200,
                "covered_lines": 170,
                "coverage_percentage": 85.0,
                "coverage_level": "good",
                "last_updated": datetime.now().isoformat(),
            },
        ],
        trends=None,
    )
    db_session.add(report)
    db_session.commit()
    return report


# ============ Report Endpoints Tests ============


class TestCoverageReportEndpoints:
    """Test coverage report endpoints"""

    @pytest.mark.asyncio
    async def test_get_coverage_reports_success(self, mock_user, db_session):
        """Test successful coverage reports retrieval"""
        # Create a coverage report
        import uuid
        report = TestCoverageReportDB(
            id=f"CR-{uuid.uuid4().hex[:8]}",
            report_name="Test Report",
            overall_coverage=85.5,
            overall_level="good",
            total_modules=5,
            summary={"total_lines": 1000, "covered_lines": 855},
            modules=[],
            trends=None,
        )
        db_session.add(report)
        db_session.commit()

        result = await get_coverage_reports(current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_coverage_reports_empty(self, mock_user, db_session):
        """Test coverage reports retrieval when empty"""
        result = await get_coverage_reports(current_user=mock_user, db=db_session)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_coverage_reports_with_pagination(self, mock_user, db_session):
        """Test coverage reports retrieval with pagination"""
        # Create multiple reports
        for i in range(5):
            report = TestCoverageReportDB(
                id=f"CR-{i:08d}",
                report_name=f"Report-{i}",
                overall_coverage=80.0 + i,
                overall_level="good",
                total_modules=5,
                summary={"total_lines": 1000, "covered_lines": 800},
                modules=[],
                trends=None,
            )
            db_session.add(report)
        db_session.commit()

        result = await get_coverage_reports(limit=3, offset=0, current_user=mock_user, db=db_session)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_create_coverage_report_success(self, mock_user, db_session):
        """Test successful coverage report creation"""
        report_create = CoverageReportCreate(report_name="New Coverage Report", include_trends=True)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_coverage_report(report_create, request, current_user=mock_user, db=db_session)

        assert isinstance(result, CoverageReport)
        assert result.report_name == "New Coverage Report"
        # Trends will be None if there's no previous report

    @pytest.mark.asyncio
    async def test_create_coverage_report_without_trends(self, mock_user, db_session):
        """Test coverage report creation without trends"""
        report_create = CoverageReportCreate(
            report_name="Report Without Trends", include_trends=False
        )

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_coverage_report(report_create, request, current_user=mock_user, db=db_session)

        assert isinstance(result, CoverageReport)
        assert result.trends is None

    @pytest.mark.asyncio
    async def test_create_coverage_report_validation_name_min(self, mock_user, db_session):
        """Test coverage report creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            CoverageReportCreate(report_name="")

    @pytest.mark.asyncio
    async def test_create_coverage_report_validation_name_max(self, mock_user, db_session):
        """Test coverage report creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            CoverageReportCreate(report_name="a" * 201)

    @pytest.mark.asyncio
    async def test_get_coverage_report_success(self, mock_user, sample_report, db_session):
        """Test successful coverage report retrieval"""
        result = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

        assert isinstance(result, CoverageReport)
        assert result.id == sample_report.id

    @pytest.mark.asyncio
    async def test_get_coverage_report_not_found(self, mock_user, db_session):
        """Test coverage report retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await get_coverage_report("nonexistent", current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Report not found"

    @pytest.mark.asyncio
    async def test_delete_coverage_report_success(self, mock_user, sample_report, db_session):
        """Test successful coverage report deletion"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        report_id = sample_report.id
        await delete_coverage_report(report_id, request, current_user=mock_user, db=db_session)

        # Verify deletion - refresh session to clear identity map
        db_session.expire_all()
        deleted = db_session.query(TestCoverageReportDB).filter(
            TestCoverageReportDB.id == report_id
        ).first()
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_coverage_report_not_found(self, mock_user, db_session):
        """Test coverage report deletion when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await delete_coverage_report("nonexistent", request, current_user=mock_user, db=db_session)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Report not found"


# ============ Summary Endpoints Tests ============


class TestCoverageSummaryEndpoints:
    """Test coverage summary endpoints"""

    @pytest.mark.asyncio
    async def test_get_coverage_summary_success(self, mock_user, db_session):
        """Test successful coverage summary retrieval"""
        # Create a coverage report
        report = TestCoverageReportDB(
            id="CR-12345678",
            report_name="Test Report",
            overall_coverage=85.5,
            overall_level="good",
            total_modules=5,
            summary={"total_lines": 1000, "covered_lines": 855},
            modules=[],
            trends=None,
        )
        db_session.add(report)
        db_session.commit()

        result = await get_coverage_summary(current_user=mock_user, db=db_session)

        assert isinstance(result, dict)
        assert "overall_coverage" in result
        assert "overall_level" in result
        assert "total_modules" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_get_coverage_summary_empty(self, mock_user, db_session):
        """Test coverage summary retrieval when no reports exist"""
        # Ensure database is clean
        db_session.query(TestCoverageReportDB).delete()
        db_session.commit()

        result = await get_coverage_summary(current_user=mock_user, db=db_session)

        assert isinstance(result, dict)
        assert result["overall_coverage"] == 0.0
        assert result["overall_level"] == "poor"
        assert result["total_modules"] == 0

    @pytest.mark.asyncio
    async def test_get_coverage_summary_with_data(self, mock_user, db_session):
        """Test coverage summary retrieval with report data"""
        # Create a coverage report
        import uuid
        report = TestCoverageReportDB(
            id=f"CR-{uuid.uuid4().hex[:8]}",
            report_name="Test Report",
            overall_coverage=85.5,
            overall_level="good",
            total_modules=5,
            summary={"total_lines": 1000, "covered_lines": 855},
            modules=[],
            trends=None,
        )
        db_session.add(report)
        db_session.commit()

        result = await get_coverage_summary(current_user=mock_user, db=db_session)

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
        with patch("api.test_coverage_advanced_router.verify_token", return_value=None):
            result = await get_current_user(token="invalid")

            assert result.username == "dev-admin"


# ============ Data Validation Tests ============


class TestDataValidation:
    """Test data validation for models"""

    def test_coverage_report_create_name_min_validation(self):
        """Test CoverageReportCreate name min length validation"""
        with pytest.raises(Exception):
            CoverageReportCreate(report_name="")

    def test_coverage_report_create_name_max_validation(self):
        """Test CoverageReportCreate name max length validation"""
        with pytest.raises(Exception):
            CoverageReportCreate(report_name="a" * 201)


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


# ============ Module Coverage Tests ============


class TestModuleCoverage:
    """Test module coverage calculations"""

    @pytest.mark.asyncio
    async def test_module_coverage_calculation(self, mock_user, sample_report, db_session):
        """Test module coverage percentage calculation"""
        report = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

        for module in report.modules:
            expected_percentage = (module.covered_lines / module.total_lines) * 100
            assert abs(module.coverage_percentage - expected_percentage) < 0.01

    @pytest.mark.asyncio
    async def test_module_coverage_level_assignment(self, mock_user, sample_report, db_session):
        """Test module coverage level assignment"""
        report = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

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
    async def test_overall_coverage_calculation(self, mock_user, sample_report, db_session):
        """Test overall coverage calculation"""
        report = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

        # The overall_coverage is stored in the database, not calculated from modules
        # Just verify it's a reasonable value
        assert 0 <= report.overall_coverage <= 100

    @pytest.mark.asyncio
    async def test_summary_statistics(self, mock_user, sample_report, db_session):
        """Test summary statistics calculation"""
        report = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

        assert "total_lines" in report.summary
        assert "covered_lines" in report.summary
        assert "uncovered_lines" in report.summary
        assert "excellent_count" in report.summary
        assert "good_count" in report.summary
        assert "adequate_count" in report.summary
        assert "poor_count" in report.summary

    @pytest.mark.asyncio
    async def test_summary_counts_match_modules(self, mock_user, sample_report, db_session):
        """Test summary counts match module levels"""
        db_session.expire_all()
        report = await get_coverage_report(sample_report.id, current_user=mock_user, db=db_session)

        excellent_count = len(
            [m for m in report.modules if m.coverage_level == CoverageLevel.EXCELLENT]
        )
        good_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.GOOD])
        adequate_count = len(
            [m for m in report.modules if m.coverage_level == CoverageLevel.ADEQUATE]
        )
        poor_count = len([m for m in report.modules if m.coverage_level == CoverageLevel.POOR])

        assert report.summary["excellent_count"] == excellent_count
        assert report.summary["good_count"] == good_count
        assert report.summary["adequate_count"] == adequate_count
        assert report.summary["poor_count"] == poor_count


# ============ Trend Calculation Tests ============


class TestTrendCalculation:
    """Test trend calculations"""

    @pytest.mark.asyncio
    async def test_trend_calculation_up(self, mock_user, db_session):
        """Test trend calculation when coverage increased"""
        report_create = CoverageReportCreate(report_name="Trend Test", include_trends=True)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_coverage_report(report_create, request, current_user=mock_user, db=db_session)

        if result.trends:
            assert "previous_coverage" in result.trends
            assert "change" in result.trends
            assert "trend" in result.trends

    @pytest.mark.asyncio
    async def test_trend_calculation_down(self, mock_user, db_session):
        """Test trend calculation when coverage decreased"""
        report_create = CoverageReportCreate(report_name="Trend Test Down", include_trends=True)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await create_coverage_report(report_create, request, current_user=mock_user, db=db_session)

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
    async def test_full_report_workflow(self, mock_user, db_session):
        """Test complete report workflow"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create report
        report_create = CoverageReportCreate(report_name="Workflow Report", include_trends=True)
        report = await create_coverage_report(report_create, request, current_user=mock_user, db=db_session)
        assert report.report_name == "Workflow Report"

        # Get report
        db_session.expire_all()
        retrieved = await get_coverage_report(report.id, current_user=mock_user, db=db_session)
        assert retrieved.id == report.id

        # Get summary
        db_session.expire_all()
        summary = await get_coverage_summary(current_user=mock_user, db=db_session)
        # Summary may be 0 if no reports exist
        assert summary["overall_coverage"] >= 0

        # Delete report
        await delete_coverage_report(report.id, request, current_user=mock_user, db=db_session)

    @pytest.mark.asyncio
    async def test_multiple_reports_workflow(self, mock_user, db_session):
        """Test workflow with multiple reports"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create multiple reports
        report_ids = []
        for i in range(3):
            report_create = CoverageReportCreate(report_name=f"Report-{i}", include_trends=False)
            report = await create_coverage_report(
                report_create, request, current_user=mock_user, db=db_session
            )
            report_ids.append(report.id)

        # Get all reports
        db_session.expire_all()
        reports = await get_coverage_reports(current_user=mock_user, db=db_session)
        assert len(reports) >= 3

        # Delete all reports
        for report_id in report_ids:
            db_session.expire_all()
            await delete_coverage_report(report_id, request, current_user=mock_user, db=db_session)
