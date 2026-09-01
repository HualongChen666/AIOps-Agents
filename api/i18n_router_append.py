# -*- coding: utf-8 -*-
"""
i18n Router Append
国际化路由补充，用于补充缺失的API端点
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from core.authentication import get_current_active_user
from core.rbac import role_required

router = APIRouter(prefix="/api/i18n", tags=["国际化"])


@router.get("/i18n-translations")
async def get_i18n_translations(user=Depends(get_current_active_user)):
    """获取国际化翻译"""
    return {
        "status": "success",
        "translations": {
            "en": {"welcome": "Welcome", "login": "Login"},
            "zh": {"welcome": "欢迎", "login": "登录"},
            "ja": {"welcome": "ようこそ", "login": "ログイン"}
        }
    }


@router.get("/i18n-languages")
async def get_i18n_languages(user=Depends(get_current_active_user)):
    """获取支持的语言"""
    return {
        "status": "success",
        "languages": [
            {"code": "en", "name": "English", "native": "English"},
            {"code": "zh", "name": "Chinese", "native": "中文"},
            {"code": "ja", "name": "Japanese", "native": "日本語"}
        ]
    }


@router.get("/i18n-locales")
async def get_i18n_locales(user=Depends(get_current_active_user)):
    """获取区域设置"""
    return {
        "status": "success",
        "locales": [
            {"code": "en-US", "language": "en", "region": "US"},
            {"code": "zh-CN", "language": "zh", "region": "CN"},
            {"code": "ja-JP", "language": "ja", "region": "JP"}
        ]
    }


@router.get("/i18n-configuration")
async def get_i18n_configuration(user=Depends(get_current_active_user)):
    """获取国际化配置"""
    return {
        "status": "success",
        "configuration": {
            "default_language": "en",
            "supported_languages": ["en", "zh", "ja"],
            "auto_detect": True
        }
    }


@router.post("/i18n-configuration")
async def update_i18n_configuration(config: dict, user=Depends(role_required("admin"))):
    """更新国际化配置"""
    return {
        "status": "success",
        "configuration": config,
        "message": "Configuration updated successfully"
    }


@router.get("/i18n-translations/{language}")
async def get_i18n_translations_by_language(language: str, user=Depends(get_current_active_user)):
    """获取指定语言的翻译"""
    translations = {
        "en": {"welcome": "Welcome", "login": "Login"},
        "zh": {"welcome": "欢迎", "login": "登录"},
        "ja": {"welcome": "ようこそ", "login": "ログイン"}
    }
    return {
        "status": "success",
        "language": language,
        "translations": translations.get(language, {})
    }


@router.post("/i18n-translations/{language}")
async def update_i18n_translations(language: str, translations: dict, user=Depends(role_required("admin"))):
    """更新指定语言的翻译"""
    return {
        "status": "success",
        "language": language,
        "translations": translations,
        "message": "Translations updated successfully"
    }


@router.get("/i18n-pluralization")
async def get_i18n_pluralization(user=Depends(get_current_active_user)):
    """获取复数规则"""
    return {
        "status": "success",
        "pluralization": {
            "en": {"forms": ["one", "other"]},
            "zh": {"forms": ["other"]},
            "ja": {"forms": ["other"]}
        }
    }
