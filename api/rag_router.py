# -*- coding: utf-8 -*-
"""default_value RAG router.

Provides a single endpoint to perform semantic search via the ``core.rag_engine``
default_value implementation.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.rag_engine import search_similar, upsert_record, upsert_records

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"query": "example", "top_k": 0}},
    }


class IngestRequest(BaseModel):
    text: str
    id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"text": "example knowledge", "payload": {}}},
    }


class BatchIngestItem(BaseModel):
    text: str
    id: Optional[int] = None
    payload: Optional[Dict[str, Any]] = None


class BatchIngestRequest(BaseModel):
    items: List[BatchIngestItem]


@router.post(
    "/search",
    response_model=list,
    summary="RAG语义搜索",
    responses={
        (200): {"description": "搜索结果"},
        (400): {"description": "查询不能为空"},
    },
)
async def rag_search(req: SearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")
    results = search_similar(req.query, top_k=req.top_k)
    return results


@router.post(
    "/ingest",
    response_model=dict,
    summary="RAG 单条写入知识",
    responses={
        (200): {"description": "写入成功"},
        (400): {"description": "文本不能为空"},
    },
)
async def rag_ingest(req: IngestRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    record_id = req.id if req.id is not None else (abs(hash(req.text)) & ((1 << 63) - 1))
    upsert_record(record_id, req.text, req.payload)
    return {"record_id": record_id, "status": "ok"}


@router.post(
    "/ingest/batch",
    response_model=dict,
    summary="RAG 批量写入知识",
    responses={
        (200): {"description": "写入成功"},
        (400): {"description": "items 不能为空"},
    },
)
async def rag_ingest_batch(req: BatchIngestRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="items cannot be empty")
    records = [
        {
            "text": item.text,
            "id": item.id if item.id is not None else (abs(hash(item.text)) & ((1 << 63) - 1)),
            "payload": item.payload,
        }
        for item in req.items
    ]
    upsert_records(records)
    return {"count": len(records), "status": "ok"}
