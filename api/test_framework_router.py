# -*- coding: utf-8 -*-
"""
Test Framework API Router
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/test-framework", tags=["Test Framework"])


@router.get(
    "/status",
    summary="获取测试框架状态",
    responses={
        200: {"description": "框架状态"},
        500: {"description": "获取失败"},
    },
)
async def get_framework_status():
    """Get test framework status"""
    try:
        from core.test_framework_manager import get_test_framework_manager

        manager = get_test_framework_manager()
        status = manager.get_test_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting framework status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/suites",
    summary="获取测试套件列表",
    responses={
        200: {"description": "测试套件列表"},
        500: {"description": "获取失败"},
    },
)
async def get_test_suites():
    """Get list of test suites"""
    try:
        from core.test_framework_manager import get_test_framework_manager

        manager = get_test_framework_manager()

        suites = [
            {
                "suite_id": suite.suite_id,
                "suite_name": suite.suite_name,
                "test_type": suite.test_type.value,
                "test_count": suite.test_count,
                "coverage_target": suite.coverage_target,
            }
            for suite in manager.test_suites.values()
        ]

        return {
            "status": "success",
            "data": {"suites": suites, "count": len(suites)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting test suites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/suite/create",
    summary="创建测试套件",
    responses={
        200: {"description": "创建结果"},
        500: {"description": "创建失败"},
    },
)
async def create_test_suite(
    suite_id: str, suite_name: str, test_type: str, description: str, coverage_target: float = 80.0
):
    """Create a test suite"""
    try:
        from core.test_framework_manager import TestType, get_test_framework_manager

        manager = get_test_framework_manager()

        type_enum = TestType(test_type)
        success = manager.create_test_suite(
            suite_id, suite_name, type_enum, description, coverage_target
        )

        return {
            "status": "success",
            "data": {"suite_id": suite_id, "created": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating test suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/test/generate",
    summary="生成测试文件",
    responses={
        200: {"description": "生成结果"},
        500: {"description": "生成失败"},
    },
)
async def generate_test_file(
    module_name: str, class_name: str, test_name: str, test_type: str, output_path: str
):
    """Generate test file from template"""
    try:
        from core.test_framework_manager import TestType, get_test_framework_manager

        manager = get_test_framework_manager()

        type_enum = TestType(test_type)
        success = manager.generate_test_file(
            module_name, class_name, test_name, type_enum, output_path
        )

        return {
            "status": "success",
            "data": {"output_path": output_path, "generated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating test file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/suite/{suite_id}/run",
    summary="运行测试套件",
    responses={
        200: {"description": "运行结果"},
        500: {"description": "运行失败"},
    },
)
async def run_test_suite(suite_id: str):
    """Run a test suite"""
    try:
        from core.test_framework_manager import get_test_framework_manager

        manager = get_test_framework_manager()

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
