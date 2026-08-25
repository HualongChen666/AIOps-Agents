# -*- coding: utf-8 -*-
"""Happy-path tests for documentation addon services."""

import pytest  # noqa: F401  # Imported for test setup

from extensions.addons.documentation.sphinx_documentation_service.service import Service


@pytest.fixture
def sphinx_service(monkeypatch):
    """Provide a Sphinx documentation service with a faked engine."""
    fake_result = {  # noqa: F841  # Variable for test verification
        "dry_run": True,
        "command": "sphinx-build docs _build",
        "source": "docs",
        "output": "_build",
        "warnings": 0,
        "errors": 0,
        "status": "would_run",
    }

    def fake_build_docs(self, source, output):
        return {**fake_result, "source": source, "output": output}

    monkeypatch.setattr(
        "extensions.addons.engines.doc_policy_engine.DocEngine.build_docs",
        fake_build_docs,
    )
    return Service(dry_run=True)


def test_sphinx_build_docs_returns_expected_result(sphinx_service):
    """execute_operation for build_docs returns a dict with expected keys."""
    payload = {"source": "docs", "output": "_build"}
    result = sphinx_service.execute_operation(
        "build_docs", payload
    )  # noqa: F841  # Variable for test verification

    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["operation"] == "build_docs"
    assert result["dry_run"] is True
    assert "result" in result
    assert result["result"]["source"] == "docs"
    assert result["result"]["output"] == "_build"
    assert result["result"]["status"] == "would_run"


def test_sphinx_list_methods_returns_expected_result(sphinx_service):
    """execute_operation for list_methods returns a valid response."""
    result = sphinx_service.execute_operation(
        "list_methods"
    )  # noqa: F841  # Variable for test verification

    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["operation"] == "list_methods"
    assert "result" in result
    assert result["result"]["message"] == "not implemented"


def test_sphinx_get_stats_returns_valid_dict(sphinx_service):
    """execute_operation for get_stats returns a valid dict."""
    result = sphinx_service.execute_operation(
        "get_stats", {}
    )  # noqa: F841  # Variable for test verification

    assert result is not None
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["operation"] == "get_stats"
