# -*- coding: utf-8 -*-
"""Advanced Test Automation API router for suites, executions, and reports."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/test-automation", tags=["test-automation-advanced"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

# 开发环境占位
FAKE_ADMIN = UserInDB(
    username="dev-admin",
    full_name="Dev Admin",
    email="dev@example.com",
    role="admin",
    disabled=False,
    hashed_password="",
)


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInDB:
    """获取当前用户；无 token 时返回开发占位 admin。"""
    if not token:
        return FAKE_ADMIN
    payload = verify_token(token)
    if not payload:
        return FAKE_ADMIN
    username = payload.get("sub")
    if not username:
        return FAKE_ADMIN
    user = await get_user(username)
    if not user:
        return FAKE_ADMIN
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============ Enums ============
class TestSuiteStatus(str, Enum):
    """测试套件状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============ Suite Models ============
class TestSuite(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    test_type: str
    framework: str
    status: TestSuiteStatus = TestSuiteStatus.ACTIVE
    test_count: int = 0
    last_execution: Optional[datetime] = None
    last_result: Optional[str] = None
    schedule: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class TestSuiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    test_type: str = Field(..., pattern="^(unit|integration|e2e|performance|security)$")
    framework: str = Field(default="pytest", max_length=50)
    schedule: Optional[str] = Field(None, max_length=100)

    model_config = {"extra": "ignore"}


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TestSuiteStatus] = None
    schedule: Optional[str] = Field(None, max_length=100)

    model_config = {"extra": "ignore"}


# ============ Execution Models ============
class TestExecution(BaseModel):
    id: str
    suite_id: str
    suite_name: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    coverage: Optional[float] = None
    triggered_by: str
    trigger_type: str = "manual"
    logs_url: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class TestExecutionCreate(BaseModel):
    suite_id: str
    trigger_type: str = Field(default="manual", pattern="^(manual|scheduled|webhook|ci)$")
    environment: Optional[str] = Field(None, max_length=50)

    model_config = {"extra": "ignore"}


# ============ In-memory data storage ============
_test_suites: Dict[str, TestSuite] = {}
_test_executions: Dict[str, TestExecution] = {}


def _init_test_suites():
    """初始化默认测试套件"""
    if not _test_suites:
        suite1 = TestSuite(
            id=str(uuid.uuid4()),
            name="API Integration Tests",
            description="测试所有API端点的集成测试",
            test_type="integration",
            framework="pytest",
            status=TestSuiteStatus.ACTIVE,
            test_count=25,
            last_execution=datetime.now() - timedelta(hours=2),
            last_result="passed",
            schedule="0 2 * * *",
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=2),
            created_by="admin",
        )
        suite2 = TestSuite(
            id=str(uuid.uuid4()),
            name="Performance Tests",
            description="系统性能和负载测试",
            test_type="performance",
            framework="locust",
            status=TestSuiteStatus.ACTIVE,
            test_count=10,
            last_execution=datetime.now() - timedelta(days=1),
            last_result="passed",
            schedule="0 3 * * 0",
            created_at=datetime.now() - timedelta(days=20),
            updated_at=datetime.now() - timedelta(days=1),
            created_by="admin",
        )
        _test_suites[suite1.id] = suite1
        _test_suites[suite2.id] = suite2


def _init_test_executions():
    """初始化默认执行记录"""
    if not _test_executions:
        for suite_id, suite in _test_suites.items():
            execution = TestExecution(
                id=str(uuid.uuid4()),
                suite_id=suite_id,
                suite_name=suite.name,
                status=ExecutionStatus.COMPLETED,
                started_at=suite.last_execution or datetime.now() - timedelta(hours=2),
                completed_at=suite.last_execution + timedelta(minutes=15) if suite.last_execution else datetime.now(),
                duration=15.0,
                total_tests=suite.test_count,
                passed_tests=suite.test_count - 2,
                failed_tests=2,
                skipped_tests=0,
                coverage=85.5,
                triggered_by="admin",
                trigger_type="scheduled",
                logs_url=f"/logs/{suite_id}",
                artifacts=[f"/artifacts/{suite_id}/report.html"],
            )
            _test_executions[execution.id] = execution


# 初始化数据
_init_test_suites()
_init_test_executions()


# ============ Suite Endpoints ============
@router.get(
    "/suites",
    response_model=List[TestSuite],
    summary="获取测试套件列表",
    responses={
        (200): {"description": "测试套件列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_suites(
    status: Optional[TestSuiteStatus] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestSuite]:
    """获取所有测试套件"""
    suites = list(_test_suites.values())

    if status:
        suites = [s for s in suites if s.status == status]

    suites.sort(key=lambda x: x.updated_at, reverse=True)
    return suites[offset : offset + limit]


@router.post(
    "/suites",
    response_model=TestSuite,
    status_code=status.HTTP_201_CREATED,
    summary="创建测试套件",
    responses={
        (201): {"description": "测试套件创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_test_suite(
    suite_create: TestSuiteCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestSuite:
    """创建新的测试套件"""
    suite_id = str(uuid.uuid4())
    now = datetime.now()

    suite = TestSuite(
        id=suite_id,
        name=suite_create.name,
        description=suite_create.description,
        test_type=suite_create.test_type,
        framework=suite_create.framework,
        status=TestSuiteStatus.ACTIVE,
        test_count=0,
        schedule=suite_create.schedule,
        created_at=now,
        updated_at=now,
        created_by=current_user.username,
    )

    _test_suites[suite_id] = suite

    logger.info(
        f"Test suite created | suite_id={suite_id} | name={suite_create.name} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return suite


@router.get(
    "/suites/{id}",
    response_model=TestSuite,
    summary="获取测试套件详情",
    responses={
        (200): {"description": "测试套件详情"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def get_test_suite(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestSuite:
    """获取指定测试套件的详情"""
    if id not in _test_suites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")
    return _test_suites[id]


@router.patch(
    "/suites/{id}",
    response_model=TestSuite,
    summary="更新测试套件",
    responses={
        (200): {"description": "测试套件更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def update_test_suite(
    id: str,
    suite_update: TestSuiteUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestSuite:
    """更新指定测试套件"""
    if id not in _test_suites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    suite = _test_suites[id]
    update_data = suite_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(suite, key):
            setattr(suite, key, value)

    suite.updated_at = datetime.now()
    _test_suites[id] = suite

    logger.info(
        f"Test suite updated | suite_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return suite


@router.delete(
    "/suites/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除测试套件",
    responses={
        (204): {"description": "测试套件删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def delete_test_suite(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定测试套件"""
    if id not in _test_suites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    del _test_suites[id]

    # 同时删除相关的执行记录
    _test_executions = {
        k: v for k, v in _test_executions.items() if v.suite_id != id
    }

    logger.info(
        f"Test suite deleted | suite_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )


# ============ Execution Endpoints ============
@router.get(
    "/executions",
    response_model=List[TestExecution],
    summary="获取执行记录列表",
    responses={
        (200): {"description": "执行记录列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_executions(
    suite_id: Optional[str] = None,
    status: Optional[ExecutionStatus] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestExecution]:
    """获取测试执行记录"""
    executions = list(_test_executions.values())

    if suite_id:
        executions = [e for e in executions if e.suite_id == suite_id]

    if status:
        executions = [e for e in executions if e.status == status]

    executions.sort(key=lambda x: x.started_at, reverse=True)
    return executions[offset : offset + limit]


@router.post(
    "/executions",
    response_model=TestExecution,
    status_code=status.HTTP_201_CREATED,
    summary="创建执行记录",
    responses={
        (201): {"description": "执行记录创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def create_test_execution(
    execution_create: TestExecutionCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestExecution:
    """创建新的测试执行"""
    if execution_create.suite_id not in _test_suites:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    suite = _test_suites[execution_create.suite_id]
    execution_id = str(uuid.uuid4())
    now = datetime.now()

    execution = TestExecution(
        id=execution_id,
        suite_id=execution_create.suite_id,
        suite_name=suite.name,
        status=ExecutionStatus.PENDING,
        started_at=now,
        total_tests=suite.test_count,
        triggered_by=current_user.username,
        trigger_type=execution_create.trigger_type,
    )

    _test_executions[execution_id] = execution

    # 更新套件的最后执行时间
    suite.last_execution = now
    suite.updated_at = now
    _test_suites[execution_create.suite_id] = suite

    logger.info(
        f"Test execution created | execution_id={execution_id} | suite_id={execution_create.suite_id} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return execution


@router.get(
    "/executions/{id}",
    response_model=TestExecution,
    summary="获取执行记录详情",
    responses={
        (200): {"description": "执行记录详情"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def get_test_execution(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestExecution:
    """获取指定执行记录的详情"""
    if id not in _test_executions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return _test_executions[id]


@router.post(
    "/executions/{id}/cancel",
    response_model=TestExecution,
    summary="取消执行",
    responses={
        (200): {"description": "执行取消成功"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def cancel_test_execution(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestExecution:
    """取消指定的测试执行"""
    if id not in _test_executions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    execution = _test_executions[id]
    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel execution that is not pending or running",
        )

    execution.status = ExecutionStatus.CANCELLED
    execution.completed_at = datetime.now()
    _test_executions[id] = execution

    logger.info(
        f"Test execution cancelled | execution_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return execution
