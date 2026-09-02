# -*- coding: utf-8 -*-
"""
Realtime Advanced API Router
高级实时通信API端点
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import RealtimeEvent, RealtimeStream, RealtimeSubscription, RealtimeWebhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["实时通信"])


# ==================== Pydantic Models ====================


class RealtimeStreamCreate(BaseModel):
    """创建实时流请求"""

    name: str = Field(..., description="流名称")
    description: Optional[str] = Field(None, description="流描述")
    stream_type: str = Field(..., description="流类型 (sse, websocket, kafka)")
    source: Optional[str] = Field(None, description="数据源")
    config: Dict[str, Any] = Field(..., description="流配置")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "告警事件流",
                "description": "实时推送告警事件",
                "stream_type": "sse",
                "source": "alerts",
                "config": {"batch_size": 100, "interval": 5},
            }
        }
    }


class RealtimeStreamUpdate(BaseModel):
    """更新实时流请求"""

    name: Optional[str] = Field(None, description="流名称")
    description: Optional[str] = Field(None, description="流描述")
    stream_type: Optional[str] = Field(None, description="流类型")
    source: Optional[str] = Field(None, description="数据源")
    config: Optional[Dict[str, Any]] = Field(None, description="流配置")
    status: Optional[str] = Field(None, description="流状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


class RealtimeStreamResponse(BaseModel):
    """实时流响应"""

    id: str
    name: str
    description: Optional[str]
    stream_type: str
    source: Optional[str]
    config: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RealtimeEventResponse(BaseModel):
    """实时事件响应"""

    id: int
    stream_id: Optional[str]
    event_type: str
    event_data: Dict[str, Any]
    timestamp: str
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RealtimeSubscriptionCreate(BaseModel):
    """创建订阅请求"""

    stream_id: str = Field(..., description="流ID")
    subscriber_id: str = Field(..., description="订阅者ID")
    subscription_type: str = Field(..., description="订阅类型 (sse, websocket)")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stream_id": "STR-001",
                "subscriber_id": "user-001",
                "subscription_type": "sse",
                "filters": {"event_type": "alert"},
            }
        }
    }


class RealtimeSubscriptionResponse(BaseModel):
    """订阅响应"""

    id: str
    stream_id: str
    subscriber_id: str
    subscription_type: str
    filters: Optional[Dict[str, Any]]
    status: str
    created_at: str
    updated_at: str
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RealtimeWebhookCreate(BaseModel):
    """创建Webhook请求"""

    name: str = Field(..., description="Webhook名称")
    description: Optional[str] = Field(None, description="Webhook描述")
    url: str = Field(..., description="Webhook URL")
    method: str = Field(default="POST", description="HTTP方法")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP头")
    body_template: Optional[str] = Field(None, description="请求体模板")
    stream_id: Optional[str] = Field(None, description="关联流ID")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="重试策略")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "告警Webhook",
                "description": "将告警事件推送到外部系统",
                "url": "https://example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "stream_id": "STR-001",
            }
        }
    }


class RealtimeWebhookResponse(BaseModel):
    """Webhook响应"""

    id: str
    name: str
    description: Optional[str]
    url: str
    method: str
    headers: Optional[Dict[str, str]]
    body_template: Optional[str]
    stream_id: Optional[str]
    enabled: bool
    retry_policy: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class RealtimeSubscriptionUpdate(BaseModel):
    """更新订阅请求"""

    subscriber_id: Optional[str] = Field(None, description="订阅者ID")
    subscription_type: Optional[str] = Field(None, description="订阅类型")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    status: Optional[str] = Field(None, description="订阅状态")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


class RealtimeWebhookUpdate(BaseModel):
    """更新Webhook请求"""

    name: Optional[str] = Field(None, description="Webhook名称")
    description: Optional[str] = Field(None, description="Webhook描述")
    url: Optional[str] = Field(None, description="Webhook URL")
    method: Optional[str] = Field(None, description="HTTP方法")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP头")
    body_template: Optional[str] = Field(None, description="请求体模板")
    stream_id: Optional[str] = Field(None, description="关联流ID")
    enabled: Optional[bool] = Field(None, description="是否启用")
    retry_policy: Optional[Dict[str, Any]] = Field(None, description="重试策略")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


# ==================== API Endpoints ====================


@router.get("/streams", response_model=List[RealtimeStreamResponse], summary="获取实时流列表")
async def get_realtime_streams(
    stream_type: Optional[str] = Query(None, description="按流类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RealtimeStreamResponse]:
    """
    获取实时流列表

    支持按流类型和状态过滤
    """
    try:
        query = db.query(RealtimeStream)

        if stream_type is not None:
            query = query.filter(RealtimeStream.stream_type == stream_type)
        if status is not None:
            query = query.filter(RealtimeStream.status == status)

        # Apply pagination
        query = query.order_by(RealtimeStream.created_at.desc())
        query = query.offset(offset)
        query = query.limit(limit)
        streams = query.all()

        return [
            RealtimeStreamResponse(
                id=stream.id,
                name=stream.name,
                description=stream.description,
                stream_type=stream.stream_type,
                source=stream.source,
                config=stream.config,
                status=stream.status,
                created_at=stream.created_at.isoformat() if stream.created_at else "",
                updated_at=stream.updated_at.isoformat() if stream.updated_at else "",
                created_by=stream.created_by,
                meta_data=stream.meta_data,
            )
            for stream in streams
        ]
    except Exception as e:
        logger.error(f"获取实时流失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时流失败: {str(e)}")


@router.post("/streams", response_model=RealtimeStreamResponse, summary="创建实时流")
async def create_realtime_stream(stream: RealtimeStreamCreate, db: Session = Depends(get_db)) -> RealtimeStreamResponse:
    """
    创建新的实时流

    流用于实时推送事件数据
    """
    try:
        # 验证流类型
        valid_types = ["sse", "websocket", "kafka"]
        if stream.stream_type not in valid_types:
            raise HTTPException(
                status_code=400, detail=f"无效的流类型: {stream.stream_type}, 必须是 {valid_types}"
            )

        # 检查名称是否已存在
        existing = db.query(RealtimeStream).filter(RealtimeStream.name == stream.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"流名称 '{stream.name}' 已存在")

        # 创建流
        stream_id = f"STR-{uuid.uuid4().hex[:8].upper()}"
        new_stream = RealtimeStream(
            id=stream_id,
            name=stream.name,
            description=stream.description,
            stream_type=stream.stream_type,
            source=stream.source,
            config=stream.config,
            status="active",
            meta_data=stream.meta_data,
            created_by="system",
        )

        db.add(new_stream)
        db.commit()
        db.refresh(new_stream)

        logger.info(f"创建实时流成功: {stream_id}")

        return RealtimeStreamResponse(
            id=new_stream.id,
            name=new_stream.name,
            description=new_stream.description,
            stream_type=new_stream.stream_type,
            source=new_stream.source,
            config=new_stream.config,
            status=new_stream.status,
            created_at=new_stream.created_at.isoformat() if new_stream.created_at else "",
            updated_at=new_stream.updated_at.isoformat() if new_stream.updated_at else "",
            created_by=new_stream.created_by,
            meta_data=new_stream.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建实时流失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建实时流失败: {str(e)}")


@router.get("/streams/{stream_id}", response_model=RealtimeStreamResponse, summary="获取单个实时流")
async def get_realtime_stream(stream_id: str, db: Session = Depends(get_db)) -> RealtimeStreamResponse:
    """
    根据ID获取单个实时流
    """
    try:
        stream = db.query(RealtimeStream).filter(RealtimeStream.id == stream_id).first()
        if not stream:
            raise HTTPException(status_code=404, detail=f"流 {stream_id} 不存在")

        return RealtimeStreamResponse(
            id=stream.id,
            name=stream.name,
            description=stream.description,
            stream_type=stream.stream_type,
            source=stream.source,
            config=stream.config,
            status=stream.status,
            created_at=stream.created_at.isoformat() if stream.created_at else "",
            updated_at=stream.updated_at.isoformat() if stream.updated_at else "",
            created_by=stream.created_by,
            meta_data=stream.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时流失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时流失败: {str(e)}")


@router.patch("/streams/{stream_id}", response_model=RealtimeStreamResponse, summary="更新实时流")
async def update_realtime_stream(
    stream_id: str, stream_update: RealtimeStreamUpdate, db: Session = Depends(get_db)
) -> RealtimeStreamResponse:
    """
    更新实时流

    支持部分更新
    """
    try:
        stream = db.query(RealtimeStream).filter(RealtimeStream.id == stream_id).first()
        if not stream:
            raise HTTPException(status_code=404, detail=f"流 {stream_id} 不存在")

        # 更新字段
        update_data = stream_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stream, field, value)

        # 验证流类型
        if stream_update.stream_type is not None:
            valid_types = ["sse", "websocket", "kafka"]
            if stream.stream_type not in valid_types:
                raise HTTPException(status_code=400, detail=f"无效的流类型: {stream.stream_type}")

        db.commit()
        db.refresh(stream)

        logger.info(f"更新实时流成功: {stream_id}")

        return RealtimeStreamResponse(
            id=stream.id,
            name=stream.name,
            description=stream.description,
            stream_type=stream.stream_type,
            source=stream.source,
            config=stream.config,
            status=stream.status,
            created_at=stream.created_at.isoformat() if stream.created_at else "",
            updated_at=stream.updated_at.isoformat() if stream.updated_at else "",
            created_by=stream.created_by,
            meta_data=stream.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新实时流失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新实时流失败: {str(e)}")


@router.delete("/streams/{stream_id}", summary="删除实时流")
async def delete_realtime_stream(stream_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除实时流
    """
    try:
        stream = db.query(RealtimeStream).filter(RealtimeStream.id == stream_id).first()
        if not stream:
            raise HTTPException(status_code=404, detail=f"流 {stream_id} 不存在")

        db.delete(stream)
        db.commit()

        logger.info(f"删除实时流成功: {stream_id}")

        return {"status": "success", "message": f"流 {stream_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除实时流失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除实时流失败: {str(e)}")


@router.get("/events", response_model=List[RealtimeEventResponse], summary="获取实时事件列表")
async def get_realtime_events(
    stream_id: Optional[str] = Query(None, description="按流ID过滤"),
    event_type: Optional[str] = Query(None, description="按事件类型过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RealtimeEventResponse]:
    """
    获取实时事件列表

    支持按流ID和事件类型过滤
    """
    try:
        query = db.query(RealtimeEvent)

        if stream_id is not None:
            query = query.filter(RealtimeEvent.stream_id == stream_id)
        if event_type is not None:
            query = query.filter(RealtimeEvent.event_type == event_type)

        events = query.order_by(RealtimeEvent.timestamp.desc()).offset(offset).limit(limit).all()

        return [
            RealtimeEventResponse(
                id=event.id,
                stream_id=event.stream_id,
                event_type=event.event_type,
                event_data=event.event_data,
                timestamp=event.timestamp.isoformat() if event.timestamp else "",
                meta_data=event.meta_data,
            )
            for event in events
        ]
    except Exception as e:
        logger.error(f"获取实时事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时事件失败: {str(e)}")


@router.get(
    "/subscriptions", response_model=List[RealtimeSubscriptionResponse], summary="获取订阅列表"
)
async def get_realtime_subscriptions(
    stream_id: Optional[str] = Query(None, description="按流ID过滤"),
    subscriber_id: Optional[str] = Query(None, description="按订阅者ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RealtimeSubscriptionResponse]:
    """
    获取订阅列表

    支持按流ID、订阅者ID和状态过滤
    """
    try:
        query = db.query(RealtimeSubscription)

        if stream_id is not None:
            query = query.filter(RealtimeSubscription.stream_id == stream_id)
        if subscriber_id is not None:
            query = query.filter(RealtimeSubscription.subscriber_id == subscriber_id)
        if status is not None:
            query = query.filter(RealtimeSubscription.status == status)

        # Apply pagination
        query = query.order_by(RealtimeSubscription.created_at.desc())
        query = query.offset(offset)
        query = query.limit(limit)
        subscriptions = query.all()

        return [
            RealtimeSubscriptionResponse(
                id=sub.id,
                stream_id=sub.stream_id,
                subscriber_id=sub.subscriber_id,
                subscription_type=sub.subscription_type,
                filters=sub.filters,
                status=sub.status,
                created_at=sub.created_at.isoformat() if sub.created_at else "",
                updated_at=sub.updated_at.isoformat() if sub.updated_at else "",
                meta_data=sub.meta_data,
            )
            for sub in subscriptions
        ]
    except Exception as e:
        logger.error(f"获取订阅列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订阅列表失败: {str(e)}")


@router.post("/subscriptions", response_model=RealtimeSubscriptionResponse, summary="创建订阅")
async def create_realtime_subscription(
    subscription: RealtimeSubscriptionCreate, db: Session = Depends(get_db)
) -> RealtimeSubscriptionResponse:
    """
    创建新的订阅

    订阅用于接收实时流的事件
    """
    try:
        # 验证流是否存在
        stream = (
            db.query(RealtimeStream).filter(RealtimeStream.id == subscription.stream_id).first()
        )
        if not stream:
            raise HTTPException(status_code=404, detail=f"流 {subscription.stream_id} 不存在")

        # 验证订阅类型
        valid_types = ["sse", "websocket"]
        if subscription.subscription_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的订阅类型: {subscription.subscription_type}, 必须是 {valid_types}",
            )

        # 创建订阅
        sub_id = f"SUB-{uuid.uuid4().hex[:8].upper()}"
        new_subscription = RealtimeSubscription(
            id=sub_id,
            stream_id=subscription.stream_id,
            subscriber_id=subscription.subscriber_id,
            subscription_type=subscription.subscription_type,
            filters=subscription.filters,
            status="active",
            meta_data=subscription.meta_data,
        )

        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)

        logger.info(f"创建订阅成功: {sub_id}")

        return RealtimeSubscriptionResponse(
            id=new_subscription.id,
            stream_id=new_subscription.stream_id,
            subscriber_id=new_subscription.subscriber_id,
            subscription_type=new_subscription.subscription_type,
            filters=new_subscription.filters,
            status=new_subscription.status,
            created_at=(
                new_subscription.created_at.isoformat() if new_subscription.created_at else ""
            ),
            updated_at=(
                new_subscription.updated_at.isoformat() if new_subscription.updated_at else ""
            ),
            meta_data=new_subscription.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建订阅失败: {str(e)}")


@router.get("/webhooks", response_model=List[RealtimeWebhookResponse], summary="获取Webhook列表")
async def get_realtime_webhooks(
    stream_id: Optional[str] = Query(None, description="按流ID过滤"),
    enabled: Optional[bool] = Query(None, description="是否只返回启用的Webhook"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[RealtimeWebhookResponse]:
    """
    获取Webhook列表

    支持按流ID和启用状态过滤
    """
    try:
        query = db.query(RealtimeWebhook)

        if stream_id is not None:
            query = query.filter(RealtimeWebhook.stream_id == stream_id)
        if enabled is not None:
            query = query.filter(RealtimeWebhook.enabled == enabled)

        webhooks = (
            query.order_by(RealtimeWebhook.created_at.desc()).offset(offset).limit(limit).all()
        )

        return [
            RealtimeWebhookResponse(
                id=webhook.id,
                name=webhook.name,
                description=webhook.description,
                url=webhook.url,
                method=webhook.method,
                headers=webhook.headers,
                body_template=webhook.body_template,
                stream_id=webhook.stream_id,
                enabled=webhook.enabled,
                retry_policy=webhook.retry_policy,
                created_at=webhook.created_at.isoformat() if webhook.created_at else "",
                updated_at=webhook.updated_at.isoformat() if webhook.updated_at else "",
                created_by=webhook.created_by,
                meta_data=webhook.meta_data,
            )
            for webhook in webhooks
        ]
    except Exception as e:
        logger.error(f"获取Webhook列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取Webhook列表失败: {str(e)}")


@router.post("/webhooks", response_model=RealtimeWebhookResponse, summary="创建Webhook")
async def create_realtime_webhook(webhook: RealtimeWebhookCreate, db: Session = Depends(get_db)) -> RealtimeWebhookResponse:
    """
    创建新的Webhook

    Webhook用于将实时事件推送到外部系统
    """
    try:
        # 验证URL格式
        from urllib.parse import urlparse
        parsed = urlparse(webhook.url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=422, detail="无效的URL格式")

        # 验证流是否存在
        if webhook.stream_id:
            query = db.query(RealtimeStream).filter(RealtimeStream.id == webhook.stream_id)
            stream = query.first()
            if not stream:
                raise HTTPException(status_code=404, detail=f"流 {webhook.stream_id} 不存在")

        # 验证HTTP方法
        valid_methods = ["GET", "POST", "PUT", "DELETE"]
        if webhook.method not in valid_methods:
            raise HTTPException(
                status_code=400, detail=f"无效的HTTP方法: {webhook.method}, 必须是 {valid_methods}"
            )

        # 检查名称是否已存在
        existing = db.query(RealtimeWebhook).filter(RealtimeWebhook.name == webhook.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Webhook名称 '{webhook.name}' 已存在")

        # 创建Webhook
        webhook_id = f"WH-{uuid.uuid4().hex[:8].upper()}"
        new_webhook = RealtimeWebhook(
            id=webhook_id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            method=webhook.method,
            headers=webhook.headers,
            body_template=webhook.body_template,
            stream_id=webhook.stream_id,
            enabled=True,
            retry_policy=webhook.retry_policy,
            meta_data=webhook.meta_data,
            created_by="system",
        )

        db.add(new_webhook)
        db.commit()
        db.refresh(new_webhook)

        logger.info(f"创建Webhook成功: {webhook_id}")

        return RealtimeWebhookResponse(
            id=new_webhook.id,
            name=new_webhook.name,
            description=new_webhook.description,
            url=new_webhook.url,
            method=new_webhook.method,
            headers=new_webhook.headers,
            body_template=new_webhook.body_template,
            stream_id=new_webhook.stream_id,
            enabled=new_webhook.enabled,
            retry_policy=new_webhook.retry_policy,
            created_at=new_webhook.created_at.isoformat() if new_webhook.created_at else "",
            updated_at=new_webhook.updated_at.isoformat() if new_webhook.updated_at else "",
            created_by=new_webhook.created_by,
            meta_data=new_webhook.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建Webhook失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建Webhook失败: {str(e)}")


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=RealtimeSubscriptionResponse,
    summary="获取单个订阅",
)
async def get_realtime_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> RealtimeSubscriptionResponse:
    """
    根据ID获取单个订阅
    """
    try:
        subscription = (
            db.query(RealtimeSubscription)
            .filter(RealtimeSubscription.id == subscription_id)
            .first()
        )
        if not subscription:
            raise HTTPException(status_code=404, detail=f"订阅 {subscription_id} 不存在")

        return RealtimeSubscriptionResponse(
            id=subscription.id,
            stream_id=subscription.stream_id,
            subscriber_id=subscription.subscriber_id,
            subscription_type=subscription.subscription_type,
            filters=subscription.filters,
            status=subscription.status,
            created_at=subscription.created_at.isoformat() if subscription.created_at else "",
            updated_at=subscription.updated_at.isoformat() if subscription.updated_at else "",
            meta_data=subscription.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取订阅失败: {str(e)}")


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=RealtimeSubscriptionResponse,
    summary="更新订阅",
)
async def update_realtime_subscription(
    subscription_id: str,
    subscription_update: RealtimeSubscriptionUpdate,
    db: Session = Depends(get_db),
) -> RealtimeSubscriptionResponse:
    """
    更新订阅

    支持部分更新
    """
    try:
        subscription = (
            db.query(RealtimeSubscription)
            .filter(RealtimeSubscription.id == subscription_id)
            .first()
        )
        if not subscription:
            raise HTTPException(status_code=404, detail=f"订阅 {subscription_id} 不存在")

        # 更新字段
        update_data = subscription_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(subscription, field, value)

        # 验证订阅类型
        if subscription_update.subscription_type is not None:
            valid_types = ["sse", "websocket"]
            if subscription.subscription_type not in valid_types:
                raise HTTPException(
                    status_code=400, detail=f"无效的订阅类型: {subscription.subscription_type}"
                )

        db.commit()
        db.refresh(subscription)

        logger.info(f"更新订阅成功: {subscription_id}")

        return RealtimeSubscriptionResponse(
            id=subscription.id,
            stream_id=subscription.stream_id,
            subscriber_id=subscription.subscriber_id,
            subscription_type=subscription.subscription_type,
            filters=subscription.filters,
            status=subscription.status,
            created_at=subscription.created_at.isoformat() if subscription.created_at else "",
            updated_at=subscription.updated_at.isoformat() if subscription.updated_at else "",
            meta_data=subscription.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新订阅失败: {str(e)}")


@router.delete("/subscriptions/{subscription_id}", summary="删除订阅")
async def delete_realtime_subscription(
    subscription_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    删除订阅
    """
    try:
        subscription = (
            db.query(RealtimeSubscription)
            .filter(RealtimeSubscription.id == subscription_id)
            .first()
        )
        if not subscription:
            raise HTTPException(status_code=404, detail=f"订阅 {subscription_id} 不存在")

        db.delete(subscription)
        db.commit()

        logger.info(f"删除订阅成功: {subscription_id}")

        return {"status": "success", "message": f"订阅 {subscription_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除订阅失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除订阅失败: {str(e)}")


@router.get(
    "/webhooks/{webhook_id}", response_model=RealtimeWebhookResponse, summary="获取单个Webhook"
)
async def get_realtime_webhook(
    webhook_id: str, db: Session = Depends(get_db)
) -> RealtimeWebhookResponse:
    """
    根据ID获取单个Webhook
    """
    try:
        webhook = (
            db.query(RealtimeWebhook).filter(RealtimeWebhook.id == webhook_id).first()
        )
        if not webhook:
            raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} 不存在")

        return RealtimeWebhookResponse(
            id=webhook.id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            method=webhook.method,
            headers=webhook.headers,
            body_template=webhook.body_template,
            stream_id=webhook.stream_id,
            enabled=webhook.enabled,
            retry_policy=webhook.retry_policy,
            created_at=webhook.created_at.isoformat() if webhook.created_at else "",
            updated_at=webhook.updated_at.isoformat() if webhook.updated_at else "",
            created_by=webhook.created_by,
            meta_data=webhook.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Webhook失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取Webhook失败: {str(e)}")


@router.patch(
    "/webhooks/{webhook_id}", response_model=RealtimeWebhookResponse, summary="更新Webhook"
)
async def update_realtime_webhook(
    webhook_id: str, webhook_update: RealtimeWebhookUpdate, db: Session = Depends(get_db)
) -> RealtimeWebhookResponse:
    """
    更新Webhook

    支持部分更新
    """
    try:
        webhook = (
            db.query(RealtimeWebhook).filter(RealtimeWebhook.id == webhook_id).first()
        )
        if not webhook:
            raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} 不存在")

        # 更新字段
        update_data = webhook_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(webhook, field, value)

        # 验证URL格式（如果更新了URL）
        if webhook_update.url is not None:
            from urllib.parse import urlparse

            parsed = urlparse(webhook.url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(status_code=422, detail="无效的URL格式")

        # 验证流是否存在（如果更新了stream_id）
        if webhook_update.stream_id is not None:
            stream = (
                db.query(RealtimeStream)
                .filter(RealtimeStream.id == webhook.stream_id)
                .first()
            )
            if not stream:
                raise HTTPException(status_code=404, detail=f"流 {webhook.stream_id} 不存在")

        # 验证HTTP方法（如果更新了method）
        if webhook_update.method is not None:
            valid_methods = ["GET", "POST", "PUT", "DELETE"]
            if webhook.method not in valid_methods:
                raise HTTPException(
                    status_code=400, detail=f"无效的HTTP方法: {webhook.method}, 必须是 {valid_methods}"
                )

        db.commit()
        db.refresh(webhook)

        logger.info(f"更新Webhook成功: {webhook_id}")

        return RealtimeWebhookResponse(
            id=webhook.id,
            name=webhook.name,
            description=webhook.description,
            url=webhook.url,
            method=webhook.method,
            headers=webhook.headers,
            body_template=webhook.body_template,
            stream_id=webhook.stream_id,
            enabled=webhook.enabled,
            retry_policy=webhook.retry_policy,
            created_at=webhook.created_at.isoformat() if webhook.created_at else "",
            updated_at=webhook.updated_at.isoformat() if webhook.updated_at else "",
            created_by=webhook.created_by,
            meta_data=webhook.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新Webhook失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新Webhook失败: {str(e)}")


@router.delete("/webhooks/{webhook_id}", summary="删除Webhook")
async def delete_realtime_webhook(
    webhook_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    删除Webhook
    """
    try:
        webhook = (
            db.query(RealtimeWebhook).filter(RealtimeWebhook.id == webhook_id).first()
        )
        if not webhook:
            raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} 不存在")

        db.delete(webhook)
        db.commit()

        logger.info(f"删除Webhook成功: {webhook_id}")

        return {"status": "success", "message": f"Webhook {webhook_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除Webhook失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除Webhook失败: {str(e)}")
