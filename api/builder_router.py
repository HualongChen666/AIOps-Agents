# -*- coding: utf-8 -*-
"""
Builder Router Module
====================

Provides API endpoints for builder functionality.
Supports template, project, and component management.

Endpoints:
- GET /api/v1/builder/templates - Get all builder templates
- POST /api/v1/builder/templates - Create new builder template
- GET /api/v1/builder/templates/{id} - Get template by ID
- PUT /api/v1/builder/templates/{id} - Update template
- DELETE /api/v1/builder/templates/{id} - Delete template
- GET /api/v1/builder/projects - Get all builder projects
- POST /api/v1/builder/projects - Create new builder project
- GET /api/v1/builder/projects/{id} - Get project by ID
- PUT /api/v1/builder/projects/{id} - Update project
- DELETE /api/v1/builder/projects/{id} - Delete project
- GET /api/v1/builder/components - Get all builder components
- POST /api/v1/builder/components - Create new builder component
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
from core.models import BuilderTemplate, BuilderProject, BuilderComponent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/builder", tags=["构建器"])


# ============================================================================
# Pydantic Models
# ============================================================================


class BuilderTemplateCreate(BaseModel):
    """构建器模板创建模型"""

    name: str = Field(..., min_length=1, max_length=200, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, description="模板分类")
    template_data: Dict[str, Any] = Field(..., description="模板数据")
    components: Optional[Dict[str, Any]] = Field(None, description="组件配置")
    is_public: bool = Field(False, description="是否公开")


class BuilderTemplateUpdate(BaseModel):
    """构建器模板更新模型"""

    name: Optional[str] = Field(None, max_length=200, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    category: Optional[str] = Field(None, description="模板分类")
    template_data: Optional[Dict[str, Any]] = Field(None, description="模板数据")
    components: Optional[Dict[str, Any]] = Field(None, description="组件配置")
    is_public: Optional[bool] = Field(None, description="是否公开")


class BuilderProjectCreate(BaseModel):
    """构建器项目创建模型"""

    name: str = Field(..., min_length=1, max_length=200, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    template_id: Optional[str] = Field(None, description="模板ID")
    project_data: Dict[str, Any] = Field(..., description="项目数据")


class BuilderProjectUpdate(BaseModel):
    """构建器项目更新模型"""

    name: Optional[str] = Field(None, max_length=200, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    project_data: Optional[Dict[str, Any]] = Field(None, description="项目数据")
    status: Optional[str] = Field(None, description="项目状态")


class BuilderComponentCreate(BaseModel):
    """构建器组件创建模型"""

    name: str = Field(..., min_length=1, max_length=200, description="组件名称")
    component_type: str = Field(..., description="组件类型")
    config: Dict[str, Any] = Field(..., description="组件配置")
    properties: Optional[Dict[str, Any]] = Field(None, description="组件属性")


class BuilderComponentUpdate(BaseModel):
    """构建器组件更新模型"""

    name: Optional[str] = Field(None, max_length=200, description="组件名称")
    component_type: Optional[str] = Field(None, description="组件类型")
    config: Optional[Dict[str, Any]] = Field(None, description="组件配置")
    properties: Optional[Dict[str, Any]] = Field(None, description="组件属性")


# ============================================================================
# Template Endpoints
# ============================================================================


@router.get("/templates", summary="获取所有构建器模板")
async def get_templates(
    category: Optional[str] = Query(None, description="分类过滤"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取所有构建器模板"""
    try:
        query = db.query(BuilderTemplate)
        
        if category:
            query = query.filter(BuilderTemplate.category == category)
        if is_public is not None:
            query = query.filter(BuilderTemplate.is_public == is_public)
        
        total = query.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        templates = query.offset(start_idx).limit(page_size).all()
        
        return {
            "templates": [
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "template_data": template.template_data,
                    "components": template.components,
                    "is_public": template.is_public,
                    "created_at": template.created_at.isoformat() if template.created_at else None,
                    "updated_at": template.updated_at.isoformat() if template.updated_at else None,
                    "created_by": template.created_by,
                }
                for template in templates
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        handle_service_error(e, "获取构建器模板列表")


@router.post("/templates", summary="创建构建器模板")
async def create_template(
    template: BuilderTemplateCreate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """创建新的构建器模板"""
    try:
        new_template = BuilderTemplate(
            id=str(uuid.uuid4()),
            name=template.name,
            description=template.description,
            category=template.category,
            template_data=template.template_data,
            components=template.components,
            is_public=template.is_public,
            created_by="system",
        )
        db.add(new_template)
        db.commit()
        db.refresh(new_template)
        
        return {
            "status": "success",
            "template": {
                "id": new_template.id,
                "name": new_template.name,
                "description": new_template.description,
                "category": new_template.category,
                "template_data": new_template.template_data,
                "components": new_template.components,
                "is_public": new_template.is_public,
                "created_at": new_template.created_at.isoformat() if new_template.created_at else None,
                "updated_at": new_template.updated_at.isoformat() if new_template.updated_at else None,
                "created_by": new_template.created_by,
            }
        }
    except Exception as e:
        db.rollback()
        handle_service_error(e, "创建构建器模板")


@router.get("/templates/{template_id}", summary="获取单个构建器模板")
async def get_template(
    template_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取单个构建器模板"""
    try:
        template = db.query(BuilderTemplate).filter(BuilderTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="构建器模板不存在")
        
        return {
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "template_data": template.template_data,
                "components": template.components,
                "is_public": template.is_public,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None,
                "created_by": template.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "获取构建器模板")


@router.put("/templates/{template_id}", summary="更新构建器模板")
async def update_template(
    template_id: str, template: BuilderTemplateUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """更新构建器模板"""
    try:
        existing_template = db.query(BuilderTemplate).filter(
            BuilderTemplate.id == template_id
        ).first()
        
        if not existing_template:
            raise HTTPException(status_code=404, detail="构建器模板不存在")
        
        if template.name is not None:
            existing_template.name = template.name
        if template.description is not None:
            existing_template.description = template.description
        if template.category is not None:
            existing_template.category = template.category
        if template.template_data is not None:
            existing_template.template_data = template.template_data
        if template.components is not None:
            existing_template.components = template.components
        if template.is_public is not None:
            existing_template.is_public = template.is_public
        existing_template.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_template)
        
        return {
            "status": "success",
            "template": {
                "id": existing_template.id,
                "name": existing_template.name,
                "description": existing_template.description,
                "category": existing_template.category,
                "template_data": existing_template.template_data,
                "components": existing_template.components,
                "is_public": existing_template.is_public,
                "created_at": existing_template.created_at.isoformat() if existing_template.created_at else None,
                "updated_at": existing_template.updated_at.isoformat() if existing_template.updated_at else None,
                "created_by": existing_template.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "更新构建器模板")


@router.delete("/templates/{template_id}", summary="删除构建器模板")
async def delete_template(
    template_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """删除构建器模板"""
    try:
        template = db.query(BuilderTemplate).filter(BuilderTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="构建器模板不存在")
        
        db.delete(template)
        db.commit()
        
        return {"status": "success", "message": "构建器模板已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "删除构建器模板")


# ============================================================================
# Project Endpoints
# ============================================================================


@router.get("/projects", summary="获取所有构建器项目")
async def get_projects(
    status: Optional[str] = Query(None, description="状态过滤"),
    template_id: Optional[str] = Query(None, description="模板ID过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取所有构建器项目"""
    try:
        query = db.query(BuilderProject)
        
        if status:
            query = query.filter(BuilderProject.status == status)
        if template_id:
            query = query.filter(BuilderProject.template_id == template_id)
        
        total = query.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        projects = query.offset(start_idx).limit(page_size).all()
        
        return {
            "projects": [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "template_id": project.template_id,
                    "project_data": project.project_data,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    "created_by": project.created_by,
                }
                for project in projects
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        handle_service_error(e, "获取构建器项目列表")


@router.post("/projects", summary="创建构建器项目")
async def create_project(
    project: BuilderProjectCreate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """创建新的构建器项目"""
    try:
        new_project = BuilderProject(
            id=str(uuid.uuid4()),
            name=project.name,
            description=project.description,
            template_id=project.template_id,
            project_data=project.project_data,
            status="draft",
            created_by="system",
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        return {
            "status": "success",
            "project": {
                "id": new_project.id,
                "name": new_project.name,
                "description": new_project.description,
                "template_id": new_project.template_id,
                "project_data": new_project.project_data,
                "status": new_project.status,
                "created_at": new_project.created_at.isoformat() if new_project.created_at else None,
                "updated_at": new_project.updated_at.isoformat() if new_project.updated_at else None,
                "created_by": new_project.created_by,
            }
        }
    except Exception as e:
        db.rollback()
        handle_service_error(e, "创建构建器项目")


@router.get("/projects/{project_id}", summary="获取单个构建器项目")
async def get_project(
    project_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取单个构建器项目"""
    try:
        project = db.query(BuilderProject).filter(BuilderProject.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="构建器项目不存在")
        
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "template_id": project.template_id,
                "project_data": project.project_data,
                "status": project.status,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "created_by": project.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_service_error(e, "获取构建器项目")


@router.put("/projects/{project_id}", summary="更新构建器项目")
async def update_project(
    project_id: str, project: BuilderProjectUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """更新构建器项目"""
    try:
        existing_project = db.query(BuilderProject).filter(
            BuilderProject.id == project_id
        ).first()
        
        if not existing_project:
            raise HTTPException(status_code=404, detail="构建器项目不存在")
        
        if project.name is not None:
            existing_project.name = project.name
        if project.description is not None:
            existing_project.description = project.description
        if project.project_data is not None:
            existing_project.project_data = project.project_data
        if project.status is not None:
            existing_project.status = project.status
        existing_project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing_project)
        
        return {
            "status": "success",
            "project": {
                "id": existing_project.id,
                "name": existing_project.name,
                "description": existing_project.description,
                "template_id": existing_project.template_id,
                "project_data": existing_project.project_data,
                "status": existing_project.status,
                "created_at": existing_project.created_at.isoformat() if existing_project.created_at else None,
                "updated_at": existing_project.updated_at.isoformat() if existing_project.updated_at else None,
                "created_by": existing_project.created_by,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "更新构建器项目")


@router.delete("/projects/{project_id}", summary="删除构建器项目")
async def delete_project(
    project_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """删除构建器项目"""
    try:
        project = db.query(BuilderProject).filter(BuilderProject.id == project_id).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="构建器项目不存在")
        
        db.delete(project)
        db.commit()
        
        return {"status": "success", "message": "构建器项目已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        handle_service_error(e, "删除构建器项目")


# ============================================================================
# Component Endpoints
# ============================================================================


@router.get("/components", summary="获取所有构建器组件")
async def get_components(
    component_type: Optional[str] = Query(None, description="组件类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """获取所有构建器组件"""
    try:
        query = db.query(BuilderComponent)
        
        if component_type:
            query = query.filter(BuilderComponent.component_type == component_type)
        
        total = query.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        components = query.offset(start_idx).limit(page_size).all()
        
        return {
            "components": [
                {
                    "id": component.id,
                    "name": component.name,
                    "component_type": component.component_type,
                    "config": component.config,
                    "properties": component.properties,
                    "created_at": component.created_at.isoformat() if component.created_at else None,
                    "updated_at": component.updated_at.isoformat() if component.updated_at else None,
                    "created_by": component.created_by,
                }
                for component in components
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        handle_service_error(e, "获取构建器组件列表")


@router.post("/components", summary="创建构建器组件")
async def create_component(
    component: BuilderComponentCreate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """创建新的构建器组件"""
    try:
        new_component = BuilderComponent(
            id=str(uuid.uuid4()),
            name=component.name,
            component_type=component.component_type,
            config=component.config,
            properties=component.properties,
            created_by="system",
        )
        db.add(new_component)
        db.commit()
        db.refresh(new_component)
        
        return {
            "status": "success",
            "component": {
                "id": new_component.id,
                "name": new_component.name,
                "component_type": new_component.component_type,
                "config": new_component.config,
                "properties": new_component.properties,
                "created_at": new_component.created_at.isoformat() if new_component.created_at else None,
                "updated_at": new_component.updated_at.isoformat() if new_component.updated_at else None,
                "created_by": new_component.created_by,
            }
        }
    except Exception as e:
        db.rollback()
        handle_service_error(e, "创建构建器组件")
