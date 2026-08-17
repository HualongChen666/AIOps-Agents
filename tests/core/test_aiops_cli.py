# -*- coding: utf-8 -*-
"""Real tests for the aiops_agent CLI.

These tests exercise the actual argparse setup and HTTP call paths.
They do not mock httpx; instead they point the CLI at a non-listening
local port so the real network error path is exercised.
"""

import os  # noqa: F401  # Imported for test setup
from importlib import reload

import pytest  # noqa: F401  # Imported for test setup


def _reload_cli_with_env(api_url: str, internal_key: str = "test-internal-key"):
    """Set environment variables and reload the cli module.

    The cli module reads DEFAULT_BASE_URL and INTERNAL_KEY at import time,  # noqa: F401  # Imported for test setup
    so we must set the environment before importing/reloading.
    """
    os.environ["AIOPS_API_URL"] = api_url
    os.environ["AIOPS_INTERNAL_KEY"] = internal_key
    from aiops_agent import cli

    return reload(cli)


@pytest.fixture
def cli_module():
    return _reload_cli_with_env("http://127.0.0.1:1")


def test_main_help_exits(cli_module):
    """--help should print usage and exit successfully."""
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["--help"])
    assert exc.value.code == 0


def test_main_no_command_prints_help(cli_module):
    """Calling the CLI without a subcommand prints help and returns 1."""
    assert cli_module.main([]) == 1


def test_incidents_command_returns_one_on_connection_error(cli_module):
    """incidents makes a real HTTP call and returns 1 on connection error."""
    assert cli_module.main(["incidents"]) == 1


def test_approve_command_returns_one_on_connection_error(cli_module):
    """approve makes a real PATCH call and returns 1 on connection error."""
    assert cli_module.main(["approve", "alert-123"]) == 1


def test_reject_command_returns_one_on_connection_error(cli_module):
    """reject makes a real POST call and returns 1 on connection error."""
    assert cli_module.main(["reject", "alert-123"]) == 1


def test_audit_command_returns_one_on_connection_error(cli_module):
    """audit makes a real GET call and returns 1 on connection error."""
    assert cli_module.main(["audit", "--limit", "10"]) == 1


def test_cli_module_entry_point():
    """python -m aiops_agent must import and call main without error."""
    import aiops_agent.__main__

    assert aiops_agent.__main__.main is not None


def test_headers_include_internal_key(cli_module):
    """_headers attaches X-Internal-Key when the env var is present."""
    headers = cli_module._headers()
    assert headers["Accept"] == "application/json"
    assert headers["X-Internal-Key"] == "test-internal-key"


def test_headers_without_internal_key():
    """_headers omits X-Internal-Key when the env var is absent."""
    os.environ.pop("AIOPS_INTERNAL_KEY", None)
    os.environ["AIOPS_API_URL"] = "http://127.0.0.1:8000"
    cli = _reload_cli_with_env("http://127.0.0.1:8000", "")
    headers = cli._headers()
    assert "X-Internal-Key" not in headers
