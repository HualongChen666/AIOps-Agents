# -*- coding: utf-8 -*-
"""Smoke tests for Group 5 integration and messaging addons."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from extensions.addons.integrations.kafka_event_service.service import Service as KafkaService
from extensions.addons.integrations.message_queue_service.service import (
    Service as MessageQueueService,
)
from extensions.addons.integrations.github_repository_service.service import (
    Service as GitHubService,
)
from extensions.addons.integrations.elk_stack_service.service import Service as ElkService


@pytest.fixture
def mock_requests():
    fake_response = MagicMock(
        status_code=200,
        json=lambda: {"ok": True},
        text='{"ok": true}',
    )
    with patch("requests.request", return_value=fake_response) as mocked:
        yield mocked


@pytest.fixture
def mock_subprocess():
    fake_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=fake_result) as mocked:
        yield mocked


def test_kafka_event_service_produces(mock_subprocess, monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    result = KafkaService.execute_operation(
        "implement_kafka_producer",
        {
            "topic": "events",
            "message": {"hello": "world"},
            "bus": "kafka",
            "dry_run": False,
        },
    )
    assert result["success"] is True
    assert result["status"] == "produced"
    mock_subprocess.assert_called_once()
    assert mock_subprocess.call_args[0][0][0] == "kafka-console-producer.sh"


def test_message_queue_service_publishes(mock_subprocess, monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    result = MessageQueueService.execute_operation(
        "implement_message_producer",
        {
            "queue": "tasks",
            "message": "hello",
            "dry_run": False,
        },
    )
    assert result["success"] is True
    assert result["status"] == "published"
    mock_subprocess.assert_called_once()
    assert mock_subprocess.call_args[0][0][0] == "rabbitmqadmin"


def test_github_repository_service_requests(mock_requests, monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    result = GitHubService.execute_operation(
        "configure_github_releases",
        {
            "owner": "octocat",
            "repo": "Hello-World",
            "endpoint": "releases",
            "dry_run": False,
        },
    )
    assert result["success"] is True
    assert result["status"] == 200
    mock_requests.assert_called_once()
    args = mock_requests.call_args[0]
    assert args[0] == "GET"
    assert "octocat/Hello-World/releases" in args[1]


def test_elk_stack_service_webhook(mock_requests, monkeypatch):
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    result = ElkService.execute_operation(
        "search_query",
        {
            "url": "https://example.com/webhook",
            "payload": {"query": {"match_all": {}}},
            "method": "POST",
            "dry_run": False,
        },
    )
    assert result["success"] is True
    assert result["status"] == 200
    mock_requests.assert_called_once()
    args = mock_requests.call_args[0]
    assert args[0] == "POST"
    assert args[1] == "https://example.com/webhook"
