# -*- coding: utf-8 -*-
"""
Documentation Advanced API Router
==================================

Advanced API endpoints for documentation management including:
- Document CRUD operations
- Template management
- Document generation
- Version control
- Review workflow
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from core.authentication import get_current_active_user

router = APIRouter(prefix="/api/v1/documentation", tags=["文档管理"])

# Try to import documentation manager
try:
    from core.documentation_manager import (
        DocStatus,
        DocTemplate,
        DocType,
        get_documentation_manager,
    )

    DOCUMENTATION_AVAILABLE = True
except ImportError:
    DOCUMENTATION_AVAILABLE = False
    logger.warning("Documentation manager not available")


# Pydantic Models
class DocumentCreate(BaseModel):
    """Request model for creating a document"""

    doc_id: Optional[str] = Field(None, description="Document ID (auto-generated if not provided)")
    title: str = Field(..., description="Document title")
    doc_type: str = Field(..., description="Document type")
    content: str = Field(..., description="Document content")
    author: Optional[str] = Field(None, description="Document author")
    version: str = Field(default="1.0", description="Document version")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "API Documentation",
                "doc_type": "api_documentation",
                "content": "# API Documentation\n\n...",
                "author": "John Doe",
                "version": "1.0",
            }
        }
    }


class DocumentUpdate(BaseModel):
    """Request model for updating a document"""

    title: Optional[str] = Field(None, description="Document title")
    content: Optional[str] = Field(None, description="Document content")
    status: Optional[str] = Field(None, description="Document status")
    version: Optional[str] = Field(None, description="Document version")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    model_config = {
        "json_schema_extra": {
            "example": {"title": "Updated API Documentation", "status": "published"}
        }
    }


class TemplateCreate(BaseModel):
    """Request model for creating a template"""

    template_id: Optional[str] = Field(
        None, description="Template ID (auto-generated if not provided)"
    )
    template_name: str = Field(..., description="Template name")
    doc_type: str = Field(..., description="Document type")
    template_content: str = Field(..., description="Template content")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_name": "API Template",
                "doc_type": "api_documentation",
                "template_content": "# {title}\n\n...",
            }
        }
    }


class GeneratorRequest(BaseModel):
    """Request model for document generation"""

    template_id: str = Field(..., description="Template ID to use")
    parameters: Dict[str, Any] = Field(..., description="Generation parameters")
    output_format: str = Field(default="markdown", description="Output format")

    model_config = {
        "json_schema_extra": {
            "example": {
                "template_id": "tpl-001",
                "parameters": {"title": "New API", "version": "1.0"},
                "output_format": "markdown",
            }
        }
    }


class ReviewCreate(BaseModel):
    """Request model for creating a review"""

    document_id: str = Field(..., description="Document ID to review")
    reviewer_id: str = Field(..., description="Reviewer ID")
    comments: str = Field(..., description="Review comments")
    status: str = Field(default="pending", description="Review status")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "doc-001",
                "reviewer_id": "user-001",
                "comments": "Good documentation",
                "status": "approved",
                "rating": 5,
            }
        }
    }


# In-memory storage for advanced features
document_versions: Dict[str, List[Dict[str, Any]]] = {}
document_reviews: Dict[str, List[Dict[str, Any]]] = {}


@router.get(
    "/documents",
    summary="列出所有文档",
    responses={
        200: {"description": "文档列表"},
        500: {"description": "获取失败"},
    },
)
async def list_documents(
    doc_type: Optional[str] = Query(None, description="按文档类型过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    author: Optional[str] = Query(None, description="按作者过滤"),
    limit: int = Query(default=100, ge=1, le=500, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
) -> Dict[str, Any]:
    """
    获取文档列表，支持多种过滤条件
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Convert string to enum if provided
        type_enum = None
        if doc_type:
            try:
                type_enum = DocType(doc_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的文档类型: {doc_type}")

        status_enum = None
        if status:
            try:
                status_enum = DocStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

        documents = manager.list_documents(type_enum, status_enum)

        # Apply additional filters
        if author:
            documents = [doc for doc in documents if doc.get("author") == author]

        # Apply pagination
        total = len(documents)
        paginated_documents = documents[offset : offset + limit]

        return {
            "status": "success",
            "data": {
                "documents": paginated_documents,
                "total": total,
                "limit": limit,
                "offset": offset,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/documents",
    summary="创建新文档",
    responses={
        201: {"description": "文档创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_document(request: DocumentCreate) -> Dict[str, Any]:
    """
    创建新文档
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Generate doc_id if not provided
        doc_id = request.doc_id or f"doc-{uuid4().hex[:8]}"

        # Convert doc_type string to enum
        try:
            type_enum = DocType(request.doc_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的文档类型: {request.doc_type}")

        # Create document
        success = manager.create_document(
            doc_id=doc_id,
            title=request.title,
            doc_type=type_enum,
            content=request.content,
            author=request.author or "System",
            version=request.version,
        )

        if not success:
            raise HTTPException(status_code=400, detail="文档创建失败")

        # Initialize version history
        document_versions[doc_id] = [
            {
                "version": request.version,
                "content": request.content,
                "created_at": datetime.utcnow().isoformat(),
                "author": request.author or "System",
            }
        ]

        return {
            "status": "success",
            "data": {
                "doc_id": doc_id,
                "title": request.title,
                "doc_type": request.doc_type,
                "version": request.version,
                "created": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents/{doc_id}",
    summary="获取文档详情",
    responses={
        200: {"description": "文档详情"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_document(doc_id: str) -> Dict[str, Any]:
    """
    根据ID获取文档详情
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()
        document = manager.get_document(doc_id)

        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        return {
            "status": "success",
            "data": {
                "doc_id": document.doc_id,
                "title": document.title,
                "doc_type": document.doc_type.value,
                "status": document.status.value,
                "version": document.version,
                "author": document.author,
                "content": document.content,
                "last_updated": document.last_updated.isoformat(),
                "metadata": document.metadata,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/documents/{doc_id}",
    summary="更新文档",
    responses={
        200: {"description": "文档更新成功"},
        404: {"description": "文档未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_document(doc_id: str, request: DocumentUpdate) -> Dict[str, Any]:
    """
    更新文档内容或状态
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        # Update content if provided
        if request.content is not None:
            manager.update_document(doc_id, content=request.content, status=None)

            # Add to version history
            if doc_id in document_versions:
                new_version = str(float(document.version) + 0.1)
                document_versions[doc_id].append(
                    {
                        "version": new_version,
                        "content": request.content,
                        "created_at": datetime.utcnow().isoformat(),
                        "author": document.author,
                    }
                )

        # Update status if provided
        if request.status is not None:
            try:
                status_enum = DocStatus(request.status)
                manager.update_document(doc_id, content=None, status=status_enum)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态: {request.status}")

        # Update title if provided
        if request.title is not None:
            document.title = request.title

        # Update version if provided
        if request.version is not None:
            document.version = request.version

        # Update metadata if provided
        if request.metadata is not None:
            document.metadata.update(request.metadata)

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "updated": True, "version": document.version},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/documents/{doc_id}",
    summary="删除文档",
    responses={
        200: {"description": "文档删除成功"},
        404: {"description": "文档未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_document(doc_id: str) -> Dict[str, Any]:
    """
    删除文档
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        # Delete document (set status to deprecated)
        manager.update_document(doc_id, content=None, status=DocStatus.DEPRECATED)

        # Clean up version history
        if doc_id in document_versions:
            del document_versions[doc_id]

        # Clean up reviews
        if doc_id in document_reviews:
            del document_reviews[doc_id]

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "deleted": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="列出所有模板",
    responses={
        200: {"description": "模板列表"},
        500: {"description": "获取失败"},
    },
)
async def list_templates(
    doc_type: Optional[str] = Query(None, description="按文档类型过滤")
) -> Dict[str, Any]:
    """
    获取文档模板列表
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()
        templates = manager.get_available_templates()

        # Filter by doc_type if provided
        if doc_type:
            templates = [t for t in templates if t.get("doc_type") == doc_type]

        return {
            "status": "success",
            "data": {"templates": templates, "count": len(templates)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/templates",
    summary="创建新模板",
    responses={
        201: {"description": "模板创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_template(request: TemplateCreate) -> Dict[str, Any]:
    """
    创建新的文档模板
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Generate template_id if not provided
        template_id = request.template_id or f"tpl-{uuid4().hex[:8]}"

        # Convert doc_type string to enum
        try:
            type_enum = DocType(request.doc_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的文档类型: {request.doc_type}")

        # Create template
        template = DocTemplate(
            template_id=template_id,
            template_name=request.template_name,
            doc_type=type_enum,
            template_content=request.template_content,
            metadata=request.metadata or {},
        )

        manager.templates[template_id] = template

        return {
            "status": "success",
            "data": {
                "template_id": template_id,
                "template_name": request.template_name,
                "doc_type": request.doc_type,
                "created": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generators",
    summary="生成文档",
    responses={
        200: {"description": "文档生成成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "模板未找到"},
        500: {"description": "生成失败"},
    },
)
async def generate_document(request: GeneratorRequest) -> Dict[str, Any]:
    """
    使用模板生成文档
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Get template
        template = manager.templates.get(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板未找到")

        # Generate content by replacing parameters
        content = template.template_content
        for key, value in request.parameters.items():
            content = content.replace(f"{{{key}}}", str(value))

        # Create document
        doc_id = f"doc-{uuid4().hex[:8]}"
        title = request.parameters.get("title", "Generated Document")

        success = manager.create_document(
            doc_id=doc_id,
            title=title,
            doc_type=template.doc_type,
            content=content,
            author="Generator",
            version="1.0",
        )

        if not success:
            raise HTTPException(status_code=500, detail="文档生成失败")

        return {
            "status": "success",
            "data": {
                "doc_id": doc_id,
                "title": title,
                "content": content,
                "output_format": request.output_format,
                "generated": True,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/versions",
    summary="列出文档版本",
    responses={
        200: {"description": "版本列表"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def list_document_versions(doc_id: str = Query(..., description="文档ID")) -> Dict[str, Any]:
    """
    获取文档的版本历史
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        versions = document_versions.get(doc_id, [])

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "versions": versions, "count": len(versions)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing document versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/reviews",
    summary="列出文档评审",
    responses={
        200: {"description": "评审列表"},
        500: {"description": "获取失败"},
    },
)
async def list_reviews(
    document_id: Optional[str] = Query(None, description="按文档ID过滤"),
    reviewer_id: Optional[str] = Query(None, description="按评审者ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Dict[str, Any]:
    """
    获取文档评审列表
    """
    try:
        reviews = []

        for doc_id, doc_reviews in document_reviews.items():
            for review in doc_reviews:
                # Apply filters
                if document_id and review.get("document_id") != document_id:
                    continue
                if reviewer_id and review.get("reviewer_id") != reviewer_id:
                    continue
                if status and review.get("status") != status:
                    continue

                reviews.append(review)

        return {
            "status": "success",
            "data": {"reviews": reviews, "count": len(reviews)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reviews",
    summary="创建文档评审",
    responses={
        201: {"description": "评审创建成功"},
        400: {"description": "请求参数错误"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_review(request: ReviewCreate) -> Dict[str, Any]:
    """
    创建文档评审
    """
    try:
        # Initialize reviews list for document if not exists
        if request.document_id not in document_reviews:
            document_reviews[request.document_id] = []

        # Create review
        review = {
            "review_id": f"rev-{uuid4().hex[:8]}",
            "document_id": request.document_id,
            "reviewer_id": request.reviewer_id,
            "comments": request.comments,
            "status": request.status,
            "rating": request.rating,
            "created_at": datetime.utcnow().isoformat(),
        }

        document_reviews[request.document_id].append(review)

        return {"status": "success", "data": review, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates/{template_id}",
    summary="获取模板详情",
    responses={
        200: {"description": "模板详情"},
        404: {"description": "模板未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_template(template_id: str) -> Dict[str, Any]:
    """
    根据ID获取模板详情
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()
        template = manager.templates.get(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="模板未找到")

        return {
            "status": "success",
            "data": {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "doc_type": template.doc_type.value,
                "template_content": template.template_content,
                "metadata": template.metadata,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/templates/{template_id}",
    summary="更新模板",
    responses={
        200: {"description": "模板更新成功"},
        404: {"description": "模板未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_template(
    template_id: str,
    template_name: Optional[str] = None,
    template_content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    更新模板内容或元数据
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()
        template = manager.templates.get(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="模板未找到")

        # Update fields if provided
        if template_name is not None:
            template.template_name = template_name
        if template_content is not None:
            template.template_content = template_content
        if metadata is not None:
            template.metadata.update(metadata)

        return {
            "status": "success",
            "data": {"template_id": template_id, "updated": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/templates/{template_id}",
    summary="删除模板",
    responses={
        200: {"description": "模板删除成功"},
        404: {"description": "模板未找到"},
        500: {"description": "删除失败"},
    },
)
async def delete_template(template_id: str) -> Dict[str, Any]:
    """
    删除模板
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()
        template = manager.templates.get(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="模板未找到")

        # Delete template
        del manager.templates[template_id]

        return {
            "status": "success",
            "data": {"template_id": template_id, "deleted": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents/{doc_id}/versions",
    summary="列出文档版本",
    responses={
        200: {"description": "版本列表"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def list_document_versions_by_doc_id(doc_id: str) -> Dict[str, Any]:
    """
    获取文档的版本历史（按文档ID路径）
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        versions = document_versions.get(doc_id, [])

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "versions": versions, "count": len(versions)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing document versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents/{doc_id}/versions/{version_id}",
    summary="获取版本详情",
    responses={
        200: {"description": "版本详情"},
        404: {"description": "版本未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_document_version(doc_id: str, version_id: str) -> Dict[str, Any]:
    """
    获取特定版本的文档详情
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        versions = document_versions.get(doc_id, [])

        # Find version by version_id (could be version string or index)
        version_data = None
        for version in versions:
            if version.get("version") == version_id or str(versions.index(version)) == version_id:
                version_data = version
                break

        if not version_data:
            raise HTTPException(status_code=404, detail="版本未找到")

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "version": version_data},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents/{doc_id}/reviews",
    summary="列出文档评审",
    responses={
        200: {"description": "评审列表"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def list_document_reviews(
    doc_id: str,
    reviewer_id: Optional[str] = Query(None, description="按评审者ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
) -> Dict[str, Any]:
    """
    获取文档的评审列表（按文档ID路径）
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        reviews = document_reviews.get(doc_id, [])

        # Apply filters
        if reviewer_id:
            reviews = [r for r in reviews if r.get("reviewer_id") == reviewer_id]
        if status:
            reviews = [r for r in reviews if r.get("status") == status]

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "reviews": reviews, "count": len(reviews)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing document reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/documents/{doc_id}/reviews",
    summary="创建文档评审",
    responses={
        201: {"description": "评审创建成功"},
        400: {"description": "请求参数错误"},
        404: {"description": "文档未找到"},
        500: {"description": "创建失败"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_document_review(doc_id: str, request: ReviewCreate) -> Dict[str, Any]:
    """
    为指定文档创建评审（按文档ID路径）
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        manager = get_documentation_manager()

        # Check if document exists
        document = manager.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="文档未找到")

        # Initialize reviews list for document if not exists
        if doc_id not in document_reviews:
            document_reviews[doc_id] = []

        # Create review with document_id from path
        review = {
            "review_id": f"rev-{uuid4().hex[:8]}",
            "document_id": doc_id,
            "reviewer_id": request.reviewer_id,
            "comments": request.comments,
            "status": request.status,
            "rating": request.rating,
            "created_at": datetime.utcnow().isoformat(),
        }

        document_reviews[doc_id].append(review)

        return {"status": "success", "data": review, "timestamp": datetime.utcnow().isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating document review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/documents/{doc_id}/reviews/{review_id}",
    summary="更新文档评审",
    responses={
        200: {"description": "评审更新成功"},
        404: {"description": "评审未找到"},
        400: {"description": "请求参数错误"},
        500: {"description": "更新失败"},
    },
)
async def update_document_review(
    doc_id: str,
    review_id: str,
    comments: Optional[str] = None,
    status: Optional[str] = None,
    rating: Optional[int] = None,
) -> Dict[str, Any]:
    """
    更新文档评审
    """
    if not DOCUMENTATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="文档管理器不可用")

    try:
        # Check if document has reviews
        if doc_id not in document_reviews:
            raise HTTPException(status_code=404, detail="文档评审未找到")

        # Find review
        review = None
        for r in document_reviews[doc_id]:
            if r.get("review_id") == review_id:
                review = r
                break

        if not review:
            raise HTTPException(status_code=404, detail="评审未找到")

        # Update fields if provided
        if comments is not None:
            review["comments"] = comments
        if status is not None:
            review["status"] = status
        if rating is not None:
            review["rating"] = rating

        return {
            "status": "success",
            "data": {"review_id": review_id, "updated": True},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document review: {e}")
        raise HTTPException(status_code=500, detail=str(e))
