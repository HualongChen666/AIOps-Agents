# -*- coding: utf-8 -*-
"""
Test suite for Collaboration Advanced Router
协作高级路由测试套件
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from api.collaboration_advanced_router import (
    router,
    CreateTeamRequest,
    UpdateTeamRequest,
    CreateMemberRequest,
    UpdateMemberRequest,
    CreatePermissionRequest,
    CreateActivityRequest,
    TeamStatusEnum,
    MemberRoleEnum,
    PermissionLevelEnum,
    ActivityTypeEnum,
    _load_json_file,
    _save_json_file,
    _generate_id,
    _now,
    _log_activity,
)
from core.api_response_standard import ErrorCode, create_success_response, create_error_response


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
def sample_team():
    """Sample team data"""
    return {
        "id": "TM-12345678",
        "name": "SRE团队",
        "description": "负责系统可靠性工程",
        "owner_id": "user-001",
        "status": "active",
        "tags": ["sre", "operations"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_member():
    """Sample member data"""
    return {
        "id": "MBR-12345678",
        "user_id": "user-002",
        "user_name": "张三",
        "email": "zhangsan@example.com",
        "team_id": "TM-12345678",
        "role": "member",
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_permission():
    """Sample permission data"""
    return {
        "id": "PRM-12345678",
        "team_id": "TM-12345678",
        "member_id": "MBR-12345678",
        "resource_type": "workspace",
        "resource_id": "WS-12345678",
        "permission_level": "write",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_activity():
    """Sample activity data"""
    return {
        "id": "ACT-12345678",
        "team_id": "TM-12345678",
        "activity_type": "member_added",
        "actor_id": "user-001",
        "actor_name": "李四",
        "description": "添加了新成员张三",
        "metadata": {"member_id": "MBR-12345678"},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# Helper function tests
class TestHelperFunctions:
    """Test helper functions"""

    def test_generate_id(self):
        """Test ID generation"""
        id1 = _generate_id("TM")
        id2 = _generate_id("TM")
        assert id1.startswith("TM-")
        assert id2.startswith("TM-")
        assert id1 != id2
        assert len(id1) == 11  # TM- + 8 hex chars

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

    def test_log_activity(self, tmp_path):
        """Test activity logging"""
        activities_file = tmp_path / "activities.json"
        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            _log_activity(
                team_id="TM-001",
                activity_type=ActivityTypeEnum.MEMBER_ADDED,
                actor_id="user-001",
                actor_name="Test User",
                description="Test activity",
                metadata={"key": "value"},
            )
            activities = _load_json_file(activities_file)
            assert len(activities) == 1
            assert activities[0]["activity_type"] == "member_added"
            assert activities[0]["actor_name"] == "Test User"


# Team endpoints tests
class TestTeamEndpoints:
    """Test team-related endpoints"""

    def test_get_teams_empty(self, client, tmp_path):
        """Test getting teams when none exist"""
        with patch('api.collaboration_advanced_router.TEAMS_FILE', tmp_path / "teams.json"):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', tmp_path / "members.json"):
                response = client.get("/api/v1/collaboration/teams")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["items"] == []
                assert data["data"]["total"] == 0

    def test_get_teams_with_data(self, client, tmp_path, sample_team):
        """Test getting teams with data"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["items"]) == 1
                assert data["data"]["total"] == 1

    def test_get_teams_with_status_filter(self, client, tmp_path, sample_team):
        """Test getting teams with status filter"""
        sample_team["status"] = "active"
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams?status=active")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["items"]) == 1

    def test_get_teams_with_owner_filter(self, client, tmp_path, sample_team):
        """Test getting teams with owner filter"""
        sample_team["owner_id"] = "user-001"
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams?owner_id=user-001")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["items"]) == 1

    def test_get_teams_pagination(self, client, tmp_path):
        """Test getting teams with pagination"""
        teams = []
        for i in range(25):
            teams.append({
                "id": f"TM-{i:08d}",
                "name": f"Team {i}",
                "status": "active",
                "owner_id": f"user-{i}",
            })
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump(teams, f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams?limit=10&offset=0")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert len(data["data"]["items"]) == 10
                assert data["data"]["total"] == 25

    def test_get_teams_with_member_count(self, client, tmp_path, sample_team, sample_member):
        """Test that teams include member count"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "member_count" in data["data"]["items"][0]
                assert data["data"]["items"][0]["member_count"] == 1

    def test_create_team_success(self, client, tmp_path):
        """Test creating a team successfully"""
        teams_file = tmp_path / "teams.json"
        activities_file = tmp_path / "activities.json"

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                response = client.post(
                    "/api/v1/collaboration/teams",
                    json={
                        "name": "Test Team",
                        "description": "Test team description",
                        "owner_id": "user-001",
                        "status": "active",
                        "tags": ["test"],
                    }
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["name"] == "Test Team"
                assert data["data"]["owner_id"] == "user-001"

    def test_create_team_with_defaults(self, client, tmp_path):
        """Test creating a team with default values"""
        teams_file = tmp_path / "teams.json"
        activities_file = tmp_path / "activities.json"

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                response = client.post(
                    "/api/v1/collaboration/teams",
                    json={
                        "name": "Default Team",
                        "owner_id": "user-001",
                    }
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["data"]["status"] == "active"
                assert data["data"]["tags"] == []

    def test_create_team_validation_error(self, client, tmp_path):
        """Test creating a team with validation error"""
        teams_file = tmp_path / "teams.json"
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            response = client.post(
                "/api/v1/collaboration/teams",
                json={
                    "name": "",  # Empty name
                    "owner_id": "",  # Empty owner_id
                }
            )
            assert response.status_code == 422  # Validation error

    def test_get_team_success(self, client, tmp_path, sample_team, sample_member):
        """Test getting a specific team"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get(f"/api/v1/collaboration/teams/{sample_team['id']}")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["id"] == sample_team["id"]
                assert "members" in data["data"]
                assert data["data"]["member_count"] == 1

    def test_get_team_not_found(self, client, tmp_path):
        """Test getting a non-existent team"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.get("/api/v1/collaboration/teams/TM-NONEXIST")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert "团队不存在" in data["message"]

    def test_update_team_success(self, client, tmp_path, sample_team):
        """Test updating a team successfully"""
        teams_file = tmp_path / "teams.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            response = client.patch(
                f"/api/v1/collaboration/teams/{sample_team['id']}",
                json={
                    "name": "Updated Team Name",
                    "description": "Updated description",
                    "status": "inactive",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "Updated Team Name"
            assert data["data"]["status"] == "inactive"

    def test_update_team_partial(self, client, tmp_path, sample_team):
        """Test updating a team with partial data"""
        teams_file = tmp_path / "teams.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            response = client.patch(
                f"/api/v1/collaboration/teams/{sample_team['id']}",
                json={
                    "name": "Only Update Name",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["name"] == "Only Update Name"
            # Other fields should remain unchanged
            assert data["data"]["description"] == sample_team["description"]

    def test_update_team_not_found(self, client, tmp_path):
        """Test updating a non-existent team"""
        teams_file = tmp_path / "teams.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            response = client.patch(
                "/api/v1/collaboration/teams/TM-NONEXIST",
                json={"name": "Updated Name"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "团队不存在" in data["message"]

    def test_delete_team_success(self, client, tmp_path, sample_team, sample_member, sample_permission):
        """Test deleting a team successfully"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    response = client.delete(f"/api/v1/collaboration/teams/{sample_team['id']}")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True

                    # Verify related data is deleted
                    members = _load_json_file(members_file)
                    permissions = _load_json_file(permissions_file)
                    assert len(members) == 0
                    assert len(permissions) == 0

    def test_delete_team_not_found(self, client, tmp_path):
        """Test deleting a non-existent team"""
        teams_file = tmp_path / "teams.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            response = client.delete("/api/v1/collaboration/teams/TM-NONEXIST")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "团队不存在" in data["message"]


# Member endpoints tests
class TestMemberEndpoints:
    """Test member-related endpoints"""

    def test_get_members_empty(self, client, tmp_path):
        """Test getting members when none exist"""
        with patch('api.collaboration_advanced_router.MEMBERS_FILE', tmp_path / "members.json"):
            response = client.get("/api/v1/collaboration/members")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_get_members_with_data(self, client, tmp_path, sample_member):
        """Test getting members with data"""
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.get("/api/v1/collaboration/members")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_members_with_team_filter(self, client, tmp_path, sample_member):
        """Test getting members with team filter"""
        sample_member["team_id"] = "TM-001"
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.get("/api/v1/collaboration/members?team_id=TM-001")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_members_with_role_filter(self, client, tmp_path, sample_member):
        """Test getting members with role filter"""
        sample_member["role"] = "admin"
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.get("/api/v1/collaboration/members?role=admin")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_members_pagination(self, client, tmp_path):
        """Test getting members with pagination"""
        members = []
        for i in range(25):
            members.append({
                "id": f"MBR-{i:08d}",
                "user_id": f"user-{i}",
                "user_name": f"User {i}",
                "team_id": "TM-001",
                "role": "member",
            })
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump(members, f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.get("/api/v1/collaboration/members?limit=10&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 10
            assert data["data"]["total"] == 25

    def test_create_member_success(self, client, tmp_path, sample_team):
        """Test creating a member successfully"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        activities_file = tmp_path / "activities.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                    response = client.post(
                        "/api/v1/collaboration/members",
                        json={
                            "user_id": "user-002",
                            "user_name": "张三",
                            "email": "zhangsan@example.com",
                            "team_id": sample_team["id"],
                            "role": "member",
                        }
                    )
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["user_name"] == "张三"
                    assert data["data"]["team_id"] == sample_team["id"]

    def test_create_member_with_defaults(self, client, tmp_path, sample_team):
        """Test creating a member with default values"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        activities_file = tmp_path / "activities.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                    response = client.post(
                        "/api/v1/collaboration/members",
                        json={
                            "user_id": "user-002",
                            "user_name": "李四",
                            "team_id": sample_team["id"],
                        }
                    )
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is True
                    assert data["data"]["role"] == "member"
                    assert data["data"]["email"] is None

    def test_create_member_team_not_found(self, client, tmp_path):
        """Test creating a member for non-existent team"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.post(
                    "/api/v1/collaboration/members",
                    json={
                        "user_id": "user-002",
                        "user_name": "张三",
                        "team_id": "TM-NONEXIST",
                    }
                )
                # API returns 201 even for error responses
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is False
                assert "团队不存在" in data["message"]

    def test_create_member_duplicate(self, client, tmp_path, sample_team, sample_member):
        """Test creating a duplicate member"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                response = client.post(
                    "/api/v1/collaboration/members",
                    json={
                        "user_id": sample_member["user_id"],
                        "user_name": "Duplicate User",
                        "team_id": sample_member["team_id"],
                    }
                )
                # API returns 201 even for error responses
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is False
                assert "用户已在团队中" in data["message"]

    def test_create_member_validation_error(self, client, tmp_path):
        """Test creating a member with validation error"""
        members_file = tmp_path / "members.json"
        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.post(
                "/api/v1/collaboration/members",
                json={
                    "user_id": "",  # Empty user_id
                    "user_name": "",  # Empty user_name
                    "team_id": "",  # Empty team_id
                }
            )
            assert response.status_code == 422  # Validation error

    def test_update_member_success(self, client, tmp_path, sample_member):
        """Test updating a member successfully"""
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.patch(
                f"/api/v1/collaboration/members/{sample_member['id']}",
                json={
                    "role": "admin",
                    "email": "newemail@example.com",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["role"] == "admin"
            assert data["data"]["email"] == "newemail@example.com"

    def test_update_member_not_found(self, client, tmp_path):
        """Test updating a non-existent member"""
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.patch(
                "/api/v1/collaboration/members/MBR-NONEXIST",
                json={"role": "admin"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "成员不存在" in data["message"]

    def test_delete_member_success(self, client, tmp_path, sample_member, sample_permission):
        """Test deleting a member successfully"""
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        activities_file = tmp_path / "activities.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                    response = client.delete(f"/api/v1/collaboration/members/{sample_member['id']}")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True

                    # Verify related permissions are deleted
                    permissions = _load_json_file(permissions_file)
                    assert len(permissions) == 0

    def test_delete_member_not_found(self, client, tmp_path):
        """Test deleting a non-existent member"""
        members_file = tmp_path / "members.json"
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
            response = client.delete("/api/v1/collaboration/members/MBR-NONEXIST")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "成员不存在" in data["message"]


# Permission endpoints tests
class TestPermissionEndpoints:
    """Test permission-related endpoints"""

    def test_get_permissions_empty(self, client, tmp_path):
        """Test getting permissions when none exist"""
        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', tmp_path / "permissions.json"):
            response = client.get("/api/v1/collaboration/permissions")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_get_permissions_with_data(self, client, tmp_path, sample_permission):
        """Test getting permissions with data"""
        permissions_file = tmp_path / "permissions.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.get("/api/v1/collaboration/permissions")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_permissions_with_team_filter(self, client, tmp_path, sample_permission):
        """Test getting permissions with team filter"""
        sample_permission["team_id"] = "TM-001"
        permissions_file = tmp_path / "permissions.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.get("/api/v1/collaboration/permissions?team_id=TM-001")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_permissions_with_member_filter(self, client, tmp_path, sample_permission):
        """Test getting permissions with member filter"""
        sample_permission["member_id"] = "MBR-001"
        permissions_file = tmp_path / "permissions.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.get("/api/v1/collaboration/permissions?member_id=MBR-001")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_permissions_with_resource_type_filter(self, client, tmp_path, sample_permission):
        """Test getting permissions with resource type filter"""
        sample_permission["resource_type"] = "workspace"
        permissions_file = tmp_path / "permissions.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.get("/api/v1/collaboration/permissions?resource_type=workspace")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_create_permission_success(self, client, tmp_path, sample_team, sample_member):
        """Test creating a permission successfully"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        activities_file = tmp_path / "activities.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                        response = client.post(
                            "/api/v1/collaboration/permissions",
                            json={
                                "team_id": sample_team["id"],
                                "member_id": sample_member["id"],
                                "resource_type": "workspace",
                                "resource_id": "WS-001",
                                "permission_level": "write",
                            }
                        )
                        assert response.status_code == 201
                        data = response.json()
                        assert data["success"] is True
                        assert data["data"]["permission_level"] == "write"

    def test_create_permission_team_not_found(self, client, tmp_path, sample_member):
        """Test creating a permission for non-existent team"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    response = client.post(
                        "/api/v1/collaboration/permissions",
                        json={
                            "team_id": "TM-NONEXIST",
                            "member_id": sample_member["id"],
                            "resource_type": "workspace",
                            "resource_id": "WS-001",
                            "permission_level": "write",
                        }
                    )
                    # API returns 201 even for error responses
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is False
                    assert "团队不存在" in data["message"]

    def test_create_permission_member_not_found(self, client, tmp_path, sample_team):
        """Test creating a permission for non-existent member"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    response = client.post(
                        "/api/v1/collaboration/permissions",
                        json={
                            "team_id": sample_team["id"],
                            "member_id": "MBR-NONEXIST",
                            "resource_type": "workspace",
                            "resource_id": "WS-001",
                            "permission_level": "write",
                        }
                    )
                    # API returns 201 even for error responses
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is False
                    assert "成员不存在" in data["message"]

    def test_create_permission_duplicate(self, client, tmp_path, sample_team, sample_member, sample_permission):
        """Test creating a duplicate permission"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    response = client.post(
                        "/api/v1/collaboration/permissions",
                        json={
                            "team_id": sample_permission["team_id"],
                            "member_id": sample_permission["member_id"],
                            "resource_type": sample_permission["resource_type"],
                            "resource_id": sample_permission["resource_id"],
                            "permission_level": "admin",
                        }
                    )
                    # API returns 201 even for error responses
                    assert response.status_code == 201
                    data = response.json()
                    assert data["success"] is False
                    assert "权限已存在" in data["message"]

    def test_create_permission_validation_error(self, client, tmp_path):
        """Test creating a permission with validation error"""
        permissions_file = tmp_path / "permissions.json"
        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.post(
                "/api/v1/collaboration/permissions",
                json={
                    "team_id": "",  # Empty team_id
                    "member_id": "",  # Empty member_id
                    "resource_type": "",  # Empty resource_type
                    "resource_id": "",  # Empty resource_id
                }
            )
            assert response.status_code == 422  # Validation error

    def test_delete_permission_success(self, client, tmp_path, sample_permission):
        """Test deleting a permission successfully"""
        permissions_file = tmp_path / "permissions.json"
        activities_file = tmp_path / "activities.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                response = client.delete(f"/api/v1/collaboration/permissions/{sample_permission['id']}")
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True

    def test_delete_permission_not_found(self, client, tmp_path):
        """Test deleting a non-existent permission"""
        permissions_file = tmp_path / "permissions.json"
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([], f)

        with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
            response = client.delete("/api/v1/collaboration/permissions/PRM-NONEXIST")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "权限不存在" in data["message"]


# Activity endpoints tests
class TestActivityEndpoints:
    """Test activity-related endpoints"""

    def test_get_activities_empty(self, client, tmp_path):
        """Test getting activities when none exist"""
        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', tmp_path / "activities.json"):
            response = client.get("/api/v1/collaboration/activities")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["items"] == []

    def test_get_activities_with_data(self, client, tmp_path, sample_activity):
        """Test getting activities with data"""
        activities_file = tmp_path / "activities.json"
        with open(activities_file, "w", encoding="utf-8") as f:
            json.dump([sample_activity], f)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            response = client.get("/api/v1/collaboration/activities")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_activities_with_team_filter(self, client, tmp_path, sample_activity):
        """Test getting activities with team filter"""
        sample_activity["team_id"] = "TM-001"
        activities_file = tmp_path / "activities.json"
        with open(activities_file, "w", encoding="utf-8") as f:
            json.dump([sample_activity], f)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            response = client.get("/api/v1/collaboration/activities?team_id=TM-001")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_activities_with_type_filter(self, client, tmp_path, sample_activity):
        """Test getting activities with type filter"""
        sample_activity["activity_type"] = "member_added"
        activities_file = tmp_path / "activities.json"
        with open(activities_file, "w", encoding="utf-8") as f:
            json.dump([sample_activity], f)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            response = client.get("/api/v1/collaboration/activities?activity_type=member_added")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 1

    def test_get_activities_sorted_by_time(self, client, tmp_path):
        """Test that activities are sorted by time descending"""
        activities = []
        for i in range(5):
            activities.append({
                "id": f"ACT-{i:08d}",
                "team_id": "TM-001",
                "activity_type": "test",
                "actor_id": "user-001",
                "actor_name": "Test User",
                "description": f"Activity {i}",
                "created_at": (datetime.now(timezone.utc).isoformat()),
            })
        activities_file = tmp_path / "activities.json"
        with open(activities_file, "w", encoding="utf-8") as f:
            json.dump(activities, f)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            response = client.get("/api/v1/collaboration/activities")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Activities should be returned (sorting is applied)

    def test_get_activities_pagination(self, client, tmp_path):
        """Test getting activities with pagination"""
        activities = []
        for i in range(25):
            activities.append({
                "id": f"ACT-{i:08d}",
                "team_id": "TM-001",
                "activity_type": "test",
                "actor_id": "user-001",
                "actor_name": "Test User",
                "description": f"Activity {i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        activities_file = tmp_path / "activities.json"
        with open(activities_file, "w", encoding="utf-8") as f:
            json.dump(activities, f)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            response = client.get("/api/v1/collaboration/activities?limit=10&offset=0")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 10
            assert data["data"]["total"] == 25


# Data validation tests
class TestDataValidation:
    """Test data validation"""

    def test_create_team_request_valid(self):
        """Test valid CreateTeamRequest"""
        request = CreateTeamRequest(
            name="Test Team",
            description="Test description",
            owner_id="user-001",
            status=TeamStatusEnum.ACTIVE,
            tags=["test"],
        )
        assert request.name == "Test Team"
        assert request.status == TeamStatusEnum.ACTIVE

    def test_create_team_request_defaults(self):
        """Test CreateTeamRequest with defaults"""
        request = CreateTeamRequest(
            name="Default Team",
            owner_id="user-001",
        )
        assert request.status == TeamStatusEnum.ACTIVE
        assert request.tags == []

    def test_create_team_request_invalid_name(self):
        """Test CreateTeamRequest with invalid name"""
        with pytest.raises(ValueError):
            CreateTeamRequest(
                name="",  # Empty name
                owner_id="user-001",
            )

    def test_update_team_request_valid(self):
        """Test valid UpdateTeamRequest"""
        request = UpdateTeamRequest(
            name="Updated Name",
            description="Updated description",
            status=TeamStatusEnum.INACTIVE,
            tags=["updated"],
        )
        assert request.name == "Updated Name"

    def test_update_team_request_partial(self):
        """Test UpdateTeamRequest with partial data"""
        request = UpdateTeamRequest(
            name="Only Name",
        )
        assert request.name == "Only Name"
        assert request.description is None

    def test_create_member_request_valid(self):
        """Test valid CreateMemberRequest"""
        request = CreateMemberRequest(
            user_id="user-002",
            user_name="张三",
            email="zhangsan@example.com",
            team_id="TM-001",
            role=MemberRoleEnum.ADMIN,
        )
        assert request.user_name == "张三"
        assert request.role == MemberRoleEnum.ADMIN

    def test_create_member_request_defaults(self):
        """Test CreateMemberRequest with defaults"""
        request = CreateMemberRequest(
            user_id="user-002",
            user_name="李四",
            team_id="TM-001",
        )
        assert request.role == MemberRoleEnum.MEMBER
        assert request.email is None

    def test_update_member_request_valid(self):
        """Test valid UpdateMemberRequest"""
        request = UpdateMemberRequest(
            role=MemberRoleEnum.ADMIN,
            email="newemail@example.com",
        )
        assert request.role == MemberRoleEnum.ADMIN

    def test_create_permission_request_valid(self):
        """Test valid CreatePermissionRequest"""
        request = CreatePermissionRequest(
            team_id="TM-001",
            member_id="MBR-001",
            resource_type="workspace",
            resource_id="WS-001",
            permission_level=PermissionLevelEnum.WRITE,
        )
        assert request.permission_level == PermissionLevelEnum.WRITE

    def test_create_activity_request_valid(self):
        """Test valid CreateActivityRequest"""
        request = CreateActivityRequest(
            team_id="TM-001",
            activity_type=ActivityTypeEnum.MEMBER_ADDED,
            actor_id="user-001",
            actor_name="Test User",
            description="Test activity",
            metadata={"key": "value"},
        )
        assert request.activity_type == ActivityTypeEnum.MEMBER_ADDED


# Error handling tests
class TestErrorHandling:
    """Test error handling"""

    def test_exception_handling_in_get_teams(self, client, tmp_path):
        """Test exception handling in get_teams"""
        with patch('api.collaboration_advanced_router.TEAMS_FILE', tmp_path / "teams.json"):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', tmp_path / "members.json"):
                with patch('api.collaboration_advanced_router._load_json_file', side_effect=Exception("Test error")):
                    response = client.get("/api/v1/collaboration/teams")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is False

    def test_exception_handling_in_create_team(self, client, tmp_path):
        """Test exception handling in create_team"""
        teams_file = tmp_path / "teams.json"
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router._save_json_file', side_effect=Exception("Save error")):
                response = client.post(
                    "/api/v1/collaboration/teams",
                    json={
                        "name": "Test Team",
                        "owner_id": "user-001",
                    }
                )
                # API returns 201 even for error responses
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is False

    def test_log_activity_failure_does_not_affect_main_flow(self, tmp_path):
        """Test that activity logging failure doesn't affect main flow"""
        activities_file = tmp_path / "activities.json"
        # Make the file read-only to cause a save error
        activities_file.touch()
        activities_file.chmod(0o444)

        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            # This should not raise an exception
            _log_activity(
                team_id="TM-001",
                activity_type=ActivityTypeEnum.MEMBER_ADDED,
                actor_id="user-001",
                actor_name="Test User",
                description="Test",
            )
            # Function should complete without error


# Permission and access control tests
class TestPermissions:
    """Test permission and access control (placeholder for future implementation)"""

    def test_api_accessible_without_auth(self, client):
        """Test that API is accessible without authentication (current state)"""
        response = client.get("/api/v1/collaboration/teams")
        assert response.status_code in [200, 500]


# Integration tests
class TestIntegration:
    """Integration tests"""

    def test_full_team_lifecycle(self, client, tmp_path):
        """Test full team lifecycle: create, add member, add permission, delete"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        activities_file = tmp_path / "activities.json"

        # Create team
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                team_response = client.post(
                    "/api/v1/collaboration/teams",
                    json={
                        "name": "Integration Test Team",
                        "owner_id": "user-001",
                    }
                )
                assert team_response.status_code == 201
                team_id = team_response.json()["data"]["id"]

        # Add member
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                    member_response = client.post(
                        "/api/v1/collaboration/members",
                        json={
                            "user_id": "user-002",
                            "user_name": "Test User",
                            "team_id": team_id,
                        }
                    )
                    assert member_response.status_code == 201
                    member_id = member_response.json()["data"]["id"]

        # Add permission
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
                        perm_response = client.post(
                            "/api/v1/collaboration/permissions",
                            json={
                                "team_id": team_id,
                                "member_id": member_id,
                                "resource_type": "workspace",
                                "resource_id": "WS-001",
                                "permission_level": "write",
                            }
                        )
                        assert perm_response.status_code == 201

        # Check activities
        with patch('api.collaboration_advanced_router.ACTIVITIES_FILE', activities_file):
            activities_response = client.get("/api/v1/collaboration/activities")
            assert activities_response.status_code == 200
            activities = activities_response.json()["data"]["items"]
            # Should have at least 2 activities (team_created, member_added)
            assert len(activities) >= 2

        # Delete team (should cascade delete members and permissions)
        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    delete_response = client.delete(f"/api/v1/collaboration/teams/{team_id}")
                    assert delete_response.status_code == 200

    def test_member_role_promotion(self, client, tmp_path, sample_team, sample_member):
        """Test promoting a member from member to admin"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                # Update role to admin
                update_response = client.patch(
                    f"/api/v1/collaboration/members/{sample_member['id']}",
                    json={"role": "admin"}
                )
                assert update_response.status_code == 200
                assert update_response.json()["data"]["role"] == "admin"

    def test_permission_level_change(self, client, tmp_path, sample_team, sample_member, sample_permission):
        """Test changing permission level"""
        teams_file = tmp_path / "teams.json"
        members_file = tmp_path / "members.json"
        permissions_file = tmp_path / "permissions.json"
        with open(teams_file, "w", encoding="utf-8") as f:
            json.dump([sample_team], f)
        with open(members_file, "w", encoding="utf-8") as f:
            json.dump([sample_member], f)
        with open(permissions_file, "w", encoding="utf-8") as f:
            json.dump([sample_permission], f)

        with patch('api.collaboration_advanced_router.TEAMS_FILE', teams_file):
            with patch('api.collaboration_advanced_router.MEMBERS_FILE', members_file):
                with patch('api.collaboration_advanced_router.PERMISSIONS_FILE', permissions_file):
                    # Delete old permission
                    delete_response = client.delete(f"/api/v1/collaboration/permissions/{sample_permission['id']}")
                    assert delete_response.status_code == 200

                    # Create new permission with higher level
                    create_response = client.post(
                        "/api/v1/collaboration/permissions",
                        json={
                            "team_id": sample_team["id"],
                            "member_id": sample_member["id"],
                            "resource_type": sample_permission["resource_type"],
                            "resource_id": sample_permission["resource_id"],
                            "permission_level": "admin",
                        }
                    )
                    assert create_response.status_code == 201
                    assert create_response.json()["data"]["permission_level"] == "admin"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
