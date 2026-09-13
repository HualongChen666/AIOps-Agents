# -*- coding: utf-8 -*-
"""
Accessibility Support Module
可访问性支持模块

提供前端可访问性支持的后端配置和辅助功能。
"""

import logging
from typing import Any, Dict

from fastapi import Response

logger = logging.getLogger(__name__)


class AccessibilityHeaders:
    """可访问性响应头"""

    @staticmethod
    def add_accessibility_headers(response: Response) -> Response:
        """
        添加可访问性响应头

        Args:
            response: FastAPI响应对象

        Returns:
            带有可访问性头的响应
        """
        # 添加内容语言头
        response.headers["Content-Language"] = "zh-CN"

        # 添加Vary头支持内容协商
        response.headers["Vary"] = "Accept-Language"

        return response

    @staticmethod
    def add_a11y_metadata(response: Response, metadata: Dict[str, Any]) -> Response:
        """
        添加可访问性元数据

        Args:
            response: FastAPI响应对象
            metadata: 元数据字典

        Returns:
            带有元数据的响应
        """
        # 添加自定义头
        if "wcag_level" in metadata:
            response.headers["X-WCAG-Level"] = metadata["wcag_level"]

        if "screen_reader_compatible" in metadata:
            response.headers["X-ScreenReader-Compatible"] = str(
                metadata["screen_reader_compatible"]
            ).lower()

        if "keyboard_navigable" in metadata:
            response.headers["X-Keyboard-Navigable"] = str(metadata["keyboard_navigable"]).lower()

        return response


class AccessibilityGuidelines:
    """可访问性指南"""

    WCAG_21_GUIDELINES = {
        "perceivable": {
            "text_alternatives": "提供文本替代内容",
            "time_based_media": "为时间相关媒体提供替代内容",
            "adaptable": "创建可适应不同呈现方式的内容",
            "distinguishable": "使内容更容易看到和听到",
        },
        "operable": {
            "keyboard_accessible": "使所有功能可通过键盘访问",
            "enough_time": "为用户提供足够的时间",
            "seizures": "不设计导致癫痫的内容",
            "navigable": "帮助用户导航和查找内容",
        },
        "understandable": {
            "readable": "使文本内容可读",
            "predictable": "使内容可预测",
            "input_assistance": "帮助用户避免和纠正错误",
        },
        "robust": {"compatible": "最大化与当前和未来用户代理的兼容性"},
    }

    @staticmethod
    def get_waag_level(level: str = "AA") -> Dict[str, Any]:
        """
        获取WCAG级别要求

        Args:
            level: WCAG级别 (A, AA, AAA)

        Returns:
            WCAG级别要求
        """
        requirements = {
            "A": {
                "level": "A",
                "description": "最低级别的可访问性",
                "requirements": ["文本替代", "键盘可访问", "足够的时间", "可导航", "可读"],
            },
            "AA": {
                "level": "AA",
                "description": "推荐级别的可访问性",
                "requirements": [
                    "A级别的所有要求",
                    "对比度至少4.5:1",
                    "文本可调整到200%",
                    "无闪烁内容",
                    "一致的导航",
                    "错误识别",
                ],
            },
            "AAA": {
                "level": "AAA",
                "description": "最高级别的可访问性",
                "requirements": [
                    "AA级别的所有要求",
                    "对比度至少7:1",
                    "文本可调整到300%",
                    "无限制的暂停",
                    "上下文相关的帮助",
                ],
            },
        }

        return requirements.get(level, requirements["AA"])


class AccessibilityAudit:
    """可访问性审计"""

    @staticmethod
    def audit_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        审计响应数据的可访问性

        Args:
            data: 响应数据

        Returns:
            审计结果
        """
        issues = []

        # 检查是否有文本替代
        if "images" in data:
            for image in data["images"]:
                if not image.get("alt"):
                    issues.append(
                        {
                            "type": "missing_alt_text",
                            "severity": "high",
                            "element": image.get("src", "unknown"),
                        }
                    )

        # 检查颜色对比度
        if "colors" in data:
            for color in data["colors"]:
                if not AccessibilityAudit._check_contrast(
                    color.get("foreground"), color.get("background")
                ):
                    ratio = AccessibilityAudit._contrast_ratio(
                        color.get("foreground"), color.get("background")
                    )
                    issues.append(
                        {
                            "type": "low_contrast",
                            "severity": "medium",
                            "element": color.get("element", "unknown"),
                            "contrast_ratio": round(ratio, 2) if ratio is not None else None,
                            "required_ratio": AccessibilityAudit.MIN_CONTRAST_RATIO_AA,
                        }
                    )

        # 检查键盘导航
        if "interactive_elements" in data:
            for element in data["interactive_elements"]:
                if not element.get("tabindex") and element.get("role") not in [
                    "presentation",
                    "none",
                ]:
                    issues.append(
                        {
                            "type": "missing_tabindex",
                            "severity": "low",
                            "element": element.get("id", "unknown"),
                        }
                    )

        return {"total_issues": len(issues), "issues": issues, "wcag_level": "AA"}

    # WCAG 2.1 AA 对普通文本要求的最小对比度
    MIN_CONTRAST_RATIO_AA = 4.5

    @staticmethod
    def _parse_color(color: Any) -> tuple:
        """
        将 #RGB/#RRGGBB 十六进制颜色字符串解析为 (r, g, b)，取值 0-255。

        解析失败（非字符串、非法字符、长度不符）时返回 None。
        """
        if not isinstance(color, str):
            return None

        value = color.strip().lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6:
            return None
        try:
            return (
                int(value[0:2], 16),
                int(value[2:4], 16),
                int(value[4:6], 16),
            )
        except ValueError:
            return None

    @staticmethod
    def _relative_luminance(rgb: tuple) -> float:
        """按 WCAG 相对亮度公式计算，输入 (r, g, b) 0-255。"""

        def _channel(c: int) -> float:
            cs = c / 255.0
            return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)

    @staticmethod
    def _contrast_ratio(foreground: str, background: str) -> Any:
        """返回 WCAG 对比度比值 (>=1.0)；无法解析颜色时返回 None。"""
        fg = AccessibilityAudit._parse_color(foreground)
        bg = AccessibilityAudit._parse_color(background)
        if fg is None or bg is None:
            return None
        l1 = AccessibilityAudit._relative_luminance(fg)
        l2 = AccessibilityAudit._relative_luminance(bg)
        lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _check_contrast(
        foreground: str,
        background: str,
        min_ratio: float = MIN_CONTRAST_RATIO_AA,
    ) -> bool:
        """
        检查颜色对比度是否符合 WCAG 2.1 AA（默认 4.5:1）。

        真实计算前景/背景色的相对亮度对比度；若任一颜色无法解析
        （例如使用 CSS 变量或命名色而非十六进制），则无法判定，返回 True
        以免对未知输入产生误报。

        Args:
            foreground: 前景色（#RGB 或 #RRGGBB）
            background: 背景色（#RGB 或 #RRGGBB）
            min_ratio: 要求的最小对比度比值

        Returns:
            是否符合对比度要求
        """
        ratio = AccessibilityAudit._contrast_ratio(foreground, background)
        if ratio is None:
            logger.debug(
                "跳过无法解析的颜色对比度检查: foreground=%r background=%r",
                foreground,
                background,
            )
            return True
        return ratio >= min_ratio


class AccessibilityMiddleware:
    """可访问性中间件配置"""

    def __init__(self):
        """初始化可访问性中间件"""
        self._headers_config = {
            "enable_a11y_headers": True,
            "wcag_level": "AA",
            "default_language": "zh-CN",
        }

    def get_config(self) -> Dict[str, Any]:
        """
        获取配置

        Returns:
            配置字典
        """
        return self._headers_config

    def update_config(self, config: Dict[str, Any]):
        """
        更新配置

        Args:
            config: 配置字典
        """
        self._headers_config.update(config)


# 全局可访问性中间件实例
accessibility_middleware = AccessibilityMiddleware()


async def setup_accessibility_support():
    """
    设置可访问性支持

    Returns:
        设置结果
    """
    try:
        logger.info("Accessibility support setup completed")

        return {
            "status": "success",
            "wcag_level": accessibility_middleware.get_config()["wcag_level"],
            "guidelines": AccessibilityGuidelines.WCAG_21_GUIDELINES,
        }

    except Exception as e:
        logger.error(f"Accessibility support setup failed: {e}")
        return {"status": "error", "error": str(e)}
