# -*- coding: utf-8 -*-
"""测试混沌工程模块"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.chaos_engineering import ChaosExperiment


@pytest.fixture
def chaos_engine(monkeypatch):
    """Provide a fresh ChaosEngine with asyncio.sleep mocked for speed."""
    from core.chaos_engineering import ChaosEngine

    monkeypatch.setattr("core.chaos_engineering.asyncio.sleep", AsyncMock())
    monkeypatch.setattr(
        "core.memory_monitor.memory_monitor",
        MagicMock(get_memory_usage=MagicMock(return_value=0.5)),
    )
    return ChaosEngine()


class TestChaosEngine:
    def test_enable_disable(self, chaos_engine):
        assert chaos_engine.is_enabled() is False
        chaos_engine.enable()
        assert chaos_engine.is_enabled() is True
        chaos_engine.disable()
        assert chaos_engine.is_enabled() is False

    def test_run_experiment_disabled(self, chaos_engine):
        result = asyncio.run(
            chaos_engine.run_experiment(ChaosExperiment.LATENCY_INJECTION, {"delay_ms": 1})
        )
        assert result.status.name == "ABORTED"
        assert result.success is False

    def test_latency_injection(self, chaos_engine):
        chaos_engine.enable()
        result = asyncio.run(
            chaos_engine.run_experiment(ChaosExperiment.LATENCY_INJECTION, {"delay_ms": 1})
        )
        assert result.success is True
        assert result.experiment.value == "latency_injection"

    def test_fault_injection_database(self, chaos_engine):
        chaos_engine.enable()
        result = asyncio.run(
            chaos_engine.run_experiment(
                ChaosExperiment.FAULT_INJECTION, {"fault_type": "database_error"}
            )
        )
        assert result.success is True

    def test_resource_limitation(self, chaos_engine):
        chaos_engine.enable()
        result = asyncio.run(
            chaos_engine.run_experiment(
                ChaosExperiment.RESOURCE_LIMITATION, {"resource_type": "memory"}
            )
        )
        assert result.success is True

    def test_network_partition(self, chaos_engine):
        chaos_engine.enable()
        result = asyncio.run(
            chaos_engine.run_experiment(
                ChaosExperiment.NETWORK_PARTITION, {"partition_type": "partial"}
            )
        )
        assert result.success is True

    def test_service_failure(self, chaos_engine):
        chaos_engine.enable()
        result = asyncio.run(
            chaos_engine.run_experiment(ChaosExperiment.SERVICE_FAILURE, {"service_name": "api"})
        )
        assert result.success is True

    def test_run_experiment_concurrent_rejected(self, chaos_engine):
        chaos_engine.enable()
        asyncio.run(chaos_engine.run_experiment(ChaosExperiment.LATENCY_INJECTION, {"delay_ms": 1}))

    def test_get_experiment_history_and_stats(self, chaos_engine):
        chaos_engine.enable()
        asyncio.run(chaos_engine.run_experiment(ChaosExperiment.LATENCY_INJECTION, {"delay_ms": 1}))
        assert len(chaos_engine.get_experiment_history()) == 1
        stats = chaos_engine.get_experiment_stats()
        assert stats["total_experiments"] == 1


class TestSetup:
    def test_setup_chaos_engineering(self, monkeypatch):
        from core.chaos_engineering import setup_chaos_engineering

        monkeypatch.setattr("core.chaos_engineering.asyncio.sleep", AsyncMock())
        result = asyncio.run(setup_chaos_engineering())
        assert result["status"] == "success"
        assert result["enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
