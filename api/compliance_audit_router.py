# -*- coding: utf-8 -*-
"""
Compliance Audit Router Module
============================

Provides API endpoints for compliance audit management.
Supports audit creation, retrieval, update, and deletion.

Endpoints:
- GET /api/v1/compliance/audits - Get all compliance audits
- POST /api/v1/compliance/audits - Create new compliance audit
- GET /api/v1/compliance/audits/{id} - Get audit by ID
- PUT /api/v1/compliance/audits/{id} - Update audit
- DELETE /api/v1/compliance/audits/{id} - Delete audit
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.common import create_success_response, create_list_response, handle_service_error
from core.database import get_db
from core.models import ComplianceAudit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/compliance", tags=["合规审计"])


# ============================================================================
# Pydantic Models
# ============================================================================


class ComplianceAuditCreate(BaseModel):
    """合规审计创建模型"""

    name: str = Field(..., min_length=1, max_length=200, description="审计名称")
    audit_type: str = Field(..., description="审计类型")
    scope: Optional[Dict[str, Any]] = Field(None, description="审计范围")
    scheduled_date: Optional[datetime] = Field(None, description="计划执行日期")


class ComplianceAuditUpdate(BaseModel):
    """合规审计更新模型"""

    name: Optional[str] = Field(None, max_length=200, description="审计名称")
    status: Optional[str] = Field(None, description="审计状态")
    findings: Optional[Dict[str, Any]] = Field(None, description="审计发现")
    result: Optional[Dict[str, Any]] = Field(None, description="审计结果")
    completed_date: Optional[datetime] = Field(None, description="完成日期")


class ComplianceAuditResponse(BaseModel):
    """合规审计响应模型"""

    id: str
    name: str
    audit_type: str
    status: str
    scope: Optional[Dict[str, Any]]
    findings: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    scheduled_date: Optional[datetime]
    completed_date: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str]


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/audits", summary="获取所有合规审计")
async def get_audits(
    audit_type: Optional[str] = Query(None, description="审计类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取所有合规审计"""
    try:
        query = db.query(ComplianceAudit)
        
        if audit_type:
            query = query.filter(ComplianceAudit.audit_type == audit_type)
        if status:
            query = query.filter(ComplianceAudit.status == status)
        
        total = query.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        audits = query.offset(start_idx).limit(page_size).all()
        
        return {
            "audits": [
                {
                    "id": audit.id,
                    "name": audit.name,
                    "audit_type": audit.audit_type,
                    "status": audit.status,
                    "scope": audit.scope,
                    "findings": audit.findings,
                    "result": audit.result,
                    "scheduled_date": audit.scheduled_date.isoformat() if audit.scheduled_date else None,
                    "completed_date": audit.completed_date.isoformat() if audit.completed_date else None,
                    "created_at": audit.created_at.isoformat() if audit.created_at else None,
                    "updated_at": audit.updated_at.isoformat() if audit.updated_at else None,
                    "created_by": audit.created_by,
                }
                for audit in audits
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        handle_service_error(e, "获取合规审计列表")


@router.post("/audits", summary="创建合规审计")
async def create_audit(
    audit: ComplianceAuditCreate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """创建新的合规审计"""
    try:
        new_audit = ComplianceAudit(
            id=str(uuid.uuid4()),
            name=audit.name,
            audit_type=audit.audit_type,
            status="pending",
            scope=audit.scope,
            findings=None,
            result=None,
            scheduled_date=audit.scheduled_date,
            completed_date=None,
            created_by="system",
        )
        db.add(new_audit)
        db.commit()
        db.refresh(new_audit)
        
        return {
            "status": "success",
            "audit": {
                "id": new_audit.id,
                "name": new_audit.name,
                "audit_type": new_audit.audit_type,
                "status": new_audit.status,
                "scope": new_audit.scope,
                "findings": new_audit.findings,
                "result": new_audit.result,
                "scheduled_date": new_audit.scheduled_date.isoformat() if new_audit.scheduled_date else None,
                "completed_date": new_audit.completed_date.isoformat() if new_audit.completed_date else None,
                "created_at": new_audit.created_at.isoformat() if new_audit.created_at else None,
                "updated_at": new_audit.updated_at.isoformat() if new_audit.updated_at else None,
                "created_by": new_audit.created_by,
            }
        }
    except Exception as e:
        db.rollback()
        handle_service_error(e, "创建合规审计")


@router.get("/audits/{audit_id}", summary="获取单个合规审计")
async def get_audit(
    audit_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取单个合规审计"""
    try:
        audit = db.query(ComplianceAudit).filter(ComplianceAudit.id == audit_id).first()
        
        if not audit:
            raise HTTPException(status_code=404, detail="合规审计不存在")
        
        return {
            "audit": {
                "id": audit.id,
                "name": audit.name,
                "audit_type": audit.audit_type,
                "status": audit.status,
                "scope": audit.scope,
                "findings": audit.findings,
                "result": audit.result,
                "scheduled_date": audit.scheduled_date.isoformat() if audit.scheduled_date else None,
                "completed_date": audit.completed_date.isoformat() if audit.completed_date else None,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
                "updated_at": audit.updated_at.isoformat() if audit.updated_at else None,
                "created_by": audit.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "获取合规审计")


@router.put("/audits/{audit_id}", summary="更新合规审计")
async def update_audit(
    audit_id: str, audit: ComplianceAuditUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """更新合规审计"""
    try:
        existing_audit = db.query(ComplianceAudit).filter(
            ComplianceAudit.id == audit_id
        ).first()
        
        if not existing_audit:
            raise HTTPException(status_code=404, detail="合规审计不存在")
        
        if audit.name is not None:
            existing_audit.name = audit.name
        if audit.status is not None:
            existing_audit.status = audit.status
        if audit.findings is not None:
            existing_audit.findings = audit.findings
        if audit.result is not None:
            existing_audit.result = audit.result
        if audit.completed_date is not None:
            existing_audit.completed_date = audit.completed_date
        existing_audit.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_audit)
        
        return {
            "status": "success",
            "audit": {
                "id": existing_audit.id,
                "name": existing_audit.name,
                "audit_type": existing_audit.audit_type,
                "status": existing_audit.status,
                "scope": existing_audit.scope,
                "findings": existing_audit.findings,
                "result": existing_audit.result,
                "scheduled_date": existing_audit.scheduled_date.isoformat() if existing_audit.scheduled_date else None,
                "completed_date": existing_audit.completed_date.isoformat() if existing_audit.completed_date else None,
                "created_at": existing_audit.created_at.isoformat() if existing_audit.created_at else None,
                "updated_at": existing_audit.updated_at.isoformat() if existing_audit.updated_at else None,
                "created_by": existing_audit.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "更新合规审计")


@router.delete("/audits/{audit_id}", summary="删除合规审计")
async def delete_audit(
    audit_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """删除合规审计"""
    try:
        audit = db.query(ComplianceAudit).filter(ComplianceAudit.id == audit_id).first()
        
        if not audit:
            raise HTTPException(status_code=404, detail="合规审计不存在")
        
        db.delete(audit)
        db.commit()
        
        return {"status": "success", "message": "合规审计已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "删除合规审计")
