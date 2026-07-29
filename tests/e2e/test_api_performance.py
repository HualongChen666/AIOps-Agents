# -*- coding: utf-8 -*-
import logging
"""
E2E Test: API Performance
真实E2E测试：API性能测试场景，不使用Mock
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestAPIPerformance:
    """API性能E2E测试"""

    @pytest.mark.asyncio
    async def test_api_response_time_benchmarks(self, http_client):
        """测试API响应时间基准"""

        endpoints = [
            ("GET", "/api/v1/health/ping", 100),  # 预期<100ms
            ("GET", "/api/v1/health", 200),  # 预期<200ms
            ("GET", "/api/v1/alerts", 500),  # 预期<500ms
        ]

        for method, endpoint, max_time in endpoints:
            start_time = time.time()

            if method == "GET":
                response = await http_client.get(f"http://localhost:8000{endpoint}", timeout=10.0)

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            assert response.status_code in [200, 404]
            assert (
                response_time < max_time
            ), f"{method} {endpoint} took {response_time}ms, expected <{max_time}ms"

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, http_client):
        """测试并发请求处理"""

        async def make_request():
            return await http_client.get("http://localhost:8000/api/v1/health/ping", timeout=10.0)

        # 发送100个并发请求
        start_time = time.time()
        responses = await asyncio.gather(*[make_request() for _ in range(100)])
        end_time = time.time()

        # 验证所有请求都成功
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 95  # 允许5%的失败率

        # 验证性能
        total_time = end_time - start_time
        assert total_time < 10.0  # 100个请求应该在10秒内完成

    @pytest.mark.asyncio
    async def test_api_throughput_measurement(self, http_client):
        """测试API吞吐量"""

        duration_seconds = 10
        request_count = 0
        start_time = time.time()

        async def continuous_requests():
            nonlocal request_count
            while time.time() - start_time < duration_seconds:
                await http_client.get("http://localhost:8000/api/v1/health/ping", timeout=5.0)
                request_count += 1

        # 启动多个并发请求者
        await asyncio.gather(*[continuous_requests() for _ in range(10)])

        # 计算吞吐量
        throughput = request_count / duration_seconds

        # 验证吞吐量
        assert throughput > 50  # 至少50请求/秒

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, http_client):
        """测试大负载处理"""

        # 创建大负载
        large_data = {
            "component": "test",
            "metrics": {f"metric_{i}": i * 10 for i in range(1000)},
            "description": "A" * 10000,  # 10KB描述
        }

        start_time = time.time()
        response = await http_client.post(
            "http://localhost:8000/api/v1/alerts", json=large_data, timeout=30.0
        )
        end_time = time.time()

        # 验证响应
        assert response.status_code in [200, 201, 202, 413]  # 413如果负载过大

        if response.status_code in [200, 201, 202]:
            response_time = (end_time - start_time) * 1000
            assert response_time < 5000  # 大负载应该在5秒内处理

    @pytest.mark.asyncio
    async def test_api_error_rate_under_load(self, http_client):
        """测试负载下的API错误率"""

        async def stress_request():
            try:
                response = await http_client.get(
                    "http://localhost:8000/api/v1/health/ping", timeout=5.0
                )
                return response.status_code
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                return 500

        # 发送负载测试
        responses = await asyncio.gather(*[stress_request() for _ in range(200)])

        # 计算错误率
        error_count = sum(1 for status in responses if status >= 400)
        error_rate = error_count / len(responses)

        # 验证错误率
        assert error_rate < 0.05  # 错误率应该小于5%

    @pytest.mark.asyncio
    async def test_api_resource_cleanup(self, http_client):
        """测试API资源清理"""

        # 创建资源
        create_response = await http_client.post(
            "http://localhost:8000/api/v1/alerts",
            json={
                "component": "cleanup_test",
                "severity": "info",
                "title": "清理测试",
                "description": "测试资源清理",
                "metrics": {"test": 100},
                "source": "test",
                "timestamp": datetime.now().isoformat(),
            },
            timeout=10.0,
        )

        if create_response.status_code in [200, 201, 202]:
            alert_id = create_response.json().get("id")

            # 删除资源
            delete_response = await http_client.delete(
                f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
            )

            assert delete_response.status_code in [200, 204]

            # 验证资源已删除
            get_response = await http_client.get(
                f"http://localhost:8000/api/v1/alerts/{alert_id}", timeout=10.0
            )

            assert get_response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])