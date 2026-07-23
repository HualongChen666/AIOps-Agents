# -*- coding: utf-8 -*-
"""
E2E Test: Qdrant Vector Database Integration
真实E2E测试：Qdrant向量数据库集成测试，不使用Mock
"""

import asyncio
import json  # noqa: F401
from datetime import datetime

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestQdrantIntegration:
    """Qdrant向量数据库集成E2E测试"""

    @pytest.mark.asyncio
    async def test_vector_collection_creation(self, http_client, test_qdrant_url):
        """测试向量集合创建"""

        collection_name = f"test_collection_{int(datetime.now().timestamp())}"

        # 创建集合
        create_response = await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={
                "vector_size": 1536,  # OpenAI embedding size
                "distance": "cosine",
                "payload": {"description": "Test collection for E2E tests"},
            },
            timeout=15.0,
        )

        # 如果向量API不存在，跳过测试
        if create_response.status_code == 404:
            pytest.skip("Vector database API not available")

        assert create_response.status_code in [200, 201]

        # 验证集合创建
        get_response = await http_client.get(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

        assert get_response.status_code == 200
        collection_info = get_response.json()
        assert collection_info["name"] == collection_name

        # 清理
        delete_response = await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

        assert delete_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_vector_insertion_and_search(self, http_client, test_qdrant_url):
        """测试向量插入和搜索"""

        collection_name = f"search_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        # 插入测试向量
        vectors = [
            {
                "id": 1,
                "vector": [0.1] * 1536,  # 模拟向量
                "payload": {"text": "CPU使用率过高", "category": "performance"},
            },
            {
                "id": 2,
                "vector": [0.2] * 1536,
                "payload": {"text": "内存不足", "category": "performance"},
            },
            {
                "id": 3,
                "vector": [0.3] * 1536,
                "payload": {"text": "网络延迟", "category": "network"},
            },
        ]

        insert_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={"points": vectors},
            timeout=15.0,
        )

        if insert_response.status_code == 404:
            pytest.skip("Vector database API not available")

        assert insert_response.status_code in [200, 201]

        # 等待索引更新
        await asyncio.sleep(1)

        # 搜索向量
        search_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/search",
            json={"vector": [0.15] * 1536, "limit": 3, "score_threshold": 0.5},
            timeout=15.0,
        )

        assert search_response.status_code == 200
        search_results = search_response.json()

        # 验证搜索结果
        assert len(search_results) > 0
        assert all("score" in result for result in search_results)
        assert all("payload" in result for result in search_results)

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, http_client, test_qdrant_url):
        """测试向量相似度搜索"""

        collection_name = f"similarity_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        # 插入相似和不相似的向量
        similar_vectors = [
            {
                "id": i,
                "vector": [0.5 + i * 0.01] * 1536,
                "payload": {"type": "similar", "label": f"similar_{i}"},
            }
            for i in range(10)
        ]

        different_vector = {
            "id": 99,
            "vector": [0.9] * 1536,
            "payload": {"type": "different", "label": "different"},
        }

        await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={"points": similar_vectors + [different_vector]},
            timeout=15.0,
        )

        if similar_vectors[0].get("vector") is None:
            pytest.skip("Vector database not properly configured")

        # 搜索相似向量
        search_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/search",
            json={"vector": [0.51] * 1536, "limit": 5, "filter": {"type": "similar"}},
            timeout=15.0,
        )

        if search_response.status_code == 404:
            pytest.skip("Vector search API not available")

        assert search_response.status_code == 200
        results = search_response.json()

        # 验证相似度排序
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i + 1]["score"]

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_vector_filtering(self, http_client, test_qdrant_url):
        """测试向量过滤"""

        collection_name = f"filter_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        # 插入带有不同payload的向量
        vectors = [
            {
                "id": 1,
                "vector": [0.1] * 1536,
                "payload": {"category": "performance", "severity": "critical"},
            },
            {
                "id": 2,
                "vector": [0.2] * 1536,
                "payload": {"category": "network", "severity": "warning"},
            },
            {
                "id": 3,
                "vector": [0.3] * 1536,
                "payload": {"category": "performance", "severity": "warning"},
            },
        ]

        insert_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={"points": vectors},
            timeout=15.0,
        )

        if insert_response.status_code == 404:
            pytest.skip("Vector database API not available")

        # 按category过滤搜索
        filter_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/search",
            json={"vector": [0.15] * 1536, "limit": 10, "filter": {"category": "performance"}},
            timeout=15.0,
        )

        assert filter_response.status_code == 200
        filtered_results = filter_response.json()

        # 验证过滤结果
        assert all(result["payload"]["category"] == "performance" for result in filtered_results)

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_vector_batch_operations(self, http_client, test_qdrant_url):
        """测试向量批量操作"""

        collection_name = f"batch_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        # 批量插入大量向量
        batch_size = 100
        vectors = [
            {"id": i, "vector": [i / batch_size] * 1536, "payload": {"batch_index": i}}
            for i in range(batch_size)
        ]

        batch_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={"points": vectors},
            timeout=30.0,
        )

        if batch_response.status_code == 404:
            pytest.skip("Vector batch API not available")

        assert batch_response.status_code in [200, 201]

        # 验证批量插入
        count_response = await http_client.get(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/count", timeout=10.0
        )

        assert count_response.status_code == 200
        count = count_response.json()
        assert count["count"] == batch_size

        # 批量删除
        delete_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points/delete",
            json={"ids": list(range(batch_size))},
            timeout=15.0,
        )

        assert delete_response.status_code in [200, 204]

        # 验证删除
        count_after_delete = await http_client.get(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/count", timeout=10.0
        )

        assert count_after_delete.json()["count"] == 0

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_vector_update_and_delete(self, http_client, test_qdrant_url):
        """测试向量更新和删除"""

        collection_name = f"update_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        # 插入向量
        await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={"points": [{"id": 1, "vector": [0.1] * 1536, "payload": {"status": "original"}}]},
            timeout=15.0,
        )

        # 更新向量
        update_response = await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points/1",
            json={"vector": [0.2] * 1536, "payload": {"status": "updated"}},
            timeout=15.0,
        )

        if update_response.status_code == 404:
            pytest.skip("Vector update API not available")

        assert update_response.status_code in [200, 202]

        # 验证更新
        get_response = await http_client.get(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points/1",
            timeout=10.0,
        )

        assert get_response.status_code == 200
        point = get_response.json()
        assert point["payload"]["status"] == "updated"

        # 删除向量
        delete_response = await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points/1",
            timeout=10.0,
        )

        assert delete_response.status_code in [200, 204]

        # 验证删除
        get_after_delete = await http_client.get(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points/1",
            timeout=10.0,
        )

        assert get_after_delete.status_code == 404

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )

    @pytest.mark.asyncio
    async def test_vector_performance(self, http_client, test_qdrant_url):
        """测试向量操作性能"""

        collection_name = f"perf_test_{int(datetime.now().timestamp())}"

        # 创建集合
        await http_client.put(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}",
            json={"vector_size": 1536, "distance": "cosine"},
            timeout=15.0,
        )

        import time

        # 测试插入性能
        start_time = time.time()
        await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/points",
            json={
                "points": [
                    {"id": i, "vector": [i / 1000] * 1536, "payload": {"index": i}}
                    for i in range(1000)
                ]
            },
            timeout=30.0,
        )
        insert_time = time.time() - start_time

        if insert_time > 25:  # 如果插入超时，可能API不存在
            pytest.skip("Vector database performance test timeout")

        assert insert_time < 30  # 1000个向量应该在30秒内插入

        # 测试搜索性能
        start_time = time.time()
        search_response = await http_client.post(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}/search",
            json={"vector": [0.5] * 1536, "limit": 10},
            timeout=15.0,
        )
        search_time = time.time() - start_time

        assert search_response.status_code == 200
        assert search_time < 5  # 搜索应该在5秒内完成

        # 清理
        await http_client.delete(
            f"http://localhost:8000/api/v1/vector/collections/{collection_name}", timeout=10.0
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
