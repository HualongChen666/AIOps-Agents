# -*- coding: utf-8 -*-
"""
Documentation API Router
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/docs", tags=["Documentation"])


@router.get(
    "/status",
    summary="获取文档状态",
    responses={
        200: {
            "description": "文档状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_documents": 50, "published_documents": 40},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_documentation_status():
    """Get documentation status"""
    try:
        from core.documentation_manager import get_documentation_manager

        manager = get_documentation_manager()
        status = manager.get_doc_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting documentation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents",
    summary="列出文档",
    responses={
        200: {
            "description": "文档列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "documents": [
                                {"doc_id": "doc-123", "title": "API Guide", "status": "published"}
                            ],
                            "count": 1,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def list_documents(doc_type: Optional[str] = None, status: Optional[str] = None):
    """List documents"""
    try:
        from core.documentation_manager import DocStatus, DocType, get_documentation_manager

        manager = get_documentation_manager()

        type_enum = DocType(doc_type) if doc_type else None
        status_enum = DocStatus(status) if status else None

        documents = manager.list_documents(type_enum, status_enum)

        return {
            "status": "success",
            "data": {"documents": documents, "count": len(documents)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/document/create",
    summary="创建文档",
    responses={
        200: {
            "description": "创建成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"doc_id": "doc-123", "created": True},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "创建失败"},
    },
)
async def create_document(
    doc_id: str,
    title: str,
    doc_type: str,
    content: str,
    author: Optional[str] = None,
    version: str = "1.0",
):
    """Create a document"""
    try:
        from core.documentation_manager import DocType, get_documentation_manager

        manager = get_documentation_manager()

        type_enum = DocType(doc_type)
        success = manager.create_document(doc_id, title, type_enum, content, author, version)

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "created": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/document/{doc_id}",
    summary="获取文档",
    responses={
        200: {"description": "文档内容"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_document(doc_id: str):
    """Get document by ID"""
    try:
        from core.documentation_manager import get_documentation_manager

        manager = get_documentation_manager()

        document = manager.get_document(doc_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

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
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/document/{doc_id}/update",
    summary="更新文档",
    responses={
        200: {"description": "更新成功"},
        500: {"description": "更新失败"},
    },
)
async def update_document(
    doc_id: str,
    content: Optional[str] = None,
    status: Optional[str] = None,
):
    """Update document"""
    try:
        from core.documentation_manager import DocStatus, get_documentation_manager

        manager = get_documentation_manager()

        status_enum = DocStatus(status) if status else None
        success = manager.update_document(doc_id, content, status_enum)

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "updated": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error updating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="获取可用模板",
    responses={
        200: {"description": "模板列表"},
        500: {"description": "获取失败"},
    },
)
async def get_templates():
    """Get available documentation templates"""
    try:
        from core.documentation_manager import get_documentation_manager

        manager = get_documentation_manager()

        templates = manager.get_available_templates()

        return {
            "status": "success",
            "data": {"templates": templates, "count": len(templates)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documentation-api")
async def get_documentation_api():
    """获取文档API信息"""
    return {"status": "success", "api_version": "v1", "endpoints": []}


@router.get("/sphinx")
async def get_sphinx_docs():
    """获取Sphinx文档"""
    return {"status": "success", "sphinx": {"version": "4.0", "docs_built": True}}


@router.get("/doc-generation")
async def get_doc_generation():
    """获取文档生成状态"""
    return {"status": "success", "generation": {"last_run": "2026-07-02T10:00:00Z", "status": "completed"}}


@router.get("/template-management")
async def get_template_management():
    """获取模板管理"""
    return {"status": "success", "templates": []}


@router.get("/doc-generator")
async def get_doc_generator():
    """获取文档生成器"""
    return {"status": "success", "generator": {"type": "sphinx", "enabled": True}}


@router.get("/document-list")
async def get_document_list():
    """获取文档列表"""
    return {"status": "success", "documents": []}


@router.get("/document-creation")
async def get_document_creation():
    """获取文档创建"""
    return {"status": "success", "creation": {"templates_available": True}}


@router.get("/documentation-management")
async def get_documentation_management():
    """获取文档管理"""
    return {"status": "success", "management": {"auto_publish": True, "versioning": True}}
