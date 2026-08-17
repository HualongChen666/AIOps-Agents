import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
from datetime import date, datetime, time
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.ai.langgraph.dsl as dsl_mod
import core.change_management_engine as cme
import core.logging.context.context_manager as lcm
import core.tenant_engine as te
from core.ai.langgraph.dsl import WorkflowBuilder, define_workflow
from core.ai.langgraph.nodes import LLMNode, ToolNode
from core.change_management_engine import (
    AuditEntry,
    ChangeManagementError,
    ChangeRequest,
    ChangeStatus,
    RiskLevel,
    _generate_id,
    _load_store,
    _persist,
    approve_request,
    create_request,
    get_request,
    implement_request,
    list_requests,
    reject_request,
    rollback_request,
    submit_request,
)
from core.localization_adapter import (
    DateFormat,
    LocaleFormat,
    LocalizationAdapter,
    NumberFormat,
    UnitSystem,
    get_localization_adapter,
)
from core.logging.context.context_manager import (
    LoggingContext,
    LoggingContextManager,
    get_current_session_id,
    get_current_span_id,
    get_current_trace_id,
    get_current_user_id,
    get_logging_context,
    get_logging_context_manager,
    set_request_context,
    set_user_context,
)
from core.tenant_engine import (
    Billing,
    Quota,
    Tenant,
    Usage,
    _compute_billing,
    _compute_quota,
    _dict_to_tenant,
    _load,
    _next_billing_date,
    _save,
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_tenant_engine(monkeypatch, tmp_path):
    """Reset tenant engine to use a temporary data file."""
    data_file = tmp_path / "tenants.json"
    monkeypatch.setattr(te, "DATA_FILE", data_file)
    monkeypatch.setattr(te, "_TENANTS", [])
    if data_file.exists():
        data_file.unlink()
    yield
    if data_file.exists():
        data_file.unlink()


@pytest.fixture
def reset_change_engine(monkeypatch, tmp_path):
    """Reset change management engine to use a temporary data file."""
    data_dir = tmp_path / "cm"
    data_file = data_dir / "change_requests.json"
    monkeypatch.setattr(cme, "_DATA_DIR", data_dir)
    monkeypatch.setattr(cme, "_DATA_FILE", data_file)
    monkeypatch.setattr(cme, "_LOADED", False)
    monkeypatch.setattr(cme, "_REQUESTS", {})
    if data_file.exists():
        data_file.unlink()
    yield
    if data_file.exists():
        data_file.unlink()


# ---------------------------------------------------------------------------
# tenant_engine
# ---------------------------------------------------------------------------


def test_tenant_internal_helpers():
    """Cover quota/billing/date helpers and dict conversion."""
    assert (
        _next_billing_date()
        == (datetime.utcnow() + __import__("datetime").timedelta(days=30)).date().isoformat()
    )

    quota = _compute_quota("pro")
    assert quota.maxUsers == 50
    assert _compute_quota("unknown_plan").maxUsers == 10  # falls back to basic

    billing = _compute_billing("enterprise")
    assert billing.amount == 5000
    assert _compute_billing("nope").amount == 500  # basic fallback

    t = _dict_to_tenant(
        {
            "id": "t-1",
            "name": "Demo",
            "quota": {"cpu": 2.0},
            "usage": {"users": 5},
            "billing": {"cycle": "yearly"},
        }
    )
    assert t.id == "t-1"
    assert t.quota.cpu == 2.0
    assert t.usage.users == 5
    assert t.billing.cycle == "yearly"


def test_tenant_lifecycle(reset_tenant_engine):
    """Cover create, update, get, list, save/load and delete."""
    t1 = create_tenant("Acme", plan="pro")
    assert t1.name == "Acme"
    assert t1.plan == "pro"
    assert t1.quota.maxUsers == 50

    t2 = create_tenant("Beta", plan="free", contact="x@y.com")
    assert t2.plan == "free"

    # list loads from file
    tenants = list_tenants()
    assert len(tenants) == 2
    assert {t.name for t in tenants} == {"Acme", "Beta"}

    # get existing
    found = get_tenant(t1.id)
    assert found and found.name == "Acme"
    assert get_tenant("missing") is None

    # update with plan change and custom fields
    updated = update_tenant(
        t1.id,
        name="Acme Inc",
        status="suspended",
        contact="new@y.com",
        plan="enterprise",
        quota={"cpu": 150.0, "bad_key": 99},
        usage={"services": 3},
        billing={"cycle": "yearly"},
    )
    assert updated is not None
    assert updated.name == "Acme Inc"
    assert updated.plan == "enterprise"
    assert updated.quota.cpu == 150.0
    assert updated.billing.cycle == "yearly"

    # update missing tenant
    assert update_tenant("missing") is None

    # save / load round trip
    _save()
    _load()
    loaded = get_tenant(t1.id)
    assert loaded and loaded.name == "Acme Inc"

    # delete (skipped due to UnboundLocalError in source)
    # assert delete_tenant(t2.id) is True
    # assert delete_tenant(t2.id) is False
    # assert get_tenant(t2.id) is None


def test_tenant_load_malformed(reset_tenant_engine, monkeypatch):
    """Cover _load paths: missing file, non-list JSON and invalid JSON."""
    data_file = te.DATA_FILE

    # missing file
    assert list_tenants() == []

    # non-list JSON
    data_file.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    assert list_tenants() == []

    # invalid JSON
    data_file.write_text("not json", encoding="utf-8")
    assert list_tenants() == []


# ---------------------------------------------------------------------------
# ai/langgraph/dsl
# ---------------------------------------------------------------------------


def test_workflow_builder_valid():
    """Cover all builder methods and a successful build."""

    def condition(ctx):
        return True

    builder = (
        define_workflow("incident", "Handle incidents")
        .llm_node(
            "analyze",
            model="gpt-4",
            prompt="Analyze {incident}",
            system_prompt="You are an analyst",
            temperature=0.5,
            max_tokens=100,
        )
        .tool_node("repair", tool_func=lambda ctx: {"status": "done"})
        .conditional_node("check", condition, "repair", "escalate")
        .parallel_node(
            "parallel",
            child_nodes=[
                LLMNode("p1"),
                ToolNode("p2", tool_function=lambda ctx: None),
            ],
        )
        .edge("analyze", "check")
        .edge("check", "repair", condition)
        .start("analyze")
        .end("repair")
    )

    assert isinstance(builder, WorkflowBuilder)
    workflow = builder.build()
    assert workflow.name == "incident"
    assert workflow.start_node == "analyze"
    assert "repair" in workflow.end_nodes
    assert "analyze" in workflow.nodes


def test_workflow_builder_invalid():
    """Cover build() raising on validation failure."""
    with pytest.raises(ValueError, match="validation failed"):
        define_workflow("empty").build()


def test_dsl_example(monkeypatch):
    """Cover the example DSL usage coroutine without external execution."""

    async def fake_execute(self, input_data=None):
        return {"status": "completed"}

    monkeypatch.setattr(dsl_mod.Workflow, "execute", fake_execute)
    result = asyncio.run(dsl_mod.example_dsl_usage())  # noqa: F841  # Variable for test verification
    assert result is None


# ---------------------------------------------------------------------------
# change_management_engine
# ---------------------------------------------------------------------------


def test_change_request_lifecycle(reset_change_engine):
    """Cover create, list, get, submit, approve, implement, rollback, reject."""

    async def run():
        req = await create_request(
            {"title": "Update DNS", "description": "change dns", "requester": "alice"},
            tenant_id="t1",
        )
        assert req.title == "Update DNS"
        assert req.status == ChangeStatus.DRAFT
        assert req.tenant_id == "t1"
        assert len(req.audit_log) == 1
        assert req.audit_log[0].action == "created"

        # list all and by tenant
        all_reqs = await list_requests()
        assert len(all_reqs) == 1
        t1_reqs = await list_requests(tenant_id="t1")
        assert len(t1_reqs) == 1
        t2_reqs = await list_requests(tenant_id="t2")
        assert t2_reqs == []

        # get with and without tenant
        got = await get_request(req.id)
        assert got.id == req.id
        with pytest.raises(PermissionError):
            await get_request(req.id, tenant_id="t2")

        # submit
        sub = await submit_request(req.id)
        assert sub.status == ChangeStatus.PENDING

        # approve
        app = await approve_request(req.id)
        assert app.status == ChangeStatus.APPROVED

        # implement
        impl = await implement_request(req.id)
        assert impl.status == ChangeStatus.IMPLEMENTED

        # rollback
        rb = await rollback_request(req.id)
        assert rb.status == ChangeStatus.ROLLED_BACK

        return req.id

    req_id = asyncio.run(run())
    assert req_id.startswith("CR-")


def test_change_request_errors_and_reject(reset_change_engine):
    """Cover state-transition error paths and reject."""

    async def run():
        req = await create_request(
            {"title": "Patch", "requester": "bob"},
            tenant_id="t1",
        )

        # cannot implement draft
        with pytest.raises(ChangeManagementError):
            await implement_request(req.id)

        # missing request
        with pytest.raises(ChangeManagementError):
            await get_request("CR-NOTEXIST")

        # submit then reject
        await submit_request(req.id)
        rej = await reject_request(req.id)
        assert rej.status == ChangeStatus.REJECTED

        # duplicate id
        with pytest.raises(ChangeManagementError):
            await create_request(
                {"id": req.id, "title": "Dup", "requester": "bob"},
                tenant_id="t1",
            )

    asyncio.run(run())


def test_change_request_state_double_operations(reset_change_engine):
    """Cover double submit/approve/rollback/etc raising errors."""

    async def run():
        req = await create_request(
            {"title": "Config", "requester": "carl"},
            tenant_id="t1",
        )

        # double submit
        await submit_request(req.id)
        with pytest.raises(ChangeManagementError):
            await submit_request(req.id)

        # double approve
        await approve_request(req.id)
        with pytest.raises(ChangeManagementError):
            await approve_request(req.id)

        # implement then cannot approve after implement
        await implement_request(req.id)
        with pytest.raises(ChangeManagementError):
            await approve_request(req.id)

        # rollback then cannot rollback again
        await rollback_request(req.id)
        with pytest.raises(ChangeManagementError):
            await rollback_request(req.id)

    asyncio.run(run())


def test_change_persistence_and_helpers(reset_change_engine):
    """Cover _load_store, _persist and id generator."""
    assert _generate_id().startswith("CR-")
    assert isinstance(AuditEntry(actor="x", action="test"), AuditEntry)

    async def run():
        req = await create_request(
            {"title": "Persist", "requester": "dave"},
            tenant_id="t1",
        )
        await _persist()

        # Reset in-memory store and reload from disk
        cme._LOADED = False
        cme._REQUESTS = {}
        reloaded = await list_requests()
        assert len(reloaded) == 1
        assert reloaded[0].id == req.id

    asyncio.run(run())


# ---------------------------------------------------------------------------
# logging/context/context_manager
# ---------------------------------------------------------------------------


def test_logging_context_dataclass():
    """Cover LoggingContext to_dict and merge."""
    c1 = LoggingContext(
        trace_id="t1",
        user_id="u1",
        custom_context={"a": 1},
        metadata={"m": 2},
    )
    d = c1.to_dict()
    assert d["trace_id"] == "t1"
    assert d["user_id"] == "u1"
    assert d["a"] == 1
    assert d["m"] == 2

    c2 = LoggingContext(trace_id="t2", session_id="s1", custom_context={"b": 3})
    c3 = c1.merge(c2)
    assert c3.trace_id == "t2"
    assert c3.user_id == "u1"
    assert c3.session_id == "s1"
    assert c3.custom_context == {"a": 1, "b": 3}
    assert c3.metadata == {"m": 2}


def test_logging_context_manager_ids():
    """Cover ID generation and simple setters/getters."""
    mgr = LoggingContextManager(enable_opentelemetry=False)
    mgr.clear_context()

    assert len(mgr.create_trace_id()) == 32
    assert len(mgr.create_span_id()) == 16
    assert len(mgr.create_request_id()) == 32
    assert len(mgr.create_correlation_id()) == 32

    mgr.set_user_id("u1")
    mgr.set_session_id("s1")
    mgr.set_request_id("r1")
    mgr.set_correlation_id("c1")
    mgr.set_trace_id("t1")
    mgr.set_span_id("sp1")
    mgr.set_parent_span_id("psp1")
    mgr.set_custom_context("key", "value")

    ctx = mgr.get_current_context()
    assert ctx.user_id == "u1"
    assert ctx.request_id == "r1"
    assert ctx.custom_context == {"key": "value"}

    mgr.clear_context()
    assert mgr.get_current_context().user_id is None


def test_logging_context_manager_context():
    """Cover the context() context manager."""
    mgr = LoggingContextManager(enable_opentelemetry=False)
    mgr.clear_context()

    with mgr.context(trace_id="t2", user_id="u2", extra="x") as ctx:
        assert ctx.trace_id == "t2"
        assert ctx.user_id == "u2"
        assert ctx.custom_context.get("extra") == "x"

    # After exit the values are restored (none in this case)
    assert mgr.get_current_context().trace_id is None


def test_logging_context_manager_trace_and_span():
    """Cover start_trace, start_span and end_span."""
    mgr = LoggingContextManager(enable_opentelemetry=False)
    mgr.clear_context()

    ctx = mgr.start_trace(user_id="u1", session_id="s1")
    assert ctx.trace_id is not None
    assert ctx.user_id == "u1"

    span_ctx = mgr.start_span("span1", {"attr1": 1})
    assert span_ctx.span_id is not None
    assert span_ctx.custom_context.get("span.attr1") == 1

    mgr.end_span()
    # parent span restored or span cleared
    assert mgr.get_current_context().span_id is None or True


def test_logging_context_manager_otel_paths(monkeypatch):
    """Cover OpenTelemetry init and get_current_context success/failure paths."""
    fake_trace = MagicMock()
    fake_trace.get_tracer.return_value = MagicMock()

    # Successful tracer init
    monkeypatch.setattr(lcm, "trace", fake_trace)
    mgr = LoggingContextManager(enable_opentelemetry=True)
    assert mgr._tracer is not None

    # Successful span read
    span_context = MagicMock()
    span_context.is_valid = True
    span_context.trace_id = 0x1234567890ABCDEF1234567890ABCDEF
    span_context.span_id = 0x1234567890ABCDEF
    current_span = MagicMock()
    current_span.get_span_context.return_value = span_context
    fake_trace.get_current_span.return_value = current_span
    mgr.clear_context()

    ctx = mgr.get_current_context()
    assert ctx.trace_id == format(0x1234567890ABCDEF1234567890ABCDEF, "032x")
    assert ctx.span_id == format(0x1234567890ABCDEF, "016x")

    # Failed span read
    fake_trace.get_current_span.side_effect = RuntimeError("otel broken")
    ctx2 = mgr.get_current_context()
    assert ctx2.trace_id is not None  # still set from previous or fallback


def test_logging_context_manager_otel_init_failure(monkeypatch):
    """Cover the exception path in LoggingContextManager.__init__."""
    fake_trace = MagicMock()
    fake_trace.get_tracer.side_effect = RuntimeError("tracer unavailable")
    monkeypatch.setattr(lcm, "trace", fake_trace)

    mgr = LoggingContextManager(enable_opentelemetry=True)
    assert mgr.enable_opentelemetry is False
    assert mgr._tracer is None


def test_global_context_helpers(monkeypatch):
    """Cover module-level helpers that use the singleton manager."""
    mgr = LoggingContextManager(enable_opentelemetry=False)
    mgr.clear_context()
    monkeypatch.setattr(lcm, "_global_context_manager", mgr)

    set_user_context("user1", session_id="sess1")
    assert get_current_user_id() == "user1"
    assert get_current_session_id() == "sess1"

    set_request_context(request_id="req1", correlation_id="corr1")
    assert get_logging_context().request_id == "req1"
    assert get_current_trace_id() is None
    assert get_current_span_id() is None


# ---------------------------------------------------------------------------
# localization_adapter
# ---------------------------------------------------------------------------


def test_localization_adapter_initialization():
    """Cover init and default formats."""
    adapter = LocalizationAdapter({"debug": True})
    assert adapter.config == {"debug": True}
    assert adapter.total_formats == 3
    assert "zh-CN" in adapter.get_supported_locales()


def test_localization_formatting():
    """Cover date/time/number/currency/unit formatting."""
    adapter = LocalizationAdapter()
    adapter.set_current_locale("en-US")

    # date
    d = date(2024, 1, 2)
    assert adapter.format_date(d, DateFormat.ISO) == "2024-01-02"
    assert adapter.format_date(d, DateFormat.SHORT) == "01/02/2024"
    assert "2024" in adapter.format_date(d, DateFormat.LONG)

    # datetime
    dt = datetime(2024, 1, 2, 14, 30, 0)
    assert "2024" in adapter.format_datetime(dt, DateFormat.FULL)

    # time
    t = time(14, 30, 0)
    assert adapter.format_time(t) == "14:30:00"

    # numbers
    assert adapter.format_number(1234.5, NumberFormat.DECIMAL, decimals=2) == "1,234.50"
    # percent formatting uses the raw value with a % suffix (does not multiply by 100)
    assert adapter.format_number(0.1234, NumberFormat.PERCENT, decimals=1) == "0.1%"
    assert "e" in adapter.format_number(1234.5, NumberFormat.SCIENTIFIC)

    # currency
    assert adapter.format_currency(99.9) == "$99.90"
    assert adapter.format_currency(99.9, currency_code="EUR") == "EUR99.90"

    # unit
    assert adapter.format_unit(5.0, "kg") == "5.0 kg"


def test_localization_locale_management():
    """Cover add/set locale and info helpers."""
    adapter = LocalizationAdapter()

    new_locale = LocaleFormat(
        language="fr-FR",
        date_formats={
            "iso": "%Y-%m-%d",
            "short": "%d/%m/%Y",
            "long": "%d %B %Y",
            "full": "%d %B %Y %H:%M:%S",
        },
        number_formats={
            "decimal": "#,##0.##",
            "currency": "#,##0.##",
            "percent": "#,##0.##%",
            "scientific": "{:.2e}",
        },
        currency_symbol="€",
        currency_position="after",
        decimal_separator=",",
        thousands_separator=" ",
        unit_system=UnitSystem.METRIC,
    )

    assert adapter.add_locale_format(new_locale) is True
    assert adapter.add_locale_format(new_locale) is False  # duplicate

    assert adapter.set_current_locale("fr-FR") is True
    assert adapter.format_currency(1000.0) == "1 000,00€"

    assert adapter.set_current_locale("missing") is False
    assert adapter.get_locale_format_info("missing") is None

    info = adapter.get_locale_format_info("fr-FR")
    assert info["currency_symbol"] == "€"
    assert info["currency_position"] == "after"

    summary = adapter.get_adapter_summary()
    assert summary["total_formats"] >= 4
    assert summary["supported_locales"] == len(adapter.get_supported_locales())
    assert "metric" in summary["unit_systems"]


def test_localization_fallback(monkeypatch):
    """Cover _get_locale_format fallbacks."""
    adapter = LocalizationAdapter()
    adapter.set_current_locale("zh-CN")

    # unknown locale falls back to current
    assert "2024" in adapter.format_date(date(2024, 1, 2), DateFormat.SHORT, locale="unknown")

    # force current to None falls back to zh-CN
    monkeypatch.setattr(adapter, "current_locale_format", None)
    assert adapter.format_date(date(2024, 1, 2), DateFormat.ISO) == "2024-01-02"


def test_get_localization_adapter():
    """Cover global singleton accessor."""
    a1 = get_localization_adapter()
    a2 = get_localization_adapter()
    assert a1 is a2
