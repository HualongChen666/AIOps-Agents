# -*- coding: utf-8 -*-
"""
全链路拓扑视图页面路由

提供一个简易的 HTML 页面，前端通过调用 `/api/topology/full-link` 接口获取全链路拓扑数据。
该页面主要用于快速查看拓扑结构，实际生产环境可将 Next.js 前端进行集成。
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from config import BASE_DIR

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/topology", tags=["全链路拓扑视图"])


@router.get("/", summary="全链路拓扑视图页面")
async def topology_page() -> FileResponse:
    """返回静态的全链路拓扑 HTML 页面。"""
    page_path = Path(BASE_DIR) / "static" / "topology.html"
    if not page_path.is_file():
        _logger.error("全链路拓扑页面文件缺失: %s", page_path)
        raise HTTPException(status_code=404, detail="Topology page not found")
    return FileResponse(str(page_path), media_type="text/html")
