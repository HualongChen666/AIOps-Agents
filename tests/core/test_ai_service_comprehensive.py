# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/ai_service.py
Target: 90%+ statement and branch coverage
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.ai_service import (
    AIContextService,
    ai_context_service,
    _safe_alert_value,
    _safe_get_metric,
    _extract_gather_result,
)


class TestSafeAlertValue:
    """Test suite for _safe_alert_value helper function"""

    def test_none_value(self):
        """Test with None value"""
        result = _safe_alert_value(None)
        assert result is None

    def test_int_value(self):
        """Test with integer value"""
        result = _safe_alert_value(42)
        assert result == 42

    def test_float_value(self):
        """Test with float value"""
        result = _safe_alert_value(3.14)
        assert result == 3.14

    def test_bool_value(self):
        """Test with boolean value"""
        result = _safe_alert_value(True)
        assert result is True

    def test_valid_string_numeric(self):
        """Test with valid numeric string"""
        result = _safe_alert_value("123.45")
        assert result == 123.45

    def test_invalid_string_numeric(self):
        """Test with invalid numeric string"""
        result = _safe_alert_value("not_a_number")
        assert result == "not_a_number"

    def test_long_string_truncation(self):
        """Test that long strings are truncated"""
        long_string = "x" * 100
        result = _safe_alert_value(long_string)
        assert len(result) == 64

    def test_other_type(self):
        """Test with other types (should convert to string)"""
        result = _safe_alert_value([1, 2, 3])
        assert isinstance(result, str)


class TestSafeGetMetric:
    """Test suite for _safe_get_metric helper function"""

    def test_valid_nested_dict(self):
        """Test with valid nested dictionary"""
        snapshot = {
            "cpu": {
                "usage": 75.5
            }
        }
        result = _safe_get_metric(snapshot, "cpu", "usage")
        assert result == 75.5

    def test_missing_section(self):
        """Test with missing section"""
        snapshot = {"cpu": {}}
        result = _safe_get_metric(snapshot, "memory", "usage", default="N/A")
        assert result == "N/A"

    def test_missing_field(self):
        """Test with missing field"""
        snapshot = {"cpu": {}}
        result = _safe_get_metric(snapshot, "cpu", "usage", default="N/A")
        assert result == "N/A"

    def test_non_dict_snapshot(self):
        """Test with non-dict snapshot"""
        result = _safe_get_metric(None, "cpu", "usage", default="N/A")
        assert result == "N/A"

    def test_non_dict_section(self):
        """Test with non-dict section"""
        snapshot = {"cpu": "not_a_dict"}
        result = _safe_get_metric(snapshot, "cpu", "usage", default="N/A")
        assert result == "N/A"

    def test_default_value(self):
        """Test custom default value"""
        snapshot = {}
        result = _safe_get_metric(snapshot, "cpu", "usage", default="DEFAULT")
        assert result == "DEFAULT"


class TestExtractGatherResult:
    """Test suite for _extract_gather_result helper function"""

    def test_cancelled_error(self):
        """Test with CancelledError"""
        result = _extract_gather_result(asyncio.CancelledError(), "test", dict)
        assert result is None

    def test_generic_exception(self):
        """Test with generic exception"""
        result = _extract_gather_result(ValueError("test"), "test", dict)
        assert result is None

    def test_none_result(self):
        """Test with None result"""
        result = _extract_gather_result(None, "test", dict)
        assert result is None

    def test_correct_type(self):
        """Test with correct type"""
        result = _extract_gather_result({"key": "value"}, "test", dict)
        assert result == {"key": "value"}

    def test_incorrect_type(self):
        """Test with incorrect type"""
        result = _extract_gather_result("not_a_dict", "test", dict)
        assert result is None

    def test_list_expected_type(self):
        """Test with list expected type"""
        result = _extract_gather_result([1, 2, 3], "test", list)
        assert result == [1, 2, 3]


class TestAIContextService:
    """Test suite for AIContextService class"""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for each test"""
        return AIContextService()

    @pytest.mark.asyncio
    async def test_collect_rich_context_basic(self, service):
        """Test basic rich context collection"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {
                "top_processes": [{"pid": 1, "name": "init"}],
                "cpu": {"usage": 50.0},
                "memory": {"total": 8000, "used": 4000}
            }
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert isinstance(result, dict)
                        assert "top_processes" in result
                        assert "recent_alerts" in result
                        assert "recent_repairs" in result
                        assert "stats" in result
                        assert "service_metrics" in result
                        assert "infrastructure_metrics" in result
                        assert "topology" in result
                        assert "dependencies" in result
                        assert "upstream_callers" in result
                        assert "downstream_dependencies" in result
                        assert "change_events" in result
                        assert "correlated_alerts" in result

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_snapshot(self, service):
        """Test rich context collection with provided snapshot"""
        snapshot = {
            "top_processes": [{"pid": 1, "name": "init"}],
            "cpu": {"usage": 50.0}
        }
        
        with patch('core.ai_service.alert_history', []):
            with patch('core.ai_service.repair_history', []):
                with patch('core.ai_service.metrics_history') as mock_metrics:
                    mock_metrics.get_stats.return_value = {}
                    
                    result = await service.collect_rich_context(snapshot=snapshot)
                    
                    assert result["top_processes"] == [{"pid": 1, "name": "init"}]

    @pytest.mark.asyncio
    async def test_collect_rich_context_with_service_name(self, service):
        """Test rich context collection with service name"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        with patch('core.ai_service.get_service_monitoring_manager') as mock_mgr:
                            mock_mgr.return_value.get_service_metrics.return_value = []
                            
                            with patch('core.ai_service.get_full_link_topology') as mock_topo:
                                mock_topo.return_value = {"nodes": [], "edges": []}
                                
                                result = await service.collect_rich_context(service_name="test-service")
                                
                                assert "service_metrics" in result
                                assert "topology" in result

    @pytest.mark.asyncio
    async def test_collect_rich_context_snapshot_fetch_failure(self, service):
        """Test handling of snapshot fetch failure"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.side_effect = Exception("Fetch failed")
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        # Should still return result with empty data
                        assert isinstance(result, dict)
                        assert result["top_processes"] == []

    @pytest.mark.asyncio
    async def test_fetch_processes(self, service):
        """Test _fetch_processes data source"""
        snapshot = {
            "top_processes": [
                {"pid": 1, "name": "init"},
                {"pid": 2, "name": "kthreadd"},
                {"pid": 3, "name": "rcu_gp"}
            ]
        }
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = snapshot
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["top_processes"]) == 3
                        assert result["top_processes"][0]["pid"] == 1

    @pytest.mark.asyncio
    async def test_fetch_processes_limit(self, service):
        """Test _fetch_processes limits to 5 processes"""
        snapshot = {
            "top_processes": [{"pid": i, "name": f"proc_{i}"} for i in range(10)]
        }
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = snapshot
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["top_processes"]) == 5

    @pytest.mark.asyncio
    async def test_fetch_processes_not_list(self, service):
        """Test _fetch_processes handles non-list data"""
        snapshot = {"top_processes": "not_a_list"}
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = snapshot
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert result["top_processes"] == []

    @pytest.mark.asyncio
    async def test_fetch_alerts(self, service):
        """Test _fetch_alerts data source"""
        alert_history = [
            {
                "level": "critical",
                "title": "High CPU",
                "desc": "CPU usage above 90%",
                "raw_time": "2024-01-01 12:00:00",
                "metric": "cpu_usage",
                "value": 95.5,
                "host": "server1",
                "source": "prometheus"
            }
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_alerts"]) == 1
                        assert result["recent_alerts"][0]["level"] == "critical"
                        assert result["recent_alerts"][0]["value"] == 95.5

    @pytest.mark.asyncio
    async def test_fetch_alerts_limit(self, service):
        """Test _fetch_alerts limits to 10 alerts"""
        alert_history = [
            {"level": "info", "title": f"Alert {i}", "desc": "", "raw_time": "", "metric": "", "value": 0, "host": "", "source": ""}
            for i in range(15)
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_alerts"]) == 10

    @pytest.mark.asyncio
    async def test_fetch_alerts_non_dict(self, service):
        """Test _fetch_alerts handles non-dict entries"""
        alert_history = ["not_a_dict", {"level": "info", "title": "Valid", "desc": "", "raw_time": "", "metric": "", "value": 0, "host": "", "source": ""}]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_alerts"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_alerts_field_truncation(self, service):
        """Test _fetch_alerts truncates long fields"""
        alert_history = [
            {
                "level": "info",
                "title": "x" * 300,
                "desc": "y" * 600,
                "raw_time": "z" * 50,
                "metric": "a" * 80,
                "value": 0,
                "host": "b" * 80,
                "source": "c" * 80
            }
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_alerts"][0]["title"]) == 200
                        assert len(result["recent_alerts"][0]["desc"]) == 500
                        assert len(result["recent_alerts"][0]["raw_time"]) == 32
                        assert len(result["recent_alerts"][0]["metric"]) == 64
                        assert len(result["recent_alerts"][0]["host"]) == 64
                        assert len(result["recent_alerts"][0]["source"]) == 64

    @pytest.mark.asyncio
    async def test_fetch_repairs(self, service):
        """Test _fetch_repairs data source"""
        repair_history = [
            {"id": 1, "action": "restart", "status": "success"},
            {"id": 2, "action": "kill", "status": "success"}
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', repair_history):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_repairs"]) == 2

    @pytest.mark.asyncio
    async def test_fetch_repairs_limit(self, service):
        """Test _fetch_repairs limits to 5 repairs"""
        repair_history = [{"id": i} for i in range(10)]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', repair_history):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["recent_repairs"]) == 5

    @pytest.mark.asyncio
    async def test_fetch_stats_with_get_stats(self, service):
        """Test _fetch_stats with get_stats method"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {"total": 100, "success": 95}
                        
                        result = await service.collect_rich_context()
                        
                        assert result["stats"] == {"total": 100, "success": 95}

    @pytest.mark.asyncio
    async def test_fetch_stats_with_to_dict(self, service):
        """Test _fetch_stats with to_dict method"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        # Remove get_stats, add to_dict
                        del mock_metrics.get_stats
                        mock_metrics.to_dict.return_value = {"total": 50}
                        
                        result = await service.collect_rich_context()
                        
                        assert result["stats"] == {"total": 50}

    @pytest.mark.asyncio
    async def test_fetch_stats_no_method(self, service):
        """Test _fetch_stats when no method available"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        # Remove both methods
                        del mock_metrics.get_stats
                        del mock_metrics.to_dict
                        
                        result = await service.collect_rich_context()
                        
                        assert result["stats"] == {}

    @pytest.mark.asyncio
    async def test_fetch_service_metrics_no_service_name(self, service):
        """Test _fetch_service_metrics when no service name provided"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert result["service_metrics"] == {}

    @pytest.mark.asyncio
    async def test_fetch_infrastructure_metrics(self, service):
        """Test _fetch_infrastructure_metrics data source"""
        snapshot = {
            "cpu": {"usage": 50.0},
            "memory": {"total": 8000, "used": 4000},
            "disk": [{"device": "/dev/sda1", "usage": 80}],
            "network": {"rx": 1000, "tx": 500},
            "system": {"uptime": 3600}
        }
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = snapshot
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert result["infrastructure_metrics"]["cpu"] == {"usage": 50.0}
                        assert result["infrastructure_metrics"]["memory"] == {"total": 8000, "used": 4000}
                        assert result["infrastructure_metrics"]["disk"] == [{"device": "/dev/sda1", "usage": 80}]

    @pytest.mark.asyncio
    async def test_fetch_topology(self, service):
        """Test _fetch_topology data source"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        with patch('core.ai_service.get_full_link_topology') as mock_topo:
                            mock_topo.return_value = {
                                "nodes": ["service_a", "service_b"],
                                "edges": [
                                    {"source": "service_a", "target": "service_b"}
                                ]
                            }
                            
                            result = await service.collect_rich_context()
                            
                            assert result["topology"]["nodes"] == ["service_a", "service_b"]
                            assert result["topology"]["edges"] == [{"source": "service_a", "target": "service_b"}]
                            assert result["dependencies"]["service_a"] == ["service_b"]

    @pytest.mark.asyncio
    async def test_fetch_topology_with_from_to(self, service):
        """Test _fetch_topology with 'from'/'to' edge format"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        with patch('core.ai_service.get_full_link_topology') as mock_topo:
                            mock_topo.return_value = {
                                "nodes": [],
                                "edges": [
                                    {"from": "service_a", "to": "service_b"}
                                ]
                            }
                            
                            result = await service.collect_rich_context()
                            
                            assert result["dependencies"]["service_a"] == ["service_b"]

    @pytest.mark.asyncio
    async def test_fetch_topology_non_dict(self, service):
        """Test _fetch_topology handles non-dict response"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        with patch('core.ai_service.get_full_link_topology') as mock_topo:
                            mock_topo.return_value = "not_a_dict"
                            
                            result = await service.collect_rich_context()
                            
                            assert result["topology"] == {}

    @pytest.mark.asyncio
    async def test_fetch_change_events(self, service):
        """Test _fetch_change_events data source"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        with patch('core.ai_service.config_manager') as mock_config:
                            mock_config._audit_log = [
                                {
                                    "timestamp": "2024-01-01T12:00:00",
                                    "change": "config_update",
                                    "details": "Updated threshold"
                                }
                            ]
                            mock_config._config_history = []
                            
                            result = await service.collect_rich_context()
                            
                            assert len(result["change_events"]) == 1
                            assert result["change_events"][0]["type"] == "config_change"

    @pytest.mark.asyncio
    async def test_fetch_correlated_alerts(self, service):
        """Test _fetch_correlated_alerts data source"""
        alert_history = [
            {
                "level": "warning",
                "title": "High Memory on test-service",
                "desc": "Memory usage high",
                "raw_time": "2024-01-01 12:00:00",
                "source": "prometheus",
                "host": "server1"
            }
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context(service_name="test-service")
                        
                        # Should include alert matching service name
                        assert len(result["correlated_alerts"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_correlated_alerts_no_service_filter(self, service):
        """Test _fetch_correlated_alerts without service filter"""
        alert_history = [
            {
                "level": "warning",
                "title": "Alert",
                "desc": "Test",
                "raw_time": "2024-01-01 12:00:00",
                "source": "prometheus",
                "host": "server1"
            }
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        # Should include all alerts when no service filter
                        assert len(result["correlated_alerts"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_correlated_alerts_limit(self, service):
        """Test _fetch_correlated_alerts limits to 20 alerts"""
        alert_history = [
            {
                "level": "info",
                "title": f"Alert {i}",
                "desc": "Test",
                "raw_time": "2024-01-01 12:00:00",
                "source": "prometheus",
                "host": "server1"
            }
            for i in range(25)
        ]
        
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', alert_history):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats.return_value = {}
                        
                        result = await service.collect_rich_context()
                        
                        assert len(result["correlated_alerts"]) == 20

    @pytest.mark.asyncio
    async def test_timeout_handling(self, service):
        """Test timeout handling in data source collection"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats = AsyncMock(side_effect=asyncio.TimeoutError())
                        
                        result = await service.collect_rich_context()
                        
                        # Should handle timeout gracefully
                        assert isinstance(result, dict)
                        assert "stats" in result

    @pytest.mark.asyncio
    async def test_cancelled_error_propagation(self, service):
        """Test that CancelledError is propagated"""
        with patch('core.ai_service.get_cached_snapshot') as mock_snapshot:
            mock_snapshot.return_value = {}
            
            with patch('core.ai_service.alert_history', []):
                with patch('core.ai_service.repair_history', []):
                    with patch('core.ai_service.metrics_history') as mock_metrics:
                        mock_metrics.get_stats = AsyncMock(side_effect=asyncio.CancelledError())
                        
                        with pytest.raises(asyncio.CancelledError):
                            await service.collect_rich_context()


class TestGlobalServiceInstance:
    """Test suite for global service instance"""

    def test_global_service_instance(self):
        """Test that ai_context_service is a singleton"""
        assert isinstance(ai_context_service, AIContextService)
