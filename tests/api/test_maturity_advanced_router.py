# -*- coding: utf-8 -*-
"""
Test suite for maturity_advanced_router.py
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

from api.maturity_advanced_router import (
    router,
    MaturityAssessmentRecord,
    MaturityAssessmentCreate,
    AssessmentStatus,
    FAKE_ADMIN,
    get_current_user,
    _assessment_records,
    _init_assessment_records,
)
from core.authentication import UserInDB


# ============ Fixtures ============

@pytest.fixture
def mock_admin_user():
    """Create a mock admin user"""
    return UserInDB(
        id=1,
        username="admin",
        full_name="Admin User",
        email="admin@example.com",
        role="admin",
        disabled=False,
        hashed_password="hashed",
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user"""
    return UserInDB(
        id=2,
        username="regular",
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
    _assessment_records.clear()
    yield
    _assessment_records.clear()


@pytest.fixture
def sample_assessment(clear_data):
    """Create a sample assessment record"""
    _init_assessment_records()
    return list(_assessment_records.values())[0]


# ============ Assessment Endpoints Tests ============

class TestAssessmentEndpoints:
    """Test assessment endpoints"""

    @pytest.mark.asyncio
    async def test_get_assessments_success(self, mock_admin_user, clear_data):
        """Test successful assessments retrieval"""
        _init_assessment_records()
        result = await router.get_assessments(current_user=mock_admin_user)
        
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_assessments_empty(self, mock_admin_user, clear_data):
        """Test assessments retrieval when empty"""
        result = await router.get_assessments(current_user=mock_admin_user)
        
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_assessments_with_status_filter(self, mock_admin_user, clear_data):
        """Test assessments retrieval with status filter"""
        _init_assessment_records()
        result = await router.get_assessments(
            status=AssessmentStatus.COMPLETED, current_user=mock_admin_user
        )
        
        assert isinstance(result, list)
        assert all(r.status == AssessmentStatus.COMPLETED for r in result)

    @pytest.mark.asyncio
    async def test_get_assessments_with_pagination(self, mock_admin_user, clear_data):
        """Test assessments retrieval with pagination"""
        _init_assessment_records()
        
        # Create multiple assessments
        for i in range(5):
            assessment_create = MaturityAssessmentCreate(
                assessment_name=f"Assessment-{i}",
                notes=f"Notes for assessment {i}"
            )
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            await router.create_assessment(assessment_create, request, current_user=mock_admin_user)
        
        result = await router.get_assessments(limit=3, offset=0, current_user=mock_admin_user)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_create_assessment_success(self, mock_admin_user, clear_data):
        """Test successful assessment creation"""
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.return_value = {
                "overall_score": 75,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [
                    {"name": "Test", "score": 75, "maxScore": 100, "description": "Test dimension"}
                ],
                "recommendations": []
            }
            
            assessment_create = MaturityAssessmentCreate(
                assessment_name="New Assessment",
                notes="Assessment notes"
            )
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            result = await router.create_assessment(assessment_create, request, current_user=mock_admin_user)
            
            assert isinstance(result, MaturityAssessmentRecord)
            assert result.assessment_name == "New Assessment"
            assert result.status == AssessmentStatus.COMPLETED
            assert result.overall_score == 75

    @pytest.mark.asyncio
    async def test_create_assessment_failure(self, mock_admin_user, clear_data):
        """Test assessment creation when assessment fails"""
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.side_effect = Exception("Assessment failed")
            
            assessment_create = MaturityAssessmentCreate(
                assessment_name="Failed Assessment"
            )
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            result = await router.create_assessment(assessment_create, request, current_user=mock_admin_user)
            
            assert isinstance(result, MaturityAssessmentRecord)
            assert result.status == AssessmentStatus.FAILED
            assert result.overall_score == 0

    @pytest.mark.asyncio
    async def test_create_assessment_validation_name_min(self, mock_admin_user, clear_data):
        """Test assessment creation with name too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            MaturityAssessmentCreate(name="")

    @pytest.mark.asyncio
    async def test_create_assessment_validation_name_max(self, mock_admin_user, clear_data):
        """Test assessment creation with name too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            MaturityAssessmentCreate(name="a" * 201)

    @pytest.mark.asyncio
    async def test_create_assessment_validation_notes_max(self, mock_admin_user, clear_data):
        """Test assessment creation with notes too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            MaturityAssessmentCreate(name="Test", notes="a" * 1001)

    @pytest.mark.asyncio
    async def test_get_assessment_success(self, mock_admin_user, sample_assessment, clear_data):
        """Test successful assessment retrieval"""
        result = await router.get_assessment(sample_assessment.id, current_user=mock_admin_user)
        
        assert isinstance(result, MaturityAssessmentRecord)
        assert result.id == sample_assessment.id

    @pytest.mark.asyncio
    async def test_get_assessment_not_found(self, mock_admin_user, clear_data):
        """Test assessment retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_assessment("nonexistent", current_user=mock_admin_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Assessment not found"

    @pytest.mark.asyncio
    async def test_delete_assessment_success(self, mock_admin_user, sample_assessment, clear_data):
        """Test successful assessment deletion"""
        from fastapi import Request
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")
        
        await router.delete_assessment(sample_assessment.id, request, current_user=mock_admin_user)
        
        assert sample_assessment.id not in _assessment_records

    @pytest.mark.asyncio
    async def test_delete_assessment_forbidden(self, mock_regular_user, sample_assessment, clear_data):
        """Test assessment deletion without admin role"""
        from fastapi import Request
        request = Mock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await router.delete_assessment(sample_assessment.id, request, current_user=mock_regular_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_assessment_not_found(self, mock_admin_user, clear_data):
        """Test assessment deletion when not found"""
        from fastapi import Request
        request = Mock(spec=Request)
        
        with pytest.raises(HTTPException) as exc_info:
            await router.delete_assessment("nonexistent", request, current_user=mock_admin_user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Assessment not found"


# ============ Export Endpoints Tests ============

class TestExportEndpoints:
    """Test export endpoints"""

    @pytest.mark.asyncio
    async def test_export_assessment_json(self, mock_admin_user, sample_assessment, clear_data):
        """Test assessment export in JSON format"""
        result = await router.export_assessment(
            sample_assessment.id, format="json", current_user=mock_admin_user
        )
        
        assert isinstance(result, dict)
        assert "id" in result
        assert "assessment_name" in result
        assert "overall_score" in result
        assert "level" in result

    @pytest.mark.asyncio
    async def test_export_assessment_summary(self, mock_admin_user, sample_assessment, clear_data):
        """Test assessment export in summary format"""
        result = await router.export_assessment(
            sample_assessment.id, format="summary", current_user=mock_admin_user
        )
        
        assert isinstance(result, dict)
        assert "id" in result
        assert "assessment_name" in result
        assert "overall_score" in result
        assert "level" in result
        assert "dimension_count" in result
        assert "recommendation_count" in result

    @pytest.mark.asyncio
    async def test_export_assessment_invalid_format(self, mock_admin_user, sample_assessment, clear_data):
        """Test assessment export with invalid format"""
        with pytest.raises(HTTPException) as exc_info:
            await router.export_assessment(
                sample_assessment.id, format="invalid", current_user=mock_admin_user
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "unsupported format" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_export_assessment_not_found(self, mock_admin_user, clear_data):
        """Test assessment export when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.export_assessment(
                "nonexistent", format="json", current_user=mock_admin_user
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Assessment not found"


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
        with patch('api.maturity_advanced_router.verify_token', return_value=None):
            result = await get_current_user(token="invalid")
            
            assert result.username == "dev-admin"


# ============ Data Validation Tests ============

class TestDataValidation:
    """Test data validation for models"""

    def test_assessment_create_name_min_validation(self):
        """Test MaturityAssessmentCreate name min length validation"""
        with pytest.raises(Exception):
            MaturityAssessmentCreate(name="")

    def test_assessment_create_name_max_validation(self):
        """Test MaturityAssessmentCreate name max length validation"""
        with pytest.raises(Exception):
            MaturityAssessmentCreate(name="a" * 201)

    def test_assessment_create_notes_max_validation(self):
        """Test MaturityAssessmentCreate notes max length validation"""
        with pytest.raises(Exception):
            MaturityAssessmentCreate(name="Test", notes="a" * 1001)


# ============ Helper Function Tests ============

class TestHelperFunctions:
    """Test helper functions"""

    def test_init_assessment_records(self, clear_data):
        """Test _init_assessment_records creates default assessment"""
        _init_assessment_records()
        
        assert len(_assessment_records) >= 1
        assessment = list(_assessment_records.values())[0]
        assert isinstance(assessment, MaturityAssessmentRecord)


# ============ Enum Tests ============

class TestEnums:
    """Test enum values"""

    def test_assessment_status_values(self):
        """Test AssessmentStatus enum values"""
        assert AssessmentStatus.IN_PROGRESS == "in_progress"
        assert AssessmentStatus.COMPLETED == "completed"
        assert AssessmentStatus.FAILED == "failed"


# ============ Integration Tests ============

class TestIntegration:
    """Integration tests for maturity operations"""

    @pytest.mark.asyncio
    async def test_full_assessment_workflow(self, mock_admin_user, clear_data):
        """Test complete assessment workflow"""
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.return_value = {
                "overall_score": 70,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [
                    {"name": "Test", "score": 70, "maxScore": 100, "description": "Test"}
                ],
                "recommendations": []
            }
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            # Create assessment
            assessment_create = MaturityAssessmentCreate(
                assessment_name="Workflow Assessment"
            )
            assessment = await router.create_assessment(
                assessment_create, request, current_user=mock_admin_user
            )
            assert assessment.assessment_name == "Workflow Assessment"
            
            # Get assessment
            retrieved = await router.get_assessment(assessment.id, current_user=mock_admin_user)
            assert retrieved.id == assessment.id
            
            # Export assessment
            exported = await router.export_assessment(
                assessment.id, format="json", current_user=mock_admin_user
            )
            assert exported["id"] == assessment.id
            
            # Delete assessment
            await router.delete_assessment(assessment.id, request, current_user=mock_admin_user)
            assert assessment.id not in _assessment_records

    @pytest.mark.asyncio
    async def test_multiple_assessments_workflow(self, mock_admin_user, clear_data):
        """Test workflow with multiple assessments"""
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.return_value = {
                "overall_score": 75,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [],
                "recommendations": []
            }
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            # Create multiple assessments
            assessment_ids = []
            for i in range(3):
                assessment_create = MaturityAssessmentCreate(
                    assessment_name=f"Assessment-{i}"
                )
                assessment = await router.create_assessment(
                    assessment_create, request, current_user=mock_admin_user
                )
                assessment_ids.append(assessment.id)
            
            # Get all assessments
            assessments = await router.get_assessments(current_user=mock_admin_user)
            assert len(assessments) >= 3
            
            # Delete all assessments
            for assessment_id in assessment_ids:
                await router.delete_assessment(assessment_id, request, current_user=mock_admin_user)

    @pytest.mark.asyncio
    async def test_assessment_export_formats(self, mock_admin_user, clear_data):
        """Test assessment export in different formats"""
        _init_assessment_records()
        assessment = list(_assessment_records.values())[0]
        
        # Export as JSON
        json_export = await router.export_assessment(
            assessment.id, format="json", current_user=mock_admin_user
        )
        assert "dimensions" in json_export
        assert "recommendations" in json_export
        
        # Export as summary
        summary_export = await router.export_assessment(
            assessment.id, format="summary", current_user=mock_admin_user
        )
        assert "dimension_count" in summary_export
        assert "recommendation_count" in summary_export
        assert "dimensions" not in summary_export


# ============ Error Handling Tests ============

class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_concurrent_assessment_creation(self, mock_admin_user, clear_data):
        """Test concurrent assessment creation"""
        import asyncio
        
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.return_value = {
                "overall_score": 70,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [],
                "recommendations": []
            }
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            async def create_assessment():
                assessment_create = MaturityAssessmentCreate(
                    assessment_name=f"Assessment-{asyncio.current_task().get_name()}"
                )
                await router.create_assessment(assessment_create, request, current_user=mock_admin_user)
            
            # Run multiple concurrent creations
            await asyncio.gather(*[create_assessment() for _ in range(5)])
            
            # Should not raise errors
            assessments = await router.get_assessments(current_user=mock_admin_user)
            assert len(assessments) >= 5

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_admin_user, clear_data):
        """Test handling of large datasets"""
        with patch('api.maturity_advanced_router.assess_maturity', new_callable=AsyncMock) as mock_assess:
            mock_assess.return_value = {
                "overall_score": 70,
                "level": 3,
                "level_name": "Intermediate",
                "dimensions": [],
                "recommendations": []
            }
            
            from fastapi import Request
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock(host="127.0.0.1")
            
            # Create many assessments
            for i in range(30):
                assessment_create = MaturityAssessmentCreate(
                    assessment_name=f"Assessment-{i}"
                )
                await router.create_assessment(assessment_create, request, current_user=mock_admin_user)
            
            # Should handle pagination correctly
            result = await router.get_assessments(limit=10, current_user=mock_admin_user)
            assert len(result) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
