# -*- coding: utf-8 -*-
"""
Test Automation API Router
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/test-automation", tags=["Test Automation"])


@router.get(
    "/status",
    summary="获取测试自动化状态",
    responses={
        200: {"description": "自动化状态"},
        500: {"description": "获取失败"},
    },
)
async def get_automation_status():
    """Get test automation status"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()
        status = manager.get_automation_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/job/create",
    summary="创建自动化任务",
    responses={
        200: {"description": "创建结果"},
        500: {"description": "创建失败"},
    },
)
async def create_automation_job(
    job_id: str, job_name: str, job_type: str, trigger_type: str = "manual"
):
    """Create an automation job"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()

        success = manager.create_automation_job(job_id, job_name, job_type, trigger_type)

        return {
            "status": "success",
            "data": {"job_id": job_id, "created": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating automation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/job/{job_id}/run",
    summary="运行自动化任务",
    responses={
        200: {"description": "运行结果"},
        500: {"description": "运行失败"},
    },
)
async def run_automation_job(job_id: str):
    """Run an automation job"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()

        success = manager.run_automation_job(job_id)

        return {
            "status": "success",
            "data": {"job_id": job_id, "started": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error running automation job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cicd/generate",
    summary="生成CI/CD流水线配置",
    responses={
        200: {"description": "生成结果"},
        500: {"description": "生成失败"},
    },
)
async def generate_cicd_pipeline(output_path: str, platform: str = "github_actions"):
    """Generate CI/CD pipeline configuration"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()

        success = manager.generate_ci_cd_pipeline(output_path, platform)

        return {
            "status": "success",
            "data": {"output_path": output_path, "platform": platform, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating CI/CD pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/report/generate",
    summary="生成测试报告",
    responses={
        200: {"description": "生成结果"},
        500: {"description": "生成失败"},
    },
)
async def generate_test_report(report_type: str = "html", output_path: str = "test_report.html"):
    """Generate test report"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()

        success = manager.generate_test_report(report_type, output_path)

        return {
            "status": "success",
            "data": {"output_path": output_path, "report_type": report_type, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating test report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/notification/send",
    summary="发送通知",
    responses={
        200: {"description": "发送结果"},
        500: {"description": "发送失败"},
    },
)
async def send_notification(job_id: str, status: str, message: str):
    """Send notification (simulated)"""
    try:
        from core.test_automation_manager import get_automation_manager

        manager = get_automation_manager()

        success = manager.send_notification(job_id, status, message)

        return {
            "status": "success",
            "data": {"job_id": job_id, "sent": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
