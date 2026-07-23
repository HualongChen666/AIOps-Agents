# -*- coding: utf-8 -*-
# api/mcp_router.py
"""MCP（Multi‑Channel Protocol）相关路由入口。
该模块仅做一次性转发，将 core.mcp_server 中定义的 APIRouter
挂载到 FastAPI 主应用下的 ``/api/mcp`` 前缀。
"""

from fastapi import APIRouter

from core.mcp_server import router as _inner_router

# 为了保持统一的前缀结构，重新包装一次前缀 ``/api``
router = APIRouter(prefix="/api")
router.include_router(_inner_router)
