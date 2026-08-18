# -*- coding: utf-8 -*-
"""Tests for schemas.py - Pydantic schemas for the Sphinx Documentation microservice."""

import pytest

from extensions.addons.documentation.sphinx_documentation_service.schemas import (
    ServiceHealth,
    StatsResponse,
    FeatureRequest,
    FeatureResponse,
)


class TestServiceHealth:
    """Test suite for ServiceHealth schema."""

    def test_default_values(self):
        """Test default ServiceHealth values."""
        health = ServiceHealth(status="ok", service="test-service")
        assert health.status == "ok"
        assert health.service == "test-service"
        assert health.uptime_seconds == 0
        assert health.index_size == 0

    def test_custom_status(self):
        """Test custom status."""
        health = ServiceHealth(status="degraded", service="test-service")
        assert health.status == "degraded"

    def test_custom_service(self):
        """Test custom service name."""
        health = ServiceHealth(status="ok", service="custom-service")
        assert health.service == "custom-service"

    def test_custom_uptime_seconds(self):
        """Test custom uptime_seconds."""
        health = ServiceHealth(status="ok", service="test-service", uptime_seconds=100)
        assert health.uptime_seconds == 100

    def test_custom_index_size(self):
        """Test custom index_size."""
        health = ServiceHealth(status="ok", service="test-service", index_size=50)
        assert health.index_size == 50

    def test_negative_uptime_seconds(self):
        """Test negative uptime_seconds."""
        health = ServiceHealth(status="ok", service="test-service", uptime_seconds=-1)
        assert health.uptime_seconds == -1

    def test_negative_index_size(self):
        """Test negative index_size."""
        health = ServiceHealth(status="ok", service="test-service", index_size=-1)
        assert health.index_size == -1

    def test_large_uptime_seconds(self):
        """Test large uptime_seconds."""
        health = ServiceHealth(status="ok", service="test-service", uptime_seconds=1000000)
        assert health.uptime_seconds == 1000000

    def test_large_index_size(self):
        """Test large index_size."""
        health = ServiceHealth(status="ok", service="test-service", index_size=1000000)
        assert health.index_size == 1000000

    def test_zero_uptime_seconds(self):
        """Test zero uptime_seconds."""
        health = ServiceHealth(status="ok", service="test-service", uptime_seconds=0)
        assert health.uptime_seconds == 0

    def test_zero_index_size(self):
        """Test zero index_size."""
        health = ServiceHealth(status="ok", service="test-service", index_size=0)
        assert health.index_size == 0

    def test_status_variations(self):
        """Test various status values."""
        statuses = ["ok", "degraded", "error", "maintenance"]
        for status in statuses:
            health = ServiceHealth(status=status, service="test-service")
            assert health.status == status

    def test_unicode_service_name(self):
        """Test unicode service name."""
        health = ServiceHealth(status="ok", service="测试服务")
        assert health.service == "测试服务"

    def test_model_dump(self):
        """Test model_dump method."""
        health = ServiceHealth(status="ok", service="test-service", uptime_seconds=100)
        data = health.model_dump()
        assert data["status"] == "ok"
        assert data["service"] == "test-service"
        assert data["uptime_seconds"] == 100

    def test_model_json_schema(self):
        """Test model_json_schema method."""
        schema = ServiceHealth.model_json_schema()
        assert "properties" in schema
        assert "status" in schema["properties"]
        assert "service" in schema["properties"]


class TestStatsResponse:
    """Test suite for StatsResponse schema."""

    def test_default_values(self):
        """Test default StatsResponse values."""
        stats = StatsResponse(
            total_requests=100, cache_hits=50, cache_misses=50
        )
        assert stats.total_requests == 100
        assert stats.cache_hits == 50
        assert stats.cache_misses == 50
        assert stats.operations == {}
        assert stats.index_size == 0
        assert stats.feature_count == 0

    def test_custom_total_requests(self):
        """Test custom total_requests."""
        stats = StatsResponse(total_requests=1000, cache_hits=500, cache_misses=500)
        assert stats.total_requests == 1000

    def test_custom_cache_hits(self):
        """Test custom cache_hits."""
        stats = StatsResponse(total_requests=100, cache_hits=75, cache_misses=25)
        assert stats.cache_hits == 75

    def test_custom_cache_misses(self):
        """Test custom cache_misses."""
        stats = StatsResponse(total_requests=100, cache_hits=25, cache_misses=75)
        assert stats.cache_misses == 75

    def test_custom_operations(self):
        """Test custom operations dict."""
        stats = StatsResponse(
            total_requests=100,
            cache_hits=50,
            cache_misses=50,
            operations={"op1": 10, "op2": 20},
        )
        assert stats.operations == {"op1": 10, "op2": 20}

    def test_custom_index_size(self):
        """Test custom index_size."""
        stats = StatsResponse(
            total_requests=100, cache_hits=50, cache_misses=50, index_size=1000
        )
        assert stats.index_size == 1000

    def test_custom_feature_count(self):
        """Test custom feature_count."""
        stats = StatsResponse(
            total_requests=100, cache_hits=50, cache_misses=50, feature_count=5
        )
        assert stats.feature_count == 5

    def test_zero_values(self):
        """Test all zero values."""
        stats = StatsResponse(total_requests=0, cache_hits=0, cache_misses=0)
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    def test_negative_values(self):
        """Test negative values (pydantic may accept)."""
        stats = StatsResponse(total_requests=-1, cache_hits=-1, cache_misses=-1)
        assert stats.total_requests == -1
        assert stats.cache_hits == -1
        assert stats.cache_misses == -1

    def test_large_values(self):
        """Test large values."""
        stats = StatsResponse(
            total_requests=1000000, cache_hits=500000, cache_misses=500000
        )
        assert stats.total_requests == 1000000
        assert stats.cache_hits == 500000
        assert stats.cache_misses == 500000

    def test_operations_with_multiple_keys(self):
        """Test operations with multiple keys."""
        stats = StatsResponse(
            total_requests=100,
            cache_hits=50,
            cache_misses=50,
            operations={"op1": 10, "op2": 20, "op3": 30, "op4": 40},
        )
        assert len(stats.operations) == 4

    def test_operations_empty_dict(self):
        """Test operations with empty dict."""
        stats = StatsResponse(
            total_requests=100, cache_hits=50, cache_misses=50, operations={}
        )
        assert stats.operations == {}

    def test_operations_with_zero_values(self):
        """Test operations with zero values."""
        stats = StatsResponse(
            total_requests=100,
            cache_hits=50,
            cache_misses=50,
            operations={"op1": 0, "op2": 0},
        )
        assert stats.operations == {"op1": 0, "op2": 0}

    def test_operations_with_unicode_keys(self):
        """Test operations with unicode keys."""
        stats = StatsResponse(
            total_requests=100,
            cache_hits=50,
            cache_misses=50,
            operations={"操作1": 10, "操作2": 20},
        )
        assert "操作1" in stats.operations

    def test_model_dump(self):
        """Test model_dump method."""
        stats = StatsResponse(
            total_requests=100, cache_hits=50, cache_misses=50, index_size=100
        )
        data = stats.model_dump()
        assert data["total_requests"] == 100
        assert data["cache_hits"] == 50
        assert data["cache_misses"] == 50
        assert data["index_size"] == 100


class TestFeatureRequest:
    """Test suite for FeatureRequest schema."""

    def test_default_values(self):
        """Test default FeatureRequest values."""
        request = FeatureRequest()
        assert request.config == {}

    def test_custom_config(self):
        """Test custom config."""
        request = FeatureRequest(config={"key": "value"})
        assert request.config == {"key": "value"}

    def test_config_with_multiple_keys(self):
        """Test config with multiple keys."""
        request = FeatureRequest(config={"key1": "val1", "key2": "val2", "key3": "val3"})
        assert len(request.config) == 3

    def test_config_with_nested_dict(self):
        """Test config with nested dict."""
        request = FeatureRequest(config={"outer": {"inner": "value"}})
        assert request.config == {"outer": {"inner": "value"}}

    def test_config_with_list(self):
        """Test config with list value."""
        request = FeatureRequest(config={"items": [1, 2, 3]})
        assert request.config == {"items": [1, 2, 3]}

    def test_config_with_number(self):
        """Test config with number value."""
        request = FeatureRequest(config={"count": 100})
        assert request.config == {"count": 100}

    def test_config_with_boolean(self):
        """Test config with boolean value."""
        request = FeatureRequest(config={"enabled": True})
        assert request.config == {"enabled": True}

    def test_config_with_none(self):
        """Test config with None value."""
        request = FeatureRequest(config={"value": None})
        assert request.config == {"value": None}

    def test_config_empty_dict(self):
        """Test config with empty dict."""
        request = FeatureRequest(config={})
        assert request.config == {}

    def test_config_with_unicode(self):
        """Test config with unicode values."""
        request = FeatureRequest(config={"text": "测试"})
        assert request.config == {"text": "测试"}

    def test_config_with_special_characters(self):
        """Test config with special characters."""
        request = FeatureRequest(config={"key": "value-with-special-chars_123"})
        assert request.config == {"key": "value-with-special-chars_123"}

    def test_model_dump(self):
        """Test model_dump method."""
        request = FeatureRequest(config={"key": "value"})
        data = request.model_dump()
        assert data["config"] == {"key": "value"}


class TestFeatureResponse:
    """Test suite for FeatureResponse schema."""

    def test_default_values(self):
        """Test default FeatureResponse values."""
        response = FeatureResponse(feature="test", success=True)
        assert response.feature == "test"
        assert response.success is True
        assert response.status == ""
        assert response.config == {}
        assert response.result == {}
        assert response.message == ""

    def test_custom_feature(self):
        """Test custom feature."""
        response = FeatureResponse(feature="custom-feature", success=True)
        assert response.feature == "custom-feature"

    def test_custom_success_true(self):
        """Test success=True."""
        response = FeatureResponse(feature="test", success=True)
        assert response.success is True

    def test_custom_success_false(self):
        """Test success=False."""
        response = FeatureResponse(feature="test", success=False)
        assert response.success is False

    def test_custom_status(self):
        """Test custom status."""
        response = FeatureResponse(feature="test", success=True, status="completed")
        assert response.status == "completed"

    def test_custom_config(self):
        """Test custom config."""
        response = FeatureResponse(
            feature="test", success=True, config={"key": "value"}
        )
        assert response.config == {"key": "value"}

    def test_custom_result(self):
        """Test custom result."""
        response = FeatureResponse(
            feature="test", success=True, result={"data": "value"}
        )
        assert response.result == {"data": "value"}

    def test_custom_message(self):
        """Test custom message."""
        response = FeatureResponse(feature="test", success=True, message="Operation completed")
        assert response.message == "Operation completed"

    def test_all_fields_populated(self):
        """Test all fields populated."""
        response = FeatureResponse(
            feature="test-feature",
            success=True,
            status="completed",
            config={"key": "value"},
            result={"data": "result"},
            message="Success",
        )
        assert response.feature == "test-feature"
        assert response.success is True
        assert response.status == "completed"
        assert response.config == {"key": "value"}
        assert response.result == {"data": "result"}
        assert response.message == "Success"

    def test_status_variations(self):
        """Test various status values."""
        statuses = ["pending", "running", "completed", "failed", "cancelled"]
        for status in statuses:
            response = FeatureResponse(feature="test", success=True, status=status)
            assert response.status == status

    def test_result_with_nested_dict(self):
        """Test result with nested dict."""
        response = FeatureResponse(
            feature="test", success=True, result={"outer": {"inner": "value"}}
        )
        assert response.result == {"outer": {"inner": "value"}}

    def test_result_with_list(self):
        """Test result with list value."""
        response = FeatureResponse(feature="test", success=True, result={"items": [1, 2, 3]})
        assert response.result == {"items": [1, 2, 3]}

    def test_result_with_number(self):
        """Test result with number value."""
        response = FeatureResponse(feature="test", success=True, result={"count": 100})
        assert response.result == {"count": 100}

    def test_result_with_boolean(self):
        """Test result with boolean value."""
        response = FeatureResponse(feature="test", success=True, result={"enabled": True})
        assert response.result == {"enabled": True}

    def test_result_with_none(self):
        """Test result with None value."""
        response = FeatureResponse(feature="test", success=True, result={"value": None})
        assert response.result == {"value": None}

    def test_empty_status(self):
        """Test empty status string."""
        response = FeatureResponse(feature="test", success=True, status="")
        assert response.status == ""

    def test_empty_message(self):
        """Test empty message string."""
        response = FeatureResponse(feature="test", success=True, message="")
        assert response.message == ""

    def test_unicode_feature_name(self):
        """Test unicode feature name."""
        response = FeatureResponse(feature="测试功能", success=True)
        assert response.feature == "测试功能"

    def test_unicode_message(self):
        """Test unicode message."""
        response = FeatureResponse(feature="test", success=True, message="操作成功")
        assert response.message == "操作成功"

    def test_model_dump(self):
        """Test model_dump method."""
        response = FeatureResponse(
            feature="test", success=True, status="completed", message="Done"
        )
        data = response.model_dump()
        assert data["feature"] == "test"
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["message"] == "Done"

    def test_success_false_with_error_message(self):
        """Test success=False with error message."""
        response = FeatureResponse(
            feature="test", success=False, status="failed", message="Error occurred"
        )
        assert response.success is False
        assert response.status == "failed"
        assert response.message == "Error occurred"
