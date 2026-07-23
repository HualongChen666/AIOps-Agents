# -*- coding: utf-8 -*-
"""
Localization Adapter Manager
Enterprise-grade localization adapter for dates, numbers, currencies, etc.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class DateFormat(Enum):
    """Date format types"""

    ISO = "iso"
    SHORT = "short"
    LONG = "long"
    FULL = "full"


class NumberFormat(Enum):
    """Number format types"""

    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENT = "percent"
    SCIENTIFIC = "scientific"


class UnitSystem(Enum):
    """Unit systems"""

    METRIC = "metric"
    IMPERIAL = "imperial"


@dataclass
class LocaleFormat:
    """Locale-specific format configuration"""

    language: str
    date_formats: Dict[str, str]
    number_formats: Dict[str, str]
    currency_symbol: str
    currency_position: str  # "before" or "after"
    decimal_separator: str
    thousands_separator: str
    unit_system: UnitSystem
    metadata: Dict[str, Any] = field(default_factory=dict)


class LocalizationAdapter:
    """
    Enterprise-grade localization adapter
    Provides formatting for dates, numbers, currencies, and units
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize localization adapter

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Locale formats
        self.locale_formats: Dict[str, LocaleFormat] = {}

        # Current locale format
        self.current_locale_format: Optional[LocaleFormat] = None

        # Statistics
        self.total_formats = 0

        # Initialize default locale formats
        self._initialize_default_formats()

        logger.info("Localization adapter initialized")

    def _initialize_default_formats(self) -> None:
        """Initialize default locale formats"""
        # Chinese (Simplified)
        self.locale_formats["zh-CN"] = LocaleFormat(
            language="zh-CN",
            date_formats={
                "iso": "%Y-%m-%d",
                "short": "%Y/%m/%d",
                "long": "%Y年%m月%d日",
                "full": "%Y年%m月%d日 %H:%M:%S",
            },
            number_formats={
                "decimal": "#,##0.##",
                "currency": "#,##0.##",
                "percent": "#,##0.##%",
                "scientific": "{:.2e}",
            },
            currency_symbol="¥",
            currency_position="before",
            decimal_separator=".",
            thousands_separator=",",
            unit_system=UnitSystem.METRIC,
        )

        # English (US)
        self.locale_formats["en-US"] = LocaleFormat(
            language="en-US",
            date_formats={
                "iso": "%Y-%m-%d",
                "short": "%m/%d/%Y",
                "long": "%B %d, %Y",
                "full": "%B %d, %Y %I:%M:%S %p",
            },
            number_formats={
                "decimal": "#,##0.##",
                "currency": "#,##0.##",
                "percent": "#,##0.##%",
                "scientific": "{:.2e}",
            },
            currency_symbol="$",
            currency_position="before",
            decimal_separator=".",
            thousands_separator=",",
            unit_system=UnitSystem.IMPERIAL,
        )

        # Japanese
        self.locale_formats["ja-JP"] = LocaleFormat(
            language="ja-JP",
            date_formats={
                "iso": "%Y-%m-%d",
                "short": "%Y/%m/%d",
                "long": "%Y年%m月%d日",
                "full": "%Y年%m月%d日 %H:%M:%S",
            },
            number_formats={
                "decimal": "#,##0.##",
                "currency": "#,##0.##",
                "percent": "#,##0.##%",
                "scientific": "{:.2e}",
            },
            currency_symbol="¥",
            currency_position="before",
            decimal_separator=".",
            thousands_separator=",",
            unit_system=UnitSystem.METRIC,
        )

        # Set current locale format
        self.current_locale_format = self.locale_formats["zh-CN"]
        self.total_formats = len(self.locale_formats)

    def add_locale_format(self, locale_format: LocaleFormat) -> bool:
        """
        Add a locale format

        Args:
            locale_format: Locale format configuration

        Returns:
            True if added, False otherwise
        """
        if locale_format.language in self.locale_formats:
            logger.warning(f"Locale format {locale_format.language} already exists")
            return False

        self.locale_formats[locale_format.language] = locale_format
        self.total_formats += 1

        logger.info(f"Added locale format: {locale_format.language}")

        return True

    def set_current_locale(self, locale_id: str) -> bool:
        """
        Set current locale format

        Args:
            locale_id: Locale identifier

        Returns:
            True if set, False otherwise
        """
        if locale_id not in self.locale_formats:
            logger.error(f"Locale format {locale_id} not found")
            return False

        self.current_locale_format = self.locale_formats[locale_id]

        logger.info(f"Set current locale format: {locale_id}")

        return True

    def format_date(
        self,
        date_obj: date,
        format_type: DateFormat = DateFormat.SHORT,
        locale: Optional[str] = None,
    ) -> str:
        """
        Format date according to locale

        Args:
            date_obj: Date to format
            format_type: Date format type
            locale: Locale identifier

        Returns:
            Formatted date string
        """
        locale_format = self._get_locale_format(locale)

        date_format = locale_format.date_formats.get(format_type.value, "%Y-%m-%d")

        return date_obj.strftime(date_format)

    def format_datetime(
        self,
        datetime_obj: datetime,
        format_type: DateFormat = DateFormat.FULL,
        locale: Optional[str] = None,
    ) -> str:
        """
        Format datetime according to locale

        Args:
            datetime_obj: Datetime to format
            format_type: Date format type
            locale: Locale identifier

        Returns:
            Formatted datetime string
        """
        locale_format = self._get_locale_format(locale)

        date_format = locale_format.date_formats.get(format_type.value, "%Y-%m-%d %H:%M:%S")

        return datetime_obj.strftime(date_format)

    def format_time(self, time_obj: time, locale: Optional[str] = None) -> str:
        """
        Format time according to locale

        Args:
            time_obj: Time to format
            locale: Locale identifier

        Returns:
            Formatted time string
        """
        return time_obj.strftime("%H:%M:%S")

    def format_number(
        self,
        number: float,
        format_type: NumberFormat = NumberFormat.DECIMAL,
        locale: Optional[str] = None,
        decimals: int = 2,
    ) -> str:
        """
        Format number according to locale

        Args:
            number: Number to format
            format_type: Number format type
            locale: Locale identifier
            decimals: Number of decimal places

        Returns:
            Formatted number string
        """
        locale_format = self._get_locale_format(locale)

        if format_type == NumberFormat.PERCENT:
            return f"{number:.{decimals}f}%"
        elif format_type == NumberFormat.SCIENTIFIC:
            return locale_format.number_formats["scientific"].format(number)
        else:
            # Simple formatting with locale separators
            formatted = f"{number:,.{decimals}f}"
            # Replace separators based on locale
            formatted = formatted.replace(",", locale_format.thousands_separator)
            formatted = formatted.replace(".", locale_format.decimal_separator)
            return formatted

    def format_currency(
        self,
        amount: float,
        currency_code: Optional[str] = None,
        locale: Optional[str] = None,
        decimals: int = 2,
    ) -> str:
        """
        Format currency according to locale

        Args:
            amount: Amount to format
            currency_code: Currency code (optional)
            locale: Locale identifier
            decimals: Number of decimal places

        Returns:
            Formatted currency string
        """
        locale_format = self._get_locale_format(locale)

        formatted_number = self.format_number(amount, NumberFormat.CURRENCY, locale, decimals)

        symbol = currency_code if currency_code else locale_format.currency_symbol

        if locale_format.currency_position == "before":
            return f"{symbol}{formatted_number}"
        else:
            return f"{formatted_number}{symbol}"

    def format_unit(
        self,
        value: float,
        unit: str,
        target_system: Optional[UnitSystem] = None,
        locale: Optional[str] = None,
    ) -> str:
        """
        Format unit according to locale and unit system

        Args:
            value: Value to format
            unit: Unit (e.g., "kg", "lb", "m", "ft")
            target_system: Target unit system
            locale: Locale identifier

        Returns:
            Formatted unit string
        """
        locale_format = self._get_locale_format(locale)
        target_system = target_system or locale_format.unit_system

        # Unit conversion (simplified)
        converted_value = self._convert_unit(value, unit, target_system)

        return f"{converted_value} {unit}"

    def _convert_unit(self, value: float, unit: str, target_system: UnitSystem) -> float:
        """
        Convert unit to target system

        Args:
            value: Value to convert
            unit: Unit
            target_system: Target unit system

        Returns:
            Converted value
        """
        # Simplified unit conversion
        # In production, use a proper unit conversion library
        return value

    def _get_locale_format(self, locale: Optional[str]) -> LocaleFormat:
        """
        Get locale format, fallback to current or default

        Args:
            locale: Locale identifier

        Returns:
            Locale format
        """
        if locale and locale in self.locale_formats:
            return self.locale_formats[locale]

        if self.current_locale_format:
            return self.current_locale_format

        return self.locale_formats["zh-CN"]

    def get_supported_locales(self) -> List[str]:
        """
        Get list of supported locales

        Returns:
            List of locale identifiers
        """
        return list(self.locale_formats.keys())

    def get_locale_format_info(self, locale: str) -> Optional[Dict[str, Any]]:
        """
        Get locale format information

        Args:
            locale: Locale identifier

        Returns:
            Locale format information or None
        """
        if locale not in self.locale_formats:
            return None

        locale_format = self.locale_formats[locale]

        return {
            "language": locale_format.language,
            "currency_symbol": locale_format.currency_symbol,
            "currency_position": locale_format.currency_position,
            "decimal_separator": locale_format.decimal_separator,
            "thousands_separator": locale_format.thousands_separator,
            "unit_system": locale_format.unit_system.value,
        }

    def get_adapter_summary(self) -> Dict[str, Any]:
        """
        Get adapter summary

        Returns:
            Adapter summary
        """
        return {
            "total_formats": self.total_formats,
            "supported_locales": len(self.locale_formats),
            "current_locale": (
                self.current_locale_format.language if self.current_locale_format else None
            ),
            "unit_systems": {
                "metric": len(
                    [
                        lf
                        for lf in self.locale_formats.values()
                        if lf.unit_system == UnitSystem.METRIC
                    ]
                ),
                "imperial": len(
                    [
                        lf
                        for lf in self.locale_formats.values()
                        if lf.unit_system == UnitSystem.IMPERIAL
                    ]
                ),
            },
        }


# Global instance
_localization_adapter: Optional[LocalizationAdapter] = None


def get_localization_adapter() -> LocalizationAdapter:
    """
    Get the global localization adapter instance

    Returns:
        LocalizationAdapter instance
    """
    global _localization_adapter
    if _localization_adapter is None:
        _localization_adapter = LocalizationAdapter()
    return _localization_adapter
