# -*- coding: utf-8 -*-
"""
gRPC Service API Router
Provides API endpoints for gRPC service management
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/grpc-services", tags=["gRPC Services"])


@router.get(
    "/status",
    summary="获取gRPC服务状态",
    responses={
        200: {
            "description": "gRPC服务状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_services": 5, "active_services": 4},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_grpc_status():
    """
    Get gRPC service status

    Returns:
        gRPC service status
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()
        status = manager.get_service_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting gRPC status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/create",
    summary="创建gRPC服务",
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "service_name": "UserService",
                            "package_name": "user",
                            "status": "active",
                            "method_count": 3,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "创建失败"},
    },
)
async def create_grpc_service(service_name: str, package_name: str, methods: Dict[str, Any]):
    """
    Create gRPC service

    Args:
        service_name: Service name
        package_name: Package name
        methods: Service methods

    Returns:
        Created gRPC service
    """
    try:
        from core.grpc_service_manager import GRPCMethod, get_grpc_service_manager

        manager = get_grpc_service_manager()

        # Convert methods dict to GRPCMethod objects
        grpc_methods = [
            GRPCMethod(
                method_name=method_data.get("method_name"),
                request_type=method_data.get("request_type"),
                response_type=method_data.get("response_type"),
                streaming_type=method_data.get("streaming_type", "unary"),
                description=method_data.get("description", ""),
            )
            for method_data in methods.get("methods", [])
        ]

        service = manager.create_service(
            service_name=service_name,
            package_name=package_name,
            methods=grpc_methods,
            messages=methods.get("messages"),
        )

        return {
            "status": "success",
            "data": {
                "service_name": service.service_name,
                "package_name": service.package_name,
                "status": service.status.value,
                "method_count": len(grpc_methods),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating gRPC service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/create/monitoring",
    summary="创建监控服务",
    responses={
        200: {"description": "创建成功"},
        500: {"description": "创建失败"},
    },
)
async def create_monitoring_service():
    """
    Create monitoring service

    Returns:
        Created monitoring service
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()
        service = manager.create_monitoring_service()

        return {
            "status": "success",
            "data": {
                "service_name": service.service_name,
                "package_name": service.package_name,
                "status": service.status.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating monitoring service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/create/alert",
    summary="创建告警服务",
    responses={
        200: {"description": "创建成功"},
        500: {"description": "创建失败"},
    },
)
async def create_alert_service():
    """
    Create alert service

    Returns:
        Created alert service
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()
        service = manager.create_alert_service()

        return {
            "status": "success",
            "data": {
                "service_name": service.service_name,
                "package_name": service.package_name,
                "status": service.status.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating alert service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/create/repair",
    summary="创建修复服务",
    responses={
        200: {"description": "创建成功"},
        500: {"description": "创建失败"},
    },
)
async def create_repair_service():
    """
    Create repair service

    Returns:
        Created repair service
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()
        service = manager.create_repair_service()

        return {
            "status": "success",
            "data": {
                "service_name": service.service_name,
                "package_name": service.package_name,
                "status": service.status.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating repair service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/export/proto/{service_name}",
    summary="导出proto文件",
    responses={
        200: {"description": "proto文件内容"},
        404: {"description": "服务未找到"},
        500: {"description": "导出失败"},
    },
)
async def export_proto_file(service_name: str):
    """
    Export proto file for service

    Args:
        service_name: Service name

    Returns:
        Proto file content
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()

        if service_name not in manager.services:
            raise HTTPException(status_code=404, detail="Service not found")

        service = manager.services[service_name]

        return {
            "status": "success",
            "data": {"service_name": service_name, "proto_content": service.proto_content},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting proto file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/export/python/{service_name}",
    summary="导出Python实现文件",
    responses={
        200: {"description": "Python文件内容"},
        404: {"description": "服务未找到"},
        500: {"description": "导出失败"},
    },
)
async def export_python_file(service_name: str):
    """
    Export Python implementation file for service

    Args:
        service_name: Service name

    Returns:
        Python file content
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()

        if service_name not in manager.services:
            raise HTTPException(status_code=404, detail="Service not found")

        service = manager.services[service_name]

        return {
            "status": "success",
            "data": {"service_name": service_name, "python_content": service.python_content},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Python file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/list",
    summary="列出所有gRPC服务",
    responses={
        200: {"description": "服务列表"},
        500: {"description": "获取失败"},
    },
)
async def list_grpc_services():
    """
    List all gRPC services

    Returns:
        List of gRPC services
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()
        summary = manager.get_service_summary()

        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing gRPC services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{service_name}",
    summary="获取单个gRPC服务详情",
    responses={
        200: {"description": "服务详情"},
        404: {"description": "服务未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_grpc_service(service_name: str):
    """
    Get gRPC service details

    Args:
        service_name: Service name

    Returns:
        Service details
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()

        if service_name not in manager.services:
            raise HTTPException(status_code=404, detail="Service not found")

        service = manager.services[service_name]
        methods = manager.methods.get(service_name, [])

        return {
            "status": "success",
            "data": {
                "service_name": service.service_name,
                "package_name": service.package_name,
                "status": service.status.value,
                "method_count": len(methods),
                "methods": [
                    {
                        "method_name": method.method_name,
                        "request_type": method.request_type,
                        "response_type": method.response_type,
                        "streaming_type": method.streaming_type,
                        "description": method.description,
                    }
                    for method in methods
                ],
                "metadata": service.metadata,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gRPC service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{service_name}",
    summary="删除gRPC服务",
    responses={
        200: {"description": "删除成功"},
        404: {"description": "服务未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_grpc_service(service_name: str):
    """
    Delete gRPC service

    Args:
        service_name: Service name

    Returns:
        Deletion result
    """
    try:
        from core.grpc_service_manager import get_grpc_service_manager

        manager = get_grpc_service_manager()

        if service_name not in manager.services:
            raise HTTPException(status_code=404, detail="Service not found")

        del manager.services[service_name]
        if service_name in manager.methods:
            del manager.methods[service_name]
        manager.total_services_defined -= 1

        logger.info(f"Deleted gRPC service: {service_name}")

        return {
            "status": "success",
            "data": {"service_name": service_name, "message": "Service deleted successfully"},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting gRPC service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{service_name}/status",
    summary="更新gRPC服务状态",
    responses={
        200: {"description": "更新成功"},
        404: {"description": "服务未找到"},
        400: {"description": "无效状态"},
        500: {"description": "更新失败"},
    },
)
async def update_service_status(service_name: str, status: str):
    """
    Update gRPC service status

    Args:
        service_name: Service name
        status: New status (defined, implemented, deployed, error)

    Returns:
        Updated service
    """
    try:
        from core.grpc_service_manager import ServiceStatus, get_grpc_service_manager

        manager = get_grpc_service_manager()

        if service_name not in manager.services:
            raise HTTPException(status_code=404, detail="Service not found")

        valid_statuses = [s.value for s in ServiceStatus]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}"
            )

        service = manager.services[service_name]
        service.status = ServiceStatus(status)

        logger.info(f"Updated gRPC service status: {service_name} -> {status}")

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "status": service.status.value,
                "message": "Service status updated successfully",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating service status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
