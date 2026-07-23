# -*- coding: utf-8 -*-
"""
审计中心页面路由

提供前端页面 `/audit_center/`，展示审计报告与导出功能。
页面文件位于 `static/audit_center.html`，若不存在会记录错误并返回 404。
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit_center", tags=["审计中心页面"])


@router.get(
    "/",
    response_class=FileResponse,
    summary="审计中心页面",
    description="返回审计中心的 HTML 页面（static/audit_center.html）",
    responses={
        200: {"description": "HTML页面"},
        404: {"description": "页面未部署"},
    },
)
async def audit_center_page() -> FileResponse:
    """返回审计中心的静态 HTML 页面。

    若页面文件缺失，记录错误并抛出 404。
    """
    page_path = BASE_DIR / "static" / "audit_center.bak"
    if not page_path.is_file():
        _logger.error("审计中心页面未找到: %s", page_path)
        raise HTTPException(status_code=404, detail="Audit center page not found")
    return FileResponse(page_path, media_type="text/html")
