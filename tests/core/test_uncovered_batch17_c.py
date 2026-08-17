# -*- coding: utf-8 -*-
"""Pytest coverage suite for batch17-c core modules."""

import asyncio
import importlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

import core.sso_auth

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.ai.llm_router.cost_optimizer
# ---------------------------------------------------------------------------
def test_cost_optimizer_inheritance_and_lookup():
    from core.ai.llm_router.capability_evaluator import TaskType
    from core.ai.llm_router.cost_optimizer import CostOptimizer

    configs = [
        {"model": "gpt-4o-mini", "max_tokens": 128000, "cost_per_1k": 0.015},
        {"model": "gpt-3.5-turbo", "max_tokens": 16384, "cost_per_1k": 0.005},
    ]
    optimizer = CostOptimizer(
        model_configs=configs,
        budget_per_request=1.0,
        max_cost_per_hour=10.0,
        max_cost_per_day=50.0,
    )

    assert optimizer.budget_per_request == 1.0
    assert optimizer._find_model_config("gpt-3.5-turbo") is not None
    assert optimizer._find_model_config("missing") is None

    monkey = {"estimate_tokens": lambda *a, **k: 1000}
    optimizer.estimate_tokens = monkey["estimate_tokens"]

    decision = optimizer.select_cheapest_model(
        "hello world",
        task_type=TaskType.GENERAL,
        min_capability_score=0.5,
    )
    assert decision is not None
    assert decision.model_name == "gpt-3.5-turbo"
    assert decision.estimated_tokens == 1000
    assert decision.estimated_cost == 0.005


def test_cost_optimizer_fallback_and_empty():
    from core.ai.llm_router.capability_evaluator import TaskType
    from core.ai.llm_router.cost_optimizer import CostOptimizer

    optimizer = CostOptimizer(model_configs=[])
    assert optimizer.select_cheapest_model("x") is None

    configs = [
        {"model": "gpt-4o-mini", "max_tokens": 128000, "cost_per_1k": 0.015},
        {"model": "gpt-3.5-turbo", "max_tokens": 16384, "cost_per_1k": 0.005},
    ]
    optimizer = CostOptimizer(model_configs=configs)
    optimizer.estimate_tokens = lambda *a, **k: 1000

    high_threshold = optimizer.select_cheapest_model(
        "hello",
        task_type=TaskType.GENERAL,
        min_capability_score=0.99,
    )
    assert high_threshold is not None
    assert high_threshold.model_name == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# core.l6l7_frontend_integrator
# ---------------------------------------------------------------------------
def _run_async(coro):
    return asyncio.run(coro)


def test_l6l7_frontend_integrator_registration_and_statistics():
    from core.l6l7_frontend_integrator import (
        ComponentConfig,
        ComponentType,
        DataBinding,
        EventType,
        FrontendEvent,
        L6L7FrontendIntegrator,
        get_l6l7_frontend_integrator,
    )

    integrator = get_l6l7_frontend_integrator(
        {"auto_refresh_enabled": True, "event_buffer_size": 50}
    )
    assert isinstance(integrator, L6L7FrontendIntegrator)

    comp = ComponentConfig(
        component_id="c1",
        component_name="Dashboard",
        component_type=ComponentType.DASHBOARD,
        data_source="ds1",
        update_frequency=2,
    )
    target = ComponentConfig(
        component_id="c2",
        component_name="Chart",
        component_type=ComponentType.CHART,
        data_source="ds2",
    )
    integrator.register_component(comp)
    integrator.register_component(target)

    handled = []

    def bad_handler(event):
        raise RuntimeError("boom")

    async def good_handler(event):
        handled.append(event.event_id)

    integrator.register_event_handler(EventType.DATA_UPDATE, bad_handler)
    integrator.register_event_handler(EventType.DATA_UPDATE, good_handler)

    binding = DataBinding(
        binding_id="b1",
        source_component="c1",
        target_component="c2",
        data_path=".",
        transformation="upper",
    )
    integrator.register_data_binding(binding)

    async def _process():
        event = FrontendEvent(
            event_id="e1",
            event_type=EventType.DATA_UPDATE,
            component_id="c1",
            component_type=ComponentType.DASHBOARD,
            data={"v": 1},
        )
        await integrator.emit_event(event)
        await integrator._process_event(event)

        assert integrator.get_component_data("c1") == {"v": 1}
        assert integrator.get_component_data("c2") == {"v": 1}
        assert "e1" in handled
        assert integrator.total_events == 1
        assert integrator.total_updates == 1

        # manual update
        ok = await integrator.update_component("c1", {"v": 2})
        assert ok
        assert integrator.total_updates == 2
        assert not await integrator.update_component("missing", {})

    _run_async(_process())

    assert integrator.get_component_config("c1")["component_id"] == "c1"
    assert integrator.get_component_config("missing") is None
    assert integrator.get_component_data("missing") is None

    stats = integrator.get_statistics()
    assert stats["total_events"] == 2
    assert stats["registered_components"] == 2
    assert stats["registered_bindings"] == 1
    assert stats["active_handlers"] == 2


def test_l6l7_event_processor_lifecycle():
    from core.l6l7_frontend_integrator import (
        ComponentConfig,
        ComponentType,
        EventType,
        FrontendEvent,
        L6L7FrontendIntegrator,
    )

    async def _run():
        integrator = L6L7FrontendIntegrator()
        integrator.register_component(
            ComponentConfig(
                component_id="c1",
                component_name="C",
                component_type=ComponentType.TABLE,
                data_source="ds",
            )
        )

        handled = []
        integrator.register_event_handler(
            EventType.DATA_UPDATE, lambda e: handled.append(e.event_id)
        )

        await integrator.start_event_processor()
        await integrator.emit_event(
            FrontendEvent(
                event_id="e1",
                event_type=EventType.DATA_UPDATE,
                component_id="c1",
                component_type=ComponentType.TABLE,
                data={"k": "v"},
            )
        )
        await asyncio.sleep(0.2)

        current = asyncio.current_task()
        for task in list(asyncio.all_tasks()):
            if task is not current:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        assert "e1" in handled

    _run_async(_run())


def test_l6l7_auto_refresh_lifecycle():
    from core.l6l7_frontend_integrator import (
        ComponentConfig,
        ComponentType,
        L6L7FrontendIntegrator,
    )

    async def _run():
        integrator = L6L7FrontendIntegrator()
        integrator.register_component(
            ComponentConfig(
                component_id="c1",
                component_name="C",
                component_type=ComponentType.NOTIFICATION,
                data_source="ds",
                auto_refresh=True,
            )
        )

        await integrator.start_auto_refresh()
        await asyncio.sleep(0.4)

        current = asyncio.current_task()
        for task in list(asyncio.all_tasks()):
            if task is not current:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        assert "c1" in integrator.components

    _run_async(_run())


# ---------------------------------------------------------------------------
# core.sso_auth
# ---------------------------------------------------------------------------
def test_sso_auth_generate_state_and_login_success():
    state = core.sso_auth.generate_state()
    assert isinstance(state, str) and len(state) > 0

    html = asyncio.run(core.sso_auth.login_success(token="abc123"))
    assert "abc123" in html.body.decode()
    assert html.status_code == 200


def test_sso_auth_disabled():
    assert core.sso_auth.SSO_ENABLED is False

    request = MagicMock()
    with pytest.raises(HTTPException, match="SSO not configured"):
        asyncio.run(core.sso_auth.login(request))
    with pytest.raises(HTTPException, match="SSO not configured"):
        asyncio.run(core.sso_auth.auth_callback(request, state="x"))


def test_sso_auth_enabled_flow(monkeypatch):
    from authlib.integrations.starlette_client import OAuthError

    monkeypatch.setenv("OIDC_ISSUER_URL", "https://idp.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:8000/auth/callback")

    importlib.reload(core.sso_auth)
    assert core.sso_auth.SSO_ENABLED is True

    sso = core.sso_auth
    request = MagicMock()

    # login
    redirect = RedirectResponse(url="https://idp.example.com/authorize")
    sso.oauth.oidc.authorize_redirect = AsyncMock(return_value=redirect)
    result = asyncio.run(sso.login(request))
    assert isinstance(result, RedirectResponse)
    assert len(sso._state_store) == 1
    state = list(sso._state_store.keys())[0]

    # invalid state
    with pytest.raises(HTTPException, match="Invalid state parameter"):
        asyncio.run(sso.auth_callback(request, state="bad"))

    # expired state
    expired_state = "expired-state"
    sso._state_store[expired_state] = datetime.now(timezone.utc) - timedelta(minutes=10)
    with pytest.raises(HTTPException, match="State parameter expired"):
        asyncio.run(sso.auth_callback(request, state=expired_state))

    # OAuth error during token exchange
    sso._state_store["valid1"] = datetime.now(timezone.utc)
    sso.oauth.oidc.authorize_access_token = AsyncMock(side_effect=OAuthError(error="invalid_grant"))
    with pytest.raises(HTTPException, match="OAuth error"):
        asyncio.run(sso.auth_callback(request, state="valid1"))

    # missing userinfo
    sso._state_store["valid2"] = datetime.now(timezone.utc)
    sso.oauth.oidc.authorize_access_token = AsyncMock(return_value={"access_token": "abc"})
    with pytest.raises(HTTPException, match="Unable to retrieve user information"):
        asyncio.run(sso.auth_callback(request, state="valid2"))

    # valid callback, new user
    sso._state_store["valid3"] = datetime.now(timezone.utc)
    sso.oauth.oidc.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "newuser",
                "email": "new@example.com",
                "name": "New User",
                "role": "admin",
            }
        }
    )
    sso.get_user = AsyncMock(return_value=None)
    result = asyncio.run(sso.auth_callback(request, state="valid3"))
    assert isinstance(result, RedirectResponse)
    assert "token=" in result.headers["location"]

    # valid callback, existing user
    sso._state_store["valid4"] = datetime.now(timezone.utc)
    existing = sso.UserInDB(
        username="existing",
        full_name="Ex",
        email="ex@example.com",
        hashed_password="hp",
        disabled=False,
        role="user",
    )
    sso.get_user = AsyncMock(return_value=existing)
    result = asyncio.run(sso.auth_callback(request, state="valid4"))
    assert isinstance(result, RedirectResponse)

    # valid callback, get_user raises
    sso._state_store["valid5"] = datetime.now(timezone.utc)
    sso.get_user = AsyncMock(side_effect=RuntimeError("db down"))
    result = asyncio.run(sso.auth_callback(request, state="valid5"))
    assert isinstance(result, RedirectResponse)

    # restore disabled state so other tests are not affected
    monkeypatch.undo()
    importlib.reload(core.sso_auth)
    assert core.sso_auth.SSO_ENABLED is False


# ---------------------------------------------------------------------------
# core.plugin_ecosystem_manager
# ---------------------------------------------------------------------------
def test_plugin_ecosystem_manager():
    from core.plugin_ecosystem_manager import (
        PluginActivityType,
        PluginEcosystemManager,
        PluginSupportLevel,
        get_ecosystem_manager,
    )

    mgr = PluginEcosystemManager({"version": "1.0"})
    assert mgr.config["version"] == "1.0"

    activity = mgr.record_activity(
        "p1",
        PluginActivityType.INSTALL,
        "u1",
        {"developer_id": "d1"},
    )
    assert activity.plugin_id == "p1"
    assert activity.activity_type == PluginActivityType.INSTALL

    assert mgr.register_developer(
        "d1",
        "Dev One",
        "d1@example.com",
        "ACME",
        PluginSupportLevel.PREMIUM,
    )
    assert not mgr.register_developer("d1", "Dup", "dup@example.com")

    assert mgr.update_developer_reputation("d1", 2.0)
    assert mgr.update_developer_reputation("d1", 10.0)  # clamp at 5.0
    assert mgr.developers["d1"].reputation_score == 5.0
    assert mgr.update_developer_reputation("d1", -10.0)  # clamp at 0.0
    assert mgr.developers["d1"].reputation_score == 0.0
    assert not mgr.update_developer_reputation("missing", 1.0)

    assert mgr.create_community_forum("f1", "Forum", "Desc", "p1")
    assert not mgr.create_community_forum("f1", "Dup", "Desc")

    assert mgr.create_developer_event(
        "e1", "Webinar", "Desc", datetime.now(timezone.utc), "webinar"
    )
    assert not mgr.create_developer_event("e1", "Dup", "Desc", datetime.now(timezone.utc))

    assert mgr.create_incentive_program("i1", "Bounty", "Desc", "cash", 100.0)
    assert not mgr.create_incentive_program("i1", "Dup", "Desc", "cash", 50.0)

    acts = mgr.get_plugin_activities("p1", timedelta(days=1))
    assert len(acts) == 1
    assert mgr.get_plugin_activities("p1")[0]["activity_type"] == "install"
    assert isinstance(mgr.get_plugin_activities("p1", timedelta(seconds=0)), list)

    stats = mgr.get_developer_stats("d1")
    assert stats is not None
    assert stats["developer_id"] == "d1"
    assert stats["support_level"] == "premium"
    assert mgr.get_developer_stats("missing") is None

    summary = mgr.get_ecosystem_summary()
    assert summary["total_activities"] >= 1
    assert summary["total_developers"] == 1
    assert summary["total_forums"] == 1
    assert summary["total_events"] == 1
    assert summary["total_programs"] == 1
    assert summary["developers_by_support_level"]["premium"] == 1

    assert isinstance(get_ecosystem_manager(), PluginEcosystemManager)


# ---------------------------------------------------------------------------
# core.documentation_generator
# ---------------------------------------------------------------------------
def test_documentation_generator(tmp_path):
    from core.documentation_generator import (
        DocumentationGenerator,
        GeneratorType,
        get_documentation_generator,
    )

    gen = DocumentationGenerator({"default_generator_type": "html"})
    assert gen.default_generator_type == GeneratorType.HTML

    templates = gen.get_available_templates()
    assert "quick_start" in templates

    vars_qs = {
        "title": "My App",
        "prerequisites": "Python 3.12",
        "installation_step_1": "pip install myapp",
        "installation_step_2": "pip install -e .",
        "installation_step_3": "myapp init",
        "first_step_1": "run server",
        "first_step_2": "open browser",
        "first_step_3": "enjoy",
        "next_step_1": "read docs",
        "next_step_2": "join community",
        "next_step_3": "contribute",
        "documentation_url": "https://docs.example.com",
        "support_url": "https://support.example.com",
        "community_url": "https://community.example.com",
    }
    doc = gen.generate_document("d1", "My App", "quick_start", vars_qs, GeneratorType.MARKDOWN)
    assert doc is not None
    assert doc.generator_type == GeneratorType.MARKDOWN
    assert "My App" in doc.content

    # unknown template
    assert gen.generate_document("d2", "X", "missing", {}) is None

    # format exception handled gracefully
    bad = gen.generate_document("d3", "X", "quick_start", {})
    assert bad is None

    # save and retrieve
    out = tmp_path / "doc.md"
    assert gen.save_generated_document("d1", str(out))
    assert "My App" in out.read_text(encoding="utf-8")
    assert not gen.save_generated_document("missing", str(out))

    assert gen.get_generated_document("d1") is not None
    assert gen.get_generated_document("missing") is None

    docs = gen.list_generated_documents()
    assert any(d["doc_id"] == "d1" for d in docs)

    summary = gen.get_generator_summary()
    assert summary["total_generated"] >= 1
    assert len(summary["available_templates"]) == len(templates)

    assert isinstance(get_documentation_generator(), DocumentationGenerator)
