# -*- coding: utf-8 -*-
"""Advanced User API router for profile, preferences, activity, sessions, notifications, teams."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

from core.authentication import UserInDB, get_user, hash_password, verify_token
from core.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users-advanced"])
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


# ============ Profile Models ============
class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    password: Optional[str] = Field(
        None, min_length=8, max_length=100, description="User password (required for new users)"
    )

    model_config = {"extra": "ignore"}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)

    model_config = {"extra": "ignore"}


# ============ Preferences Models ============
class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"
    notifications_enabled: bool = True
    email_notifications: bool = True
    desktop_notifications: bool = False
    auto_refresh_interval: int = 30
    items_per_page: int = 20
    default_dashboard: str = "overview"

    model_config = {"extra": "ignore"}


class UserPreferencesUpdate(BaseModel):
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    date_format: Optional[str] = Field(None, max_length=20)
    time_format: Optional[str] = Field(None, pattern="^(12h|24h)$")
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    desktop_notifications: Optional[bool] = None
    auto_refresh_interval: Optional[int] = Field(None, ge=5, le=300)
    items_per_page: Optional[int] = Field(None, ge=5, le=100)
    default_dashboard: Optional[str] = Field(None, max_length=50)

    model_config = {"extra": "ignore"}


# ============ Activity Models ============
class ActivityLog(BaseModel):
    id: str
    user_id: int
    username: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    model_config = {"extra": "ignore"}


# ============ Session Models ============
class Session(BaseModel):
    id: str
    user_id: int
    username: str
    ip_address: str
    user_agent: str
    device_type: str
    browser: str
    os: str
    location: Optional[str] = None
    is_current: bool = False
    created_at: datetime
    last_activity: datetime
    expires_at: datetime

    model_config = {"extra": "ignore"}


# ============ Notification Models ============
class Notification(BaseModel):
    id: str
    user_id: int
    type: str
    title: str
    message: str
    priority: str = "normal"
    read: bool = False
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"extra": "ignore"}


class NotificationUpdate(BaseModel):
    read: Optional[bool] = None
    read_all: Optional[bool] = None

    model_config = {"extra": "ignore"}


# ============ Team Models ============
class TeamMember(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    team_role: str
    joined_at: datetime

    model_config = {"extra": "ignore"}


# ============ Permission Models ============
class UserPermission(BaseModel):
    asset_id: int
    permission: str = Field(..., pattern="^(view|edit|admin)$")
    granted_at: Optional[datetime] = None
    granted_by: Optional[str] = None

    model_config = {"extra": "ignore"}


class UserPermissionsResponse(BaseModel):
    user_id: int
    username: str
    permissions: List[UserPermission]

    model_config = {"extra": "ignore"}


# ============ Group Models ============
class UserGroup(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    member_count: int
    created_at: Optional[datetime] = None

    model_config = {"extra": "ignore"}


class UserGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    model_config = {"extra": "ignore"}


# ============ In-memory data storage (for demo) ============
_user_preferences: Dict[int, UserPreferences] = {}
_activity_logs: List[ActivityLog] = []
_user_sessions: Dict[int, List[Session]] = {}
_user_notifications: Dict[int, List[Notification]] = {}
_user_permissions: Dict[int, List[UserPermission]] = {}
_user_groups: List[UserGroup] = []


def _get_user_preferences(user_id: int) -> UserPreferences:
    """获取用户偏好设置"""
    if user_id not in _user_preferences:
        _user_preferences[user_id] = UserPreferences()
    return _user_preferences[user_id]


def _add_activity_log(
    user_id: int,
    username: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> ActivityLog:
    """添加活动日志"""
    global _activity_logs
    log = ActivityLog(
        id=f"act-{len(_activity_logs) + 1}",
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        created_at=datetime.now(),
    )
    _activity_logs.append(log)
    # 只保留最近1000条
    if len(_activity_logs) > 1000:
        _activity_logs = _activity_logs[
            -1000:
        ]  # noqa: F841 - Intentionally filtering to maintain data consistency
    return log


def _get_user_sessions(user_id: int) -> List[Session]:
    """获取用户会话"""
    if user_id not in _user_sessions:
        # 创建默认会话
        _user_sessions[user_id] = [
            Session(
                id=f"session-{user_id}-1",
                user_id=user_id,
                username="current",
                ip_address="127.0.0.1",
                user_agent="Mozilla/5.0",
                device_type="desktop",
                browser="Chrome",
                os="Windows",
                is_current=True,
                created_at=datetime.now() - timedelta(hours=2),
                last_activity=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7),
            )
        ]
    return _user_sessions[user_id]


def _get_user_notifications(user_id: int) -> List[Notification]:
    """获取用户通知"""
    if user_id not in _user_notifications:
        # 创建默认通知
        _user_notifications[user_id] = [
            Notification(
                id=f"notif-{user_id}-1",
                user_id=user_id,
                type="info",
                title="欢迎使用系统",
                message="感谢您注册使用AIOps Agent系统",
                priority="normal",
                read=False,
                created_at=datetime.now() - timedelta(days=1),
            ),
            Notification(
                id=f"notif-{user_id}-2",
                user_id=user_id,
                type="alert",
                title="系统更新通知",
                message="系统已更新到最新版本，请查看更新日志",
                priority="high",
                read=False,
                created_at=datetime.now() - timedelta(hours=6),
            ),
        ]
    return _user_notifications[user_id]


def _get_team_members() -> List[TeamMember]:
    """获取团队成员（模拟数据）"""
    return [
        TeamMember(
            id=1,
            username="admin",
            full_name="系统管理员",
            email="admin@example.com",
            role="admin",
            team_role="owner",
            joined_at=datetime.now() - timedelta(days=30),
        ),
        TeamMember(
            id=2,
            username="operator",
            full_name="运维工程师",
            email="operator@example.com",
            role="operator",
            team_role="member",
            joined_at=datetime.now() - timedelta(days=15),
        ),
    ]


# ============ Profile Endpoints ============
@router.get(
    "/profile",
    response_model=UserProfile,
    summary="获取用户资料",
    responses={
        (200): {"description": "用户资料"},
        (401): {"description": "未授权"},
    },
)
async def get_user_profile(current_user: UserInDB = Depends(get_current_user)) -> UserProfile:
    """获取当前用户的详细资料"""
    user = await user_service.get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfile(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=None,
        bio=None,
        location=None,
        website=None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch(
    "/profile",
    response_model=UserProfile,
    summary="更新用户资料",
    responses={
        (200): {"description": "用户资料更新成功"},
        (401): {"description": "未授权"},
        (400): {"description": "无效的请求数据"},
    },
)
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> UserProfile:
    """更新当前用户的资料"""
    success = await user_service.update_user(
        username=current_user.username,
        email=profile_update.email,
        full_name=profile_update.full_name,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile"
        )

    user = await user_service.get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 记录活动日志
    _add_activity_log(
        user_id=user.id if user.id else 0,
        username=user.username,
        action="update_profile",
        resource_type="user",
        resource_id=str(user.id),
        details="Updated user profile",
    )

    return UserProfile(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=profile_update.avatar_url,
        bio=profile_update.bio,
        location=profile_update.location,
        website=profile_update.website,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


# ============ Preferences Endpoints ============
@router.get(
    "/preferences",
    response_model=UserPreferences,
    summary="获取用户偏好设置",
    responses={
        (200): {"description": "用户偏好设置"},
        (401): {"description": "未授权"},
    },
)
async def get_user_preferences_endpoint(
    current_user: UserInDB = Depends(get_current_user),
) -> UserPreferences:
    """获取当前用户的偏好设置"""
    user_id = current_user.id if current_user.id else 0
    return _get_user_preferences(user_id)


@router.patch(
    "/preferences",
    response_model=UserPreferences,
    summary="更新用户偏好设置",
    responses={
        (200): {"description": "偏好设置更新成功"},
        (401): {"description": "未授权"},
    },
)
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> UserPreferences:
    """更新当前用户的偏好设置"""
    user_id = current_user.id if current_user.id else 0
    preferences = _get_user_preferences(user_id)

    update_data = preferences_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(preferences, key):
            setattr(preferences, key, value)

    _user_preferences[user_id] = preferences

    # 记录活动日志
    _add_activity_log(
        user_id=user_id,
        username=current_user.username,
        action="update_preferences",
        resource_type="preferences",
        details=f"Updated preferences: {list(update_data.keys())}",
    )

    return preferences


# ============ Activity Endpoints ============
@router.get(
    "/activity",
    response_model=List[ActivityLog],
    summary="获取用户活动日志",
    responses={
        (200): {"description": "活动日志列表"},
        (401): {"description": "未授权"},
    },
)
async def get_user_activity(
    limit: int = 50,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[ActivityLog]:
    """获取当前用户的活动日志"""
    user_id = current_user.id if current_user.id else 0
    user_logs = [log for log in _activity_logs if log.user_id == user_id]
    user_logs.sort(key=lambda x: x.created_at, reverse=True)
    return user_logs[offset : offset + limit]


# ============ Sessions Endpoints ============
@router.get(
    "/sessions",
    response_model=List[Session],
    summary="获取用户会话列表",
    responses={
        (200): {"description": "会话列表"},
        (401): {"description": "未授权"},
    },
)
async def get_user_sessions(
    current_user: UserInDB = Depends(get_current_user),
) -> List[Session]:
    """获取当前用户的所有活跃会话"""
    user_id = current_user.id if current_user.id else 0
    sessions = _get_user_sessions(user_id)
    # 标记当前会话
    for session in sessions:
        if session.is_current:
            session.last_activity = datetime.now()
    return sessions


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户会话",
    responses={
        (204): {"description": "会话删除成功"},
        (401): {"description": "未授权"},
        (404): {"description": "会话不存在"},
    },
)
async def delete_user_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定的用户会话（退出登录）"""
    user_id = current_user.id if current_user.id else 0
    sessions = _get_user_sessions(user_id)

    original_count = len(sessions)
    _user_sessions[user_id] = [s for s in sessions if s.id != session_id]

    if len(_user_sessions[user_id]) == original_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # 记录活动日志
    _add_activity_log(
        user_id=user_id,
        username=current_user.username,
        action="delete_session",
        resource_type="session",
        resource_id=session_id,
        details=f"Deleted session: {session_id}",
    )


# ============ Notifications Endpoints ============
@router.get(
    "/notifications",
    response_model=List[Notification],
    summary="获取用户通知",
    responses={
        (200): {"description": "通知列表"},
        (401): {"description": "未授权"},
    },
)
async def get_user_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_user),
) -> List[Notification]:
    """获取当前用户的通知"""
    user_id = current_user.id if current_user.id else 0
    notifications = _get_user_notifications(user_id)

    if unread_only:
        notifications = [n for n in notifications if not n.read]

    notifications.sort(key=lambda x: x.created_at, reverse=True)
    return notifications[:limit]


@router.patch(
    "/notifications/{notification_id}",
    response_model=Notification,
    summary="更新通知状态",
    responses={
        (200): {"description": "通知更新成功"},
        (401): {"description": "未授权"},
        (404): {"description": "通知不存在"},
    },
)
async def update_notification(
    notification_id: str,
    notification_update: NotificationUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> Notification:
    """更新指定通知的状态"""
    user_id = current_user.id if current_user.id else 0
    notifications = _get_user_notifications(user_id)

    for notification in notifications:
        if notification.id == notification_id:
            if notification_update.read is not None:
                notification.read = notification_update.read
            return notification

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


@router.patch(
    "/notifications",
    summary="批量更新通知",
    responses={
        (200): {"description": "批量更新成功"},
        (401): {"description": "未授权"},
    },
)
async def bulk_update_notifications(
    notification_update: NotificationUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> Dict[str, Any]:
    """批量更新通知（如全部标记为已读）"""
    user_id = current_user.id if current_user.id else 0
    notifications = _get_user_notifications(user_id)

    if notification_update.read_all:
        for notification in notifications:
            notification.read = True
        return {"message": f"Marked {len(notifications)} notifications as read"}

    return {"message": "No changes made"}


# ============ Teams Endpoints ============
@router.get(
    "/teams",
    response_model=List[TeamMember],
    summary="获取团队成员",
    responses={
        (200): {"description": "团队成员列表"},
        (401): {"description": "未授权"},
    },
)
async def get_team_members(
    current_user: UserInDB = Depends(get_current_user),
) -> List[TeamMember]:
    """获取当前用户所在团队的成员列表"""
    return _get_team_members()


# ============ Profiles Endpoints ============
@router.get(
    "/profiles",
    response_model=List[UserProfile],
    summary="获取所有用户资料",
    responses={
        (200): {"description": "用户资料列表"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def get_all_profiles(
    limit: int = 100,
    offset: int = 0,
    current_user: UserInDB = Depends(get_current_user),
) -> List[UserProfile]:
    """获取所有用户的资料列表（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    users = await user_service.list_users(limit=limit, offset=offset)
    profiles = []
    for user in users:
        profiles.append(
            UserProfile(
                id=user.id if user.id else 0,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                avatar_url=None,
                bio=None,
                location=None,
                website=None,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            )
        )
    return profiles


@router.post(
    "/profiles",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户资料",
    responses={
        (201): {"description": "用户资料创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def create_user_profile(
    profile_data: UserProfile,
    current_user: UserInDB = Depends(get_current_user),
) -> UserProfile:
    """创建新用户资料（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    # 检查用户是否已存在
    existing = await user_service.get_user_by_username(profile_data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    # 验证密码是否提供
    if not profile_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required for user creation"
        )

    # 创建用户
    hashed_password = hash_password(profile_data.password)
    success = await user_service.create_user(
        username=profile_data.username,
        hashed_password=hashed_password,
        email=profile_data.email,
        full_name=profile_data.full_name,
        role=profile_data.role,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user"
        )

    user = await user_service.get_user_by_username(profile_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed"
        )

    # 记录活动日志
    _add_activity_log(
        user_id=user.id if user.id else 0,
        username=user.username,
        action="create_profile",
        resource_type="user",
        resource_id=str(user.id),
        details=f"Created user profile: {user.username}",
    )

    return UserProfile(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=profile_data.avatar_url,
        bio=profile_data.bio,
        location=profile_data.location,
        website=profile_data.website,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get(
    "/profiles/{id}",
    response_model=UserProfile,
    summary="获取指定用户资料",
    responses={
        (200): {"description": "用户资料"},
        (401): {"description": "未授权"},
        (404): {"description": "用户不存在"},
    },
)
async def get_user_profile_by_id(
    id: int,
    current_user: UserInDB = Depends(get_current_user),
) -> UserProfile:
    """获取指定用户的资料"""
    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfile(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=None,
        bio=None,
        location=None,
        website=None,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch(
    "/profiles/{id}",
    response_model=UserProfile,
    summary="更新指定用户资料",
    responses={
        (200): {"description": "用户资料更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
    },
)
async def update_user_profile_by_id(
    id: int,
    profile_update: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> UserProfile:
    """更新指定用户的资料（需要管理员权限或本人）"""
    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 权限检查：只有管理员或本人可以更新
    if current_user.role != "admin" and current_user.id != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    success = await user_service.update_user(
        username=user.username,
        email=profile_update.email,
        full_name=profile_update.full_name,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update profile"
        )

    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 记录活动日志
    _add_activity_log(
        user_id=user.id if user.id else 0,
        username=user.username,
        action="update_profile",
        resource_type="user",
        resource_id=str(user.id),
        details=f"Updated user profile by {current_user.username}",
    )

    return UserProfile(
        id=user.id if user.id else 0,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=profile_update.avatar_url,
        bio=profile_update.bio,
        location=profile_update.location,
        website=profile_update.website,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.delete(
    "/profiles/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除用户资料",
    responses={
        (204): {"description": "用户删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
    },
)
async def delete_user_profile_by_id(
    id: int,
    current_user: UserInDB = Depends(get_current_user),
) -> None:
    """删除指定用户（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    if current_user.id == id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    success = await user_service.delete_user(user.username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete user"
        )

    # 记录活动日志
    _add_activity_log(
        user_id=id,
        username=user.username,
        action="delete_profile",
        resource_type="user",
        resource_id=str(id),
        details=f"Deleted user profile by {current_user.username}",
    )


# ============ Permissions Endpoints ============
@router.get(
    "/permissions",
    response_model=UserPermissionsResponse,
    summary="获取当前用户权限",
    responses={
        (200): {"description": "用户权限"},
        (401): {"description": "未授权"},
    },
)
async def get_user_permissions_endpoint(
    current_user: UserInDB = Depends(get_current_user),
) -> UserPermissionsResponse:
    """获取当前用户的权限列表"""
    user_id = current_user.id if current_user.id else 0
    permissions = _user_permissions.get(user_id, [])

    return UserPermissionsResponse(
        user_id=user_id,
        username=current_user.username,
        permissions=permissions,
    )


@router.get(
    "/permissions/{id}",
    response_model=UserPermissionsResponse,
    summary="获取指定用户权限",
    responses={
        (200): {"description": "用户权限"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
        (404): {"description": "用户不存在"},
    },
)
async def get_user_permissions_by_id(
    id: int,
    current_user: UserInDB = Depends(get_current_user),
) -> UserPermissionsResponse:
    """获取指定用户的权限列表（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    permissions = _user_permissions.get(id, [])

    return UserPermissionsResponse(
        user_id=id,
        username=user.username,
        permissions=permissions,
    )


# ============ Groups Endpoints ============
@router.get(
    "/groups",
    response_model=List[UserGroup],
    summary="获取用户组列表",
    responses={
        (200): {"description": "用户组列表"},
        (401): {"description": "未授权"},
    },
)
async def get_user_groups(
    current_user: UserInDB = Depends(get_current_user),
) -> List[UserGroup]:
    """获取所有用户组"""
    return _user_groups


@router.post(
    "/groups",
    response_model=UserGroup,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户组",
    responses={
        (201): {"description": "用户组创建成功"},
        (400): {"description": "无效的请求数据"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足"},
    },
)
async def create_user_group(
    group_create: UserGroupCreate,
    current_user: UserInDB = Depends(get_current_user),
) -> UserGroup:
    """创建新用户组（需要管理员权限）"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    new_group = UserGroup(
        id=len(_user_groups) + 1,
        name=group_create.name,
        description=group_create.description,
        member_count=0,
        created_at=datetime.now(),
    )

    _user_groups.append(new_group)

    # 记录活动日志
    _add_activity_log(
        user_id=current_user.id if current_user.id else 0,
        username=current_user.username,
        action="create_group",
        resource_type="group",
        resource_id=str(new_group.id),
        details=f"Created user group: {group_create.name}",
    )

    return new_group
