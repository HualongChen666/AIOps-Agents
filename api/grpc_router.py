# -*- coding: utf-8 -*-
"""
gRPC API Router
Phase 3 集成: gRPC 接口路由
"""

import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grpc", tags=["grpc"])

# Phase 3 集成: gRPC 接口
try:
    from core.interface.grpc import AIOpsGrpcServer

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    logger.warning("Phase 3 gRPC not available")


_grpc_server: Optional[AIOpsGrpcServer] = None

if GRPC_AVAILABLE:
    try:
        # Initialize gRPC server
        _grpc_server = AIOpsGrpcServer(host=os.getenv("GRPC_HOST", "127.0.0.1"), port=50051)
        logger.info("Phase 3 gRPC server initialized")
    except Exception as e:
        logger.error(f"Failed to initialize gRPC server: {e}")
        _grpc_server = None


@router.get(
    "/health",
    summary="gRPC健康检查",
    responses={
        200: {
            "description": "健康状态",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "grpc_available": True, "server_running": True}
                }
            },
        },
    },
)
async def grpc_health() -> Dict[str, Any]:
    """gRPC health check endpoint"""
    return {
        "status": "healthy" if GRPC_AVAILABLE else "degraded",
        "grpc_available": GRPC_AVAILABLE,
        "server_running": _grpc_server is not None,
    }


@router.post(
    "/start",
    summary="启动gRPC服务器",
    responses={
        200: {
            "description": "启动成功",
            "content": {
                "application/json": {
                    "example": {"status": "started", "message": "gRPC server started successfully"}
                }
            },
        },
        503: {"description": "gRPC不可用"},
        500: {"description": "启动失败"},
    },
)
async def start_grpc_server() -> Dict[str, Any]:
    """Start gRPC server"""
    if not GRPC_AVAILABLE or not _grpc_server:
        raise HTTPException(status_code=503, detail="gRPC not available")

    try:
        await _grpc_server.start()
        return {"status": "started", "message": "gRPC server started successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start gRPC server: {str(e)}")


@router.post(
    "/stop",
    summary="停止gRPC服务器",
    responses={
        200: {
            "description": "停止成功",
            "content": {
                "application/json": {
                    "example": {"status": "stopped", "message": "gRPC server stopped successfully"}
                }
            },
        },
        503: {"description": "gRPC不可用"},
        500: {"description": "停止失败"},
    },
)
async def stop_grpc_server() -> Dict[str, Any]:
    """Stop gRPC server"""
    if not GRPC_AVAILABLE or not _grpc_server:
        raise HTTPException(status_code=503, detail="gRPC not available")

    try:
        await _grpc_server.stop()
        return {"status": "stopped", "message": "gRPC server stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop gRPC server: {str(e)}")
