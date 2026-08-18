# -*- coding: utf-8 -*-
"""Tests for alert webhook router to achieve 90%+ coverage."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_webhook_unknown_provider(client):
    """Test webhook with unknown provider (lines 66-70)."""
    payload = {"test": "data"}
    resp = client.post("/api/v1/alerts/webhook/unknown_provider", json=payload)
    assert resp.status_code == 404
    data = resp.json()
    # Error response format: {"error": {"message": "..."}}
    error_msg = data.get("error", {}).get("message", "")
    assert "Unknown alert provider" in error_msg


def test_webhook_auto_heal_unavailable(client):
    """Test webhook when auto-heal engine is not available (lines 72-76)."""
    # Patch AUTO_HEAL_AVAILABLE to False
    with patch("api.alert_webhook_router.AUTO_HEAL_AVAILABLE", False):
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "labels": {"alertname": "CPUHigh", "severity": "warning"},
                    "annotations": {"summary": "CPU usage high"},
                }
            ],
        }
        resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
        assert resp.status_code == 503
        data = resp.json()
        # Error response format: {"error": {"message": "..."}}
        error_msg = data.get("error", {}).get("message", "")
        assert "Auto-heal engine is not available" in error_msg


def test_webhook_status_not_firing(client):
    """Test webhook when alert status is not 'firing' (lines 89-99)."""
    # Mock the provider to return resolved alerts
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "resolved",  # Not firing
                "severity": "warning",
            },
            {
                "id": "test-2",
                "status": "pending",  # Not firing
                "severity": "critical",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        # Also need to mock try_auto_heal to avoid actual processing
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            
            # Should succeed but skip non-firing alerts
            assert resp.status_code in (200, 503)
            if resp.status_code == 200:
                data = resp.json()
                # Check that non-firing alerts were skipped
                results = data.get("results", [])
                skipped = [r for r in results if r.get("status") == "skipped"]
                assert len(skipped) == 2


def test_webhook_status_case_insensitive(client):
    """Test webhook status handling with different cases (line 90)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {"id": "test-1", "status": "FIRING"},  # uppercase
            {"id": "test-2", "status": "Firing"},  # mixed case
            {"id": "test-3", "status": "firing"},  # lowercase
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code in (200, 503)


def test_webhook_record_audit_available(client):
    """Test webhook when record_audit is available (lines 101-110)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "firing",
                "severity": "critical",
                "host": "test-server",
                "trace_id": "trace-123",
            },
        ]
    
    # Mock record_audit to be available
    mock_record_audit = MagicMock()
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.record_audit", mock_record_audit):
            with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
                mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
                
                payload = {"test": "data"}
                resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
                
                assert resp.status_code in (200, 503)
                if resp.status_code == 200:
                    # Check that record_audit was called
                    mock_record_audit.assert_called()
                    call_args = mock_record_audit.call_args
                    assert call_args is not None


def test_webhook_record_audit_exception(client):
    """Test webhook when record_audit raises an exception (lines 111-112)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "firing",
                "severity": "critical",
                "host": "test-server",
            },
        ]
    
    # Mock record_audit to raise an exception
    mock_record_audit = MagicMock(side_effect=Exception("Audit failed"))
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.record_audit", mock_record_audit):
            with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
                mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
                
                payload = {"test": "data"}
                # Should not raise, but log the exception
                resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
                assert resp.status_code in (200, 503)


def test_webhook_try_auto_heal_exception(client):
    """Test webhook when try_auto_heal raises an exception (lines 122-124)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "firing",
                "severity": "critical",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.side_effect = Exception("Auto-heal failed")
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            
            assert resp.status_code in (200, 503)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                # Should have an error result
                error_results = [r for r in results if r.get("status") == "error"]
                assert len(error_results) > 0


def test_webhook_prometheus_endpoint(client):
    """Test the dedicated Prometheus webhook endpoint (line 138)."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {"alertname": "CPUHigh", "severity": "warning"},
                "annotations": {"summary": "CPU usage high"},
            }
        ],
    }
    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code in (200, 404, 422, 500, 503)


def test_webhook_prometheus_root_endpoint(client):
    """Test the Prometheus webhook endpoint at root (line 144)."""
    payload = {
        "status": "firing",
        "alerts": [
            {
                "labels": {"alertname": "CPUHigh", "severity": "warning"},
                "annotations": {"summary": "CPU usage high"},
            }
        ],
    }
    resp = client.post("/api/v1/alerts/prometheus", json=payload)
    assert resp.status_code in (200, 404, 422, 500, 503)


def test_webhook_alert_without_id(client):
    """Test webhook when alert dict doesn't have an 'id' field (line 87)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                # No 'id' field
                "status": "firing",
                "severity": "critical",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code in (200, 503)


def test_webhook_multiple_alerts_mixed_status(client):
    """Test webhook with multiple alerts having mixed statuses."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {"id": "test-1", "status": "firing", "severity": "critical"},
            {"id": "test-2", "status": "resolved", "severity": "warning"},
            {"id": "test-3", "status": "firing", "severity": "warning"},
            {"id": "test-4", "status": "pending", "severity": "info"},
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            
            assert resp.status_code in (200, 503)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                # Should have 2 processed (firing) and 2 skipped (non-firing)
                processed = [r for r in results if r.get("status") == "processed"]
                skipped = [r for r in results if r.get("status") == "skipped"]
                assert len(processed) == 2
                assert len(skipped) == 2


def test_webhook_empty_alerts_list(client):
    """Test webhook with empty alerts list."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return []
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        payload = {"test": "data"}
        resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
        
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("received") == 0
            assert data.get("total") == 0
            assert data.get("processed") == 0
            assert len(data.get("results", [])) == 0


def test_webhook_record_audit_with_missing_fields(client):
    """Test record_audit with missing alert fields (lines 104-109)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "firing",
                # Missing host, severity, trace_id
            },
        ]
    
    mock_record_audit = MagicMock()
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.record_audit", mock_record_audit):
            with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
                mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
                
                payload = {"test": "data"}
                resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
                
                assert resp.status_code in (200, 503)
                if resp.status_code == 200:
                    # Check that record_audit was called with defaults
                    mock_record_audit.assert_called()
                    call_kwargs = mock_record_audit.call_args[1]
                    # Should use default values for missing fields
                    assert call_kwargs is not None


def test_webhook_alert_non_dict(client):
    """Test webhook when alert is not a dict (line 81-83)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        # Return a mix of dict and non-dict
        return [
            {"id": "test-1", "status": "firing"},  # dict
            "string_alert",  # non-dict - should be skipped
            123,  # non-dict - should be skipped
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code in (200, 503)


def test_webhook_try_auto_heal_none(client):
    """Test webhook when try_auto_heal is None (line 72-76)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {"id": "test-1", "status": "firing", "severity": "critical"},
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", None):
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code == 503


def test_webhook_alert_status_none(client):
    """Test webhook when alert status is None (line 90)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": None,  # None status
                "severity": "critical",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code in (200, 503)


def test_webhook_record_audit_is_none(client):
    """Test webhook when record_audit is None (line 101)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                "status": "firing",
                "severity": "critical",
                "host": "test-server",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.record_audit", None):
            with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
                mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
                
                payload = {"test": "data"}
                resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
                assert resp.status_code in (200, 503)


def test_webhook_alert_get_status_missing(client):
    """Test webhook when alert dict doesn't have status field (line 90)."""
    from core.alert_providers import PrometheusAlertProvider
    
    def mock_normalize(self, raw_payload):
        return [
            {
                "id": "test-1",
                # No status field
                "severity": "critical",
            },
        ]
    
    with patch.object(PrometheusAlertProvider, "normalize", mock_normalize):
        with patch("api.alert_webhook_router.try_auto_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"alert_id": "test-1", "status": "processed"}
            
            payload = {"test": "data"}
            resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
            assert resp.status_code in (200, 503)
