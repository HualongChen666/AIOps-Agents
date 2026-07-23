# -*- coding: utf-8 -*-
"""
Test Coverage API Router
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/test-coverage", tags=["Test Coverage"])


@router.get(
    "/status",
    summary="获取测试覆盖率状态",
    responses={
        200: {"description": "覆盖率状态"},
        500: {"description": "获取失败"},
    },
)
async def get_coverage_status():
    """Get test coverage status"""
    try:
        from core.test_coverage_manager import get_coverage_manager

        manager = get_coverage_manager()
        status = manager.get_coverage_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting coverage status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/module/add",
    summary="添加模块覆盖率数据",
    responses={
        200: {"description": "添加结果"},
        500: {"description": "添加失败"},
    },
)
async def add_module_coverage(
    module_id: str, module_name: str, total_lines: int, covered_lines: int
):
    """Add module coverage data"""
    try:
        from core.test_coverage_manager import get_coverage_manager

        manager = get_coverage_manager()

        success = manager.add_module_coverage(module_id, module_name, total_lines, covered_lines)

        return {
            "status": "success",
            "data": {"module_id": module_id, "added": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error adding module coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/module/{module_id}",
    summary="获取模块覆盖率数据",
    responses={
        200: {"description": "模块覆盖率数据"},
        404: {"description": "模块覆盖率未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_module_coverage(module_id: str, module_type: str = "core"):
    """Get module coverage data"""
    try:
        from core.test_coverage_manager import get_coverage_manager

        manager = get_coverage_manager()

        coverage = manager.get_module_coverage(module_id)
        threshold_check = manager.check_coverage_threshold(module_id, module_type)

        if not coverage:
            raise HTTPException(status_code=404, detail="Module coverage not found")

        return {
            "status": "success",
            "data": {
                "module_id": module_id,
                "module_name": coverage.module_name,
                "coverage_percentage": coverage.coverage_percentage,
                "coverage_level": coverage.coverage_level.value,
                "threshold_check": threshold_check,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting module coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/report",
    summary="获取覆盖率报告",
    responses={
        200: {"description": "覆盖率报告"},
        500: {"description": "获取失败"},
    },
)
async def get_coverage_report():
    """Get detailed coverage report"""
    try:
        from core.test_coverage_manager import get_coverage_manager

        manager = get_coverage_manager()

        report = manager.get_coverage_report()

        return {"status": "success", "data": report, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting coverage report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
