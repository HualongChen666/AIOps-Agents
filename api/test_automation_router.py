# -*- coding: utf-8 -*-
"""
Test Automation API Router
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

router = APIRouter(prefix="/api/test-automation", tags=["Test Automation"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/status",
    summary="获取测试自动化状态",
    responses={
        200: {"description": "自动化状态"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "获取失败"},
    },
)
@limiter.limit("100/minute")
async def get_automation_status(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get test automation status"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)
        status = manager.get_automation_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/job/create",
    summary="创建自动化任务",
    responses={
        200: {"description": "创建结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "创建失败"},
    },
)
@limiter.limit("50/minute")
async def create_automation_job(
    request: Request,
    job_id: str,
    job_name: str,
    job_type: str,
    trigger_type: str = "manual",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create an automation job"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)

        success = manager.create_automation_job(
            job_id, job_name, job_type, trigger_type, created_by=current_user.username
        )

        return {
            "status": "success",
            "data": {"job_id": job_id, "created": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating automation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/job/{job_id}/run",
    summary="运行自动化任务",
    responses={
        200: {"description": "运行结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "运行失败"},
    },
)
@limiter.limit("30/minute")
async def run_automation_job(
    request: Request,
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Run an automation job"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)

        success = manager.run_automation_job(job_id)

        return {
            "status": "success",
            "data": {"job_id": job_id, "started": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running automation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cicd/generate",
    summary="生成CI/CD流水线配置",
    responses={
        200: {"description": "生成结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "生成失败"},
    },
)
@limiter.limit("20/minute")
async def generate_cicd_pipeline(
    request: Request,
    output_path: str,
    platform: str = "github_actions",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate CI/CD pipeline configuration"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)

        success = manager.generate_ci_cd_pipeline(output_path, platform, created_by=current_user.username)

        return {
            "status": "success",
            "data": {"output_path": output_path, "platform": platform, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating CI/CD pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/report/generate",
    summary="生成测试报告",
    responses={
        200: {"description": "生成结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "生成失败"},
    },
)
@limiter.limit("20/minute")
async def generate_test_report(
    request: Request,
    report_type: str = "html",
    output_path: str = "test_report.html",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Generate test report"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: read permission for testing
        if current_user.role not in ["admin", "operator", "user"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin、operator或user角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)

        success = manager.generate_test_report(report_type, output_path)

        return {
            "status": "success",
            "data": {"output_path": output_path, "report_type": report_type, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notification/send",
    summary="发送通知",
    responses={
        200: {"description": "发送结果"},
        401: {"description": "未授权"},
        403: {"description": "权限不足"},
        429: {"description": "请求过于频繁"},
        500: {"description": "发送失败"},
    },
)
@limiter.limit("30/minute")
async def send_notification(
    request: Request,
    job_id: str,
    status: str,
    message: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send notification"""
    try:
        from core.test_automation_manager import get_automation_manager
        from core.test_repository import TestRepository

        # RBAC check: write permission for testing
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="权限不足: 需要admin或operator角色")

        repository = TestRepository(db)
        manager = get_automation_manager()
        manager.set_repository(repository)

        success = manager.send_notification(job_id, status, message)

        return {
            "status": "success",
            "data": {"job_id": job_id, "sent": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
