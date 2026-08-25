# -*- coding: utf-8 -*-
"""
Priority Advanced API Router
高级优先级管理API端点
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import PriorityRule, PriorityScore, PriorityHistory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/priority", tags=["优先级管理"])


# ==================== Pydantic Models ====================


class PriorityRuleCreate(BaseModel):
    """创建优先级规则请求"""

    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    conditions: Dict[str, Any] = Field(..., description="规则条件")
    priority_level: str = Field(..., description="优先级级别 (P0, P1, P2, P3, P4)")
    weight: float = Field(default=1.0, description="权重")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "高CPU使用率规则",
                "description": "当CPU使用率超过90%时设置为P0",
                "conditions": {"metric": "cpu_usage", "operator": ">", "threshold": 90},
                "priority_level": "P0",
                "weight": 1.0,
            }
        }
    }


class PriorityRuleUpdate(BaseModel):
    """更新优先级规则请求"""

    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    conditions: Optional[Dict[str, Any]] = Field(None, description="规则条件")
    priority_level: Optional[str] = Field(None, description="优先级级别")
    weight: Optional[float] = Field(None, description="权重")
    enabled: Optional[bool] = Field(None, description="是否启用")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="元数据")

    model_config = {"extra": "ignore"}


class PriorityRuleResponse(BaseModel):
    """优先级规则响应"""

    id: str
    name: str
    description: Optional[str]
    conditions: Dict[str, Any]
    priority_level: str
    weight: float
    enabled: bool
    created_at: str
    updated_at: str
    created_by: Optional[str]
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class PriorityScoreRequest(BaseModel):
    """优先级分数计算请求"""

    alert_id: str = Field(..., description="告警ID")
    metrics: Dict[str, Any] = Field(..., description="指标数据")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert_id": "ALT-001",
                "metrics": {"cpu_usage": 95, "memory_usage": 80, "response_time": 5000},
                "context": {"service": "api-service", "affected_users": 1000},
            }
        }
    }


class PriorityScoreResponse(BaseModel):
    """优先级分数响应"""

    id: int
    alert_id: str
    priority_level: str
    score: float
    bis_score: Optional[float]
    factors: Optional[Dict[str, Any]]
    calculated_at: str
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class PriorityHistoryResponse(BaseModel):
    """优先级历史响应"""

    id: int
    alert_id: str
    old_priority: Optional[str]
    new_priority: str
    old_score: Optional[float]
    new_score: float
    change_reason: Optional[str]
    changed_by: Optional[str]
    changed_at: str
    meta_data: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


# ==================== API Endpoints ====================


@router.get("/rules", response_model=List[PriorityRuleResponse], summary="获取优先级规则列表")
async def get_priority_rules(
    enabled: Optional[bool] = Query(None, description="是否只返回启用的规则"),
    priority_level: Optional[str] = Query(None, description="按优先级级别过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[PriorityRuleResponse]:
    """
    获取优先级规则列表

    支持按启用状态和优先级级别过滤
    """
    try:
        query = db.query(PriorityRule)

        if enabled is not None:
            query = query.filter(PriorityRule.enabled == enabled)
        if priority_level is not None:
            query = query.filter(PriorityRule.priority_level == priority_level)

        rules = query.order_by(PriorityRule.created_at.desc()).offset(offset).limit(limit).all()

        return [
            PriorityRuleResponse(
                id=rule.id,
                name=rule.name,
                description=rule.description,
                conditions=rule.conditions,
                priority_level=rule.priority_level,
                weight=rule.weight,
                enabled=rule.enabled,
                created_at=rule.created_at.isoformat() if rule.created_at else "",
                updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
                created_by=rule.created_by,
                meta_data=rule.meta_data,
            )
            for rule in rules
        ]
    except Exception as e:
        logger.error(f"获取优先级规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优先级规则失败: {str(e)}")


@router.post("/rules", response_model=PriorityRuleResponse, summary="创建优先级规则")
async def create_priority_rule(
    rule: PriorityRuleCreate, db: Session = Depends(get_db)
) -> PriorityRuleResponse:
    """
    创建新的优先级规则

    规则用于根据条件自动计算告警的优先级
    """
    try:
        # 验证优先级级别
        valid_levels = ["P0", "P1", "P2", "P3", "P4"]
        if rule.priority_level not in valid_levels:
            raise HTTPException(
                status_code=400, detail=f"无效的优先级级别: {rule.priority_level}, 必须是 {valid_levels}"
            )

        # 检查名称是否已存在
        existing = db.query(PriorityRule).filter(PriorityRule.name == rule.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"规则名称 '{rule.name}' 已存在")

        # 创建规则
        rule_id = f"PR-{uuid.uuid4().hex[:8].upper()}"
        new_rule = PriorityRule(
            id=rule_id,
            name=rule.name,
            description=rule.description,
            conditions=rule.conditions,
            priority_level=rule.priority_level,
            weight=rule.weight,
            enabled=True,
            meta_data=rule.meta_data,
            created_by="system",
        )

        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)

        logger.info(f"创建优先级规则成功: {rule_id}")

        return PriorityRuleResponse(
            id=new_rule.id,
            name=new_rule.name,
            description=new_rule.description,
            conditions=new_rule.conditions,
            priority_level=new_rule.priority_level,
            weight=new_rule.weight,
            enabled=new_rule.enabled,
            created_at=new_rule.created_at.isoformat() if new_rule.created_at else "",
            updated_at=new_rule.updated_at.isoformat() if new_rule.updated_at else "",
            created_by=new_rule.created_by,
            meta_data=new_rule.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"创建优先级规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建优先级规则失败: {str(e)}")


@router.get("/rules/{rule_id}", response_model=PriorityRuleResponse, summary="获取单个优先级规则")
async def get_priority_rule(
    rule_id: str, db: Session = Depends(get_db)
) -> PriorityRuleResponse:
    """
    根据ID获取单个优先级规则
    """
    try:
        rule = db.query(PriorityRule).filter(PriorityRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        return PriorityRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            conditions=rule.conditions,
            priority_level=rule.priority_level,
            weight=rule.weight,
            enabled=rule.enabled,
            created_at=rule.created_at.isoformat() if rule.created_at else "",
            updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
            created_by=rule.created_by,
            meta_data=rule.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取优先级规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优先级规则失败: {str(e)}")


@router.patch("/rules/{rule_id}", response_model=PriorityRuleResponse, summary="更新优先级规则")
async def update_priority_rule(
    rule_id: str, rule_update: PriorityRuleUpdate, db: Session = Depends(get_db)
) -> PriorityRuleResponse:
    """
    更新优先级规则

    支持部分更新
    """
    try:
        rule = db.query(PriorityRule).filter(PriorityRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        # 更新字段
        update_data = rule_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        # 验证优先级级别
        if rule_update.priority_level is not None:
            valid_levels = ["P0", "P1", "P2", "P3", "P4"]
            if rule.priority_level not in valid_levels:
                raise HTTPException(
                    status_code=400, detail=f"无效的优先级级别: {rule.priority_level}"
                )

        db.commit()
        db.refresh(rule)

        logger.info(f"更新优先级规则成功: {rule_id}")

        return PriorityRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            conditions=rule.conditions,
            priority_level=rule.priority_level,
            weight=rule.weight,
            enabled=rule.enabled,
            created_at=rule.created_at.isoformat() if rule.created_at else "",
            updated_at=rule.updated_at.isoformat() if rule.updated_at else "",
            created_by=rule.created_by,
            meta_data=rule.meta_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新优先级规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新优先级规则失败: {str(e)}")


@router.delete("/rules/{rule_id}", summary="删除优先级规则")
async def delete_priority_rule(rule_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    删除优先级规则
    """
    try:
        rule = db.query(PriorityRule).filter(PriorityRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        db.delete(rule)
        db.commit()

        logger.info(f"删除优先级规则成功: {rule_id}")

        return {"status": "success", "message": f"规则 {rule_id} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除优先级规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除优先级规则失败: {str(e)}")


@router.get("/scores", response_model=List[PriorityScoreResponse], summary="获取优先级分数列表")
async def get_priority_scores(
    alert_id: Optional[str] = Query(None, description="按告警ID过滤"),
    priority_level: Optional[str] = Query(None, description="按优先级级别过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[PriorityScoreResponse]:
    """
    获取优先级分数列表

    支持按告警ID和优先级级别过滤
    """
    try:
        query = db.query(PriorityScore)

        if alert_id is not None:
            query = query.filter(PriorityScore.alert_id == alert_id)
        if priority_level is not None:
            query = query.filter(PriorityScore.priority_level == priority_level)

        scores = query.order_by(PriorityScore.calculated_at.desc()).offset(offset).limit(limit).all()

        return [
            PriorityScoreResponse(
                id=score.id,
                alert_id=score.alert_id,
                priority_level=score.priority_level,
                score=score.score,
                bis_score=score.bis_score,
                factors=score.factors,
                calculated_at=score.calculated_at.isoformat() if score.calculated_at else "",
                meta_data=score.meta_data,
            )
            for score in scores
        ]
    except Exception as e:
        logger.error(f"获取优先级分数失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优先级分数失败: {str(e)}")


@router.post("/calculator", response_model=PriorityScoreResponse, summary="计算优先级分数")
async def calculate_priority_score(
    request: PriorityScoreRequest, db: Session = Depends(get_db)
) -> PriorityScoreResponse:
    """
    计算告警的优先级分数

    基于指标数据和规则计算优先级分数
    """
    try:
        # 获取启用的规则
        rules = db.query(PriorityRule).filter(PriorityRule.enabled == True).all()

        # 计算分数
        score = 0.0
        priority_level = "P3"
        factors = {}

        for rule in rules:
            # 简单的规则匹配逻辑
            conditions = rule.conditions
            matched = True

            for key, condition in conditions.items():
                if key in request.metrics:
                    metric_value = request.metrics[key]
                    operator = condition.get("operator", "==")
                    threshold = condition.get("threshold", 0)

                    if operator == ">" and metric_value <= threshold:
                        matched = False
                        break
                    elif operator == "<" and metric_value >= threshold:
                        matched = False
                        break
                    elif operator == ">=" and metric_value < threshold:
                        matched = False
                        break
                    elif operator == "<=" and metric_value > threshold:
                        matched = False
                        break
                    elif operator == "==" and metric_value != threshold:
                        matched = False
                        break

            if matched:
                # 根据优先级级别计算分数
                level_scores = {"P0": 100, "P1": 80, "P2": 60, "P3": 40, "P4": 20}
                rule_score = level_scores.get(rule.priority_level, 40) * rule.weight
                score = max(score, rule_score)
                priority_level = rule.priority_level
                factors[rule.name] = {
                    "matched": True,
                    "priority_level": rule.priority_level,
                    "weight": rule.weight,
                    "score": rule_score,
                }

        # 计算业务影响分数
        bis_score = 0.0
        if request.context:
            affected_users = request.context.get("affected_users", 0)
            if affected_users > 10000:
                bis_score = 1.0
            elif affected_users > 1000:
                bis_score = 0.8
            elif affected_users > 100:
                bis_score = 0.6
            elif affected_users > 10:
                bis_score = 0.4
            else:
                bis_score = 0.2

        # 保存分数
        new_score = PriorityScore(
            alert_id=request.alert_id,
            priority_level=priority_level,
            score=score,
            bis_score=bis_score,
            factors=factors,
            meta_data=request.context,
        )

        db.add(new_score)
        db.commit()
        db.refresh(new_score)

        # 记录历史
        history = PriorityHistory(
            alert_id=request.alert_id,
            old_priority=None,
            new_priority=priority_level,
            old_score=None,
            new_score=score,
            change_reason="初始计算",
            changed_by="system",
        )
        db.add(history)
        db.commit()

        logger.info(f"计算优先级分数成功: {request.alert_id}, score={score}")

        return PriorityScoreResponse(
            id=new_score.id,
            alert_id=new_score.alert_id,
            priority_level=new_score.priority_level,
            score=new_score.score,
            bis_score=new_score.bis_score,
            factors=new_score.factors,
            calculated_at=new_score.calculated_at.isoformat() if new_score.calculated_at else "",
            meta_data=new_score.meta_data,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"计算优先级分数失败: {e}")
        raise HTTPException(status_code=500, detail=f"计算优先级分数失败: {str(e)}")


@router.get("/history", response_model=List[PriorityHistoryResponse], summary="获取优先级历史记录")
async def get_priority_history(
    alert_id: Optional[str] = Query(None, description="按告警ID过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> List[PriorityHistoryResponse]:
    """
    获取优先级变更历史记录

    支持按告警ID过滤
    """
    try:
        query = db.query(PriorityHistory)

        if alert_id is not None:
            query = query.filter(PriorityHistory.alert_id == alert_id)

        history = query.order_by(PriorityHistory.changed_at.desc()).offset(offset).limit(limit).all()

        return [
            PriorityHistoryResponse(
                id=h.id,
                alert_id=h.alert_id,
                old_priority=h.old_priority,
                new_priority=h.new_priority,
                old_score=h.old_score,
                new_score=h.new_score,
                change_reason=h.change_reason,
                changed_by=h.changed_by,
                changed_at=h.changed_at.isoformat() if h.changed_at else "",
                meta_data=h.meta_data,
            )
            for h in history
        ]
    except Exception as e:
        logger.error(f"获取优先级历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取优先级历史失败: {str(e)}")
