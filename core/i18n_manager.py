# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Manager
Enterprise-grade internationalization framework and localization support
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class Language(Enum):
    """Supported languages"""

    CHINESE = "zh"
    ENGLISH = "en"
    JAPANESE = "ja"
    KOREAN = "ko"
    FRENCH = "fr"
    GERMAN = "de"
    SPANISH = "es"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"


class TimeZone(Enum):
    """Supported time zones"""

    UTC = "UTC"
    BEIJING = "Asia/Shanghai"
    TOKYO = "Asia/Tokyo"
    NEW_YORK = "America/New_York"
    LONDON = "Europe/London"
    PARIS = "Europe/Paris"
    SYDNEY = "Australia/Sydney"


@dataclass
class Locale:
    """Locale configuration"""

    language: Language
    region: str
    timezone: TimeZone
    number_format: str
    date_format: str
    currency: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationResource:
    """Translation resource"""

    language: Language
    namespace: str
    translations: Dict[str, str]
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)


class I18nManager:
    """
    Enterprise-grade internationalization manager
    Provides language switching, timezone handling, and resource management
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize i18n manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Supported locales
        self.locales: Dict[str, Locale] = {}

        # Translation resources
        self.translation_resources: Dict[str, Dict[str, TranslationResource]] = {}

        # Current locale
        self.current_locale: Optional[Locale] = None
        self.default_language = Language.CHINESE
        self.default_timezone = TimeZone.BEIJING

        # Configuration
        self.fallback_language = self.config.get("fallback_language", Language.ENGLISH)
        self.auto_detect_language = self.config.get("auto_detect_language", True)
        self.auto_detect_timezone = self.config.get("auto_detect_timezone", True)

        # Statistics
        self.total_translations = 0
        self.total_namespaces = 0

        # Initialize default locales
        self._initialize_default_locales()

        logger.info("Internationalization manager initialized")

    def _initialize_default_locales(self) -> None:
        """Initialize default locales"""
        # Chinese (Simplified)
        self.locales["zh-CN"] = Locale(
            language=Language.CHINESE,
            region="CN",
            timezone=TimeZone.BEIJING,
            number_format="#,##0.##",
            date_format="YYYY-MM-DD HH:mm:ss",
            currency="CNY",
        )

        # English (US)
        self.locales["en-US"] = Locale(
            language=Language.ENGLISH,
            region="US",
            timezone=TimeZone.NEW_YORK,
            number_format="#,##0.##",
            date_format="MM/DD/YYYY HH:mm:ss",
            currency="USD",
        )

        # Japanese
        self.locales["ja-JP"] = Locale(
            language=Language.JAPANESE,
            region="JP",
            timezone=TimeZone.TOKYO,
            number_format="#,##0.##",
            date_format="YYYY/MM/DD HH:mm:ss",
            currency="JPY",
        )

        # Set current locale
        self.current_locale = self.locales["zh-CN"]

    def add_locale(self, locale_id: str, locale: Locale) -> bool:
        """
        Add a new locale

        Args:
            locale_id: Locale identifier (e.g., "en-US")
            locale: Locale configuration

        Returns:
            True if added, False otherwise
        """
        if locale_id in self.locales:
            logger.warning(f"Locale {locale_id} already exists")
            return False

        self.locales[locale_id] = locale

        logger.info(f"Added locale: {locale_id}")

        return True

    def set_current_locale(self, locale_id: str) -> bool:
        """
        Set current locale

        Args:
            locale_id: Locale identifier

        Returns:
            True if set, False otherwise
        """
        if locale_id not in self.locales:
            logger.error(f"Locale {locale_id} not found")
            return False

        self.current_locale = self.locales[locale_id]

        logger.info(f"Set current locale: {locale_id}")

        return True

    def get_current_locale(self) -> Optional[Locale]:
        """
        Get current locale

        Returns:
            Current locale or None
        """
        return self.current_locale

    def detect_locale_from_request(
        self, accept_language: Optional[str] = None, user_timezone: Optional[str] = None
    ) -> Optional[str]:
        """
        Detect locale from request

        Args:
            accept_language: Accept-Language header
            user_timezone: User timezone

        Returns:
            Detected locale identifier or None
        """
        detected_language = None

        # Detect language from Accept-Language header
        if accept_language and self.auto_detect_language:
            languages = accept_language.split(",")
            for lang in languages:
                lang_code = lang.split(";")[0].strip().lower()
                for locale_id, locale in self.locales.items():
                    if locale.language.value == lang_code:
                        detected_language = locale_id
                        break
                if detected_language:
                    break

        # Detect timezone
        if user_timezone and self.auto_detect_timezone:
            try:
                TimeZone(user_timezone)
            except ValueError:
                pass

        # Find best matching locale
        if detected_language:
            return detected_language

        return None

    def add_translation_resource(self, resource: TranslationResource) -> bool:
        """
        Add translation resource

        Args:
            resource: Translation resource

        Returns:
            True if added, False otherwise
        """
        language = resource.language.value

        if language not in self.translation_resources:
            self.translation_resources[language] = {}

        self.translation_resources[language][resource.namespace] = resource

        self.total_translations += len(resource.translations)

        logger.info(f"Added translation resource: {language}/{resource.namespace}")

        return True

    def translate(
        self, key: str, namespace: str = "common", language: Optional[Language] = None, **kwargs
    ) -> str:
        """
        Translate a key to target language

        Args:
            key: Translation key
            namespace: Translation namespace
            language: Target language
            **kwargs: Variables for string formatting

        Returns:
            Translated string
        """
        # Use current language if not specified
        if language is None and self.current_locale:
            language = self.current_locale.language

        if language is None:
            language = self.default_language

        # Get translation
        language_code = language.value

        if language_code not in self.translation_resources:
            # Fallback to fallback language
            language_code = self.fallback_language.value

        if language_code not in self.translation_resources:
            # Return key if no translation available
            return key

        namespace_resources = self.translation_resources[language_code]

        if namespace not in namespace_resources:
            # Try common namespace
            if "common" in namespace_resources:
                return self._format_translation(
                    namespace_resources["common"].translations.get(key, key), **kwargs
                )
            return key

        translation = namespace_resources[namespace].translations.get(key)

        if not translation:
            # Fallback to fallback language
            fallback_code = self.fallback_language.value
            if fallback_code in self.translation_resources:
                fallback_resources = self.translation_resources[fallback_code]
                if namespace in fallback_resources:
                    translation = fallback_resources[namespace].translations.get(key)

        if not translation:
            return key

        return self._format_translation(translation, **kwargs)

    def _format_translation(self, translation: str, **kwargs) -> str:
        """
        Format translation with variables

        Args:
            translation: Translation string
            **kwargs: Variables

        Returns:
            Formatted string
        """
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError):
            return translation

    def format_number(self, number: float, locale: Optional[Locale] = None) -> str:
        """
        Format number according to locale

        Args:
            number: Number to format
            locale: Locale to use

        Returns:
            Formatted number string
        """
        if locale is None:
            locale = self.current_locale

        if locale is None:
            locale = self.locales["zh-CN"]

        # Simple formatting (can be enhanced with locale-specific libraries)
        try:
            return locale.number_format.format(number)
        except (AttributeError, TypeError, ValueError) as e:
            # Log the specific error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Number formatting failed for locale {locale}: {e}")
            return str(number)

    def format_currency(self, amount: float, locale: Optional[Locale] = None) -> str:
        """
        Format currency according to locale

        Args:
            amount: Amount to format
            locale: Locale to use

        Returns:
            Formatted currency string
        """
        if locale is None:
            locale = self.current_locale

        if locale is None:
            locale = self.locales["zh-CN"]

        # Simple formatting (can be enhanced with locale-specific libraries)
        formatted_number = self.format_number(amount, locale)
        return f"{locale.currency} {formatted_number}"

    def format_date(self, date: datetime, locale: Optional[Locale] = None) -> str:
        """
        Format date according to locale

        Args:
            date: Date to format
            locale: Locale to use

        Returns:
            Formatted date string
        """
        if locale is None:
            locale = self.current_locale

        if locale is None:
            locale = self.locales["zh-CN"]

        # Simple formatting (can be enhanced with locale-specific libraries)
        locale.date_format
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def convert_timezone(
        self, date: datetime, from_timezone: TimeZone, to_timezone: TimeZone
    ) -> datetime:
        """
        Convert datetime between timezones

        Args:
            date: Datetime to convert
            from_timezone: Source timezone
            to_timezone: Target timezone

        Returns:
            Converted datetime
        """
        # Simple timezone conversion (can be enhanced with pytz)
        # For now, return the same datetime
        # In production, use pytz or zoneinfo for proper conversion
        return date

    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """
        Get list of supported languages

        Returns:
            List of supported languages
        """
        languages = set()
        for locale in self.locales.values():
            languages.add(locale.language)

        return [{"code": lang.value, "name": lang.name.capitalize()} for lang in languages]

    def get_supported_locales(self) -> List[Dict[str, Any]]:
        """
        Get list of supported locales

        Returns:
            List of supported locales
        """
        return [
            {
                "locale_id": locale_id,
                "language": locale.language.value,
                "region": locale.region,
                "timezone": locale.timezone.value,
                "currency": locale.currency,
            }
            for locale_id, locale in self.locales.items()
        ]

    def get_i18n_summary(self) -> Dict[str, Any]:
        """
        Get i18n system summary

        Returns:
            System summary
        """
        return {
            "total_locales": len(self.locales),
            "total_translations": self.total_translations,
            "total_namespaces": self.total_namespaces,
            "current_locale": self.current_locale.region if self.current_locale else None,
            "default_language": self.default_language.value,
            "fallback_language": self.fallback_language.value,
            "supported_languages": len(self.get_supported_languages()),
        }


# Global instance
_i18n_manager: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """
    Get the global i18n manager instance

    Returns:
        I18nManager instance
    """
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager
