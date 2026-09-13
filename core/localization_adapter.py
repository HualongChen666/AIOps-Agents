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


# 单位定义：符号 -> (所属单位制, 物理量, 换算到公制基准的系数)
_UNIT_DEFINITIONS: Dict[str, tuple] = {
    # 长度（基准：米）
    "m": (UnitSystem.METRIC, "length", 1.0),
    "km": (UnitSystem.METRIC, "length", 1000.0),
    "cm": (UnitSystem.METRIC, "length", 0.01),
    "mm": (UnitSystem.METRIC, "length", 0.001),
    "ft": (UnitSystem.IMPERIAL, "length", 0.3048),
    "mi": (UnitSystem.IMPERIAL, "length", 1609.344),
    "in": (UnitSystem.IMPERIAL, "length", 0.0254),
    # 质量（基准：千克）
    "kg": (UnitSystem.METRIC, "mass", 1.0),
    "g": (UnitSystem.METRIC, "mass", 0.001),
    "lb": (UnitSystem.IMPERIAL, "mass", 0.45359237),
    "oz": (UnitSystem.IMPERIAL, "mass", 0.028349523125),
    # 体积（基准：升）
    "l": (UnitSystem.METRIC, "volume", 1.0),
    "ml": (UnitSystem.METRIC, "volume", 0.001),
    "gal": (UnitSystem.IMPERIAL, "volume", 3.785411784),
    # 速度（基准：千米/小时）
    "km/h": (UnitSystem.METRIC, "speed", 1.0),
    "mph": (UnitSystem.IMPERIAL, "speed", 1.609344),
}

# 各物理量在目标单位制下使用的展示单位
_UNIT_TARGET_SYMBOL: Dict[str, Dict[UnitSystem, str]] = {
    "length": {UnitSystem.METRIC: "m", UnitSystem.IMPERIAL: "ft"},
    "mass": {UnitSystem.METRIC: "kg", UnitSystem.IMPERIAL: "lb"},
    "volume": {UnitSystem.METRIC: "l", UnitSystem.IMPERIAL: "gal"},
    "speed": {UnitSystem.METRIC: "km/h", UnitSystem.IMPERIAL: "mph"},
}

# 温度单位（摄氏/华氏使用非线性换算）
_TEMPERATURE_UNITS = {"c", "°c", "f", "°f"}

# 常见单位全称/别名的归一化映射
_UNIT_ALIASES: Dict[str, str] = {
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "kilometer": "km", "kilometers": "km", "kilometre": "km", "kilometres": "km",
    "centimeter": "cm", "centimeters": "cm", "centimetre": "cm", "centimetres": "cm",
    "millimeter": "mm", "millimeters": "mm",
    "foot": "ft", "feet": "ft",
    "mile": "mi", "miles": "mi",
    "inch": "in", "inches": "in",
    "kilogram": "kg", "kilograms": "kg",
    "gram": "g", "grams": "g",
    "pound": "lb", "pounds": "lb",
    "ounce": "oz", "ounces": "oz",
    "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "milliliter": "ml", "milliliters": "ml",
    "gallon": "gal", "gallons": "gal",
    "kph": "km/h", "kilometers per hour": "km/h",
    "mph": "mph", "miles per hour": "mph",
}


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

        converted_value, display_unit = self._convert_unit_full(value, unit, target_system)

        return f"{converted_value} {display_unit}"

    def _convert_unit_full(
        self, value: float, unit: str, target_system: UnitSystem
    ) -> tuple:
        """按目标单位制换算数值并返回换算后的展示单位。

        未知单位或单位已属于目标单位制时原样返回。
        """
        key = (unit or "").strip().lower()
        if not key:
            return value, unit
        key = _UNIT_ALIASES.get(key, key)

        # 温度换算
        if key in _TEMPERATURE_UNITS:
            is_celsius = key.endswith("c")
            if is_celsius and target_system == UnitSystem.IMPERIAL:
                return value * 9 / 5 + 32, "°F"
            if (not is_celsius) and target_system == UnitSystem.METRIC:
                return (value - 32) * 5 / 9, "°C"
            return value, unit

        definition = _UNIT_DEFINITIONS.get(key)
        if definition is None:
            return value, unit

        source_system, quantity, factor = definition
        if source_system == target_system:
            return value, unit

        base_value = value * factor
        target_symbol = _UNIT_TARGET_SYMBOL[quantity][target_system]
        target_factor = _UNIT_DEFINITIONS[target_symbol][2]
        return base_value / target_factor, target_symbol

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
        converted_value, _ = self._convert_unit_full(value, unit, target_system)
        return converted_value

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
