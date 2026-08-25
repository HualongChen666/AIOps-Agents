# -*- coding: utf-8 -*-
"""Advanced Dashboard API router for widgets and layouts."""

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

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard-advanced"])
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
class WidgetType(str, Enum):
    """小部件类型"""
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    LOG = "log"
    ALERT = "alert"
    STATUS = "status"


class LayoutType(str, Enum):
    """布局类型"""
    GRID = "grid"
    FLEX = "flex"
    CUSTOM = "custom"


# ============ Widget Models ============
class DashboardWidget(BaseModel):
    id: str
    widget_type: WidgetType
    title: str
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    data_source: Optional[str] = None
    refresh_interval: int = 30
    position: Dict[str, int] = Field(default_factory=dict)
    size: Dict[str, int] = Field(default_factory=lambda: {"width": 4, "height": 3})
    enabled: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class DashboardWidgetCreate(BaseModel):
    widget_type: WidgetType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None
    data_source: Optional[str] = Field(None, max_length=200)
    refresh_interval: int = Field(default=30, ge=5, le=3600)
    position: Optional[Dict[str, int]] = None
    size: Optional[Dict[str, int]] = None

    model_config = {"extra": "ignore"}


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    config: Optional[Dict[str, Any]] = None
    data_source: Optional[str] = Field(None, max_length=200)
    refresh_interval: Optional[int] = Field(None, ge=5, le=3600)
    position: Optional[Dict[str, int]] = None
    size: Optional[Dict[str, int]] = None
    enabled: Optional[bool] = None

    model_config = {"extra": "ignore"}


# ============ Layout Models ============
class DashboardLayout(BaseModel):
    id: str
    layout_name: str
    layout_type: LayoutType
    columns: int = 12
    rows: int = 12
    gap: int = 16
    widgets: List[str] = Field(default_factory=list)  # widget IDs
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {"extra": "ignore"}


class DashboardLayoutUpdate(BaseModel):
    layout_name: Optional[str] = Field(None, min_length=1, max_length=200)
    layout_type: Optional[LayoutType] = None
    columns: Optional[int] = Field(None, ge=1, le=24)
    rows: Optional[int] = Field(None, ge=1, le=50)
    gap: Optional[int] = Field(None, ge=0, le=100)
    widgets: Optional[List[str]] = None
    is_default: Optional[bool] = None

    model_config = {"extra": "ignore"}


# ============ In-memory data storage ============
_dashboard_widgets: Dict[str, DashboardWidget] = {}
_dashboard_layouts: Dict[str, DashboardLayout] = {}


def _init_dashboard_widgets():
    """初始化默认小部件"""
    if not _dashboard_widgets:
        widget1 = DashboardWidget(
            id=str(uuid.uuid4()),
            widget_type=WidgetType.METRIC,
            title="Total Hosts",
            description="Total number of monitored hosts",
            config={"metric": "hosts.total", "unit": "count"},
            data_source="/api/v1/hosts",
            refresh_interval=60,
            position={"x": 0, "y": 0},
            size={"width": 3, "height": 2},
            enabled=True,
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=1),
            created_by="admin",
        )

        widget2 = DashboardWidget(
            id=str(uuid.uuid4()),
            widget_type=WidgetType.CHART,
            title="CPU Usage",
            description="CPU usage over time",
            config={"chart_type": "line", "time_range": "1h"},
            data_source="/api/v1/metrics/cpu",
            refresh_interval=30,
            position={"x": 3, "y": 0},
            size={"width": 6, "height": 3},
            enabled=True,
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=1),
            created_by="admin",
        )

        widget3 = DashboardWidget(
            id=str(uuid.uuid4()),
            widget_type=WidgetType.ALERT,
            title="Active Alerts",
            description="Currently active alerts",
            config={"severity": ["critical", "warning"]},
            data_source="/api/v1/alerts",
            refresh_interval=15,
            position={"x": 9, "y": 0},
            size={"width": 3, "height": 3},
            enabled=True,
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=1),
            created_by="admin",
        )

        _dashboard_widgets[widget1.id] = widget1
        _dashboard_widgets[widget2.id] = widget2
        _dashboard_widgets[widget3.id] = widget3


def _init_dashboard_layouts():
    """初始化默认布局"""
    if not _dashboard_layouts:
        _init_dashboard_widgets()
        widget_ids = list(_dashboard_widgets.keys())

        layout = DashboardLayout(
            id=str(uuid.uuid4()),
            layout_name="Default Layout",
            layout_type=LayoutType.GRID,
            columns=12,
            rows=12,
            gap=16,
            widgets=widget_ids,
            is_default=True,
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(hours=1),
            created_by="admin",
        )

        _dashboard_layouts[layout.id] = layout


# 初始化数据
_init_dashboard_widgets()
_init_dashboard_layouts()


# ============ Widget Endpoints ============
@router.get(
    "/widgets",
    response_model=List[DashboardWidget],
    summary="获取仪表盘小部件列表",
    responses={
        (200): {"description": "小部件列表"},
        (401): {"description": "未授权"},
    },
)
async def get_dashboard_widgets(
    widget_type: Optional[WidgetType] = None,
    enabled_only: bool = False,
    current_user: UserInDB = Depends(get_current_user),
) -> List[DashboardWidget]:
    """获取所有仪表盘小部件"""
    widgets = list(_dashboard_widgets.values())

    if widget_type:
        widgets = [w for w in widgets if w.widget_type == widget_type]

    if enabled_only:
        widgets = [w for w in widgets if w.enabled]

    return widgets


@router.post(
    "/widgets",
    response_model=DashboardWidget,
    status_code=status.HTTP_201_CREATED,
    summary="创建仪表盘小部件",
    responses={
        (201): {"description": "小部件创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_dashboard_widget(
    widget_create: DashboardWidgetCreate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardWidget:
    """创建新的仪表盘小部件"""
    widget_id = str(uuid.uuid4())
    now = datetime.now()

    widget = DashboardWidget(
        id=widget_id,
        widget_type=widget_create.widget_type,
        title=widget_create.title,
        description=widget_create.description,
        config=widget_create.config or {},
        data_source=widget_create.data_source,
        refresh_interval=widget_create.refresh_interval,
        position=widget_create.position or {"x": 0, "y": 0},
        size=widget_create.size or {"width": 4, "height": 3},
        enabled=True,
        created_at=now,
        updated_at=now,
        created_by=current_user.username,
    )

    _dashboard_widgets[widget_id] = widget

    logger.info(
        f"Dashboard widget created | widget_id={widget_id} | title={widget_create.title} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return widget


@router.get(
    "/widgets/{id}",
    response_model=DashboardWidget,
    summary="获取小部件详情",
    responses={
        (200): {"description": "小部件详情"},
        (401): {"description": "未授权"},
        (404): {"description": "小部件不存在"},
    },
)
async def get_dashboard_widget(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardWidget:
    """获取指定小部件的详情"""
    if id not in _dashboard_widgets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return _dashboard_widgets[id]


@router.patch(
    "/widgets/{id}",
    response_model=DashboardWidget,
    summary="更新小部件",
    responses={
        (200): {"description": "小部件更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "小部件不存在"},
    },
)
async def update_dashboard_widget(
    id: str,
    widget_update: DashboardWidgetUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardWidget:
    """更新指定小部件"""
    if id not in _dashboard_widgets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    widget = _dashboard_widgets[id]
    update_data = widget_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(widget, key):
            setattr(widget, key, value)

    widget.updated_at = datetime.now()
    _dashboard_widgets[id] = widget

    logger.info(
        f"Dashboard widget updated | widget_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return widget


@router.delete(
    "/widgets/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除小部件",
    responses={
        (204): {"description": "小部件删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "小部件不存在"},
    },
)
async def delete_dashboard_widget(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定小部件"""
    if id not in _dashboard_widgets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    del _dashboard_widgets[id]

    # 从所有布局中移除该小部件
    for layout in _dashboard_layouts.values():
        if id in layout.widgets:
            layout.widgets = [w for w in layout.widgets if w != id]
            layout.updated_at = datetime.now()

    logger.info(
        f"Dashboard widget deleted | widget_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )


# ============ Layout Endpoints ============
@router.get(
    "/layouts",
    response_model=List[DashboardLayout],
    summary="获取仪表盘布局列表",
    responses={
        (200): {"description": "布局列表"},
        (401): {"description": "未授权"},
    },
)
async def get_dashboard_layouts(
    current_user: UserInDB = Depends(get_current_user),
) -> List[DashboardLayout]:
    """获取所有仪表盘布局"""
    return list(_dashboard_layouts.values())


@router.post(
    "/layouts",
    response_model=DashboardLayout,
    status_code=status.HTTP_201_CREATED,
    summary="创建仪表盘布局",
    responses={
        (201): {"description": "布局创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
    },
)
async def create_dashboard_layout(
    layout_name: str,
    layout_type: LayoutType = LayoutType.GRID,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardLayout:
    """创建新的仪表盘布局"""
    layout_id = str(uuid.uuid4())
    now = datetime.now()

    layout = DashboardLayout(
        id=layout_id,
        layout_name=layout_name,
        layout_type=layout_type,
        columns=12,
        rows=12,
        gap=16,
        widgets=[],
        is_default=False,
        created_at=now,
        updated_at=now,
        created_by=current_user.username,
    )

    _dashboard_layouts[layout_id] = layout

    logger.info(
        f"Dashboard layout created | layout_id={layout_id} | name={layout_name} | "
        f"user={current_user.username} | ip={get_client_ip(request)}"
    )

    return layout


@router.get(
    "/layouts/{id}",
    response_model=DashboardLayout,
    summary="获取布局详情",
    responses={
        (200): {"description": "布局详情"},
        (401): {"description": "未授权"},
        (404): {"description": "布局不存在"},
    },
)
async def get_dashboard_layout(
    id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardLayout:
    """获取指定布局的详情"""
    if id not in _dashboard_layouts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found")
    return _dashboard_layouts[id]


@router.patch(
    "/layouts/{id}",
    response_model=DashboardLayout,
    summary="更新布局",
    responses={
        (200): {"description": "布局更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "布局不存在"},
    },
)
async def update_dashboard_layout(
    id: str,
    layout_update: DashboardLayoutUpdate,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> DashboardLayout:
    """更新指定布局"""
    if id not in _dashboard_layouts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found")

    layout = _dashboard_layouts[id]
    update_data = layout_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(layout, key):
            setattr(layout, key, value)

    layout.updated_at = datetime.now()
    _dashboard_layouts[id] = layout

    logger.info(
        f"Dashboard layout updated | layout_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )

    return layout


@router.delete(
    "/layouts/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除布局",
    responses={
        (204): {"description": "布局删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "布局不存在"},
    },
)
async def delete_dashboard_layout(
    id: str,
    request: Request,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定布局"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    if id not in _dashboard_layouts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout not found")

    layout = _dashboard_layouts[id]
    if layout.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default layout"
        )

    del _dashboard_layouts[id]

    logger.info(
        f"Dashboard layout deleted | layout_id={id} | user={current_user.username} | ip={get_client_ip(request)}"
    )
