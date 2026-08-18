# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/performance_report_generator.py
Target: 90%+ statement and branch coverage
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.performance_report_generator import (
    PerformanceReportGenerator,
    generate_performance_report,
)


class TestPerformanceReportGenerator:
    """Test suite for PerformanceReportGenerator class"""

    @pytest.fixture
    def generator(self):
        """Create a fresh generator instance for each test"""
        return PerformanceReportGenerator()

    @pytest.mark.asyncio
    async def test_context_manager(self, generator):
        """Test async context manager"""
        async with generator as gen:
            assert gen is generator
            assert gen.session is not None

    @pytest.mark.asyncio
    async def test_generate_daily_report_success(self, generator):
        """Test successful daily report generation"""
        mock_metrics = [
            MagicMock(
                component="service_a",
                p95_time_ms=100.0,
                throughput_ops=1000.0,
                error_count=5
            ),
            MagicMock(
                component="service_b",
                p95_time_ms=150.0,
                throughput_ops=800.0,
                error_count=2
            )
        ]
        
        mock_regressions = [
            MagicMock(
                regression_id=1,
                component="service_a",
                severity="high",
                deviation=0.15
            )
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            # Mock execute for metrics
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            # Mock execute for regressions
            mock_result2 = MagicMock()
            mock_result2.scalars.return_value.all.return_value = mock_regressions
            mock_session_instance.execute.side_effect = [mock_result, mock_result2]
            
            result = await generator.generate_daily_report(environment="dev")
            
            assert result["report_type"] == "daily"
            assert result["environment"] == "dev"
            assert result["summary"]["total_tests"] == 2
            assert result["summary"]["total_components"] == 2
            assert result["summary"]["total_regressions"] == 1
            assert "service_a" in result["component_stats"]
            assert "service_b" in result["component_stats"]

    @pytest.mark.asyncio
    async def test_generate_daily_report_with_date(self, generator):
        """Test daily report generation with specific date"""
        specific_date = datetime(2024, 1, 15)
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_daily_report(
                environment="dev",
                date=specific_date
            )
            
            assert result["date"] == "2024-01-15"

    @pytest.mark.asyncio
    async def test_generate_daily_report_exception(self, generator):
        """Test daily report generation with exception"""
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session_instance.execute.side_effect = Exception("DB error")
            
            result = await generator.generate_daily_report(environment="dev")
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_generate_weekly_report_success(self, generator):
        """Test successful weekly report generation"""
        mock_metrics = [
            MagicMock(
                timestamp=datetime(2024, 1, 1),
                p95_time_ms=100.0
            ),
            MagicMock(
                timestamp=datetime(2024, 1, 2),
                p95_time_ms=110.0
            )
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_weekly_report(environment="dev")
            
            assert result["report_type"] == "weekly"
            assert result["environment"] == "dev"
            assert "daily_stats" in result

    @pytest.mark.asyncio
    async def test_generate_weekly_report_with_start_date(self, generator):
        """Test weekly report generation with specific start date"""
        start_date = datetime(2024, 1, 1)
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_weekly_report(
                environment="dev",
                start_date=start_date
            )
            
            assert result["start_date"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_generate_weekly_report_exception(self, generator):
        """Test weekly report generation with exception"""
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session_instance.execute.side_effect = Exception("DB error")
            
            result = await generator.generate_weekly_report(environment="dev")
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_generate_monthly_report_success(self, generator):
        """Test successful monthly report generation"""
        mock_metrics = [
            MagicMock(
                timestamp=datetime(2024, 1, 1),
                p95_time_ms=100.0
            ),
            MagicMock(
                timestamp=datetime(2024, 1, 8),
                p95_time_ms=110.0
            )
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_monthly_report(
                environment="dev",
                year=2024,
                month=1
            )
            
            assert result["report_type"] == "monthly"
            assert result["year"] == 2024
            assert result["month"] == 1
            assert "weekly_stats" in result

    @pytest.mark.asyncio
    async def test_generate_monthly_report_december(self, generator):
        """Test monthly report generation for December (year boundary)"""
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_monthly_report(
                environment="dev",
                year=2024,
                month=12
            )
            
            assert result["year"] == 2024
            assert result["month"] == 12

    @pytest.mark.asyncio
    async def test_generate_monthly_report_exception(self, generator):
        """Test monthly report generation with exception"""
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session_instance.execute.side_effect = Exception("DB error")
            
            result = await generator.generate_monthly_report(environment="dev")
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_success(self, generator):
        """Test successful trend analysis generation"""
        mock_metrics = [
            MagicMock(
                timestamp=datetime(2024, 1, 1),
                p95_time_ms=100.0
            ),
            MagicMock(
                timestamp=datetime(2024, 1, 15),
                p95_time_ms=110.0
            )
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30,
                environment="dev"
            )
            
            assert result["component"] == "service_a"
            assert result["metric_name"] == "p95_time_ms"
            assert result["days"] == 30
            assert result["data_points"] == 2
            assert result["trend_direction"] in ["up", "down", "stable"]

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_upward_trend(self, generator):
        """Test trend analysis with upward trend"""
        mock_metrics = [
            MagicMock(timestamp=datetime(2024, 1, 1), p95_time_ms=100.0),
            MagicMock(timestamp=datetime(2024, 1, 15), p95_time_ms=150.0)
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result["trend_direction"] == "up"
            assert result["change_percentage"] > 0

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_downward_trend(self, generator):
        """Test trend analysis with downward trend"""
        mock_metrics = [
            MagicMock(timestamp=datetime(2024, 1, 1), p95_time_ms=150.0),
            MagicMock(timestamp=datetime(2024, 1, 15), p95_time_ms=100.0)
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result["trend_direction"] == "down"
            assert result["change_percentage"] < 0

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_insufficient_data(self, generator):
        """Test trend analysis with insufficient data points"""
        mock_metrics = [
            MagicMock(timestamp=datetime(2024, 1, 1), p95_time_ms=100.0)
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result["trend_direction"] == "stable"
            assert result["change_percentage"] == 0

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_zero_first_value(self, generator):
        """Test trend analysis when first value is zero"""
        mock_metrics = [
            MagicMock(timestamp=datetime(2024, 1, 1), p95_time_ms=0.0),
            MagicMock(timestamp=datetime(2024, 1, 15), p95_time_ms=100.0)
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result["change_percentage"] == 0

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_exception(self, generator):
        """Test trend analysis with exception"""
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            mock_session_instance.execute.side_effect = Exception("DB error")
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_none_metric_values(self, generator):
        """Test trend analysis when metric values are None"""
        mock_metrics = [
            MagicMock(timestamp=datetime(2024, 1, 1), p95_time_ms=None),
            MagicMock(timestamp=datetime(2024, 1, 15), p95_time_ms=None)
        ]
        
        with patch('core.performance_report_generator.AsyncSessionLocal') as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_session_instance
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_metrics
            mock_session_instance.execute.return_value = mock_result
            
            result = await generator.generate_trend_analysis(
                component="service_a",
                metric_name="p95_time_ms",
                days=30
            )
            
            assert result["data_points"] == 0


class TestGeneratePerformanceReport:
    """Test suite for generate_performance_report convenience function"""

    @pytest.mark.asyncio
    async def test_generate_performance_report_daily(self):
        """Test generate_performance_report for daily report"""
        with patch('core.performance_report_generator.PerformanceReportGenerator') as mock_gen:
            mock_instance = AsyncMock()
            mock_gen.return_value = mock_instance
            mock_instance.generate_daily_report.return_value = {"report_type": "daily"}
            
            result = await generate_performance_report(report_type="daily", environment="dev")
            
            assert result["report_type"] == "daily"
            mock_instance.generate_daily_report.assert_called_once_with("dev")

    @pytest.mark.asyncio
    async def test_generate_performance_report_weekly(self):
        """Test generate_performance_report for weekly report"""
        with patch('core.performance_report_generator.PerformanceReportGenerator') as mock_gen:
            mock_instance = AsyncMock()
            mock_gen.return_value = mock_instance
            mock_instance.generate_weekly_report.return_value = {"report_type": "weekly"}
            
            result = await generate_performance_report(report_type="weekly", environment="dev")
            
            assert result["report_type"] == "weekly"
            mock_instance.generate_weekly_report.assert_called_once_with("dev")

    @pytest.mark.asyncio
    async def test_generate_performance_report_monthly(self):
        """Test generate_performance_report for monthly report"""
        with patch('core.performance_report_generator.PerformanceReportGenerator') as mock_gen:
            mock_instance = AsyncMock()
            mock_gen.return_value = mock_instance
            mock_instance.generate_monthly_report.return_value = {"report_type": "monthly"}
            
            result = await generate_performance_report(report_type="monthly", environment="dev")
            
            assert result["report_type"] == "monthly"
            mock_instance.generate_monthly_report.assert_called_once_with("dev")

    @pytest.mark.asyncio
    async def test_generate_performance_report_invalid_type(self):
        """Test generate_performance_report with invalid report type"""
        with patch('core.performance_report_generator.PerformanceReportGenerator') as mock_gen:
            mock_instance = AsyncMock()
            mock_gen.return_value = mock_instance
            
            result = await generate_performance_report(report_type="invalid", environment="dev")
            
            assert result == {}
