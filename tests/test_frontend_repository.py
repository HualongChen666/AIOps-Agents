# -*- coding: utf-8 -*-
"""
Unit tests for Frontend Repository
==================================

Tests for the FrontendRepository implementation using pytest-xdist for parallel testing.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal
from core.models import (
    FrontendComponent,
    FrontendTheme,
    FrontendLayout,
    FrontendUserPreference,
)
from core.repositories.frontend_repository_impl import FrontendRepositoryImpl


@pytest.mark.asyncio
@pytest.mark.unit
class TestFrontendRepository:
    """Test FrontendRepository implementation"""

    @pytest.fixture
    async def db_session(self):
        """Create a database session for testing"""
        async with AsyncSessionLocal() as session:
            yield session
            await session.rollback()

    @pytest.fixture
    async def repo(self, db_session: AsyncSession):
        """Create repository instance"""
        return FrontendRepositoryImpl(session=db_session)

    async def test_create_component(self, repo: FrontendRepositoryImpl):
        """Test creating a component"""
        component_data = {
            "id": "test-component-1",
            "name": "Test Component",
            "type": "button",
            "category": "ui",
            "description": "Test component description",
            "code": "export const TestComponent = () => { return <button>Test</button>; }",
            "props": {"variant": "primary"},
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        }

        component_id = await repo.create_component(component_data)
        assert component_id == "test-component-1"

        # Verify component was created
        component = await repo.get_component(component_id)
        assert component is not None
        assert component["name"] == "Test Component"
        assert component["type"] == "button"

    async def test_get_component_not_found(self, repo: FrontendRepositoryImpl):
        """Test getting a non-existent component"""
        component = await repo.get_component("non-existent-id")
        assert component is None

    async def test_list_components(self, repo: FrontendRepositoryImpl):
        """Test listing components with filters"""
        # Create test components
        await repo.create_component({
            "id": "comp-1",
            "name": "Component 1",
            "type": "button",
            "category": "ui",
            "description": "Description 1",
            "code": "code 1",
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        })
        await repo.create_component({
            "id": "comp-2",
            "name": "Component 2",
            "type": "card",
            "category": "ui",
            "description": "Description 2",
            "code": "code 2",
            "is_public": False,
            "status": "active",
            "created_by": "test-user",
        })

        # List all components
        components = await repo.list_components()
        assert len(components) >= 2

        # Filter by type
        button_components = await repo.list_components(filters={"type": "button"})
        assert len(button_components) >= 1
        assert all(c["type"] == "button" for c in button_components)

        # Filter by is_public
        public_components = await repo.list_components(filters={"is_public": True})
        assert len(public_components) >= 1
        assert all(c["is_public"] for c in public_components)

    async def test_update_component(self, repo: FrontendRepositoryImpl):
        """Test updating a component"""
        # Create component
        await repo.create_component({
            "id": "comp-update",
            "name": "Original Name",
            "type": "button",
            "category": "ui",
            "description": "Original description",
            "code": "original code",
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        })

        # Update component
        updates = {
            "name": "Updated Name",
            "description": "Updated description",
        }
        success = await repo.update_component("comp-update", updates)
        assert success is True

        # Verify update
        component = await repo.get_component("comp-update")
        assert component["name"] == "Updated Name"
        assert component["description"] == "Updated description"

    async def test_delete_component(self, repo: FrontendRepositoryImpl):
        """Test deleting a component"""
        # Create component
        await repo.create_component({
            "id": "comp-delete",
            "name": "Delete Me",
            "type": "button",
            "category": "ui",
            "description": "To be deleted",
            "code": "code",
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        })

        # Delete component
        success = await repo.delete_component("comp-delete")
        assert success is True

        # Verify deletion
        component = await repo.get_component("comp-delete")
        assert component is None

    async def test_count_components(self, repo: FrontendRepositoryImpl):
        """Test counting components"""
        # Create test components
        await repo.create_component({
            "id": "comp-count-1",
            "name": "Count 1",
            "type": "button",
            "category": "ui",
            "description": "Description",
            "code": "code",
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        })
        await repo.create_component({
            "id": "comp-count-2",
            "name": "Count 2",
            "type": "button",
            "category": "ui",
            "description": "Description",
            "code": "code",
            "is_public": True,
            "status": "active",
            "created_by": "test-user",
        })

        # Count all
        count = await repo.count_components()
        assert count >= 2

        # Count with filter
        button_count = await repo.count_components(filters={"type": "button"})
        assert button_count >= 2

    async def test_create_theme(self, repo: FrontendRepositoryImpl):
        """Test creating a theme"""
        theme_data = {
            "id": "theme-test-1",
            "name": "Test Theme",
            "base_theme": "light",
            "description": "Test theme description",
            "colors": {
                "primary": "#3b82f6",
                "secondary": "#6366f1",
                "background": "#ffffff",
                "text": "#1f2937",
            },
            "fonts": {},
            "spacing": {},
            "is_default": False,
            "is_public": True,
            "created_by": "test-user",
        }

        theme_id = await repo.create_theme(theme_data)
        assert theme_id == "theme-test-1"

        # Verify theme was created
        theme = await repo.get_theme(theme_id)
        assert theme is not None
        assert theme["name"] == "Test Theme"
        assert theme["base_theme"] == "light"

    async def test_create_layout(self, repo: FrontendRepositoryImpl):
        """Test creating a layout"""
        layout_data = {
            "id": "layout-test-1",
            "name": "Test Layout",
            "type": "dashboard",
            "description": "Test layout description",
            "structure": {
                "header": {"height": 64},
                "sidebar": {"width": 240},
                "content": {"flex": 1},
            },
            "breakpoints": {},
            "is_default": False,
            "is_public": True,
            "created_by": "test-user",
        }

        layout_id = await repo.create_layout(layout_data)
        assert layout_id == "layout-test-1"

        # Verify layout was created
        layout = await repo.get_layout(layout_id)
        assert layout is not None
        assert layout["name"] == "Test Layout"
        assert layout["type"] == "dashboard"

    async def test_user_preferences(self, repo: FrontendRepositoryImpl):
        """Test user preferences CRUD"""
        user_id = "test-user-123"

        # Create user preferences
        pref_data = {
            "theme": "dark",
            "language": "en-US",
            "timezone": "America/New_York",
            "date_format": "MM/DD/YYYY",
            "time_format": "hh:mm:ss A",
            "view_mode": "list",
            "notifications_enabled": False,
            "notification_sound": True,
            "auto_refresh_interval": 60,
            "dashboard_layout": {},
            "custom_colors": {},
            "accessibility_settings": {},
        }

        success = await repo.create_user_preferences(user_id, pref_data)
        assert success is True

        # Get user preferences
        pref = await repo.get_user_preferences(user_id)
        assert pref is not None
        assert pref["theme"] == "dark"
        assert pref["language"] == "en-US"

        # Update user preferences
        updates = {"theme": "light", "language": "zh-CN"}
        success = await repo.update_user_preferences(user_id, updates)
        assert success is True

        # Verify update
        pref = await repo.get_user_preferences(user_id)
        assert pref["theme"] == "light"
        assert pref["language"] == "zh-CN"

    async def test_localization(self, repo: FrontendRepositoryImpl):
        """Test localization CRUD"""
        # Create localization
        success = await repo.upsert_localization(
            "en-US", "test_key", "Test Value", "Test Context"
        )
        assert success is True

        # Get localization
        loc = await repo.get_localization("en-US", "test_key")
        assert loc is not None
        assert loc["translation_value"] == "Test Value"
        assert loc["context"] == "Test Context"

        # Update localization
        success = await repo.upsert_localization(
            "en-US", "test_key", "Updated Value", "Updated Context"
        )
        assert success is True

        # Verify update
        loc = await repo.get_localization("en-US", "test_key")
        assert loc["translation_value"] == "Updated Value"

        # Delete localization
        success = await repo.delete_localization("en-US", "test_key")
        assert success is True

        # Verify deletion
        loc = await repo.get_localization("en-US", "test_key")
        assert loc is None

    async def test_dashboard_widget(self, repo: FrontendRepositoryImpl):
        """Test dashboard widget CRUD"""
        widget_data = {
            "id": "widget-test-1",
            "dashboard_id": "dashboard-1",
            "widget_id": "widget-1",
            "widget_type": "metrics",
            "title": "Test Widget",
            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
            "config": {"show_legend": True},
            "data_source": "api/v1/metrics",
            "refresh_interval": 30,
            "enabled": True,
            "created_by": "test-user",
        }

        widget_id = await repo.create_dashboard_widget(widget_data)
        assert widget_id == "widget-test-1"

        # Get widget
        widget = await repo.get_dashboard_widget(widget_id)
        assert widget is not None
        assert widget["title"] == "Test Widget"

        # List widgets for dashboard
        widgets = await repo.list_dashboard_widgets("dashboard-1")
        assert len(widgets) >= 1

        # Update widget
        updates = {"title": "Updated Widget", "enabled": False}
        success = await repo.update_dashboard_widget(widget_id, updates)
        assert success is True

        # Verify update
        widget = await repo.get_dashboard_widget(widget_id)
        assert widget["title"] == "Updated Widget"
        assert widget["enabled"] is False

        # Delete widget
        success = await repo.delete_dashboard_widget(widget_id)
        assert success is True

        # Verify deletion
        widget = await repo.get_dashboard_widget(widget_id)
        assert widget is None

    async def test_report_template(self, repo: FrontendRepositoryImpl):
        """Test report template CRUD"""
        template_data = {
            "id": "template-test-1",
            "name": "Test Template",
            "description": "Test template description",
            "data_sources": ["metrics", "alerts"],
            "filters": {"time_range": "24h"},
            "visualization_config": {"chart_type": "line"},
            "format": "pdf",
            "schedule": "0 0 * * *",
            "created_by": "test-user",
        }

        template_id = await repo.create_report_template(template_data)
        assert template_id == "template-test-1"

        # Get template
        template = await repo.get_report_template(template_id)
        assert template is not None
        assert template["name"] == "Test Template"

        # List templates
        templates = await repo.list_report_templates()
        assert len(templates) >= 1

        # Update template
        updates = {"name": "Updated Template", "format": "html"}
        success = await repo.update_report_template(template_id, updates)
        assert success is True

        # Verify update
        template = await repo.get_report_template(template_id)
        assert template["name"] == "Updated Template"
        assert template["format"] == "html"

        # Delete template
        success = await repo.delete_report_template(template_id)
        assert success is True

        # Verify deletion
        template = await repo.get_report_template(template_id)
        assert template is None
