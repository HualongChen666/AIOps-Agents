# -*- coding: utf-8 -*-
"""测试 core/cost_monitor 的成本采集、预测与预算状态"""

from datetime import datetime

from core import cost_monitor


class TestCollectCosts:
    def test_collect_costs_returns_records(self):
        result = cost_monitor.collect_costs()
        assert len(result) == 30
        assert result[0]["source"] == "aws"
        assert result[0]["service"] == "ec2"

    def test_collect_costs_exception(self, monkeypatch):
        from datetime import timedelta as real_timedelta

        class BadDatetime:
            @staticmethod
            def now():
                raise RuntimeError("boom")

            timedelta = real_timedelta

        monkeypatch.setattr(cost_monitor, "datetime", BadDatetime)
        result = cost_monitor.collect_costs()
        assert result == []


class TestForecastCosts:
    def test_forecast_costs_returns_records(self):
        result = cost_monitor.forecast_costs(days=7)
        assert len(result) == 7
        assert "forecasted_cost" in result[0]

    def test_forecast_costs_empty_history(self, monkeypatch):
        monkeypatch.setattr(cost_monitor, "collect_costs", lambda: [])
        result = cost_monitor.forecast_costs()
        assert result == []


class TestBudgetStatus:
    def _single_cost(self, amount: float):
        return [{"timestamp": datetime.now().isoformat(), "cost": amount}]

    def _set_collect_costs(self, monkeypatch, amount: float):
        monkeypatch.setattr(cost_monitor, "collect_costs", lambda: self._single_cost(amount))

    def test_budget_status_healthy(self, monkeypatch):
        # Force very low current month spend
        self._set_collect_costs(monkeypatch, 0.01)
        result = cost_monitor.budget_status()
        assert result["status"] == "healthy"
        assert result["alert_level"] == "low"
        assert result["budget"]["monthly_budget"] == 5000.0

    def test_budget_status_warning(self, monkeypatch):
        # 85% triggers warning but not critical
        self._set_collect_costs(monkeypatch, 4250.0)
        result = cost_monitor.budget_status()
        assert result["status"] == "warning"
        assert result["alert_level"] == "medium"
        assert len(result["recommendations"]) > 0

    def test_budget_status_critical(self, monkeypatch):
        self._set_collect_costs(monkeypatch, 4750.0)
        result = cost_monitor.budget_status()
        assert result["status"] == "critical"
        assert result["alert_level"] == "high"

    def test_budget_status_exception(self, monkeypatch):
        def bad_collect():
            raise RuntimeError("boom")

        monkeypatch.setattr(cost_monitor, "collect_costs", bad_collect)
        result = cost_monitor.budget_status()
        assert result["status"] == "error"
        assert result["budget"] is None
