# -*- coding: utf-8 -*-
"""
Test suite for Frontend Advanced Router
========================================

Comprehensive tests for frontend enhancement API endpoints including:
- Component management (CRUD)
- Theme management (CRUD)
- Layout management (CRUD)
- Localization management
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the router
from api.frontend_advanced_router import (
    router,
    ComponentCreate,
    ComponentUpdate,
    ThemeCreate,
    ThemeUpdate,
    LayoutCreate,
    LayoutUpdate,
    LocalizationUpdate,
    components,
    themes,
    layouts,
    localization,
    FRONTEND_AVAILABLE
)


# Mock frontend enhancement manager
class MockFrontendEnhancementManager:
    def __init__(self):
        self.custom_themes = {}
    
    def get_theme_config(self, theme_type):
        # Return mock theme config
        return {
            "primary": "#3b82f6",
            "secondary": "#6366f1",
            "background": "#ffffff",
            "text": "#1f2937"
        }
    
    def create_custom_theme(self, theme_id, name, colors, base_theme):
        self.custom_themes[theme_id] = {
            "name": name,
            "colors": colors,
            "base_theme": base_theme
        }


@pytest.fixture
def mock_manager():
    """Create a mock frontend enhancement manager"""
    return MockFrontendEnhancementManager()


@pytest.fixture
def mock_theme_type():
    """Mock ThemeType enum"""
    from enum import Enum
    class MockThemeType(Enum):
        LIGHT = "light"
        DARK = "dark"
        CUSTOM = "custom"
    return MockThemeType


@pytest.fixture
def clear_storage():
    """Clear in-memory storage before each test"""
    components.clear()
    themes.clear()
    layouts.clear()
    yield
    components.clear()
    themes.clear()
    layouts.clear()


@pytest.fixture
def client(mock_manager, mock_theme_type, clear_storage):
    """Create a test client with mocked dependencies"""
    with patch('api.frontend_advanced_router.FRONTEND_AVAILABLE', True):
        with patch('api.frontend_advanced_router.frontend_enhancement_manager', mock_manager):
            with patch('api.frontend_advanced_router.ThemeType', mock_theme_type):
                from fastapi import FastAPI
                app = FastAPI()
                app.include_router(router)
                return TestClient(app)


# ==================== Component Management Tests ====================

class TestListComponents:
    """Test cases for listing components"""
    
    def test_list_components_success(self, client):
        """Test successful component listing"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "CustomButton",
            "type": "button",
            "category": "ui",
            "description": "A custom button",
            "props": {},
            "code": "export const CustomButton = () => { ... }",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "components" in data["data"]
        assert len(data["data"]["components"]) >= 1
    
    def test_list_components_with_type_filter(self, client):
        """Test component listing with type filter"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components?type=button")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_list_components_with_category_filter(self, client):
        """Test component listing with category filter"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components?category=ui")
        assert response.status_code == 200
    
    def test_list_components_with_public_filter(self, client):
        """Test component listing with public filter"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components?is_public=true")
        assert response.status_code == 200
    
    def test_list_components_with_status_filter(self, client):
        """Test component listing with status filter"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components?status=active")
        assert response.status_code == 200
    
    def test_list_components_with_pagination(self, client):
        """Test component listing with pagination"""
        for i in range(5):
            components[f"comp-{i:03d}"] = {
                "component_id": f"comp-{i:03d}",
                "name": f"Component {i}",
                "type": "button",
                "category": "ui",
                "description": f"Component {i}",
                "props": {},
                "code": f"code {i}",
                "dependencies": [],
                "is_public": True,
                "status": "active",
                "created_at": "2024-01-01",
                "updated_at": "2024-01-01"
            }
        
        response = client.get("/api/v1/frontend/components?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["components"]) == 2
        assert data["data"]["total"] == 5
    
    def test_list_components_empty(self, client):
        """Test listing components when none exist"""
        response = client.get("/api/v1/frontend/components")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["components"]) == 0


class TestCreateComponent:
    """Test cases for creating components"""
    
    def test_create_component_success(self, client):
        """Test successful component creation"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "CustomButton",
                "type": "button",
                "category": "ui",
                "description": "A custom button component",
                "code": "export const CustomButton = () => { return <button>Click</button>; }"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "component_id" in data["data"]
        assert data["data"]["name"] == "CustomButton"
        assert data["data"]["status"] == "active"
    
    def test_create_component_with_custom_id(self, client):
        """Test component creation with custom ID"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "component_id": "custom-comp-001",
                "name": "Custom Component",
                "type": "button",
                "category": "ui",
                "description": "Custom",
                "code": "code"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["component_id"] == "custom-comp-001"
    
    def test_create_component_with_props(self, client):
        """Test component creation with props"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "Button",
                "type": "button",
                "category": "ui",
                "description": "Button",
                "code": "code",
                "props": {
                    "label": "string",
                    "onClick": "function",
                    "disabled": "boolean"
                }
            }
        )
        assert response.status_code == 201
    
    def test_create_component_with_dependencies(self, client):
        """Test component creation with dependencies"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "Modal",
                "type": "modal",
                "category": "ui",
                "description": "Modal",
                "code": "code",
                "dependencies": ["react", "react-dom"]
            }
        )
        assert response.status_code == 201
    
    def test_create_component_public(self, client):
        """Test creating public component"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "PublicComponent",
                "type": "button",
                "category": "ui",
                "description": "Public",
                "code": "code",
                "is_public": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["is_public"] is True
    
    def test_create_component_duplicate_id(self, client):
        """Test component creation with duplicate ID"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Existing",
            "type": "button",
            "category": "ui",
            "description": "Existing",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "component_id": "comp-001",
                "name": "Duplicate",
                "type": "button",
                "category": "ui",
                "description": "Duplicate",
                "code": "code"
            }
        )
        assert response.status_code == 400
    
    def test_create_component_missing_required_fields(self, client):
        """Test component creation with missing required fields"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "Test"
                # Missing type, category, description, code
            }
        )
        assert response.status_code == 422


class TestGetComponent:
    """Test cases for getting component details"""
    
    def test_get_component_success(self, client):
        """Test successful component retrieval"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "CustomButton",
            "type": "button",
            "category": "ui",
            "description": "A custom button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/components/comp-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["component_id"] == "comp-001"
        assert data["data"]["name"] == "CustomButton"
    
    def test_get_component_not_found(self, client):
        """Test getting non-existent component"""
        response = client.get("/api/v1/frontend/components/nonexistent")
        assert response.status_code == 404


class TestUpdateComponent:
    """Test cases for updating components"""
    
    def test_update_component_name(self, client):
        """Test updating component name"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Old Name",
            "type": "button",
            "category": "ui",
            "description": "Old",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/components/comp-001",
            json={"name": "New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "New Name"
    
    def test_update_component_description(self, client):
        """Test updating component description"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Old description",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/components/comp-001",
            json={"description": "New description"}
        )
        assert response.status_code == 200
    
    def test_update_component_code(self, client):
        """Test updating component code"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "old code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/components/comp-001",
            json={"code": "new code"}
        )
        assert response.status_code == 200
    
    def test_update_component_status(self, client):
        """Test updating component status"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/components/comp-001",
            json={"status": "deprecated"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "deprecated"
    
    def test_update_component_not_found(self, client):
        """Test updating non-existent component"""
        response = client.patch(
            "/api/v1/frontend/components/nonexistent",
            json={"name": "New Name"}
        )
        assert response.status_code == 404


class TestDeleteComponent:
    """Test cases for deleting components"""
    
    def test_delete_component_success(self, client):
        """Test successful component deletion"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.delete("/api/v1/frontend/components/comp-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["deleted"] is True
        assert "comp-001" not in components
    
    def test_delete_component_not_found(self, client):
        """Test deleting non-existent component"""
        response = client.delete("/api/v1/frontend/components/nonexistent")
        assert response.status_code == 404


# ==================== Theme Management Tests ====================

class TestListThemes:
    """Test cases for listing themes"""
    
    def test_list_themes_success(self, client):
        """Test successful theme listing"""
        themes["theme-001"] = {
            "theme_id": "theme-001",
            "name": "Custom Blue",
            "base_theme": "light",
            "colors": {
                "primary": "#3b82f6",
                "secondary": "#6366f1"
            },
            "fonts": {},
            "spacing": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "themes" in data["data"]
    
    def test_list_themes_with_base_theme_filter(self, client):
        """Test theme listing with base theme filter"""
        themes["theme-001"] = {
            "theme_id": "theme-001",
            "name": "Light Theme",
            "base_theme": "light",
            "colors": {},
            "fonts": {},
            "spacing": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/themes?base_theme=light")
        assert response.status_code == 200
    
    def test_list_themes_with_default_filter(self, client):
        """Test theme listing with default filter"""
        themes["theme-001"] = {
            "theme_id": "theme-001",
            "name": "Default Theme",
            "base_theme": "light",
            "colors": {},
            "fonts": {},
            "spacing": {},
            "is_default": True,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/themes?is_default=true")
        assert response.status_code == 200
    
    def test_list_themes_with_builtin_themes(self, client):
        """Test theme listing includes built-in themes"""
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 200
        data = response.json()
        assert "built_in_themes" in data["data"]
    
    def test_list_themes_empty(self, client):
        """Test listing themes when none exist"""
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["themes"]) == 0


class TestCreateTheme:
    """Test cases for creating themes"""
    
    def test_create_theme_success(self, client):
        """Test successful theme creation"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "name": "Custom Blue",
                "base_theme": "light",
                "colors": {
                    "primary": "#3b82f6",
                    "secondary": "#6366f1",
                    "background": "#ffffff",
                    "text": "#1f2937"
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "theme_id" in data["data"]
        assert data["data"]["name"] == "Custom Blue"
    
    def test_create_theme_with_custom_id(self, client):
        """Test theme creation with custom ID"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "theme_id": "custom-theme-001",
                "name": "Custom Theme",
                "base_theme": "dark",
                "colors": {"primary": "#000000"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["theme_id"] == "custom-theme-001"
    
    def test_create_theme_with_fonts(self, client):
        """Test theme creation with fonts"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "name": "Typography Theme",
                "base_theme": "light",
                "colors": {"primary": "#3b82f6"},
                "fonts": {
                    "primary": "Inter",
                    "mono": "Fira Code"
                }
            }
        )
        assert response.status_code == 201
    
    def test_create_theme_with_spacing(self, client):
        """Test theme creation with spacing"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "name": "Spaced Theme",
                "base_theme": "light",
                "colors": {"primary": "#3b82f6"},
                "spacing": {
                    "unit": 4,
                    "container": 1200
                }
            }
        )
        assert response.status_code == 201
    
    def test_create_theme_default(self, client):
        """Test creating default theme"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "name": "Default Theme",
                "base_theme": "light",
                "colors": {"primary": "#3b82f6"},
                "is_default": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["is_default"] is True
    
    def test_create_theme_duplicate_id(self, client):
        """Test theme creation with duplicate ID"""
        themes["theme-001"] = {
            "theme_id": "theme-001",
            "name": "Existing",
            "base_theme": "light",
            "colors": {},
            "fonts": {},
            "spacing": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "theme_id": "theme-001",
                "name": "Duplicate",
                "base_theme": "light",
                "colors": {}
            }
        )
        assert response.status_code == 400
    
    def test_create_theme_missing_required_fields(self, client):
        """Test theme creation with missing required fields"""
        response = client.post(
            "/api/v1/frontend/themes",
            json={
                "name": "Test"
                # Missing base_theme and colors
            }
        )
        assert response.status_code == 422


# ==================== Layout Management Tests ====================

class TestListLayouts:
    """Test cases for listing layouts"""
    
    def test_list_layouts_success(self, client):
        """Test successful layout listing"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Main Dashboard",
            "type": "dashboard",
            "structure": {
                "header": {"height": 64},
                "sidebar": {"width": 240},
                "content": {"flex": 1}
            },
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/layouts")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "layouts" in data["data"]
    
    def test_list_layouts_with_type_filter(self, client):
        """Test layout listing with type filter"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Dashboard",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/layouts?type=dashboard")
        assert response.status_code == 200
    
    def test_list_layouts_with_default_filter(self, client):
        """Test layout listing with default filter"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Default Layout",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": True,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/layouts?is_default=true")
        assert response.status_code == 200
    
    def test_list_layouts_with_pagination(self, client):
        """Test layout listing with pagination"""
        for i in range(5):
            layouts[f"layout-{i:03d}"] = {
                "layout_id": f"layout-{i:03d}",
                "name": f"Layout {i}",
                "type": "dashboard",
                "structure": {},
                "breakpoints": {},
                "is_default": False,
                "created_at": "2024-01-01",
                "updated_at": "2024-01-01"
            }
        
        response = client.get("/api/v1/frontend/layouts?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["layouts"]) == 2
        assert data["data"]["total"] == 5
    
    def test_list_layouts_empty(self, client):
        """Test listing layouts when none exist"""
        response = client.get("/api/v1/frontend/layouts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["layouts"]) == 0


class TestCreateLayout:
    """Test cases for creating layouts"""
    
    def test_create_layout_success(self, client):
        """Test successful layout creation"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Main Dashboard",
                "type": "dashboard",
                "structure": {
                    "header": {"height": 64},
                    "sidebar": {"width": 240},
                    "content": {"flex": 1}
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "layout_id" in data["data"]
        assert data["data"]["name"] == "Main Dashboard"
    
    def test_create_layout_with_custom_id(self, client):
        """Test layout creation with custom ID"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "layout_id": "custom-layout-001",
                "name": "Custom Layout",
                "type": "page",
                "structure": {"header": {"height": 72}}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["layout_id"] == "custom-layout-001"
    
    def test_create_layout_with_breakpoints(self, client):
        """Test layout creation with breakpoints"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Responsive Layout",
                "type": "dashboard",
                "structure": {"header": {"height": 64}},
                "breakpoints": {
                    "mobile": {"sidebar": {"width": 0}},
                    "tablet": {"sidebar": {"width": 200}},
                    "desktop": {"sidebar": {"width": 240}}
                }
            }
        )
        assert response.status_code == 201
    
    def test_create_layout_default(self, client):
        """Test creating default layout"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Default Layout",
                "type": "dashboard",
                "structure": {},
                "is_default": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["is_default"] is True
    
    def test_create_layout_duplicate_id(self, client):
        """Test layout creation with duplicate ID"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Existing",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "layout_id": "layout-001",
                "name": "Duplicate",
                "type": "dashboard",
                "structure": {}
            }
        )
        assert response.status_code == 400
    
    def test_create_layout_missing_required_fields(self, client):
        """Test layout creation with missing required fields"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Test"
                # Missing type and structure
            }
        )
        assert response.status_code == 422


class TestGetLayout:
    """Test cases for getting layout details"""
    
    def test_get_layout_success(self, client):
        """Test successful layout retrieval"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Main Dashboard",
            "type": "dashboard",
            "structure": {
                "header": {"height": 64},
                "sidebar": {"width": 240}
            },
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get("/api/v1/frontend/layouts/layout-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["layout_id"] == "layout-001"
    
    def test_get_layout_not_found(self, client):
        """Test getting non-existent layout"""
        response = client.get("/api/v1/frontend/layouts/nonexistent")
        assert response.status_code == 404


class TestUpdateLayout:
    """Test cases for updating layouts"""
    
    def test_update_layout_name(self, client):
        """Test updating layout name"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Old Name",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/layouts/layout-001",
            json={"name": "New Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "New Name"
    
    def test_update_layout_structure(self, client):
        """Test updating layout structure"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Dashboard",
            "type": "dashboard",
            "structure": {"header": {"height": 64}},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/layouts/layout-001",
            json={"structure": {"header": {"height": 72}, "footer": {"height": 48}}}
        )
        assert response.status_code == 200
    
    def test_update_layout_breakpoints(self, client):
        """Test updating layout breakpoints"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Dashboard",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.patch(
            "/api/v1/frontend/layouts/layout-001",
            json={"breakpoints": {"mobile": {"sidebar": {"width": 0}}}}
        )
        assert response.status_code == 200
    
    def test_update_layout_not_found(self, client):
        """Test updating non-existent layout"""
        response = client.patch(
            "/api/v1/frontend/layouts/nonexistent",
            json={"name": "New Name"}
        )
        assert response.status_code == 404


class TestDeleteLayout:
    """Test cases for deleting layouts"""
    
    def test_delete_layout_success(self, client):
        """Test successful layout deletion"""
        layouts["layout-001"] = {
            "layout_id": "layout-001",
            "name": "Dashboard",
            "type": "dashboard",
            "structure": {},
            "breakpoints": {},
            "is_default": False,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.delete("/api/v1/frontend/layouts/layout-001")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["deleted"] is True
        assert "layout-001" not in layouts
    
    def test_delete_layout_not_found(self, client):
        """Test deleting non-existent layout"""
        response = client.delete("/api/v1/frontend/layouts/nonexistent")
        assert response.status_code == 404


# ==================== Localization Tests ====================

class TestLocalization:
    """Test cases for localization management"""
    
    def test_get_localization_all(self, client):
        """Test getting all localizations"""
        response = client.get("/api/v1/frontend/localization")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "available_languages" in data["data"]
        assert "localization" in data["data"]
    
    def test_get_localization_specific_language(self, client):
        """Test getting localization for specific language"""
        response = client.get("/api/v1/frontend/localization?language=en-US")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["language"] == "en-US"
        assert "translations" in data["data"]
    
    def test_get_localization_chinese(self, client):
        """Test getting Chinese localization"""
        response = client.get("/api/v1/frontend/localization?language=zh-CN")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["language"] == "zh-CN"
    
    def test_get_localization_nonexistent_language(self, client):
        """Test getting localization for non-existent language"""
        response = client.get("/api/v1/frontend/localization?language=fr-FR")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["language"] == "fr-FR"
        assert len(data["data"]["translations"]) == 0
    
    def test_update_localization_existing_language(self, client):
        """Test updating localization for existing language"""
        response = client.patch(
            "/api/v1/frontend/localization",
            json={
                "language": "en-US",
                "translations": {
                    "new_key": "New Value",
                    "dashboard": "Updated Dashboard"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["language"] == "en-US"
    
    def test_update_localization_new_language(self, client):
        """Test updating localization for new language"""
        response = client.patch(
            "/api/v1/frontend/localization",
            json={
                "language": "es-ES",
                "translations": {
                    "welcome": "Bienvenido",
                    "dashboard": "Panel"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["language"] == "es-ES"
    
    def test_update_localization_chinese(self, client):
        """Test updating Chinese localization"""
        response = client.patch(
            "/api/v1/frontend/localization",
            json={
                "language": "zh-CN",
                "translations": {
                    "new_feature": "新功能",
                    "settings": "设置"
                }
            }
        )
        assert response.status_code == 200
    
    def test_update_localization_empty_translations(self, client):
        """Test updating localization with empty translations"""
        response = client.patch(
            "/api/v1/frontend/localization",
            json={
                "language": "en-US",
                "translations": {}
            }
        )
        assert response.status_code == 200
    
    def test_update_localization_missing_required_fields(self, client):
        """Test updating localization with missing required fields"""
        response = client.patch(
            "/api/v1/frontend/localization",
            json={
                "language": "en-US"
                # Missing translations
            }
        )
        assert response.status_code == 422


# ==================== Data Validation Tests ====================

class TestDataValidation:
    """Test cases for data validation"""
    
    def test_component_create_validation(self):
        """Test ComponentCreate model validation"""
        component = ComponentCreate(
            name="Test Component",
            type="button",
            category="ui",
            description="Test",
            code="code"
        )
        assert component.name == "Test Component"
        assert component.is_public is False  # Default value
    
    def test_component_update_validation(self):
        """Test ComponentUpdate model validation"""
        # All fields optional
        component = ComponentUpdate()
        assert component.name is None
        assert component.code is None
    
    def test_theme_create_validation(self):
        """Test ThemeCreate model validation"""
        theme = ThemeCreate(
            name="Test Theme",
            base_theme="light",
            colors={"primary": "#3b82f6"}
        )
        assert theme.name == "Test Theme"
        assert theme.is_default is False  # Default value
    
    def test_theme_update_validation(self):
        """Test ThemeUpdate model validation"""
        # All fields optional
        theme = ThemeUpdate()
        assert theme.name is None
        assert theme.colors is None
    
    def test_layout_create_validation(self):
        """Test LayoutCreate model validation"""
        layout = LayoutCreate(
            name="Test Layout",
            type="dashboard",
            structure={"header": {"height": 64}}
        )
        assert layout.name == "Test Layout"
        assert layout.is_default is False  # Default value
    
    def test_layout_update_validation(self):
        """Test LayoutUpdate model validation"""
        # All fields optional
        layout = LayoutUpdate()
        assert layout.name is None
        assert layout.structure is None
    
    def test_localization_update_validation(self):
        """Test LocalizationUpdate model validation"""
        loc = LocalizationUpdate(
            language="en-US",
            translations={"key": "value"}
        )
        assert loc.language == "en-US"


# ==================== Edge Cases and Error Handling ====================

class TestEdgeCases:
    """Test cases for edge cases and error handling"""
    
    def test_special_characters_in_names(self, client):
        """Test creating component with special characters"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "Component & Co.",
                "type": "button",
                "category": "ui",
                "description": "Test",
                "code": "code"
            }
        )
        assert response.status_code == 201
    
    def test_unicode_in_names(self, client):
        """Test creating component with unicode characters"""
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "组件",
                "type": "button",
                "category": "ui",
                "description": "测试",
                "code": "code"
            }
        )
        assert response.status_code == 201
    
    def test_large_code_content(self, client):
        """Test creating component with large code content"""
        large_code = "code " * 10000
        response = client.post(
            "/api/v1/frontend/components",
            json={
                "name": "Large Component",
                "type": "button",
                "category": "ui",
                "description": "Large",
                "code": large_code
            }
        )
        assert response.status_code == 201
    
    def test_complex_structure(self, client):
        """Test creating layout with complex structure"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Complex Layout",
                "type": "dashboard",
                "structure": {
                    "header": {
                        "height": 64,
                        "components": ["logo", "nav", "user-menu"]
                    },
                    "sidebar": {
                        "width": 240,
                        "collapsible": True,
                        "components": ["menu", "widgets"]
                    },
                    "content": {
                        "flex": 1,
                        "padding": 24,
                        "maxWidth": 1200
                    },
                    "footer": {
                        "height": 48,
                        "components": ["copyright", "links"]
                    }
                }
            }
        )
        assert response.status_code == 201
    
    def test_empty_structure(self, client):
        """Test creating layout with empty structure"""
        response = client.post(
            "/api/v1/frontend/layouts",
            json={
                "name": "Empty Layout",
                "type": "page",
                "structure": {}
            }
        )
        assert response.status_code == 201
    
    def test_pagination_offset_beyond_data(self, client):
        """Test pagination with offset beyond available data"""
        response = client.get("/api/v1/frontend/components?limit=10&offset=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["components"]) == 0
    
    def test_multiple_filters(self, client):
        """Test listing with multiple filters"""
        components["comp-001"] = {
            "component_id": "comp-001",
            "name": "Button",
            "type": "button",
            "category": "ui",
            "description": "Button",
            "props": {},
            "code": "code",
            "dependencies": [],
            "is_public": True,
            "status": "active",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01"
        }
        
        response = client.get(
            "/api/v1/frontend/components?type=button&category=ui&is_public=true&status=active"
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
