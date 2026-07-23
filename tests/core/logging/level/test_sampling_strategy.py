# -*- coding: utf-8 -*-
"""
Unit tests for log sampling strategy
日志采样策略单元测试
"""

import logging

import pytest

from core.logging.level.level_manager import LogLevel
from core.logging.level.sampling_strategy import (
    CompositeSampler,
    DynamicSampler,
    LevelBasedSampler,
    RatioSampler,
)


class TestRatioSampler:
    """Test cases for RatioSampler"""

    def create_log_record(self, level: int = logging.INFO):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_full_sampling(self):
        """Test 100% sampling rate"""
        sampler = RatioSampler(sampling_rate=1.0)
        record = self.create_log_record()

        assert sampler.should_sample(record) is True

    def test_no_sampling(self):
        """Test 0% sampling rate"""
        sampler = RatioSampler(sampling_rate=0.0)
        record = self.create_log_record()

        assert sampler.should_sample(record) is False

    def test_half_sampling(self):
        """Test 50% sampling rate"""
        sampler = RatioSampler(sampling_rate=0.5, seed=42)
        record = self.create_log_record()

        # With seed=42, we can test deterministically
        results = [sampler.should_sample(record) for _ in range(100)]
        # Should be approximately 50%
        assert 40 <= sum(results) <= 60

    def test_get_sampling_rate(self):
        """Test getting sampling rate"""
        sampler = RatioSampler(sampling_rate=0.7)
        assert sampler.get_sampling_rate() == 0.7

    def test_set_sampling_rate(self):
        """Test setting sampling rate"""
        sampler = RatioSampler(sampling_rate=0.5)
        sampler.set_sampling_rate(0.8)
        assert sampler.get_sampling_rate() == 0.8

    def test_invalid_sampling_rate_high(self):
        """Test invalid sampling rate > 1.0"""
        with pytest.raises(ValueError):
            RatioSampler(sampling_rate=1.5)

    def test_invalid_sampling_rate_low(self):
        """Test invalid sampling rate < 0.0"""
        with pytest.raises(ValueError):
            RatioSampler(sampling_rate=-0.1)

    def test_set_invalid_sampling_rate(self):
        """Test setting invalid sampling rate"""
        sampler = RatioSampler(sampling_rate=0.5)
        with pytest.raises(ValueError):
            sampler.set_sampling_rate(1.5)

    def test_seed_consistency(self):
        """Test seed produces consistent results"""
        sampler1 = RatioSampler(sampling_rate=0.5, seed=42)
        sampler2 = RatioSampler(sampling_rate=0.5, seed=42)

        record = self.create_log_record()

        results1 = [sampler1.should_sample(record) for _ in range(10)]
        results2 = [sampler2.should_sample(record) for _ in range(10)]

        assert results1 == results2


class TestDynamicSampler:
    """Test cases for DynamicSampler"""

    def create_log_record(self, level: int = logging.INFO):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_initial_rate(self):
        """Test initial sampling rate"""
        sampler = DynamicSampler(initial_rate=0.8)
        assert sampler.get_sampling_rate() == 0.8

    def test_manual_rate_adjustment(self):
        """Test manual rate adjustment"""
        sampler = DynamicSampler(initial_rate=0.5)
        sampler.set_sampling_rate(0.7)
        assert sampler.get_sampling_rate() == 0.7

    def test_manual_rate_within_bounds(self):
        """Test manual rate stays within bounds"""
        sampler = DynamicSampler(min_rate=0.2, max_rate=0.8)
        sampler.set_sampling_rate(0.9)
        assert sampler.get_sampling_rate() == 0.8  # Clamped to max

    def test_manual_rate_below_min(self):
        """Test manual rate below minimum"""
        sampler = DynamicSampler(min_rate=0.2, max_rate=0.8)
        sampler.set_sampling_rate(0.1)
        assert sampler.get_sampling_rate() == 0.2  # Clamped to min

    def test_custom_callback(self):
        """Test custom rate adjustment callback can be set"""

        def adjust_callback(current_rate):
            return max(0.1, current_rate - 0.1)

        sampler = DynamicSampler(
            initial_rate=0.8,
            min_rate=0.1,
            max_rate=1.0,
            adjustment_interval=60.0,
            rate_adjustment_callback=adjust_callback,
        )

        # Verify callback is set
        assert sampler.rate_adjustment_callback is not None

    def test_invalid_rate_range(self):
        """Test invalid rate range initialization"""
        with pytest.raises(ValueError):
            DynamicSampler(min_rate=0.8, max_rate=0.2)

    def test_set_invalid_rate(self):
        """Test setting invalid rate"""
        sampler = DynamicSampler()
        with pytest.raises(ValueError):
            sampler.set_sampling_rate(1.5)


class TestLevelBasedSampler:
    """Test cases for LevelBasedSampler"""

    def create_log_record(self, level: int):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_default_level_rates(self):
        """Test default level sampling rates"""
        sampler = LevelBasedSampler()

        # Debug should be sampled 10%
        debug_results = [
            sampler.should_sample(self.create_log_record(logging.DEBUG)) for _ in range(100)
        ]
        assert 0 <= sum(debug_results) <= 30  # Allow some variance

        # Error should be sampled 100%
        for _ in range(10):
            assert sampler.should_sample(self.create_log_record(logging.ERROR)) is True

    def test_custom_level_rates(self):
        """Test custom level sampling rates"""
        sampler = LevelBasedSampler()
        sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.0)
        sampler.set_level_sampling_rate(LogLevel.INFO, 1.0)

        debug_record = self.create_log_record(logging.DEBUG)
        info_record = self.create_log_record(logging.INFO)

        assert sampler.should_sample(debug_record) is False
        assert sampler.should_sample(info_record) is True

    def test_get_level_sampling_rate(self):
        """Test getting level-specific sampling rate"""
        sampler = LevelBasedSampler()
        sampler.set_level_sampling_rate(LogLevel.WARNING, 0.7)

        assert sampler.get_level_sampling_rate(LogLevel.WARNING) == 0.7
        assert sampler.get_level_sampling_rate(LogLevel.DEBUG) == 0.1  # Default

    def test_set_level_sampling_rate(self):
        """Test setting level sampling rate"""
        sampler = LevelBasedSampler()
        sampler.set_level_sampling_rate(LogLevel.INFO, 0.9)

        assert sampler.get_level_sampling_rate(LogLevel.INFO) == 0.9

    def test_set_invalid_level_rate(self):
        """Test setting invalid level sampling rate"""
        sampler = LevelBasedSampler()
        with pytest.raises(ValueError):
            sampler.set_level_sampling_rate(LogLevel.INFO, 1.5)

    def test_set_default_rate(self):
        """Test setting default sampling rate"""
        sampler = LevelBasedSampler(default_rate=0.5)
        sampler.set_level_sampling_rate(LogLevel.DEBUG, 0.1)

        # For undefined level, should use default
        assert sampler.get_sampling_rate() == 0.5

    def test_set_invalid_default_rate(self):
        """Test setting invalid default rate"""
        sampler = LevelBasedSampler()
        with pytest.raises(ValueError):
            sampler.set_default_rate(-0.1)

    def test_all_critical_logs_sampled(self):
        """Test that all critical logs are sampled by default"""
        sampler = LevelBasedSampler()

        for _ in range(10):
            assert sampler.should_sample(self.create_log_record(logging.CRITICAL)) is True


class TestCompositeSampler:
    """Test cases for CompositeSampler"""

    def create_log_record(self, level: int = logging.INFO):
        """Helper to create a log record"""
        record = logging.LogRecord(
            name="test_module",
            level=level,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_and_operator(self):
        """Test AND operator"""
        sampler1 = RatioSampler(sampling_rate=0.5, seed=42)
        sampler2 = RatioSampler(sampling_rate=0.5, seed=43)

        composite = CompositeSampler(samplers=[sampler1, sampler2], operator="AND")

        record = self.create_log_record()
        results = [composite.should_sample(record) for _ in range(100)]

        # AND should result in lower sampling rate
        assert sum(results) < 50

    def test_or_operator(self):
        """Test OR operator"""
        sampler1 = RatioSampler(sampling_rate=0.5, seed=42)
        sampler2 = RatioSampler(sampling_rate=0.5, seed=43)

        composite = CompositeSampler(samplers=[sampler1, sampler2], operator="OR")

        record = self.create_log_record()
        results = [composite.should_sample(record) for _ in range(100)]

        # OR should result in higher sampling rate
        assert sum(results) > 50

    def test_empty_samplers(self):
        """Test empty samplers list"""
        composite = CompositeSampler(samplers=[])
        record = self.create_log_record()

        assert composite.should_sample(record) is True

    def test_get_sampling_rate(self):
        """Test getting average sampling rate"""
        sampler1 = RatioSampler(sampling_rate=0.5)
        sampler2 = RatioSampler(sampling_rate=0.7)

        composite = CompositeSampler(samplers=[sampler1, sampler2])

        assert composite.get_sampling_rate() == 0.6

    def test_add_sampler(self):
        """Test adding sampler"""
        sampler1 = RatioSampler(sampling_rate=0.5)
        composite = CompositeSampler(samplers=[sampler1])

        sampler2 = RatioSampler(sampling_rate=0.7)
        composite.add_sampler(sampler2)

        assert len(composite.samplers) == 2
        assert composite.get_sampling_rate() == 0.6

    def test_remove_sampler(self):
        """Test removing sampler"""
        sampler1 = RatioSampler(sampling_rate=0.5)
        sampler2 = RatioSampler(sampling_rate=0.7)
        composite = CompositeSampler(samplers=[sampler1, sampler2])

        composite.remove_sampler(sampler2)

        assert len(composite.samplers) == 1
        assert composite.get_sampling_rate() == 0.5

    def test_invalid_operator_defaults_to_and(self):
        """Test invalid operator defaults to AND"""
        sampler1 = RatioSampler(sampling_rate=0.5, seed=42)
        sampler2 = RatioSampler(sampling_rate=0.5, seed=43)

        composite = CompositeSampler(samplers=[sampler1, sampler2], operator="INVALID")

        record = self.create_log_record()
        results = [composite.should_sample(record) for _ in range(100)]

        # Should behave like AND
        assert sum(results) < 50

    def test_mixed_sampler_types(self):
        """Test composite with different sampler types"""
        ratio_sampler = RatioSampler(sampling_rate=0.5, seed=42)
        level_sampler = LevelBasedSampler()

        composite = CompositeSampler(samplers=[ratio_sampler, level_sampler], operator="AND")

        # ERROR level from level_sampler always passes
        error_record = self.create_log_record(logging.ERROR)
        # Should depend on ratio_sampler
        results = [composite.should_sample(error_record) for _ in range(100)]
        assert 40 <= sum(results) <= 60
