# -*- coding: utf-8 -*-
"""
Test suite for users_advanced_router.py
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

from api.users_advanced_router import (
    FAKE_ADMIN,
    ActivityLog,
    Notification,
    NotificationUpdate,
    Session,
    TeamMember,
    UserGroup,
    UserGroupCreate,
    UserPermission,
    UserPermissionsResponse,
    UserPreferences,
    UserPreferencesUpdate,
    UserProfile,
    UserProfileUpdate,
    _activity_logs,
    _add_activity_log,
    _get_team_members,
    _get_user_notifications,
    _get_user_preferences,
    _get_user_sessions,
    _user_groups,
    _user_notifications,
    _user_permissions,
    _user_preferences,
    _user_sessions,
    get_current_user,
    router,
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
def mock_disabled_user():
    """Create a mock disabled user"""
    return UserInDB(
        id=3,
        username="disableduser",
        full_name="Disabled User",
        email="disabled@example.com",
        role="user",
        disabled=True,
        hashed_password="hashed",
    )


@pytest.fixture
def client(mock_user):
    """Create a test client with mocked authentication"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override the dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides = {}


@pytest.fixture
def clear_data():
    """Clear in-memory data before each test"""
    _user_preferences.clear()
    _activity_logs.clear()
    _user_sessions.clear()
    _user_notifications.clear()
    _user_permissions.clear()
    _user_groups.clear()
    yield
    _user_preferences.clear()
    _activity_logs.clear()
    _user_sessions.clear()
    _user_notifications.clear()
    _user_permissions.clear()
    _user_groups.clear()


# ============ Profile Endpoints Tests ============


class TestUserProfileEndpoints:
    """Test user profile endpoints"""

    def test_get_user_profile_success(self, client, mock_user, clear_data):
        """Test successful user profile retrieval"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.get_user_by_username = AsyncMock(return_value=mock_user)

            response = client.get("/api/v1/users/profile")

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["role"] == "admin"

    def test_get_user_profile_not_found(self, client, mock_user, clear_data):
        """Test user profile retrieval when user not found"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.get_user_by_username = AsyncMock(return_value=None)

            response = client.get("/api/v1/users/profile")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_update_user_profile_success(self, client, mock_user, clear_data):
        """Test successful user profile update"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.update_user = AsyncMock(return_value=True)
            mock_service.get_user_by_username = AsyncMock(return_value=mock_user)

            response = client.patch(
                "/api/v1/users/profile",
                json={"full_name": "Updated Name", "email": "updated@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "Updated Name"
            assert data["email"] == "updated@example.com"

    def test_update_user_profile_failure(self, client, mock_user, clear_data):
        """Test user profile update failure"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.update_user = AsyncMock(return_value=False)

            response = client.patch("/api/v1/users/profile", json={"full_name": "Updated Name"})

            assert response.status_code == 400
            assert "failed" in response.json()["detail"].lower()

    def test_update_user_profile_validation(self, client, clear_data):
        """Test user profile update with invalid data"""
        response = client.patch(
            "/api/v1/users/profile", json={"full_name": "a" * 101}  # Exceeds max length
        )

        assert response.status_code == 422  # Validation error

    def test_update_user_profile_partial_update(self, client, mock_user, clear_data):
        """Test partial user profile update"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.update_user = AsyncMock(return_value=True)
            mock_service.get_user_by_username = AsyncMock(return_value=mock_user)

            response = client.patch("/api/v1/users/profile", json={"full_name": "New Name Only"})

            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "New Name Only"


# ============ Preferences Endpoints Tests ============


class TestUserPreferencesEndpoints:
    """Test user preferences endpoints"""

    def test_get_user_preferences_success(self, client, clear_data):
        """Test successful user preferences retrieval"""
        response = client.get("/api/v1/users/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "light"
        assert data["language"] == "zh-CN"
        assert data["timezone"] == "Asia/Shanghai"

    def test_update_user_preferences_success(self, client, clear_data):
        """Test successful user preferences update"""
        response = client.patch(
            "/api/v1/users/preferences",
            json={"theme": "dark", "language": "en-US", "notifications_enabled": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["language"] == "en-US"
        assert data["notifications_enabled"] == False

    def test_update_user_preferences_validation_theme(self, client, clear_data):
        """Test user preferences update with invalid theme"""
        response = client.patch("/api/v1/users/preferences", json={"theme": "invalid_theme"})

        assert response.status_code == 422  # Validation error

    def test_update_user_preferences_validation_time_format(self, client, clear_data):
        """Test user preferences update with invalid time format"""
        response = client.patch("/api/v1/users/preferences", json={"time_format": "invalid"})

        assert response.status_code == 422  # Validation error

    def test_update_user_preferences_validation_auto_refresh(self, client, clear_data):
        """Test user preferences update with invalid auto refresh interval"""
        response = client.patch(
            "/api/v1/users/preferences", json={"auto_refresh_interval": 400}  # Exceeds max
        )

        assert response.status_code == 422  # Validation error

    def test_update_user_preferences_partial(self, client, clear_data):
        """Test partial user preferences update"""
        response = client.patch("/api/v1/users/preferences", json={"theme": "dark"})

        assert response.status_code == 200
        data = response.json()
        assert data["theme"] == "dark"
        assert data["language"] == "zh-CN"  # Should remain unchanged


# ============ Activity Endpoints Tests ============


class TestUserActivityEndpoints:
    """Test user activity endpoints"""

    def test_get_user_activity_empty(self, client, clear_data):
        """Test user activity retrieval with no logs"""
        response = client.get("/api/v1/users/activity")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_user_activity_with_logs(self, client, mock_user, clear_data):
        """Test user activity retrieval with logs"""
        _add_activity_log(
            user_id=mock_user.id,
            username=mock_user.username,
            action="test_action",
            resource_type="test",
        )

        response = client.get("/api/v1/users/activity")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "test_action"

    def test_get_user_activity_with_pagination(self, client, mock_user, clear_data):
        """Test user activity retrieval with pagination"""
        for i in range(10):
            _add_activity_log(
                user_id=mock_user.id,
                username=mock_user.username,
                action=f"action_{i}",
                resource_type="test",
            )

        response = client.get("/api/v1/users/activity?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_user_activity_limit(self, client, mock_user, clear_data):
        """Test user activity retrieval with limit"""
        for i in range(100):
            _add_activity_log(
                user_id=mock_user.id,
                username=mock_user.username,
                action=f"action_{i}",
                resource_type="test",
            )

        response = client.get("/api/v1/users/activity?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 50


# ============ Sessions Endpoints Tests ============


class TestUserSessionsEndpoints:
    """Test user sessions endpoints"""

    def test_get_user_sessions_success(self, client, clear_data):
        """Test successful user sessions retrieval"""
        response = client.get("/api/v1/users/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_delete_user_session_success(self, client, mock_user, clear_data):
        """Test successful user session deletion"""
        sessions = _get_user_sessions(mock_user.id)
        session_id = sessions[0].id

        response = client.delete(f"/api/v1/users/sessions/{session_id}")

        assert response.status_code == 204

    def test_delete_user_session_not_found(self, client, clear_data):
        """Test user session deletion when session not found"""
        response = client.delete("/api/v1/users/sessions/non-existent-session")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ============ Notifications Endpoints Tests ============


class TestUserNotificationsEndpoints:
    """Test user notifications endpoints"""

    def test_get_user_notifications_all(self, client, clear_data):
        """Test getting all user notifications"""
        response = client.get("/api/v1/users/notifications")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_user_notifications_unread_only(self, client, clear_data):
        """Test getting only unread notifications"""
        response = client.get("/api/v1/users/notifications?unread_only=true")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(not n["read"] for n in data)

    def test_get_user_notifications_with_limit(self, client, clear_data):
        """Test getting notifications with limit"""
        response = client.get("/api/v1/users/notifications?limit=1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_update_notification_success(self, client, mock_user, clear_data):
        """Test successful notification update"""
        notifications = _get_user_notifications(mock_user.id)
        notification_id = notifications[0].id

        response = client.patch(
            f"/api/v1/users/notifications/{notification_id}", json={"read": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["read"] == True

    def test_update_notification_not_found(self, client, clear_data):
        """Test notification update when notification not found"""
        response = client.patch("/api/v1/users/notifications/non-existent", json={"read": True})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_bulk_update_notifications_read_all(self, client, clear_data):
        """Test bulk update notifications - mark all as read"""
        response = client.patch("/api/v1/users/notifications", json={"read_all": True})

        assert response.status_code == 200
        data = response.json()
        assert "marked" in data["message"].lower()

    def test_bulk_update_notifications_no_changes(self, client, clear_data):
        """Test bulk update notifications with no changes"""
        response = client.patch("/api/v1/users/notifications", json={})

        assert response.status_code == 200
        data = response.json()
        assert "no changes" in data["message"].lower()


# ============ Teams Endpoints Tests ============


class TestUserTeamsEndpoints:
    """Test user teams endpoints"""

    def test_get_team_members_success(self, client, clear_data):
        """Test successful team members retrieval"""
        response = client.get("/api/v1/users/teams")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


# ============ Profiles Endpoints Tests ============


class TestUserProfilesEndpoints:
    """Test user profiles endpoints"""

    def test_get_all_profiles_admin(self, client, mock_user, clear_data):
        """Test getting all profiles with admin role"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.list_users = AsyncMock(return_value=[mock_user])

            response = client.get("/api/v1/users/profiles")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1

    def test_get_all_profiles_forbidden(self, client, mock_regular_user, clear_data):
        """Test getting all profiles without admin role"""
        # Override with regular user
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: mock_regular_user

        with TestClient(app) as test_client:
            response = test_client.get("/api/v1/users/profiles")

            assert response.status_code == 403
            assert "admin" in response.json()["detail"].lower()

        app.dependency_overrides = {}

    def test_get_all_profiles_with_pagination(self, client, mock_user, clear_data):
        """Test getting all profiles with pagination"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            users = [mock_user] * 20
            mock_service.list_users = AsyncMock(return_value=users)

            response = client.get("/api/v1/users/profiles?limit=10&offset=0")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 10


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
        with patch("api.users_advanced_router.verify_token", return_value=None):
            result = await get_current_user(token="invalid")

            assert result.username == "dev-admin"

    @pytest.mark.asyncio
    async def test_get_current_user_disabled_user(self, mock_disabled_user):
        """Test get_current_user with disabled user raises exception"""
        with patch("api.users_advanced_router.verify_token", return_value={"sub": "disableduser"}):
            with patch(
                "api.users_advanced_router.get_user", AsyncMock(return_value=mock_disabled_user)
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(token="valid_token")

                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
                assert "disabled" in exc_info.value.detail.lower()


# ============ Data Validation Tests ============


class TestDataValidation:
    """Test data validation for models"""

    def test_user_profile_update_max_length_validation(self):
        """Test UserProfileUpdate max length validation"""
        with pytest.raises(Exception):
            UserProfileUpdate(full_name="a" * 101)

    def test_user_preferences_update_theme_validation(self):
        """Test UserPreferencesUpdate theme validation"""
        with pytest.raises(Exception):
            UserPreferencesUpdate(theme="invalid")

    def test_user_preferences_update_time_format_validation(self):
        """Test UserPreferencesUpdate time format validation"""
        with pytest.raises(Exception):
            UserPreferencesUpdate(time_format="invalid")

    def test_user_preferences_update_auto_refresh_min_validation(self):
        """Test UserPreferencesUpdate auto refresh min validation"""
        with pytest.raises(Exception):
            UserPreferencesUpdate(auto_refresh_interval=4)

    def test_user_preferences_update_auto_refresh_max_validation(self):
        """Test UserPreferencesUpdate auto refresh max validation"""
        with pytest.raises(Exception):
            UserPreferencesUpdate(auto_refresh_interval=301)

    def test_user_group_create_name_min_validation(self):
        """Test UserGroupCreate name min length validation"""
        with pytest.raises(Exception):
            UserGroupCreate(name="")

    def test_user_group_create_name_max_validation(self):
        """Test UserGroupCreate name max length validation"""
        with pytest.raises(Exception):
            UserGroupCreate(name="a" * 101)

    def test_user_permission_pattern_validation(self):
        """Test UserPermission pattern validation"""
        with pytest.raises(Exception):
            UserPermission(asset_id=1, permission="invalid")


# ============ Helper Function Tests ============


class TestHelperFunctions:
    """Test helper functions"""

    def test_get_user_preferences_new_user(self, clear_data):
        """Test _get_user_preferences creates default for new user"""
        result = _get_user_preferences(user_id=999)

        assert isinstance(result, UserPreferences)
        assert result.theme == "light"

    def test_get_user_preferences_existing_user(self, clear_data):
        """Test _get_user_preferences returns existing for known user"""
        _user_preferences[1] = UserPreferences(theme="dark")
        result = _get_user_preferences(user_id=1)

        assert result.theme == "dark"

    def test_add_activity_log(self, clear_data):
        """Test _add_activity_log creates log entry"""
        log = _add_activity_log(
            user_id=1, username="test", action="test_action", resource_type="test"
        )

        assert isinstance(log, ActivityLog)
        assert log.action == "test_action"
        assert len(_activity_logs) == 1

    def test_add_activity_log_limit(self, clear_data):
        """Test _add_activity_log respects 1000 log limit"""
        for i in range(1005):
            _add_activity_log(
                user_id=1, username="test", action=f"action_{i}", resource_type="test"
            )

        assert len(_activity_logs) == 1000

    def test_get_user_sessions_new_user(self, clear_data):
        """Test _get_user_sessions creates default for new user"""
        result = _get_user_sessions(user_id=999)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].is_current == True

    def test_get_user_notifications_new_user(self, clear_data):
        """Test _get_user_notifications creates default for new user"""
        result = _get_user_notifications(user_id=999)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_team_members(self, clear_data):
        """Test _get_team_members returns mock data"""
        result = _get_team_members()

        assert isinstance(result, list)
        assert len(result) == 2


# ============ Integration Tests ============


class TestIntegration:
    """Integration tests for user operations"""

    def test_full_user_profile_workflow(self, client, mock_user, clear_data):
        """Test complete user profile workflow"""
        with patch("api.users_advanced_router.user_service") as mock_service:
            mock_service.get_user_by_username = AsyncMock(return_value=mock_user)
            mock_service.update_user = AsyncMock(return_value=True)

            # Get profile
            response = client.get("/api/v1/users/profile")
            assert response.status_code == 200
            assert response.json()["username"] == "testuser"

            # Update profile
            response = client.patch("/api/v1/users/profile", json={"full_name": "New Name"})
            assert response.status_code == 200
            assert response.json()["full_name"] == "New Name"

            # Get preferences
            response = client.get("/api/v1/users/preferences")
            assert response.status_code == 200
            assert response.json()["theme"] == "light"

            # Update preferences
            response = client.patch("/api/v1/users/preferences", json={"theme": "dark"})
            assert response.status_code == 200
            assert response.json()["theme"] == "dark"

    def test_notification_workflow(self, client, mock_user, clear_data):
        """Test complete notification workflow"""
        # Get notifications
        response = client.get("/api/v1/users/notifications")
        assert response.status_code == 200
        notifications = response.json()
        assert len(notifications) >= 2

        # Mark as read
        notification_id = notifications[0]["id"]
        response = client.patch(
            f"/api/v1/users/notifications/{notification_id}", json={"read": True}
        )
        assert response.status_code == 200
        assert response.json()["read"] == True

        # Mark all as read
        response = client.patch("/api/v1/users/notifications", json={"read_all": True})
        assert response.status_code == 200
        assert "marked" in response.json()["message"].lower()

    def test_session_workflow(self, client, mock_user, clear_data):
        """Test complete session workflow"""
        # Get sessions
        response = client.get("/api/v1/users/sessions")
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) >= 1

        # Delete session
        session_id = sessions[0]["id"]
        response = client.delete(f"/api/v1/users/sessions/{session_id}")
        assert response.status_code == 204


# ============ Error Handling Tests ============


class TestErrorHandling:
    """Test error handling"""

    def test_large_data_handling(self, client, mock_user, clear_data):
        """Test handling of large data sets"""
        # Add many activity logs
        for i in range(500):
            _add_activity_log(
                user_id=mock_user.id,
                username=mock_user.username,
                action=f"action_{i}",
                resource_type="test",
            )

        # Should handle pagination correctly
        response = client.get("/api/v1/users/activity?limit=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
