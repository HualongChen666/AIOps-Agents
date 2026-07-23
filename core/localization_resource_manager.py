# -*- coding: utf-8 -*-
"""
Localization Resource Manager
Enterprise-grade multilingual resource management
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ResourceFile:
    """Resource file metadata"""

    language: str
    namespace: str
    version: str
    file_path: str
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationEntry:
    """Translation entry"""

    key: str
    value: str
    context: Optional[str] = None
    plural_forms: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalizationResourceManager:
    """
    Enterprise-grade localization resource manager
    Provides resource file management, dynamic loading, and version control
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize localization resource manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Resource files registry
        self.resource_files: Dict[str, ResourceFile] = {}

        # In-memory translation cache
        self.translation_cache: Dict[str, Dict[str, Dict[str, str]]] = {}

        # Resource version management
        self.resource_versions: Dict[str, str] = {}

        # Configuration
        self.resource_directory = self.config.get("resource_directory", "locales")
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.auto_reload = self.config.get("auto_reload", False)

        # Statistics
        self.total_resources = 0
        self.total_translations = 0

        # Load default resources
        self._load_default_resources()

        logger.info("Localization resource manager initialized")

    def _load_default_resources(self) -> None:
        """Load default translation resources"""
        # Chinese (Simplified) - Common namespace
        self._add_translations_to_cache(
            language="zh",
            namespace="common",
            translations={
                "welcome": "欢迎",
                "login": "登录",
                "logout": "退出",
                "dashboard": "仪表盘",
                "settings": "设置",
                "profile": "个人资料",
                "language": "语言",
                "timezone": "时区",
                "save": "保存",
                "cancel": "取消",
                "delete": "删除",
                "edit": "编辑",
                "create": "创建",
                "search": "搜索",
                "filter": "筛选",
                "export": "导出",
                "import": "导入",
                "success": "成功",
                "error": "错误",
                "warning": "警告",
                "info": "信息",
                "loading": "加载中...",
                "no_data": "暂无数据",
                "confirm": "确认",
                "back": "返回",
                "next": "下一步",
                "previous": "上一步",
                "submit": "提交",
                "reset": "重置",
            },
        )

        # English - Common namespace
        self._add_translations_to_cache(
            language="en",
            namespace="common",
            translations={
                "welcome": "Welcome",
                "login": "Login",
                "logout": "Logout",
                "dashboard": "Dashboard",
                "settings": "Settings",
                "profile": "Profile",
                "language": "Language",
                "timezone": "Timezone",
                "save": "Save",
                "cancel": "Cancel",
                "delete": "Delete",
                "edit": "Edit",
                "create": "Create",
                "search": "Search",
                "filter": "Filter",
                "export": "Export",
                "import": "Import",
                "success": "Success",
                "error": "Error",
                "warning": "Warning",
                "info": "Info",
                "loading": "Loading...",
                "no_data": "No data available",
                "confirm": "Confirm",
                "back": "Back",
                "next": "Next",
                "previous": "Previous",
                "submit": "Submit",
                "reset": "Reset",
            },
        )

        # Japanese - Common namespace
        self._add_translations_to_cache(
            language="ja",
            namespace="common",
            translations={
                "welcome": "ようこそ",
                "login": "ログイン",
                "logout": "ログアウト",
                "dashboard": "ダッシュボード",
                "settings": "設定",
                "profile": "プロフィール",
                "language": "言語",
                "timezone": "タイムゾーン",
                "save": "保存",
                "cancel": "キャンセル",
                "delete": "削除",
                "edit": "編集",
                "create": "作成",
                "search": "検索",
                "filter": "フィルター",
                "export": "エクスポート",
                "import": "インポート",
                "success": "成功",
                "error": "エラー",
                "warning": "警告",
                "info": "情報",
                "loading": "読み込み中...",
                "no_data": "データがありません",
                "confirm": "確認",
                "back": "戻る",
                "next": "次へ",
                "previous": "前へ",
                "submit": "送信",
                "reset": "リセット",
            },
        )

        # Error messages namespace
        self._add_translations_to_cache(
            language="zh",
            namespace="errors",
            translations={
                "invalid_credentials": "用户名或密码错误",
                "session_expired": "会话已过期，请重新登录",
                "permission_denied": "权限不足",
                "resource_not_found": "资源未找到",
                "server_error": "服务器错误",
                "network_error": "网络错误",
                "validation_error": "验证错误",
                "unknown_error": "未知错误",
            },
        )

        self._add_translations_to_cache(
            language="en",
            namespace="errors",
            translations={
                "invalid_credentials": "Invalid username or password",
                "session_expired": "Session expired, please login again",
                "permission_denied": "Permission denied",
                "resource_not_found": "Resource not found",
                "server_error": "Server error",
                "network_error": "Network error",
                "validation_error": "Validation error",
                "unknown_error": "Unknown error",
            },
        )

        self._add_translations_to_cache(
            language="ja",
            namespace="errors",
            translations={
                "invalid_credentials": "ユーザー名またはパスワードが間違っています",
                "session_expired": "セッションが期限切れです。再度ログインしてください",
                "permission_denied": "権限がありません",
                "resource_not_found": "リソースが見つかりません",
                "server_error": "サーバーエラー",
                "network_error": "ネットワークエラー",
                "validation_error": "検証エラー",
                "unknown_error": "不明なエラー",
            },
        )

    def _add_translations_to_cache(
        self, language: str, namespace: str, translations: Dict[str, str]
    ) -> None:
        """
        Add translations to cache

        Args:
            language: Language code
            namespace: Translation namespace
            translations: Translation dictionary
        """
        if language not in self.translation_cache:
            self.translation_cache[language] = {}

        self.translation_cache[language][namespace] = translations
        self.total_translations += len(translations)
        self.total_resources += 1

        if namespace not in self.resource_versions:
            self.resource_versions[namespace] = "1.0"

    def register_resource_file(
        self, language: str, namespace: str, file_path: str, version: str = "1.0"
    ) -> bool:
        """
        Register a resource file

        Args:
            language: Language code
            namespace: Translation namespace
            file_path: File path
            version: Resource version

        Returns:
            True if registered, False otherwise
        """
        resource_id = f"{language}_{namespace}"

        if resource_id in self.resource_files:
            logger.warning(f"Resource file {resource_id} already registered")
            return False

        resource_file = ResourceFile(
            language=language,
            namespace=namespace,
            version=version,
            file_path=file_path,
            last_updated=datetime.now(timezone.utc),
        )

        self.resource_files[resource_id] = resource_file
        self.resource_versions[namespace] = version

        logger.info(f"Registered resource file: {resource_id}")

        return True

    def load_resource_file(self, language: str, namespace: str) -> bool:
        """
        Load resource file into cache

        Args:
            language: Language code
            namespace: Translation namespace

        Returns:
            True if loaded, False otherwise
        """
        resource_id = f"{language}_{namespace}"

        if resource_id not in self.resource_files:
            logger.error(f"Resource file {resource_id} not found")
            return False

        resource_file = self.resource_files[resource_id]

        try:
            # Load JSON file
            with open(resource_file.file_path, "r", encoding="utf-8") as f:
                translations = json.load(f)

            self._add_translations_to_cache(language, namespace, translations)

            logger.info(f"Loaded resource file: {resource_id}")

            return True
        except Exception as e:
            logger.error(f"Error loading resource file {resource_id}: {e}")
            return False

    def get_translations(self, language: str, namespace: str) -> Optional[Dict[str, str]]:
        """
        Get translations for a language and namespace

        Args:
            language: Language code
            namespace: Translation namespace

        Returns:
            Translation dictionary or None
        """
        if language not in self.translation_cache:
            return None

        return self.translation_cache[language].get(namespace)

    def add_translation(self, language: str, namespace: str, key: str, value: str) -> bool:
        """
        Add a translation entry

        Args:
            language: Language code
            namespace: Translation namespace
            key: Translation key
            value: Translation value

        Returns:
            True if added, False otherwise
        """
        if language not in self.translation_cache:
            self.translation_cache[language] = {}

        if namespace not in self.translation_cache[language]:
            self.translation_cache[language][namespace] = {}

        self.translation_cache[language][namespace][key] = value
        self.total_translations += 1

        logger.info(f"Added translation: {language}/{namespace}/{key}")

        return True

    def export_translations(self, language: str, namespace: str, output_path: str) -> bool:
        """
        Export translations to JSON file

        Args:
            language: Language code
            namespace: Translation namespace
            output_path: Output file path

        Returns:
            True if exported, False otherwise
        """
        translations = self.get_translations(language, namespace)

        if not translations:
            logger.error(f"No translations found for {language}/{namespace}")
            return False

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(translations, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported translations to {output_path}")

            return True
        except Exception as e:
            logger.error(f"Error exporting translations: {e}")
            return False

    def import_translations(self, language: str, namespace: str, input_path: str) -> bool:
        """
        Import translations from JSON file

        Args:
            language: Language code
            namespace: Translation namespace
            input_path: Input file path

        Returns:
            True if imported, False otherwise
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                translations = json.load(f)

            self._add_translations_to_cache(language, namespace, translations)

            logger.info(f"Imported translations from {input_path}")

            return True
        except Exception as e:
            logger.error(f"Error importing translations: {e}")
            return False

    def get_missing_translations(
        self, source_language: str, target_language: str, namespace: str
    ) -> List[str]:
        """
        Get missing translations for target language

        Args:
            source_language: Source language
            target_language: Target language
            namespace: Translation namespace

        Returns:
            List of missing translation keys
        """
        source_translations = self.get_translations(source_language, namespace)
        target_translations = self.get_translations(target_language, namespace)

        if not source_translations:
            return []

        if not target_translations:
            return list(source_translations.keys())

        missing = [key for key in source_translations.keys() if key not in target_translations]

        return missing

    def get_resource_summary(self) -> Dict[str, Any]:
        """
        Get resource manager summary

        Returns:
            Resource manager summary
        """
        languages = set()
        namespaces = set()

        for lang, ns_dict in self.translation_cache.items():
            languages.add(lang)
            for ns in ns_dict.keys():
                namespaces.add(ns)

        return {
            "total_resources": self.total_resources,
            "total_translations": self.total_translations,
            "total_languages": len(languages),
            "total_namespaces": len(namespaces),
            "languages": list(languages),
            "namespaces": list(namespaces),
            "registered_files": len(self.resource_files),
        }


# Global instance
_resource_manager: Optional[LocalizationResourceManager] = None


def get_resource_manager() -> LocalizationResourceManager:
    """
    Get the global localization resource manager instance

    Returns:
        LocalizationResourceManager instance
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = LocalizationResourceManager()
    return _resource_manager
