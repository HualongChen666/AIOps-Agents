# -*- coding: utf-8 -*-
# core/es_logger.py
# Elasticsearch 日志聚合封装
# 提供异步客户端单例、日志写入、搜索接口
# 依赖 elasticsearch[async] >= 8.13.0

from core.observability_query import (
    DEFAULT_MAX_LLM_ITEMS,
    QueryCache,
    cached_query,
    make_cache_key,
    prepare_for_llm,
    validate_es_query_string,
    with_query_timeout,
)
from config import ELASTICSEARCH_URL
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast  # noqa: F401

logger = logging.getLogger(__name__)

try:
    from elasticsearch import AsyncElasticsearch, NotFoundError

    ElasticsearchClient = AsyncElasticsearch
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("elasticsearch not available, ES logging disabled: %s", e)
    AsyncElasticsearch = None  # type: ignore[assignment]
    ElasticsearchClient = None  # type: ignore[assignment]

    # Define a dummy NotFoundError if elasticsearch is not available
    NotFoundError = Exception  # type: ignore[misc,assignment]


logger = logging.getLogger(__name__)

# 单例客户端
_es_client: Optional[Any] = None  # type: ignore[misc]
_es_query_cache = QueryCache()


def get_es_client():
    """获取或创建全局 AsyncElasticsearch 客户端实例"""
    global _es_client
    if _es_client is None:
        es_url = ELASTICSEARCH_URL
        _es_client = AsyncElasticsearch([es_url], request_timeout=30)
        logger.info(f"Elasticsearch client initialized | url={es_url}")
    return _es_client


async def index_log(index: str, doc: Dict[str, Any]) -> str:
    """向指定索引写入单条日志文档，返回文档 ID。ES 不可用时落地到本地 NDJSON fallback。"""
    client = get_es_client()
    if client is not None:
        try:
            resp = await client.index(index=index, document=doc)
            doc_id = str(resp["_id"])
            logger.debug(f"Indexed log into {index} id={doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to index log to Elasticsearch: {e}, falling back to local file")

    doc_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    fallback_path = Path("data/es_fallback") / f"{index}.ndjson"
    fallback_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with fallback_path.open("a", encoding="utf-8") as f:
            line = {"_id": doc_id, "@timestamp": timestamp, "document": doc}
            f.write(__import__("json").dumps(line, ensure_ascii=False) + "\n")
        logger.info(f"ES fallback: log written to {fallback_path} id={doc_id}")
    except Exception as fallback_exc:
        logger.error(f"ES fallback write failed: {fallback_exc}")
        raise
    return doc_id


async def es_search_logs(
    index: str = "logs",
    query: str = "*",
    size: int = 100,
    from_: int = 0,
) -> List[Dict[str, Any]]:
    """在 Elasticsearch 中搜索日志
    参数:
        index   索引名称（默认 logs）
        query   Elasticsearch DSL 简单查询字符串
        size    返回条数上限
        from_   分页偏移
    返回:
        包含 _source 的日志列表
    """
    client = get_es_client()
    # Validate the free-text query to mitigate query_string injection.
    try:
        validate_es_query_string(query)
    except ValueError as exc:
        logger.warning("Invalid Elasticsearch query rejected: %s", exc)
        return []

    size = min(int(size), DEFAULT_MAX_LLM_ITEMS)
    from_ = max(0, int(from_))

    body = {
        "query": {
            "query_string": {
                "query": query,
                "default_field": "message",
                "default_operator": "AND",
                "allow_leading_wildcard": False,
            }
        },
        "from": from_,
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
    }

    async def _search() -> List[Dict[str, Any]]:
        resp = await client.search(index=index, body=body, request_timeout=30)
        hits = resp.get("hits", {}).get("hits", [])
        return [hit.get("_source", {}) for hit in hits]

    try:
        cache_key = make_cache_key("es_search", index, query, size, from_)
        results = await cached_query(
            _es_query_cache,
            cache_key,
            with_query_timeout(_search()),
        )
        # Redact PII and bound token volume before downstream/API/LLM consumption.
        return cast(List[Dict[str, Any]], prepare_for_llm(results))
    except NotFoundError:
        logger.warning(f"Elasticsearch index not found: {index}")
        return []
    except Exception as e:
        logger.error(f"Elasticsearch search error: {e}", exc_info=True)
        return []
