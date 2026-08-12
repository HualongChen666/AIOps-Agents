import asyncio
import pytest
from core.api_performance import monitor_api_performance, API_PERFORMANCE_STATS


def test_api_performance_decorator_smoke():
    API_PERFORMANCE_STATS.clear()

    @monitor_api_performance
    async def sample_api():
        return 42

    result = asyncio.run(sample_api())
    assert result == 42
    assert "sample_api" in API_PERFORMANCE_STATS
    assert len(API_PERFORMANCE_STATS["sample_api"]) == 1
