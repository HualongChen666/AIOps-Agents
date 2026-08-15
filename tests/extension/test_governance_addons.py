# -*- coding: utf-8 -*-
"""Tests for the governance group addons (documentation & policy engines)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from extensions.addons.documentation.sphinx_documentation_service.service import (
    Service as SphinxService,
)
from extensions.addons.infrastructure.api_standards_service.service import (
    Service as ApiStandardsService,
)
from extensions.addons.infrastructure.config_service.service import Service as ConfigService
from extensions.addons.infrastructure.data_standards_service.service import (
    Service as DataStandardsService,
)
from extensions.addons.infrastructure.plugin_market_service.service import (
    Service as PluginMarketService,
)
from extensions.addons.infrastructure.plugin_system_service.service import (
    Service as PluginSystemService,
)
from extensions.addons.infrastructure.user_service.service import Service as UserService


@pytest.fixture(autouse=True)
def _reset_execute_env(monkeypatch):
    """Keep execution gated off by default."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "false")


def test_sphinx_documentation_service_build_docs(monkeypatch):
    """Sphinx documentation dispatches build_docs and parses subprocess output."""
    monkeypatch.setenv("INFRA_EXECUTE_ENABLED", "true")
    SphinxService._engine.dry_run = False

    mock_proc = MagicMock(returncode=0, stdout="build succeeded\n", stderr="")
    with patch("extensions.addons.engines.doc_policy_engine.subprocess.run") as mock_run:
        mock_run.return_value = mock_proc
        result = SphinxService.execute_operation(
            "build_docs", {"source": "docs", "output": "_build"}
        )

    assert result["success"] is True
    assert result["operation"] == "build_docs"
    assert result["result"]["dry_run"] is False
    assert result["result"]["returncode"] == 0
    mock_run.assert_called_once_with(
        ["sphinx-build", "docs", "_build"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_api_standards_service_lint_openapi():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API"},
        "paths": {},
    }
    result = ApiStandardsService.execute_operation("lint_openapi", {"spec": spec})
    assert result["success"] is True
    assert result["result"]["valid"] is True


def test_data_standards_service_validate_schema():
    obj = {"name": "alice"}
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
    }
    result = DataStandardsService.execute_operation(
        "validate_schema", {"obj": obj, "schema": schema}
    )
    assert result["success"] is True
    assert result["result"]["valid"] is True


def test_config_service_load_config_env(monkeypatch):
    monkeypatch.setenv("GOV_TEST_CFG", "42")
    result = ConfigService.execute_operation("load_config", {"key": "GOV_TEST_CFG"})
    assert result["success"] is True
    assert result["result"]["value"] == 42


def test_user_service_user_lookup():
    result = UserService.execute_operation("user_lookup", {"user_id": "admin"})
    assert result["success"] is True
    assert result["result"]["found"] is True
    assert result["result"]["user_id"] == "admin"


def test_plugin_market_service_plugin_index():
    result = PluginMarketService.execute_operation("plugin_index", {})
    assert result["success"] is True
    assert isinstance(result["result"], list)
    assert any(item["id"] == "sphinx_documentation_service" for item in result["result"])


def test_plugin_system_service_plugin_load():
    result = PluginSystemService.execute_operation(
        "plugin_load", {"plugin_id": "json"}
    )
    assert result["success"] is True
    assert result["result"]["dry_run"] is True
    assert result["result"]["plugin_id"] == "json"
