# -*- coding: utf-8 -*-
"""
Collaboration Advanced Router
协作高级路由

提供完整的团队协作API端点，包括团队、成员、权限、活动等功能。
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.api_response_standard import (
    ErrorCode,
    create_error_response,
    create_success_response,
)
from core.database import get_db
from core.models import (
    CollaborationTeamDB,
    CollaborationMemberDB,
    CollaborationPermissionDB,
    CollaborationActivityDB,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collaboration", tags=["协作高级"])


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



def _now() -> str:
    """获取当前时间戳"""
    return datetime.now(timezone.utc).isoformat()


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
    db: Session = None,
) -> None:
    """记录活动日志"""
    try:
        if db is None:
            return
            
        activity = CollaborationActivityDB(
            id=_generate_id("ACT"),
            team_id=team_id,
            activity_type=activity_type.value,
            actor_id=actor_id,
            actor_name=actor_name,
            description=description,
            metadata=metadata or {},
        )
        db.add(activity)
        db.commit()
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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取团队列表

    支持按状态和所有者筛选，支持分页。
    """
    try:
        # Try to get teams from database
        query = db.query(CollaborationTeamDB)
        
        # Filter by status
        if status:
            query = query.filter(CollaborationTeamDB.team_status == status.value)
        
        # Filter by owner
        if owner_id:
            query = query.filter(CollaborationTeamDB.team_lead_id == owner_id)
        
        # Pagination
        teams = query.offset(offset).limit(limit).all()
        
        # Convert to response format
        team_list = [
            {
                "id": str(team.id),
                "name": team.team_name,
                "description": team.team_description,
                "status": team.team_status,
                "owner_id": team.team_lead_id,
                "tags": team.team_metadata.get("tags", []) if team.team_metadata else [],
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None,
            }
            for team in teams
        ]
        
        return create_success_response(data={"teams": team_list, "total": len(team_list)})
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="获取团队列表失败",
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
async def create_team(request: CreateTeamRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    创建新的团队

    创建一个协作团队，指定所有者和初始状态。
    """
    try:
        # Try to create team in database
        team_id = _generate_id("TM")
        new_team = CollaborationTeamDB(
            id=team_id,
            team_name=request.name,
            team_description=request.description,
            team_status=request.status.value,
            team_lead_id=request.owner_id,
            team_metadata={"tags": request.tags},
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        
        team_data = {
            "id": str(new_team.id),
            "name": new_team.team_name,
            "description": new_team.team_description,
            "status": new_team.team_status,
            "owner_id": new_team.team_lead_id,
            "tags": new_team.team_metadata.get("tags", []) if new_team.team_metadata else [],
            "created_at": new_team.created_at.isoformat() if new_team.created_at else None,
            "updated_at": new_team.updated_at.isoformat() if new_team.updated_at else None,
        }
        
        return create_success_response(data=team_data, status_code=201)
        
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        return create_error_response(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="创建团队失败",
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
        db = next(get_db())
        try:
            team = db.query(CollaborationTeamDB).filter(
                CollaborationTeamDB.id == team_id
            ).first()
            
            if not team:
                return create_error_response(
                    error=f"Team {team_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="团队不存在",
                )
            
            # 获取团队成员
            members = db.query(CollaborationMemberDB).filter(
                CollaborationMemberDB.team_id == team_id
            ).all()
            
            team_data = {
                "id": str(team.id),
                "name": team.team_name,
                "description": team.team_description,
                "status": team.team_status,
                "owner_id": team.team_lead_id,
                "tags": team.team_metadata.get("tags", []) if team.team_metadata else [],
                "members": [
                    {
                        "id": str(m.id),
                        "user_id": m.user_id,
                        "user_name": m.user_name,
                        "role": m.role,
                    }
                    for m in members
                ],
                "member_count": len(members),
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None,
            }
            
            return create_success_response(team_data)
        finally:
            db.close()
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
        db = next(get_db())
        try:
            team = db.query(CollaborationTeamDB).filter(
                CollaborationTeamDB.id == team_id
            ).first()
            
            if not team:
                return create_error_response(
                    error=f"Team {team_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="团队不存在",
                )
            
            # 更新字段
            if request.name is not None:
                team.team_name = request.name
            if request.description is not None:
                team.team_description = request.description
            if request.status is not None:
                team.team_status = request.status.value
            if request.tags is not None:
                if team.team_metadata is None:
                    team.team_metadata = {}
                team.team_metadata["tags"] = request.tags
            
            team.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            team_data = {
                "id": str(team.id),
                "name": team.team_name,
                "description": team.team_description,
                "status": team.team_status,
                "owner_id": team.team_lead_id,
                "tags": team.team_metadata.get("tags", []) if team.team_metadata else [],
                "updated_at": team.updated_at.isoformat() if team.updated_at else None,
            }
            
            return create_success_response(team_data, "团队更新成功")
        finally:
            db.close()
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
        db = next(get_db())
        try:
            team = db.query(CollaborationTeamDB).filter(
                CollaborationTeamDB.id == team_id
            ).first()
            
            if not team:
                return create_error_response(
                    error=f"Team {team_id} not found",
                    error_code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="团队不存在",
                )
            
            # 删除相关成员
            db.query(CollaborationMemberDB).filter(
                CollaborationMemberDB.team_id == team_id
            ).delete()
            
            # 删除相关权限
            db.query(CollaborationPermissionDB).filter(
                CollaborationPermissionDB.team_id == team_id
            ).delete()
            
            # 删除团队
            db.delete(team)
            db.commit()
            
            return create_success_response({"id": team_id}, "团队删除成功")
        finally:
            db.close()
    except Exception as e:

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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取成员列表

    支持按团队和角色筛选，支持分页。
    """
    try:
        query = db.query(CollaborationMemberDB)
        
        # 过滤
        if team_id:
            query = query.filter(CollaborationMemberDB.team_id == team_id)
        if role:
            query = query.filter(CollaborationMemberDB.role == role.value)

        # 分页
        total = query.count()
        members = query.offset(offset).limit(limit).all()

        return create_success_response(
            {
                "items": [
                    {
                        "id": str(member.id),
                        "team_id": member.team_id,
                        "user_id": member.user_id,
                        "user_name": member.user_name,
                        "role": member.role,
                        "status": member.status,
                        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    }
                    for member in members
                ],
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
async def create_member(request: CreateMemberRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    创建新的团队成员

    将用户添加到团队中，指定其角色。
    """
    try:
        # 验证团队是否存在
        team = db.query(CollaborationTeamDB).filter(CollaborationTeamDB.id == request.team_id).first()
        if not team:
            return create_error_response(
                error=f"Team {request.team_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="团队不存在",
            )

        # 检查成员是否已存在
        existing_member = db.query(CollaborationMemberDB).filter(
            CollaborationMemberDB.team_id == request.team_id,
            CollaborationMemberDB.user_id == request.user_id
        ).first()
        if existing_member:
            return create_error_response(
                error="Member already exists in team",
                error_code=ErrorCode.DUPLICATE_RESOURCE,
                message="成员已存在于团队中",
            )

        # 创建新成员
        member_id = str(uuid.uuid4())
        new_member = CollaborationMemberDB(
            id=member_id,
            team_id=request.team_id,
            user_id=request.user_id,
            user_name=request.user_name,
            role=request.role,
            status="active",
            joined_at=datetime.utcnow(),
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)

        return create_success_response(
            {
                "id": str(new_member.id),
                "team_id": new_member.team_id,
                "user_id": new_member.user_id,
                "user_name": new_member.user_name,
                "role": new_member.role,
                "status": new_member.status,
                "joined_at": new_member.joined_at.isoformat() if new_member.joined_at else None,
            },
            status_code=201,
        )
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
async def update_member(member_id: str, request: UpdateMemberRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    更新成员信息

    更新成员的角色和邮箱等信息。
    """
    try:
        member = db.query(CollaborationMemberDB).filter(CollaborationMemberDB.id == member_id).first()

        if not member:
            return create_error_response(
                error=f"Member {member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        # 更新字段
        if request.role is not None:
            member.role = request.role.value
        if request.email is not None:
            member.email = request.email

        member.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(member)

        return create_success_response(
            {
                "id": str(member.id),
                "team_id": member.team_id,
                "user_id": member.user_id,
                "user_name": member.user_name,
                "role": member.role,
                "status": member.status,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            },
            "成员更新成功"
        )
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
async def delete_member(member_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除成员

    从团队中移除成员。
    """
    try:
        member = db.query(CollaborationMemberDB).filter(CollaborationMemberDB.id == member_id).first()

        if not member:
            return create_error_response(
                error=f"Member {member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        team_id = member.team_id
        user_name = member.user_name

        # 删除相关权限
        db.query(CollaborationPermissionDB).filter(CollaborationPermissionDB.member_id == member_id).delete()

        # 删除成员
        db.delete(member)
        db.commit()

        # 记录活动
        _log_activity(
            team_id=team_id,
            activity_type=ActivityTypeEnum.MEMBER_REMOVED,
            actor_id="system",
            actor_name="System",
            description=f"移除了成员 {user_name}",
            metadata={"member_id": member_id},
            db=db,
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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取权限列表

    支持按团队、成员和资源类型筛选。
    """
    try:
        query = db.query(CollaborationPermissionDB)

        # 过滤
        if team_id:
            query = query.filter(CollaborationPermissionDB.team_id == team_id)
        if member_id:
            query = query.filter(CollaborationPermissionDB.member_id == member_id)
        if resource_type:
            query = query.filter(CollaborationPermissionDB.resource_type == resource_type)

        permissions = query.limit(limit).all()

        return create_success_response(
            {
                "items": [
                    {
                        "id": str(permission.id),
                        "team_id": permission.team_id,
                        "member_id": permission.member_id,
                        "resource_type": permission.resource_type,
                        "resource_id": permission.resource_id,
                        "permission_level": permission.permission_level,
                        "granted_at": permission.granted_at.isoformat() if permission.granted_at else None,
                    }
                    for permission in permissions
                ],
                "total": len(permissions),
                "limit": limit,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取权限列表失败"
        )

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
async def create_permission(request: CreatePermissionRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    创建新的权限

    为团队成员分配对特定资源的访问权限。
    """
    try:
        # 验证成员是否存在
        member = db.query(CollaborationMemberDB).filter(CollaborationMemberDB.id == request.member_id).first()
        if not member:
            return create_error_response(
                error=f"Member {request.member_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="成员不存在",
            )

        # 检查权限是否已存在
        existing_permission = db.query(CollaborationPermissionDB).filter(
            CollaborationPermissionDB.member_id == request.member_id,
            CollaborationPermissionDB.resource_type == request.resource_type,
            CollaborationPermissionDB.resource_id == request.resource_id
        ).first()
        if existing_permission:
            return create_error_response(
                error="Permission already exists",
                error_code=ErrorCode.DUPLICATE_RESOURCE,
                message="权限已存在",
            )

        # 创建新权限
        permission_id = str(uuid.uuid4())
        new_permission = CollaborationPermissionDB(
            id=permission_id,
            team_id=request.team_id,
            member_id=request.member_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            permission_level=request.permission_level.value,
            granted_at=datetime.utcnow(),
        )
        db.add(new_permission)
        db.commit()
        db.refresh(new_permission)

        return create_success_response(
            {
                "id": str(new_permission.id),
                "team_id": new_permission.team_id,
                "member_id": new_permission.member_id,
                "resource_type": new_permission.resource_type,
                "resource_id": new_permission.resource_id,
                "permission_level": new_permission.permission_level,
                "granted_at": new_permission.granted_at.isoformat() if new_permission.granted_at else None,
            },
            "权限创建成功",
            status_code=201,
        )
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
async def delete_permission(permission_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除权限

    撤销成员对特定资源的访问权限。
    """
    try:
        permission = db.query(CollaborationPermissionDB).filter(CollaborationPermissionDB.id == permission_id).first()

        if not permission:
            return create_error_response(
                error=f"Permission {permission_id} not found",
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="权限不存在",
            )

        team_id = permission.team_id

        db.delete(permission)
        db.commit()

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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    获取活动列表

    支持按团队和活动类型筛选，支持分页。
    """
    try:
        query = db.query(CollaborationActivityDB)

        # 过滤
        if team_id:
            query = query.filter(CollaborationActivityDB.team_id == team_id)
        if activity_type:
            query = query.filter(CollaborationActivityDB.activity_type == activity_type.value)

        # 按时间倒序排序
        query = query.order_by(CollaborationActivityDB.created_at.desc())

        # 分页
        total = query.count()
        activities = query.offset(offset).limit(limit).all()

        return create_success_response(
            {
                "items": [
                    {
                        "id": str(activity.id),
                        "team_id": activity.team_id,
                        "activity_type": activity.activity_type,
                        "actor_id": activity.actor_id,
                        "actor_name": activity.actor_name,
                        "description": activity.description,
                        "metadata": activity.metadata,
                        "created_at": activity.created_at.isoformat() if activity.created_at else None,
                    }
                    for activity in activities
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        return create_error_response(
            error=str(e), error_code=ErrorCode.INTERNAL_ERROR, message="获取活动列表失败"
        )
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
