# -*- coding: utf-8 -*-
"""Advanced Test Automation API router for suites, executions, and reports."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token
from core.database import get_db
from core.models import TestSuiteDB, TestExecutionDB
from sqlalchemy.orm import Session

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


# ============ Database Helper Functions ============
def _db_to_suite(suite_db: TestSuiteDB) -> TestSuite:
    """Convert database model to API model"""
    return TestSuite(
        id=suite_db.id,
        name=suite_db.name,
        description=suite_db.description,
        test_type=suite_db.test_type,
        framework=suite_db.framework,
        status=TestSuiteStatus(suite_db.status),
        test_count=0,  # Will be calculated from executions
        last_execution=None,  # Will be fetched from executions
        last_result=None,
        schedule=suite_db.schedule,
        created_at=suite_db.created_at or datetime.now(),
        updated_at=suite_db.updated_at or datetime.now(),
        created_by=suite_db.created_by or "system",
    )


def _db_to_execution(exec_db: TestExecutionDB) -> TestExecution:
    """Convert database model to API model"""
    duration = None
    if exec_db.started_at and exec_db.completed_at:
        duration = (exec_db.completed_at - exec_db.started_at).total_seconds()
    
    return TestExecution(
        id=exec_db.id,
        suite_id=exec_db.suite_id,
        suite_name=exec_db.suite_name,
        status=ExecutionStatus(exec_db.status),
        started_at=exec_db.started_at or datetime.now(),
        completed_at=exec_db.completed_at,
        duration=duration,
        total_tests=exec_db.total_tests,
        passed_tests=exec_db.passed_tests,
        failed_tests=exec_db.failed_tests,
        skipped_tests=exec_db.skipped_tests,
        coverage=None,
        triggered_by=exec_db.triggered_by or "system",
        trigger_type=exec_db.trigger_type,
        logs_url=None,
        artifacts=[],
    )


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
    db: Session = Depends(get_db),
) -> List[TestSuite]:
    """获取所有测试套件"""
    query = db.query(TestSuiteDB)
    
    if status:
        query = query.filter(TestSuiteDB.status == status.value)
    
    suites_db = query.order_by(TestSuiteDB.updated_at.desc()).offset(offset).limit(limit).all()
    
    return [_db_to_suite(suite) for suite in suites_db]


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
    db: Session = Depends(get_db),
) -> TestSuite:
    """创建新的测试套件"""
    suite_id = str(uuid.uuid4())
    now = datetime.now()

    suite_db = TestSuiteDB(
        id=suite_id,
        name=suite_create.name,
        description=suite_create.description,
        test_type=suite_create.test_type,
        framework=suite_create.framework,
        status=TestSuiteStatus.ACTIVE.value,
        schedule=suite_create.schedule,
        created_by=current_user.username,
        created_at=now,
        updated_at=now,
    )
    
    db.add(suite_db)
    db.commit()
    db.refresh(suite_db)

    logger.info(
        f"Test suite created | suite_id={suite_id} | name={suite_create.name} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_suite(suite_db)


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
    db: Session = Depends(get_db),
) -> TestSuite:
    """获取指定测试套件的详情"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()
    
    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")
    
    return _db_to_suite(suite_db)


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
    db: Session = Depends(get_db),
) -> TestSuite:
    """更新指定测试套件"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()
    
    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    update_data = suite_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(suite_db, key):
            setattr(suite_db, key, value)
    
    suite_db.updated_at = datetime.now()
    db.commit()
    db.refresh(suite_db)

    logger.info(
        f"Test suite updated | suite_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _db_to_suite(suite_db)


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
    db: Session = Depends(get_db),
) -> None:
    """删除指定测试套件"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()
    
    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    # 删除相关的执行记录
    db.query(TestExecutionDB).filter(TestExecutionDB.suite_id == id).delete()
    
    # 删除套件
    db.delete(suite_db)
    db.commit()

    logger.info(
        f"Test suite deleted | suite_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
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
    db: Session = Depends(get_db),
) -> List[TestExecution]:
    """获取测试执行记录"""
    query = db.query(TestExecutionDB)
    
    if suite_id:
        query = query.filter(TestExecutionDB.suite_id == suite_id)
    
    if status:
        query = query.filter(TestExecutionDB.status == status.value)
    
    executions_db = query.order_by(TestExecutionDB.started_at.desc()).offset(offset).limit(limit).all()
    
    return [_db_to_execution(execution) for execution in executions_db]


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
    db: Session = Depends(get_db),
) -> TestExecution:
    """创建新的测试执行"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == execution_create.suite_id).first()
    
    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    execution_id = str(uuid.uuid4())
    now = datetime.now()

    execution_db = TestExecutionDB(
        id=execution_id,
        suite_id=execution_create.suite_id,
        suite_name=suite_db.name,
        status=ExecutionStatus.PENDING.value,
        started_at=now,
        total_tests=0,
        triggered_by=current_user.username,
        trigger_type=execution_create.trigger_type,
    )
    
    db.add(execution_db)
    db.commit()
    db.refresh(execution_db)

    # 更新套件的最后执行时间
    suite_db.updated_at = now
    db.commit()

    logger.info(
        f"Test execution created | execution_id={execution_id} "
        f"| suite_id={execution_create.suite_id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _db_to_execution(execution_db)


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
    db: Session = Depends(get_db),
) -> TestExecution:
    """获取指定执行记录的详情"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()
    
    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    
    return _db_to_execution(execution_db)


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
    db: Session = Depends(get_db),
) -> TestExecution:
    """取消指定的测试执行"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()
    
    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution_db.status not in [ExecutionStatus.PENDING.value, ExecutionStatus.RUNNING.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel execution that is not pending or running",
        )

    execution_db.status = ExecutionStatus.CANCELLED.value
    execution_db.completed_at = datetime.now()
    db.commit()
    db.refresh(execution_db)

    logger.info(
        f"Test execution cancelled | execution_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _db_to_execution(execution_db)
