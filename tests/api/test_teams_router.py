# -*- coding: utf-8 -*-
"""Teams Router Tests"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].get_current_active_user = lambda: {
    "username": "testuser",
    "role": "user",
}
sys.modules["core.teams_adapter"] = MagicMock()
sys.modules["core.chat_command_handler"] = MagicMock()

from api.teams_router import router  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestTeamsRouter:
    def test_send_message_success(self, client):
        with patch("api.teams_router.post_message", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"message_id": "123"}
            response = client.post(
                "/api/teams/message",
                json={"text": "Test message", "title": "Alert", "channel": "General"},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_send_message_unavailable(self, client):
        with patch("api.teams_router.post_message", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("Teams webhook not configured")
            response = client.post("/api/teams/message", json={"text": "Test"})
            assert response.status_code == 503

    def test_send_interactive_success(self, client):
        with patch(
            "api.teams_router.post_interactive_message", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = {"message_id": "456"}
            response = client.post(
                "/api/teams/interactive",
                json={
                    "title": "Ack",
                    "description": "High CPU",
                    "actions": [
                        {"title": "Ack", "type": "Action.Submit", "action": "ack", "value": "ok"}
                    ],
                },
            )
            assert response.status_code == 200

    def test_events_callback_approve(self, client):
        with patch("api.teams_router.handle_instruction") as mock_handle:
            response = client.post(
                "/api/teams/events",
                json={"value": {"action": "approve", "value": "server-01"}},
            )
            assert response.status_code == 200
            assert response.json()["action"]["type"] == "approve"
            mock_handle.assert_not_called()

    def test_events_callback_text(self, client):
        with patch("api.teams_router.handle_instruction") as mock_handle:
            mock_handle.return_value = {"command": "ack", "target": "server-01"}
            response = client.post(
                "/api/teams/events",
                json={"text": "ack server-01", "from": "user1", "channel": "General"},
            )
            assert response.status_code == 200
            assert response.json()["action"]["command"] == "ack"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
