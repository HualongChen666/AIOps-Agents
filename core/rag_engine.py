# -*- coding: utf-8 -*-
# core/rag_engine.py
"""RAG (Retrieval‑Augmented Generation) 引擎

- 使用 Qdrant 作为向量数据库（本地自托管或远程 SaaS）
- 使用 sentence‑transformers 的 BGE‑zh‑Embedding 模型进行中文语义向量化
- 提供统一的 `upsert_verify_record` 与 `search_similar` 接口，供 `runbook_generator`
  与 `verifier` 调用

设计原则
~~~~~~~~~~
1. **懒加载** – 在首次使用时才创建 Qdrant 客户端，避免在没有 Qdrant 服务的环境下导入失败。
2. **容错** – 若 Qdrant 连接异常，日志记录错误并返回空结果，业务流程仍可继续。
3. **向量维度自适应** – 通过模型的 `get_sentence_embedding_dimension()` 动态获取维度。
4. **统一 collection** – 所有验证记录写入同一 collection `verify_records`，payload 中保存原始 JSON，便于后续检索展示。
"""

import json
import logging
import os
from typing import Any, Dict, List, cast

from config import QDRANT_URL

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# 单例‑客户端以及模型加载（懒惰）
# ------------------------------------------------------------
_client: Any | None = None
_model: Any | None = None
_qmodels: Any | None = None
QdrantClient: Any | None = None
SentenceTransformer: Any | None = None
_COLLECTION_NAME = "verify_records"
_DEFAULT_EMBEDDING_MODEL = os.environ.get("AIOPS_EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
_FALLBACK_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_RETRIEVAL_SCORE_THRESHOLD = float(os.environ.get("RAG_SCORE_THRESHOLD", "0.55"))


def _get_client() -> Any:
    """获取全局 Qdrant 客户端实例，首次调用时创建。"""
    global _client, _qmodels, QdrantClient
    if QdrantClient is None:
        from qdrant_client import QdrantClient as _QdrantClient
        from qdrant_client.http import models as qmodels

        QdrantClient = _QdrantClient
        _qmodels = qmodels
    if _client is None:
        try:
            _client = QdrantClient(url=QDRANT_URL)
            logger.info("[RAG] Qdrant client 初始化完成 (url=%s)", QDRANT_URL)
        except Exception as e:
            logger.error("[RAG] Qdrant client 初始化失败: %s", e)
            raise
    return _client


def _get_model() -> Any:
    """加载 BGE 中文嵌入模型（一次性），返回模型实例。"""
    global _model, SentenceTransformer
    if SentenceTransformer is None:
        from sentence_transformers import SentenceTransformer as _SentenceTransformer

        SentenceTransformer = _SentenceTransformer
    if _model is None:
        # Try primary Chinese/ops model, then fallback to ensure availability
        for model_name in (_DEFAULT_EMBEDDING_MODEL, _FALLBACK_EMBEDDING_MODEL):
            try:
                _model = SentenceTransformer(model_name, local_files_only=True)
                logger.info("[RAG] SentenceTransformer 模型加载完成: %s", model_name)
                break
            except Exception as e:
                logger.warning("[RAG] 加载 SentenceTransformer %s 失败: %s", model_name, e)
        if _model is None:
            raise RuntimeError("[RAG] 无法加载任何 SentenceTransformer 模型")
    return _model


def _get_qmodels() -> Any:
    """Lazy accessor for qdrant http models used by upsert/search."""
    global _qmodels
    if _qmodels is None:
        from qdrant_client.http import models as qmodels

        _qmodels = qmodels
    return _qmodels


def _ensure_collection(dim: int) -> None:
    """确保 Qdrant 中存在 collection，若不存在则创建。"""
    client = _get_client()
    qm = _get_qmodels()
    try:
        client.get_collection(_COLLECTION_NAME)
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        # 创建 collection，使用 HNSW 索引，metric 为 cosine
        client.create_collection(
            collection_name=_COLLECTION_NAME,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )
        logger.info("[RAG] 创建 Qdrant collection '%s' (dim=%d)", _COLLECTION_NAME, dim)


# ------------------------------------------------------------
# 公共向量化函数
# ------------------------------------------------------------
def _embed(texts: List[str]) -> List[List[float]]:
    """使用 SentenceTransformer 将文本列表转为向量。"""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    if hasattr(embeddings, "tolist"):
        return cast(List[List[float]], embeddings.tolist())
    # If it's already a list, ensure it's the right type
    return cast(List[List[float]], embeddings)


# ------------------------------------------------------------
# 对外 API – 写入验证记录向量
# ------------------------------------------------------------
def upsert_verify_record(record_id: int, payload: Dict[str, Any]) -> None:
    """将单条验证记录写入 Qdrant。

    - `record_id` : SQLite 主键，用作向量的唯一 ID。
    - `payload`   : 需要保存在向量库的原始数据（JSON 可序列化），
                    常包含 `repair_id`, `alert_id`, `script_key`, `host`,
                    `verified`, `comment` 等业务字段。
    """
    try:
        # 将业务描述字段拼接为检索文本，降低维度稀疏性
        # 将关键字段拼接为检索文本，包含 evidence（如有）
        search_parts = []
        for key in [
            "repair_id",
            "alert_id",
            "script_key",
            "host",
            "verified",
            "comment",
            "evidence",
        ]:
            val = payload.get(key)
            if val is None:
                continue
            # evidence 可能是 dict，转为 JSON 字符串便于检索
            if isinstance(val, dict):
                try:
                    val_str = json.dumps(val, ensure_ascii=False)
                except Exception as e:
                    logging.exception("Unexpected exception: %s", e)
                    val_str = str(val)
            else:
                val_str = str(val)
            search_parts.append(val_str)
        search_text = " ".join(search_parts)
        vectors = _embed([search_text])
        # SECURITY: Check if vectors is empty to avoid IndexError
        if not vectors or not vectors[0]:
            raise ValueError("Embedding failed - empty vectors returned")
        dim = len(vectors[0])
        _ensure_collection(dim)
        client = _get_client()
        client.upsert(
            collection_name=_COLLECTION_NAME,
            points=[
                _get_qmodels().PointStruct(
                    id=record_id,
                    vector=vectors[0],
                    payload=payload,
                )
            ],
        )
        logger.info("[RAG] Upsert verify record id=%s 成功", record_id)
    except Exception as e:
        logger.error("[RAG] Upsert verify record id=%s 失败: %s", record_id, e)


# ------------------------------------------------------------
# 对外 API – 语义检索
# ------------------------------------------------------------
class AIOpsRAG:
    """RAG wrapper exposing search semantics used by MCP tools."""

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search similar records using the global RAG engine."""
        return search_similar(query, top_k=top_k)


def search_similar(
    query: str, top_k: int = 5, score_threshold: float = 0.0
) -> List[Dict[str, Any]]:
    """基于语义相似度检索历史验证记录。

    返回列表中每项包含原始 `payload` 与相似度分数 `score`。
    当 `score_threshold` 为 0 时使用环境变量 `RAG_SCORE_THRESHOLD` 默认值。
    """
    try:
        threshold = score_threshold or _RETRIEVAL_SCORE_THRESHOLD
        vectors = _embed([query])
        # SECURITY: Check if vectors is empty to avoid IndexError
        if not vectors or not vectors[0]:
            raise ValueError("Embedding failed - empty vectors returned")
        dim = len(vectors[0])
        _ensure_collection(dim)
        client = _get_client()
        raw = client.search(  # type: ignore[attr-defined]
            collection_name=_COLLECTION_NAME,
            query_vector=vectors[0],
            limit=top_k,
            with_payload=True,
            score_threshold=threshold,
        )
        results = []
        for point in raw:
            results.append({"score": point.score, "payload": point.payload})
        logger.info("[RAG] search_similar query='%s' 返回 %d 条", query, len(results))
        return results
    except Exception as e:
        logger.error("[RAG] search_similar 失败: %s", e)
        return []


# ------------------------------------------------------------
# 简易示例（仅在直接运行本文件时执行，生产环境通过 API 调用）
# ------------------------------------------------------------
__all__ = [
    "AIOpsRAG",
    "search_similar",
    "upsert_verify_record",
]

if __name__ == "__main__":
    demo_payload = {
        "repair_id": 1,
        "alert_id": "cpu_high",
        "script_key": "restart_service",
        "host": "host-01",
        "verified": True,
        "comment": "服务成功重启",
    }
    upsert_verify_record(9999, demo_payload)
    print(search_similar("服务 重启 主机"))