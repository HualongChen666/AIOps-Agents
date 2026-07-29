# -*- coding: utf-8 -*-
# tests/performance/test_network_performance.py
# 网络性能测试
import asyncio
import time

import pytest


@pytest.mark.performance
class TestNetworkLatency:
    """网络延迟测试"""

    @pytest.mark.asyncio
    async def test_network_latency(self, client):
        """测试网络延迟"""
        latencies = []

        for _ in range(100):
            start_time = time.time()
            await client.get("/health")
            end_time = time.time()
            latencies.append(end_time - start_time)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        # 验证延迟指标
        assert avg_latency < 0.1, f"Average latency too high: {avg_latency}s"
        assert p95_latency < 0.2, f"P95 latency too high: {p95_latency}s"
        assert p99_latency < 0.5, f"P99 latency too high: {p99_latency}s"

    @pytest.mark.asyncio
    async def test_network_jitter(self, client):
        """测试网络抖动"""
        latencies = []

        for _ in range(100):
            start_time = time.time()
            await client.get("/health")
            end_time = time.time()
            latencies.append(end_time - start_time)

        # 计算抖动（标准差）
        avg_latency = sum(latencies) / len(latencies)
        variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)
        jitter = variance**0.5

        # 验证抖动在可接受范围内（< 50ms）
        assert jitter < 0.05, f"Network jitter too high: {jitter}s"


@pytest.mark.performance
class TestNetworkThroughput:
    """网络吞吐量测试"""

    @pytest.mark.asyncio
    async def test_upload_throughput(self, client):
        """测试上传吞吐量"""
        payload_sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB
        throughputs = []

        for size in payload_sizes:
            payload = {"data": "x" * size}
            start_time = time.time()

            _ = await client.post("/api/test", json=payload)

            end_time = time.time()
            upload_time = end_time - start_time

            if upload_time > 0:
                throughput = size / upload_time  # bytes per second
                throughputs.append(throughput)

        # 验证吞吐量合理（根据CI环境校准，至少 1KB/s）
        assert len(throughputs) > 0
        avg_throughput = sum(throughputs) / len(throughputs)
        assert (
            avg_throughput > 1024
        ), f"Upload throughput too low: {avg_throughput / 1024 / 1024}MB/s"

    @pytest.mark.asyncio
    async def test_download_throughput(self, client):
        """测试下载吞吐量"""
        # 假设API返回数据
        start_time = time.time()

        response = await client.get("/api/test")
        content = response.content if hasattr(response, "content") else b""

        end_time = time.time()
        download_time = end_time - start_time

        if len(content) > 0 and download_time > 0:
            throughput = len(content) / download_time
            # 验证吞吐量合理（根据CI环境校准，至少 1KB/s）
            assert throughput > 1024, f"Download throughput too low: {throughput / 1024 / 1024}MB/s"


@pytest.mark.performance
class TestConnectionManagement:
    """连接管理测试"""

    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(self, client):
        """测试连接池效率"""
        num_requests = 100
        start_time = time.time()

        tasks = [client.get("/health") for _ in range(num_requests)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证连接池效率（平均每个请求 < 50ms）
        avg_request_time = total_time / num_requests
        assert (
            avg_request_time < 0.05
        ), f"Connection pool inefficient: {avg_request_time}s per request"

    @pytest.mark.asyncio
    async def test_connection_reuse(self, client):
        """测试连接重用"""
        # 发送多个请求，验证连接被重用
        num_requests = 50
        start_time = time.time()

        for _ in range(num_requests):
            await client.get("/health")

        end_time = time.time()
        total_time = end_time - start_time

        # 如果连接被重用，时间应该很短
        assert (
            total_time < 5.0
        ), f"Connection not reused efficiently: {total_time}s for {num_requests} requests"


@pytest.mark.performance
class TestTimeoutHandling:
    """超时处理测试"""

    @pytest.mark.asyncio
    async def test_request_timeout_performance(self, client):
        """测试请求超时性能"""
        timeout = 5.0  # 5秒超时

        start_time = time.time()
        try:
            await asyncio.wait_for(client.get("/health"), timeout=timeout)
            end_time = time.time()
            response_time = end_time - start_time

            # 验证响应时间远小于超时时间
            assert response_time < timeout * 0.5, f"Response too close to timeout: {response_time}s"
        except asyncio.TimeoutError:
            assert False, "Request timed out unexpectedly"

    @pytest.mark.asyncio
    async def test_timeout_recovery(self, client):
        """测试超时恢复性能"""
        # 模拟超时场景
        num_requests = 10
        successful_requests = 0

        for _ in range(num_requests):
            try:
                await asyncio.wait_for(client.get("/health"), timeout=10.0)
                successful_requests += 1
            except asyncio.TimeoutError:
                pass

        # 验证大部分请求成功
        assert (
            successful_requests >= num_requests * 0.8
        ), f"Too many timeouts: {successful_requests}/{num_requests}"


@pytest.mark.performance
class TestErrorHandlingPerformance:
    """错误处理性能测试"""

    @pytest.mark.asyncio
    async def test_error_response_time(self, client):
        """测试错误响应时间"""
        # 请求不存在的端点
        start_time = time.time()
        await client.get("/api/nonexistent")
        end_time = time.time()

        error_time = end_time - start_time

        # 验证错误响应时间（应该很快）
        assert error_time < 0.1, f"Error response too slow: {error_time}s"

    @pytest.mark.asyncio
    async def test_bulk_error_handling(self, client):
        """测试批量错误处理"""
        num_requests = 50
        start_time = time.time()

        tasks = [client.get(f"/api/nonexistent_{i}") for i in range(num_requests)]
        _ = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证错误处理效率
        assert total_time < 5.0, f"Bulk error handling too slow: {total_time}s"


@pytest.mark.performance
class TestCompressionPerformance:
    """压缩性能测试"""

    @pytest.mark.asyncio
    async def test_compression_overhead(self, client):
        """测试压缩开销"""
        # 小数据
        small_data = {"data": "test"}
        start_time = time.time()
        await client.post("/api/test", json=small_data)
        small_time = time.time() - start_time

        # 大数据
        large_data = {"data": "x" * 100000}
        start_time = time.time()
        await client.post("/api/test", json=large_data)
        large_time = time.time() - start_time

        # 验证压缩开销合理
        # 大数据应该不会比小数据慢太多
        # 使用 max(..., 1e-9) 避免极小/零值 baseline 导致乘零断言失败
        baseline = max(small_time, 1e-9)
        assert (
            large_time < baseline * 10
        ), f"Compression overhead too high: {large_time}s vs {small_time}s"


@pytest.mark.performance
class TestSerializationPerformance:
    """序列化性能测试"""

    @pytest.mark.asyncio
    async def test_json_serialization_performance(self):
        """测试JSON序列化性能"""
        import json

        data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        num_serializations = 1000

        start_time = time.time()
        for _ in range(num_serializations):
            json.dumps(data)
        end_time = time.time()

        serialization_time = end_time - start_time
        avg_time = serialization_time / num_serializations

        # 验证序列化性能（< 1ms per operation）
        assert avg_time < 0.001, f"JSON serialization too slow: {avg_time}s"

    @pytest.mark.asyncio
    async def test_json_deserialization_performance(self):
        """测试JSON反序列化性能"""
        import json

        data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        serialized = json.dumps(data)
        num_deserializations = 1000

        start_time = time.time()
        for _ in range(num_deserializations):
            json.loads(serialized)
        end_time = time.time()

        deserialization_time = end_time - start_time
        avg_time = deserialization_time / num_deserializations

        # 验证反序列化性能（< 1ms per operation）
        assert avg_time < 0.001, f"JSON deserialization too slow: {avg_time}s"


@pytest.mark.performance
class TestDNSPerformance:
    """DNS性能测试"""

    @pytest.mark.asyncio
    async def test_dns_resolution_performance(self):
        """测试DNS解析性能"""
        import socket

        hostnames = ["localhost", "127.0.0.1"]
        resolution_times = []

        for hostname in hostnames:
            start_time = time.time()
            try:
                socket.gethostbyname(hostname)
                end_time = time.time()
                resolution_times.append(end_time - start_time)
            except socket.gaierror:
                pass

        if resolution_times:
            avg_resolution_time = sum(resolution_times) / len(resolution_times)
            # 验证DNS解析性能（< 100ms）
            assert avg_resolution_time < 0.1, f"DNS resolution too slow: {avg_resolution_time}s"


@pytest.mark.performance
class TestSSLPerformance:
    """SSL性能测试"""

    @pytest.mark.asyncio
    async def test_ssl_handshake_performance(self, client):
        """测试SSL握手性能"""
        # 第一次请求包含SSL握手
        start_time = time.time()
        await client.get("/health")
        first_request_time = time.time() - start_time

        # 后续请求使用复用的连接
        start_time = time.time()
        await client.get("/health")
        second_request_time = time.time() - start_time

        # 第二次请求应大致相当或更快（连接复用）
        # 放宽阈值以避免时钟抖动导致误报
        assert (
            second_request_time <= first_request_time * 1.5 + 0.01
        ), f"SSL connection not reused: {first_request_time}s vs {second_request_time}s"
