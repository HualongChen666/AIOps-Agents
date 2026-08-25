# -*- coding: utf-8 -*-
"""Advanced Test Framework API router for configurations and settings."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/test-framework", tags=["test-framework-advanced"])
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
class FrameworkType(str, Enum):
    """测试框架类型"""
    PYTEST = "pytest"
    JUNIT = "junit"
    SELENIUM = "selenium"
    CYPRESS = "cypress"
    LOCUST = "locust"
    JEST = "jest"


class ParallelMode(str, Enum):
    """并行模式"""
    NONE = "none"
    PROCESSES = "processes"
    THREADS = "threads"
    DISTRIBUTED = "distributed"


# ============ Configuration Models ============
class TestFrameworkConfig(BaseModel):
    id: str
    framework: FrameworkType
    version: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    test_paths: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    parallel_mode: ParallelMode = ParallelMode.NONE
    parallel_workers: int = 1
    timeout: int = 300
    retry_count: int = 0
    coverage_enabled: bool = True
    coverage_threshold: float = 80.0
    reporting_enabled: bool = True
    report_formats: List[str] = Field(default_factory=lambda: ["html", "json"])
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class TestFrameworkConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    test_paths: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    parallel_mode: Optional[ParallelMode] = None
    parallel_workers: Optional[int] = Field(None, ge=1, le=32)
    timeout: Optional[int] = Field(None, ge=1, le=3600)
    retry_count: Optional[int] = Field(None, ge=0, le=5)
    coverage_enabled: Optional[bool] = None
    coverage_threshold: Optional[float] = Field(None, ge=0, le=100)
    reporting_enabled: Optional[bool] = None
    report_formats: Optional[List[str]] = None

    model_config = {"extra": "ignore"}


# ============ In-memory data storage ============
_framework_configs: Dict[str, TestFrameworkConfig] = {}


def _init_framework_configs():
    """初始化默认框架配置"""
    if not _framework_configs:
        config1 = TestFrameworkConfig(
            id="pytest-config",
            framework=FrameworkType.PYTEST,
            version="7.4.0",
            enabled=True,
            config={
                "addopts": "-v --tb=short",
                "testpaths": ["tests"],
                "python_files": ["test_*.py"],
                "python_classes": ["Test*"],
                "python_functions": ["test_*"],
            },
            test_paths=["tests/unit", "tests/integration"],
            exclude_patterns=["tests/e2e/*", "tests/performance/*"],
            parallel_mode=ParallelMode.PROCESSES,
            parallel_workers=4,
            timeout=300,
            retry_count=1,
            coverage_enabled=True,
            coverage_threshold=80.0,
            reporting_enabled=True,
            report_formats=["html", "json", "xml"],
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=1),
            created_by="admin",
        )

        config2 = TestFrameworkConfig(
            id="locust-config",
            framework=FrameworkType.LOCUST,
            version="2.15.0",
            enabled=True,
            config={
                "host": "http://localhost:8000",
                "users": 100,
                "spawn_rate": 10,
                "run_time": "5m",
            },
            test_paths=["tests/performance"],
            exclude_patterns=[],
            parallel_mode=ParallelMode.DISTRIBUTED,
            parallel_workers=2,
            timeout=600,
            retry_count=0,
            coverage_enabled=False,
            coverage_threshold=0.0,
            reporting_enabled=True,
            report_formats=["html"],
            created_at=datetime.now() - timedelta(days=20),
            updated_at=datetime.now() - timedelta(hours=2),
            created_by="admin",
        )

        _framework_configs[config1.id] = config1
        _framework_configs[config2.id] = config2


# 初始化数据
_init_framework_configs()


# ============ Configuration Endpoints ============
@router.get(
    "/configurations",
    response_model=List[TestFrameworkConfig],
    summary="获取测试框架配置列表",
    responses={
        (200): {"description": "框架配置列表"},
        (401): {"description": "未授权"},
    },
)
async def get_framework_configurations(
    framework: Optional[FrameworkType] = None,
    enabled_only: bool = False,
    current_user: UserInDB = Depends(get_current_user),
) -> List[TestFrameworkConfig]:
    """获取所有测试框架配置"""
    configs = list(_framework_configs.values())

    if framework:
        configs = [c for c in configs if c.framework == framework]

    if enabled_only:
        configs = [c for c in configs if c.enabled]

    return configs


@router.get(
    "/configurations/{id}",
    response_model=TestFrameworkConfig,
    summary="获取框架配置详情",
    responses={
        (200): {"description": "框架配置详情"},
        (401): {"description": "未授权"},
        (404): {"description": "配置不存在"},
    },
)
async def get_framework_configuration(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> TestFrameworkConfig:
    """获取指定框架配置的详情"""
    if id not in _framework_configs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")
    return _framework_configs[id]


@router.patch(
    "/configurations/{id}",
    response_model=TestFrameworkConfig,
    summary="更新框架配置",
    responses={
        (200): {"description": "框架配置更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "配置不存在"},
    },
)
async def update_framework_configuration(
    id: str,
    config_update: TestFrameworkConfigUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> TestFrameworkConfig:
    """更新指定框架配置"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    if id not in _framework_configs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    config = _framework_configs[id]
    update_data = config_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    config.updated_at = datetime.now()
    _framework_configs[id] = config

    logger.info(
        f"Framework config updated | config_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return config


@router.post(
    "/configurations/{id}/validate",
    summary="验证框架配置",
    responses={
        (200): {"description": "配置验证结果"},
        (401): {"description": "未授权"},
        (404): {"description": "配置不存在"},
    },
)
async def validate_framework_configuration(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """验证指定的框架配置是否有效"""
    if id not in _framework_configs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found")

    config = _framework_configs[id]

    # 模拟验证逻辑
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "config_id": id,
        "framework": config.framework.value,
    }

    # 检查测试路径是否存在
    if not config.test_paths:
        validation_result["warnings"].append("No test paths configured")

    # 检查覆盖率阈值
    if config.coverage_enabled and config.coverage_threshold < 50:
        validation_result["warnings"].append("Coverage threshold is below 50%")

    # 检查并行设置
    if config.parallel_mode != ParallelMode.NONE and config.parallel_workers < 2:
        validation_result["errors"].append("Parallel mode requires at least 2 workers")
        validation_result["valid"] = False

    return validation_result


@router.get(
    "/status",
    summary="获取框架状态",
    responses={
        (200): {"description": "框架状态"},
        (401): {"description": "未授权"},
    },
)
async def get_framework_status(
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """获取所有测试框架的状态"""
    configs = list(_framework_configs.values())

    status_summary = {
        "total_frameworks": len(configs),
        "enabled_frameworks": len([c for c in configs if c.enabled]),
        "frameworks": [],
        "timestamp": datetime.now().isoformat(),
    }

    for config in configs:
        status_summary["frameworks"].append(
            {
                "id": config.id,
                "framework": config.framework.value,
                "version": config.version,
                "enabled": config.enabled,
                "test_paths": config.test_paths,
                "parallel_mode": config.parallel_mode.value,
                "parallel_workers": config.parallel_workers,
            }
        )

    return status_summary
