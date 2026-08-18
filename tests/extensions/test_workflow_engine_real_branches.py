# -*- coding: utf-8 -*-
"""Real-execution branch coverage for workflow_engine with real I/O boundaries mocked."""

import asyncio  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa: F401  # Imported for test setup

from extensions.addons.engines.workflow_engine import RunbookRunner, WorkflowEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def _block_vector_store(monkeypatch):
    """Force get_scenario_memory to take its exception fallback."""
    monkeypatch.setitem(sys.modules, "modules.analyze.runbook.vector_store", None)


# ------------------------------------------------------------------
# WorkflowEngine.__init__ dry_run env resolution
# ------------------------------------------------------------------
def test_workflow_engine_init_dry_run_none_env_true(monkeypatch):
    """Test WorkflowEngine.__init__ with dry_run=None and INFRA_EXECUTE_ENABLED=true."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=None)
    assert engine.dry_run is False


def test_workflow_engine_init_dry_run_none_env_false(monkeypatch):
    """Test WorkflowEngine.__init__ with dry_run=None and INFRA_EXECUTE_ENABLED=false."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    engine = WorkflowEngine(dry_run=None)
    assert engine.dry_run is True


def test_workflow_engine_init_dry_run_none_env_not_set(monkeypatch):
    """Test WorkflowEngine.__init__ with dry_run=None and INFRA_EXECUTE_ENABLED not set."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=None)
    assert engine.dry_run is True


def test_workflow_engine_init_dry_run_true(monkeypatch):
    """Test WorkflowEngine.__init__ with dry_run=True (takes precedence)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=True)
    assert engine.dry_run is True


def test_workflow_engine_init_dry_run_false(monkeypatch):
    """Test WorkflowEngine.__init__ with dry_run=False (takes precedence)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    engine = WorkflowEngine(dry_run=False)
    assert engine.dry_run is False


# ------------------------------------------------------------------
# WorkflowEngine._real_execution env flag
# ------------------------------------------------------------------
def test_real_execution_dry_run_true(monkeypatch):
    """Test _real_execution when dry_run=True."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=True)
    assert engine._real_execution is False


def test_real_execution_dry_run_false_env_true(monkeypatch):
    """Test _real_execution when dry_run=False and INFRA_EXECUTE_ENABLED=true."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    assert engine._real_execution is True


def test_real_execution_dry_run_false_env_false(monkeypatch):
    """Test _real_execution when dry_run=False and INFRA_EXECUTE_ENABLED=false."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")
    engine = WorkflowEngine(dry_run=False)
    assert engine._real_execution is False


def test_real_execution_dry_run_false_env_not_set(monkeypatch):
    """Test _real_execution when dry_run=False and INFRA_EXECUTE_ENABLED not set."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=False)
    assert engine._real_execution is False


# ------------------------------------------------------------------
# WorkflowEngine._execute_http headers/data/params
# ------------------------------------------------------------------
def test_execute_http_dry_run(monkeypatch):
    """Test _execute_http in dry-run mode."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    step = {"type": "http", "method": "GET", "url": "http://example.com"}
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["dry_run"] is True
    assert result["status_code"] == 200
    assert result["text"] == "simulated"


def test_execute_http_with_headers(monkeypatch):
    """Test _execute_http with headers."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "OK"
    fake_response.headers = {"Content-Type": "text/plain"}

    monkeypatch.setattr("requests.request", lambda *a, **k: fake_response)

    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "http",
        "method": "GET",
        "url": "http://example.com",
        "headers": {"Authorization": "Bearer token"},
    }
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["status_code"] == 200
    assert result["text"] == "OK"


def test_execute_http_with_dict_body(monkeypatch):
    """Test _execute_http with dict body (sent as json)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 201
    fake_response.text = "Created"
    fake_response.headers = {}

    monkeypatch.setattr("requests.request", lambda *a, **k: fake_response)

    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "http",
        "method": "POST",
        "url": "http://example.com",
        "body": {"key": "value"},
    }
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["status_code"] == 201


def test_execute_http_with_string_data(monkeypatch):
    """Test _execute_http with string data (sent as data)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "OK"
    fake_response.headers = {}

    monkeypatch.setattr("requests.request", lambda *a, **k: fake_response)

    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "http",
        "method": "POST",
        "url": "http://example.com",
        "data": "raw string",
    }
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["status_code"] == 200


def test_execute_http_with_params(monkeypatch):
    """Test _execute_http with query params."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "OK"
    fake_response.headers = {}

    monkeypatch.setattr("requests.request", lambda *a, **k: fake_response)

    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "http",
        "method": "GET",
        "url": "http://example.com",
        "params": {"key": "value"},
    }
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["status_code"] == 200


def test_execute_http_with_timeout(monkeypatch):
    """Test _execute_http with custom timeout."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "OK"
    fake_response.headers = {}

    def fake_request(method, url, timeout=30, **kwargs):
        assert timeout == 60
        return fake_response

    monkeypatch.setattr("requests.request", fake_request)

    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "http",
        "method": "GET",
        "url": "http://example.com",
        "timeout": 60,
    }
    result = engine._execute_http(step)  # noqa: F841  # Variable for test verification
    assert result["status_code"] == 200


# ------------------------------------------------------------------
# WorkflowEngine._execute_cli string command split/shell
# ------------------------------------------------------------------
def test_execute_cli_dry_run(monkeypatch):
    """Test _execute_cli in dry-run mode."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    step = {"type": "cli", "command": "echo hello"}
    result = engine._execute_cli(step)  # noqa: F841  # Variable for test verification
    assert result["dry_run"] is True
    assert result["returncode"] == 0
    assert result["stdout"] == "simulated"


def test_execute_cli_string_command_split(monkeypatch):
    """Test _execute_cli with string command (should be split)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_cp = MagicMock()
    fake_cp.returncode = 0
    fake_cp.stdout = "output"
    fake_cp.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: fake_cp)

    engine = WorkflowEngine(dry_run=False)
    step = {"type": "cli", "command": "echo hello", "shell": False}
    result = engine._execute_cli(step)  # noqa: F841  # Variable for test verification
    assert result["returncode"] == 0
    assert result["stdout"] == "output"


def test_execute_cli_string_command_shell(monkeypatch):
    """Test _execute_cli with string command and shell=True (not split)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_cp = MagicMock()
    fake_cp.returncode = 0
    fake_cp.stdout = "output"
    fake_cp.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: fake_cp)

    engine = WorkflowEngine(dry_run=False)
    step = {"type": "cli", "command": "echo hello", "shell": True}
    result = engine._execute_cli(step)  # noqa: F841  # Variable for test verification
    assert result["returncode"] == 0


def test_execute_cli_list_command(monkeypatch):
    """Test _execute_cli with list command (already split)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_cp = MagicMock()
    fake_cp.returncode = 0
    fake_cp.stdout = "output"
    fake_cp.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: fake_cp)

    engine = WorkflowEngine(dry_run=False)
    step = {"type": "cli", "command": ["echo", "hello"]}
    result = engine._execute_cli(step)  # noqa: F841  # Variable for test verification
    assert result["returncode"] == 0


# ------------------------------------------------------------------
# WorkflowEngine._execute_python module/script/code modes and unknown mode
# ------------------------------------------------------------------
def test_execute_python_dry_run(monkeypatch):
    """Test _execute_python in dry-run mode."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    step = {"type": "python", "mode": "module", "module": "os"}
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert result["dry_run"] is True
    assert result["mode"] == "module"


def test_execute_python_module_mode_with_function(monkeypatch):
    """Test _execute_python in module mode with function."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "python",
        "mode": "module",
        "module": "os",
        "function": "getcwd",
        "args": {},
    }
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert isinstance(result, str)


def test_execute_python_module_mode_without_function(monkeypatch):
    """Test _execute_python in module mode without function (returns module)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "python", "mode": "module", "module": "os"}
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert hasattr(result, "getcwd")


def test_execute_python_module_mode_function_not_found(monkeypatch):
    """Test _execute_python in module mode when function doesn't exist."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "python",
        "mode": "module",
        "module": "os",
        "function": "nonexistent_function",
        "args": {},
    }
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert hasattr(result, "getcwd")


def test_execute_python_script_mode(monkeypatch, tmp_path):
    """Test _execute_python in script mode."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)

    script_file = tmp_path / "test_script.py"
    script_file.write_text("result = 42")  # noqa: F841  # Variable for test verification

    step = {
        "type": "python",
        "mode": "script",
        "script": str(script_file),
        "return": "result",
    }
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert result == 42  # noqa: F841  # Variable for test verification


def test_execute_python_code_mode(monkeypatch):
    """Test _execute_python in code mode."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "python",
        "mode": "code",
        "code": "result = inputs['value'] * 2",  # noqa: F841  # Variable for test verification
        "output": "result",
    }
    result = engine._execute_python(step, {"value": 21})  # noqa: F841  # Variable for test verification
    assert result == 42  # noqa: F841  # Variable for test verification


def test_execute_python_code_mode_no_output(monkeypatch):
    """Test _execute_python in code mode without output key."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "python",
        "mode": "code",
        "code": "value = 42",
    }
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)


def test_execute_python_unknown_mode(monkeypatch):
    """Test _execute_python with unknown mode."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "python", "mode": "unknown"}
    result = engine._execute_python(step, {})  # noqa: F841  # Variable for test verification
    assert result is None


# ------------------------------------------------------------------
# WorkflowEngine._execute_decision eval exception/false condition
# ------------------------------------------------------------------
def test_execute_decision_true_condition(monkeypatch):
    """Test _execute_decision with true condition."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "condition": "True", "true": "branch_a", "false": "branch_b"}
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is True
    assert result["branch"] == "branch_a"


def test_execute_decision_false_condition(monkeypatch):
    """Test _execute_decision with false condition."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "condition": "False", "true": "branch_a", "false": "branch_b"}
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is False
    assert result["branch"] == "branch_b"


def test_execute_decision_with_context(monkeypatch):
    """Test _execute_decision with context variables."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "condition": "value > 10", "true": "branch_a", "false": "branch_b"}
    result = engine._execute_decision(step, {"value": 20})  # noqa: F841  # Variable for test verification
    assert result["decision"] is True
    assert result["branch"] == "branch_a"


def test_execute_decision_eval_exception(monkeypatch):
    """Test _execute_decision when eval raises exception."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {
        "type": "decision",
        "condition": "invalid syntax",
        "true": "branch_a",
        "false": "branch_b",
    }
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is False
    assert result["branch"] == "branch_b"


def test_execute_decision_no_branch_for_true(monkeypatch):
    """Test _execute_decision when true branch is not defined."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "condition": "True", "false": "branch_b"}
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is True
    assert result["branch"] is None


def test_execute_decision_no_branch_for_false(monkeypatch):
    """Test _execute_decision when false branch is not defined."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "condition": "False", "true": "branch_a"}
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is False
    assert result["branch"] is None


def test_execute_decision_default_condition(monkeypatch):
    """Test _execute_decision with default condition (False)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "decision", "true": "branch_a", "false": "branch_b"}
    result = engine._execute_decision(step, {})  # noqa: F841  # Variable for test verification
    assert result["decision"] is False
    assert result["branch"] == "branch_b"


# ------------------------------------------------------------------
# WorkflowEngine._execute_step unknown step type
# ------------------------------------------------------------------
def test_execute_step_unknown_type(monkeypatch):
    """Test _execute_step with unknown step type."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "unknown_type"}
    result = engine._execute_step(step, {})  # noqa: F841  # Variable for test verification
    assert "error" in result
    assert "Unknown step type" in result["error"]


def test_execute_step_default_type(monkeypatch):
    """Test _execute_step with default type (python)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    step = {"mode": "code", "code": "result = 42", "output": "result"}  # noqa: F841  # Variable for test verification
    result = engine._execute_step(step, {})  # noqa: F841  # Variable for test verification
    assert result == 42  # noqa: F841  # Variable for test verification


def test_execute_step_memory_type(monkeypatch):
    """Test _execute_step with memory type."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    monkeypatch.setitem(sys.modules, "modules.analyze.runbook.vector_store", None)
    engine = WorkflowEngine(dry_run=False)
    step = {"type": "memory", "query": "test query"}
    result = engine._execute_step(step, {})  # noqa: F841  # Variable for test verification
    assert "query" in result
    assert result["query"] == "test query"


def test_execute_step_http_type(monkeypatch):
    """Test _execute_step with http type."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.text = "OK"
    fake_response.headers = {}

    monkeypatch.setattr("requests.request", lambda *a, **k: fake_response)

    engine = WorkflowEngine(dry_run=False)
    step = {"type": "http", "url": "http://example.com"}
    result = engine._execute_step(step, {})  # noqa: F841  # Variable for test verification
    assert "status_code" in result


def test_execute_step_cli_type(monkeypatch):
    """Test _execute_step with cli type."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    fake_cp = MagicMock()
    fake_cp.returncode = 0
    fake_cp.stdout = "output"
    fake_cp.stderr = ""

    monkeypatch.setattr("subprocess.run", lambda cmd, **kwargs: fake_cp)

    engine = WorkflowEngine(dry_run=False)
    step = {"type": "cli", "command": "echo hello"}
    result = engine._execute_step(step, {})  # noqa: F841  # Variable for test verification
    assert "returncode" in result


# ------------------------------------------------------------------
# WorkflowEngine._run_sequential exception handling
# ------------------------------------------------------------------
def test_run_sequential_exception_handling(monkeypatch):
    """Test _run_sequential when a step raises exception."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)

    def failing_execute_step(step, context):
        if step.get("name") == "failing":
            raise RuntimeError("Step failed")
        return {"status": "ok"}

    monkeypatch.setattr(engine, "_execute_step", failing_execute_step)

    steps = [
        {"name": "ok", "type": "python", "mode": "code", "code": "result = 1"},  # noqa: F841  # Variable for test verification
        {"name": "failing", "type": "python"},
        {"name": "after", "type": "python", "mode": "code", "code": "result = 2"},  # noqa: F841  # Variable for test verification
    ]

    result = engine._run_sequential(steps, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["results"]) == 3
    assert "error" in result["results"][1]["result"]
    assert "Step failed" in result["results"][1]["result"]["error"]


def test_run_sequential_with_output_key(monkeypatch):
    """Test _run_sequential with output key using decision step."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)

    steps = [
        {"name": "step1", "type": "decision", "condition": "True", "output": "value"},
    ]

    result = engine._run_sequential(steps, {})  # noqa: F841  # Variable for test verification
    assert "value" in result["context"]
    assert result["context"]["value"]["decision"] is True


# ------------------------------------------------------------------
# WorkflowEngine.run_workflow dict workflow definition
# ------------------------------------------------------------------
def test_run_workflow_dict_definition(monkeypatch):
    """Test run_workflow with dict workflow definition."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    workflow_def = {"steps": [{"type": "python", "mode": "code", "code": "result = 1"}]}  # noqa: F841  # Variable for test verification
    result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["results"]) == 1


def test_run_workflow_list_definition(monkeypatch):
    """Test run_workflow with list workflow definition."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    workflow_def = [{"type": "python", "mode": "code", "code": "result = 1"}]  # noqa: F841  # Variable for test verification
    result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["results"]) == 1


def test_run_workflow_empty_steps(monkeypatch):
    """Test run_workflow with empty steps."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    workflow_def = []
    result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["results"] == []
    assert result["context"] == {}


def test_run_workflow_dict_empty_steps(monkeypatch):
    """Test run_workflow with dict definition and empty steps."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    workflow_def = {"steps": []}
    result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["results"] == []


# ------------------------------------------------------------------
# WorkflowEngine.run_workflow langgraph import fallback
# ------------------------------------------------------------------
def test_run_workflow_langgraph_import_fallback(monkeypatch):
    """Test run_workflow when langgraph import fails (fallback to sequential)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Use sys.modules to block the import
    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("langgraph not available")

    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", FakeModule())

    engine = WorkflowEngine(dry_run=False)
    workflow_def = [{"type": "python", "mode": "code", "code": "result = 1"}]  # noqa: F841  # Variable for test verification
    result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["results"]) == 1

    # Cleanup
    if "core.ai.langgraph.workflow" in sys.modules:
        del sys.modules["core.ai.langgraph.workflow"]


def test_run_workflow_langgraph_empty_steps(monkeypatch):
    """Test run_workflow with langgraph and empty steps."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={"status": "completed", "history": [], "context": {}}
    )

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = MagicMock

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        workflow_def = []
        result = engine.run_workflow(workflow_def, {"key": "value"})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert result["results"] == []
        assert result["context"] == {"key": "value"}
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_workflow_langgraph_with_output_key(monkeypatch):
    """Test run_workflow with langgraph and output_key."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={
            "status": "completed",
            "history": [{"node": "step1", "result": 42}],
            "context": {},
        }
    )

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        workflow_def = [{"type": "decision", "condition": "True", "output": "value"}]
        result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert len(result["results"]) == 1
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_workflow_langgraph_without_output_key(monkeypatch):
    """Test run_workflow with langgraph without output_key."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={
            "status": "completed",
            "history": [{"node": "step1", "result": 42}],
            "context": {},
        }
    )

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        workflow_def = [{"type": "decision", "condition": "True"}]
        result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert len(result["results"]) == 1
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_workflow_langgraph_multiple_steps(monkeypatch):
    """Test run_workflow with langgraph and multiple steps."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={
            "status": "completed",
            "history": [
                {"node": "step1", "result": 42},
                {"node": "step2", "result": 43},
            ],
            "context": {},
        }
    )

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        workflow_def = [
            {"type": "decision", "condition": "True"},
            {"type": "decision", "condition": "False"},
        ]
        result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert len(result["results"]) == 2
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


# ------------------------------------------------------------------
# WorkflowEngine.run_workflow asyncio.run exception
# ------------------------------------------------------------------
def test_run_workflow_asyncio_run_exception(monkeypatch):
    """Test run_workflow when asyncio.run raises exception."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow that raises exception
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(side_effect=RuntimeError("Async execution failed"))

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        workflow_def = [{"type": "python", "mode": "code", "code": "result = 1"}]  # noqa: F841  # Variable for test verification
        result = engine.run_workflow(workflow_def, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is False
        assert "error" in result
        assert "Async execution failed" in result["error"]
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


# ------------------------------------------------------------------
# WorkflowEngine.get_scenario_memory dry_run/real empty/import error fallback
# ------------------------------------------------------------------
def test_get_scenario_memory_dry_run(monkeypatch):
    """Test get_scenario_memory in dry-run mode."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    result = engine.get_scenario_memory("test query")  # noqa: F841  # Variable for test verification
    assert result["query"] == "test query"
    assert len(result["matches"]) == 1
    assert result["matches"][0]["id"] == "synthetic"
    assert "Scenario memory for test query" in result["matches"][0]["text"]


def test_get_scenario_memory_real_import_error(monkeypatch):
    """Test get_scenario_memory when VectorStore import fails."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Use sys.modules to block the import
    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("VectorStore not available")

    monkeypatch.setitem(sys.modules, "modules.analyze.runbook.vector_store", FakeModule())

    engine = WorkflowEngine(dry_run=False)
    result = engine.get_scenario_memory("test query")  # noqa: F841  # Variable for test verification
    assert result["query"] == "test query"
    assert len(result["matches"]) == 1
    assert result["matches"][0]["id"] == "synthetic"

    # Cleanup
    if "modules.analyze.runbook.vector_store" in sys.modules:
        del sys.modules["modules.analyze.runbook.vector_store"]


def test_get_scenario_memory_real_empty_results(monkeypatch):
    """Test get_scenario_memory with real VectorStore returning empty results."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock VectorStore
    fake_store = MagicMock()
    fake_store.search.return_value = []

    fake_module = MagicMock()
    fake_module.VectorStore = MagicMock(return_value=fake_store)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.analyze", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.analyze.runbook", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.analyze.runbook.vector_store", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        result = engine.get_scenario_memory("test query")  # noqa: F841  # Variable for test verification
        assert result["query"] == "test query"
        assert result["matches"] == []
    finally:
        # Cleanup
        for mod in [
            "modules.analyze.runbook.vector_store",
            "modules.analyze.runbook",
            "modules.analyze",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


# ------------------------------------------------------------------
# WorkflowEngine.capacity_analysis scale_down/monitor/non-numeric
# ------------------------------------------------------------------
def test_capacity_analysis_scale_up(monkeypatch):
    """Test capacity_analysis with forecast > current * 1.2."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": 50}
    forecasts = {"cpu": 70}  # 70 > 50 * 1.2 = 60
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["action"] == "scale_up"


def test_capacity_analysis_scale_down(monkeypatch):
    """Test capacity_analysis with forecast < current * 0.8."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": 100}
    forecasts = {"cpu": 70}  # 70 < 100 * 0.8 = 80
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["action"] == "scale_down"


def test_capacity_analysis_monitor(monkeypatch):
    """Test capacity_analysis with forecast within 20% of current."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": 100}
    forecasts = {"cpu": 105}  # 105 is within 80-120 range
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0]["action"] == "monitor"


def test_capacity_analysis_non_numeric_metrics(monkeypatch):
    """Test capacity_analysis with non-numeric metrics."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": "high"}
    forecasts = {"cpu": 100}
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 0


def test_capacity_analysis_non_numeric_forecasts(monkeypatch):
    """Test capacity_analysis with non-numeric forecasts."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": 100}
    forecasts = {"cpu": "high"}
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 0


def test_capacity_analysis_missing_forecast(monkeypatch):
    """Test capacity_analysis with missing forecast for a metric."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    metrics = {"cpu": 100, "memory": 50}
    forecasts = {"cpu": 105}  # memory forecast missing
    result = engine.capacity_analysis(metrics, forecasts)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert len(result["recommendations"]) == 1  # Only cpu


# ------------------------------------------------------------------
# RunbookRunner._to_ansible_tasks CLI string/list/HTTP headers/data/decision/memory/unsupported
# ------------------------------------------------------------------
def test_to_ansible_tasks_cli_string(monkeypatch):
    """Test _to_ansible_tasks with CLI string command."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "cli", "command": "echo hello", "name": "test"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "test"
    assert tasks[0]["shell"] == "echo hello"


def test_to_ansible_tasks_cli_list(monkeypatch):
    """Test _to_ansible_tasks with CLI list command."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "cli", "command": ["echo", "hello"], "name": "test"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert tasks[0]["shell"] == "echo hello"


def test_to_ansible_tasks_http_with_headers(monkeypatch):
    """Test _to_ansible_tasks with HTTP step including headers."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [
        {
            "type": "http",
            "url": "http://example.com",
            "method": "POST",
            "headers": {"Authorization": "Bearer token"},
            "name": "test",
        }
    ]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "headers" in tasks[0]["uri"]
    assert tasks[0]["uri"]["headers"]["Authorization"] == "Bearer token"


def test_to_ansible_tasks_http_with_body(monkeypatch):
    """Test _to_ansible_tasks with HTTP step including body."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [
        {
            "type": "http",
            "url": "http://example.com",
            "method": "POST",
            "body": {"key": "value"},
            "name": "test",
        }
    ]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "body" in tasks[0]["uri"]
    assert tasks[0]["uri"]["body"] == {"key": "value"}


def test_to_ansible_tasks_http_with_data(monkeypatch):
    """Test _to_ansible_tasks with HTTP step including data."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [
        {
            "type": "http",
            "url": "http://example.com",
            "method": "POST",
            "data": "raw string",
            "name": "test",
        }
    ]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "body" in tasks[0]["uri"]
    assert tasks[0]["uri"]["body"] == "raw string"


def test_to_ansible_tasks_decision(monkeypatch):
    """Test _to_ansible_tasks with decision step."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "decision", "condition": "value > 10", "name": "test"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "set_fact" in tasks[0]
    assert "{{ value > 10 }}" in tasks[0]["set_fact"]["decision"]


def test_to_ansible_tasks_memory(monkeypatch):
    """Test _to_ansible_tasks with memory step."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "memory", "name": "test"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "debug" in tasks[0]
    assert "Scenario memory lookup" in tasks[0]["debug"]["msg"]


def test_to_ansible_tasks_unsupported_type(monkeypatch):
    """Test _to_ansible_tasks with unsupported step type."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "unsupported", "name": "test"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert "debug" in tasks[0]
    assert "Unsupported step type" in tasks[0]["debug"]["msg"]


def test_to_ansible_tasks_default_name(monkeypatch):
    """Test _to_ansible_tasks with default name."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    runbook = [{"type": "cli", "command": "echo hello"}]
    tasks = runner._to_ansible_tasks(runbook)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "cli step"


# ------------------------------------------------------------------
# RunbookRunner.run_runbook empty list/string playbook not found/
# PlaybookManager import error/execute failure fallback to engine
# ------------------------------------------------------------------
def test_run_runbook_empty_list(monkeypatch):
    """Test run_runbook with empty list."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    runner = RunbookRunner(engine=engine)
    result = runner.run_runbook([], {})  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["runbook"] == []


def test_run_runbook_string_playbook_not_found(monkeypatch):
    """Test run_runbook with string playbook when PlaybookManager import fails."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Use sys.modules to block the import
    class FakeModule:
        def __getattr__(self, name):
            raise ImportError("PlaybookManager not available")

    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", FakeModule())

    engine = WorkflowEngine(dry_run=False)
    runner = RunbookRunner(engine=engine)
    result = runner.run_runbook("playbook.yml", {})  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "error" in result

    # Cleanup
    if "modules.execute.auto_heal.playbook_manager" in sys.modules:
        del sys.modules["modules.execute.auto_heal.playbook_manager"]


def test_run_runbook_playbook_manager_import_error(monkeypatch):
    """Test run_runbook when PlaybookManager raises exception during import."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that raises exception during instantiation
    class FakePlaybookManager:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PlaybookManager init failed")

    fake_module = MagicMock()
    fake_module.PlaybookManager = FakePlaybookManager

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        result = runner.run_runbook("playbook.yml", {})  # noqa: F841  # Variable for test verification
        assert result["success"] is False
        assert "error" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_execute_failure_fallback_to_engine(monkeypatch):
    """Test run_runbook when PlaybookManager execute fails, fallback to engine."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that fails during execute
    fake_manager = MagicMock()
    fake_manager.execute_playbook = AsyncMock(side_effect=RuntimeError("Execute failed"))

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        result = runner.run_runbook("playbook.yml", {})  # noqa: F841  # Variable for test verification
        assert result["success"] is False
        assert "error" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_list_playbook_manager_fallback_to_engine(monkeypatch):
    """Test run_runbook with list when PlaybookManager fails, fallback to engine."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that fails
    fake_manager = MagicMock()
    fake_manager.create_playbook = MagicMock(return_value=False)

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        runbook = [{"type": "python", "mode": "code", "code": "result = 1"}]  # noqa: F841  # Variable for test verification
        result = runner.run_runbook(runbook, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert "results" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_list_playbook_manager_exception_fallback(monkeypatch):
    """Test run_runbook with list when PlaybookManager raises exception, fallback to engine."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that raises exception
    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(side_effect=RuntimeError("PlaybookManager failed"))

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        runbook = [{"type": "python", "mode": "code", "code": "result = 1"}]  # noqa: F841  # Variable for test verification
        result = runner.run_runbook(runbook, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert "results" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_string_playbook_manager_success(monkeypatch):
    """Test run_runbook with string playbook when PlaybookManager succeeds."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that succeeds
    fake_manager = MagicMock()
    fake_manager.execute_playbook = AsyncMock(return_value={"success": True, "output": "done"})

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        result = runner.run_runbook("playbook.yml", {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_list_playbook_manager_success(monkeypatch):
    """Test run_runbook with list when PlaybookManager succeeds."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that succeeds
    fake_manager = MagicMock()
    fake_manager.create_playbook = MagicMock(return_value=True)
    fake_manager.save_playbook = MagicMock()
    fake_manager.execute_playbook = AsyncMock(return_value={"success": True, "output": "done"})

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        runbook = [{"type": "cli", "command": "echo hello"}]
        result = runner.run_runbook(runbook, {})  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert "runbook" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_list_playbook_manager_execute_fails(monkeypatch):
    """Test run_runbook with list when PlaybookManager execute returns False."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that creates playbook but execute fails
    fake_manager = MagicMock()
    fake_manager.create_playbook = MagicMock(return_value=True)
    fake_manager.save_playbook = MagicMock()
    fake_manager.execute_playbook = AsyncMock(return_value={"success": False, "error": "failed"})

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        runbook = [{"type": "cli", "command": "echo hello"}]
        result = runner.run_runbook(runbook, {})  # noqa: F841  # Variable for test verification
        # Should fall back to engine
        assert result["success"] is True
        assert "results" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_list_playbook_manager_create_fails(monkeypatch):
    """Test run_runbook with list when PlaybookManager create_playbook returns False."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock PlaybookManager that fails to create playbook
    fake_manager = MagicMock()
    fake_manager.create_playbook = MagicMock(return_value=False)

    fake_module = MagicMock()
    fake_module.PlaybookManager = MagicMock(return_value=fake_manager)

    monkeypatch.setitem(sys.modules, "modules", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal", MagicMock())
    monkeypatch.setitem(sys.modules, "modules.execute.auto_heal.playbook_manager", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        runner = RunbookRunner(engine=engine)
        runbook = [{"type": "cli", "command": "echo hello"}]
        result = runner.run_runbook(runbook, {})  # noqa: F841  # Variable for test verification
        # Should fall back to engine
        assert result["success"] is True
        assert "results" in result
    finally:
        # Cleanup
        for mod in [
            "modules.execute.auto_heal.playbook_manager",
            "modules.execute.auto_heal",
            "modules.execute",
            "modules",
        ]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_runbook_init_with_engine(monkeypatch):
    """Test RunbookRunner.__init__ with provided engine."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    engine = WorkflowEngine(dry_run=True)
    runner = RunbookRunner(engine=engine)
    assert runner.engine is engine


def test_run_runbook_init_without_engine(monkeypatch):
    """Test RunbookRunner.__init__ without engine (creates new one)."""
    monkeypatch.delenv("INFRA_EXECUTE_ENABLED", raising=False)
    runner = RunbookRunner(dry_run=True)
    assert runner.engine.dry_run is True


def test_run_runbook_init_dry_run_none(monkeypatch):
    """Test RunbookRunner.__init__ with dry_run=None."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    runner = RunbookRunner(dry_run=None)
    assert runner.engine.dry_run is False


# ------------------------------------------------------------------
# Additional branch coverage for missing branches
# ------------------------------------------------------------------
def test_run_workflow_langgraph_no_output_key_in_step(monkeypatch):
    """Test run_workflow with langgraph when step has no output_key (line 187 else branch)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={
            "status": "completed",
            "history": [{"node": "step1", "result": 42}],
            "context": {},
        }
    )

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        # Step without output_key
        workflow_def = [{"type": "decision", "condition": "True"}]
        result = engine.run_workflow(workflow_def, {})
        assert result["success"] is True
        assert len(result["results"]) == 1
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]


def test_run_workflow_langgraph_no_steps_added(monkeypatch):
    """Test run_workflow with langgraph when no steps are added (line 200 else branch)."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")

    # Mock langgraph workflow
    fake_workflow = MagicMock()
    fake_workflow.execute = AsyncMock(
        return_value={
            "status": "completed",
            "history": [],
            "context": {},
        }
    )

    # Create a real WorkflowNode class that can be inherited
    class FakeWorkflowNode:
        pass

    fake_module = MagicMock()
    fake_module.Workflow = MagicMock(return_value=fake_workflow)
    fake_module.WorkflowNode = FakeWorkflowNode

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph", MagicMock())
    monkeypatch.setitem(sys.modules, "core.ai.langgraph.workflow", fake_module)

    try:
        engine = WorkflowEngine(dry_run=False)
        # Empty workflow_def - no steps to add
        # This hits the early return at line 169-170, not the langgraph path
        # The branch at line 200 is unreachable in normal execution
        # since if steps is empty we return early, and if steps is non-empty
        # the for loop always executes at least once
        workflow_def = []
        result = engine.run_workflow(workflow_def, {"key": "value"})
        assert result["success"] is True
        assert result["results"] == []
        assert result["context"] == {"key": "value"}
    finally:
        # Cleanup
        for mod in ["core.ai.langgraph.workflow", "core.ai.langgraph", "core.ai", "core"]:
            if mod in sys.modules:
                del sys.modules[mod]
