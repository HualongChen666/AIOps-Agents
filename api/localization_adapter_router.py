# -*- coding: utf-8 -*-
"""
Localization Adapter API Router
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/localization-adapter", tags=["Localization Adapter"])


@router.get(
    "/status",
    summary="获取本地化适配器状态",
    responses={
        200: {
            "description": "适配器状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"available": True, "current_locale": "zh-CN"},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取失败"},
    },
)
async def get_adapter_status():
    """Get localization adapter status"""
    try:
        from core.localization_adapter import get_localization_adapter

        adapter = get_localization_adapter()
        status = adapter.get_adapter_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting adapter status: {e}")
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
    """Get list of supported locales"""
    try:
        from core.localization_adapter import get_localization_adapter

        adapter = get_localization_adapter()
        locales = adapter.get_supported_locales()
        return {
            "status": "success",
            "data": {"locales": locales, "count": len(locales)},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting locales: {e}")
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
    """Set current locale for formatting"""
    try:
        from core.localization_adapter import get_localization_adapter

        adapter = get_localization_adapter()
        success = adapter.set_current_locale(locale_id)
        return {
            "status": "success",
            "data": {"locale_id": locale_id, "set": success},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting locale: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/date",
    summary="格式化日期",
    responses={
        200: {
            "description": "格式化结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"formatted_date": "2026年7月3日", "locale": "zh-CN"},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "格式化失败"},
    },
)
async def format_date(date_str: str, format_type: str = "short", locale: Optional[str] = None):
    """Format date according to locale"""
    try:
        from core.localization_adapter import DateFormat, get_localization_adapter

        adapter = get_localization_adapter()
        date_obj = date.fromisoformat(date_str)
        format_enum = DateFormat(format_type)
        formatted = adapter.format_date(date_obj, format_enum, locale)
        return {
            "status": "success",
            "data": {
                "date": date_str,
                "format_type": format_type,
                "locale": locale,
                "formatted": formatted,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting date: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/datetime",
    summary="格式化日期时间",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_datetime(
    datetime_str: str, format_type: str = "full", locale: Optional[str] = None
):
    """Format datetime according to locale"""
    try:
        from core.localization_adapter import DateFormat, get_localization_adapter

        adapter = get_localization_adapter()
        datetime_obj = datetime.fromisoformat(datetime_str)
        format_enum = DateFormat(format_type)
        formatted = adapter.format_datetime(datetime_obj, format_enum, locale)
        return {
            "status": "success",
            "data": {
                "datetime": datetime_str,
                "format_type": format_type,
                "locale": locale,
                "formatted": formatted,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting datetime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/number",
    summary="格式化数字",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_number(
    number: float, format_type: str = "decimal", locale: Optional[str] = None, decimals: int = 2
):
    """Format number according to locale"""
    try:
        from core.localization_adapter import NumberFormat, get_localization_adapter

        adapter = get_localization_adapter()
        format_enum = NumberFormat(format_type)
        formatted = adapter.format_number(number, format_enum, locale, decimals)
        return {
            "status": "success",
            "data": {
                "number": number,
                "format_type": format_type,
                "locale": locale,
                "formatted": formatted,
            },
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
async def format_currency(
    amount: float,
    currency_code: Optional[str] = None,
    locale: Optional[str] = None,
    decimals: int = 2,
):
    """Format currency according to locale"""
    try:
        from core.localization_adapter import get_localization_adapter

        adapter = get_localization_adapter()
        formatted = adapter.format_currency(amount, currency_code, locale, decimals)
        return {
            "status": "success",
            "data": {
                "amount": amount,
                "currency_code": currency_code,
                "locale": locale,
                "formatted": formatted,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting currency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/format/unit",
    summary="格式化单位",
    responses={
        200: {"description": "格式化结果"},
        500: {"description": "格式化失败"},
    },
)
async def format_unit(
    value: float, unit: str, target_system: Optional[str] = None, locale: Optional[str] = None
):
    """Format unit according to locale and unit system"""
    try:
        from core.localization_adapter import UnitSystem, get_localization_adapter

        adapter = get_localization_adapter()
        target_system_enum = UnitSystem(target_system) if target_system else None
        formatted = adapter.format_unit(value, unit, target_system_enum, locale)
        return {
            "status": "success",
            "data": {
                "value": value,
                "unit": unit,
                "target_system": target_system,
                "locale": locale,
                "formatted": formatted,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error formatting unit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
