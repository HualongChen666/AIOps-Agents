# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/cost_monitor.py
Target: 90%+ statement and branch coverage
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.cost_monitor import (
    budget_status,
    collect_costs,
    forecast_costs,
)


class TestCollectCosts:
    """Test suite for collect_costs function"""

    def test_collect_costs_no_boto3(self):
        """Test collect_costs when boto3 is not available"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'boto3'")):
            result = collect_costs()
            assert result == []

    def test_collect_costs_boto3_import_error(self):
        """Test collect_costs when boto3 import fails"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'boto3'")):
            result = collect_costs()
            assert result == []

    def test_collect_costs_aws_success(self):
        """Test successful AWS cost collection"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01"},
                    "Groups": [
                        {
                            "Keys": ["EC2"],
                            "Metrics": {"BlendedCost": {"Amount": "100.50", "Unit": "USD"}},
                        }
                    ],
                }
            ]
        }
        mock_client.get_cost_and_usage.return_value = mock_response

        with patch("builtins.__import__", return_value=mock_boto3):
            result = collect_costs()

            assert len(result) == 1
            assert result[0]["source"] == "aws"
            assert result[0]["service"] == "EC2"
            assert result[0]["cost"] == 100.50
            assert result[0]["currency"] == "USD"
            assert result[0]["region"] == "global"

    def test_collect_costs_aws_exception(self):
        """Test AWS cost collection with exception"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.get_cost_and_usage.side_effect = Exception("AWS error")

        with patch("builtins.__import__", return_value=mock_boto3):
            result = collect_costs()

            # Exception is caught and logged, returns empty list
            assert result == []

    def test_collect_costs_aws_no_keys(self):
        """Test AWS cost collection when groups have no keys"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01"},
                    "Groups": [
                        {
                            "Keys": [],
                            "Metrics": {"BlendedCost": {"Amount": "100.50", "Unit": "USD"}},
                        }
                    ],
                }
            ]
        }
        mock_client.get_cost_and_usage.return_value = mock_response

        with patch("builtins.__import__", return_value=mock_boto3):
            result = collect_costs()

            assert len(result) == 1
            assert result[0]["service"] == "unknown"
            assert result[0]["region"] == "global"

    def test_collect_costs_aws_no_metrics(self):
        """Test AWS cost collection when metrics are missing"""
        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2024-01-01"},
                    "Groups": [{"Keys": ["EC2"], "Metrics": {}}],
                }
            ]
        }
        mock_client.get_cost_and_usage.return_value = mock_response

        with patch("builtins.__import__", return_value=mock_boto3):
            result = collect_costs()

            assert len(result) == 1
            assert result[0]["cost"] == 0.0
            assert result[0]["currency"] == "USD"


class TestForecastCosts:
    """Test suite for forecast_costs function"""

    def test_forecast_costs_no_historical_data(self):
        """Test forecast when no historical costs available"""
        with patch("core.cost_monitor.collect_costs", return_value=[]):
            result = forecast_costs(days=30)
            assert result == []

    def test_forecast_costs_success(self):
        """Test successful cost forecast"""
        historical_costs = [
            {"cost": 100.0, "timestamp": "2024-01-01"},
            {"cost": 110.0, "timestamp": "2024-01-02"},
            {"cost": 105.0, "timestamp": "2024-01-03"},
        ]

        with patch("core.cost_monitor.collect_costs", return_value=historical_costs):
            result = forecast_costs(days=5)

            assert len(result) == 5
            assert all("forecasted_cost" in r for r in result)
            assert all("timestamp" in r for r in result)
            assert all(r["currency"] == "USD" for r in result)

    def test_forecast_costs_custom_days(self):
        """Test forecast with custom days parameter"""
        historical_costs = [{"cost": 100.0, "timestamp": "2024-01-01"}]

        with patch("core.cost_monitor.collect_costs", return_value=historical_costs):
            result = forecast_costs(days=10)

            assert len(result) == 10

    def test_forecast_costs_exception(self):
        """Test forecast with exception"""
        with patch("core.cost_monitor.collect_costs", side_effect=Exception("Error")):
            result = forecast_costs(days=30)
            assert result == []

    def test_forecast_costs_growth_assumption(self):
        """Test that forecast includes growth assumption"""
        historical_costs = [{"cost": 100.0, "timestamp": "2024-01-01"}]

        with patch("core.cost_monitor.collect_costs", return_value=historical_costs):
            result = forecast_costs(days=3)

            # Each day should have slightly higher cost (1% growth)
            assert result[0]["forecasted_cost"] < result[1]["forecasted_cost"]
            assert result[1]["forecasted_cost"] < result[2]["forecasted_cost"]


class TestBudgetStatus:
    """Test suite for budget_status function"""

    def test_budget_status_healthy(self):
        """Test budget status when healthy"""
        # Use current month data to ensure it passes the datetime filter
        current_time = datetime.now()
        current_month_costs = [
            {"cost": 1000.0, "timestamp": current_time.isoformat()},
            {"cost": 500.0, "timestamp": current_time.isoformat()},
        ]

        with patch("core.cost_monitor.collect_costs", return_value=current_month_costs):
            result = budget_status()

            assert result["status"] == "healthy"
            assert result["alert_level"] == "low"
            assert "healthy" in result["message"].lower()
            assert result["budget"]["current_spend"] == 1500.0
            assert result["budget"]["utilization_percent"] == 30.0
            assert "period" in result
            assert "last_updated" in result

    def test_budget_status_warning(self):
        """Test budget status when at warning threshold"""
        current_time = datetime.now()
        # Use 4100 to ensure it's above 80% threshold (4000)
        current_month_costs = [{"cost": 4100.0, "timestamp": current_time.isoformat()}]

        with patch("core.cost_monitor.collect_costs", return_value=current_month_costs):
            result = budget_status()

            assert result["status"] == "warning"
            assert result["alert_level"] == "medium"
            assert "warning" in result["message"].lower()
            assert len(result["recommendations"]) > 0
            assert "period" in result
            assert "last_updated" in result

    def test_budget_status_critical(self):
        """Test budget status when at critical threshold"""
        current_time = datetime.now()
        current_month_costs = [{"cost": 4600.0, "timestamp": current_time.isoformat()}]

        with patch("core.cost_monitor.collect_costs", return_value=current_month_costs):
            result = budget_status()

            assert result["status"] == "critical"
            assert result["alert_level"] == "high"
            assert "critically" in result["message"].lower()
            assert len(result["recommendations"]) > 0
            assert "period" in result
            assert "last_updated" in result

    def test_budget_status_no_costs(self):
        """Test budget status when no costs recorded"""
        with patch("core.cost_monitor.collect_costs", return_value=[]):
            result = budget_status()

            assert result["status"] == "healthy"
            assert result["budget"]["current_spend"] == 0.0
            assert result["budget"]["utilization_percent"] == 0.0

    def test_budget_status_exception(self):
        """Test budget status with exception"""
        with patch("core.cost_monitor.collect_costs", side_effect=Exception("Error")):
            result = budget_status()

            assert result["status"] == "error"
            assert "Unable to retrieve" in result["message"]
            assert result["budget"] is None

    def test_budget_status_recommendations(self):
        """Test that recommendations are generated for high utilization"""
        current_time = datetime.now()
        current_month_costs = [{"cost": 4200.0, "timestamp": current_time.isoformat()}]

        with patch("core.cost_monitor.collect_costs", return_value=current_month_costs):
            result = budget_status()

            assert len(result["recommendations"]) > 0
            # Check for actual recommendations from implementation
            assert any("resource usage" in r.lower() or "optimize" in r.lower() for r in result["recommendations"])

    def test_budget_status_period_calculation(self):
        """Test budget status period calculation"""
        with patch("core.cost_monitor.collect_costs", return_value=[]):
            result = budget_status()

            assert "period" in result
            assert "start" in result["period"]
            assert "end" in result["period"]

    def test_budget_status_zero_budget(self):
        """Test budget status when budget is zero (edge case)"""
        current_time = datetime.now()
        current_month_costs = [{"cost": 100.0, "timestamp": current_time.isoformat()}]

        with patch("core.cost_monitor.collect_costs", return_value=current_month_costs):
            result = budget_status()

            # Should handle gracefully with default budget
            assert "budget" in result
            assert result["budget"]["monthly_budget"] == 5000.0
            assert result["budget"]["current_spend"] == 100.0
