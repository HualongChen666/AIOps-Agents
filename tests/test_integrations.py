# -*- coding: utf-8 -*-
"""
Integration Tests for L7 Layer - ITSM and Collaboration Integrations
Tests for ServiceNow, Jira, Slack, and Teams integrations
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from core.integration.l7.itSM_integration import (
    ITSMIntegration,
    get_itsm_integration,
    init_itsm_integration
)
from core.integration.l7.collaboration_integration import (
    CollaborationIntegration,
    get_collaboration_integration,
    init_collaboration_integration
)


def create_mock_response(data):
    """Helper to create mock response"""
    mock_response = MagicMock()
    mock_response.json.return_value = data
    mock_response.raise_for_status = MagicMock()
    return mock_response


def create_mock_client(response):
    """Helper to create mock async client"""
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.post = AsyncMock(return_value=response)
    mock_client_instance.get = AsyncMock(return_value=response)
    mock_client_instance.patch = AsyncMock(return_value=response)
    mock_client_instance.put = AsyncMock(return_value=response)
    return mock_client_instance


class TestServiceNowIntegration:
    """Test ServiceNow integration functionality"""

    @pytest.fixture
    def servicenow_config(self):
        """ServiceNow configuration for testing"""
        return {
            "servicenow": {
                "enabled": True,
                "instance": "testinstance",
                "username": "testuser",
                "password": "testpass",
            }
        }

    @pytest.fixture
    def integration(self, servicenow_config):
        """Create ITSM integration instance"""
        return ITSMIntegration(servicenow_config)

    def test_initialization(self, integration):
        """Test ServiceNow integration initialization"""
        assert integration.servicenow_enabled is True
        assert integration.servicenow_instance == "testinstance"
        assert integration._is_initialized is True

    @pytest.mark.asyncio
    async def test_create_servicenow_incident(self, integration):
        """Test creating a ServiceNow incident"""
        mock_response = create_mock_response({
            "result": {
                "number": "INC001",
                "state": "New",
                "sys_created_on": "2026-08-31T10:00:00"
            }
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.create_servicenow_incident(
                title="Test Incident",
                description="Test Description",
                severity="high",
                priority=1
            )

            assert result["number"] == "INC001"
            assert result["title"] == "Test Incident"
            assert result["severity"] == "high"
            assert result["priority"] == 1
            assert result["status"] == "New"

    @pytest.mark.asyncio
    async def test_get_servicenow_incident(self, integration):
        """Test getting a ServiceNow incident"""
        mock_response = create_mock_response({
            "result": [
                {
                    "number": "INC001",
                    "short_description": "Test Incident",
                    "description": "Test Description",
                    "state": "In Progress",
                    "priority": "1",
                    "urgency": "1",
                    "assignment_group": "Network",
                    "assigned_to": "admin",
                    "sys_created_on": "2026-08-31T10:00:00",
                    "sys_updated_on": "2026-08-31T11:00:00"
                }
            ]
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.get_servicenow_incident("INC001")

            assert result["number"] == "INC001"
            assert result["title"] == "Test Incident"
            assert result["status"] == "In Progress"
            assert result["priority"] == "1"
            assert result["assigned_to"] == "admin"

    @pytest.mark.asyncio
    async def test_update_servicenow_incident(self, integration):
        """Test updating a ServiceNow incident"""
        lookup_response = create_mock_response({
            "result": [{"sys_id": "sys123", "number": "INC001"}]
        })
        update_response = create_mock_response({
            "result": {"sys_updated_on": "2026-08-31T12:00:00"}
        })
        
        # Create a mock client that returns different responses for different calls
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get = AsyncMock(return_value=lookup_response)
        mock_client_instance.patch = AsyncMock(return_value=update_response)
        
        with patch.object(httpx, "AsyncClient", return_value=mock_client_instance):
            result = await integration.update_servicenow_incident(
                "INC001", {"state": "Resolved"}
            )

            assert result["number"] == "INC001"
            assert result["updated"] is True
            assert result["updates"]["state"] == "Resolved"

    @pytest.mark.asyncio
    async def test_add_servicenow_comment(self, integration):
        """Test adding a comment to a ServiceNow incident"""
        lookup_response = create_mock_response({
            "result": [{"sys_id": "sys123", "number": "INC001"}]
        })
        comment_response = create_mock_response({
            "result": {"sys_updated_on": "2026-08-31T12:00:00"}
        })
        
        # Create a mock client that returns different responses for different calls
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get = AsyncMock(return_value=lookup_response)
        mock_client_instance.post = AsyncMock(return_value=comment_response)
        
        with patch.object(httpx, "AsyncClient", return_value=mock_client_instance):
            result = await integration.add_servicenow_comment(
                "INC001", "Test comment"
            )

            assert result["number"] == "INC001"
            assert result["comment_added"] is True
            assert result["comment"] == "Test comment"

    @pytest.mark.asyncio
    async def test_close_servicenow_incident(self, integration):
        """Test closing a ServiceNow incident"""
        lookup_response = create_mock_response({
            "result": [{"sys_id": "sys123", "number": "INC001"}]
        })
        update_response = create_mock_response({
            "result": {"sys_updated_on": "2026-08-31T12:00:00"}
        })
        
        # Create a mock client that returns different responses for different calls
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get = AsyncMock(return_value=lookup_response)
        mock_client_instance.patch = AsyncMock(return_value=update_response)
        
        with patch.object(httpx, "AsyncClient", return_value=mock_client_instance):
            result = await integration.close_servicenow_incident(
                "INC001", "resolved", "Issue resolved"
            )

            assert result["number"] == "INC001"
            assert result["updated"] is True

    def test_servicenow_disabled(self):
        """Test ServiceNow integration when disabled"""
        config = {"servicenow": {"enabled": False}}
        integration = ITSMIntegration(config)
        
        assert integration.servicenow_enabled is False

    @pytest.mark.asyncio
    async def test_servicenow_disabled_error(self):
        """Test ServiceNow operations when disabled"""
        config = {"servicenow": {"enabled": False}}
        integration = ITSMIntegration(config)
        
        result = await integration.create_servicenow_incident("Test", "Test")
        assert "error" in result
        assert result["error"] == "ServiceNow not enabled"


class TestJiraIntegration:
    """Test Jira integration functionality"""

    @pytest.fixture
    def jira_config(self):
        """Jira configuration for testing"""
        return {
            "jira": {
                "enabled": True,
                "url": "https://test.atlassian.net",
                "username": "testuser",
                "api_token": "testtoken",
                "default_project": "TEST"
            }
        }

    @pytest.fixture
    def integration(self, jira_config):
        """Create ITSM integration instance"""
        return ITSMIntegration(jira_config)

    def test_initialization(self, integration):
        """Test Jira integration initialization"""
        assert integration.jira_enabled is True
        assert integration.jira_url == "https://test.atlassian.net"
        assert integration._is_initialized is True

    @pytest.mark.asyncio
    async def test_create_jira_issue(self, integration):
        """Test creating a Jira issue"""
        mock_response = create_mock_response({
            "key": "TEST-123",
            "fields": {
                "created": "2026-08-31T10:00:00.000+0000"
            }
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.create_jira_issue(
                summary="Test Issue",
                description="Test Description",
                issue_type="Bug",
                priority="High"
            )

            assert result["key"] == "TEST-123"
            assert result["summary"] == "Test Issue"
            assert result["issue_type"] == "Bug"
            assert result["priority"] == "High"
            assert result["project_key"] == "TEST"

    @pytest.mark.asyncio
    async def test_get_jira_issue(self, integration):
        """Test getting a Jira issue"""
        mock_response = create_mock_response({
            "key": "TEST-123",
            "fields": {
                "summary": "Test Issue",
                "description": "Test Description",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "assignee": {"displayName": "Test User"},
                "created": "2026-08-31T10:00:00.000+0000",
                "updated": "2026-08-31T11:00:00.000+0000"
            }
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.get_jira_issue("TEST-123")

            assert result["key"] == "TEST-123"
            assert result["summary"] == "Test Issue"
            assert result["status"] == "In Progress"
            assert result["priority"] == "High"
            assert result["assignee"] == "Test User"

    @pytest.mark.asyncio
    async def test_update_jira_issue(self, integration):
        """Test updating a Jira issue"""
        mock_response = create_mock_response({})
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.update_jira_issue(
                "TEST-123", {"summary": "Updated Summary"}
            )

            assert result["key"] == "TEST-123"
            assert result["updated"] is True
            assert result["updates"]["summary"] == "Updated Summary"

    @pytest.mark.asyncio
    async def test_add_jira_comment(self, integration):
        """Test adding a comment to a Jira issue"""
        mock_response = create_mock_response({"id": "comment123"})
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.add_jira_comment("TEST-123", "Test comment")

            assert result["key"] == "TEST-123"
            assert result["comment_added"] is True
            assert result["comment_id"] == "comment123"

    @pytest.mark.asyncio
    async def test_transition_jira_issue(self, integration):
        """Test transitioning a Jira issue"""
        transitions_response = create_mock_response({
            "transitions": [
                {"id": "transition1", "name": "In Progress"}
            ]
        })
        transition_response = create_mock_response({})
        
        # Create a mock client that returns different responses for different calls
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get = AsyncMock(return_value=transitions_response)
        mock_client_instance.post = AsyncMock(return_value=transition_response)
        
        with patch.object(httpx, "AsyncClient", return_value=mock_client_instance):
            result = await integration.transition_jira_issue(
                "TEST-123", "In Progress", "Moving to In Progress"
            )

            assert result["key"] == "TEST-123"
            assert result["transitioned"] is True
            assert result["transition"] == "In Progress"

    def test_jira_disabled(self):
        """Test Jira integration when disabled"""
        config = {"jira": {"enabled": False}}
        integration = ITSMIntegration(config)
        
        assert integration.jira_enabled is False

    @pytest.mark.asyncio
    async def test_jira_disabled_error(self):
        """Test Jira operations when disabled"""
        config = {"jira": {"enabled": False}}
        integration = ITSMIntegration(config)
        
        result = await integration.create_jira_issue("Test", "Test")
        assert "error" in result
        assert result["error"] == "Jira not enabled"


class TestSlackIntegration:
    """Test Slack integration functionality"""

    @pytest.fixture
    def slack_config(self):
        """Slack configuration for testing"""
        return {
            "slack": {
                "enabled": True,
                "bot_token": "xoxb-test-token",
                "channel": "#test-channel",
                "api_url": "https://slack.com/api/chat.postMessage"
            }
        }

    @pytest.fixture
    def integration(self, slack_config):
        """Create collaboration integration instance"""
        return CollaborationIntegration(slack_config)

    def test_initialization(self, integration):
        """Test Slack integration initialization"""
        assert integration.slack_enabled is True
        assert integration.slack_channel == "#test-channel"
        assert integration._is_initialized is True

    @pytest.mark.asyncio
    async def test_send_slack_notification(self, integration):
        """Test sending a Slack notification"""
        mock_response = create_mock_response({
            "ok": True,
            "ts": "1234567890.123456"
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.send_slack_notification("Test message")

            assert result["success"] is True
            assert result["channel"] == "#test-channel"
            assert result["ts"] == "1234567890.123456"

    @pytest.mark.asyncio
    async def test_send_slack_approval_request(self, integration):
        """Test sending a Slack approval request"""
        mock_response = create_mock_response({
            "ok": True,
            "ts": "1234567890.123456"
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            actions = [
                {"text": "Approve", "value": "approve"},
                {"text": "Reject", "value": "reject"}
            ]

            result = await integration.send_slack_approval_request(
                "Approval Request",
                "Please approve this request",
                actions
            )

            assert result["success"] is True
            assert result["channel"] == "#test-channel"

    @pytest.mark.asyncio
    async def test_get_slack_channel_info(self, integration):
        """Test getting Slack channel information"""
        mock_response = create_mock_response({
            "ok": True,
            "channel": {
                "id": "C123456",
                "name": "test-channel",
                "is_channel": True,
                "is_private": False,
                "num_members": 10,
                "topic": {"value": "Test topic"}
            }
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.get_slack_channel_info()

            assert result["id"] == "C123456"
            assert result["name"] == "test-channel"
            assert result["members"] == 10
            assert result["topic"] == "Test topic"

    @pytest.mark.asyncio
    async def test_get_slack_user_info(self, integration):
        """Test getting Slack user information"""
        mock_response = create_mock_response({
            "ok": True,
            "user": {
                "id": "U123456",
                "real_name": "Test User",
                "display_name": "Test User",
                "profile": {"email": "test@example.com"},
                "is_admin": False,
                "is_owner": False
            }
        })
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.get_slack_user_info("U123456")

            assert result["id"] == "U123456"
            assert result["name"] == "Test User"
            assert result["email"] == "test@example.com"
            assert result["is_admin"] is False

    def test_slack_disabled(self):
        """Test Slack integration when disabled"""
        config = {"slack": {"enabled": False}}
        integration = CollaborationIntegration(config)
        
        assert integration.slack_enabled is False

    @pytest.mark.asyncio
    async def test_slack_disabled_error(self):
        """Test Slack operations when disabled"""
        config = {"slack": {"enabled": False}}
        integration = CollaborationIntegration(config)
        
        result = await integration.send_slack_notification("Test")
        assert "error" in result
        assert result["error"] == "Slack not enabled"


class TestTeamsIntegration:
    """Test Teams integration functionality"""

    @pytest.fixture
    def teams_config(self):
        """Teams configuration for testing"""
        return {
            "teams": {
                "enabled": True,
                "webhook": "https://outlook.office.com/webhook/test",
                "channel": "test-channel"
            }
        }

    @pytest.fixture
    def integration(self, teams_config):
        """Create collaboration integration instance"""
        return CollaborationIntegration(teams_config)

    def test_initialization(self, integration):
        """Test Teams integration initialization"""
        assert integration.teams_enabled is True
        assert integration.teams_webhook == "https://outlook.office.com/webhook/test"
        assert integration._is_initialized is True

    @pytest.mark.asyncio
    async def test_send_teams_notification(self, integration):
        """Test sending a Teams notification"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            result = await integration.send_teams_notification(
                "Test message",
                title="Test Title",
                color="0078D4"
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_teams_approval_card(self, integration):
        """Test sending a Teams approval card"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(httpx, "AsyncClient", return_value=create_mock_client(mock_response)):
            actions = [
                {"text": "Approve", "value": "approve"},
                {"text": "Reject", "value": "reject"}
            ]

            result = await integration.send_teams_approval_card(
                "Approval Request",
                "Please approve this request",
                actions
            )

            assert result["success"] is True

    def test_teams_disabled(self):
        """Test Teams integration when disabled"""
        config = {"teams": {"enabled": False}}
        integration = CollaborationIntegration(config)
        
        assert integration.teams_enabled is False

    @pytest.mark.asyncio
    async def test_teams_disabled_error(self):
        """Test Teams operations when disabled"""
        config = {"teams": {"enabled": False}}
        integration = CollaborationIntegration(config)
        
        result = await integration.send_teams_notification("Test")
        assert "error" in result
        assert result["error"] == "Teams not enabled"


class TestGlobalInstances:
    """Test global singleton instances"""

    def test_get_itsm_integration_none(self):
        """Test getting ITSM integration when not initialized"""
        result = get_itsm_integration()
        assert result is None

    def test_init_itsm_integration(self):
        """Test initializing ITSM integration"""
        config = {
            "servicenow": {"enabled": True, "instance": "test"}
        }
        result = init_itsm_integration(config)
        assert result is not None
        assert result.servicenow_enabled is True

    def test_get_itsm_integration_after_init(self):
        """Test getting ITSM integration after initialization"""
        config = {
            "servicenow": {"enabled": True, "instance": "test"}
        }
        init_itsm_integration(config)
        result = get_itsm_integration()
        assert result is not None
        assert result.servicenow_enabled is True

    def test_get_collaboration_integration_none(self):
        """Test getting collaboration integration when not initialized"""
        result = get_collaboration_integration()
        assert result is None

    def test_init_collaboration_integration(self):
        """Test initializing collaboration integration"""
        config = {
            "slack": {"enabled": True, "bot_token": "test"}
        }
        result = init_collaboration_integration(config)
        assert result is not None
        assert result.slack_enabled is True

    def test_get_collaboration_integration_after_init(self):
        """Test getting collaboration integration after initialization"""
        config = {
            "slack": {"enabled": True, "bot_token": "test"}
        }
        init_collaboration_integration(config)
        result = get_collaboration_integration()
        assert result is not None
        assert result.slack_enabled is True


class TestIntegrationStatus:
    """Test integration status reporting"""

    @pytest.fixture
    def full_config(self):
        """Full configuration for testing"""
        return {
            "servicenow": {
                "enabled": True,
                "instance": "testinstance",
                "username": "testuser",
                "password": "testpass",
            },
            "jira": {
                "enabled": True,
                "url": "https://test.atlassian.net",
                "username": "testuser",
                "api_token": "testtoken",
                "default_project": "TEST"
            },
            "slack": {
                "enabled": True,
                "bot_token": "xoxb-test-token",
                "channel": "#test-channel",
                "api_url": "https://slack.com/api/chat.postMessage"
            },
            "teams": {
                "enabled": True,
                "webhook": "https://outlook.office.com/webhook/test",
                "channel": "test-channel"
            }
        }

    def test_itsm_integration_status(self, full_config):
        """Test ITSM integration status"""
        integration = ITSMIntegration(full_config)
        status = integration.get_status()
        
        assert status["initialized"] is True
        assert status["servicenow"]["enabled"] is True
        assert status["servicenow"]["instance"] == "testinstance"
        assert status["jira"]["enabled"] is True
        assert status["jira"]["url"] == "https://test.atlassian.net"

    def test_collaboration_integration_status(self, full_config):
        """Test collaboration integration status"""
        integration = CollaborationIntegration(full_config)
        status = integration.get_status()
        
        assert status["initialized"] is True
        assert status["slack"]["enabled"] is True
        assert status["slack"]["channel"] == "#test-channel"
        assert status["teams"]["enabled"] is True
        assert status["teams"]["channel"] == "test-channel"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])