# -*- coding: utf-8 -*-
"""qdrant_router.py

FastAPI 路由，封装对 Qdrant 向量库的 CRUD 操作。
所有端点均受 JWT 鉴权（admin 或 user 均可），
并返回结构化 JSON。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.authentication import get_current_active_user, role_required
from core.qdrant_service import (
    create_collection,
    delete_collection,
    delete_points,
    health_check,
    list_collections,
    search,
    upsert_points,
)

router = APIRouter(prefix="/api/qdrant", tags=["qdrant"])


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="集合名称（全局唯一）")
    vector_size: int = Field(..., gt=0, description="向量维度")
    distance: str = Field("Cosine", description="距离度量：Cosine、Euclid、Dot")

    @field_validator("distance")
    @classmethod
    def _check_distance(cls, v: str) -> str:
        allowed = {"Cosine", "Euclid", "Dot"}
        if v not in allowed:
            raise ValueError(f"distance 必须是 {allowed} 之一")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"name": "example", "vector_size": 0, "distance": "example"}
        },
    }


class PointModel(BaseModel):
    id: Any = Field(..., description="向量点的唯一标识（int 或 str）")
    vector: List[float] = Field(..., description="向量列表")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        if len(v) < 1:
            raise ValueError("vector must have at least 1 element")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"id": None, "vector": [], "payload": "example"}},
    }


class UpsertPointsRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    points: List[PointModel]

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "points": []}},
    }


class SearchRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    query_vector: List[float] = Field(..., description="查询向量")
    top_k: int = Field(5, gt=0, description="返回最近邻的数量")
    filter: Optional[Dict[str, Any]] = Field(
        None, description="可选的过滤条件（Qdrant filter DSL）"
    )

    @field_validator("query_vector")
    @classmethod
    def validate_query_vector(cls, v: List[float]) -> List[float]:
        if len(v) < 1:
            raise ValueError("query_vector must have at least 1 element")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "collection": "example",
                "query_vector": [],
                "top_k": 0,
                "filter": "example",
            }
        },
    }


class DeletePointsRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    ids: List[Any] = Field(..., description="要删除的点的 ID 列表")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "ids": []}},
    }


@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Qdrant健康检查",
    responses={
        (200): {
            "description": "健康状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "version": "1.7.0",
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (503): {"description": "Qdrant服务不可用"},
    },
)
async def qdrant_health(user=Depends(get_current_active_user)):
    """返回 Qdrant 健康状态"""
    return health_check()


@router.get(
    "/collections",
    response_model=List[Dict[str, Any]],
    summary="获取所有集合",
    responses={
        (200): {
            "description": "集合列表",
            "content": {
                "application/json": {
                    "example": [
                        {"name": "test_collection", "vector_size": 768, "points_count": 1000}
                    ]
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def get_collections(user=Depends(get_current_active_user)):
    return list_collections()


@router.post(
    "/collections",
    response_model=Dict[str, Any],
    summary="创建集合",
    responses={
        (200): {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {"status": "success", "collection_name": "test_collection"}
                }
            },
        },
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "创建失败"},
    },
)
async def post_collection(
    payload: CreateCollectionRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        return create_collection(
            name=payload.name, vector_size=payload.vector_size, distance=payload.distance
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/collections/{name}",
    response_model=Dict[str, Any],
    summary="删除集合",
    responses={
        (200): {
            "description": "删除成功",
            "content": {
                "application/json": {
                    "example": {"status": "success", "collection_name": "test_collection"}
                }
            },
        },
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (404): {"description": "集合不存在"},
        (500): {"description": "删除失败"},
    },
)
async def delete_collection_endpoint(
    name: str, user=Depends(get_current_active_user), admin=Depends(role_required("admin"))
):
    try:
        return delete_collection(name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/points",
    response_model=Dict[str, Any],
    summary="插入或更新向量点",
    responses={
        (200): {
            "description": "操作成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "operation_id": "op-123",
                        "upserted_count": 10,
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "操作失败"},
    },
)
async def upsert_points_endpoint(
    payload: UpsertPointsRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        points = [p.model_dump() for p in payload.points]
        return upsert_points(collection=payload.collection, points=points)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/search",
    response_model=List[Dict[str, Any]],
    summary="向量搜索",
    responses={
        (200): {
            "description": "搜索结果",
            "content": {
                "application/json": {
                    "example": [{"id": 1, "score": 0.95, "payload": {"text": "sample text"}}]
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "搜索失败"},
    },
)
async def search_endpoint(payload: SearchRequest, user=Depends(get_current_active_user)):
    try:
        return search(
            collection=payload.collection,
            query_vector=payload.query_vector,
            top_k=payload.top_k,
            filter=payload.filter,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/points",
    response_model=Dict[str, Any],
    summary="删除向量点",
    responses={
        (200): {"description": "删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "删除失败"},
    },
)
async def delete_points_endpoint(
    payload: DeletePointsRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        return delete_points(collection=payload.collection, ids=payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
