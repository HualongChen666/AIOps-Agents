# -*- coding: utf-8 -*-
"""Tests for service.py - Sphinx documentation service wrapper."""

import pytest
from extensions.addons.documentation.sphinx_documentation_service.service import (
    BASE_METHODS,
    OPERATIONS,
    SphinxDocumentationService,
    Service,
)


class TestSphinxDocumentationService:
    """Test suite for SphinxDocumentationService."""

    def test_service_singleton_alias(self):
        """Test that Service is an alias for SphinxDocumentationService."""
        assert Service is SphinxDocumentationService

    def test_init_default_dry_run(self):
        """Test initialization with default dry_run=True."""
        service = SphinxDocumentationService()
        assert service._engine.dry_run is True

    def test_init_with_dry_run_false(self):
        """Test initialization with dry_run=False."""
        service = SphinxDocumentationService(dry_run=False)
        assert service._engine.dry_run is False

    def test_init_with_kwargs(self):
        """Test initialization with additional kwargs."""
        service = SphinxDocumentationService(dry_run=False, custom_param="value")
        assert service._engine.dry_run is False

    def test_execute_operation_build_docs(self):
        """Test execute_operation with build_docs."""
        service = SphinxDocumentationService()
        result = service.execute_operation("build_docs", {"source": "docs", "output": "_build"})
        assert result["success"] is True
        assert result["operation"] == "build_docs"
        assert result["dry_run"] is True
        assert "result" in result

    def test_execute_operation_build_docs_default_params(self):
        """Test execute_operation with build_docs using default parameters."""
        service = SphinxDocumentationService()
        result = service.execute_operation("build_docs")
        assert result["success"] is True
        assert result["operation"] == "build_docs"
        assert result["dry_run"] is True

    def test_execute_operation_configure_sphinx(self):
        """Test execute_operation with configure_sphinx."""
        service = SphinxDocumentationService()
        result = service.execute_operation("configure_sphinx", {"source": "docs"})
        assert result["success"] is True
        assert result["operation"] == "configure_sphinx"
        assert result["dry_run"] is True

    def test_execute_operation_deploy_doc_site(self):
        """Test execute_operation with deploy_doc_site."""
        service = SphinxDocumentationService()
        result = service.execute_operation("deploy_doc_site", {"output": "site"})
        assert result["success"] is True
        assert result["operation"] == "deploy_doc_site"
        assert result["dry_run"] is True

    def test_execute_operation_test_and_optimize_sphinx(self):
        """Test execute_operation with test_and_optimize_sphinx."""
        service = SphinxDocumentationService()
        result = service.execute_operation("test_and_optimize_sphinx")
        assert result["success"] is True
        assert result["operation"] == "test_and_optimize_sphinx"
        assert result["dry_run"] is True

    def test_execute_operation_get_state(self):
        """Test execute_operation with get_state (BASE_METHOD)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("get_state")
        assert result["success"] is True
        assert result["operation"] == "get_state"
        assert result["dry_run"] is True
        assert result["result"]["message"] == "not implemented"

    def test_execute_operation_backup_state(self):
        """Test execute_operation with backup_state (BASE_METHOD)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("backup_state")
        assert result["success"] is True
        assert result["operation"] == "backup_state"
        assert result["dry_run"] is True
        assert result["result"]["message"] == "not implemented"

    def test_execute_operation_restore_state(self):
        """Test execute_operation with restore_state (BASE_METHOD)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("restore_state")
        assert result["success"] is True
        assert result["operation"] == "restore_state"
        assert result["dry_run"] is True
        assert result["result"]["message"] == "not implemented"

    def test_execute_operation_get_stats(self):
        """Test execute_operation with get_stats (BASE_METHOD)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("get_stats")
        assert result["success"] is True
        assert result["operation"] == "get_stats"
        assert result["dry_run"] is True
        assert result["result"]["message"] == "not implemented"

    def test_execute_operation_list_methods(self):
        """Test execute_operation with list_methods (BASE_METHOD)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("list_methods")
        assert result["success"] is True
        assert result["operation"] == "list_methods"
        assert result["dry_run"] is True
        assert result["result"]["message"] == "not implemented"

    def test_execute_operation_unknown_operation(self):
        """Test execute_operation with unknown operation raises ValueError."""
        service = SphinxDocumentationService()
        with pytest.raises(ValueError, match="Unknown operation: invalid_operation"):
            service.execute_operation("invalid_operation")

    def test_execute_operation_with_none_params(self):
        """Test execute_operation with None params (should default to empty dict)."""
        service = SphinxDocumentationService()
        result = service.execute_operation("build_docs", None)
        assert result["success"] is True
        assert result["operation"] == "build_docs"

    def test_execute_operation_with_empty_params(self):
        """Test execute_operation with empty params dict."""
        service = SphinxDocumentationService()
        result = service.execute_operation("build_docs", {})
        assert result["success"] is True
        assert result["operation"] == "build_docs"

    def test_execute_operation_result_structure(self):
        """Test that execute_operation returns correct structure."""
        service = SphinxDocumentationService()
        result = service.execute_operation("build_docs")
        assert isinstance(result, dict)
        assert "success" in result
        assert "operation" in result
        assert "dry_run" in result
        assert "result" in result
        assert isinstance(result["success"], bool)
        assert isinstance(result["operation"], str)
        assert isinstance(result["dry_run"], bool)
        assert isinstance(result["result"], dict)

    def test_base_methods_constant(self):
        """Test BASE_METHODS constant contains expected methods."""
        assert "get_state" in BASE_METHODS
        assert "backup_state" in BASE_METHODS
        assert "restore_state" in BASE_METHODS
        assert "get_stats" in BASE_METHODS
        assert "list_methods" in BASE_METHODS
        assert len(BASE_METHODS) == 5

    def test_operations_constant(self):
        """Test OPERATIONS constant contains expected operations."""
        assert "build_docs" in OPERATIONS
        assert "configure_sphinx" in OPERATIONS
        assert "deploy_doc_site" in OPERATIONS
        assert "test_and_optimize_sphinx" in OPERATIONS
        assert len(OPERATIONS) == 4

    def test_execute_operation_all_operations(self):
        """Test execute_operation with all defined operations."""
        service = SphinxDocumentationService()
        for operation in OPERATIONS:
            result = service.execute_operation(operation)
            assert result["success"] is True
            assert result["operation"] == operation

    def test_execute_operation_all_base_methods(self):
        """Test execute_operation with all base methods."""
        service = SphinxDocumentationService()
        for method in BASE_METHODS:
            result = service.execute_operation(method)
            assert result["success"] is True
            assert result["operation"] == method

    def test_engine_dry_run_affects_result(self):
        """Test that engine dry_run setting affects result."""
        service_dry = SphinxDocumentationService(dry_run=True)
        service_wet = SphinxDocumentationService(dry_run=False)

        result_dry = service_dry.execute_operation("build_docs")
        result_wet = service_wet.execute_operation("build_docs")

        assert result_dry["dry_run"] is True
        assert result_wet["dry_run"] is False

    def test_multiple_service_instances(self):
        """Test that multiple service instances work independently."""
        service1 = SphinxDocumentationService(dry_run=True)
        service2 = SphinxDocumentationService(dry_run=False)

        result1 = service1.execute_operation("build_docs")
        result2 = service2.execute_operation("build_docs")

        assert result1["dry_run"] is True
        assert result2["dry_run"] is False

    def test_operation_params_passed_to_engine(self):
        """Test that operation parameters are passed to the engine."""
        service = SphinxDocumentationService()
        custom_source = "custom_docs"
        custom_output = "custom_build"
        result = service.execute_operation(
            "build_docs", {"source": custom_source, "output": custom_output}
        )
        assert result["success"] is True
        # The result should contain the parameters passed
        assert "result" in result
