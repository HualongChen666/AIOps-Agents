# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 13-c modules."""

import copy
import logging
import re
import shutil
import subprocess
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.chat_command_handler as cch
import core.exceptions.critical as critical
import core.logging.level.filter_strategy as fs
import core.security.subprocess_runner as sp_runner
import core.workflow_engine as wf

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.exceptions.critical
# ---------------------------------------------------------------------------
def test_critical_exception_basics():
    exc = critical.CriticalException("boom", context={"x": 1})
    assert exc.message == "boom"
    assert exc.error_code == "20_15_0001"
    assert exc.severity.value == "fatal"
    assert exc.category.value == "critical"
    assert exc.context == {"x": 1}
    assert "boom" in str(exc)
    assert "20_15_0001" in exc.to_json()


def test_system_fatal_exception():
    original = ValueError("root")
    exc = critical.SystemFatalException(
        "system down",
        service="auth",
        error_code_detail="AUTH_001",
        context={"host": "h1"},
        original_exception=original,
    )
    assert exc.message == "system down"
    assert exc.error_code == "20_15_0001"
    assert exc.service == "auth"
    assert exc.error_code_detail == "AUTH_001"
    assert exc.context["service"] == "auth"
    assert exc.context["error_code_detail"] == "AUTH_001"
    assert exc.context["host"] == "h1"
    assert exc.original_exception is original
    assert exc.to_dict()["error_type"] == "SystemFatalException"


def test_data_corruption_exception():
    exc = critical.DataCorruptionException(
        "rows broken",
        table="events",
        constraint="pk_events",
        context={"shard": 3},
    )
    assert exc.table == "events"
    assert exc.constraint == "pk_events"
    assert exc.context["table"] == "events"
    assert exc.context["constraint"] == "pk_events"
    assert exc.context["shard"] == 3


# ---------------------------------------------------------------------------
# core.security.subprocess_runner
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_subprocess(monkeypatch):
    """Provide a fully mocked subprocess stack for the runner."""
    monkeypatch.setattr(sp_runner.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    fake_sp = MagicMock()
    fake_sp.run = MagicMock(return_value=MagicMock(returncode=0))
    fake_sp.check_output = MagicMock(return_value=b"out")
    fake_sp.check_call = MagicMock(return_value=0)
    fake_sp.call = MagicMock(return_value=0)
    fake_sp.Popen = MagicMock(return_value=MagicMock(returncode=0))
    fake_sp.PIPE = -1
    fake_sp.STDOUT = -2
    fake_sp.DEVNULL = -3
    fake_sp.CompletedProcess = subprocess.CompletedProcess
    fake_sp.CalledProcessError = subprocess.CalledProcessError
    fake_sp.TimeoutExpired = subprocess.TimeoutExpired
    fake_sp.SubprocessError = subprocess.SubprocessError
    fake_sp.CREATE_NEW_CONSOLE = 0
    monkeypatch.setattr(sp_runner, "_sp", fake_sp)
    return fake_sp


def test_resolve_cmd_accepts_string(monkeypatch):
    monkeypatch.setattr(sp_runner.shutil, "which", lambda exe: f"/usr/bin/{exe}")
    assert sp_runner._resolve_cmd(("ls",)) == ["/usr/bin/ls"]


def test_resolve_cmd_accepts_list_and_tuple(monkeypatch):
    monkeypatch.setattr(sp_runner.shutil, "which", lambda exe: f"/bin/{exe}")
    assert sp_runner._resolve_cmd([["ls", "-la"]]) == ["/bin/ls", "-la"]
    assert sp_runner._resolve_cmd((("cat", "file"),)) == ["/bin/cat", "file"]


def test_resolve_cmd_empty_and_not_found(monkeypatch):
    monkeypatch.setattr(sp_runner.shutil, "which", lambda exe: None)
    with pytest.raises(ValueError, match="single command argument"):
        sp_runner._resolve_cmd(("a", "b"))
    with pytest.raises(ValueError, match="cannot be empty"):
        sp_runner._resolve_cmd(("",))
    with pytest.raises(FileNotFoundError, match="not found"):
        sp_runner._resolve_cmd(("missing-cmd",))


def test_run_and_callers(monkeypatch, fake_subprocess):
    # basic run with string command
    assert sp_runner.run("ls") is not None
    assert sp_runner.run(["ls", "-la"]) is not None

    # shell=True is rejected for all callers
    with pytest.raises(ValueError, match="shell=True"):
        sp_runner.run("ls", shell=True)
    with pytest.raises(ValueError, match="shell=True"):
        sp_runner.check_output("ls", shell=True)
    with pytest.raises(ValueError, match="shell=True"):
        sp_runner.check_call("ls", shell=True)
    with pytest.raises(ValueError, match="shell=True"):
        sp_runner.call("ls", shell=True)

    # sanity on return values
    assert sp_runner.check_output("ls") == b"out"
    assert sp_runner.check_call("ls") == 0
    assert sp_runner.call("ls") == 0


def test_popen_and_constants():
    # Popen re-export is callable; constants are re-exported.
    assert sp_runner.PIPE == -1
    assert sp_runner.STDOUT == -2
    assert sp_runner.DEVNULL == -3
    assert sp_runner.CompletedProcess is subprocess.CompletedProcess
    assert sp_runner.CalledProcessError is subprocess.CalledProcessError
    assert sp_runner.TimeoutExpired is subprocess.TimeoutExpired
    assert sp_runner.SubprocessError is subprocess.SubprocessError


# ---------------------------------------------------------------------------
# core.logging.level.filter_strategy
# ---------------------------------------------------------------------------
def _make_record(name="mod.a", level=logging.INFO, message="hello world"):
    return logging.LogRecord(name, level, "", 0, message, (), None)


def test_module_filter():
    default_true = fs.ModuleFilter()
    assert default_true.should_log(_make_record()) is True

    default_false = fs.ModuleFilter(default_action=False)
    assert default_false.should_log(_make_record()) is False

    inc = fs.ModuleFilter(include_modules={"mod.a"})
    assert inc.should_log(_make_record()) is True
    assert inc.should_log(_make_record("mod.b")) is False

    exc = fs.ModuleFilter(exclude_modules={"mod.b"})
    assert exc.should_log(_make_record()) is True
    assert exc.should_log(_make_record("mod.b")) is False

    pat = fs.ModuleFilter(include_patterns=[r"^mod\."], exclude_patterns=[r".*\.test$"])
    assert pat.should_log(_make_record("mod.prod")) is True
    assert pat.should_log(_make_record("other")) is False
    assert pat.should_log(_make_record("mod.something.test")) is False


def test_level_filter():
    range_f = fs.LevelFilter(min_level=fs.LogLevel.INFO, max_level=fs.LogLevel.ERROR)
    assert range_f.should_log(_make_record(level=logging.INFO)) is True
    assert range_f.should_log(_make_record(level=logging.WARNING)) is True
    assert range_f.should_log(_make_record(level=logging.CRITICAL)) is False
    assert range_f.should_log(_make_record(level=logging.DEBUG)) is False

    allowed = fs.LevelFilter(allowed_levels={fs.LogLevel.WARNING})
    assert allowed.should_log(_make_record(level=logging.WARNING)) is True
    assert allowed.should_log(_make_record(level=logging.INFO)) is False


def test_keyword_filter():
    # include keywords
    inc = fs.KeywordFilter(include_keywords={"hello"})
    assert inc.should_log(_make_record(message="hello world")) is True
    assert inc.should_log(_make_record(message="goodbye")) is False

    # exclude keywords
    exc = fs.KeywordFilter(exclude_keywords={"noise"})
    assert exc.should_log(_make_record(message="this is noise")) is False
    assert exc.should_log(_make_record(message="this is fine")) is True

    # case sensitivity
    ci = fs.KeywordFilter(include_keywords={"ALERT"})
    assert ci.should_log(_make_record(message="Alert message")) is True

    cs = fs.KeywordFilter(include_keywords={"ALERT"}, case_sensitive=True)
    assert cs.should_log(_make_record(message="alert message")) is False
    assert cs.should_log(_make_record(message="ALERT message")) is True

    # patterns
    pat = fs.KeywordFilter(
        include_patterns=[r"\buser\d+"],
        exclude_patterns=[r"\bspam\b"],
    )
    assert pat.should_log(_make_record(message="user42 logged in")) is True
    assert pat.should_log(_make_record(message="some spam here")) is False
    assert pat.should_log(_make_record(message="plain text")) is False


def test_composite_filter(monkeypatch):
    always_true = fs.ModuleFilter(default_action=True)
    always_false = fs.ModuleFilter(default_action=False)

    and_filter = fs.CompositeFilter(filters=[always_true, always_true], operator="AND")
    assert and_filter.should_log(_make_record()) is True

    and_filter.filters.append(always_false)
    assert and_filter.should_log(_make_record()) is False

    or_filter = fs.CompositeFilter(filters=[always_false, always_true], operator="OR")
    assert or_filter.should_log(_make_record()) is True

    empty = fs.CompositeFilter(filters=[])
    assert empty.should_log(_make_record()) is True

    bad = fs.CompositeFilter(filters=[always_true], operator="XOR")
    warn_spy = MagicMock()
    monkeypatch.setattr(fs.logger, "warning", warn_spy)
    assert bad.should_log(_make_record()) is True
    warn_spy.assert_called_once()

    # add/remove
    comp = fs.CompositeFilter(filters=[])
    comp.add_filter(always_true)
    assert comp.filters == [always_true]
    comp.remove_filter(always_true)
    assert comp.filters == []


# ---------------------------------------------------------------------------
# core.workflow_engine
# ---------------------------------------------------------------------------
@pytest.fixture
def fresh_workflows(monkeypatch):
    """Provide an isolated copy of workflow definitions for mutating tests."""
    original_raw = wf._WORKFLOW_DEFINITIONS_RAW
    original_keys = wf._VALID_WF_KEYS
    snapshot = copy.deepcopy(original_raw)
    monkeypatch.setattr(wf, "_WORKFLOW_DEFINITIONS_RAW", snapshot)
    monkeypatch.setattr(wf, "_VALID_WF_KEYS", frozenset(snapshot.keys()))
    yield snapshot


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(wf.asyncio, "sleep", AsyncMock())


@pytest.fixture
def deterministic_random(monkeypatch):
    fake_random = MagicMock()
    fake_random.randint = MagicMock(return_value=50)
    fake_random.random = MagicMock(return_value=0.0)
    monkeypatch.setattr(wf, "_secure_random", fake_random)


@pytest.mark.asyncio
async def test_simulate_workflow_stream_success(no_sleep, deterministic_random):
    events = [e async for e in wf.simulate_workflow_stream("noise")]
    types = [e["type"] for e in events]
    assert types[0] == "workflow_start"
    assert types[-1] == "workflow_done"
    assert "step_start" in types
    assert "step_complete" in types
    assert "step_warn" in types
    done = events[-1]
    assert done["warning_count"] >= 0
    assert done["total_steps"] == 5
    assert "total_ms" in done


@pytest.mark.asyncio
async def test_simulate_unknown_workflow():
    events = [e async for e in wf.simulate_workflow_stream("nope")]
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "nope" in events[0]["msg"]


@pytest.mark.asyncio
async def test_simulate_invalid_steps(fresh_workflows, no_sleep, monkeypatch):
    # steps not a list
    wf._WORKFLOW_DEFINITIONS_RAW["bad"] = {"name": "bad", "steps": "notalist"}
    wf._VALID_WF_KEYS = frozenset(["bad"])
    events = [e async for e in wf.simulate_workflow_stream("bad")]
    assert any(e["type"] == "error" for e in events)

    # empty steps
    wf._WORKFLOW_DEFINITIONS_RAW["empty"] = {"name": "empty", "steps": []}
    wf._VALID_WF_KEYS = frozenset(["empty"])
    events = [e async for e in wf.simulate_workflow_stream("empty")]
    assert any(e["type"] == "error" for e in events)


@pytest.mark.asyncio
async def test_simulate_non_dict_step(fresh_workflows, no_sleep, deterministic_random, monkeypatch):
    wf._WORKFLOW_DEFINITIONS_RAW["weird"] = {
        "name": "weird",
        "steps": ["not-a-dict"],
    }
    wf._VALID_WF_KEYS = frozenset(["weird"])
    events = [e async for e in wf.simulate_workflow_stream("weird")]
    assert events[0]["type"] == "workflow_start"
    assert any(e["type"] == "step_start" for e in events)


def test_safe_extract_step():
    assert wf._safe_extract_step(None, 0) == ("step-0", "步骤 1", "")
    assert wf._safe_extract_step({}, 3) == ("step-3", "步骤 4", "")
    assert wf._safe_extract_step(
        {"key": "k", "title": "t", "desc": "d"}, 0
    ) == ("k", "t", "d")
    long = {"key": "x" * 200, "title": "x" * 200, "desc": "x" * 300}
    key, title, desc = wf._safe_extract_step(long, 0)
    assert len(key) == 128
    assert len(title) == 128
    assert len(desc) == 256


@pytest.mark.asyncio
async def test_execute_langgraph_workflow_not_available(monkeypatch):
    monkeypatch.setattr(wf, "_langgraph_executor", None)
    result = await wf.execute_langgraph_workflow("w1", {"x": 1})
    assert result == {"error": "LangGraph not available"}


@pytest.mark.asyncio
async def test_execute_langgraph_workflow_success(monkeypatch):
    executor = AsyncMock()
    executor.execute = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(wf, "_langgraph_executor", executor)
    monkeypatch.setattr(wf, "Workflow", MagicMock(), raising=False)
    monkeypatch.setattr(wf, "LLMNode", MagicMock(), raising=False)
    result = await wf.execute_langgraph_workflow("w1", {"x": 1})
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_execute_langgraph_workflow_failure(monkeypatch):
    executor = AsyncMock()
    executor.execute = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(wf, "_langgraph_executor", executor)
    monkeypatch.setattr(wf, "Workflow", MagicMock(), raising=False)
    monkeypatch.setattr(wf, "LLMNode", MagicMock(), raising=False)
    result = await wf.execute_langgraph_workflow("w1", {"x": 1})
    assert "error" in result


def test_get_workflow_definitions():
    defs = wf.get_workflow_definitions()
    assert "collect" in defs
    # returned value should be a deep copy
    defs["collect"]["name"] = "changed"
    assert wf.get_workflow_definitions()["collect"]["name"] != "changed"


def test_workflow_crud(fresh_workflows):
    new_def = {
        "name": "Custom",
        "steps": [
            {"key": "c-0", "title": "First", "desc": "d"},
            {"key": "c-1", "title": "Second"},
        ],
    }
    created = wf.create_workflow_definition("custom", new_def)
    assert created["name"] == "Custom"
    assert created["nodes"] == 2
    assert wf.is_valid_workflow_key("custom") is True
    assert "custom" in wf.get_valid_workflow_keys()

    # duplicate create
    with pytest.raises(ValueError, match="已存在"):
        wf.create_workflow_definition("custom", new_def)

    updated = wf.update_workflow_definition(
        "custom",
        {
            "name": "CustomUpdated",
            "steps": [{"key": "c-0", "title": "Only"}],
        },
    )
    assert updated["name"] == "CustomUpdated"
    assert updated["nodes"] == 1

    # update missing
    with pytest.raises(ValueError, match="不存在"):
        wf.update_workflow_definition("ghost", new_def)

    wf.delete_workflow_definition("custom")
    assert wf.is_valid_workflow_key("custom") is False

    # delete missing
    with pytest.raises(ValueError, match="不存在"):
        wf.delete_workflow_definition("custom")


def test_validate_workflow_definition():
    with pytest.raises(ValueError, match="非空字符串"):
        wf._validate_workflow_definition("", {"name": "x", "steps": [{"key": "k"}]})
    with pytest.raises(ValueError, match="字母、数字"):
        wf._validate_workflow_definition("bad key!", {"name": "x", "steps": [{"key": "k"}]})
    with pytest.raises(ValueError, match="非空列表"):
        wf._validate_workflow_definition("x", {"name": "x", "steps": []})
    with pytest.raises(ValueError, match="字典"):
        wf._validate_workflow_definition("x", {"name": "x", "steps": ["notdict"]})

    safe = wf._validate_workflow_definition("ok", {
        "name": "Ok",
        "steps": [{"key": "s1", "title": "Step", "desc": "desc"}],
    })
    assert safe["name"] == "Ok"
    assert safe["nodes"] == 1
    assert safe["time"] == "N/A"
    assert safe["rate"] == "N/A"


# ---------------------------------------------------------------------------
# core.chat_command_handler
# ---------------------------------------------------------------------------
def test_normalize_and_helpers():
    assert cch._normalize_text("  你好，世界。  ") == "你好,世界."
    # _contains_any lower-cases the keyword but compares against the raw text.
    assert cch._contains_any("hello world", "HELLO") is True
    assert cch._contains_any("Hello World", "bye") is False
    assert cch._extract_target("查看名为 my-pod 的 pod") == "my-pod"
    assert cch._extract_target("pod web-123 的状态") == "web-123"
    assert cch._extract_target("nothing here") == ""


def test_check_malicious():
    blocked = cch._check_malicious("删除所有pod")
    assert blocked is not None
    assert blocked[1] == "禁止删除所有资源"

    high = cch._check_malicious("删除 pod")
    assert high is not None and high[0].value == "high"

    safe = cch._check_malicious("查询状态")
    assert safe is None


def test_classify_action():
    assert cch._classify_action("暂停自动修复")[0] == cch.ActionType.PAUSE
    assert cch._classify_action("查日志")[0] == cch.ActionType.INVESTIGATE
    assert cch._classify_action("继续排查")[0] == cch.ActionType.INVESTIGATE
    assert cch._classify_action("同意执行")[0] == cch.ActionType.APPROVE
    assert cch._classify_action("拒绝")[0] == cch.ActionType.REJECT
    assert cch._classify_action("忽略告警")[0] == cch.ActionType.IGNORE
    assert cch._classify_action("@alice")[0] == cch.ActionType.ASSIGN
    assert cch._classify_action("进展如何")[0] == cch.ActionType.STATUS
    assert cch._classify_action("random gibberish")[0] == cch.ActionType.UNKNOWN


def test_get_user_roles(monkeypatch):
    monkeypatch.setenv("CHAT_COMMAND_ROLES", "alice:admin,oncall;bob:viewer")
    assert cch._get_user_roles("alice") == {"admin", "oncall"}
    assert cch._get_user_roles("bob") == {"viewer"}
    # default fallback + username hints
    assert "admin" in cch._get_user_roles("admin_user")
    assert "oncall" in cch._get_user_roles("oncall_bob")
    assert "sre" in cch._get_user_roles("sre_lead")


def test_parse_chat_command_unverified_and_blocked(monkeypatch):
    # blocked regardless of verification
    blocked = cch.parse_chat_command("删除所有pod", user_id="admin", verified=True)
    assert blocked.action == cch.ActionType.BLOCKED
    assert blocked.allowed is False

    # unverified safe action is rejected
    unverified = cch.parse_chat_command("暂停", user_id="admin", verified=False)
    assert unverified.allowed is False
    assert unverified.risk_level == cch.RiskLevel.HIGH


def test_parse_chat_command_roles(monkeypatch):
    monkeypatch.setenv("CHAT_COMMAND_ROLES", "bob:viewer")
    # viewer cannot PAUSE
    viewer_pause = cch.parse_chat_command("暂停", user_id="bob", verified=True)
    assert viewer_pause.allowed is False

    # admin can PAUSE
    monkeypatch.setenv("CHAT_COMMAND_ROLES", "alice:admin")
    admin_pause = cch.parse_chat_command("暂停", user_id="alice", verified=True)
    assert admin_pause.allowed is True
    assert admin_pause.action == cch.ActionType.PAUSE
    assert admin_pause.risk_level == cch.RiskLevel.LOW


def test_parse_chat_command_scenarios(monkeypatch):
    monkeypatch.setenv("CHAT_COMMAND_ROLES", "alice:admin,oncall,sre")
    base = {"user_id": "alice", "user_name": "Alice", "channel": "slack", "verified": True}

    status = cch.parse_chat_command("现在状态如何", **base)
    assert status.action == cch.ActionType.STATUS
    assert status.allowed is True

    approve = cch.parse_chat_command("同意执行名为 web-1 的操作", **base)
    assert approve.action == cch.ActionType.APPROVE
    assert approve.target == "web-1"

    reject = cch.parse_chat_command("拒绝 pod web-1", **base)
    assert reject.action == cch.ActionType.REJECT
    assert reject.target == "web-1"

    ignore = cch.parse_chat_command("忽略这个告警", **base)
    assert ignore.action == cch.ActionType.IGNORE
    assert ignore.allowed is True

    assign = cch.parse_chat_command("转给 @bob", **base)
    assert assign.action == cch.ActionType.ASSIGN
    assert assign.params.get("assignee") == "bob"

    unknown = cch.parse_chat_command("foobar", **base)
    assert unknown.action == cch.ActionType.UNKNOWN
    assert unknown.allowed is True  # alice has admin role


def test_handle_instruction():
    result = cch.handle_instruction("状态", user_id="admin", verified=True)
    assert result["action"] == "status"
    assert result["allowed"] is True
    assert "risk_level" in result
