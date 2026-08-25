# -*- coding: utf-8 -*-
"""
Test suite for dashboard_advanced_router.py
Tests all endpoints with comprehensive coverage including:
- GET, POST, PATCH, DELETE operations
- Normal and error cases
- Data validation
- Permission control
- Mock dependencies
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.dashboard_advanced_router import (
    FAKE_ADMIN,
    DashboardLayout,
    DashboardLayoutUpdate,
    DashboardWidget,
    DashboardWidgetCreate,
    DashboardWidgetUpdate,
    LayoutType,
    WidgetType,
    _dashboard_layouts,
    _dashboard_widgets,
    _init_dashboard_layouts,
    _init_dashboard_widgets,
    get_current_user,
    router,
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
    _dashboard_widgets.clear()
    _dashboard_layouts.clear()
    yield
    _dashboard_widgets.clear()
    _dashboard_layouts.clear()


@pytest.fixture
def sample_widget(clear_data):
    """Create a sample dashboard widget"""
    _init_dashboard_widgets()
    return list(_dashboard_widgets.values())[0]


@pytest.fixture
def sample_layout(clear_data):
    """Create a sample dashboard layout"""
    _init_dashboard_layouts()
    return list(_dashboard_layouts.values())[0]


# ============ Widget Endpoints Tests ============


class TestWidgetEndpoints:
    """Test widget endpoints"""

    @pytest.mark.asyncio
    async def test_get_dashboard_widgets_success(self, mock_admin_user, clear_data):
        """Test successful dashboard widgets retrieval"""
        _init_dashboard_widgets()
        result = await router.get_dashboard_widgets(current_user=mock_admin_user)

        assert isinstance(result, list)
        assert len(result) >= 3

    @pytest.mark.asyncio
    async def test_get_dashboard_widgets_empty(self, mock_admin_user, clear_data):
        """Test dashboard widgets retrieval when empty"""
        result = await router.get_dashboard_widgets(current_user=mock_admin_user)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_widgets_with_type_filter(self, mock_admin_user, clear_data):
        """Test dashboard widgets retrieval with type filter"""
        _init_dashboard_widgets()
        result = await router.get_dashboard_widgets(
            widget_type=WidgetType.METRIC, current_user=mock_admin_user
        )

        assert isinstance(result, list)
        assert all(w.widget_type == WidgetType.METRIC for w in result)

    @pytest.mark.asyncio
    async def test_get_dashboard_widgets_enabled_only(self, mock_admin_user, clear_data):
        """Test dashboard widgets retrieval with enabled only filter"""
        _init_dashboard_widgets()
        result = await router.get_dashboard_widgets(enabled_only=True, current_user=mock_admin_user)

        assert isinstance(result, list)
        assert all(w.enabled for w in result)

    @pytest.mark.asyncio
    async def test_get_dashboard_widgets_combined_filters(self, mock_admin_user, clear_data):
        """Test dashboard widgets retrieval with combined filters"""
        _init_dashboard_widgets()
        result = await router.get_dashboard_widgets(
            widget_type=WidgetType.METRIC, enabled_only=True, current_user=mock_admin_user
        )

        assert isinstance(result, list)
        assert all(w.widget_type == WidgetType.METRIC and w.enabled for w in result)

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_success(self, mock_admin_user, clear_data):
        """Test successful dashboard widget creation"""
        widget_create = DashboardWidgetCreate(
            widget_type=WidgetType.CHART,
            title="New Widget",
            description="A new widget",
            config={"chart_type": "line"},
            data_source="/api/v1/metrics/test",
        )

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.create_dashboard_widget(
            widget_create, request, current_user=mock_admin_user
        )

        assert isinstance(result, DashboardWidget)
        assert result.title == "New Widget"
        assert result.widget_type == WidgetType.CHART
        assert result.enabled == True

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_validation_title_min(self, mock_admin_user, clear_data):
        """Test dashboard widget creation with title too short"""
        with pytest.raises(Exception):  # Pydantic validation error
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="")

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_validation_title_max(self, mock_admin_user, clear_data):
        """Test dashboard widget creation with title too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="a" * 201)

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_validation_description_max(
        self, mock_admin_user, clear_data
    ):
        """Test dashboard widget creation with description too long"""
        with pytest.raises(Exception):  # Pydantic validation error
            DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title="Test", description="a" * 501
            )

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_validation_refresh_interval_min(
        self, mock_admin_user, clear_data
    ):
        """Test dashboard widget creation with refresh interval below min"""
        with pytest.raises(Exception):  # Pydantic validation error
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="Test", refresh_interval=4)

    @pytest.mark.asyncio
    async def test_create_dashboard_widget_validation_refresh_interval_max(
        self, mock_admin_user, clear_data
    ):
        """Test dashboard widget creation with refresh interval above max"""
        with pytest.raises(Exception):  # Pydantic validation error
            DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title="Test", refresh_interval=3601
            )

    @pytest.mark.asyncio
    async def test_get_dashboard_widget_success(self, mock_admin_user, sample_widget, clear_data):
        """Test successful dashboard widget retrieval"""
        result = await router.get_dashboard_widget(sample_widget.id, current_user=mock_admin_user)

        assert isinstance(result, DashboardWidget)
        assert result.id == sample_widget.id

    @pytest.mark.asyncio
    async def test_get_dashboard_widget_not_found(self, mock_admin_user, clear_data):
        """Test dashboard widget retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_dashboard_widget("nonexistent", current_user=mock_admin_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Widget not found"

    @pytest.mark.asyncio
    async def test_update_dashboard_widget_success(
        self, mock_admin_user, sample_widget, clear_data
    ):
        """Test successful dashboard widget update"""
        widget_update = DashboardWidgetUpdate(title="Updated Title", enabled=False)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.update_dashboard_widget(
            sample_widget.id, widget_update, request, current_user=mock_admin_user
        )

        assert isinstance(result, DashboardWidget)
        assert result.title == "Updated Title"
        assert result.enabled == False

    @pytest.mark.asyncio
    async def test_update_dashboard_widget_not_found(self, mock_admin_user, clear_data):
        """Test dashboard widget update when not found"""
        widget_update = DashboardWidgetUpdate(title="Updated")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.update_dashboard_widget(
                "nonexistent", widget_update, request, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Widget not found"

    @pytest.mark.asyncio
    async def test_delete_dashboard_widget_success(
        self, mock_admin_user, sample_widget, clear_data
    ):
        """Test successful dashboard widget deletion"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        await router.delete_dashboard_widget(
            sample_widget.id, request, current_user=mock_admin_user
        )

        assert sample_widget.id not in _dashboard_widgets

    @pytest.mark.asyncio
    async def test_delete_dashboard_widget_not_found(self, mock_admin_user, clear_data):
        """Test dashboard widget deletion when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.delete_dashboard_widget(
                "nonexistent", request, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Widget not found"

    @pytest.mark.asyncio
    async def test_delete_dashboard_widget_cascades_to_layouts(
        self, mock_admin_user, sample_widget, clear_data
    ):
        """Test dashboard widget deletion cascades to layouts"""
        _init_dashboard_layouts()

        # Ensure widget is in a layout
        layout = list(_dashboard_layouts.values())[0]
        if sample_widget.id not in layout.widgets:
            layout.widgets.append(sample_widget.id)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        await router.delete_dashboard_widget(
            sample_widget.id, request, current_user=mock_admin_user
        )

        # Widget should be removed from layout
        updated_layout = _dashboard_layouts[layout.id]
        assert sample_widget.id not in updated_layout.widgets


# ============ Layout Endpoints Tests ============


class TestLayoutEndpoints:
    """Test layout endpoints"""

    @pytest.mark.asyncio
    async def test_get_dashboard_layouts_success(self, mock_admin_user, clear_data):
        """Test successful dashboard layouts retrieval"""
        _init_dashboard_layouts()
        result = await router.get_dashboard_layouts(current_user=mock_admin_user)

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_dashboard_layouts_empty(self, mock_admin_user, clear_data):
        """Test dashboard layouts retrieval when empty"""
        result = await router.get_dashboard_layouts(current_user=mock_admin_user)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_create_dashboard_layout_success(self, mock_admin_user, clear_data):
        """Test successful dashboard layout creation"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.create_dashboard_layout(
            layout_name="New Layout",
            layout_type=LayoutType.FLEX,
            request=request,
            current_user=mock_admin_user,
        )

        assert isinstance(result, DashboardLayout)
        assert result.layout_name == "New Layout"
        assert result.layout_type == LayoutType.FLEX
        assert result.is_default == False

    @pytest.mark.asyncio
    async def test_get_dashboard_layout_success(self, mock_admin_user, sample_layout, clear_data):
        """Test successful dashboard layout retrieval"""
        result = await router.get_dashboard_layout(sample_layout.id, current_user=mock_admin_user)

        assert isinstance(result, DashboardLayout)
        assert result.id == sample_layout.id

    @pytest.mark.asyncio
    async def test_get_dashboard_layout_not_found(self, mock_admin_user, clear_data):
        """Test dashboard layout retrieval when not found"""
        with pytest.raises(HTTPException) as exc_info:
            await router.get_dashboard_layout("nonexistent", current_user=mock_admin_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Layout not found"

    @pytest.mark.asyncio
    async def test_update_dashboard_layout_success(
        self, mock_admin_user, sample_layout, clear_data
    ):
        """Test successful dashboard layout update"""
        layout_update = DashboardLayoutUpdate(layout_name="Updated Layout", columns=16)

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        result = await router.update_dashboard_layout(
            sample_layout.id, layout_update, request, current_user=mock_admin_user
        )

        assert isinstance(result, DashboardLayout)
        assert result.layout_name == "Updated Layout"
        assert result.columns == 16

    @pytest.mark.asyncio
    async def test_update_dashboard_layout_not_found(self, mock_admin_user, clear_data):
        """Test dashboard layout update when not found"""
        layout_update = DashboardLayoutUpdate(layout_name="Updated")

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.update_dashboard_layout(
                "nonexistent", layout_update, request, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Layout not found"

    @pytest.mark.asyncio
    async def test_delete_dashboard_layout_success(self, mock_admin_user, clear_data):
        """Test successful dashboard layout deletion"""
        _init_dashboard_layouts()
        layout = list(_dashboard_layouts.values())[0]

        # Create a non-default layout
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        new_layout = await router.create_dashboard_layout(
            layout_name="Deletable Layout", request=request, current_user=mock_admin_user
        )

        await router.delete_dashboard_layout(new_layout.id, request, current_user=mock_admin_user)

        assert new_layout.id not in _dashboard_layouts

    @pytest.mark.asyncio
    async def test_delete_dashboard_layout_forbidden(self, mock_regular_user, clear_data):
        """Test dashboard layout deletion without admin role"""
        _init_dashboard_layouts()
        layout = list(_dashboard_layouts.values())[0]

        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.delete_dashboard_layout(layout.id, request, current_user=mock_regular_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_dashboard_layout_not_found(self, mock_admin_user, clear_data):
        """Test dashboard layout deletion when not found"""
        from fastapi import Request

        request = Mock(spec=Request)

        with pytest.raises(HTTPException) as exc_info:
            await router.delete_dashboard_layout(
                "nonexistent", request, current_user=mock_admin_user
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Layout not found"

    @pytest.mark.asyncio
    async def test_delete_default_layout_forbidden(self, mock_admin_user, clear_data):
        """Test deletion of default layout is forbidden"""
        _init_dashboard_layouts()
        layout = list(_dashboard_layouts.values())[0]
        layout.is_default = True

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        with pytest.raises(HTTPException) as exc_info:
            await router.delete_dashboard_layout(layout.id, request, current_user=mock_admin_user)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "default" in exc_info.value.detail.lower()


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
        with patch("api.dashboard_advanced_router.verify_token", return_value=None):
            result = await get_current_user(token="invalid")

            assert result.username == "dev-admin"


# ============ Data Validation Tests ============


class TestDataValidation:
    """Test data validation for models"""

    def test_widget_create_title_min_validation(self):
        """Test DashboardWidgetCreate title min length validation"""
        with pytest.raises(Exception):
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="")

    def test_widget_create_title_max_validation(self):
        """Test DashboardWidgetCreate title max length validation"""
        with pytest.raises(Exception):
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="a" * 201)

    def test_widget_create_description_max_validation(self):
        """Test DashboardWidgetCreate description max length validation"""
        with pytest.raises(Exception):
            DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title="Test", description="a" * 501
            )

    def test_widget_create_refresh_interval_min_validation(self):
        """Test DashboardWidgetCreate refresh interval min validation"""
        with pytest.raises(Exception):
            DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="Test", refresh_interval=4)

    def test_widget_create_refresh_interval_max_validation(self):
        """Test DashboardWidgetCreate refresh interval max validation"""
        with pytest.raises(Exception):
            DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title="Test", refresh_interval=3601
            )

    def test_widget_update_title_min_validation(self):
        """Test DashboardWidgetUpdate title min length validation"""
        with pytest.raises(Exception):
            DashboardWidgetUpdate(title="")

    def test_widget_update_title_max_validation(self):
        """Test DashboardWidgetUpdate title max length validation"""
        with pytest.raises(Exception):
            DashboardWidgetUpdate(title="a" * 201)

    def test_layout_update_name_min_validation(self):
        """Test DashboardLayoutUpdate name min length validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(layout_name="")

    def test_layout_update_name_max_validation(self):
        """Test DashboardLayoutUpdate name max length validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(layout_name="a" * 201)

    def test_layout_update_columns_min_validation(self):
        """Test DashboardLayoutUpdate columns min validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(columns=0)

    def test_layout_update_columns_max_validation(self):
        """Test DashboardLayoutUpdate columns max validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(columns=25)

    def test_layout_update_rows_min_validation(self):
        """Test DashboardLayoutUpdate rows min validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(rows=0)

    def test_layout_update_rows_max_validation(self):
        """Test DashboardLayoutUpdate rows max validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(rows=51)

    def test_layout_update_gap_min_validation(self):
        """Test DashboardLayoutUpdate gap min validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(gap=-1)

    def test_layout_update_gap_max_validation(self):
        """Test DashboardLayoutUpdate gap max validation"""
        with pytest.raises(Exception):
            DashboardLayoutUpdate(gap=101)


# ============ Helper Function Tests ============


class TestHelperFunctions:
    """Test helper functions"""

    def test_init_dashboard_widgets(self, clear_data):
        """Test _init_dashboard_widgets creates default widgets"""
        _init_dashboard_widgets()

        assert len(_dashboard_widgets) >= 3
        assert all(isinstance(w, DashboardWidget) for w in _dashboard_widgets.values())

    def test_init_dashboard_layouts(self, clear_data):
        """Test _init_dashboard_layouts creates default layout"""
        _init_dashboard_layouts()

        assert len(_dashboard_layouts) >= 1
        assert all(isinstance(l, DashboardLayout) for l in _dashboard_layouts.values())


# ============ Enum Tests ============


class TestEnums:
    """Test enum values"""

    def test_widget_type_values(self):
        """Test WidgetType enum values"""
        assert WidgetType.METRIC == "metric"
        assert WidgetType.CHART == "chart"
        assert WidgetType.TABLE == "table"
        assert WidgetType.LOG == "log"
        assert WidgetType.ALERT == "alert"
        assert WidgetType.STATUS == "status"

    def test_layout_type_values(self):
        """Test LayoutType enum values"""
        assert LayoutType.GRID == "grid"
        assert LayoutType.FLEX == "flex"
        assert LayoutType.CUSTOM == "custom"


# ============ Integration Tests ============


class TestIntegration:
    """Integration tests for dashboard operations"""

    @pytest.mark.asyncio
    async def test_full_widget_workflow(self, mock_admin_user, clear_data):
        """Test complete widget workflow"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create widget
        widget_create = DashboardWidgetCreate(
            widget_type=WidgetType.METRIC, title="Workflow Widget"
        )
        widget = await router.create_dashboard_widget(
            widget_create, request, current_user=mock_admin_user
        )
        assert widget.title == "Workflow Widget"

        # Get widget
        retrieved = await router.get_dashboard_widget(widget.id, current_user=mock_admin_user)
        assert retrieved.id == widget.id

        # Update widget
        widget_update = DashboardWidgetUpdate(title="Updated Widget")
        updated = await router.update_dashboard_widget(
            widget.id, widget_update, request, current_user=mock_admin_user
        )
        assert updated.title == "Updated Widget"

        # Delete widget
        await router.delete_dashboard_widget(widget.id, request, current_user=mock_admin_user)
        assert widget.id not in _dashboard_widgets

    @pytest.mark.asyncio
    async def test_full_layout_workflow(self, mock_admin_user, clear_data):
        """Test complete layout workflow"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create layout
        layout = await router.create_dashboard_layout(
            layout_name="Workflow Layout", request=request, current_user=mock_admin_user
        )
        assert layout.layout_name == "Workflow Layout"

        # Get layout
        retrieved = await router.get_dashboard_layout(layout.id, current_user=mock_admin_user)
        assert retrieved.id == layout.id

        # Update layout
        layout_update = DashboardLayoutUpdate(layout_name="Updated Layout")
        updated = await router.update_dashboard_layout(
            layout.id, layout_update, request, current_user=mock_admin_user
        )
        assert updated.layout_name == "Updated Layout"

        # Delete layout
        await router.delete_dashboard_layout(layout.id, request, current_user=mock_admin_user)
        assert layout.id not in _dashboard_layouts

    @pytest.mark.asyncio
    async def test_widget_in_layout_workflow(self, mock_admin_user, clear_data):
        """Test widget and layout integration"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create widget
        widget_create = DashboardWidgetCreate(widget_type=WidgetType.METRIC, title="Test Widget")
        widget = await router.create_dashboard_widget(
            widget_create, request, current_user=mock_admin_user
        )

        # Create layout
        layout = await router.create_dashboard_layout(
            layout_name="Test Layout", request=request, current_user=mock_admin_user
        )

        # Add widget to layout
        layout_update = DashboardLayoutUpdate(widgets=[widget.id])
        updated_layout = await router.update_dashboard_layout(
            layout.id, layout_update, request, current_user=mock_admin_user
        )
        assert widget.id in updated_layout.widgets

        # Delete widget should remove from layout
        await router.delete_dashboard_widget(widget.id, request, current_user=mock_admin_user)
        final_layout = await router.get_dashboard_layout(layout.id, current_user=mock_admin_user)
        assert widget.id not in final_layout.widgets


# ============ Error Handling Tests ============


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_concurrent_widget_creation(self, mock_admin_user, clear_data):
        """Test concurrent widget creation"""
        import asyncio

        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        async def create_widget():
            widget_create = DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title=f"Widget-{asyncio.current_task().get_name()}"
            )
            await router.create_dashboard_widget(
                widget_create, request, current_user=mock_admin_user
            )

        # Run multiple concurrent creations
        await asyncio.gather(*[create_widget() for _ in range(5)])

        # Should not raise errors
        widgets = await router.get_dashboard_widgets(current_user=mock_admin_user)
        assert len(widgets) >= 5

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self, mock_admin_user, clear_data):
        """Test handling of large datasets"""
        from fastapi import Request

        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock(host="127.0.0.1")

        # Create many widgets
        for i in range(30):
            widget_create = DashboardWidgetCreate(
                widget_type=WidgetType.METRIC, title=f"Widget-{i}"
            )
            await router.create_dashboard_widget(
                widget_create, request, current_user=mock_admin_user
            )

        # Should handle correctly
        widgets = await router.get_dashboard_widgets(current_user=mock_admin_user)
        assert len(widgets) >= 30


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
