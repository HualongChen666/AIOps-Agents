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


@router.post(
    "/locale/add",
    summary="添加新的语言环境",
    responses={
        200: {"description": "添加成功"},
        400: {"description": "参数无效"},
        500: {"description": "添加失败"},
    },
)
async def add_locale(
    locale_id: str,
    language: str,
    region: str,
    timezone: str,
    number_format: str = "#,##0.##",
    date_format: str = "YYYY-MM-DD HH:mm:ss",
    currency: str = "USD",
):
    """
    Add a new locale

    Args:
        locale_id: Locale identifier (e.g., "en-US")
        language: Language code (e.g., "en")
        region: Region code (e.g., "US")
        timezone: Timezone (e.g., "America/New_York")
        number_format: Number format string
        date_format: Date format string
        currency: Currency code

    Returns:
        Addition result
    """
    try:
        from core.i18n_manager import Language, Locale, TimeZone, get_i18n_manager

        manager = get_i18n_manager()

        # Validate language enum
        try:
            language_enum = Language(language)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid language code: {language}")

        # Validate timezone enum
        try:
            timezone_enum = TimeZone(timezone)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone}")

        # Create locale
        locale = Locale(
            language=language_enum,
            region=region,
            timezone=timezone_enum,
            number_format=number_format,
            date_format=date_format,
            currency=currency,
        )

        success = manager.add_locale(locale_id, locale)

        if not success:
            raise HTTPException(status_code=400, detail=f"Locale {locale_id} already exists")

        logger.info(f"Added locale: {locale_id}")

        return {
            "status": "success",
            "data": {
                "locale_id": locale_id,
                "language": language,
                "region": region,
                "added": success,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding locale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/locale/detect",
    summary="从请求检测语言环境",
    responses={
        200: {"description": "检测结果"},
        500: {"description": "检测失败"},
    },
)
async def detect_locale(
    accept_language: Optional[str] = None, user_timezone: Optional[str] = None
):
    """
    Detect locale from request headers

    Args:
        accept_language: Accept-Language header value
        user_timezone: User timezone

    Returns:
        Detected locale
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        detected_locale = manager.detect_locale_from_request(accept_language, user_timezone)

        return {
            "status": "success",
            "data": {
                "accept_language": accept_language,
                "user_timezone": user_timezone,
                "detected_locale": detected_locale,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error detecting locale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/translation/resource/add",
    summary="添加翻译资源",
    responses={
        200: {"description": "添加成功"},
        400: {"description": "参数无效"},
        500: {"description": "添加失败"},
    },
)
async def add_translation_resource(
    language: str,
    namespace: str,
    translations: dict,
    version: str = "1.0",
):
    """
    Add translation resource

    Args:
        language: Language code
        namespace: Translation namespace
        translations: Translation key-value pairs
        version: Resource version

    Returns:
        Addition result
    """
    try:
        from core.i18n_manager import Language, TranslationResource, get_i18n_manager

        manager = get_i18n_manager()

        # Validate language enum
        try:
            language_enum = Language(language)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid language code: {language}")

        # Create translation resource
        resource = TranslationResource(
            language=language_enum,
            namespace=namespace,
            translations=translations,
            version=version,
        )

        success = manager.add_translation_resource(resource)

        if not success:
            raise HTTPException(
                status_code=400, detail=f"Failed to add translation resource for {language}/{namespace}"
            )

        logger.info(f"Added translation resource: {language}/{namespace}")

        return {
            "status": "success",
            "data": {
                "language": language,
                "namespace": namespace,
                "translation_count": len(translations),
                "version": version,
                "added": success,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding translation resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/translations/namespace",
    summary="获取命名空间翻译",
    responses={
        200: {"description": "翻译内容"},
        404: {"description": "翻译未找到"},
        500: {"description": "获取失败"},
    },
)
async def get_namespace_translations(locale_id: str, namespace: str = "common"):
    """
    Get all translations for a locale and namespace

    Args:
        locale_id: Locale identifier
        namespace: Translation namespace

    Returns:
        Translation key-value pairs
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        translations = manager.get_namespace_translations(locale_id, namespace)

        if not translations:
            raise HTTPException(
                status_code=404,
                detail=f"Translations not found for locale {locale_id} and namespace {namespace}",
            )

        return {
            "status": "success",
            "data": {
                "locale_id": locale_id,
                "namespace": namespace,
                "translations": translations,
                "count": len(translations),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting namespace translations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/timezone/convert",
    summary="转换时区",
    responses={
        200: {"description": "转换结果"},
        400: {"description": "参数无效"},
        500: {"description": "转换失败"},
    },
)
async def convert_timezone(
    date_str: str, from_timezone: str, to_timezone: str
):
    """
    Convert datetime between timezones

    Args:
        date_str: Date string (ISO format)
        from_timezone: Source timezone
        to_timezone: Target timezone

    Returns:
        Converted datetime
    """
    try:
        from core.i18n_manager import TimeZone, get_i18n_manager

        manager = get_i18n_manager()

        # Validate timezones
        try:
            from_tz = TimeZone(from_timezone)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid source timezone: {from_timezone}")

        try:
            to_tz = TimeZone(to_timezone)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid target timezone: {to_timezone}")

        date_obj = datetime.fromisoformat(date_str)

        converted = manager.convert_timezone(date_obj, from_tz, to_tz)

        return {
            "status": "success",
            "data": {
                "original_date": date_str,
                "from_timezone": from_timezone,
                "to_timezone": to_timezone,
                "converted_date": converted.isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting timezone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/languages",
    summary="获取支持的语言列表",
    responses={
        200: {"description": "语言列表"},
        500: {"description": "获取失败"},
    },
)
async def get_supported_languages():
    """
    Get list of supported languages

    Returns:
        List of supported languages
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        languages = manager.get_supported_languages()

        return {
            "status": "success",
            "data": {"languages": languages, "count": len(languages)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting supported languages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/summary",
    summary="获取国际化系统摘要",
    responses={
        200: {"description": "系统摘要"},
        500: {"description": "获取失败"},
    },
)
async def get_i18n_summary():
    """
    Get i18n system summary

    Returns:
        System summary statistics
    """
    try:
        from core.i18n_manager import get_i18n_manager

        manager = get_i18n_manager()

        summary = manager.get_i18n_summary()

        return {
            "status": "success",
            "data": summary,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting i18n summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
