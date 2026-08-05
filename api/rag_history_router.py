# -*- coding: utf-8 -*-
"""
RAG 历史搜索页面路由

提供一个简易的 HTML 页面，用户可以输入关键字并通过前端 fetch 调用
已有的 RAG 搜索接口（/api/rag/search）查看相似记录。

GET /rag_history/    -> 返回 static/rag_history_search.html 页面
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag_history", tags=["RAG 历史搜索"])


@router.get(
    "/",
    response_class=FileResponse,
    summary="RAG 历史搜索页面",
    description="返回用于搜索历史相似案例的前端页面",
    responses={
        200: {"description": "HTML页面"},
        404: {"description": "页面未部署"},
    },
)
async def rag_history_page() -> FileResponse:
    """返回 RAG 历史搜索 UI 页面（HTML）。"""
    html_path = BASE_DIR / "static" / "rag_history_search.html"
    if not html_path.is_file():
        _logger.error("RAG 历史搜索页面文件未找到: %s", html_path)
        raise HTTPException(status_code=404, detail="RAG 历史搜索页面未部署")
    return FileResponse(path=html_path, media_type="text/html")
