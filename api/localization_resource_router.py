# -*- coding: utf-8 -*-
"""
Localization Resource API Router
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/localization", tags=["Localization"])


@router.get(
    "/status",
    summary="获取本地化资源状态",
    responses={
        200: {
            "description": "资源状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"total_languages": 3, "total_translations": 1000},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_resource_status():
    """Get localization resource status"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        status = manager.get_resource_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting resource status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/translations",
    summary="获取翻译",
    responses={
        200: {
            "description": "翻译内容",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "language": "zh-CN",
                            "namespace": "common",
                            "translations": {"hello": "你好", "world": "世界"},
                            "count": 2,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        404: {"description": "翻译未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_translations(language: str, namespace: str):
    """Get translations for a language and namespace"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        translations = manager.get_translations(language, namespace)
        if not translations:
            raise HTTPException(status_code=404, detail="Translations not found")
        return {
            "status": "success",
            "data": {
                "language": language,
                "namespace": namespace,
                "translations": translations,
                "count": len(translations),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translation/add",
    summary="添加翻译",
    responses={
        200: {
            "description": "添加成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "language": "zh-CN",
                            "namespace": "common",
                            "key": "hello",
                            "added": True,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "添加失败"},
    },
)
async def add_translation(language: str, namespace: str, key: str, value: str):
    """Add a translation entry"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        success = manager.add_translation(language, namespace, key, value)
        return {
            "status": "success",
            "data": {"language": language, "namespace": namespace, "key": key, "added": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error adding translation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translation/export",
    summary="导出翻译",
    responses={
        200: {
            "description": "导出成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "export_path": "/app/data/translations.json",
                            "count": 100,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "导出失败"},
    },
)
async def export_translations(language: str, namespace: str, output_path: str):
    """Export translations to JSON file"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        success = manager.export_translations(language, namespace, output_path)
        return {
            "status": "success",
            "data": {
                "language": language,
                "namespace": namespace,
                "output_path": output_path,
                "exported": success,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error exporting translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translation/import",
    summary="导入翻译",
    responses={
        200: {"description": "导入成功"},
        500: {"description": "导入失败"},
    },
)
async def import_translations(language: str, namespace: str, input_path: str):
    """Import translations from JSON file"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        success = manager.import_translations(language, namespace, input_path)
        return {
            "status": "success",
            "data": {
                "language": language,
                "namespace": namespace,
                "input_path": input_path,
                "imported": success,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error importing translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/translations/missing",
    summary="获取缺失的翻译",
    responses={
        200: {"description": "缺失的翻译键"},
        500: {"description": "获取失败"},
    },
)
async def get_missing_translations(source_language: str, target_language: str, namespace: str):
    """Get missing translations for target language"""
    try:
        from core.localization_resource_manager import get_resource_manager

        manager = get_resource_manager()
        missing = manager.get_missing_translations(source_language, target_language, namespace)
        return {
            "status": "success",
            "data": {
                "source_language": source_language,
                "target_language": target_language,
                "namespace": namespace,
                "missing_keys": missing,
                "count": len(missing),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting missing translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
