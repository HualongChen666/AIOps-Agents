# -*- coding: utf-8 -*-
"""
Test Framework API Router
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

router = APIRouter(prefix="/api/test-framework", tags=["Test Framework"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/status",
    summary="获取测试框架状态",
    responses={
        200: {"description": "框架状态"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_framework_status(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get test framework status"""
    try:
        from core.test_framework_manager import get_test_framework_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_test_framework_manager()
        manager.set_repository(repository)
        status = manager.get_test_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting framework status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/suites",
    summary="获取测试套件列表",
    responses={
        200: {"description": "测试套件列表"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_test_suites(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get list of test suites"""
    try:
        from core.test_framework_manager import get_test_framework_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_test_framework_manager()
        manager.set_repository(repository)

        suites = repository.get_all_test_suites()

        suites_data = [
            {
                "suite_id": suite.suite_id,
                "suite_name": suite.suite_name,
                "test_type": suite.test_type,
                "test_count": suite.test_count,
                "coverage_target": suite.coverage_target,
            }
            for suite in suites
        ]

        return {
            "status": "success",
            "data": {"suites": suites_data, "count": len(suites)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test suites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/suite/create",
    summary="创建测试套件",
    responses={
        200: {"description": "创建结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "创建失败"},
    },
)
@limiter.limit("50/minute")
async def create_test_suite(
    request: Request,
    suite_id: str,
    suite_name: str,
    test_type: str,
    description: str,
    coverage_target: float = 80.0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a test suite"""
    try:
        from core.test_framework_manager import TestType, get_test_framework_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_test_framework_manager()
        manager.set_repository(repository)

        success = manager.create_test_suite(
            suite_id, suite_name, test_type, description, coverage_target, created_by=current_user.username
        )

        return {
            "status": "success",
            "data": {"suite_id": suite_id, "created": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/test/generate",
    summary="生成测试文件",
    responses={
        200: {"description": "生成结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "生成失败"},
    },
)
@limiter.limit("30/minute")
async def generate_test_file(
    request: Request,
    module_name: str,
    class_name: str,
    test_name: str,
    test_type: str,
    output_path: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate test file from template"""
    try:
        from core.test_framework_manager import TestType, get_test_framework_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_test_framework_manager()
        manager.set_repository(repository)

        success = manager.generate_test_file(
            module_name, class_name, test_name, test_type, output_path
        )

        return {
            "status": "success",
            "data": {"output_path": output_path, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating test file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/suite/{suite_id}/run",
    summary="运行测试套件",
    responses={
        200: {"description": "运行结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        404: {"description": "测试套件未找到"},
        429: {"description": "请求过于频繁"},
        500: {"description": "运行失败"},
    },
)
@limiter.limit("30/minute")
async def run_test_suite(
    request: Request,
    suite_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run a test suite"""
    try:
        from core.test_framework_manager import get_test_framework_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_test_framework_manager()
        manager.set_repository(repository)

        report = manager.run_test_suite(suite_id)

        if not report:
            raise HTTPException(status_code=404, detail="Test suite not found")

        return {
            "status": "success",
            "data": {
                "suite_id": suite_id,
                "report_id": report.report_id,
                "total_tests": report.total_tests,
                "passed_tests": report.passed_tests,
                "failed_tests": report.failed_tests,
                "coverage": report.coverage,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running test suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))
