# -*- coding: utf-8 -*-
"""
i18n Router Append
国际化路由补充；全部数据来自真实的 ``core.i18n_manager``（语言/区域/翻译存储），
不再返回硬编码示例字典。
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from core.authentication import get_current_active_user
from core.i18n_manager import Language, get_i18n_manager
from core.rbac import role_required

router = APIRouter(prefix="/api/i18n", tags=["国际化"])


def _manager():
    return get_i18n_manager()


def _locale_id_for_language(language: str) -> str:
    """Resolve a language code (e.g. "en") to a configured locale id (e.g. "en-US")."""
    manager = _manager()
    for locale_id, locale in manager.locales.items():
        if locale.language.value == language or locale_id == language:
            return locale_id
    raise HTTPException(status_code=404, detail=f"Unsupported language: {language}")


@router.get("/i18n-translations")
async def get_i18n_translations(user=Depends(get_current_active_user)):
    """获取国际化翻译（真实翻译存储）"""
    manager = _manager()
    translations: Dict[str, Dict[str, Dict[str, str]]] = {}
    for language, resources in manager.translation_resources.items():
        translations[language] = {
            namespace: dict(resource.translations) for namespace, resource in resources.items()
        }
    return {"status": "success", "translations": translations}


@router.get("/i18n-languages")
async def get_i18n_languages(user=Depends(get_current_active_user)):
    """获取支持的语言（来自 i18n 管理器）"""
    return {"status": "success", "languages": _manager().get_supported_languages()}


@router.get("/i18n-locales")
async def get_i18n_locales(user=Depends(get_current_active_user)):
    """获取区域设置（来自 i18n 管理器）"""
    return {"status": "success", "locales": _manager().get_supported_locales()}


@router.get("/i18n-configuration")
async def get_i18n_configuration(user=Depends(get_current_active_user)):
    """获取国际化配置（真实运行态）"""
    manager = _manager()
    return {
        "status": "success",
        "configuration": {
            "default_language": manager.default_language.value,
            "fallback_language": manager.fallback_language.value,
            "supported_languages": [lang["code"] for lang in manager.get_supported_languages()],
            "auto_detect": manager.auto_detect_language,
        },
    }


@router.post("/i18n-configuration")
async def update_i18n_configuration(config: dict, user=Depends(role_required("admin"))):
    """更新国际化配置（真实生效）"""
    manager = _manager()
    updated: Dict[str, Any] = {}
    if "default_language" in config:
        try:
            manager.default_language = Language(config["default_language"])
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Unsupported language: {config['default_language']}"
            )
        updated["default_language"] = manager.default_language.value
    if "auto_detect" in config:
        manager.auto_detect_language = bool(config["auto_detect"])
        updated["auto_detect"] = manager.auto_detect_language
    return {
        "status": "success",
        "configuration": updated,
        "message": "Configuration updated successfully",
    }


@router.get("/i18n-translations/{language}")
async def get_i18n_translations_by_language(language: str, user=Depends(get_current_active_user)):
    """获取指定语言的翻译（真实翻译存储）"""
    locale_id = _locale_id_for_language(language)
    manager = _manager()
    resources = manager.translation_resources.get(locale_id.split("-")[0], {})
    translations: Dict[str, Dict[str, str]] = {
        namespace: dict(resource.translations) for namespace, resource in resources.items()
    }
    return {"status": "success", "language": language, "translations": translations}


@router.post("/i18n-translations/{language}")
async def update_i18n_translations(
    language: str, translations: dict, user=Depends(role_required("admin"))
):
    """更新指定语言的翻译（写入真实翻译存储）"""
    locale_id = _locale_id_for_language(language)
    manager = _manager()
    namespace = translations.pop("namespace", "common")
    written = 0
    for key, value in translations.items():
        if manager.set_translation(locale_id, namespace, str(key), str(value)):
            written += 1
    return {
        "status": "success",
        "language": language,
        "written": written,
        "message": "Translations updated successfully",
    }


@router.get("/i18n-pluralization")
async def get_i18n_pluralization(user=Depends(get_current_active_user)):
    """获取复数规则（基于 CLDR 复数类别的静态语言学规则）"""
    return {
        "status": "success",
        "pluralization": {
            "en": {"forms": ["one", "other"]},
            "zh": {"forms": ["other"]},
            "ja": {"forms": ["other"]},
            "ko": {"forms": ["other"]},
            "fr": {"forms": ["one", "many", "other"]},
            "de": {"forms": ["one", "other"]},
            "es": {"forms": ["one", "other"]},
            "pt": {"forms": ["one", "other"]},
            "ru": {"forms": ["one", "few", "many", "other"]},
            "ar": {"forms": ["zero", "one", "two", "few", "many", "other"]},
        },
    }
