# -*- coding: utf-8 -*-
"""qdrant_router.py

FastAPI 路由，封装对 Qdrant 向量库的 CRUD 操作。
所有端点均受 JWT 鉴权（admin 或 user 均可），
并返回结构化 JSON。
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from core.authentication import get_current_active_user, role_required
from core.qdrant_service import (
    create_collection,
    delete_collection,
    delete_points,
    get_collection_info,
    get_point_count,
    get_vector_stats,
    health_check,
    list_collections,
    search,
    search_hybrid,
    search_multi_vector,
    upsert_points,
    upsert_points_batch,
    clear_collection,
    update_collection_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vector", tags=["qdrant"])


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


class BatchUpsertRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    points: List[PointModel]
    batch_size: int = Field(100, gt=0, le=1000, description="批量处理大小")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "points": [], "batch_size": 100}},
    }


class BatchDeleteRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    ids: List[Any]
    batch_size: int = Field(100, gt=0, le=1000, description="批量处理大小")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "ids": [], "batch_size": 100}},
    }


class UpdatePointsRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    points: List[PointModel]

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "points": []}},
    }


class HybridSearchRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    query_vector: List[float] = Field(..., description="查询向量")
    query_text: str = Field(..., description="查询文本")
    top_k: int = Field(5, gt=0, description="返回结果数量")
    alpha: float = Field(0.7, ge=0, le=1, description="向量与文本权重平衡")

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
                "query_text": "example",
                "top_k": 5,
                "alpha": 0.7,
            }
        },
    }


class MultiVectorSearchRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    query_vectors: List[List[float]] = Field(..., description="多个查询向量")
    weights: Optional[List[float]] = Field(None, description="各向量的权重")
    top_k: int = Field(5, gt=0, description="返回结果数量")

    @field_validator("query_vectors")
    @classmethod
    def validate_query_vectors(cls, v: List[List[float]]) -> List[List[float]]:
        if len(v) < 1:
            raise ValueError("query_vectors must have at least 1 vector")
        for vec in v:
            if len(vec) < 1:
                raise ValueError("each query_vector must have at least 1 element")
        return v

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {
                "collection": "example",
                "query_vectors": [[]],
                "weights": [1.0],
                "top_k": 5,
            }
        },
    }


class CollectionConfigRequest(BaseModel):
    collection: str = Field(..., description="集合名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="配置参数")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "params": {}}},
    }


class GetPointRequest(BaseModel):
    collection: str = Field(..., description="目标集合名称")
    id: Any = Field(..., description="向量点ID")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"collection": "example", "id": 1}},
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
        logger.error(f"Error deleting points from {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# 批量操作端点
@router.post(
    "/points/batch",
    response_model=Dict[str, Any],
    summary="批量插入或更新向量点",
    responses={
        (200): {"description": "批量操作成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "操作失败"},
    },
)
async def batch_upsert_points_endpoint(
    payload: BatchUpsertRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        points = [p.model_dump() for p in payload.points]
        return upsert_points_batch(
            collection=payload.collection,
            points=points,
            batch_size=payload.batch_size,
        )
    except Exception as exc:
        logger.error(f"Error batch upserting points to {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/points/batch",
    response_model=Dict[str, Any],
    summary="批量删除向量点",
    responses={
        (200): {"description": "批量删除成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "删除失败"},
    },
)
async def batch_delete_points_endpoint(
    payload: BatchDeleteRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        return delete_points(collection=payload.collection, ids=payload.ids)
    except Exception as exc:
        logger.error(f"Error batch deleting points from {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put(
    "/points",
    response_model=Dict[str, Any],
    summary="更新向量点",
    responses={
        (200): {"description": "更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "更新失败"},
    },
)
async def update_points_endpoint(
    payload: UpdatePointsRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        points = [p.model_dump() for p in payload.points]
        return upsert_points(collection=payload.collection, points=points)
    except Exception as exc:
        logger.error(f"Error updating points in {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# 高级检索端点
@router.post(
    "/search/hybrid",
    response_model=List[Dict[str, Any]],
    summary="混合搜索(向量+关键词)",
    responses={
        (200): {"description": "混合搜索结果"},
        (401): {"description": "未授权"},
        (500): {"description": "搜索失败"},
    },
)
async def hybrid_search_endpoint(
    payload: HybridSearchRequest,
    user=Depends(get_current_active_user),
):
    try:
        return search_hybrid(
            collection=payload.collection,
            query_vector=payload.query_vector,
            query_text=payload.query_text,
            top_k=payload.top_k,
            alpha=payload.alpha,
        )
    except Exception as exc:
        logger.error(f"Error in hybrid search for {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/search/multi-vector",
    response_model=List[Dict[str, Any]],
    summary="多向量搜索",
    responses={
        (200): {"description": "多向量搜索结果"},
        (401): {"description": "未授权"},
        (500): {"description": "搜索失败"},
    },
)
async def multi_vector_search_endpoint(
    payload: MultiVectorSearchRequest,
    user=Depends(get_current_active_user),
):
    try:
        return search_multi_vector(
            collection=payload.collection,
            query_vectors=payload.query_vectors,
            weights=payload.weights,
            top_k=payload.top_k,
        )
    except Exception as exc:
        logger.error(f"Error in multi-vector search for {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# 集合管理端点
@router.get(
    "/collections/{name}/info",
    response_model=Dict[str, Any],
    summary="获取集合详情",
    responses={
        (200): {"description": "集合详情"},
        (401): {"description": "未授权"},
        (404): {"description": "集合不存在"},
        (500): {"description": "获取失败"},
    },
)
async def get_collection_info_endpoint(
    name: str,
    user=Depends(get_current_active_user),
):
    try:
        return get_collection_info(name)
    except Exception as exc:
        logger.error(f"Error getting info for collection {name}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put(
    "/collections/{name}/config",
    response_model=Dict[str, Any],
    summary="更新集合配置",
    responses={
        (200): {"description": "配置更新成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "更新失败"},
    },
)
async def update_collection_config_endpoint(
    name: str,
    payload: CollectionConfigRequest,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        return update_collection_config(collection=name, params=payload.params)
    except Exception as exc:
        logger.error(f"Error updating config for collection {name}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/collections/{name}/clear",
    response_model=Dict[str, Any],
    summary="清空集合",
    responses={
        (200): {"description": "清空成功"},
        (401): {"description": "未授权"},
        (403): {"description": "权限不足(需要管理员)"},
        (500): {"description": "清空失败"},
    },
)
async def clear_collection_endpoint(
    name: str,
    user=Depends(get_current_active_user),
    admin=Depends(role_required("admin")),
):
    try:
        return clear_collection(name)
    except Exception as exc:
        logger.error(f"Error clearing collection {name}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# 向量管理端点
@router.post(
    "/points/get",
    response_model=Dict[str, Any],
    summary="获取向量点详情",
    responses={
        (200): {"description": "向量点详情"},
        (401): {"description": "未授权"},
        (404): {"description": "向量点不存在"},
        (500): {"description": "获取失败"},
    },
)
async def get_point_endpoint(
    payload: GetPointRequest,
    user=Depends(get_current_active_user),
):
    try:
        client = __import__("core.qdrant_service", fromlist=["get_qdrant_client"]).get_qdrant_client()
        if not client:
            raise HTTPException(status_code=503, detail="Qdrant client not available")
        
        from qdrant_client.models import PointId
        result = client.retrieve(
            collection_name=payload.collection,
            ids=[PointId(int=payload.id) if isinstance(payload.id, (int, str) and payload.id.isdigit()) else PointId(payload.id)],
        )
        if not result:
            raise HTTPException(status_code=404, detail="Point not found")
        
        return {
            "id": result[0].id,
            "vector": result[0].vector.tolist() if hasattr(result[0].vector, 'tolist') else result[0].vector,
            "payload": result[0].payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting point {payload.id} from {payload.collection}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/collections/{name}/count",
    response_model=Dict[str, Any],
    summary="获取集合向量计数",
    responses={
        (200): {"description": "向量计数"},
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def get_point_count_endpoint(
    name: str,
    user=Depends(get_current_active_user),
):
    try:
        return get_point_count(name)
    except Exception as exc:
        logger.error(f"Error getting point count for collection {name}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="获取向量服务统计",
    responses={
        (200): {"description": "服务统计"},
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def get_vector_stats_endpoint(
    user=Depends(get_current_active_user),
):
    try:
        return get_vector_stats()
    except Exception as exc:
        logger.error(f"Error getting vector stats: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
