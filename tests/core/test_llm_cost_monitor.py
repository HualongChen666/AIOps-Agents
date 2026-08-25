# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/llm_cost_monitor.py
Target: 90%+ statement and branch coverage
"""

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.llm_cost_monitor import (
    DEFAULT_LLM_BUDGET_PER_REQUEST,
    DEFAULT_LLM_MAX_COST_PER_DAY,
    DEFAULT_LLM_MAX_COST_PER_HOUR,
    DEFAULT_LLM_ROUTER_MODELS,
    DEFAULT_LLM_ROUTER_TOKEN_COST_THRESHOLD,
    LLMCostMonitor,
    SessionBudget,
    _safe_float_env,
    get_llm_cost_monitor,
    get_session_budget,
    reset_llm_cost_monitor,
    set_llm_cost_monitor,
)


class TestSafeFloatEnv:
    """Test suite for _safe_float_env helper function"""

    def test_safe_float_env_default(self):
        """Test default value when env var not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = _safe_float_env("NONEXISTENT_VAR", 10.0)
            assert result == 10.0

    def test_safe_float_env_valid(self):
        """Test valid environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": "5.5"}):
            result = _safe_float_env("TEST_VAR", 10.0)
            assert result == 5.5

    def test_safe_float_env_invalid_string(self):
        """Test invalid string in environment variable"""
        with patch.dict(os.environ, {"TEST_VAR": "invalid"}):
            result = _safe_float_env("TEST_VAR", 10.0)
            assert result == 10.0  # Should return default

    def test_safe_float_env_whitespace(self):
        """Test environment variable with whitespace"""
        with patch.dict(os.environ, {"TEST_VAR": "  7.5  "}):
            result = _safe_float_env("TEST_VAR", 10.0)
            assert result == 7.5

    def test_safe_float_env_below_min(self):
        """Test value below minimum threshold"""
        with patch.dict(os.environ, {"TEST_VAR": "2.0"}):
            result = _safe_float_env("TEST_VAR", 10.0, min_val=5.0)
            assert result == 5.0  # Should return min_val

    def test_safe_float_env_above_max(self):
        """Test value above maximum threshold"""
        with patch.dict(os.environ, {"TEST_VAR": "15.0"}):
            result = _safe_float_env("TEST_VAR", 10.0, max_val=12.0)
            assert result == 12.0  # Should return max_val

    def test_safe_float_env_within_bounds(self):
        """Test value within min and max bounds"""
        with patch.dict(os.environ, {"TEST_VAR": "8.0"}):
            result = _safe_float_env("TEST_VAR", 10.0, min_val=5.0, max_val=12.0)
            assert result == 8.0

    def test_safe_float_env_none_min_max(self):
        """Test with None min and max (no bounds)"""
        with patch.dict(os.environ, {"TEST_VAR": "999.0"}):
            result = _safe_float_env("TEST_VAR", 10.0, min_val=None, max_val=None)
            assert result == 999.0


class TestLLMCostMonitorInit:
    """Test suite for LLMCostMonitor initialization"""

    def test_init_defaults(self):
        """Test initialization with default values"""
        monitor = LLMCostMonitor()

        assert monitor.model_configs == DEFAULT_LLM_ROUTER_MODELS
        assert monitor.token_cost_threshold == DEFAULT_LLM_ROUTER_TOKEN_COST_THRESHOLD
        assert monitor.budget_per_request == DEFAULT_LLM_BUDGET_PER_REQUEST
        assert monitor.max_cost_per_hour == DEFAULT_LLM_MAX_COST_PER_HOUR
        assert monitor.max_cost_per_day == DEFAULT_LLM_MAX_COST_PER_DAY
        assert monitor._hourly_cost == 0.0
        assert monitor._daily_cost == 0.0
        assert monitor._request_count == 0
        assert monitor._hour_start is None
        assert monitor._day_start is None

    def test_init_custom_model_configs(self):
        """Test initialization with custom model configs"""
        custom_configs = [
            {"provider": "test", "model": "test-model", "max_tokens": 1000, "cost_per_1k": 0.1}
        ]
        monitor = LLMCostMonitor(model_configs=custom_configs)

        assert monitor.model_configs == custom_configs

    def test_init_custom_token_threshold(self):
        """Test initialization with custom token threshold"""
        monitor = LLMCostMonitor(token_cost_threshold=50000)
        assert monitor.token_cost_threshold == 50000

    def test_init_custom_budgets(self):
        """Test initialization with custom budget settings"""
        monitor = LLMCostMonitor(
            budget_per_request=1.0, max_cost_per_hour=20.0, max_cost_per_day=100.0
        )
        assert monitor.budget_per_request == 1.0
        assert monitor.max_cost_per_hour == 20.0
        assert monitor.max_cost_per_day == 100.0

    def test_init_env_override(self):
        """Test initialization with environment variable overrides"""
        with patch.dict(
            os.environ,
            {
                "LLM_BUDGET_PER_REQUEST": "2.0",
                "LLM_MAX_COST_PER_HOUR": "50.0",
                "LLM_MAX_COST_PER_DAY": "200.0",
            },
        ):
            monitor = LLMCostMonitor()
            assert monitor.budget_per_request == 2.0
            assert monitor.max_cost_per_hour == 50.0
            assert monitor.max_cost_per_day == 200.0


class TestLLMCostMonitorModelConfig:
    """Test suite for model configuration methods"""

    def test_get_model_config_found_by_model(self):
        """Test finding model config by 'model' field"""
        monitor = LLMCostMonitor()
        config = monitor.get_model_config("gpt-4o-mini")

        assert config is not None
        assert config["model"] == "gpt-4o-mini"
        assert config["provider"] == "openai"

    def test_get_model_config_found_by_name(self):
        """Test finding model config by 'name' field"""
        monitor = LLMCostMonitor()
        # Add a config with 'name' field
        monitor.model_configs.append({"name": "custom-model", "cost_per_1k": 0.5})

        config = monitor.get_model_config("custom-model")
        assert config is not None
        assert config["name"] == "custom-model"

    def test_get_model_config_not_found(self):
        """Test when model config is not found"""
        monitor = LLMCostMonitor()
        config = monitor.get_model_config("nonexistent-model")

        assert config is None

    def test_get_cost_per_1k_found(self):
        """Test getting cost per 1k tokens for existing model"""
        monitor = LLMCostMonitor()
        cost = monitor.get_cost_per_1k("gpt-4o-mini")

        assert cost == 0.015

    def test_get_cost_per_1k_not_found_default(self):
        """Test getting cost per 1k tokens with default for nonexistent model"""
        monitor = LLMCostMonitor()
        cost = monitor.get_cost_per_1k("nonexistent-model", default=0.999)

        assert cost == 0.999

    def test_get_cost_per_1k_not_found_no_default(self):
        """Test getting cost per 1k tokens without default for nonexistent model"""
        monitor = LLMCostMonitor()
        cost = monitor.get_cost_per_1k("nonexistent-model")

        assert cost == 0.0

    def test_get_cost_per_1k_config_missing_cost_field(self):
        """Test when config exists but cost_per_1k field is missing"""
        monitor = LLMCostMonitor()
        monitor.model_configs.append({"model": "no-cost-model"})

        cost = monitor.get_cost_per_1k("no-cost-model", default=0.5)
        assert cost == 0.5


class TestLLMCostMonitorEstimation:
    """Test suite for cost estimation methods"""

    def test_estimate_tokens(self):
        """Test token estimation"""
        monitor = LLMCostMonitor()
        tokens = monitor.estimate_tokens("Hello world")

        assert tokens > 0
        assert isinstance(tokens, int)

    def test_estimate_tokens_with_model(self):
        """Test token estimation with model parameter"""
        monitor = LLMCostMonitor()
        tokens = monitor.estimate_tokens("Hello world", model="gpt-4")

        assert tokens > 0

    def test_estimate_cost_input_only(self):
        """Test cost estimation with input tokens only"""
        monitor = LLMCostMonitor()
        cost = monitor.estimate_cost("gpt-4o-mini", 1000)

        assert cost == 0.015  # 1000 tokens * 0.015 per 1k

    def test_estimate_cost_with_output(self):
        """Test cost estimation with both input and output tokens"""
        monitor = LLMCostMonitor()
        cost = monitor.estimate_cost("gpt-4o-mini", 1000, 500)

        assert cost == 0.0225  # 1500 tokens * 0.015 per 1k

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model"""
        monitor = LLMCostMonitor()
        cost = monitor.estimate_cost("unknown-model", 1000, 500)

        assert cost == 0.0  # Should return 0 for unknown model

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens"""
        monitor = LLMCostMonitor()
        cost = monitor.estimate_cost("gpt-4o-mini", 0, 0)

        assert cost == 0.0


class TestLLMCostMonitorBudgetCheck:
    """Test suite for budget checking methods"""

    def test_check_budget_within_limits(self):
        """Test budget check when cost is within all limits"""
        monitor = LLMCostMonitor(
            budget_per_request=1.0, max_cost_per_hour=10.0, max_cost_per_day=50.0
        )

        result = monitor.check_budget(0.5)
        assert result is True

    def test_check_budget_exceeds_per_request(self):
        """Test budget check when cost exceeds per-request budget"""
        monitor = LLMCostMonitor(budget_per_request=0.5)

        result = monitor.check_budget(1.0)
        assert result is False

    def test_check_budget_no_per_request_limit(self):
        """Test budget check when per-request limit is not set"""
        monitor = LLMCostMonitor(budget_per_request=0.0)
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        result = monitor.check_budget(1000.0)
        # When budget_per_request is 0, it still checks the limit
        # So we need to set it to None or a high value to disable
        assert result is False  # 0 means limit is 0, so anything > 0 fails

    def test_check_budget_exceeds_hourly(self):
        """Test budget check when cost would exceed hourly limit"""
        monitor = LLMCostMonitor(max_cost_per_hour=5.0)
        monitor._hourly_cost = 4.0
        monitor._hour_start = time.time()

        result = monitor.check_budget(2.0)  # 4.0 + 2.0 > 5.0
        assert result is False

    def test_check_budget_within_hourly(self):
        """Test budget check when cost is within hourly limit"""
        monitor = LLMCostMonitor(max_cost_per_hour=5.0, budget_per_request=10.0)
        monitor._hourly_cost = 2.0
        monitor._hour_start = time.time()

        result = monitor.check_budget(2.0)  # 2.0 + 2.0 < 5.0
        assert result is True

    def test_check_budget_exceeds_daily(self):
        """Test budget check when cost would exceed daily limit"""
        monitor = LLMCostMonitor(max_cost_per_day=10.0, budget_per_request=10.0)
        monitor._daily_cost = 9.0
        monitor._day_start = time.time()

        result = monitor.check_budget(2.0)  # 9.0 + 2.0 > 10.0
        assert result is False

    def test_check_budget_hourly_passes_daily_fails(self):
        """Test budget check when hourly passes but daily fails"""
        monitor = LLMCostMonitor(
            max_cost_per_hour=100.0, max_cost_per_day=10.0, budget_per_request=10.0
        )
        monitor._hourly_cost = 5.0
        monitor._daily_cost = 9.0
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        result = monitor.check_budget(2.0)  # Hourly: 5+2<100, Daily: 9+2>10
        assert result is False

    def test_check_budget_no_hourly_limit_set(self):
        """Test budget check when max_cost_per_hour is None (not set)"""
        monitor = LLMCostMonitor(
            max_cost_per_hour=None, max_cost_per_day=10.0, budget_per_request=10.0
        )
        monitor._daily_cost = 5.0
        monitor._day_start = time.time()

        result = monitor.check_budget(2.0)
        # Should skip hourly check and only check daily
        assert result is True

    def test_check_budget_no_daily_limit_set(self):
        """Test budget check when max_cost_per_day is None (not set)"""
        monitor = LLMCostMonitor(
            max_cost_per_hour=10.0, max_cost_per_day=None, budget_per_request=10.0
        )
        monitor._hourly_cost = 5.0
        monitor._hour_start = time.time()

        result = monitor.check_budget(2.0)
        # Should skip daily check and only check hourly
        assert result is True

    def test_check_budget_no_per_request_limit_set(self):
        """Test budget check when budget_per_request is None (not set)"""
        # When budget_per_request is None, it uses the default from env or DEFAULT
        # So we need to set it to a high value to effectively disable it
        monitor = LLMCostMonitor(
            budget_per_request=1000.0,  # High value to effectively disable
            max_cost_per_hour=10.0,
            max_cost_per_day=100.0,
        )
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        result = monitor.check_budget(5.0)
        # Should pass per-request check and be within hourly limit
        assert result is True

    def test_check_budget_within_daily(self):
        """Test budget check when cost is within daily limit"""
        monitor = LLMCostMonitor(max_cost_per_day=10.0, budget_per_request=10.0)
        monitor._daily_cost = 5.0
        monitor._day_start = time.time()

        result = monitor.check_budget(2.0)  # 5.0 + 2.0 < 10.0
        assert result is True

    def test_check_budget_no_hourly_limit(self):
        """Test budget check when hourly limit is not set"""
        monitor = LLMCostMonitor(max_cost_per_hour=0.0, budget_per_request=10000.0)
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        result = monitor.check_budget(1000.0)
        # When max_cost_per_hour is 0, it still checks the limit
        assert result is False  # 0 means limit is 0, so anything > 0 fails

    def test_check_budget_no_daily_limit(self):
        """Test budget check when daily limit is not set"""
        monitor = LLMCostMonitor(max_cost_per_day=0.0, budget_per_request=10000.0)
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        result = monitor.check_budget(1000.0)
        # When max_cost_per_day is 0, it still checks the limit
        assert result is False  # 0 means limit is 0, so anything > 0 fails


class TestLLMCostMonitorCostRecording:
    """Test suite for cost recording methods"""

    def test_record_cost(self):
        """Test recording actual cost"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        monitor.record_cost(0.5)

        assert monitor._hourly_cost == 0.5
        assert monitor._daily_cost == 0.5
        assert monitor._request_count == 1

    def test_record_cost_multiple(self):
        """Test recording multiple costs"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        monitor.record_cost(0.5)
        monitor.record_cost(0.3)
        monitor.record_cost(0.2)

        assert monitor._hourly_cost == 1.0
        assert monitor._daily_cost == 1.0
        assert monitor._request_count == 3


class TestLLMCostMonitorStats:
    """Test suite for statistics methods"""

    def test_get_hourly_stats_empty(self):
        """Test getting hourly stats when no costs recorded"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        stats = monitor.get_hourly_stats()

        assert stats["hourly_cost"] == 0.0
        assert stats["daily_cost"] == 0.0
        assert stats["request_count"] == 0
        assert stats["avg_cost_per_request"] == 0.0

    def test_get_hourly_stats_with_data(self):
        """Test getting hourly stats with recorded data"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time()
        monitor._day_start = time.time()
        monitor.record_cost(1.0)
        monitor.record_cost(2.0)

        stats = monitor.get_hourly_stats()

        assert stats["hourly_cost"] == 3.0
        assert stats["daily_cost"] == 3.0
        assert stats["request_count"] == 2
        assert stats["avg_cost_per_request"] == 1.5


class TestLLMCostMonitorTimeTracking:
    """Test suite for time-based tracking methods"""

    def test_update_hourly_tracking_first_call(self):
        """Test hourly tracking on first call (initializes hour_start)"""
        monitor = LLMCostMonitor()

        monitor._update_hourly_tracking()

        assert monitor._hour_start is not None
        assert monitor._hourly_cost == 0.0
        assert monitor._request_count == 0

    def test_update_hourly_tracking_within_hour(self):
        """Test hourly tracking when within the same hour"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time()
        monitor._hourly_cost = 5.0
        monitor._request_count = 10

        monitor._update_hourly_tracking()

        # Should not reset if within hour
        assert monitor._hourly_cost == 5.0
        assert monitor._request_count == 10

    def test_update_hourly_tracking_after_hour(self):
        """Test hourly tracking when hour has passed"""
        monitor = LLMCostMonitor()
        monitor._hour_start = time.time() - 3700  # More than 1 hour ago
        monitor._hourly_cost = 5.0
        monitor._request_count = 10

        monitor._update_hourly_tracking()

        # Should reset after hour
        assert monitor._hourly_cost == 0.0
        assert monitor._request_count == 0
        assert monitor._hour_start > time.time() - 100  # Should be recent

    def test_update_daily_tracking_first_call(self):
        """Test daily tracking on first call (initializes day_start)"""
        monitor = LLMCostMonitor()

        monitor._update_daily_tracking()

        assert monitor._day_start is not None
        assert monitor._daily_cost == 0.0

    def test_update_daily_tracking_within_day(self):
        """Test daily tracking when within the same day"""
        monitor = LLMCostMonitor()
        monitor._day_start = time.time()
        monitor._daily_cost = 10.0

        monitor._update_daily_tracking()

        # Should not reset if within day
        assert monitor._daily_cost == 10.0

    def test_update_daily_tracking_after_day(self):
        """Test daily tracking when day has passed"""
        monitor = LLMCostMonitor()
        monitor._day_start = time.time() - 86500  # More than 1 day ago
        monitor._daily_cost = 10.0

        monitor._update_daily_tracking()

        # Should reset after day
        assert monitor._daily_cost == 0.0
        assert monitor._day_start > time.time() - 100  # Should be recent


class TestLLMCostMonitorSingleton:
    """Test suite for singleton pattern"""

    def test_get_llm_cost_monitor_singleton(self):
        """Test that get_llm_cost_monitor returns singleton"""
        reset_llm_cost_monitor()

        monitor1 = get_llm_cost_monitor()
        monitor2 = get_llm_cost_monitor()

        assert monitor1 is monitor2
        assert isinstance(monitor1, LLMCostMonitor)

    def test_set_llm_cost_monitor(self):
        """Test setting custom monitor instance"""
        reset_llm_cost_monitor()

        custom_monitor = LLMCostMonitor(budget_per_request=999.0)
        set_llm_cost_monitor(custom_monitor)

        retrieved = get_llm_cost_monitor()
        assert retrieved is custom_monitor
        assert retrieved.budget_per_request == 999.0

    def test_reset_llm_cost_monitor(self):
        """Test resetting the singleton"""
        reset_llm_cost_monitor()

        monitor1 = get_llm_cost_monitor()
        monitor1.record_cost(1.0)

        reset_llm_cost_monitor()

        monitor2 = get_llm_cost_monitor()
        assert monitor1 is not monitor2
        assert monitor2._hourly_cost == 0.0


class TestSessionBudget:
    """Test suite for SessionBudget class"""

    def test_session_budget_init(self):
        """Test SessionBudget initialization"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=10.0)

        assert budget.session_id == "session-1"
        assert budget.max_tokens == 1000
        assert budget.max_cost == 10.0
        assert budget.tokens_used == 0
        assert budget.cost_used == 0.0

    def test_session_budget_check_and_record_within_limits(self):
        """Test check_and_record when within budget limits"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=10.0)

        result = budget.check_and_record(100, 1.0)

        assert result is True
        assert budget.tokens_used == 100
        assert budget.cost_used == 1.0

    def test_session_budget_check_and_record_exceeds_tokens(self):
        """Test check_and_record when token budget exceeded"""
        budget = SessionBudget("session-1", max_tokens=100, max_cost=10.0)
        budget.tokens_used = 90

        result = budget.check_and_record(20, 1.0)  # 90 + 20 > 100

        assert result is False
        assert budget.tokens_used == 90  # Should not record
        assert budget.cost_used == 0.0

    def test_session_budget_check_and_record_exceeds_cost(self):
        """Test check_and_record when cost budget exceeded"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=5.0)
        budget.cost_used = 4.5

        result = budget.check_and_record(100, 1.0)  # 4.5 + 1.0 > 5.0

        assert result is False
        assert budget.tokens_used == 0
        assert budget.cost_used == 4.5  # Should not record

    def test_session_budget_check_and_record_no_token_limit(self):
        """Test check_and_record when no token limit set"""
        budget = SessionBudget("session-1", max_tokens=None, max_cost=10.0)

        result = budget.check_and_record(1000000, 1.0)

        assert result is True
        assert budget.tokens_used == 1000000

    def test_session_budget_check_and_record_no_cost_limit(self):
        """Test check_and_record when no cost limit set"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=None)

        result = budget.check_and_record(100, 1000000.0)

        assert result is True
        assert budget.cost_used == 1000000.0

    def test_session_budget_record_cost(self):
        """Test recording cost after call completes"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=10.0)

        budget.record_cost(5.0)

        assert budget.cost_used == 5.0

    def test_session_budget_thread_safety(self):
        """Test that SessionBudget is thread-safe"""
        budget = SessionBudget("session-1", max_tokens=1000, max_cost=10.0)

        def record_usage():
            for _ in range(100):
                budget.check_and_record(1, 0.01)

        threads = [threading.Thread(target=record_usage) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert budget.tokens_used == 1000  # 10 threads * 100 * 1
        # Use approximate comparison for floating point
        assert abs(budget.cost_used - 10.0) < 0.01  # 10 threads * 100 * 0.01


class TestGetSessionBudget:
    """Test suite for get_session_budget function"""

    def test_get_session_budget_new_session(self):
        """Test getting budget for new session"""
        # Clear any existing session budgets
        from core.llm_cost_monitor import _SESSION_BUDGETS

        _SESSION_BUDGETS.clear()

        budget = get_session_budget("new-session")

        assert budget is not None
        assert budget.session_id == "new-session"

    def test_session_budget_env_var_invalid(self):
        """Test session budget with invalid environment variable"""
        from core.llm_cost_monitor import _DEFAULT_SESSION_TOKEN_BUDGET, _SESSION_BUDGETS

        _SESSION_BUDGETS.clear()

        # Set invalid value for token budget
        with patch.dict(os.environ, {"AIOPS_SESSION_TOKEN_BUDGET": "invalid"}):
            # Re-import to trigger the exception handling
            import importlib

            import core.llm_cost_monitor

            importlib.reload(core.llm_cost_monitor)

            # Should fall back to default 50000
            assert core.llm_cost_monitor._DEFAULT_SESSION_TOKEN_BUDGET == 50000

    def test_get_session_budget_existing_session(self):
        """Test getting budget for existing session"""
        from core.llm_cost_monitor import _SESSION_BUDGETS

        _SESSION_BUDGETS.clear()

        budget1 = get_session_budget("existing-session")
        budget1.tokens_used = 100

        budget2 = get_session_budget("existing-session")

        assert budget1 is budget2
        assert budget2.tokens_used == 100

    def test_get_session_budget_none_session_id(self):
        """Test getting budget with None session ID"""
        budget = get_session_budget(None)

        assert budget is None

    def test_get_session_budget_empty_session_id(self):
        """Test getting budget with empty session ID"""
        budget = get_session_budget("")

        assert budget is None

    def test_get_session_budget_thread_safety(self):
        """Test that get_session_budget is thread-safe"""
        from core.llm_cost_monitor import _SESSION_BUDGETS

        _SESSION_BUDGETS.clear()

        def get_and_use(session_id):
            budget = get_session_budget(session_id)
            budget.check_and_record(10, 0.1)

        threads = [threading.Thread(target=get_and_use, args=(f"session-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each session should have its own budget
        assert len(_SESSION_BUDGETS) == 10
        for budget in _SESSION_BUDGETS.values():
            assert budget.tokens_used == 10
            assert budget.cost_used == 0.1


class TestLLMCostMonitorIntegration:
    """Integration tests for LLMCostMonitor"""

    def test_full_workflow(self):
        """Test complete workflow: check budget, record cost, get stats"""
        monitor = LLMCostMonitor(
            budget_per_request=1.0, max_cost_per_hour=10.0, max_cost_per_day=50.0
        )
        monitor._hour_start = time.time()
        monitor._day_start = time.time()

        # Check budget
        assert monitor.check_budget(0.5) is True

        # Record cost
        monitor.record_cost(0.5)

        # Get stats
        stats = monitor.get_hourly_stats()
        assert stats["hourly_cost"] == 0.5
        assert stats["request_count"] == 1

    def test_budget_enforcement(self):
        """Test that budget enforcement works correctly"""
        monitor = LLMCostMonitor(budget_per_request=0.1)

        # Small cost should pass
        assert monitor.check_budget(0.05) is True

        # Large cost should fail
        assert monitor.check_budget(0.2) is False

    def test_time_window_reset(self):
        """Test that time windows reset correctly"""
        monitor = LLMCostMonitor()

        # Set old timestamps
        monitor._hour_start = time.time() - 3700
        monitor._day_start = time.time() - 86500
        monitor._hourly_cost = 100.0
        monitor._daily_cost = 500.0
        monitor._request_count = 50

        # Update tracking should reset
        monitor._update_hourly_tracking()
        monitor._update_daily_tracking()

        assert monitor._hourly_cost == 0.0
        assert monitor._daily_cost == 0.0
        assert monitor._request_count == 0
