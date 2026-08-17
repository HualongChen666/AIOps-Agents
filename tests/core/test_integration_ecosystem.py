# -*- coding: utf-8 -*-
"""Tests for core/integration_ecosystem.py."""

import hashlib
import hmac
import json  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup

import core.integration_ecosystem as ie


@pytest.fixture
def no_http(monkeypatch):
    monkeypatch.setattr(ie, "REQUESTS_AVAILABLE", False)
    monkeypatch.setattr(ie, "AIOHTTP_AVAILABLE", False)


@pytest.fixture
def ecosystem(no_http):
    return ie.IntegrationEcosystem()


async def test_register_and_query_integrations(ecosystem):
    config = {"url": "http://prom", "port": 9090}
    integration = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration=config,
    )
    assert integration.provider == "prometheus"
    assert integration.id in ecosystem.integrations

    status = await ecosystem.get_integration_status(integration.id)
    assert status is not None

    all_integrations = await ecosystem.list_integrations()
    assert len(all_integrations) == 1

    filtered = await ecosystem.list_integrations(ie.IntegrationType.MONITORING)
    assert len(filtered) == 1


async def test_register_cloud_and_cicd_integrations(ecosystem):
    cloud = await ecosystem.register_integration(
        name="AWS",
        integration_type=ie.IntegrationType.CLOUD,
        provider="aws",
        configuration={},
        credentials={"access_key": "a", "secret_key": "s", "region": "us"},
    )
    assert cloud.type == ie.IntegrationType.CLOUD

    cicd = await ecosystem.register_integration(
        name="GitHub",
        integration_type=ie.IntegrationType.CICD,
        provider="github",
        configuration={},
        credentials={"repo": "r", "token": "t"},
    )
    assert cicd.type == ie.IntegrationType.CICD


async def test_register_notification_integration(ecosystem):
    slack = await ecosystem.register_integration(  # noqa: F841  # Variable for test verification
        name="Slack",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={"webhook_url": "http://hook", "channel": "#alerts"},
    )
    assert slack.provider == "slack"
    assert len(ecosystem.webhooks) == 1

    result = await ecosystem.send_notification(  # noqa: F841  # Variable for test verification
        ie.NotificationChannel.SLACK, "hello", metadata={"channel": "#alerts"}
    )
    assert result is False


async def test_webhook_signature_and_trigger(ecosystem):
    webhook = await ecosystem.register_webhook(
        url="http://example.com", secret="s3cret", events=["alert"]
    )
    payload = {"event": "alert"}
    raw = json.dumps(payload, sort_keys=True)
    expected = hmac.new("s3cret".encode(), raw.encode(), hashlib.sha256).hexdigest()

    result = await ecosystem.trigger_webhook(webhook.id, {**payload, "signature": expected})  # noqa: F841  # Variable for test verification
    assert result is False

    missing = await ecosystem.trigger_webhook(webhook.id, payload)
    assert missing is False

    unknown = await ecosystem.trigger_webhook("not-found", payload)
    assert unknown is False


async def test_publish_and_process_event(ecosystem):
    called = []

    async def handler(event):
        called.append(event.event_type)

    ecosystem.register_event_handler("test", handler)
    result = await ecosystem.publish_event("test", {"x": 1})  # noqa: F841  # Variable for test verification
    assert result is True
    assert len(ecosystem.event_queue) == 1

    event = ecosystem.event_queue[0]
    await ecosystem._process_event(event)
    assert called == ["test"]
    assert event.status == "processed"


async def test_query_and_trigger_methods(ecosystem):
    integration = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://prom", "port": 9090},
    )
    result = await ecosystem.query_prometheus_metrics("up", integration.id, time_range="1h")  # noqa: F841  # Variable for test verification
    assert result is None

    jenkins = await ecosystem.register_integration(
        name="Jenkins",
        integration_type=ie.IntegrationType.CICD,
        provider="jenkins",
        configuration={"url": "http://jenkins"},
    )
    assert await ecosystem.trigger_jenkins_build("job", jenkins.id) is False

    jira = await ecosystem.register_integration(
        name="Jira",
        integration_type=ie.IntegrationType.ITSM,
        provider="jira",
        configuration={"url": "http://jira", "project_key": "OPS"},
        credentials={"username": "u", "api_token": "t"},
    )
    assert await ecosystem.create_jira_ticket("sum", "desc", jira.id) is None


async def test_disable_enable_remove(ecosystem):
    integration = await ecosystem.register_integration(
        name="AWS",
        integration_type=ie.IntegrationType.CLOUD,
        provider="aws",
        configuration={},
        credentials={"access_key": "a", "secret_key": "s", "region": "us"},
    )
    assert await ecosystem.disable_integration(integration.id) is True
    assert ecosystem.integrations[integration.id].status == ie.IntegrationStatus.INACTIVE

    assert await ecosystem.enable_integration(integration.id) is True
    assert ecosystem.integrations[integration.id].status == ie.IntegrationStatus.ACTIVE

    assert await ecosystem.remove_integration(integration.id) is True
    assert integration.id not in ecosystem.integrations


async def test_integration_statistics(ecosystem):
    await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://prom", "port": 9090},
    )
    stats = await ecosystem.get_integration_statistics()
    assert stats["total_integrations"] == 1
    assert stats["by_type"]["monitoring"] == 1
    assert stats["total_webhooks"] == 0


def test_extended_integration_registry():
    registry = ie.ExtendedIntegrationRegistry()
    template = registry.get_integration_template("prometheus")
    assert template is not None
    assert template["name"] == "Prometheus"

    monitoring = registry.list_integrations_by_category("monitoring")
    assert any(t["name"] == "Prometheus" for t in monitoring)

    search = registry.search_integrations("Grafana")
    assert any("Grafana" in s["name"] for s in search)


async def test_connector_marketplace():
    market = ie.ConnectorMarketplace()
    connectors = await market.discover_connectors()
    assert connectors

    install = await market.install_connector("prometheus", {"url": "http://prom", "port": 9090})
    assert install["success"] is True

    details = await market.get_connector_details("prometheus")
    assert details is not None
    assert details["installed"] is True

    rating = await market.rate_connector("prometheus", 4.5)
    assert rating["success"] is True
    assert rating["average_rating"] == 4.5

    uninstall = await market.uninstall_connector("prometheus")
    assert uninstall["success"] is True


async def test_plugin_sdk():
    sdk = ie.PluginSDK()

    async def handler(data):
        return {"result": data}

    reg = await sdk.register_plugin(
        plugin_id="p1",
        plugin_name="Test Plugin",
        plugin_version="1.0.0",
        plugin_config={},
        plugin_handler=handler,
    )
    assert reg["success"] is True

    result = await sdk.execute_plugin("p1", {"x": 1})  # noqa: F841  # Variable for test verification
    assert result["success"] is True

    hooks = []

    async def hook(data):
        hooks.append(data)
        return "ok"

    await sdk.register_hook("on_event", hook)
    triggered = await sdk.trigger_hook("on_event", {"x": 1})
    assert triggered == [{"success": True, "result": "ok"}]

    plugins = sdk.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["name"] == "Test Plugin"

    template = sdk.get_plugin_template()
    assert "plugin_handler" in template

    unreg = await sdk.unregister_plugin("p1")
    assert unreg["success"] is True
