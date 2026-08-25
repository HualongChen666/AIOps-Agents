# -*- coding: utf-8 -*-
"""
Collaboration Advanced Router
协作高级路由

提供完整的团队协作API端点，包括团队、成员、权限、活动等功能。
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.api_response_standard import (
    ErrorCode,
    create_error_response,
    create_success_response,
)

router = APIRouter(prefix="/api/v1/collaboration", tags=["协作高级"])

# Data storage paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TEAMS_FILE = DATA_DIR / "collaboration_teams.json"
MEMBERS_FILE = DATA_DIR / "collaboration_members.json"
PERMISSIONS_FILE = DATA_DIR / "collaboration_permissions.json"
ACTIVITIES_FILE = DATA_DIR / "collaboration_activities.json"


# Pydantic Models
class TeamStatusEnum(str, Enum):
    """团队状态枚举"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class MemberRoleEnum(str, Enum):
    """成员角色枚举"""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class PermissionLevelEnum(str, Enum):
    """权限级别枚举"""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    FULL = "full"


class ActivityTypeEnum(str, Enum):
    """活动类型枚举"""

    TEAM_CREATED = "team_created"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    WORKSPACE_CREATED = "workspace_created"
    MESSAGE_POSTED = "message_posted"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"


class CreateTeamRequest(BaseModel):
    """创建团队请求"""

    name: str = Field(..., min_length=1, max_length=200, description="团队名称")
    description: Optional[str] = Field(None, max_length=1000, description="团队描述")
    owner_id: str = Field(..., min_length=1, max_length=100, description="所有者ID")
    status: TeamStatusEnum = Field(default=TeamStatusEnum.ACTIVE, description="团队状态")
    tags: List[str] = Field(default_factory=list, description="标签")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "SRE团队",
                "description": "负责系统可靠性工程",
                "owner_id": "user-001",
                "status": "active",
                "tags": ["sre", "operations"],
            }
        }
    }


class UpdateTeamRequest(BaseModel):
    """更新团队请求"""

    name: Optional[str] = Field(None, max_length=200, description="团队名称")
    description: Optional[str] = Field(None, max_length=1000, description="团队描述")
    status: Optional[TeamStatusEnum] = Field(None, description="团队状态")
    tags: Optional[List[str]] = Field(None, description="标签")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "SRE团队（更新）",
                "description": "负责系统可靠性工程和运维",
                "status": "active",
            }
        }
    }


class CreateMemberRequest(BaseModel):
    """创建成员请求"""

    user_id: str = Field(..., min_length=1, max_length=100, description="用户ID")
    user_name: str = Field(..., min_length=1, max_length=200, description="用户名称")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")
    team_id: str = Field(..., min_length=1, max_length=100, description="团队ID")
    role: MemberRoleEnum = Field(default=MemberRoleEnum.MEMBER, description="角色")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user-002",
                "user_name": "张三",
                "email": "zhangsan@example.com",
                "team_id": "team-001",
                "role": "member",
            }
        }
    }


class UpdateMemberRequest(BaseModel):
    """更新成员请求"""

    role: Optional[MemberRoleEnum] = Field(None, description="角色")
    email: Optional[str] = Field(None, max_length=255, description="邮箱")

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": "admin",
                "email": "zhangsan@example.com",
            }
        }
    }


class CreatePermissionRequest(BaseModel):
    """创建权限请求"""

    team_id: str = Field(..., min_length=1, max_length=100, description="团队ID")
    member_id: str = Field(..., min_length=1, max_length=100, description="成员ID")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., description="资源ID")
    permission_level: PermissionLevelEnum = Field(..., description="权限级别")

    model_config = {
        "json_schema_extra": {
            "example": {
                "team_id": "team-001",
                "member_id": "member-001",
                "resource_type": "workspace",
                "resource_id": "ws-001",
                "permission_level": "write",
            }
        }
    }


class CreateActivityRequest(BaseModel):
    """创建活动请求"""

    team_id: str = Field(..., min_length=1, max_length=100, description="团队ID")
    activity_type: ActivityTypeEnum = Field(..., description="活动类型")
    actor_id: str = Field(..., min_length=1, max_length=100, description="执行者ID")
    actor_name: str = Field(..., min_length=1, max_length=200, description="执行者名称")
    description: str = Field(..., min_length=1, max_length=1000, description="活动描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "team_id": "team-001",
                "activity_type": "member_added",
                "actor_id": "user-001",
                "actor_name": "李四",
                "description": "添加了新成员张三",
                "metadata": {"member_id": "member-002"},
            }
        }
    }


# Data storage helpers
def _load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """加载JSON文件"""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Failed to load JSON file {file_path}: {exc}")
        return []
    except Exception as e:  # noqa: F841 - Exception intentionally unused
        return []


def _save_json_file(file_path: Path, data: List[Dict[str, Any]]) -> None:
    """保存JSON文件"""
    import os
    import stat

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        # Set restrictive permissions for collaboration data file (600 - owner read/write only)
        try:
            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, AttributeError):
            # chmod may fail on Windows or non-Unix systems
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data: {str(e)}")


def _generate_id(prefix: str) -> str:
    """生成唯一ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _now() -> str:
    """获取当前时间戳"""
    return datetime.now(timezone.utc).isoformat()


def _log_activity(
    team_id: str,
    activity_type: ActivityTypeEnum,
    actor_id: str,
    actor_name: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """记录活动日志"""
    try:
        activities = _load_json_file(ACTIVITIES_FILE)
        activity = {
            "id": _generate_id("ACT"),
            "team_id": team_id,
            "activity_type": activity_type.value,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "description": description,
            "metadata": metadata or {},
            "created_at": _now(),
        }
        activities.append(activity)
        _save_json_file(ACTIVITIES_FILE, activities)
    except Exception as e:  # noqa: F841 - Exception intentionally unused
        # 记录失败不影响主流程
        pass


# Team endpoints
@router.get(
    "/teams",
    summary="获取团队列表",
    responses={
        200: {"description": "团队列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_teams(
    status: Optional[TeamStatusEnum] = Query(None, description="按状态筛选"),
    owner_id: Optional[str] = Query(None, description="按所有者筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取团队列表

    支持按状态和所有者筛选，支持分页。
    """
    try:
        teams = _load_json_file(TEAMS_FILE)

        # 过滤
        if status:
            teams = [t for t in teams if t.get("status") == status.value]
        if owner_id:
            teams = [t for t in teams if t.get("owner_id") == owner_id]

        # 分页
        total = len(teams)
        paginated = teams[offset : offset + limit]

        # 为每个团队添加成员数量
        members = _load_json_file(MEMBERS_FILE)
        for team in paginated:
            team_id = team.get("id")
            member_count = sum(1 for m in members if m.get("team_id") == team_id)
            team["member_count"] = member_count

        return create_success_response(
            {
                "items": paginated,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取团队列表失败"
        )


@router.post(
    "/teams",
    summary="创建团队",
    status_code=201,
    responses={
        201: {"description": "团队创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_team(request: CreateTeamRequest) -> Dict[str, Any]:
    """
    创建新的团队

    创建一个协作团队，指定所有者和初始状态。
    """
    try:
        teams = _load_json_file(TEAMS_FILE)

        team = {
            "id": _generate_id("TM"),
            "name": request.name,
            "description": request.description,
            "owner_id": request.owner_id,
            "status": request.status.value,
            "tags": request.tags,
            "created_at": _now(),
            "updated_at": _now(),
        }

        teams.append(team)
        _save_json_file(TEAMS_FILE, teams)

        # 记录活动
        _log_activity(
            team_id=team["id"],
            activity_type=ActivityTypeEnum.TEAM_CREATED,
            actor_id=request.owner_id,
            actor_name="System",
            description=f"创建了团队 {request.name}",
            metadata={"team_name": request.name},
        )

        return create_success_response(team, "团队创建成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建团队失败"
        )


@router.get(
    "/teams/{team_id}",
    summary="获取团队详情",
    responses={
        200: {"description": "团队详情"},
        404: {"description": "团队不存在"},
        500: {"description": "服务器错误"},
    },
)
async def get_team(team_id: str) -> Dict[str, Any]:
    """
    获取指定团队的详细信息

    根据团队ID获取团队的完整配置和成员信息。
    """
    try:
        teams = _load_json_file(TEAMS_FILE)
        team = next((t for t in teams if t.get("id") == team_id), None)

        if not team:
            return create_error_response(
                error=f"Team {team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        # 获取团队成员
        members = _load_json_file(MEMBERS_FILE)
        team_members = [m for m in members if m.get("team_id") == team_id]
        team["members"] = team_members
        team["member_count"] = len(team_members)

        return create_success_response(team)
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取团队详情失败"
        )


@router.patch(
    "/teams/{team_id}",
    summary="更新团队",
    responses={
        200: {"description": "团队更新成功"},
        404: {"description": "团队不存在"},
        500: {"description": "服务器错误"},
    },
)
async def update_team(team_id: str, request: UpdateTeamRequest) -> Dict[str, Any]:
    """
    更新团队配置

    更新团队的名称、描述、状态等信息。
    """
    try:
        teams = _load_json_file(TEAMS_FILE)
        team = next((t for t in teams if t.get("id") == team_id), None)

        if not team:
            return create_error_response(
                error=f"Team {team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        # 更新字段
        if request.name is not None:
            team["name"] = request.name
        if request.description is not None:
            team["description"] = request.description
        if request.status is not None:
            team["status"] = request.status.value
        if request.tags is not None:
            team["tags"] = request.tags

        team["updated_at"] = _now()

        _save_json_file(TEAMS_FILE, teams)

        return create_success_response(team, "团队更新成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="更新团队失败"
        )


@router.delete(
    "/teams/{team_id}",
    summary="删除团队",
    responses={
        200: {"description": "团队删除成功"},
        404: {"description": "团队不存在"},
        500: {"description": "服务器错误"},
    },
)
async def delete_team(team_id: str) -> Dict[str, Any]:
    """
    删除团队

    根据团队ID删除团队配置。
    """
    try:
        teams = _load_json_file(TEAMS_FILE)
        team = next((t for t in teams if t.get("id") == team_id), None)

        if not team:
            return create_error_response(
                error=f"Team {team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        teams = [t for t in teams if t.get("id") != team_id]
        _save_json_file(TEAMS_FILE, teams)

        # 同时删除相关成员
        members = _load_json_file(MEMBERS_FILE)
        members = [m for m in members if m.get("team_id") != team_id]
        _save_json_file(MEMBERS_FILE, members)

        # 删除相关权限
        permissions = _load_json_file(PERMISSIONS_FILE)
        permissions = [p for p in permissions if p.get("team_id") != team_id]
        _save_json_file(PERMISSIONS_FILE, permissions)

        return create_success_response({"id": team_id}, "团队删除成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="删除团队失败"
        )


# Member endpoints
@router.get(
    "/members",
    summary="获取成员列表",
    responses={
        200: {"description": "成员列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_members(
    team_id: Optional[str] = Query(None, description="按团队ID筛选"),
    role: Optional[MemberRoleEnum] = Query(None, description="按角色筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取成员列表

    支持按团队和角色筛选，支持分页。
    """
    try:
        members = _load_json_file(MEMBERS_FILE)

        # 过滤
        if team_id:
            members = [m for m in members if m.get("team_id") == team_id]
        if role:
            members = [m for m in members if m.get("role") == role.value]

        # 分页
        total = len(members)
        paginated = members[offset : offset + limit]

        return create_success_response(
            {
                "items": paginated,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取成员列表失败"
        )


@router.post(
    "/members",
    summary="创建成员",
    status_code=201,
    responses={
        201: {"description": "成员创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_member(request: CreateMemberRequest) -> Dict[str, Any]:
    """
    创建新的团队成员

    将用户添加到团队中，指定其角色。
    """
    try:
        # 验证团队是否存在
        teams = _load_json_file(TEAMS_FILE)
        team = next((t for t in teams if t.get("id") == request.team_id), None)
        if not team:
            return create_error_response(
                error=f"Team {request.team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        members = _load_json_file(MEMBERS_FILE)

        # 检查用户是否已在团队中
        for member in members:
            if (
                member.get("user_id") == request.user_id
                and member.get("team_id") == request.team_id
            ):
                return create_error_response(
                    error="User already in team",
                    error_code=ErrorCode.BAD_REQUEST,
                    message="用户已在团队中",
                )

        member = {
            "id": _generate_id("MBR"),
            "user_id": request.user_id,
            "user_name": request.user_name,
            "email": request.email,
            "team_id": request.team_id,
            "role": request.role.value,
            "joined_at": _now(),
            "updated_at": _now(),
        }

        members.append(member)
        _save_json_file(MEMBERS_FILE, members)

        # 记录活动
        _log_activity(
            team_id=request.team_id,
            activity_type=ActivityTypeEnum.MEMBER_ADDED,
            actor_id=request.user_id,
            actor_name=request.user_name,
            description=f"添加了成员 {request.user_name}",
            metadata={"member_id": member["id"]},
        )

        return create_success_response(member, "成员创建成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建成员失败"
        )


@router.patch(
    "/members/{member_id}",
    summary="更新成员",
    responses={
        200: {"description": "成员更新成功"},
        404: {"description": "成员不存在"},
        500: {"description": "服务器错误"},
    },
)
async def update_member(member_id: str, request: UpdateMemberRequest) -> Dict[str, Any]:
    """
    更新成员信息

    更新成员的角色和邮箱等信息。
    """
    try:
        members = _load_json_file(MEMBERS_FILE)
        member = next((m for m in members if m.get("id") == member_id), None)

        if not member:
            return create_error_response(
                error=f"Member {member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        # 更新字段
        if request.role is not None:
            member["role"] = request.role.value
        if request.email is not None:
            member["email"] = request.email

        member["updated_at"] = _now()

        _save_json_file(MEMBERS_FILE, members)

        return create_success_response(member, "成员更新成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="更新成员失败"
        )


@router.delete(
    "/members/{member_id}",
    summary="删除成员",
    responses={
        200: {"description": "成员删除成功"},
        404: {"description": "成员不存在"},
        500: {"description": "服务器错误"},
    },
)
async def delete_member(member_id: str) -> Dict[str, Any]:
    """
    删除成员

    从团队中移除成员。
    """
    try:
        members = _load_json_file(MEMBERS_FILE)
        member = next((m for m in members if m.get("id") == member_id), None)

        if not member:
            return create_error_response(
                error=f"Member {member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        team_id = member.get("team_id")
        user_name = member.get("user_name")

        members = [m for m in members if m.get("id") != member_id]
        _save_json_file(MEMBERS_FILE, members)

        # 删除相关权限
        permissions = _load_json_file(PERMISSIONS_FILE)
        permissions = [p for p in permissions if p.get("member_id") != member_id]
        _save_json_file(PERMISSIONS_FILE, permissions)

        # 记录活动
        _log_activity(
            team_id=team_id,
            activity_type=ActivityTypeEnum.MEMBER_REMOVED,
            actor_id="system",
            actor_name="System",
            description=f"移除了成员 {user_name}",
            metadata={"member_id": member_id},
        )

        return create_success_response({"id": member_id}, "成员删除成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="删除成员失败"
        )


# Permission endpoints
@router.get(
    "/permissions",
    summary="获取权限列表",
    responses={
        200: {"description": "权限列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_permissions(
    team_id: Optional[str] = Query(None, description="按团队ID筛选"),
    member_id: Optional[str] = Query(None, description="按成员ID筛选"),
    resource_type: Optional[str] = Query(None, description="按资源类型筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
) -> Dict[str, Any]:
    """
    获取权限列表

    支持按团队、成员和资源类型筛选。
    """
    try:
        permissions = _load_json_file(PERMISSIONS_FILE)

        # 过滤
        if team_id:
            permissions = [p for p in permissions if p.get("team_id") == team_id]
        if member_id:
            permissions = [p for p in permissions if p.get("member_id") == member_id]
        if resource_type:
            permissions = [p for p in permissions if p.get("resource_type") == resource_type]

        paginated = permissions[:limit]

        return create_success_response(
            {
                "items": paginated,
                "total": len(permissions),
                "limit": limit,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取权限列表失败"
        )


@router.post(
    "/permissions",
    summary="创建权限",
    status_code=201,
    responses={
        201: {"description": "权限创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器错误"},
    },
)
async def create_permission(request: CreatePermissionRequest) -> Dict[str, Any]:
    """
    创建新的权限

    为团队成员分配对特定资源的访问权限。
    """
    try:
        # 验证团队和成员是否存在
        teams = _load_json_file(TEAMS_FILE)
        team = next((t for t in teams if t.get("id") == request.team_id), None)
        if not team:
            return create_error_response(
                error=f"Team {request.team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        members = _load_json_file(MEMBERS_FILE)
        member = next((m for m in members if m.get("id") == request.member_id), None)
        if not member:
            return create_error_response(
                error=f"Member {request.member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        permissions = _load_json_file(PERMISSIONS_FILE)

        # 检查权限是否已存在
        for perm in permissions:
            if (
                perm.get("member_id") == request.member_id
                and perm.get("resource_type") == request.resource_type
                and perm.get("resource_id") == request.resource_id
            ):
                return create_error_response(
                    error="Permission already exists",
                    error_code=ErrorCode.BAD_REQUEST,
                    message="权限已存在",
                )

        permission = {
            "id": _generate_id("PRM"),
            "team_id": request.team_id,
            "member_id": request.member_id,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "permission_level": request.permission_level.value,
            "created_at": _now(),
            "updated_at": _now(),
        }

        permissions.append(permission)
        _save_json_file(PERMISSIONS_FILE, permissions)

        # 记录活动
        _log_activity(
            team_id=request.team_id,
            activity_type=ActivityTypeEnum.PERMISSION_GRANTED,
            actor_id="system",
            actor_name="System",
            description=f"授予了权限 {request.permission_level.value}",
            metadata={
                "member_id": request.member_id,
                "resource_type": request.resource_type,
                "resource_id": request.resource_id,
            },
        )

        return create_success_response(permission, "权限创建成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="创建权限失败"
        )


@router.delete(
    "/permissions/{permission_id}",
    summary="删除权限",
    responses={
        200: {"description": "权限删除成功"},
        404: {"description": "权限不存在"},
        500: {"description": "服务器错误"},
    },
)
async def delete_permission(permission_id: str) -> Dict[str, Any]:
    """
    删除权限

    撤销成员对特定资源的访问权限。
    """
    try:
        permissions = _load_json_file(PERMISSIONS_FILE)
        permission = next((p for p in permissions if p.get("id") == permission_id), None)

        if not permission:
            return create_error_response(
                error=f"Permission {permission_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="权限不存在",
            )

        team_id = permission.get("team_id")

        permissions = [p for p in permissions if p.get("id") != permission_id]
        _save_json_file(PERMISSIONS_FILE, permissions)

        # 记录活动
        _log_activity(
            team_id=team_id,
            activity_type=ActivityTypeEnum.PERMISSION_REVOKED,
            actor_id="system",
            actor_name="System",
            description=f"撤销了权限",
            metadata={"permission_id": permission_id},
        )

        return create_success_response({"id": permission_id}, "权限删除成功")
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="删除权限失败"
        )


# Activity endpoints
@router.get(
    "/activities",
    summary="获取活动列表",
    responses={
        200: {"description": "活动列表"},
        500: {"description": "服务器错误"},
    },
)
async def get_activities(
    team_id: Optional[str] = Query(None, description="按团队ID筛选"),
    activity_type: Optional[ActivityTypeEnum] = Query(None, description="按活动类型筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取活动列表

    支持按团队和活动类型筛选，支持分页。
    """
    try:
        activities = _load_json_file(ACTIVITIES_FILE)

        # 过滤
        if team_id:
            activities = [a for a in activities if a.get("team_id") == team_id]
        if activity_type:
            activities = [a for a in activities if a.get("activity_type") == activity_type.value]

        # 按时间倒序排序
        activities.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 分页
        total = len(activities)
        paginated = activities[offset : offset + limit]

        return create_success_response(
            {
                "items": paginated,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取活动列表失败"
        )
