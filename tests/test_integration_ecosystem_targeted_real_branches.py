# -*- coding: utf-8 -*-
"""Targeted real branch-coverage tests for core/integration_ecosystem.py.

Uses real ``IntegrationEcosystem`` / ``ConnectorMarketplace`` / ``PluginSDK``
instances and in-memory data.  No ``unittest.mock`` / ``pytest.mock`` objects.
"""
import asyncio
import os
from datetime import timedelta

import pytest

import core.integration_ecosystem as ie


class _InMemResponse:
    """Minimal in-memory HTTP response object."""

    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        return self._json if self._json is not None else {}


class _InMemSession:
    """In-memory HTTP transport for exercising status-code branches
    without real network calls.
    """

    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self.json_data = json_data

    def get(self, *args, **kwargs):
        return _InMemResponse(self.status_code, self.json_data)

    def post(self, *args, **kwargs):
        return _InMemResponse(self.status_code, self.json_data)


async def test_remaining_provider_activation_pass_branches():
    """Cover otherwise-uncovered provider activation ``pass`` branches."""
    ecosystem = ie.IntegrationEcosystem()

    monitoring = [
        ("prometheus", {"url": "http://x", "port": 1}),
        ("grafana", {"url": "http://x"}),
    ]
    for provider, config in monitoring:
        integration = await ecosystem.register_integration(
            name=provider.capitalize(),
            integration_type=ie.IntegrationType.MONITORING,
            provider=provider,
            configuration=config,
        )
        assert integration.status == ie.IntegrationStatus.ACTIVE

    cloud = [
        ("aws", {"access_key": "a", "secret_key": "s", "region": "r"}),
        ("azure", {}),
    ]
    for provider, creds in cloud:
        integration = await ecosystem.register_integration(
            name=provider.capitalize(),
            integration_type=ie.IntegrationType.CLOUD,
            provider=provider,
            configuration={},
            credentials=creds,
        )
        assert integration.status == ie.IntegrationStatus.ACTIVE

    cicd = [
        ("jenkins", {"api_token": "t"}),
        ("gitlab", {"private_token": "t"}),
    ]
    for provider, creds in cicd:
        integration = await ecosystem.register_integration(
            name=provider.capitalize(),
            integration_type=ie.IntegrationType.CICD,
            provider=provider,
            configuration={},
            credentials=creds,
        )
        assert integration.status == ie.IntegrationStatus.ACTIVE

    notifications = [
        ("teams", {"webhook_url": "http://x"}, {}),
        ("dingtalk", {"webhook_url": "http://x"}, {"secret": "s"}),
        ("wecom", {"webhook_url": "http://x"}, {}),
        ("email", {"smtp_host": "h", "smtp_port": 1, "sender": "a@b"}, {}),
    ]
    for provider, config, creds in notifications:
        integration = await ecosystem.register_integration(
            name=provider.capitalize(),
            integration_type=ie.IntegrationType.NOTIFICATION,
            provider=provider,
            configuration=config,
            credentials=creds,
        )
        assert integration.status == ie.IntegrationStatus.ACTIVE


async def test_integration_lifecycle_branches():
    """Cover list, disable, enable, and cleanup-without-url branches."""
    ecosystem = ie.IntegrationEcosystem()

    prom = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://x", "port": 1},
    )

    # list with and without filter (930/931/933)
    assert await ecosystem.list_integrations()
    assert await ecosystem.list_integrations(ie.IntegrationType.MONITORING)

    # disable a real integration (940)
    assert await ecosystem.disable_integration(prom.id) is True
    assert prom.status == ie.IntegrationStatus.INACTIVE

    # enable a real integration (950)
    assert await ecosystem.enable_integration(prom.id) is True
    assert prom.status == ie.IntegrationStatus.ACTIVE

    # remove an integration with no url to exercise cleanup url-false branch
    aws = await ecosystem.register_integration(
        name="AWS",
        integration_type=ie.IntegrationType.CLOUD,
        provider="aws",
        configuration={},
        credentials={"access_key": "a", "secret_key": "s", "region": "r"},
    )
    assert await ecosystem.remove_integration(aws.id) is True


async def test_publish_and_event_loop_branches():
    """Cover publish_event and the event-processing loop inner while branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.event_processing_interval = timedelta(seconds=0.01)

    # publish_event (703)
    assert await ecosystem.publish_event("demo", {"x": 1}) is True
    assert len(ecosystem.event_queue) == 1

    called = []

    async def handler(event):
        called.append(event.id)

    ecosystem.register_event_handler("demo", handler)

    task = asyncio.create_task(ecosystem._event_processing_loop())
    try:
        await asyncio.sleep(0.05)
        assert len(called) == 1
        assert len(ecosystem.event_queue) == 0
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def test_prometheus_query_remaining_branches():
    """Cover not-found, invalid query, no HTTP and non-200 branches."""
    ecosystem = ie.IntegrationEcosystem()

    # integration not found (761)
    assert await ecosystem.query_prometheus_metrics("up", "missing", "1h") is None

    prom = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://x", "port": 1},
    )

    # invalid PromQL (770)
    assert await ecosystem.query_prometheus_metrics("!!!", prom.id, "1h") is None
    # invalid time range (775) -- exercised for completeness
    assert await ecosystem.query_prometheus_metrics("up", prom.id, "bad") is None

    # HTTP not available (796)
    original = ie.REQUESTS_AVAILABLE
    try:
        ie.REQUESTS_AVAILABLE = False
        assert await ecosystem.query_prometheus_metrics("up", prom.id, "1h") is None
    finally:
        ie.REQUESTS_AVAILABLE = original

    # non-200 response (820)
    ecosystem.http_session = _InMemSession(500)
    result = await ecosystem.query_prometheus_metrics("up", prom.id, "1h")
    assert result is not None and "error" in result


async def test_jenkins_jira_remaining_branches():
    """Cover not-found, no-HTTP and 201/non-201 branches for Jenkins/Jira."""
    ecosystem = ie.IntegrationEcosystem()

    # not found (844 / 879)
    assert await ecosystem.trigger_jenkins_build("job", "missing", {}) is False
    assert await ecosystem.create_jira_ticket("summary", "desc", "missing") is None

    jenkins = await ecosystem.register_integration(
        name="Jenkins",
        integration_type=ie.IntegrationType.CICD,
        provider="jenkins",
        configuration={"url": "http://x"},
        credentials={"api_token": "t"},
    )
    jira = await ecosystem.register_integration(
        name="Jira",
        integration_type=ie.IntegrationType.ITSM,
        provider="jira",
        configuration={"url": "http://x", "project_key": "OPS"},
        credentials={"username": "u", "api_token": "t"},
    )

    # HTTP not available (861/862 and 913/914)
    original = ie.REQUESTS_AVAILABLE
    try:
        ie.REQUESTS_AVAILABLE = False
        assert await ecosystem.trigger_jenkins_build("job", jenkins.id, {}) is False
        assert await ecosystem.create_jira_ticket("summary", "desc", jira.id) is None
    finally:
        ie.REQUESTS_AVAILABLE = original

    # Jira 201 (907,908)
    ecosystem.http_session = _InMemSession(201, {"key": "OPS-1"})
    assert await ecosystem.create_jira_ticket("summary", "desc", jira.id) == "OPS-1"

    # Jira non-201 (907,910)
    ecosystem.http_session = _InMemSession(500)
    assert await ecosystem.create_jira_ticket("summary", "desc", jira.id) is None


async def test_p2_connector_marketplace_remaining_branches():
    """Cover discover, uninstall, first rating and details branches."""
    market = ie.ConnectorMarketplace()

    # discover with no filter, category and search (1559, 1560, 1562)
    all_conn = await market.discover_connectors()
    assert all_conn
    cloud = await market.discover_connectors(category="cloud")
    assert cloud
    search = await market.discover_connectors(search_query="AWS")
    assert search

    # install a connector and then exercise details and rating
    install = await market.install_connector(
        "prometheus", {"url": "http://x", "port": 1}
    )
    assert install["success"]

    details = await market.get_connector_details("prometheus")
    assert details is not None

    # first rating (1641)
    rate = await market.rate_connector("prometheus", 5.0)
    assert rate["success"]

    # uninstall not installed (1617)
    bad_uninstall = await market.uninstall_connector("not_installed")
    assert bad_uninstall["success"] is False

    # uninstall installed (1617 fallthrough)
    good_uninstall = await market.uninstall_connector("prometheus")
    assert good_uninstall["success"] is True

    # invalid rating (1638/1641)
    invalid = await market.rate_connector("prometheus", 7.0)
    assert invalid["success"] is False


async def test_p2_plugin_sdk_remaining_branches():
    """Cover plugin register duplicate, execute/not-found, hooks."""
    sdk = ie.PluginSDK()

    async def ok(data):
        return data

    await sdk.register_plugin("p1", "Plugin", "1.0", {}, ok)

    # duplicate registration (1716)
    dup = await sdk.register_plugin("p1", "Plugin", "1.0", {}, ok)
    assert dup["success"] is False

    # execute not found (1757)
    notfound = await sdk.execute_plugin("missing", {})
    assert notfound["success"] is False

    # execute exception (1765)
    async def boom(data):
        raise ValueError("boom")

    await sdk.register_plugin("p2", "Boom", "1.0", {}, boom)
    exc = await sdk.execute_plugin("p2", {})
    assert exc["success"] is False

    # unregister not found (1739)
    unreg = await sdk.unregister_plugin("missing")
    assert unreg["success"] is False

    # first hook registration (1779)
    reg1 = await sdk.register_hook("h1", ok)
    assert reg1["success"]

    # trigger hook with no handlers (1797)
    assert await sdk.trigger_hook("no_such_hook", {}) == []

    # trigger hook exception (1804)
    await sdk.register_hook("h2", boom)
    res = await sdk.trigger_hook("h2", {})
    assert len(res) == 1
    assert res[0]["success"] is False


async def test_activation_fallthrough_and_notification_else():
    """Cover activation fall-throughs and the send_notification else branch."""
    ecosystem = ie.IntegrationEcosystem()

    # fall-through branches for unknown providers (391->exit, 405->exit, 419->exit)
    datadog = await ecosystem.register_integration(
        name="Datadog",
        integration_type=ie.IntegrationType.MONITORING,
        provider="datadog",
        configuration={"api_key": "k", "app_key": "a"},
    )
    assert datadog.status == ie.IntegrationStatus.ACTIVE

    alicloud = await ecosystem.register_integration(
        name="Alibaba Cloud",
        integration_type=ie.IntegrationType.CLOUD,
        provider="alibaba_cloud",
        configuration={"access_key": "a", "secret_key": "s", "region": "r"},
    )
    assert alicloud.status == ie.IntegrationStatus.ACTIVE

    circle = await ecosystem.register_integration(
        name="CircleCI",
        integration_type=ie.IntegrationType.CICD,
        provider="circleci",
        configuration={"project_slug": "o/r", "api_token": "t"},
    )
    assert circle.status == ie.IntegrationStatus.ACTIVE

    # send_notification else for unsupported channel (455,458)
    assert await ecosystem.send_notification(ie.NotificationChannel.SMS, "hello") is False
    assert await ecosystem.send_notification(ie.NotificationChannel.WEBHOOK, "hello") is False

    # slack with requests disabled (467,468)
    slack = await ecosystem.register_integration(
        name="Slack",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={"webhook_url": "http://x", "channel": "#ops"},
    )
    original = ie.REQUESTS_AVAILABLE
    try:
        ie.REQUESTS_AVAILABLE = False
        assert await ecosystem.send_notification(ie.NotificationChannel.SLACK, "hello") is False
    finally:
        ie.REQUESTS_AVAILABLE = original


async def test_email_notification_branches():
    """Cover email not-found and missing-config branches."""
    ecosystem = ie.IntegrationEcosystem()

    # email integration not found (528,529)
    assert await ecosystem.send_notification(ie.NotificationChannel.EMAIL, "hello") is False

    # email integration with missing host/sender/recipient (539,540)
    email = await ecosystem.register_integration(
        name="Email",
        integration_type=ie.IntegrationType.NOTIFICATION,
        provider="email",
        configuration={},
    )
    assert await ecosystem.send_notification(ie.NotificationChannel.EMAIL, "hello") is False


async def test_validation_missing_fields_and_prometheus_200():
    """Cover validation missing-field branches and the prometheus 200 branch."""
    ecosystem = ie.IntegrationEcosystem()

    # missing required field branches
    prom_bad = ie.IntegrationConfig(
        id="prom_bad",
        name="Prometheus",
        type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_monitoring_integration(prom_bad))["valid"] is False

    aws_bad = ie.IntegrationConfig(
        id="aws_bad",
        name="AWS",
        type=ie.IntegrationType.CLOUD,
        provider="aws",
        configuration={},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_cloud_integration(aws_bad))["valid"] is False

    gh_bad = ie.IntegrationConfig(
        id="gh_bad",
        name="GitHub",
        type=ie.IntegrationType.CICD,
        provider="github",
        configuration={},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_cicd_integration(gh_bad))["valid"] is False

    slack_bad = ie.IntegrationConfig(
        id="slack_bad",
        name="Slack",
        type=ie.IntegrationType.NOTIFICATION,
        provider="slack",
        configuration={},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_notification_integration(slack_bad))["valid"] is False

    # prometheus connection success (318,319)
    ecosystem.http_session = _InMemSession(200)
    prom_ok = ie.IntegrationConfig(
        id="prom_ok",
        name="Prometheus",
        type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://x", "port": 1},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_monitoring_integration(prom_ok))["valid"] is True

    # prometheus non-200 still valid (318,323)
    ecosystem.http_session = _InMemSession(503)
    prom_503 = ie.IntegrationConfig(
        id="prom_503",
        name="Prometheus",
        type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://x", "port": 1},
        status=ie.IntegrationStatus.PENDING,
    )
    assert (await ecosystem._validate_monitoring_integration(prom_503))["valid"] is True


async def test_query_prometheus_200_and_jenkins_201(tmp_path):
    """Cover the prometheus 200 and jenkins 201 success branches."""
    ecosystem = ie.IntegrationEcosystem()

    prom = await ecosystem.register_integration(
        name="Prometheus",
        integration_type=ie.IntegrationType.MONITORING,
        provider="prometheus",
        configuration={"url": "http://x", "port": 1},
    )
    ecosystem.http_session = _InMemSession(200, {"data": {"result": []}})
    result = await ecosystem.query_prometheus_metrics("up", prom.id, "1h")
    assert result == {"data": {"result": []}}

    jenkins = await ecosystem.register_integration(
        name="Jenkins",
        integration_type=ie.IntegrationType.CICD,
        provider="jenkins",
        configuration={"url": "http://x"},
        credentials={"api_token": "t"},
    )
    ecosystem.http_session = _InMemSession(201)
    assert await ecosystem.trigger_jenkins_build("job", jenkins.id, {}) is True


async def test_load_existing_integrations_valid_and_invalid(tmp_path):
    """Cover the valid/invalid load branches from integrations.json."""
    path = tmp_path / "integrations.json"
    path.write_text(
        '[{"name": "Prometheus", "type": "monitoring", "provider": "prometheus", '
        '"configuration": {"url": "http://x", "port": 1}, "status": "pending"}, '
        '{"type": "monitoring"}]',
        encoding="utf-8",
    )
    os.environ["AIOPS_INTEGRATIONS_PATH"] = str(path)
    try:
        ecosystem = ie.IntegrationEcosystem()
        await ecosystem._load_existing_integrations()
        assert any(i.provider == "prometheus" for i in ecosystem.integrations.values())
    finally:
        if "AIOPS_INTEGRATIONS_PATH" in os.environ:
            del os.environ["AIOPS_INTEGRATIONS_PATH"]


async def test_p2_marketplace_and_plugin_extra_branches():
    """Cover re-rating, unknown rating, unregister and second hook branches."""
    market = ie.ConnectorMarketplace()

    # rate an unknown connector (1635,1636)
    assert (await market.rate_connector("unknown", 3.0))["success"] is False

    # install and rate twice to cover second-rating branch (1641,1644)
    await market.install_connector("prometheus", {"url": "http://x", "port": 1})
    await market.rate_connector("prometheus", 4.0)
    await market.rate_connector("prometheus", 5.0)

    sdk = ie.PluginSDK()

    async def ok(data):
        return data

    await sdk.register_plugin("p1", "P", "1.0", {}, ok)
    # unregister a registered plugin (1739,1742)
    assert (await sdk.unregister_plugin("p1"))["success"] is True

    # second handler for the same hook (1779,1782)
    await sdk.register_hook("h1", ok)
    await sdk.register_hook("h1", ok)
    results = await sdk.trigger_hook("h1", {})
    assert len(results) == 2


async def test_register_integration_validation_failure():
    """Cover the validation-failure branch in register_integration."""
    ecosystem = ie.IntegrationEcosystem()

    with pytest.raises(ValueError, match="validation failed"):
        await ecosystem.register_integration(
            name="Slack",
            integration_type=ie.IntegrationType.NOTIFICATION,
            provider="slack",
            configuration={},
        )


async def test_register_integration_max_limit():
    """Cover the maximum-integration limit branch."""
    ecosystem = ie.IntegrationEcosystem()
    ecosystem.max_integrations = 1

    await ecosystem.register_integration(
        name="First",
        integration_type=ie.IntegrationType.MONITORING,
        provider="grafana",
        configuration={"url": "http://x"},
    )

    with pytest.raises(ValueError, match="Maximum integration limit"):
        await ecosystem.register_integration(
            name="Second",
            integration_type=ie.IntegrationType.CLOUD,
            provider="gcp",
            configuration={},
        )


class _InMemAioResponse:
    def __init__(self, status):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class _InMemAioSession:
    def __init__(self, status):
        self.status = status

    def post(self, *args, **kwargs):
        return _InMemAioResponse(self.status)


async def test_trigger_webhook_aiohttp_branches():
    """Cover the aiohttp webhook branches."""
    ecosystem = ie.IntegrationEcosystem()
    webhook = await ecosystem.register_webhook(
        url="http://x", events=["alert"]
    )

    original_aio = ie.AIOHTTP_AVAILABLE
    try:
        ie.AIOHTTP_AVAILABLE = True
        ecosystem.aiohttp_session = _InMemAioSession(200)
        assert await ecosystem.trigger_webhook(webhook.id, {"event": "alert"}) is True

        ecosystem.aiohttp_session = _InMemAioSession(500)
        assert await ecosystem.trigger_webhook(webhook.id, {"event": "alert"}) is False
    finally:
        ie.AIOHTTP_AVAILABLE = original_aio


async def test_trigger_webhook_no_http_client():
    """Cover the no-HTTP-client branch in trigger_webhook."""
    ecosystem = ie.IntegrationEcosystem()
    webhook = await ecosystem.register_webhook(
        url="http://x", events=["alert"]
    )

    original_requests = ie.REQUESTS_AVAILABLE
    original_aio = ie.AIOHTTP_AVAILABLE
    try:
        ie.REQUESTS_AVAILABLE = False
        ie.AIOHTTP_AVAILABLE = False
        assert await ecosystem.trigger_webhook(webhook.id, {"event": "alert"}) is False
    finally:
        ie.REQUESTS_AVAILABLE = original_requests
        ie.AIOHTTP_AVAILABLE = original_aio
