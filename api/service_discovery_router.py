# -*- coding: utf-8 -*-
"""
Service Discovery API Router
Provides API endpoints for service discovery and monitoring
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/service-discovery", tags=["Service Discovery"])


@router.get(
    "/status",
    summary="获取服务发现状态",
    responses={
        200: {"description": "服务发现状态"},
        500: {"description": "获取失败"},
    },
)
async def get_discovery_status():
    """
    Get service discovery status

    Returns:
        Service discovery status
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        status = manager.get_service_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting discovery status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/register",
    summary="注册服务实例",
    responses={
        200: {"description": "注册结果"},
        500: {"description": "注册失败"},
    },
)
async def register_service(
    service_name: str, instance_id: str, host: str, port: int, weight: int = 1
):
    """
    Register service instance

    Args:
        service_name: Service name
        instance_id: Instance ID
        host: Host address
        port: Port number
        weight: Instance weight for load balancing

    Returns:
        Registered service instance
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        instance = manager.register_service(
            service_name=service_name, instance_id=instance_id, host=host, port=port, weight=weight
        )

        return {
            "status": "success",
            "data": {
                "instance_id": instance.instance_id,
                "service_name": instance.service_name,
                "host": instance.host,
                "port": instance.port,
                "status": instance.status.value,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error registering service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/deregister",
    summary="注销服务实例",
    responses={
        200: {"description": "注销结果"},
        500: {"description": "注销失败"},
    },
)
async def deregister_service(service_name: str, instance_id: str):
    """
    Deregister service instance

    Args:
        service_name: Service name
        instance_id: Instance ID

    Returns:
        Deregistration result
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        success = manager.deregister_service(service_name, instance_id)

        return {
            "status": "success",
            "data": {"success": success, "service_name": service_name, "instance_id": instance_id},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error deregistering service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/discover/{service_name}",
    summary="发现服务实例",
    responses={
        200: {"description": "服务实例列表"},
        500: {"description": "发现失败"},
    },
)
async def discover_service(service_name: str):
    """
    Discover service instances

    Args:
        service_name: Service name

    Returns:
        Service instances
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        instances = manager.discover_service(service_name)

        return {
            "status": "success",
            "data": {
                "service_name": service_name,
                "instances": [
                    {
                        "instance_id": inst.instance_id,
                        "host": inst.host,
                        "port": inst.port,
                        "status": inst.status.value,
                        "weight": inst.weight,
                    }
                    for inst in instances
                ],
                "count": len(instances),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error discovering service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/get-instance/{service_name}",
    summary="获取服务实例",
    responses={
        200: {"description": "服务实例"},
        404: {"description": "无可用实例"},
        500: {"description": "获取失败"},
    },
)
async def get_service_instance(service_name: str, strategy: str = "round_robin"):
    """
    Get service instance using load balancing

    Args:
        service_name: Service name
        strategy: Load balance strategy

    Returns:
        Selected service instance
    """
    try:
        from core.service_discovery_manager import (
            LoadBalanceStrategy,
            get_service_discovery_manager,
        )

        manager = get_service_discovery_manager()

        strategy_enum = LoadBalanceStrategy(strategy)
        instance = manager.get_service_instance(service_name, strategy_enum)

        if not instance:
            raise HTTPException(status_code=404, detail="No healthy instances available")

        return {
            "status": "success",
            "data": {
                "instance_id": instance.instance_id,
                "service_name": instance.service_name,
                "host": instance.host,
                "port": instance.port,
                "status": instance.status.value,
                "strategy": strategy,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting service instance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/details/{service_name}",
    summary="获取服务详情",
    responses={
        200: {"description": "服务详情"},
        500: {"description": "获取失败"},
    },
)
async def get_service_details(service_name: str):
    """
    Get service details

    Args:
        service_name: Service name

    Returns:
        Service details
    """
    try:
        from core.service_discovery_manager import get_service_discovery_manager

        manager = get_service_discovery_manager()
        details = manager.get_service_details(service_name)

        return {"status": "success", "data": details, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting service details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
