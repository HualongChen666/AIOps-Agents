# -*- coding: utf-8 -*-
"""
HITL (Human‑In‑The‑Loop) 审批中心页面路由

提供一个静态 HTML 页面，用于展示待审批的修复请求列表，
页面会自行调用后端 `/api/v1/hitl/approval/approve`、`/api/v1/hitl/approval/reject` 等接口获取数据。

访问方式:
    GET /hitl-page/   -> 返回 static/hitl_approval.html（HTML）

真实审批端点位于 `api/hitl_router.py`。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl-page", tags=["HITL Approval Page"])


@router.get(
    "/",
    response_class=FileResponse,
    summary="返回 HITL 审批中心页面",
    description="返回存放于 static 目录下的 HITL 审批中心 HTML 页面（hitl_approval.html）",
    responses={
        200: {"description": "HTML页面"},
        404: {"description": "页面未部署"},
    },
)
def hitl_approval_page() -> FileResponse:
    """读取并返回 static/hitl_approval.bak 文件。

    若文件缺失则记录错误日志并抛出 404。
    """
    page_path: Path = BASE_DIR / "static" / "hitl_approval.html"
    if not page_path.is_file():
        _logger.error("HITL 审批中心页面文件未找到: %s", page_path)
        raise HTTPException(status_code=404, detail="HITL Approval page not found")
    return FileResponse(page_path, media_type="text/html")
