# -*- coding: utf-8 -*-
"""default_value RAG router.

Provides a single endpoint to perform semantic search via the ``core.rag_engine``
default_value implementation.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.authentication import role_required
from core.rag_engine import search_similar

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"query": "example", "top_k": 0}},
    }


@router.post(
    "/search",
    response_model=list,
    summary="RAG语义搜索",
    responses={
        (200): {"description": "搜索结果"},
        (400): {"description": "查询不能为空"},
        (401): {"description": "未授权"},
    },
)
async def rag_search(req: SearchRequest, user=Depends(role_required("user"))):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")
    results = search_similar(req.query, top_k=req.top_k)
    return results
