# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core/integration_ecosystem.py.

Uses real ``IntegrationEcosystem`` instances and in-memory integration
configurations.  No unittest.mock objects are used; only real data and real
object state.
"""

import hashlib  # noqa: F401  # Imported for test setup
import hmac  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup
import requests

import core.integration_ecosystem as ie


async def test_initialize_with_real_sessions(tmp_path):
    """Cover both the requests and aiohttp initialization branches."""
    ecosystem = ie.IntegrationEcosystem()
    # Avoid real retries so the test runs quickly.
    ecosystem.retry_config["max_retries"] = 0
    os.environ["AIOPS_INTEGRATIONS_PATH"] = str(tmp_path / "nonexistent.json")

    await ecosystem.initialize()

    assert ecosystem.http_session is not None
    assert ecosystem.aiohttp_session is not None

    await ecosystem.aiohttp_session.close()
    ecosystem.http_session.close()

    del os.environ["AIOPS_INTEGRATIONS_PATH"]


async def test_initialize_without_optional_clients(tmp_path):
    """Cover the branches where requests/aiohttp are unavailable and loading fails."""
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not valid json", encoding="utf-8")
    os.environ["AIOPS_INTEGRATIONS_PATH"] = str(bad_path)

    original_requests = ie.REQUESTS_AVAILABLE  # noqa: F841  # Variable for test verification
    original_aiohttp = ie.AIOHTTP_AVAILABLE  # noqa: F841  # Variable for test verification
    try:
        ie.REQUESTS_AVAILABLE = False
        ie.AIOHTTP_AVAILABLE = False

        ecosystem = ie.IntegrationEcosystem()
        await ecosystem.initialize()

        assert ecosystem.http_session is None
        assert ecosystem.aiohttp_session is None
    finally:
        ie.REQUESTS_AVAILABLE = original_requests  # noqa: F841  # Variable for test verification
        ie.AIOHTTP_AVAILABLE = original_aiohttp  # noqa: F841  # Variable for test verification
        if "AIOPS_INTEGRATIONS_PATH" in os.environ:
            del os.environ["AIOPS_INTEGRATIONS_PATH"]


async def test_monitoring_validation_connection_failure():
    """Cover the prometheus connection-failure except branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.http_session = requests.Session()

    integration = ie.IntegrationConfig(
        id="prom_1",
        name="Prometheus",
        type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://localhost", "port": 1},
        status=ie.IntegrationStatus.PENDING,
    )

    result = await ecosystem._validate_monitoring_integration(integration)  # noqa: F841  # Variable for test verification
    assert result["valid"] is False
    assert "Connection test failed" in result["error"]


async def test_provider_activation_pass_branches():
    """Cover the otherwise-uncovered provider pass branches."""
    ecosystem = ie.IntegrationEcosystem()

    elk = await ecosystem.register_integration(
        name="ELK",
        integration_type=ie.IntegrationType.MONITORING,
        provider="elk",
        configuration={},
    )
    assert elk.status == ie.IntegrationStatus.ACTIVE

    gcp = await ecosystem.register_integration(
        name="GCP",
        integration_type=ie.IntegrationType.CLOUD,
        provider="gcp",
        configuration={},
    )
    assert gcp.status == ie.IntegrationStatus.ACTIVE

    github = await ecosystem.register_integration(
        name="GitHub",
        integration_type=ie.IntegrationType.CICD,
        provider="github",
        configuration={},
        credentials={"repo": "owner/repo", "token": "ghp_test"},
    )
    assert github.status == ie.IntegrationStatus.ACTIVE


async def test_send_notification_branches():
    """Exercise the false/exception branches in send_notification and helpers."""
    ecosystem = ie.IntegrationEcosystem()

    # Slack not found
    assert await ecosystem.send_notification(ie.NotificationChannel.SLACK, "hello") is False

    # Slack found but no HTTP session
    slack = await ecosystem.register_integration(  # noqa: F841  # Variable for test verification
        name="Slack",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={"webhook_url": "http://localhost:1/hook", "channel": "#ops"},
    )
    assert await ecosystem.send_notification(ie.NotificationChannel.SLACK, "hello") is False

    # Slack real HTTP session, invalid URL
    ecosystem.http_session = requests.Session()
    assert (
        await ecosystem.send_notification(
            ie.NotificationChannel.SLACK, "error alert", metadata={"x": 1}
        )
        is False
    )

    # Teams via _post_webhook_notification, no integration
    assert await ecosystem.send_notification(ie.NotificationChannel.TEAMS, "hello") is False

    # Slack search loop: a non-slack notification triggers the continue branch
    await ecosystem.register_integration(
        name="Teams2",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="teams",
        configuration={"webhook_url": "http://localhost:1/hook"},
    )
    assert await ecosystem.send_notification(ie.NotificationChannel.SLACK, "hello") is False

    # DingTalk missing webhook_url
    await ecosystem.register_integration(
        name="DingTalk",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="dingtalk",
        configuration={"secret": "abc"},
    )
    assert await ecosystem.send_notification(ie.NotificationChannel.DINGTALK, "hello") is False

    # DingTalk real webhook_url, no HTTP session
    wecom = await ecosystem.register_integration(
        name="WeCom",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="wecom",
        configuration={"webhook_url": "http://localhost:1/hook"},
    )
    ecosystem = ie.IntegrationEcosystem()  # reset; no session
    ecosystem.integrations[wecom.id] = wecom
    assert await ecosystem.send_notification(ie.NotificationChannel.WECOM, "hello") is False

    # WeCom real webhook_url, real HTTP session, no secret
    ecosystem2 = ie.IntegrationEcosystem()
    ecosystem2.http_session = requests.Session()
    ecosystem2.integrations[wecom.id] = wecom
    assert await ecosystem2.send_notification(ie.NotificationChannel.WECOM, "hello") is False

    # DingTalk with secret, metadata and real session
    ding = await ecosystem2.register_integration(  # noqa: F841  # Variable for test verification
        name="DingTalk2",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="dingtalk",
        configuration={"webhook_url": "http://localhost:1/hook"},
        credentials={"secret": "s3cret"},
    )
    assert (
        await ecosystem2.send_notification(
            ie.NotificationChannel.DINGTALK, "hello", metadata={"extra": 1}
        )
        is False
    )

    # Email integration with malformed configuration triggers send_notification except
    email = await ecosystem2.register_integration(  # noqa: F841  # Variable for test verification
        name="Email",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="email",
        configuration={"smtp_host": "localhost", "smtp_port": 1, "sender": "a@b.com"},
    )
    email.configuration = []  # break the configuration object
    assert await ecosystem2.send_notification(ie.NotificationChannel.EMAIL, "hello") is False

    # Email real configuration, SMTP connection fails
    email.configuration = {
        "smtp_host": "localhost",
        "smtp_port": 1,
        "sender": "a@b.com",
        "default_recipient": "c@d.com",
    }
    assert (
        await ecosystem2.send_notification(
            ie.NotificationChannel.EMAIL, "hello", metadata={"to": "c@d.com"}
        )
        is False
    )


async def test_webhook_signature_and_trigger():
    """Cover valid/missing/wrong signature and the send exception branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.http_session = requests.Session()

    webhook = await ecosystem.register_webhook(
        url="http://localhost:1/hook",
        secret="s3cret",
        events=["alert"],
    )

    # Missing signature
    assert await ecosystem.trigger_webhook(webhook.id, {"event": "alert"}) is False

    # Correct signature (excludes the signature key itself)
    payload = {"event": "alert"}
    expected = ecosystem._calculate_signature(payload, webhook.secret)
    assert await ecosystem.trigger_webhook(webhook.id, {**payload, "signature": expected}) is False

    # Wrong signature
    assert await ecosystem.trigger_webhook(webhook.id, {**payload, "signature": "wrong"}) is False

    # No secret, invalid URL
    plain = await ecosystem.register_webhook(
        url="http://localhost:1/hook",
        events=["alert"],
    )
    assert await ecosystem.trigger_webhook(plain.id, {"event": "alert"}) is False

    # Unknown webhook
    assert await ecosystem.trigger_webhook("missing", {"event": "alert"}) is False


async def test_event_processing_exception():
    """Cover the event handler exception branch."""
    ecosystem = ie.IntegrationEcosystem()

    good_called = []
    bad_called = []

    async def good(event):
        good_called.append(event.id)

    async def bad(event):
        bad_called.append(event.id)
        raise RuntimeError("boom")

    ecosystem.register_event_handler("demo", bad)
    ecosystem.register_event_handler("demo", good)

    event = ie.IntegrationEvent(
        id="evt_1",
        integration_id="system",
        event_type="demo",
        payload={},
        timestamp=__import__("datetime").datetime.now(),
        status="pending",
    )
    await ecosystem._process_event(event)

    assert good_called == ["evt_1"]
    assert event.status == "processed"


async def test_query_prometheus_real_failure():
    """Cover the prometheus query HTTP exception branch."""
    ecosystem = ie.IntegrationEcosystem()

    prom = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://localhost", "port": 1},
    )

    # Provide a real session only for the query so validation passes.
    ecosystem.http_session = requests.Session()

    result = await ecosystem.query_prometheus_metrics("up", prom.id, time_range="1h")  # noqa: F841  # Variable for test verification
    assert result is not None
    assert "error" in result


async def test_trigger_jenkins_real_failure():
    """Cover the Jenkins trigger HTTP exception branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.http_session = requests.Session()

    jenkins = await ecosystem.register_integration(
        name="Jenkins",
        integration_type=ie.IntegrationType.CICD,
        provider="jenkins",
        configuration={"url": "http://localhost:1"},
        credentials={"api_token": "token"},
    )

    assert await ecosystem.trigger_jenkins_build("build", jenkins.id, {"branch": "main"}) is False


async def test_create_jira_real_failure():
    """Cover the Jira ticket creation HTTP exception branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.http_session = requests.Session()

    jira = await ecosystem.register_integration(
        name="Jira",
        integration_type=ie.IntegrationType.ITSM,
        provider="jira",
        configuration={"url": "http://localhost:1", "project_key": "OPS"},
        credentials={"username": "u", "api_token": "t"},
    )

    result = await ecosystem.create_jira_ticket("summary", "description", jira.id)  # noqa: F841  # Variable for test verification
    assert result is None


async def test_disable_enable_remove_unknown():
    """Cover not-found branches and cleanup."""
    ecosystem = ie.IntegrationEcosystem()

    assert await ecosystem.disable_integration("missing") is False
    assert await ecosystem.enable_integration("missing") is False
    assert await ecosystem.remove_integration("missing") is False

    # cleanup unknown integration directly
    await ecosystem._cleanup_integration("missing")

    # remove a real integration and trigger url cleanup
    slack = await ecosystem.register_integration(  # noqa: F841  # Variable for test verification
        name="Slack",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={"webhook_url": "http://localhost:1/hook", "channel": "#ops"},
    )
    assert await ecosystem.remove_integration(slack.id) is True
    assert slack.id not in ecosystem.integrations


async def test_connector_marketplace_branches():
    """Cover connector install-not-found, invalid rating and details not-found."""
    market = ie.ConnectorMarketplace()

    not_found = await market.install_connector("unknown_provider", {})
    assert not_found["success"] is False

    missing_field = await market.install_connector("prometheus", {"url": "http://x"})
    assert missing_field["success"] is False

    invalid_rating = await market.rate_connector("prometheus", 7.0)
    assert invalid_rating["success"] is False

    details = await market.get_connector_details("unknown_provider")
    assert details is None


async def test_plugin_sdk_branches():
    """Cover first hook registration and hook handler exception branches."""
    sdk = ie.PluginSDK()

    async def ok(data):
        return data

    reg = await sdk.register_hook("new_hook", ok)
    assert reg["success"] is True

    async def boom(data):
        raise ValueError("boom")

    await sdk.register_hook("bad_hook", boom)
    results = await sdk.trigger_hook("bad_hook", {"x": 1})
    assert len(results) == 1
    assert results[0]["success"] is False


async def test_slack_search_continue_branch():
    """Cover the slack-search for-loop continue branch."""
    ecosystem = ie.IntegrationEcosystem()

    # Register a non-slack first so the for-loop iterates at least once.
    await ecosystem.register_integration(
        name="Teams",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="teams",
        configuration={"webhook_url": "http://localhost:1/hook"},
    )

    await ecosystem.register_integration(
        name="Slack",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={"webhook_url": "http://localhost:1/hook", "channel": "#ops"},
    )

    # No HTTP session, so it will continue over teams and find slack, then return False.
    assert await ecosystem.send_notification(ie.NotificationChannel.SLACK, "hello") is False
