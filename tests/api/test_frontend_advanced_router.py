# -*- coding: utf-8 -*-
"""
Test suite for Frontend Advanced Router (repository-backed).

The router persists everything through
:class:`core.repositories.frontend_repository_impl.FrontendRepositoryImpl`.
Rather than reaching into deleted module-level in-memory dicts (``components`` /
``themes`` / ``layouts`` / ``localization`` — removed when the router moved to
the repository pattern), these tests override the repository dependency with a
faithful in-memory double.  This keeps the tests fast and deterministic while
still exercising the real routing, validation, permission and response-mapping
logic.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.frontend_advanced_router import (
    ComponentCreate,
    ComponentUpdate,
    LayoutCreate,
    LayoutUpdate,
    LocalizationUpdate,
    ThemeCreate,
    ThemeUpdate,
    get_frontend_repository,
    router,
)
from api.middleware.auth_middleware import get_current_active_user


class _FakeFrontendRepository:
    """In-memory stand-in for ``FrontendRepositoryImpl``."""

    def __init__(self) -> None:
        self.components: dict = {}
        self.themes: dict = {}
        self.layouts: dict = {}
        self.localizations: dict = {}  # language -> {key: value}

    # ---- components ----
    async def create_component(self, component: dict) -> str:
        self.components[component["id"]] = dict(component)
        return component["id"]

    async def get_component(self, component_id: str):
        return self.components.get(component_id)

    async def list_components(self, filters=None, limit: int = 100, offset: int = 0):
        items = list(self.components.values())
        if filters:
            for key, value in filters.items():
                items = [i for i in items if i.get(key) == value]
        return items[offset : offset + limit]

    async def update_component(self, component_id: str, updates: dict) -> bool:
        if component_id not in self.components:
            return False
        self.components[component_id].update(updates)
        return True

    async def delete_component(self, component_id: str) -> bool:
        return self.components.pop(component_id, None) is not None

    async def count_components(self, filters=None) -> int:
        return len(await self.list_components(filters=filters, limit=10**9))

    # ---- themes ----
    async def create_theme(self, theme: dict) -> str:
        self.themes[theme["id"]] = dict(theme)
        return theme["id"]

    async def get_theme(self, theme_id: str):
        return self.themes.get(theme_id)

    async def list_themes(self, filters=None, limit: int = 100, offset: int = 0):
        items = list(self.themes.values())
        if filters:
            for key, value in filters.items():
                items = [i for i in items if i.get(key) == value]
        return items[offset : offset + limit]

    async def count_themes(self, filters=None) -> int:
        return len(await self.list_themes(filters=filters, limit=10**9))

    # ---- layouts ----
    async def create_layout(self, layout: dict) -> str:
        self.layouts[layout["id"]] = dict(layout)
        return layout["id"]

    async def get_layout(self, layout_id: str):
        return self.layouts.get(layout_id)

    async def list_layouts(self, filters=None, limit: int = 100, offset: int = 0):
        items = list(self.layouts.values())
        if filters:
            for key, value in filters.items():
                items = [i for i in items if i.get(key) == value]
        return items[offset : offset + limit]

    async def update_layout(self, layout_id: str, updates: dict) -> bool:
        if layout_id not in self.layouts:
            return False
        self.layouts[layout_id].update(updates)
        return True

    async def delete_layout(self, layout_id: str) -> bool:
        return self.layouts.pop(layout_id, None) is not None

    async def count_layouts(self, filters=None) -> int:
        return len(await self.list_layouts(filters=filters, limit=10**9))

    # ---- localization ----
    async def list_localizations(self, language=None, limit: int = 1000):
        records = []
        for lang, translations in self.localizations.items():
            if language and lang != language:
                continue
            for key, value in translations.items():
                records.append(
                    {
                        "language": lang,
                        "translation_key": key,
                        "translation_value": value,
                    }
                )
        return records[:limit]

    async def upsert_localization(
        self, language: str, translation_key: str, translation_value: str, context=None
    ) -> bool:
        self.localizations.setdefault(language, {})[translation_key] = translation_value
        return True


@pytest.fixture
def fake_repo() -> _FakeFrontendRepository:
    return _FakeFrontendRepository()


@pytest.fixture
def admin_user():
    user = Mock()
    user.id = "admin-1"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def client(fake_repo, admin_user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    app.dependency_overrides[get_frontend_repository] = lambda: fake_repo
    return TestClient(app)


# ---------------------------------------------------------------------------
# Component endpoints
# ---------------------------------------------------------------------------


class TestComponentEndpoints:
    def test_list_components_empty(self, client):
        response = client.get("/api/v1/frontend/components")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["components"] == []
        assert data["total"] == 0

    def test_create_and_get_component(self, client):
        payload = {
            "name": "CustomButton",
            "type": "button",
            "category": "ui",
            "description": "A custom button",
            "code": "<button/>",
        }
        created = client.post("/api/v1/frontend/components", json=payload)
        assert created.status_code == 201, created.text
        component = created.json()["data"]
        assert component["name"] == "CustomButton"
        assert component["status"] == "active"
        assert component["created_by"] == "admin"

        fetched = client.get(f"/api/v1/frontend/components/{component['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["data"]["id"] == component["id"]

    def test_list_components_with_type_filter(self, client):
        client.post(
            "/api/v1/frontend/components",
            json={"name": "Button", "type": "button", "category": "ui", "description": "d", "code": "x"},
        )
        client.post(
            "/api/v1/frontend/components",
            json={"name": "Chart", "type": "chart", "category": "data", "description": "d", "code": "y"},
        )
        response = client.get("/api/v1/frontend/components?type=button")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        assert data["components"][0]["type"] == "button"

    def test_get_component_not_found(self, client):
        response = client.get("/api/v1/frontend/components/does-not-exist")
        assert response.status_code == 404

    def test_update_component(self, client):
        created = client.post(
            "/api/v1/frontend/components",
            json={"name": "Button", "type": "button", "category": "ui", "description": "d", "code": "x"},
        ).json()["data"]
        response = client.patch(
            f"/api/v1/frontend/components/{created['id']}",
            json={"description": "updated", "status": "deprecated"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["description"] == "updated"
        assert data["status"] == "deprecated"

    def test_update_component_not_found(self, client):
        response = client.patch(
            "/api/v1/frontend/components/nope", json={"description": "x"}
        )
        assert response.status_code == 404

    def test_delete_component(self, client):
        created = client.post(
            "/api/v1/frontend/components",
            json={"name": "Button", "type": "button", "category": "ui", "description": "d", "code": "x"},
        ).json()["data"]
        response = client.delete(f"/api/v1/frontend/components/{created['id']}")
        assert response.status_code == 200
        assert response.json()["data"]["deleted"] is True

    def test_delete_component_not_found(self, client):
        assert client.delete("/api/v1/frontend/components/nope").status_code == 404

    def test_create_component_validation_error(self, client):
        # ``name`` is required
        assert client.post("/api/v1/frontend/components", json={"type": "button"}).status_code == 422


# ---------------------------------------------------------------------------
# Theme endpoints
# ---------------------------------------------------------------------------


class TestThemeEndpoints:
    def test_list_themes_empty(self, client):
        response = client.get("/api/v1/frontend/themes")
        assert response.status_code == 200
        assert response.json()["data"]["themes"] == []

    def test_create_theme(self, client):
        payload = {
            "name": "Dark",
            "base_theme": "light",
            "colors": {"primary": "#000000"},
        }
        response = client.post("/api/v1/frontend/themes", json=payload)
        assert response.status_code == 201, response.text
        data = response.json()["data"]
        assert data["name"] == "Dark"
        assert data["colors"] == {"primary": "#000000"}

    def test_list_themes_with_base_theme_filter(self, client):
        client.post(
            "/api/v1/frontend/themes",
            json={"name": "A", "base_theme": "light", "colors": {}},
        )
        client.post(
            "/api/v1/frontend/themes",
            json={"name": "B", "base_theme": "dark", "colors": {}},
        )
        response = client.get("/api/v1/frontend/themes?base_theme=dark")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        assert data["themes"][0]["base_theme"] == "dark"


# ---------------------------------------------------------------------------
# Layout endpoints
# ---------------------------------------------------------------------------


class TestLayoutEndpoints:
    def test_list_layouts_empty(self, client):
        response = client.get("/api/v1/frontend/layouts")
        assert response.status_code == 200
        assert response.json()["data"]["layouts"] == []

    def test_create_get_update_delete_layout(self, client):
        payload = {
            "name": "Main Dashboard",
            "type": "dashboard",
            "structure": {"header": {"height": 64}},
        }
        created = client.post("/api/v1/frontend/layouts", json=payload)
        assert created.status_code == 201, created.text
        layout = created.json()["data"]
        assert layout["name"] == "Main Dashboard"

        got = client.get(f"/api/v1/frontend/layouts/{layout['id']}")
        assert got.status_code == 200
        assert got.json()["data"]["id"] == layout["id"]

        updated = client.patch(
            f"/api/v1/frontend/layouts/{layout['id']}", json={"name": "Renamed"}
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["name"] == "Renamed"

        deleted = client.delete(f"/api/v1/frontend/layouts/{layout['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["data"]["deleted"] is True

    def test_get_layout_not_found(self, client):
        assert client.get("/api/v1/frontend/layouts/nope").status_code == 404

    def test_update_layout_not_found(self, client):
        assert (
            client.patch("/api/v1/frontend/layouts/nope", json={"name": "x"}).status_code
            == 404
        )

    def test_delete_layout_not_found(self, client):
        assert client.delete("/api/v1/frontend/layouts/nope").status_code == 404


# ---------------------------------------------------------------------------
# Localization endpoints
# ---------------------------------------------------------------------------


class TestLocalizationEndpoints:
    def test_update_and_get_localization(self, client):
        response = client.patch(
            "/api/v1/frontend/localization",
            json={"language": "zh-CN", "translations": {"welcome": "欢迎"}},
        )
        assert response.status_code == 200
        assert response.json()["data"]["translations"]["welcome"] == "欢迎"

        got = client.get("/api/v1/frontend/localization?language=zh-CN")
        assert got.status_code == 200
        assert got.json()["data"]["translations"] == {"welcome": "欢迎"}

    def test_get_localization_all_languages(self, client):
        client.patch(
            "/api/v1/frontend/localization",
            json={"language": "en-US", "translations": {"welcome": "Welcome"}},
        )
        client.patch(
            "/api/v1/frontend/localization",
            json={"language": "zh-CN", "translations": {"welcome": "欢迎"}},
        )
        got = client.get("/api/v1/frontend/localization")
        assert got.status_code == 200
        data = got.json()["data"]
        assert set(data["available_languages"]) == {"en-US", "zh-CN"}
        assert data["localization"]["en-US"]["welcome"] == "Welcome"

    def test_localization_requires_language(self, client):
        assert (
            client.patch("/api/v1/frontend/localization", json={"translations": {}}).status_code
            == 422
        )


# ---------------------------------------------------------------------------
# Permission enforcement
# ---------------------------------------------------------------------------


class TestPermissionEnforcement:
    def test_missing_user_is_rejected(self, fake_repo):
        """Without the auth override the protected endpoints must not return 200."""
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_frontend_repository] = lambda: fake_repo
        anonymous = TestClient(app)
        response = anonymous.get("/api/v1/frontend/components")
        assert response.status_code in (401, 403)
