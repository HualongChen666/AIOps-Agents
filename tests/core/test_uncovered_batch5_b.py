# -*- coding: utf-8 -*-
"""Targeted coverage tests for core.agent.coding_tools, core.agent.subagent and core.linux_repair."""

import asyncio
import sqlite3
import sys
import uuid
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.agent.coding_tools as coding_tools
import core.agent.subagent as subagent
import core.linux_repair as linux_repair
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core/agent/coding_tools.py
# ---------------------------------------------------------------------------
class TestCodingToolsPaths:
    def test_get_workspace_root_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        assert coding_tools._get_workspace_root() == tmp_path.resolve()

    def test_resolve_allowed_path_relative(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        path = coding_tools._resolve_allowed_path("sub/file.txt")
        assert path == (tmp_path / "sub" / "file.txt").resolve()

    def test_resolve_allowed_path_with_cwd(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "base").mkdir()
        path = coding_tools._resolve_allowed_path("file.txt", cwd="base")
        assert path == (tmp_path / "base" / "file.txt").resolve()

    def test_resolve_allowed_path_outside_workspace(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        outside = tmp_path / ".." / "outside.txt"
        with pytest.raises(ValueError, match="outside workspace"):
            coding_tools._resolve_allowed_path(str(outside.resolve()))


class TestCodingToolsValidateCommandArgs:
    def test_valid_command(self):
        coding_tools._validate_command_args(["ls", "-la", "file"])

    def test_empty_command(self):
        with pytest.raises(ValueError, match="empty command"):
            coding_tools._validate_command_args([])

    def test_disallowed_base_commands(self):
        for base in ["ssh", "curl", "pip", "nc"]:
            with pytest.raises(ValueError, match=f"Command '{base}' is not allowed"):
                coding_tools._validate_command_args([base, "arg"])

    def test_interpreter_flags(self):
        for base, flag in [("bash", "-c"), ("python", "-c"), ("node", "-e")]:
            with pytest.raises(ValueError, match="Interpreter flag"):
                coding_tools._validate_command_args([base, flag, "print(1)"])

    def test_windows_cmd_flags(self):
        with pytest.raises(ValueError, match="cmd /c or /k is not allowed"):
            coding_tools._validate_command_args(["cmd", "/c", "dir"])

    def test_powershell_command_flags(self):
        with pytest.raises(ValueError, match="PowerShell -Command is not allowed"):
            coding_tools._validate_command_args(["powershell", "-command", "echo 1"])

    def test_path_traversal_in_args(self):
        with pytest.raises(ValueError, match="path traversal or absolute path"):
            coding_tools._validate_command_args(["cat", "../passwd"])
        with pytest.raises(ValueError, match="path traversal or absolute path"):
            coding_tools._validate_command_args(["cat", "/etc/passwd"])
        with pytest.raises(ValueError, match="path traversal or absolute path"):
            coding_tools._validate_command_args(["cat", "C:\\Windows"])

    def test_dangerous_metacharacters(self):
        with pytest.raises(ValueError, match="dangerous characters"):
            coding_tools._validate_command_args(["echo", "x;rm"])

    def test_recursive_flags(self):
        with pytest.raises(ValueError, match="Recursive flag"):
            coding_tools._validate_command_args(["ls", "-R"])
        with pytest.raises(ValueError, match="grep -r is not allowed"):
            coding_tools._validate_command_args(["grep", "-r", "x"])

    def test_find_destructive(self):
        for action in ["-delete", "-exec", "-execdir", "-ok", "-okdir"]:
            with pytest.raises(ValueError, match=f"find action '{action}' is not allowed"):
                coding_tools._validate_command_args(["find", "tmp", action])


class TestCodingToolsValidateBashCommand:
    def test_valid_string_command_guard(self, monkeypatch):
        monkeypatch.setattr(coding_tools, "COMMAND_GUARD_AVAILABLE", True)
        monkeypatch.setattr(
            coding_tools, "_analyze_command", lambda cmd: {"risk_level": RiskLevel.LOW}
        )
        args = coding_tools._validate_bash_command("ls -la file")
        assert args == ["ls", "-la", "file"]

    def test_valid_list_command(self):
        args = coding_tools._validate_bash_command(["echo", "hello"])
        assert args == ["echo", "hello"]

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="must be a string or list"):
            coding_tools._validate_bash_command(123)

    def test_empty_command(self):
        with pytest.raises(ValueError, match="empty command"):
            coding_tools._validate_bash_command("")
        with pytest.raises(ValueError, match="empty command"):
            coding_tools._validate_bash_command("   ")

    def test_blocked_by_command_guard(self, monkeypatch):
        monkeypatch.setattr(coding_tools, "COMMAND_GUARD_AVAILABLE", True)
        monkeypatch.setattr(
            coding_tools,
            "_analyze_command",
            lambda cmd: {"risk_level": RiskLevel.BLOCKED, "reason": "blocked"},
        )
        with pytest.raises(ValueError, match="Command blocked by command_guard"):
            coding_tools._validate_bash_command("ls")

    def test_fallback_metacharacters(self, monkeypatch):
        monkeypatch.setattr(coding_tools, "COMMAND_GUARD_AVAILABLE", False)
        monkeypatch.setattr(coding_tools, "_analyze_command", None)
        with pytest.raises(ValueError, match="disallowed shell metacharacters"):
            coding_tools._validate_bash_command("echo;ls")

    def test_fallback_path_traversal(self, monkeypatch):
        monkeypatch.setattr(coding_tools, "COMMAND_GUARD_AVAILABLE", False)
        monkeypatch.setattr(coding_tools, "_analyze_command", None)
        with pytest.raises(ValueError, match="path traversal attempt"):
            coding_tools._validate_bash_command("cat ../file")


class TestCodingToolsCodeTool:
    def test_validate_parameters_unknown(self):
        tool = coding_tools.CodeTool(
            name="bash",
            description="test",
            category=coding_tools.ToolCategory.EXECUTION,
            function=coding_tools._bash,
            required_params=["command"],
            optional_params=["cwd", "timeout"],
        )
        with pytest.raises(ValueError, match="Parameter 'unknown' is not allowed"):
            tool._validate_parameters({"command": "ls", "unknown": "x"})

    def test_validate_parameters_file_path_outside(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        tool = coding_tools.CodeTool(
            name="read_file",
            description="test",
            category=coding_tools.ToolCategory.DIAGNOSTIC,
            function=coding_tools._read_file,
            required_params=["file_path"],
        )
        with pytest.raises(ValueError, match="outside workspace"):
            tool._validate_parameters({"file_path": "../outside.txt"})

    def test_validate_parameters_content_size(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        big = "a" * (coding_tools._MAX_FILE_WRITE_BYTES + 1)
        tool = coding_tools.CodeTool(
            name="write_to_file",
            description="test",
            category=coding_tools.ToolCategory.EXECUTION,
            function=coding_tools._write_to_file,
            required_params=["file_path", "content"],
        )
        with pytest.raises(ValueError, match="exceeds maximum size"):
            tool._validate_parameters({"file_path": "f.txt", "content": big})

    def test_validate_parameters_timeout_range(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        tool = coding_tools.CodeTool(
            name="bash",
            description="test",
            category=coding_tools.ToolCategory.EXECUTION,
            function=coding_tools._bash,
            required_params=["command"],
            optional_params=["timeout"],
        )
        with pytest.raises(ValueError, match="must be between"):
            tool._validate_parameters({"command": "ls", "timeout": 99999})
        with pytest.raises(ValueError, match="must be an integer"):
            tool._validate_parameters({"command": "ls", "timeout": "abc"})

    def test_validate_parameters_varkw(self):
        def func(**kwargs):  # noqa: D103
            return kwargs

        tool = coding_tools.CodeTool(
            name="dyn",
            description="test",
            category=coding_tools.ToolCategory.EXECUTION,
            function=func,
            required_params=[],
        )
        tool._validate_parameters({"anything": "value"})


class TestCodingToolsFunctions:
    def test_bash_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        run = MagicMock(return_value=MagicMock(returncode=0, stdout="ok", stderr=""))
        monkeypatch.setattr(coding_tools.subprocess_runner, "run", run)
        result = coding_tools._bash("echo hello")
        assert result["returncode"] == 0
        assert result["stdout"] == "ok"

    def test_bash_failure(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        run = MagicMock(return_value=MagicMock(returncode=1, stdout="out", stderr="err"))
        monkeypatch.setattr(coding_tools.subprocess_runner, "run", run)
        with pytest.raises(RuntimeError, match="Command failed with exit code 1"):
            coding_tools._bash("false")

    def test_bash_timeout(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        exc = coding_tools.subprocess_runner.TimeoutExpired(
            "cmd", 30, output=b"timed", stderr=b"err"
        )
        monkeypatch.setattr(coding_tools.subprocess_runner, "run", MagicMock(side_effect=exc))
        with pytest.raises(RuntimeError, match="Command timed out after"):
            coding_tools._bash("sleep 5")

    def test_bash_timeout_with_string_stdout(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        exc = coding_tools.subprocess_runner.TimeoutExpired(
            "cmd", 30, output="timed", stderr="err"
        )
        monkeypatch.setattr(coding_tools.subprocess_runner, "run", MagicMock(side_effect=exc))
        with pytest.raises(RuntimeError, match="Command timed out after"):
            coding_tools._bash("sleep 5")

    def test_bash_timeout_clamp(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
        monkeypatch.setattr(coding_tools.subprocess_runner, "run", run)
        coding_tools._bash("ls", timeout=5)
        assert run.call_args.kwargs["timeout"] == 5
        coding_tools._bash("ls", timeout=99999)
        assert run.call_args.kwargs["timeout"] == coding_tools._MAX_BASH_TIMEOUT

    def test_read_file_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
        assert coding_tools._read_file("a.txt") == "hello"

    def test_read_file_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="is not a regular file"):
            coding_tools._read_file("missing.txt")

    def test_read_file_not_regular(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "dir").mkdir()
        with pytest.raises(ValueError, match="is not a regular file"):
            coding_tools._read_file("dir")

    def test_read_file_too_large(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "big.txt").write_bytes(b"x" * (coding_tools._MAX_FILE_READ_BYTES + 1))
        with pytest.raises(ValueError, match="exceeding maximum"):
            coding_tools._read_file("big.txt")

    def test_read_file_unicode_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "bad.txt").write_bytes(b"\xff\xfe")
        with pytest.raises(ValueError, match="not valid UTF-8"):
            coding_tools._read_file("bad.txt")

    def test_read_file_path_checks(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="exceeds maximum length"):
            coding_tools._read_file("x" * 5000)
        with pytest.raises(ValueError, match="contains null bytes"):
            coding_tools._read_file("a\x00b")

    def test_write_to_file_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        result = coding_tools._write_to_file("sub/new.txt", "hello")
        assert result["status"] == "success"
        assert (tmp_path / "sub" / "new.txt").read_text() == "hello"

    def test_write_to_file_too_large(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        big = "a" * (coding_tools._MAX_FILE_WRITE_BYTES + 1)
        with pytest.raises(ValueError, match="Content exceeds maximum size"):
            coding_tools._write_to_file("big.txt", big)

    def test_write_to_file_path_checks(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="exceeds maximum length"):
            coding_tools._write_to_file("x" * 5000, "a")
        with pytest.raises(ValueError, match="contains null bytes"):
            coding_tools._write_to_file("a\x00b", "c")

    def test_edit_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "f.txt").write_text("hello world", encoding="utf-8")
        result = coding_tools._edit("f.txt", "world", "earth")
        assert result["status"] == "success"
        assert (tmp_path / "f.txt").read_text() == "hello earth"

    def test_edit_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="is not a regular file"):
            coding_tools._edit("missing.txt", "a", "b")

    def test_edit_old_string_not_found(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AIOPS_AGENT_WORKSPACE", str(tmp_path))
        (tmp_path / "f.txt").write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError, match="old_string not found"):
            coding_tools._edit("f.txt", "missing", "x")

    def test_edit_empty_old_string(self):
        with pytest.raises(ValueError, match="old_string cannot be empty"):
            coding_tools._edit("f.txt", "", "x")

    def test_edit_too_long_strings(self):
        big = "a" * (coding_tools._MAX_FILE_WRITE_BYTES + 1)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            coding_tools._edit("f.txt", big, "x")
        with pytest.raises(ValueError, match="exceeds maximum size"):
            coding_tools._edit("f.txt", "x", big)

    def test_coding_tool_registry_and_executor(self):
        registry = coding_tools.CodingToolRegistry()
        assert "bash" in registry.tools
        assert "read_file" in registry.tools
        executor = coding_tools.create_coding_tool_executor()
        assert executor is not None
        assert executor.registry is not None


# ---------------------------------------------------------------------------
# core/agent/subagent.py
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_executor(monkeypatch):
    class FakeExecutor:
        execution_mode = "hybrid"
        max_subagent_depth = 3
        dry_run = False

        def __init__(self, *args, **kwargs):
            pass

        def execute_plan(self, *args, **kwargs):
            return {"ok": True}

    monkeypatch.setattr(subagent, "AutonomousExecutor", FakeExecutor)
    return FakeExecutor


class TestSubAgentResult:
    def test_to_dict(self):
        result = subagent.SubAgentResult(
            agent_id="a1", task_id="t1", status="completed", result="x", error=None
        )
        d = result.to_dict()
        assert d["agent_id"] == "a1"
        assert d["status"] == "completed"


class TestAuditSubagent:
    def test_audit_available_success(self, monkeypatch):
        monkeypatch.setattr(subagent, "AUDIT_AVAILABLE", True)
        log = MagicMock()
        monkeypatch.setattr(subagent, "_log_audit_event", log)
        subagent._audit_subagent("a1", "run", "success", {"x": 1})
        log.assert_called_once()

    def test_audit_available_failure(self, monkeypatch):
        monkeypatch.setattr(subagent, "AUDIT_AVAILABLE", True)
        log = MagicMock(side_effect=RuntimeError("audit"))
        monkeypatch.setattr(subagent, "_log_audit_event", log)
        subagent._audit_subagent("a1", "run", "success")

    def test_audit_unavailable(self, monkeypatch):
        monkeypatch.setattr(subagent, "AUDIT_AVAILABLE", False)
        monkeypatch.setattr(subagent, "_log_audit_event", None)
        subagent._audit_subagent("a1", "run", "success")


class TestSubAgent:
    def test_init_defaults(self, fake_executor):
        sa = subagent.SubAgent("agent-1")
        assert sa.agent_id == "agent-1"
        assert sa.role == "worker"
        assert sa.status == subagent.SubAgentStatus.IDLE

    def test_run_success(self, fake_executor):
        sa = subagent.SubAgent("a1", planner=MagicMock(), tool_executor=MagicMock())
        result = sa.run("goal", {}, ["tool"])
        assert result.status == "completed"
        assert result.result == {"ok": True}
        assert result.agent_id == "a1"

    def test_run_failure(self, fake_executor, monkeypatch):
        class FailingExecutor:
            execution_mode = "hybrid"
            max_subagent_depth = 3
            dry_run = False

            def __init__(self, *args, **kwargs):
                pass

            def execute_plan(self, *args, **kwargs):
                raise RuntimeError("boom")

        monkeypatch.setattr(subagent, "AutonomousExecutor", FailingExecutor)
        sa = subagent.SubAgent("a1", planner=MagicMock(), tool_executor=MagicMock())
        result = sa.run("goal", {}, ["tool"])
        assert result.status == "failed"
        assert "boom" in result.error

    def test_run_terminated(self, fake_executor):
        sa = subagent.SubAgent("a1", planner=MagicMock(), tool_executor=MagicMock())
        sa.terminate()
        result = sa.run("goal", {}, ["tool"])
        assert result.status == "terminated"

    def test_terminate_and_is_terminated(self, fake_executor):
        sa = subagent.SubAgent("a1", planner=MagicMock(), tool_executor=MagicMock())
        assert not sa.is_terminated()
        sa.terminate()
        assert sa.is_terminated()

    def test_to_dict(self, fake_executor):
        sa = subagent.SubAgent("a1", role="analyzer", planner=MagicMock(), tool_executor=MagicMock())
        sa.terminate()
        d = sa.to_dict()
        assert d["agent_id"] == "a1"
        assert d["role"] == "analyzer"
        assert d["terminated"] is True


class TestSubAgentDispatcher:
    def test_create_subagent(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        sa = dispatcher.create_subagent(role="worker")
        assert sa.agent_id in dispatcher._subagents
        dispatcher.shutdown(wait=False)

    def test_create_subagent_inherits_config(self, fake_executor):
        sb = MagicMock()
        dispatcher = subagent.SubAgentDispatcher(
            max_workers=1,
            safety_boundary=sb,
            execution_mode="autonomous",
            max_subagent_depth=5,
            dry_run=True,
            default_timeout=10,
        )
        sa = dispatcher.create_subagent(role="tester")
        assert sa.safety_boundary is sb
        assert sa.executor.execution_mode == "autonomous"
        assert sa.executor.max_subagent_depth == 5
        assert sa.executor.dry_run is True
        dispatcher.shutdown(wait=False)

    def test_dispatch_wait_success(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher._executor = MagicMock()
            future = MagicMock()
            future.result.return_value = subagent.SubAgentResult(
                agent_id="a1", task_id="t1", status="completed", result={"ok": True}
            )
            dispatcher._executor.submit.return_value = future
            result = dispatcher.dispatch("goal", {}, ["tool"], wait=True)
            assert result.status == "completed"
        finally:
            dispatcher.shutdown(wait=False)

    def test_dispatch_wait_failure(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher._executor = MagicMock()
            future = MagicMock()
            future.result.side_effect = Exception("timeout")
            dispatcher._executor.submit.return_value = future
            result = dispatcher.dispatch("goal", {}, ["tool"], wait=True)
            assert result.status == "failed"
            assert "timeout" in result.error
        finally:
            dispatcher.shutdown(wait=False)

    def test_dispatch_no_wait(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher._executor = MagicMock()
            future = MagicMock()
            dispatcher._executor.submit.return_value = future
            result = dispatcher.dispatch("goal", {}, ["tool"], wait=False)
            assert result is future
        finally:
            dispatcher.shutdown(wait=False)

    def test_dispatch_batch(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher._executor = MagicMock()
            f_ok = MagicMock()
            f_ok.result.return_value = subagent.SubAgentResult(
                agent_id="a1", task_id="t1", status="completed"
            )
            f_fail = MagicMock()
            f_fail.result.side_effect = Exception("x")
            dispatcher._executor.submit.side_effect = [f_ok, f_fail]
            results = dispatcher.dispatch_batch(
                [{"goal": "g1"}, {"goal": "g2"}], _depth=0
            )
            assert results[0].status == "completed"
            assert results[1].status == "failed"
        finally:
            dispatcher.shutdown(wait=False)

    def test_dispatch_parallel(self, fake_executor, monkeypatch):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher._executor = MagicMock()
            future = MagicMock()
            future.result.return_value = subagent.SubAgentResult(
                agent_id="a1", task_id="t1", status="completed"
            )
            dispatcher._executor.submit.return_value = future
            monkeypatch.setattr(subagent, "as_completed", lambda d: iter(d.keys()))
            results = dispatcher.dispatch_parallel([{"goal": "g1"}], _depth=0)
            assert len(results) == 1
            assert list(results.values())[0].status == "completed"
        finally:
            dispatcher.shutdown(wait=False)

    def test_getters_and_summary(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            sa = dispatcher.create_subagent(agent_id="id1")
            assert dispatcher.get_subagent("id1") is sa
            assert dispatcher.list_subagents() == [sa]
            assert dispatcher.get_result("id1") is None
        finally:
            dispatcher.shutdown(wait=False)

    def test_terminate_subagent_cancel(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            sa = dispatcher.create_subagent(agent_id="id1")
            future = MagicMock()
            future.done.return_value = False
            future.cancel.return_value = True
            dispatcher._futures["id1"] = future
            assert dispatcher.terminate("id1") is True
            assert sa.status == subagent.SubAgentStatus.TERMINATED
            assert dispatcher.get_result("id1").status == "terminated"
        finally:
            dispatcher.shutdown(wait=False)

    def test_terminate_subagent_no_cancel(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher.create_subagent(agent_id="id1")
            future = MagicMock()
            future.done.return_value = True
            future.cancel.return_value = False
            dispatcher._futures["id1"] = future
            assert dispatcher.terminate("id1") is True
        finally:
            dispatcher.shutdown(wait=False)

    def test_terminate_missing(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            assert dispatcher.terminate("missing") is False
        finally:
            dispatcher.shutdown(wait=False)

    def test_get_summary(self, fake_executor):
        dispatcher = subagent.SubAgentDispatcher(max_workers=1)
        try:
            dispatcher.create_subagent(agent_id="a1")
            dispatcher.create_subagent(agent_id="a2")
            dispatcher._results["a1"] = subagent.SubAgentResult(
                agent_id="a1", task_id="t1", status="completed"
            )
            dispatcher._results["a2"] = subagent.SubAgentResult(
                agent_id="a2", task_id="t2", status="failed"
            )
            summary = dispatcher.get_summary()
            assert summary["completed"] == 1
            assert summary["failed"] == 1
            assert summary["success_rate"] == 0.5
        finally:
            dispatcher.shutdown(wait=False)

    def test_create_subagent_dispatcher(self):
        d = subagent.create_subagent_dispatcher(max_workers=1)
        assert isinstance(d, subagent.SubAgentDispatcher)
        d.shutdown(wait=False)

    def test_dispatch_task(self, fake_executor, monkeypatch):
        result = subagent.SubAgentResult(
            agent_id="a1", task_id="t1", status="completed"
        )
        d = MagicMock()
        d.dispatch.return_value = result
        d.shutdown = MagicMock()
        monkeypatch.setattr(subagent, "SubAgentDispatcher", MagicMock(return_value=d))
        out = subagent.dispatch_task("goal", {"x": 1}, ["tool"], role="worker")
        assert out is result


# ---------------------------------------------------------------------------
# core/linux_repair.py
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_repair_state():
    linux_repair.linux_repair_history.clear()
    yield
    linux_repair.linux_repair_history.clear()


@pytest.fixture
def fake_sqlite(monkeypatch):
    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    connect = MagicMock(return_value=conn)
    monkeypatch.setattr("sqlite3.connect", connect)
    return connect, cursor, conn


@pytest.fixture
def fake_asyncssh(monkeypatch):
    saved = sys.modules.get("asyncssh")
    mod = MagicMock()
    conn = MagicMock()
    conn.close = AsyncMock()
    mod.connect = AsyncMock(return_value=conn)
    sys.modules["asyncssh"] = mod
    yield conn
    if saved is not None:
        sys.modules["asyncssh"] = saved
    else:
        sys.modules.pop("asyncssh", None)


class TestLinuxRepairSafeRecordAudit:
    async def test_safe_record_audit_success(self, monkeypatch):
        record = MagicMock()
        monkeypatch.setattr(linux_repair, "record_audit", record)
        await linux_repair._safe_record_audit("h", "cmd", "low")
        record.assert_called_once()

    async def test_safe_record_audit_failure(self, monkeypatch):
        record = MagicMock(side_effect=RuntimeError("audit"))
        monkeypatch.setattr(linux_repair, "record_audit", record)
        await linux_repair._safe_record_audit("h", "cmd", "low")


class TestLinuxRepairFindHostConfig:
    def test_empty_name(self, monkeypatch):
        assert linux_repair._find_host_config("") is None

    def test_dict_hosts(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "LINUX_HOSTS", {"hosts": [{"name": "h1", "host": "1.2.3.4"}]})
        assert linux_repair._find_host_config("h1")["host"] == "1.2.3.4"

    def test_list_hosts(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "LINUX_HOSTS", [{"name": "h2", "host": "2.2.2.2"}])
        assert linux_repair._find_host_config("h2")["host"] == "2.2.2.2"

    def test_default(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "LINUX_HOSTS", {"hosts": []})
        assert linux_repair._find_host_config("h3") == {"name": "h3", "host": "h3"}


class TestLinuxRepairRecordSqlite:
    def test_bool_success(self, fake_sqlite):
        assert linux_repair._record_to_sqlite_sync(True) is True

    def test_dict_success(self, fake_sqlite):
        record = {"success": True, "host": "h", "script_key": "k", "rule_name": "r", "params": {"p": 1}, "output": "o"}
        assert linux_repair._record_to_sqlite_sync(record) is True

    def test_dict_bad_params(self, fake_sqlite):
        record = {"success": True, "host": "h", "script_key": "k", "rule_name": "r", "params": "bad", "output": "o"}
        assert linux_repair._record_to_sqlite_sync(record) is True

    def test_failure(self, monkeypatch):
        monkeypatch.setattr("sqlite3.connect", MagicMock(side_effect=Exception("db")))
        assert linux_repair._record_to_sqlite_sync(True) is False


class TestLinuxRepairSanitizeParam:
    def test_generic_sanitization(self):
        assert linux_repair._sanitize_param("key", "a;b") == "ab"
        assert len(linux_repair._sanitize_param("key", "a" * 200)) == linux_repair._PARAM_MAX_LEN

    def test_pid_valid(self):
        assert linux_repair._sanitize_param("pid", "12345") == "12345"

    def test_pid_invalid(self):
        with pytest.raises(ValueError, match="必须为纯数字"):
            linux_repair._sanitize_param("pid", "abc")

    def test_pid_out_of_range(self):
        with pytest.raises(ValueError, match="必须在"):
            linux_repair._sanitize_param("pid", "999999999")
        with pytest.raises(ValueError, match="必须在"):
            linux_repair._sanitize_param("pid", "0")

    def test_pid_reserved(self):
        with pytest.raises(ValueError, match="禁止操作 PID"):
            linux_repair._sanitize_param("pid", "5")

    def test_pid_protected(self, monkeypatch):
        monkeypatch.setattr("core.command_guard.get_protected_pids", lambda: {12345})
        with pytest.raises(ValueError, match="禁止操作 PID"):
            linux_repair._sanitize_param("pid", "12345")

    def test_service_name_valid(self):
        assert linux_repair._sanitize_param("service_name", "nginx.service") == "nginx.service"

    def test_service_name_invalid(self):
        with pytest.raises(ValueError, match="非法字符"):
            linux_repair._sanitize_param("service_name", "nginx rm")
        with pytest.raises(ValueError, match="路径遍历"):
            linux_repair._sanitize_param("service_name", "nginx..service")


class TestLinuxRepairHelpers:
    def test_validate_script_key(self):
        assert linux_repair._validate_script_key("clear_tmp") is not None
        assert linux_repair._validate_script_key("missing") is None

    def test_prepare_safe_params(self):
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["restart_service"]
        params, error = linux_repair._prepare_safe_params({"service_name": "nginx"}, script)
        assert error is None
        assert params["service_name"] == "nginx"

        _, error = linux_repair._prepare_safe_params({}, script)
        assert "缺少参数" in error

        _, error = linux_repair._prepare_safe_params({"service_name": "bad bad"}, script)
        assert error is not None

    def test_render_command(self):
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["restart_service"]
        result = linux_repair._render_command(script, {"service_name": "nginx"})
        assert "nginx" in result


class TestLinuxRepairRiskHandlers:
    async def test_handle_blocked_risk(self, monkeypatch):
        record = AsyncMock()
        monkeypatch.setattr(linux_repair, "_safe_record_audit", record)
        result = await linux_repair._handle_blocked_risk("h", "cmd", "blocked", "bad")
        assert result["blocked"] is True
        assert "bad" in result["error"]

    async def test_handle_high_risk_approval(self, monkeypatch):
        monkeypatch.setattr("core.approval_store.upsert_approval", MagicMock())
        monkeypatch.setattr("core.db_engine.upsert_pending_approval", MagicMock())
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["kill_process"]
        result = await linux_repair._handle_high_risk_approval(
            "h", "kill_process", script, "cmd", {"reason": "danger"}, "high", {"pid": "12345"}
        )
        assert result["pending_approval"] is True
        assert "alert_id" in result

    async def test_handle_high_risk_db_failure(self, monkeypatch):
        monkeypatch.setattr("core.approval_store.upsert_approval", MagicMock())
        monkeypatch.setattr(
            "core.db_engine.upsert_pending_approval",
            MagicMock(side_effect=Exception("db")),
        )
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["kill_process"]
        result = await linux_repair._handle_high_risk_approval(
            "h", "kill_process", script, "cmd", {"reason": "danger"}, "high", {"pid": "12345"}
        )
        assert result["pending_approval"] is True


class TestLinuxRepairSSH:
    async def test_run_ssh_command_success_with_password(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(return_value=MagicMock(stdout="ok", stderr="", exit_status=0))
        result = await linux_repair._run_ssh_command("h", "cmd", username="root", password="p")
        assert result["success"] is True
        assert result["output"] == "ok"

    async def test_run_ssh_command_nonzero(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(return_value=MagicMock(stdout="out", stderr="err", exit_status=1))
        result = await linux_repair._run_ssh_command("h", "cmd")
        assert result["success"] is False
        assert "err" in result["error"]

    async def test_run_ssh_command_timeout(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(side_effect=asyncio.TimeoutError())
        result = await linux_repair._run_ssh_command("h", "cmd")
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    async def test_run_ssh_command_connection_error(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(side_effect=ConnectionError("down"))
        result = await linux_repair._run_ssh_command("h", "cmd")
        assert result["success"] is False
        assert "Connection error" in result["error"]

    async def test_run_ssh_command_generic_exception(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(side_effect=RuntimeError("boom"))
        result = await linux_repair._run_ssh_command("h", "cmd")
        assert result["success"] is False

    async def test_run_ssh_command_close_exception(self, fake_asyncssh):
        fake_asyncssh.run = AsyncMock(return_value=MagicMock(stdout="ok", stderr="", exit_status=0))
        fake_asyncssh.close = AsyncMock(side_effect=RuntimeError("close"))
        result = await linux_repair._run_ssh_command("h", "cmd")
        assert result["success"] is True

    def test_normalize_ssh_output(self):
        assert linux_repair._normalize_ssh_output(None) == ""
        assert linux_repair._normalize_ssh_output("text") == "text"
        assert linux_repair._normalize_ssh_output(b"bytes") == "bytes"
        assert linux_repair._normalize_ssh_output(123) == "123"

    def test_is_execution_success(self):
        assert linux_repair._is_execution_success("ok") is True
        assert linux_repair._is_execution_success("") is False
        assert linux_repair._is_execution_success("TIMEOUT") is False
        assert linux_repair._is_execution_success("ERROR: x") is False

    async def test_execute_ssh_command(self, monkeypatch):
        monkeypatch.setattr(
            linux_repair,
            "_run_ssh_command",
            AsyncMock(return_value={"success": True, "output": b"ok"}),
        )
        output, success = await linux_repair._execute_ssh_command({"host": "h", "username": "root"}, "cmd")
        assert success is True
        assert output == "ok"

    async def test_execute_ssh_command_exception(self, monkeypatch):
        monkeypatch.setattr(
            linux_repair,
            "_run_ssh_command",
            AsyncMock(side_effect=Exception("ssh"))
        )
        output, success = await linux_repair._execute_ssh_command({"host": "h"}, "cmd")
        assert success is False
        assert "ssh" in output


class TestLinuxRepairValidateAndBuild:
    def test_validate_repair_request(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "LINUX_HOSTS", {"hosts": []})
        host, script, error = linux_repair._validate_repair_request("h", "clear_tmp", {})
        assert error is None
        assert script["name"] == "清理临时文件"

        _, _, error = linux_repair._validate_repair_request("h", "missing", {})
        assert "Script not found" in error

    def test_build_repair_command(self):
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["restart_service"]
        cmd = linux_repair._build_repair_command(script, {"service_name": "nginx"})
        assert "nginx" in cmd

    def test_normalize_risk_level(self):
        assert linux_repair._normalize_risk_level({"risk_level": RiskLevel.HIGH})[0] == RiskLevel.HIGH
        assert linux_repair._normalize_risk_level({"risk_level": "low"})[0] == RiskLevel.LOW
        assert linux_repair._normalize_risk_level({"risk_level": "unknown"})[0] == RiskLevel.LOW
        assert linux_repair._normalize_risk_level({"risk_level": "low", "allowed": False})[0] == RiskLevel.BLOCKED


class TestLinuxRepairExecute:
    async def test_execute_repair_with_risk_check_blocked(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "_handle_blocked_risk", AsyncMock(return_value={"blocked": True}))
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["clear_tmp"]
        result = await linux_repair._execute_repair_with_risk_check(
            {}, "cmd", "h", "clear_tmp", script, {"risk_level": RiskLevel.BLOCKED}, {}
        )
        assert result["blocked"] is True

    async def test_execute_repair_with_risk_check_high(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "_handle_high_risk_approval", AsyncMock(return_value={"pending_approval": True}))
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["kill_process"]
        result = await linux_repair._execute_repair_with_risk_check(
            {}, "cmd", "h", "kill_process", script, {"risk_level": RiskLevel.HIGH}, {"pid": "123"}
        )
        assert result["pending_approval"] is True

    async def test_execute_repair_with_risk_check_low(self, monkeypatch, fake_sqlite):
        monkeypatch.setattr(
            linux_repair,
            "_execute_ssh_command",
            AsyncMock(return_value=("ok", True)),
        )
        monkeypatch.setattr(linux_repair, "_safe_record_audit", AsyncMock())
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["clear_tmp"]
        result = await linux_repair._execute_repair_with_risk_check(
            {"host": "h"}, "cmd", "h", "clear_tmp", script, {"risk_level": RiskLevel.LOW}, {}
        )
        assert result["success"] is True
        assert result["output"] == "ok"

    async def test_execute_repair_low_failure(self, monkeypatch, fake_sqlite):
        monkeypatch.setattr(
            linux_repair,
            "_execute_ssh_command",
            AsyncMock(return_value=("fail", False)),
        )
        monkeypatch.setattr(linux_repair, "_safe_record_audit", AsyncMock())
        script = linux_repair._LINUX_REPAIR_SCRIPTS_RAW["clear_tmp"]
        result = await linux_repair._execute_repair_with_risk_check(
            {"host": "h"}, "cmd", "h", "clear_tmp", script, {"risk_level": RiskLevel.LOW}, {}
        )
        assert result["success"] is False

    async def test_execute_linux_repair_validation_error(self):
        result = await linux_repair.execute_linux_repair("h", "missing")
        assert result["success"] is False
        assert "Script not found" in result["error"]

    async def test_execute_linux_repair_full(self, monkeypatch, fake_sqlite):
        monkeypatch.setattr(linux_repair, "LINUX_HOSTS", {"hosts": []})
        monkeypatch.setattr(
            "core.command_guard.analyze_command",
            lambda cmd: {"risk_level": RiskLevel.LOW},
        )
        monkeypatch.setattr(
            linux_repair,
            "_execute_repair_with_risk_check",
            AsyncMock(return_value={"success": True}),
        )
        result = await linux_repair.execute_linux_repair("h", "clear_tmp", {})
        assert result["success"] is True

    async def test_execute_linux_repair_exception(self, monkeypatch):
        monkeypatch.setattr(linux_repair, "analyze_command", lambda cmd: {"risk_level": RiskLevel.LOW})
        monkeypatch.setattr(
            linux_repair,
            "_execute_repair_with_risk_check",
            AsyncMock(side_effect=Exception("boom")),
        )
        result = await linux_repair.execute_linux_repair("h", "clear_tmp", {})
        assert result["success"] is False
        assert "boom" in result["error"]


class TestLinuxRepairQueries:
    def test_get_linux_repair_scripts(self):
        scripts = linux_repair.get_linux_repair_scripts()
        assert "clear_tmp" in scripts

    def test_get_linux_repair_history_and_clear(self):
        linux_repair.linux_repair_history.append({"id": "1"})
        linux_repair.linux_repair_history.append({"id": "2"})
        assert len(linux_repair.get_linux_repair_history(limit=1)) == 1
        count = linux_repair.clear_linux_repair_history()
        assert count == 2
        assert len(linux_repair.linux_repair_history) == 0
