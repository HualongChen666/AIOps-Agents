# -*- coding: utf-8 -*-
"""
Documentation Generator API Router
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/doc-generator", tags=["Documentation Generator"])


@router.get(
    "/status",
    summary="获取文档生成器状态",
    responses={
        200: {
            "description": "生成器状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"available": True, "total_templates": 5},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取状态失败"},
    },
)
async def get_generator_status():
    """Get generator status"""
    try:
        from core.documentation_generator import get_documentation_generator

        generator = get_documentation_generator()
        status = generator.get_generator_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting generator status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/templates",
    summary="获取可用模板",
    responses={
        200: {
            "description": "模板列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "templates": ["api-doc", "user-guide", "deployment-guide"],
                            "count": 3,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_generator_templates():
    """Get available generator templates"""
    try:
        from core.documentation_generator import get_documentation_generator

        generator = get_documentation_generator()

        templates = generator.get_available_templates()

        return {
            "status": "success",
            "data": {"templates": templates, "count": len(templates)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting generator templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/document/generate",
    summary="生成文档",
    responses={
        200: {
            "description": "文档生成结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "doc_id": "doc-123",
                            "title": "API Documentation",
                            "generator_type": "markdown",
                            "generated_at": "2026-07-03T09:00:00Z",
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        404: {"description": "生成失败"},
        500: {"description": "生成失败"},
    },
)
async def generate_document(
    doc_id: str,
    title: str,
    template_name: str,
    content_vars: dict,
    generator_type: Optional[str] = None,
):
    """Generate document from template"""
    try:
        from core.documentation_generator import GeneratorType, get_documentation_generator

        generator = get_documentation_generator()

        type_enum = GeneratorType(generator_type) if generator_type else None
        generated_doc = generator.generate_document(
            doc_id, title, template_name, content_vars, type_enum
        )

        if not generated_doc:
            raise HTTPException(status_code=404, detail="Failed to generate document")

        return {
            "status": "success",
            "data": {
                "doc_id": generated_doc.doc_id,
                "title": generated_doc.title,
                "generator_type": generated_doc.generator_type.value,
                "generated_at": generated_doc.generated_at.isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/document/{doc_id}",
    summary="获取生成的文档",
    responses={
        200: {"description": "文档内容"},
        404: {"description": "文档未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_generated_document(doc_id: str):
    """Get generated document by ID"""
    try:
        from core.documentation_generator import get_documentation_generator

        generator = get_documentation_generator()

        generated_doc = generator.get_generated_document(doc_id)

        if not generated_doc:
            raise HTTPException(status_code=404, detail="Generated document not found")

        return {
            "status": "success",
            "data": {
                "doc_id": generated_doc.doc_id,
                "title": generated_doc.title,
                "generator_type": generated_doc.generator_type.value,
                "content": generated_doc.content,
                "generated_at": generated_doc.generated_at.isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generated document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/document/{doc_id}/save",
    summary="保存生成的文档",
    responses={
        200: {"description": "保存成功"},
        500: {"description": "保存失败"},
    },
)
async def save_generated_document(doc_id: str, output_path: str):
    """Save generated document to file"""
    try:
        from core.documentation_generator import get_documentation_generator

        generator = get_documentation_generator()

        success = generator.save_generated_document(doc_id, output_path)

        return {
            "status": "success",
            "data": {"doc_id": doc_id, "output_path": output_path, "saved": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error saving generated document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/documents",
    summary="列出所有生成的文档",
    responses={
        200: {"description": "文档列表"},
        500: {"description": "获取失败"},
    },
)
async def list_generated_documents():
    """List all generated documents"""
    try:
        from core.documentation_generator import get_documentation_generator

        generator = get_documentation_generator()

        documents = generator.list_generated_documents()

        return {
            "status": "success",
            "data": {"documents": documents, "count": len(documents)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing generated documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
