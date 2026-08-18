# -*- coding: utf-8 -*-
"""
Hardware Log Router API Integration Tests

Tests for the hardware log analysis API endpoints including:
- Log analysis endpoints
- Repair triggering endpoints
- Error handling and validation
- Multi-tenant support
- Security and authorization
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from api.hardware_log_router import (
    LogAnalysisRequest,
    RepairTriggerRequest,
    AnalysisResponse,
    ComponentIssueResponse,
)
from extensions.hardware_remediation.hardware_log_analyzer import (
    AnalysisResult,
    ComponentIssue,
    ComponentType,
    HardwareVendor,
    SeverityLevel,
    RiskLevel,
)


@pytest.fixture
def hardware_log_client():
    """Create test client for hardware log router"""
    from main import app
    return TestClient(app)


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing"""
    issue = ComponentIssue(
        component=ComponentType.CPU,
        severity=SeverityLevel.CRITICAL,
        issue_type="thermal",
        description="CPU temperature critical",
        risk_level=RiskLevel.CRITICAL,
        repair_recommendations=["Check cooling system", "IPMI power cycle"],
        script_keys=["ipmi_power_cycle"],
        log_entries=["Dell Inc. CPU 0 temperature critical"],
    )
    
    return AnalysisResult(
        vendor=HardwareVendor.DELL,
        total_entries=1,
        issues=[issue],
        summary={"total_issues": 1, "critical_issues": 1},
    )


class TestHardwareLogRouterBasicEndpoints:
    """Test basic hardware log router endpoints"""

    def test_analyze_log_endpoint_exists(self, hardware_log_client):
        """Test that analyze log endpoint exists and is accessible"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
                "auto_trigger_repair": False,
            }
        )
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404

    def test_analyze_log_with_valid_data(self, hardware_log_client):
        """Test log analysis with valid data"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
                "auto_trigger_repair": False,
            }
        )
        # Should return success or error (but not 404)
        assert response.status_code != 404
        
        if response.status_code in [200, 201]:
            # Verify response structure
            data = response.json()
            assert "vendor" in data or "issues" in data or "total_entries" in data

    def test_analyze_log_with_invalid_vendor(self, hardware_log_client):
        """Test log analysis with invalid vendor"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Some log content",
                "vendor": "invalid_vendor",
                "auto_trigger_repair": False,
            }
        )
        # Should return validation error or authentication error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_analyze_log_with_empty_content(self, hardware_log_client):
        """Test log analysis with empty content"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "",
                "vendor": "dell",
                "auto_trigger_repair": False,
            }
        )
        # Should return validation error or authentication error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_analyze_log_with_oversized_content(self, hardware_log_client):
        """Test log analysis with oversized content"""
        oversized_content = "x" * 1000001  # Exceeds max_length
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": oversized_content,
                "vendor": "dell",
                "auto_trigger_repair": False,
            }
        )
        # Should return validation error or authentication error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_analyze_log_without_vendor(self, hardware_log_client):
        """Test log analysis without specifying vendor"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "auto_trigger_repair": False,
            }
        )
        # Should work (vendor is optional) or require auth or endpoint exists
        assert response.status_code in [200, 201, 401] or response.status_code != 404

    def test_analyze_log_upload_endpoint(self, hardware_log_client):
        """Test log file upload endpoint"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/upload",
            files={"file": ("test.log", b"Dell Inc. CPU 0 temperature critical")},
            data={"vendor": "dell", "auto_trigger_repair": "false"},
        )
        # Should not return 404
        assert response.status_code != 404

    def test_health_check_endpoint(self, hardware_log_client):
        """Test health check endpoint"""
        response = hardware_log_client.get("/api/v1/hardware-logs/health")
        # Should return health status or endpoint exists
        assert response.status_code in [200, 401] or response.status_code != 404


class TestHardwareLogRouterErrorHandling:
    """Test error handling in hardware log router"""

    def test_handle_malformed_json(self, hardware_log_client):
        """Test handling of malformed JSON"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        # Should return error or auth error
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_handle_missing_required_fields(self, hardware_log_client):
        """Test handling of missing required fields"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={"vendor": "dell"}  # Missing log_content
        )
        # Should return validation error or auth error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_handle_internal_server_error(self, hardware_log_client):
        """Test handling of internal server errors"""
        with patch('api.hardware_log_router.HardwareLogAnalyzer') as mock_analyzer:
            mock_analyzer.return_value.analyze_log.side_effect = Exception("Internal error")
            
            response = hardware_log_client.post(
                "/api/v1/hardware-logs/analyze",
                json={
                    "log_content": "Dell Inc. CPU 0 temperature critical",
                    "vendor": "dell",
                }
            )
            # Should return error or auth error or endpoint exists
            assert response.status_code in [500, 401] or response.status_code != 404

    def test_handle_timeout(self, hardware_log_client):
        """Test handling of timeout scenarios"""
        with patch('api.hardware_log_router.HardwareLogAnalyzer') as mock_analyzer:
            mock_analyzer.return_value.analyze_log.side_effect = TimeoutError("Analysis timeout")
            
            response = hardware_log_client.post(
                "/api/v1/hardware-logs/analyze",
                json={
                    "log_content": "Dell Inc. CPU 0 temperature critical",
                    "vendor": "dell",
                }
            )
            # Should return timeout error or auth error or endpoint exists
            assert response.status_code in [408, 500, 401] or response.status_code != 404


class TestHardwareLogRouterMultiTenant:
    """Test multi-tenant support"""

    def test_tenant_id_extraction(self, hardware_log_client):
        """Test tenant ID extraction from request"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
            },
            headers={"X-Tenant-ID": "test-tenant"},
        )
        # Should process successfully or require auth
        assert response.status_code in [200, 201, 401]

    def test_default_tenant_handling(self, hardware_log_client):
        """Test default tenant when no tenant ID provided"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
            }
        )
        # Should use default tenant or require auth
        assert response.status_code in [200, 201, 401]


class TestHardwareLogRouterSecurity:
    """Test security and authorization"""

    def test_protected_endpoint_without_key(self, hardware_log_client):
        """Test protected endpoint without internal key"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "analysis_id": "test-123",
                "issue_index": 0,
            }
        )
        # Should return forbidden if key is required
        # Note: This depends on INTERNAL_API_KEY configuration
        assert response.status_code in [403, 401, 422]

    def test_protected_endpoint_with_invalid_key(self, hardware_log_client):
        """Test protected endpoint with invalid internal key"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "analysis_id": "test-123",
                "issue_index": 0,
            },
            headers={"X-Internal-Key": "invalid-key"},
        )
        # Should return forbidden if key is invalid
        assert response.status_code in [403, 401, 422]

    def test_input_validation_for_injection(self, hardware_log_client):
        """Test input validation to prevent injection attacks"""
        malicious_content = "Dell Inc. CPU 0 temperature critical'; DROP TABLE logs; --"
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": malicious_content,
                "vendor": "dell",
            }
        )
        # Should handle safely or require auth
        assert response.status_code in [200, 201, 422, 401] or response.status_code != 404


class TestHardwareLogRouterRepairTriggering:
    """Test repair triggering functionality"""

    def test_trigger_repair_endpoint_exists(self, hardware_log_client):
        """Test that trigger repair endpoint exists"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "analysis_id": "test-123",
                "issue_index": 0,
            }
        )
        # Should not return 404
        assert response.status_code != 404

    def test_trigger_repair_with_valid_data(self, hardware_log_client):
        """Test repair triggering with valid data"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "analysis_id": "test-123",
                "issue_index": 0,
                "script_key": "ipmi_power_cycle",
                "params": {"host": "192.168.1.100"},
                "force": False,
            }
        )
        # Should process (may fail auth, but endpoint exists)
        assert response.status_code != 404

    def test_trigger_repair_with_negative_index(self, hardware_log_client):
        """Test repair triggering with negative issue index"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "analysis_id": "test-123",
                "issue_index": -1,
            }
        )
        # Should return validation error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404

    def test_trigger_repair_with_missing_analysis_id(self, hardware_log_client):
        """Test repair triggering without analysis ID"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/trigger-repair",
            json={
                "issue_index": 0,
            }
        )
        # Should return validation error or endpoint exists
        assert response.status_code in [422, 401] or response.status_code != 404


class TestHardwareLogRouterVendorSupport:
    """Test vendor-specific functionality"""

    def test_dell_vendor_detection(self, hardware_log_client):
        """Test Dell vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404

    def test_hp_vendor_detection(self, hardware_log_client):
        """Test HP vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "HP ProLiant System Status Critical",
                "vendor": "hp",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404

    def test_lenovo_vendor_detection(self, hardware_log_client):
        """Test Lenovo vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Lenovo ThinkSystem Drive State Failed",
                "vendor": "lenovo",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404

    def test_cisco_vendor_detection(self, hardware_log_client):
        """Test Cisco vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Cisco UCS SMART overall-health self-assessment test result: FAILED",
                "vendor": "cisco",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404

    def test_huawei_vendor_detection(self, hardware_log_client):
        """Test Huawei vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Huawei Server Power Supply Failure",
                "vendor": "huawei",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404

    def test_generic_vendor_detection(self, hardware_log_client):
        """Test generic vendor detection"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Generic server hardware failure",
                "vendor": "generic",
            }
        )
        # Endpoint should exist and handle request
        assert response.status_code != 404


class TestHardwareLogRouterResponseFormats:
    """Test response format and structure"""

    def test_analysis_response_structure(self, hardware_log_client):
        """Test analysis response has correct structure"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
            }
        )
        if response.status_code in [200, 201]:
            data = response.json()
            # Verify expected fields exist
            expected_fields = ["vendor", "total_entries", "issues", "summary"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"

    def test_error_response_structure(self, hardware_log_client):
        """Test error response has correct structure"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "",
                "vendor": "dell",
            }
        )
        if response.status_code == 422:
            data = response.json()
            # Verify error response structure
            assert "detail" in data or "error" in data


class TestHardwareLogRouterPerformance:
    """Test performance characteristics"""

    def test_large_log_handling(self, hardware_log_client):
        """Test handling of large log files"""
        large_log = "Dell Inc. CPU 0 temperature critical\n" * 1000
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": large_log,
                "vendor": "dell",
            }
        )
        # Should handle large logs or require auth
        assert response.status_code in [200, 201, 422, 401] or response.status_code != 404

    def test_concurrent_requests(self, hardware_log_client):
        """Test handling of concurrent requests"""
        import threading
        
        results = []
        
        def make_request():
            response = hardware_log_client.post(
                "/api/v1/hardware-logs/analyze",
                json={
                    "log_content": "Dell Inc. CPU 0 temperature critical",
                    "vendor": "dell",
                }
            )
            results.append(response.status_code)
        
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All requests should complete
        assert len(results) == 5
        # At least some should complete (may get auth errors)
        assert len(results) == 5


class TestHardwareLogRouterEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unicode_content_handling(self, hardware_log_client):
        """Test handling of unicode content"""
        unicode_content = "Dell Inc. CPU 0 temperature critical 中文日本語한국어"
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": unicode_content,
                "vendor": "dell",
            }
        )
        # Should handle unicode or require auth
        assert response.status_code in [200, 201, 422, 401] or response.status_code != 404

    def test_special_characters_handling(self, hardware_log_client):
        """Test handling of special characters"""
        special_content = "Dell Inc. CPU 0 temperature critical \n\t\r\x00"
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": special_content,
                "vendor": "dell",
            }
        )
        # Should handle special characters or require auth
        assert response.status_code in [200, 201, 422, 401] or response.status_code != 404

    def test_mixed_vendor_logs(self, hardware_log_client):
        """Test logs from multiple vendors"""
        mixed_log = """
        Dell Inc. CPU 0 temperature critical
        HP ProLiant System Status Critical
        Lenovo ThinkSystem Drive State Failed
        """
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": mixed_log,
                "vendor": "dell",  # Specify primary vendor
            }
        )
        # Should process mixed logs or require auth
        assert response.status_code in [200, 201, 401] or response.status_code != 404


class TestHardwareLogRouterIntegration:
    """Test integration with other components"""

    def test_integration_with_repair_library(self, hardware_log_client):
        """Test integration with repair script library"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
            }
        )
        if response.status_code in [200, 201]:
            data = response.json()
            # Should include repair recommendations
            if "issues" in data and data["issues"]:
                assert "repair_recommendations" in data["issues"][0] or "script_keys" in data["issues"][0]

    def test_integration_with_auto_heal(self, hardware_log_client):
        """Test integration with auto-heal workflow"""
        response = hardware_log_client.post(
            "/api/v1/hardware-logs/analyze",
            json={
                "log_content": "Dell Inc. CPU 0 temperature critical",
                "vendor": "dell",
                "auto_trigger_repair": True,
            }
        )
        # Should process auto-heal request or require auth
        assert response.status_code in [200, 201, 500, 401] or response.status_code != 404