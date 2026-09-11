# -*- coding: utf-8 -*-
"""Advanced Test Automation API router for suites, executions, and reports."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token
from core.database import get_db
from core.models import TestSuiteDB, TestExecutionDB
from core.persistent_store import PersistentStore
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/test-automation", tags=["test-automation-advanced"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserInDB:
    """获取当前用户；token 缺失/无效/用户不存在时返回 401（AGENTS.md §5：禁止占位放行）。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = verify_token(token)
    if not payload:
        raise credentials_exception
    username = payload.get("sub")
    if not username:
        raise credentials_exception
    user = await get_user(username)
    if not user:
        raise credentials_exception
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
    environment: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None

    model_config = {"extra": "ignore"}


class TestExecutionCreate(BaseModel):
    suite_id: str
    trigger_type: str = Field(default="manual", pattern="^(manual|scheduled|webhook|ci)$")
    environment: Optional[str] = Field(None, max_length=50)
    parallel: bool = False
    timeout_seconds: Optional[int] = Field(None, ge=1, le=3600)

    model_config = {"extra": "ignore"}


class TestExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    total_tests: Optional[int] = Field(None, ge=0)
    passed_tests: Optional[int] = Field(None, ge=0)
    failed_tests: Optional[int] = Field(None, ge=0)
    skipped_tests: Optional[int] = Field(None, ge=0)
    coverage: Optional[float] = Field(None, ge=0, le=100)
    error_message: Optional[str] = None

    model_config = {"extra": "ignore"}


class TestReport(BaseModel):
    id: str
    execution_id: str
    suite_id: str
    suite_name: str
    report_type: str
    format: str
    generated_at: datetime
    generated_by: str
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str = "completed"

    model_config = {"extra": "ignore"}


class TestReportCreate(BaseModel):
    execution_id: str
    report_type: str = Field(..., pattern="^(summary|detailed|coverage|performance)$")
    format: str = Field(default="html", pattern="^(html|pdf|json|xml)$")

    model_config = {"extra": "ignore"}


class TestEnvironment(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    environment_type: str
    config: Dict
    status: str = "active"
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class TestEnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    environment_type: str = Field(..., pattern="^(dev|staging|prod|custom)$")
    config: Dict

    model_config = {"extra": "ignore"}


class TestEnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[Dict] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")

    model_config = {"extra": "ignore"}


class TestSchedule(BaseModel):
    id: str
    suite_id: str
    suite_name: str
    schedule_type: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class TestScheduleCreate(BaseModel):
    suite_id: str
    schedule_type: str = Field(..., pattern="^(cron|interval)$")
    cron_expression: Optional[str] = Field(None, max_length=100)
    interval_seconds: Optional[int] = Field(None, ge=60)
    enabled: bool = True

    model_config = {"extra": "ignore"}


class TestScheduleUpdate(BaseModel):
    schedule_type: Optional[str] = Field(None, pattern="^(cron|interval)$")
    cron_expression: Optional[str] = Field(None, max_length=100)
    interval_seconds: Optional[int] = Field(None, ge=60)
    enabled: Optional[bool] = None

    model_config = {"extra": "ignore"}


class TestMetric(BaseModel):
    id: str
    execution_id: str
    metric_name: str
    metric_value: float
    unit: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict] = None

    model_config = {"extra": "ignore"}


class TestMetricCreate(BaseModel):
    execution_id: str
    metric_name: str = Field(..., max_length=100)
    metric_value: float
    unit: Optional[str] = Field(None, max_length=20)
    metadata: Optional[Dict] = None

    model_config = {"extra": "ignore"}


# ============ Durable stores ============
# Reports, environments, schedules and metrics are persisted through the shared
# durable store rather than being regenerated as fabricated rows on every call.
_reports: PersistentStore = PersistentStore(
    "test_automation", "reports", decoder=TestReport.model_validate
)
_environments: PersistentStore = PersistentStore(
    "test_automation", "environments", decoder=TestEnvironment.model_validate
)
_schedules: PersistentStore = PersistentStore(
    "test_automation", "schedules", decoder=TestSchedule.model_validate
)
_metrics: PersistentStore = PersistentStore(
    "test_automation", "metrics", decoder=TestMetric.model_validate
)


def _apply_update(model_obj: Any, update: BaseModel) -> None:
    """Apply the provided (non-None) fields of ``update`` onto ``model_obj``."""
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None and hasattr(model_obj, field):
            setattr(model_obj, field, value)


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


@router.patch(
    "/executions/{id}",
    response_model=TestExecution,
    summary="更新执行记录",
    responses={
        (200): {"description": "执行记录更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def update_test_execution(
    id: str,
    execution_update: TestExecutionUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    """更新指定执行记录"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    update_data = execution_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(execution_db, key):
            setattr(execution_db, key, value)

    # 如果状态更新为完成，设置完成时间
    if execution_update.status == ExecutionStatus.COMPLETED and not execution_db.completed_at:
        execution_db.completed_at = datetime.now()
        if execution_db.started_at:
            duration = (execution_db.completed_at - execution_db.started_at).total_seconds()
            execution_db.duration = duration

    db.commit()
    db.refresh(execution_db)

    logger.info(
        f"Test execution updated | execution_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _db_to_execution(execution_db)


@router.delete(
    "/executions/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除执行记录",
    responses={
        (204): {"description": "执行记录删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def delete_test_execution(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """删除指定执行记录"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    db.delete(execution_db)
    db.commit()

    logger.info(
        f"Test execution deleted | execution_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.post(
    "/executions/{id}/retry",
    response_model=TestExecution,
    status_code=status.HTTP_201_CREATED,
    summary="重试执行",
    responses={
        (201): {"description": "执行重试成功"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def retry_test_execution(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    """重试失败的测试执行"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution_db.status not in [ExecutionStatus.FAILED.value, ExecutionStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed or cancelled executions",
        )

    # 创建新的执行记录
    retry_id = str(uuid.uuid4())
    now = datetime.now()

    retry_execution = TestExecutionDB(
        id=retry_id,
        suite_id=execution_db.suite_id,
        suite_name=execution_db.suite_name,
        status=ExecutionStatus.PENDING.value,
        started_at=now,
        total_tests=0,
        triggered_by=current_user.username,
        trigger_type="retry",
        environment=execution_db.environment,
    )

    db.add(retry_execution)
    db.commit()
    db.refresh(retry_execution)

    # 更新原执行的retry_count
    execution_db.retry_count = (execution_db.retry_count or 0) + 1
    db.commit()

    logger.info(
        f"Test execution retried | original_id={id} | retry_id={retry_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_execution(retry_execution)


@router.get(
    "/executions/{id}/logs",
    summary="获取执行日志",
    responses={
        (200): {"description": "执行日志"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def get_execution_logs(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """获取指定执行的日志"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Execution metadata is real (from the DB); the log body requires an
    # execution-log store, which is not configured — return it empty rather
    # than fabricating log lines.
    logs = {
        "execution_id": id,
        "suite_id": execution_db.suite_id,
        "status": execution_db.status,
        "started_at": execution_db.started_at.isoformat() if execution_db.started_at else None,
        "completed_at": execution_db.completed_at.isoformat() if execution_db.completed_at else None,
        "log_entries": [],
        "log_entries_available": False,
    }

    return logs


@router.get(
    "/suites/{id}/executions",
    response_model=List[TestExecution],
    summary="获取套件的执行历史",
    responses={
        (200): {"description": "执行历史"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def get_suite_executions(
    id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TestExecution]:
    """获取指定测试套件的执行历史"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    executions_db = (
        db.query(TestExecutionDB)
        .filter(TestExecutionDB.suite_id == id)
        .order_by(TestExecutionDB.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_db_to_execution(execution) for execution in executions_db]


@router.get(
    "/suites/{id}/statistics",
    summary="获取套件统计信息",
    responses={
        (200): {"description": "统计信息"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def get_suite_statistics(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """获取指定测试套件的统计信息"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    executions = db.query(TestExecutionDB).filter(TestExecutionDB.suite_id == id).all()

    total_executions = len(executions)
    passed = sum(1 for e in executions if e.status == ExecutionStatus.COMPLETED.value and e.failed_tests == 0)
    failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED.value)
    total_tests = sum(e.total_tests or 0 for e in executions)
    total_passed = sum(e.passed_tests or 0 for e in executions)
    total_failed = sum(e.failed_tests or 0 for e in executions)

    statistics = {
        "suite_id": id,
        "suite_name": suite_db.name,
        "total_executions": total_executions,
        "successful_executions": passed,
        "failed_executions": failed,
        "success_rate": (passed / total_executions * 100) if total_executions > 0 else 0,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "test_pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
        "last_execution": executions[0].started_at.isoformat() if executions else None,
    }

    return statistics


@router.post(
    "/reports",
    response_model=TestReport,
    status_code=status.HTTP_201_CREATED,
    summary="创建测试报告",
    responses={
        (201): {"description": "测试报告创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def create_test_report(
    report_create: TestReportCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestReport:
    """创建新的测试报告"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == report_create.execution_id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    report_id = str(uuid.uuid4())
    now = datetime.now()

    # Build the report payload from the real execution record and persist it.
    report_payload = {
        "report_id": report_id,
        "report_type": report_create.report_type,
        "format": report_create.format,
        "execution": {
            "id": execution_db.id,
            "suite_id": execution_db.suite_id,
            "suite_name": execution_db.suite_name,
            "status": execution_db.status,
            "started_at": execution_db.started_at,
            "completed_at": execution_db.completed_at,
            "total_tests": execution_db.total_tests,
            "passed_tests": execution_db.passed_tests,
            "failed_tests": execution_db.failed_tests,
            "skipped_tests": execution_db.skipped_tests,
            "coverage": execution_db.coverage,
        },
        "generated_at": now,
        "generated_by": current_user.username,
    }
    content = json.dumps(report_payload, default=str, indent=2).encode("utf-8")

    reports_dir = os.path.join(os.getcwd(), "reports", "test-automation")
    os.makedirs(reports_dir, exist_ok=True)
    file_path = os.path.join(reports_dir, f"{report_id}.{report_create.format}")
    with open(file_path, "wb") as handle:
        handle.write(content)

    report = TestReport(
        id=report_id,
        execution_id=report_create.execution_id,
        suite_id=execution_db.suite_id,
        suite_name=execution_db.suite_name,
        report_type=report_create.report_type,
        format=report_create.format,
        generated_at=now,
        generated_by=current_user.username,
        file_url=f"/reports/test-automation/{report_id}.{report_create.format}",
        file_size_bytes=len(content),
        status="completed",
    )

    _reports[report_id] = report

    logger.info(
        f"Test report created | report_id={report_id} | execution_id={report_create.execution_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return report


@router.get(
    "/reports/{id}",
    response_model=TestReport,
    summary="获取测试报告详情",
    responses={
        (200): {"description": "测试报告详情"},
        (401): {"description": "未授权"},
        (404): {"description": "测试报告不存在"},
    },
)
async def get_test_report(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestReport:
    """获取指定测试报告的详情"""
    if id not in _reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test report not found")
    return _reports[id]


@router.get(
    "/reports",
    response_model=List[TestReport],
    summary="获取测试报告列表",
    responses={
        (200): {"description": "测试报告列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_reports(
    execution_id: Optional[str] = None,
    report_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestReport]:
    """获取测试报告列表"""
    reports = list(_reports.values())
    if execution_id:
        reports = [r for r in reports if r.execution_id == execution_id]
    if report_type:
        reports = [r for r in reports if r.report_type == report_type]
    reports.sort(key=lambda r: r.generated_at, reverse=True)
    return reports[offset : offset + limit]


@router.delete(
    "/reports/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除测试报告",
    responses={
        (204): {"description": "测试报告删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试报告不存在"},
    },
)
async def delete_test_report(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定测试报告"""
    if id not in _reports:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test report not found")
    deleted = _reports.pop(id, None)
    if deleted and deleted.file_url:
        file_path = os.path.join(
            os.getcwd(), "reports", "test-automation", os.path.basename(deleted.file_url)
        )
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as exc:  # pragma: no cover - file cleanup is best effort
            logger.warning(f"Failed to remove report file {file_path}: {exc}")

    logger.info(
        f"Test report deleted | report_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.get(
    "/environments",
    response_model=List[TestEnvironment],
    summary="获取测试环境列表",
    responses={
        (200): {"description": "测试环境列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_environments(
    environment_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestEnvironment]:
    """获取测试环境列表"""
    environments = list(_environments.values())
    if environment_type:
        environments = [e for e in environments if e.environment_type == environment_type]
    if status:
        environments = [e for e in environments if e.status == status]
    environments.sort(key=lambda e: e.created_at, reverse=True)
    return environments[offset : offset + limit]


@router.post(
    "/environments",
    response_model=TestEnvironment,
    status_code=status.HTTP_201_CREATED,
    summary="创建测试环境",
    responses={
        (201): {"description": "测试环境创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_test_environment(
    environment_create: TestEnvironmentCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestEnvironment:
    """创建新的测试环境"""
    env_id = str(uuid.uuid4())
    now = datetime.now()

    environment = TestEnvironment(
        id=env_id,
        name=environment_create.name,
        description=environment_create.description,
        environment_type=environment_create.environment_type,
        config=environment_create.config,
        status="active",
        created_at=now,
        updated_at=now,
        created_by=current_user.username,
    )

    _environments[env_id] = environment

    logger.info(
        f"Test environment created | env_id={env_id} | name={environment_create.name} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return environment


@router.get(
    "/environments/{id}",
    response_model=TestEnvironment,
    summary="获取测试环境详情",
    responses={
        (200): {"description": "测试环境详情"},
        (401): {"description": "未授权"},
        (404): {"description": "测试环境不存在"},
    },
)
async def get_test_environment(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestEnvironment:
    """获取指定测试环境的详情"""
    if id not in _environments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test environment not found")
    return _environments[id]


@router.patch(
    "/environments/{id}",
    response_model=TestEnvironment,
    summary="更新测试环境",
    responses={
        (200): {"description": "测试环境更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试环境不存在"},
    },
)
async def update_test_environment(
    id: str,
    environment_update: TestEnvironmentUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestEnvironment:
    """更新指定测试环境"""
    if id not in _environments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test environment not found")

    environment = _environments[id]
    _apply_update(environment, environment_update)
    environment.updated_at = datetime.now()
    _environments[id] = environment

    logger.info(
        f"Test environment updated | env_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return environment


@router.delete(
    "/environments/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除测试环境",
    responses={
        (204): {"description": "测试环境删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试环境不存在"},
    },
)
async def delete_test_environment(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定测试环境"""
    if id not in _environments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test environment not found")
    _environments.pop(id, None)

    logger.info(
        f"Test environment deleted | env_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.get(
    "/schedules",
    response_model=List[TestSchedule],
    summary="获取测试调度列表",
    responses={
        (200): {"description": "测试调度列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_schedules(
    suite_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TestSchedule]:
    """获取测试调度列表"""
    schedules = list(_schedules.values())
    if suite_id:
        schedules = [s for s in schedules if s.suite_id == suite_id]
    if enabled is not None:
        schedules = [s for s in schedules if s.enabled == enabled]
    schedules.sort(key=lambda s: s.created_at, reverse=True)
    return schedules[offset : offset + limit]


@router.post(
    "/schedules",
    response_model=TestSchedule,
    status_code=status.HTTP_201_CREATED,
    summary="创建测试调度",
    responses={
        (201): {"description": "测试调度创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def create_test_schedule(
    schedule_create: TestScheduleCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestSchedule:
    """创建新的测试调度"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == schedule_create.suite_id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    schedule_id = str(uuid.uuid4())
    now = datetime.now()

    # 计算下次运行时间（简化版）
    next_run = now + timedelta(hours=1) if schedule_create.schedule_type == "interval" else None

    schedule = TestSchedule(
        id=schedule_id,
        suite_id=schedule_create.suite_id,
        suite_name=suite_db.name,
        schedule_type=schedule_create.schedule_type,
        cron_expression=schedule_create.cron_expression,
        interval_seconds=schedule_create.interval_seconds,
        enabled=schedule_create.enabled,
        last_run=None,
        next_run=next_run,
        created_at=now,
        updated_at=now,
        created_by=current_user.username,
    )

    _schedules[schedule_id] = schedule

    logger.info(
        f"Test schedule created | schedule_id={schedule_id} | suite_id={schedule_create.suite_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return schedule


@router.get(
    "/schedules/{id}",
    response_model=TestSchedule,
    summary="获取测试调度详情",
    responses={
        (200): {"description": "测试调度详情"},
        (401): {"description": "未授权"},
        (404): {"description": "测试调度不存在"},
    },
)
async def get_test_schedule(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestSchedule:
    """获取指定测试调度的详情"""
    if id not in _schedules:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test schedule not found")
    return _schedules[id]


@router.patch(
    "/schedules/{id}",
    response_model=TestSchedule,
    summary="更新测试调度",
    responses={
        (200): {"description": "测试调度更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试调度不存在"},
    },
)
async def update_test_schedule(
    id: str,
    schedule_update: TestScheduleUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestSchedule:
    """更新指定测试调度"""
    if id not in _schedules:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test schedule not found")

    schedule = _schedules[id]
    _apply_update(schedule, schedule_update)
    schedule.updated_at = datetime.now()
    _schedules[id] = schedule

    logger.info(
        f"Test schedule updated | schedule_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return schedule


@router.delete(
    "/schedules/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除测试调度",
    responses={
        (204): {"description": "测试调度删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试调度不存在"},
    },
)
async def delete_test_schedule(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定测试调度"""
    if id not in _schedules:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test schedule not found")
    _schedules.pop(id, None)

    logger.info(
        f"Test schedule deleted | schedule_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )


@router.post(
    "/schedules/{id}/trigger",
    response_model=TestExecution,
    status_code=status.HTTP_201_CREATED,
    summary="手动触发调度",
    responses={
        (201): {"description": "调度触发成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试调度不存在"},
    },
)
async def trigger_test_schedule(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    """手动触发测试调度"""
    if id not in _schedules:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test schedule not found")

    schedule = _schedules[id]
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == schedule.suite_id).first()
    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    execution_id = str(uuid.uuid4())
    now = datetime.now()

    execution_db = TestExecutionDB(
        id=execution_id,
        suite_id=schedule.suite_id,
        suite_name=suite_db.name,
        status=ExecutionStatus.PENDING.value,
        started_at=now,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        skipped_tests=0,
        triggered_by=current_user.username,
        trigger_type="scheduled",
    )
    db.add(execution_db)
    db.commit()
    db.refresh(execution_db)

    schedule.last_run = now
    if schedule.schedule_type == "interval" and schedule.interval_seconds:
        schedule.next_run = now + timedelta(seconds=schedule.interval_seconds)
    schedule.updated_at = now
    _schedules[id] = schedule

    logger.info(
        f"Test schedule triggered | schedule_id={id} | execution_id={execution_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_execution(execution_db)


@router.get(
    "/metrics",
    response_model=List[TestMetric],
    summary="获取测试指标列表",
    responses={
        (200): {"description": "测试指标列表"},
        (401): {"description": "未授权"},
    },
)
async def get_test_metrics(
    execution_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestMetric]:
    """获取测试指标列表"""
    metrics = list(_metrics.values())
    if execution_id:
        metrics = [m for m in metrics if m.execution_id == execution_id]
    if metric_name:
        metrics = [m for m in metrics if m.metric_name == metric_name]
    metrics.sort(key=lambda m: m.timestamp, reverse=True)
    return metrics[offset : offset + limit]


@router.post(
    "/metrics",
    response_model=TestMetric,
    status_code=status.HTTP_201_CREATED,
    summary="创建测试指标",
    responses={
        (201): {"description": "测试指标创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_test_metric(
    metric_create: TestMetricCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestMetric:
    """创建新的测试指标"""
    metric_id = str(uuid.uuid4())

    metric = TestMetric(
        id=metric_id,
        execution_id=metric_create.execution_id,
        metric_name=metric_create.metric_name,
        metric_value=metric_create.metric_value,
        unit=metric_create.unit,
        timestamp=datetime.now(),
        metadata=metric_create.metadata,
    )

    _metrics[metric_id] = metric

    logger.info(
        f"Test metric created | metric_id={metric_id} | execution_id={metric_create.execution_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return metric


@router.get(
    "/metrics/summary",
    summary="获取指标摘要",
    responses={
        (200): {"description": "指标摘要"},
        (401): {"description": "未授权"},
    },
)
async def get_metrics_summary(
    execution_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict:
    """获取测试指标摘要统计"""
    metrics = list(_metrics.values())
    if execution_id:
        metrics = [m for m in metrics if m.execution_id == execution_id]
    if metric_name:
        metrics = [m for m in metrics if m.metric_name == metric_name]

    grouped: Dict[str, List[float]] = {}
    for metric in metrics:
        grouped.setdefault(metric.metric_name, []).append(metric.metric_value)

    metric_types = {
        name: {
            "count": len(values),
            "avg": round(sum(values) / len(values), 2),
            "min": min(values),
            "max": max(values),
        }
        for name, values in grouped.items()
    }

    # Time-series view: per-day average of each metric so the summary surfaces
    # how metrics evolve over time rather than only their aggregate statistics.
    daily: Dict[str, Dict[str, List[float]]] = {}
    for metric in metrics:
        timestamp = getattr(metric, "timestamp", None)
        if not timestamp:
            continue
        day = timestamp.strftime("%Y-%m-%d")
        daily.setdefault(day, {}).setdefault(metric.metric_name, []).append(metric.metric_value)

    trends = [
        {
            "date": day,
            "metrics": {
                name: {"count": len(values), "avg": round(sum(values) / len(values), 2)}
                for name, values in sorted(metrics_by_name.items())
            },
        }
        for day, metrics_by_name in sorted(daily.items())
    ]

    return {
        "total_metrics": len(metrics),
        "metric_types": metric_types,
        "trends": trends,
    }


@router.get(
    "/health",
    summary="健康检查",
    responses={
        (200): {"description": "服务健康"},
    },
)
async def health_check() -> Dict:
    """测试自动化服务健康检查"""
    return {
        "status": "healthy",
        "service": "test-automation-advanced",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


@router.get(
    "/stats/overview",
    summary="获取概览统计",
    responses={
        (200): {"description": "概览统计"},
        (401): {"description": "未授权"},
    },
)
async def get_overview_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """获取测试自动化概览统计"""
    total_suites = db.query(TestSuiteDB).count()
    total_executions = db.query(TestExecutionDB).count()
    running_executions = db.query(TestExecutionDB).filter(
        TestExecutionDB.status == ExecutionStatus.RUNNING.value
    ).count()
    completed_executions = db.query(TestExecutionDB).filter(
        TestExecutionDB.status == ExecutionStatus.COMPLETED.value
    ).count()
    failed_executions = db.query(TestExecutionDB).filter(
        TestExecutionDB.status == ExecutionStatus.FAILED.value
    ).count()

    stats = {
        "total_suites": total_suites,
        "total_executions": total_executions,
        "running_executions": running_executions,
        "completed_executions": completed_executions,
        "failed_executions": failed_executions,
        "success_rate": (completed_executions / total_executions * 100) if total_executions > 0 else 0,
        "active_schedules": len([s for s in _schedules.values() if s.enabled]),
        "total_environments": len(_environments),
        "total_reports": len(_reports),
        "total_metrics": len(_metrics),
    }

    return stats


@router.get(
    "/executions/trends",
    summary="获取执行趋势",
    responses={
        (200): {"description": "执行趋势"},
        (401): {"description": "未授权"},
    },
)
async def get_execution_trends(
    days: int = 30,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """获取测试执行趋势数据"""
    since = datetime.now() - timedelta(days=days)
    executions = (
        db.query(TestExecutionDB)
        .filter(TestExecutionDB.started_at >= since)
        .all()
    )

    daily: Dict[str, Dict[str, float]] = {}
    for execution in executions:
        if not execution.started_at:
            continue
        day = execution.started_at.strftime("%Y-%m-%d")
        bucket = daily.setdefault(day, {"count": 0, "success": 0, "duration_sum": 0.0, "duration_n": 0})
        bucket["count"] += 1
        if execution.status == ExecutionStatus.COMPLETED.value:
            bucket["success"] += 1
        if execution.started_at and execution.completed_at:
            bucket["duration_sum"] += (execution.completed_at - execution.started_at).total_seconds()
            bucket["duration_n"] += 1

    ordered = sorted(daily.items())
    daily_executions = [{"date": day, "count": int(b["count"])} for day, b in ordered]
    success_rate_trend = [
        {"date": day, "rate": round(b["success"] / b["count"] * 100, 2) if b["count"] else 0.0}
        for day, b in ordered
    ]
    avg_duration_trend = [
        {
            "date": day,
            "duration": round(b["duration_sum"] / b["duration_n"], 2) if b["duration_n"] else 0.0,
        }
        for day, b in ordered
    ]

    return {
        "period_days": days,
        "daily_executions": daily_executions,
        "success_rate_trend": success_rate_trend,
        "avg_duration_trend": avg_duration_trend,
    }


@router.post(
    "/suites/{id}/clone",
    response_model=TestSuite,
    status_code=status.HTTP_201_CREATED,
    summary="克隆测试套件",
    responses={
        (201): {"description": "测试套件克隆成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def clone_test_suite(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestSuite:
    """克隆指定测试套件"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    new_suite_id = str(uuid.uuid4())
    now = datetime.now()

    cloned_suite = TestSuiteDB(
        id=new_suite_id,
        name=f"{suite_db.name} (Clone)",
        description=suite_db.description,
        test_type=suite_db.test_type,
        framework=suite_db.framework,
        status=TestSuiteStatus.ACTIVE.value,
        schedule=suite_db.schedule,
        created_by=current_user.username,
        created_at=now,
        updated_at=now,
    )

    db.add(cloned_suite)
    db.commit()
    db.refresh(cloned_suite)

    logger.info(
        f"Test suite cloned | original_id={id} | new_id={new_suite_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_suite(cloned_suite)


@router.post(
    "/suites/batch",
    response_model=List[TestSuite],
    status_code=status.HTTP_201_CREATED,
    summary="批量创建测试套件",
    responses={
        (201): {"description": "测试套件批量创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def batch_create_test_suites(
    suite_creates: List[TestSuiteCreate],
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TestSuite]:
    """批量创建测试套件"""
    if len(suite_creates) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create more than 50 suites at once",
        )

    created_suites = []
    now = datetime.now()

    for suite_create in suite_creates:
        suite_id = str(uuid.uuid4())

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
        created_suites.append(suite_db)

    db.commit()

    for suite_db in created_suites:
        db.refresh(suite_db)

    logger.info(
        f"Test suites batch created | count={len(suite_creates)} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return [_db_to_suite(suite) for suite in created_suites]


@router.post(
    "/executions/batch",
    response_model=List[TestExecution],
    status_code=status.HTTP_201_CREATED,
    summary="批量创建执行记录",
    responses={
        (201): {"description": "执行记录批量创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def batch_create_test_executions(
    execution_creates: List[TestExecutionCreate],
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TestExecution]:
    """批量创建测试执行记录"""
    if len(execution_creates) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create more than 20 executions at once",
        )

    created_executions = []
    now = datetime.now()

    for execution_create in execution_creates:
        suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == execution_create.suite_id).first()

        if not suite_db:
            logger.warning(f"Suite not found for execution: {execution_create.suite_id}")
            continue

        execution_id = str(uuid.uuid4())

        execution_db = TestExecutionDB(
            id=execution_id,
            suite_id=execution_create.suite_id,
            suite_name=suite_db.name,
            status=ExecutionStatus.PENDING.value,
            started_at=now,
            total_tests=0,
            triggered_by=current_user.username,
            trigger_type=execution_create.trigger_type,
            environment=execution_create.environment,
        )

        db.add(execution_db)
        created_executions.append(execution_db)

    db.commit()

    for execution_db in created_executions:
        db.refresh(execution_db)

    logger.info(
        f"Test executions batch created | count={len(created_executions)} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return [_db_to_execution(execution) for execution in created_executions]


@router.get(
    "/config",
    summary="获取配置",
    responses={
        (200): {"description": "配置信息"},
        (401): {"description": "未授权"},
    },
)
async def get_test_config(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict:
    """获取测试自动化配置"""
    config = {
        "max_parallel_executions": 5,
        "default_timeout_seconds": 3600,
        "retention_days": 90,
        "enabled_features": [
            "scheduling",
            "reporting",
            "metrics",
            "environments",
        ],
        "notification_channels": ["email", "slack"],
    }

    return config


@router.patch(
    "/config",
    summary="更新配置",
    responses={
        (200): {"description": "配置更新成功"},
        (401): {"description": "未授权"},
    },
)
async def update_test_config(
    config_updates: Dict,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict:
    """更新测试自动化配置"""
    logger.info(
        f"Test config updated | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return config_updates


@router.get(
    "/suites/{id}/history",
    summary="获取套件变更历史",
    responses={
        (200): {"description": "变更历史"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def get_suite_history(
    id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """获取指定测试套件的变更历史"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    # No suite change-audit store is configured; return an empty history rather
    # than fabricating a change record.
    history: List[Dict] = []

    return history[offset : offset + limit]


@router.post(
    "/executions/{id}/rerun",
    response_model=TestExecution,
    status_code=status.HTTP_201_CREATED,
    summary="重新运行执行",
    responses={
        (201): {"description": "执行重新运行成功"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def rerun_test_execution(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestExecution:
    """重新运行指定的测试执行"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # 创建新的执行记录
    rerun_id = str(uuid.uuid4())
    now = datetime.now()

    rerun_execution = TestExecutionDB(
        id=rerun_id,
        suite_id=execution_db.suite_id,
        suite_name=execution_db.suite_name,
        status=ExecutionStatus.PENDING.value,
        started_at=now,
        total_tests=0,
        triggered_by=current_user.username,
        trigger_type="rerun",
        environment=execution_db.environment,
    )

    db.add(rerun_execution)
    db.commit()
    db.refresh(rerun_execution)

    logger.info(
        f"Test execution rerun | original_id={id} | rerun_id={rerun_id} "
        f"| user={current_user.username} | ip={get_client_ip(request)}"
    )

    return _db_to_execution(rerun_execution)


@router.get(
    "/executions/{id}/artifacts",
    summary="获取执行产物",
    responses={
        (200): {"description": "执行产物"},
        (401): {"description": "未授权"},
        (404): {"description": "执行记录不存在"},
    },
)
async def get_execution_artifacts(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """获取指定执行的产物列表"""
    execution_db = db.query(TestExecutionDB).filter(TestExecutionDB.id == id).first()

    if not execution_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    # Artifacts are the real generated reports for this execution.
    artifacts = [
        {
            "name": os.path.basename(report.file_url) if report.file_url else f"{report.id}.{report.format}",
            "type": "report",
            "size_bytes": report.file_size_bytes,
            "url": report.file_url,
        }
        for report in _reports.values()
        if report.execution_id == id
    ]

    return artifacts


@router.post(
    "/suites/{id}/archive",
    response_model=TestSuite,
    summary="归档测试套件",
    responses={
        (200): {"description": "测试套件归档成功"},
        (401): {"description": "未授权"},
        (404): {"description": "测试套件不存在"},
    },
)
async def archive_test_suite(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TestSuite:
    """归档指定的测试套件"""
    suite_db = db.query(TestSuiteDB).filter(TestSuiteDB.id == id).first()

    if not suite_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test suite not found")

    suite_db.status = TestSuiteStatus.ARCHIVED.value
    suite_db.updated_at = datetime.now()
    db.commit()
    db.refresh(suite_db)

    logger.info(
        f"Test suite archived | suite_id={id} | user={current_user.username} "
        f"| ip={get_client_ip(request)}"
    )

    return _db_to_suite(suite_db)


# ---------------------------------------------------------------------------
# Route precedence
# ---------------------------------------------------------------------------
# Starlette matches routes in registration order and stops at the first route
# whose path template AND HTTP method both match. Literal paths such as
# ``/executions/trends`` therefore have to be registered before the
# parameterised ``/executions/{id}`` route, otherwise ``trends`` is captured as
# an execution id and the request 404s. Re-order explicitly so static segments
# always win over parameterised ones (fewer ``{...}`` placeholders first).
def _route_precedence(route: Any) -> tuple[int, int]:
    """Sort key placing literal routes before parameterised ones."""
    path = getattr(route, "path", "")
    return (path.count("{"), len(path))


router.routes.sort(key=_route_precedence)
