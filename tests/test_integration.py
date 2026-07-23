# -*- coding: utf-8 -*-
"""
Integration Tests
集成测试
"""

import os
import sys

import pytest  # noqa: F401

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegration:
    def test_api_response_format(self):
        from core.api_response_standard import create_success_response

        response = create_success_response({"test": "data"})
        assert response["success"] is True
        assert response["data"]["test"] == "data"

    def test_error_response_format(self):
        from core.api_response_standard import create_error_response

        response = create_error_response("Test error", "TEST_ERROR")
        assert response["success"] is False
        assert response["error"] == "Test error"
        assert response["error_code"] == "TEST_ERROR"

    def test_module_dependencies(self):
        from core.module_dependencies import validate_initialization_order

        result = validate_initialization_order()
        assert result is True
