# -*- coding: utf-8 -*-
"""
Test Coverage API Router
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.middleware.rbac_auth_middleware import require_permission, require_roles
from api.middleware.auth_middleware import get_current_active_user
from core.models import User
from core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/test-coverage", tags=["Test Coverage"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/status",
    summary="获取测试覆盖率状态",
    responses={
        200: {"description": "覆盖率状态"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_coverage_status(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get test coverage status"""
    try:
        from core.test_coverage_manager import get_coverage_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_coverage_manager()
        manager.set_repository(repository)
        status = manager.get_coverage_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting coverage status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/module/add",
    summary="添加模块覆盖率数据",
    responses={
        200: {"description": "添加结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "添加失败"},
    },
)
@limiter.limit("50/minute")
async def add_module_coverage(
    request: Request,
    module_id: str,
    module_name: str,
    total_lines: int,
    covered_lines: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add module coverage data"""
    try:
        from core.test_coverage_manager import get_coverage_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_coverage_manager()
        manager.set_repository(repository)

        success = manager.add_module_coverage(module_id, module_name, total_lines, covered_lines)

        return {
            "status": "success",
            "data": {"module_id": module_id, "added": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding module coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/module/{module_id}",
    summary="获取模块覆盖率数据",
    responses={
        200: {"description": "模块覆盖率数据"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "模块覆盖率未找到"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_module_coverage(
    request: Request,
    module_id: str,
    module_type: str = "core",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get module coverage data"""
    try:
        from core.test_coverage_manager import get_coverage_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_coverage_manager()
        manager.set_repository(repository)

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
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("50/minute")
async def get_coverage_report(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed coverage report"""
    try:
        from core.test_coverage_manager import get_coverage_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_coverage_manager()
        manager.set_repository(repository)

        report = manager.get_coverage_report()

        return {"status": "success", "data": report, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting coverage report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
