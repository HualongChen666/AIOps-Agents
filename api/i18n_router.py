# -*- coding: utf-8 -*-
"""
Internationalization API Router
Provides API endpoints for internationalization management
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/i18n", tags=["Internationalization"])


@router.get(
    "/status",
    summary="获取国际化状态",
    responses={
        200: {
            "description": "国际化状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"enabled": True, "default_locale": "zh-CN", "total_locales": 5},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_i18n_status():
    """
    Get internationalization system status

    Returns:
        I18n system status
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()
        status = manager.get_i18n_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting i18n status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/locales",
    summary="获取支持的语言环境",
    responses={
        200: {
            "description": "语言环境列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"locales": ["zh-CN", "en-US", "ja-JP"], "count": 3},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_supported_locales():
    """
    Get list of supported locales

    Returns:
        List of supported locales
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()
        locales = manager.get_supported_locales()
        return {
            "status": "success",
            "data": {"locales": locales, "count": len(locales)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting locales: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/locales/{locale_id}",
    summary="获取语言环境信息",
    responses={
        200: {
            "description": "语言环境信息",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"locale_id": "zh-CN", "name": "简体中文", "enabled": True},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_locale_info(locale_id: str):
    """
    Get locale information

    Args:
        locale_id: Locale identifier

    Returns:
        Locale information
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        locale_info = manager.get_supported_locales()

        return {
            "status": "success",
            "data": {"locale_id": locale_id, "locales": locale_info},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting locale info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/locale/set",
    summary="设置当前语言环境",
    responses={
        200: {
            "description": "设置成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"locale_id": "zh-CN", "set": True},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "设置失败"},
    },
)
async def set_current_locale(locale_id: str):
    """
    Set current locale

    Args:
        locale_id: Locale identifier

    Returns:
        Set result
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        success = manager.set_current_locale(locale_id)

        return {
            "status": "success",
            "data": {"locale_id": locale_id, "set": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting locale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/translate",
    summary="翻译文本",
    responses={
        200: {
            "description": "翻译结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "key": "welcome_message",
                            "namespace": "common",
                            "language": "zh-CN",
                            "translation": "欢迎使用",
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "翻译失败"},
    },
)
async def translate(key: str, namespace: str = "common", language: Optional[str] = None):
    """
    Translate a key to target language

    Args:
        key: Translation key
        namespace: Translation namespace
        language: Target language

    Returns:
        Translated string
    """
    try:
        from core.i18n_manager import Language, get_i18n_manager

        manager = get_i18n_manager()

        lang_enum = Language(language) if language else None
        translated = manager.translate(key, namespace, lang_enum)

        return {
            "status": "success",
            "data": {
                "key": key,
                "namespace": namespace,
                "language": language,
                "translation": translated,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error translating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/translate",
    summary="更新翻译文本",
    responses={
        200: {"description": "更新结果"},
        400: {"description": "参数无效"},
        500: {"description": "更新失败"},
    },
)
async def update_translation(
    key: str,
    translation: str,
    namespace: str = "common",
    language: Optional[str] = None,
):
    """Update a translation for a key/namespace/language."""
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()
        if language and language in manager.locales:
            target_locale = language
        elif manager.current_locale:
            target_locale = next(
                (
                    lid
                    for lid, loc in manager.locales.items()
                    if loc.language == manager.current_locale.language
                ),
                "zh-CN",
            )
        else:
            target_locale = "zh-CN"
        success = manager.set_translation(target_locale, namespace, key, translation)
        if not success:
            raise HTTPException(status_code=400, detail=f"Locale {target_locale} not supported")

        return {
            "status": "success",
            "data": {
                "key": key,
                "namespace": namespace,
                "language": target_locale,
                "translation": translation,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating translation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/number",
    summary="格式化数字",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_number(number: float, locale: Optional[str] = None, decimals: int = 2):
    """
    Format number according to locale

    Args:
        number: Number to format
        locale: Locale identifier
        decimals: Number of decimal places

    Returns:
        Formatted number string
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        # Convert locale string to Locale object if provided
        locale_obj = None
        if locale:
            locale_obj = manager.locales.get(locale)

        formatted = manager.format_number(number, locale_obj)

        return {
            "status": "success",
            "data": {"number": number, "locale": locale, "formatted": formatted},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting number: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/currency",
    summary="格式化货币",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_currency(amount: float, locale: Optional[str] = None):
    """
    Format currency according to locale

    Args:
        amount: Amount to format
        locale: Locale identifier

    Returns:
        Formatted currency string
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        # Convert locale string to Locale object if provided
        locale_obj = None
        if locale:
            locale_obj = manager.locales.get(locale)

        formatted = manager.format_currency(amount, locale_obj)

        return {
            "status": "success",
            "data": {"amount": amount, "locale": locale, "formatted": formatted},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/date",
    summary="格式化日期",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_date(date_str: str, locale: Optional[str] = None):
    """
    Format date according to locale

    Args:
        date_str: Date string (ISO format)
        locale: Locale identifier

    Returns:
        Formatted date string
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        date_obj = datetime.fromisoformat(date_str)

        # Convert locale string to Locale object if provided
        locale_obj = None
        if locale:
            locale_obj = manager.locales.get(locale)

        formatted = manager.format_date(date_obj, locale_obj)

        return {
            "status": "success",
            "data": {"date": date_str, "locale": locale, "formatted": formatted},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locale-switching")
async def get_locale_switching():
    """获取语言切换"""
    return {"status": "success", "locale_switching": {"current": "zh-CN", "available": ["zh-CN", "en-US"]}}


@router.get("/resource-management")
async def get_resource_management():
    """获取资源管理"""
    return {"status": "success", "resources": {"translations": 1000, "keys": 500}}


@router.get("/localization-resource")
async def get_localization_resource():
    """获取本地化资源"""
    return {"status": "success", "localization_resources": []}


@router.get("/currency-format")
async def get_currency_format():
    """获取货币格式"""
    return {"status": "success", "currency_format": {"symbol": "$", "locale": "en-US"}}


@router.get("/date-format")
async def get_date_format():
    """获取日期格式"""
    return {"status": "success", "date_format": {"format": "YYYY-MM-DD", "locale": "zh-CN"}}


@router.get("/localization-adapter")
async def get_localization_adapter():
    """获取本地化适配器"""
    return {"status": "success", "adapter": {"enabled": True, "type": "auto"}}


@router.get("/formatting")
async def get_formatting():
    """获取格式化"""
    return {"status": "success", "formatting": {"number": "1,000.00", "date": "2026-07-02"}}


@router.get("/translation")
async def get_translation():
    """获取翻译"""
    return {"status": "success", "translation": {"source": "en", "target": "zh"}}


@router.get("/language-support")
async def get_language_support():
    """获取语言支持"""
    return {"status": "success", "languages": ["zh-CN", "en-US", "ja-JP"]}


@router.get("/i18n-management")
async def get_i18n_management():
    """获取i18n管理"""
    return {"status": "success", "management": {"auto_detect": True, "fallback": "en-US"}}
