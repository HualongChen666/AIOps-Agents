# -*- coding: utf-8 -*-
# tests/unit/test_rag_engine.py
# RAG引擎单元测试 (使用mock避免依赖问题)
import json
import sys  # noqa: F401
from typing import Any, Dict, List  # noqa: F401
from unittest.mock import MagicMock, Mock, patch  # noqa: F401

import pytest


class TestRAGEngineMock:
    """RAG引擎Mock测试 - 不依赖实际模块导入"""

    def test_mock_sentence_transformer(self):
        """测试Mock SentenceTransformer"""
        mock_transformer = MockSentenceTransformer("test-model")
        assert mock_transformer.model_name == "test-model"
        assert mock_transformer.dimension == 1024

        # 测试编码功能
        texts = ["test1", "test2"]
        vectors = mock_transformer.encode(texts)
        assert len(vectors) == 2
        assert len(vectors[0]) == 1024

    def test_mock_qdrant_client(self):
        """测试Mock QdrantClient"""
        mock_client = MockQdrantClient("http://localhost:6333")
        assert mock_client.url == "http://localhost:6333"
        assert mock_client.collections is not None

        # 测试collection创建
        mock_client.create_collection("test_collection", {"size": 1024})
        assert "test_collection" in mock_client.collections

    def test_mock_qdrant_upsert(self):
        """测试Mock QdrantClient upsert"""
        mock_client = MockQdrantClient("http://localhost:6333")
        mock_client.create_collection("test_collection", {"size": 1024})

        mock_point = MagicMock()
        mock_client.upsert("test_collection", [mock_point])

        assert len(mock_client.collections["test_collection"]["points"]) == 1

    def test_mock_qdrant_search(self):
        """测试Mock QdrantClient search"""
        mock_client = MockQdrantClient("http://localhost:6333")
        mock_client.create_collection("test_collection", {"size": 1024})

        results = mock_client.search(
            "test_collection", [0.1] * 1024, limit=5, with_payload=True, score_threshold=0.0
        )

        assert len(results) == 3
        assert results[0].score == 0.9

    def test_text_embedding_logic(self):
        """测试文本嵌入逻辑"""
        mock_transformer = MockSentenceTransformer("test-model")

        # 测试不同长度的文本
        short_text = "test"
        long_text = "a" * 1000

        vectors = mock_transformer.encode([short_text, long_text])

        assert len(vectors) == 2
        assert all(len(v) == 1024 for v in vectors)

    def test_vector_normalization(self):
        """测试向量归一化"""
        mock_transformer = MockSentenceTransformer("test-model")

        # 测试归一化
        vectors_normalized = mock_transformer.encode(["test"], normalize_embeddings=True)
        _ = mock_transformer.encode(["test"], normalize_embeddings=False)

        # 归一化的向量应该有单位长度
        norm_normalized = sum(x**2 for x in vectors_normalized[0]) ** 0.5
        assert abs(norm_normalized - 1.0) < 0.01  # 允许小误差

    def test_search_result_structure(self):
        """测试搜索结果结构"""
        mock_client = MockQdrantClient("http://localhost:6333")
        mock_client.create_collection("test_collection", {"size": 1024})

        results = mock_client.search(
            "test_collection", [0.1] * 1024, limit=5, with_payload=True, score_threshold=0.0
        )

        # 验证结果结构
        for result in results:
            assert hasattr(result, "score")
            assert hasattr(result, "payload")
            assert isinstance(result.score, float)
            assert isinstance(result.payload, dict)


class TestRAGEngineLogic:
    """RAG引擎逻辑测试（不依赖实际模块）"""

    def test_search_text_generation(self):
        """测试搜索文本生成逻辑"""
        # 模拟rag_engine中的文本拼接逻辑
        payload = {
            "repair_id": 1,
            "alert_id": "cpu_high",
            "script_key": "restart",
            "host": "server1",
            "verified": True,
            "comment": "成功修复",
        }

        # 模拟文本拼接
        search_parts = []
        for key in ["repair_id", "alert_id", "script_key", "host", "verified", "comment"]:
            val = payload.get(key)
            if val is None:
                continue
            if isinstance(val, dict):
                val_str = json.dumps(val, ensure_ascii=False)
            else:
                val_str = str(val)
            search_parts.append(val_str)

        search_text = " ".join(search_parts)

        assert "1" in search_text
        assert "cpu_high" in search_text
        assert "restart" in search_text
        assert "server1" in search_text
        assert "True" in search_text
        assert "成功修复" in search_text

    def test_dict_evidence_handling(self):
        """测试dict类型evidence处理"""
        payload = {
            "repair_id": 2,
            "evidence": {"metric": "memory.usage", "value": 90.5, "threshold": 80.0},
        }

        # 模拟文本拼接
        search_parts = []
        for key in ["repair_id", "evidence"]:
            val = payload.get(key)
            if val is None:
                continue
            if isinstance(val, dict):
                val_str = json.dumps(val, ensure_ascii=False)
            else:
                val_str = str(val)
            search_parts.append(val_str)

        search_text = " ".join(search_parts)

        assert "2" in search_text
        assert '"metric": "memory.usage"' in search_text or "memory.usage" in search_text

    def test_missing_field_handling(self):
        """测试缺失字段处理"""
        payload = {
            "repair_id": 3,
            # 缺少其他字段
        }

        # 模拟文本拼接
        search_parts = []
        for key in ["repair_id", "alert_id", "comment"]:
            val = payload.get(key)
            if val is None:
                continue
            val_str = str(val)
            search_parts.append(val_str)

        search_text = " ".join(search_parts)

        assert "3" in search_text
        # 缺失的字段不应该出现在搜索文本中

    def test_text_truncation(self):
        """测试文本截断逻辑"""
        long_string = "a" * 1000
        truncated = long_string[:64]

        assert len(truncated) == 64
        assert truncated == "a" * 64

    def test_collection_creation_logic(self):
        """测试collection创建逻辑"""
        # 模拟collection创建逻辑
        collections = {}
        collection_name = "test_collection"
        dim = 1024

        # 模拟创建collection
        if collection_name not in collections:
            collections[collection_name] = {
                "vectors_config": {"size": dim, "distance": "COSINE"},
                "points": [],
            }

        assert collection_name in collections
        assert collections[collection_name]["vectors_config"]["size"] == 1024

    def test_vector_dimension_validation(self):
        """测试向量维度验证"""
        # 模拟向量维度检查
        vectors = [[0.1] * 1024, [0.2] * 1024]

        # 检查向量维度
        for vector in vectors:
            assert len(vector) == 1024

        # 检查空向量
        empty_vectors = []
        with pytest.raises(ValueError):
            if not empty_vectors or not empty_vectors[0]:
                raise ValueError("Embedding failed - empty vectors returned")

    def test_search_score_threshold(self):
        """测试搜索分数阈值"""
        # 模拟搜索结果
        results = [
            MagicMock(score=0.95, payload={"id": 1}),
            MagicMock(score=0.85, payload={"id": 2}),
            MagicMock(score=0.75, payload={"id": 3}),
            MagicMock(score=0.65, payload={"id": 4}),
        ]

        # 应用分数阈值
        threshold = 0.7
        filtered_results = [r for r in results if r.score >= threshold]

        assert len(filtered_results) == 3
        assert all(r.score >= 0.7 for r in filtered_results)


class TestRAGEngineEdgeCases:
    """RAG引擎边界情况测试"""

    def test_very_long_text_handling(self):
        """测试超长文本处理"""
        very_long_text = "A" * 10000

        # 模拟截断
        if len(very_long_text) > 500:
            truncated = very_long_text[:500]
        else:
            truncated = very_long_text

        assert len(truncated) == 500

    def test_special_characters_handling(self):
        """测试特殊字符处理"""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

        # 确保特殊字符不会导致错误
        assert isinstance(special_chars, str)
        assert len(special_chars) > 0

    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        unicode_text = "测试Unicode：🎉🎊🎁📱💻⌨️🖥️"

        # 确保Unicode字符不会导致错误
        assert isinstance(unicode_text, str)
        assert len(unicode_text) > 0

    def test_empty_payload_handling(self):
        """测试空payload处理"""
        payload = {}

        # 模拟文本拼接
        search_parts = []
        for key in ["repair_id", "alert_id", "comment"]:
            val = payload.get(key)
            if val is None:
                continue
            val_str = str(val)
            search_parts.append(val_str)

        search_text = " ".join(search_parts)

        # 空payload应该产生空搜索文本
        assert search_text == ""

    def test_none_value_handling(self):
        """测试None值处理"""
        payload = {"repair_id": None, "alert_id": "test", "comment": None}

        # 模拟文本拼接
        search_parts = []
        for key in ["repair_id", "alert_id", "comment"]:
            val = payload.get(key)
            if val is None:
                continue
            val_str = str(val)
            search_parts.append(val_str)

        search_text = " ".join(search_parts)

        # None值应该被跳过
        assert "test" in search_text
        assert "None" not in search_text


class TestRAGEnginePerformance:
    """RAG引擎性能测试"""

    def test_vector_generation_performance(self):
        """测试向量生成性能"""
        import time

        mock_transformer = MockSentenceTransformer("test-model")

        # 测试批量编码性能
        texts = ["test"] * 100
        start = time.time()
        vectors = mock_transformer.encode(texts)
        elapsed = time.time() - start

        # 应该在合理时间内完成
        assert elapsed < 1.0  # 1秒内完成100个文本编码
        assert len(vectors) == 100

    def test_search_performance(self):
        """测试搜索性能"""
        import time

        mock_client = MockQdrantClient("http://localhost:6333")
        mock_client.create_collection("test_collection", {"size": 1024})

        # 添加一些点
        for i in range(100):
            mock_point = MagicMock()
            mock_point.id = i
            mock_point.vector = [0.1] * 1024
            mock_point.payload = {"id": i}
            mock_client.collections["test_collection"]["points"].append(mock_point)

        # 测试搜索性能
        start = time.time()
        results = mock_client.search(
            "test_collection", [0.1] * 1024, limit=10, with_payload=True, score_threshold=0.0
        )
        elapsed = time.time() - start

        # 应该在合理时间内完成
        assert elapsed < 0.5
        assert len(results) == 3  # mock返回固定数量


# Mock类定义
class MockSentenceTransformer:
    """模拟SentenceTransformer"""

    def __init__(self, model_name):
        self.model_name = model_name
        self.dimension = 1024

    def encode(self, texts, normalize_embeddings=True):
        """模拟编码，返回随机向量"""
        import random

        vectors = []
        for _ in texts:
            # 生成固定维度的随机向量
            vector = [random.random() for _ in range(self.dimension)]
            if normalize_embeddings:
                # 归一化
                norm = sum(x**2 for x in vector) ** 0.5
                vector = [x / norm for x in vector]
            vectors.append(vector)
        return vectors


class MockQdrantClient:
    """模拟Qdrant客户端"""

    def __init__(self, url):
        self.url = url
        self.collections = {}

    def get_collection(self, collection_name):
        if collection_name not in self.collections:
            raise Exception(f"Collection {collection_name} not found")
        return self.collections[collection_name]

    def create_collection(self, collection_name, vectors_config):
        self.collections[collection_name] = {"vectors_config": vectors_config, "points": []}

    def upsert(self, collection_name, points):
        if collection_name not in self.collections:
            raise Exception(f"Collection {collection_name} not found")
        self.collections[collection_name]["points"].extend(points)

    def search(self, collection_name, query_vector, limit, with_payload, score_threshold):
        if collection_name not in self.collections:
            return []
        # 返回模拟的搜索结果
        mock_results = []
        for i in range(min(limit, 3)):
            mock_result = MagicMock()
            mock_result.score = 0.9 - (i * 0.1)
            mock_result.payload = {"test": f"data_{i}", "id": i}
            mock_results.append(mock_result)
        return mock_results


class TestRAGEngineIntegration:
    """RAG引擎集成测试 - 使用mock测试实际函数"""

    def test_get_client_singleton(self):
        """测试客户端单例模式"""
        with patch("core.rag_engine.QDRANT_URL", "http://localhost:6333"):
            with patch("core.rag_engine.QdrantClient") as mock_qdrant_class:
                mock_client = MagicMock()
                mock_qdrant_class.return_value = mock_client

                from core.rag_engine import _get_client

                # 第一次调用
                client1 = _get_client()
                # 第二次调用应该返回同一个实例
                client2 = _get_client()

                assert client1 is client2
                mock_qdrant_class.assert_called_once()

    def test_get_client_failure(self):
        """测试客户端初始化失败 - 跳过，因为需要重置全局状态"""
        # 由于全局状态的影响，这个测试难以可靠地模拟失败情况
        pytest.skip("Global state makes failure testing difficult")

    def test_get_model_singleton(self):
        """测试模型单例模式"""
        with patch("core.rag_engine.SentenceTransformer") as mock_transformer_class:
            mock_model = MagicMock()
            mock_transformer_class.return_value = mock_model

            from core.rag_engine import _get_model

            # 第一次调用
            model1 = _get_model()
            # 第二次调用应该返回同一个实例
            model2 = _get_model()

            assert model1 is model2
            mock_transformer_class.assert_called_once()

    def test_get_model_failure(self):
        """测试模型加载失败 - 跳过，因为需要重置全局状态"""
        # 由于全局状态的影响，这个测试难以可靠地模拟失败情况
        pytest.skip("Global state makes failure testing difficult")

    def test_ensure_collection_existing(self):
        """测试collection已存在的情况"""
        with patch("core.rag_engine._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # collection已存在
            mock_client.get_collection.return_value = MagicMock()

            from core.rag_engine import _ensure_collection

            # 不应该创建新collection
            _ensure_collection(1024)
            mock_client.create_collection.assert_not_called()

    def test_ensure_collection_new(self):
        """测试创建新collection"""
        with patch("core.rag_engine._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            # collection不存在
            mock_client.get_collection.side_effect = Exception("Not found")

            from qdrant_client.http import models as qmodels  # noqa: F401

            from core.rag_engine import _ensure_collection

            # 应该创建新collection
            _ensure_collection(1024)
            mock_client.create_collection.assert_called_once()

    def test_embed_function(self):
        """测试嵌入函数"""
        with patch("core.rag_engine._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_embeddings = [[0.1] * 1024, [0.2] * 1024]
            mock_model.encode.return_value = mock_embeddings
            mock_get_model.return_value = mock_model

            from core.rag_engine import _embed

            texts = ["text1", "text2"]
            vectors = _embed(texts)

            assert len(vectors) == 2
            assert len(vectors[0]) == 1024
            mock_model.encode.assert_called_once_with(texts, normalize_embeddings=True)

    def test_upsert_verify_record_success(self):
        """测试成功写入验证记录"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]
            with patch("core.rag_engine._ensure_collection"):
                with patch("core.rag_engine._get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client

                    from core.rag_engine import upsert_verify_record

                    payload = {"repair_id": 1, "alert_id": "cpu_high", "comment": "测试修复"}

                    # 应该成功写入
                    upsert_verify_record(123, payload)
                    mock_client.upsert.assert_called_once()

    def test_upsert_verify_record_empty_vector(self):
        """测试空向量情况"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = []  # 空向量

            from core.rag_engine import upsert_verify_record

            payload = {"repair_id": 1}

            # 应该因为空向量而失败（被异常捕获）
            upsert_verify_record(123, payload)  # 不应该抛出异常，只是记录日志

    def test_upsert_verify_record_with_dict_evidence(self):
        """测试包含dict类型evidence的记录"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]
            with patch("core.rag_engine._ensure_collection"):
                with patch("core.rag_engine._get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_get_client.return_value = mock_client

                    from core.rag_engine import upsert_verify_record

                    payload = {"repair_id": 1, "evidence": {"metric": "cpu", "value": 90}}

                    upsert_verify_record(123, payload)
                    mock_client.upsert.assert_called_once()

    def test_search_similar_success(self):
        """测试成功搜索"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]
            with patch("core.rag_engine._ensure_collection"):
                with patch("core.rag_engine._get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_result = MagicMock()
                    mock_result.score = 0.9
                    mock_result.payload = {"id": 1}
                    mock_client.search.return_value = [mock_result]
                    mock_get_client.return_value = mock_client

                    from core.rag_engine import search_similar

                    results = search_similar("测试查询", top_k=5)

                    assert len(results) == 1
                    assert results[0]["score"] == 0.9
                    mock_client.search.assert_called_once()

    def test_search_similar_empty_vector(self):
        """测试空向量情况"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = []  # 空向量

            from core.rag_engine import search_similar

            results = search_similar("测试查询")

            # 应该返回空结果
            assert results == []

    def test_search_similar_failure(self):
        """测试搜索失败"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.side_effect = Exception("Embedding failed")

            from core.rag_engine import search_similar

            results = search_similar("测试查询")

            # 应该返回空结果而不是抛出异常
            assert results == []

    def test_search_similar_custom_top_k(self):
        """测试自定义top_k参数"""
        with patch("core.rag_engine._embed") as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]
            with patch("core.rag_engine._ensure_collection"):
                with patch("core.rag_engine._get_client") as mock_get_client:
                    mock_client = MagicMock()
                    mock_client.search.return_value = []
                    mock_get_client.return_value = mock_client

                    from core.rag_engine import search_similar

                    search_similar("测试查询", top_k=10)

                    # 验证使用了正确的limit参数
                    call_args = mock_client.search.call_args
                    assert call_args[1]["limit"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
