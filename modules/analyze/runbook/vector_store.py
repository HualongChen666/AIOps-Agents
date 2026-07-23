# -*- coding: utf-8 -*-
"""
Vector Store for RAG
向量存储模块，用于RAG的向量检索

功能:
- 向量嵌入
- 向量存储
- 相似度搜索
- 批量操作
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union  # noqa: F401

import numpy as np

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    # Define a stub for type checking
    if TYPE_CHECKING:
        from qdrant_client import QdrantClient  # type: ignore[misc]

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Define a stub for type checking
    if TYPE_CHECKING:
        from sentence_transformers import SentenceTransformer  # type: ignore[misc]

logger = logging.getLogger(__name__)


class VectorStore:
    """
    向量存储类

    使用Qdrant作为向量数据库，SentenceTransformers作为嵌入模型。

    参数:
        collection_name: 集合名称
        embedding_model: 嵌入模型名称或路径
        qdrant_url: Qdrant服务URL
        qdrant_api_key: Qdrant API密钥
        vector_size: 向量维度
        distance: 距离度量方式
    """

    def __init__(
        self,
        collection_name: str = "runbook_knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
        vector_size: int = 384,
        distance: str = "cosine",
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.vector_size = vector_size
        self.distance = distance

        self.client: Optional[QdrantClient] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.is_initialized = False

    def initialize(self) -> None:
        """初始化向量存储"""
        logger.info("Initializing vector store")

        # 初始化嵌入模型
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded: %s", self.embedding_model_name)
            except Exception as e:
                logger.warning("Failed to load embedding model: %s", e)
        else:
            logger.warning("sentence-transformers not installed")

        # 初始化Qdrant客户端
        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key,
                )
                logger.info("Qdrant client connected: %s", self.qdrant_url)

                # 创建集合（如果不存在）
                self._create_collection_if_not_exists()

            except Exception as e:
                logger.warning("Failed to connect to Qdrant: %s", e)
        else:
            logger.warning("qdrant-client not installed")

        self.is_initialized = True
        logger.info("Vector store initialized")

    def _create_collection_if_not_exists(self) -> None:
        """创建集合（如果不存在）"""
        if self.client is None:
            return

        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                distance_map = {
                    "cosine": Distance.COSINE,
                    "euclidean": Distance.EUCLID,
                    "dot": Distance.DOT,
                }

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=distance_map.get(self.distance, Distance.COSINE),
                    ),
                )
                logger.info("Collection created: %s", self.collection_name)
        except Exception as e:
            logger.warning("Failed to create collection: %s", e)

    def embed_text(self, text: str) -> np.ndarray:
        """
        将文本嵌入为向量

        参数:
            text: 输入文本

        返回:
            向量
        """
        if self.embedding_model is None:
            # 降级：返回随机向量
            logger.warning("Embedding model not available, using random vector")
            return np.random.rand(self.vector_size).astype(np.float32)

        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error("Failed to embed text: %s", e)
            return np.random.rand(self.vector_size).astype(np.float32)

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        批量嵌入文本

        参数:
            texts: 文本列表

        返回:
            向量列表
        """
        if self.embedding_model is None:
            logger.warning("Embedding model not available, using random vectors")
            return [np.random.rand(self.vector_size).astype(np.float32) for _ in texts]

        try:
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            return [emb.astype(np.float32) for emb in embeddings]
        except Exception as e:
            logger.error("Failed to embed batch: %s", e)
            return [np.random.rand(self.vector_size).astype(np.float32) for _ in texts]

    def add_document(
        self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加文档到向量存储

        参数:
            document_id: 文档ID
            content: 文档内容
            metadata: 元数据

        返回:
            是否成功
        """
        if not self.is_initialized:
            self.initialize()

        if self.client is None:
            logger.warning("Qdrant client not available")
            return False

        try:
            # 嵌入文本
            embedding = self.embed_text(content)

            # 创建点
            point = PointStruct(
                id=document_id,
                vector=embedding.tolist(),
                payload={
                    "content": content,
                    **(metadata or {}),
                },
            )

            # 插入点
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug("Document added: %s", document_id)
            return True

        except Exception as e:
            logger.error("Failed to add document: %s", e)
            return False

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """
        批量添加文档

        参数:
            documents: 文档列表，每个文档包含id、content、metadata

        返回:
            成功添加的数量
        """
        if not self.is_initialized:
            self.initialize()

        if self.client is None:
            logger.warning("Qdrant client not available")
            return 0

        try:
            # 批量嵌入
            texts = [doc["content"] for doc in documents]
            embeddings = self.embed_batch(texts)

            # 创建点
            points = []
            for doc, embedding in zip(documents, embeddings):
                point = PointStruct(
                    id=doc["id"],
                    vector=embedding.tolist(),
                    payload={
                        "content": doc["content"],
                        **(doc.get("metadata", {})),
                    },
                )
                points.append(point)

            # 批量插入
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info("Batch added %d documents", len(documents))
            return len(documents)

        except Exception as e:
            logger.error("Failed to add documents batch: %s", e)
            return 0

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        相似度搜索

        参数:
            query: 查询文本
            top_k: 返回top-k结果
            score_threshold: 分数阈值
            filter_metadata: 元数据过滤条件

        返回:
            搜索结果列表
        """
        if not self.is_initialized:
            self.initialize()

        if self.client is None:
            logger.warning("Qdrant client not available")
            return []

        try:
            # 嵌入查询
            query_embedding = self.embed_text(query)

            # 构建过滤条件
            query_filter = None
            if filter_metadata:
                conditions: List[Union[FieldCondition, Filter]] = []
                for key, value in filter_metadata.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)  # type: ignore[arg-type]

            # 搜索
            search_result = self.client.search(  # type: ignore[attr-defined]
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            # 格式化结果
            results = []
            for hit in search_result:
                results.append(
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "payload": hit.payload,
                    }
                )

            logger.debug("Search returned %d results", len(results))
            return results

        except Exception as e:
            logger.error("Failed to search: %s", e)
            return []

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档

        参数:
            document_id: 文档ID

        返回:
            是否成功
        """
        if self.client is None:
            return False

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[document_id],
            )
            logger.debug("Document deleted: %s", document_id)
            return True
        except Exception as e:
            logger.error("Failed to delete document: %s", e)
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        """
        获取集合信息

        返回:
            集合信息
        """
        if self.client is None:
            return {}

        try:
            info = self.client.get_collection(self.collection_name)
            vectors_config = info.config.params.vectors
            if isinstance(vectors_config, dict):
                vector_size = next(iter(vectors_config.values())).size if vectors_config else 0
            elif vectors_config is not None:
                vector_size = vectors_config.size
            else:
                vector_size = 0
            return {
                "name": vector_size,
                "vector_count": info.points_count,
                "indexed_vector_count": info.indexed_vectors_count,
            }
        except Exception as e:
            logger.error("Failed to get collection info: %s", e)
            return {}

    def clear_collection(self) -> bool:
        """
        清空集合

        返回:
            是否成功
        """
        if self.client is None:
            return False

        try:
            self.client.delete_collection(self.collection_name)
            self._create_collection_if_not_exists()
            logger.info("Collection cleared: %s", self.collection_name)
            return True
        except Exception as e:
            logger.error("Failed to clear collection: %s", e)
            return False
