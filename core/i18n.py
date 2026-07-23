# -*- coding: utf-8 -*-
# core/i18n.py — AIOps Agent 后端国际化引擎(v2.2)
#
# 设计要点:
#   - I18N-1: ContextVar 协程安全,每个请求独立语言上下文
#   - I18N-2: lifespan 预加载,运行期无锁快速路径
#   - I18N-3: 三级降级: 目标语言 → 中文兜底 → key 本身
#   - I18N-4: 支持 {name} 插值语法
#   - I18N-5: 线程安全加载(Lock 保护,仅首次/热重载时)
#   - I18N-6: 热重载接口(不重启更新语言包)
#   - I18N-7: _meta 字段自动过滤(不污染翻译键空间)
#
# 使用方式:
#   from core.i18n import msg, set_locale, get_locale
#   return {"error": msg("alert.not_found", alert_id=alert_id)}

import json
import logging
from contextvars import ContextVar
from pathlib import Path
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# 常量
# ============================================================
_SUPPORTED_LOCALES: frozenset = frozenset(["zh", "en"])
_FALLBACK_LOCALE: str = "zh"

# 语言包目录:使用 config.BASE_DIR 确保路径一致性
try:
    from config import BASE_DIR

    _MESSAGES_DIR: Path = BASE_DIR / "messages"
except ImportError:
    _MESSAGES_DIR = Path(__file__).resolve().parent.parent / "messages"

# 自动创建 messages 目录(首次部署时)
try:
    _MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError) as e:
    logger.warning(f"i18n: messages 目录创建失败(不影响启动): {e}")

# ============================================================
# 协程安全的当前语言上下文
# I18N-1: 每个请求通过中间件 set_locale(),互不干扰
# ============================================================
_current_locale: ContextVar[str] = ContextVar("i18n_locale", default=_FALLBACK_LOCALE)

# ============================================================
# 语言包存储 + 加载锁
# I18N-2 + I18N-5: lifespan 预加载 + 线程安全
# ============================================================
_messages: dict[str, dict[str, str]] = {}
_load_lock: Lock = Lock()
_loaded: bool = False


def _load_messages(force: bool = False) -> None:
    """
    加载所有语言包 JSON 文件到内存

    I18N-2: 由 lifespan 在启动时调用(同步,无事件循环阻塞风险)
    I18N-5: Lock 保护,多线程安全
    I18N-6: force=True 时强制重新加载(热重载)
    I18N-7: 自动过滤以 _ 开头的元数据键(如 _meta)
    """
    global _loaded

    with _load_lock:
        if _loaded and not force:
            return

        for locale in _SUPPORTED_LOCALES:
            filepath = _MESSAGES_DIR / f"{locale}.json"
            if not filepath.exists():
                logger.warning(f"i18n: 语言包文件不存在: {filepath},该语言的翻译将降级到 key 本身")
                _messages[locale] = {}
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    translations = json.load(f)

                if not isinstance(translations, dict):
                    logger.error(
                        f"i18n: 语言包 {locale}.json 根元素必须是 dict,"
                        f"实际类型: {type(translations).__name__}"
                    )
                    _messages[locale] = {}
                    continue

                # I18N-7: 过滤以 _ 开头的元数据键
                _messages[locale] = {k: v for k, v in translations.items() if not k.startswith("_")}

                logger.info(
                    f"i18n: 已加载语言包 {locale} | "
                    f"路径={filepath} | "
                    f"条目数={len(_messages[locale])}"
                )

            except json.JSONDecodeError as e:
                logger.error(f"i18n: 语言包 {locale}.json JSON 解析失败: {e}")
                _messages[locale] = {}

            except Exception as e:
                logger.error(
                    f"i18n: 语言包 {locale}.json 加载异常: {e}",
                    exc_info=True,
                )
                _messages[locale] = {}

        _loaded = True
        logger.info(
            "i18n: 语言包加载完成 | "
            f"已加载语言: {sorted(_messages.keys())} | "
            f"总条目数: {sum(len(v) for v in _messages.values())}"
        )


# ============================================================
# 核心 API: 设置/获取当前语言
# ============================================================
def set_locale(locale: str) -> None:
    """
    设置当前请求的语言(由 i18n 中间件调用)

    I18N-1: 基于 ContextVar,协程安全,不同请求互不影响

    Args:
        locale: 'zh' 或 'en',非法值自动降级到 'zh'
    """
    if not isinstance(locale, str):
        locale = _FALLBACK_LOCALE
    safe = locale.strip().lower()
    if safe not in _SUPPORTED_LOCALES:
        safe = _FALLBACK_LOCALE
    _current_locale.set(safe)


def get_locale() -> str:
    """获取当前请求的语言"""
    return _current_locale.get()


# ============================================================
# 核心 API: 翻译函数
# ============================================================
def msg(key: str, **kwargs: Any) -> str:
    """
    后端翻译函数 — 根据当前请求语言返回对应文本

    I18N-3: 三级降级策略:
      1. 目标语言翻译(如 en.json 中的 key)
      2. 中文兜底(zh.json 中的 key)
      3. key 本身(两个语言包都没有)

    I18N-4: 支持 {name} 插值语法:
      msg("alert.not_found", alert_id="CPU-123")
      → "未找到待审批记录: CPU-123"  (中文)
      → "Pending approval not found: CPU-123"  (英文)

    Args:
        key:    翻译 key,格式: "模块.动作_描述"
        kwargs: 插值参数,替换文本中的 {name}

    Returns:
        翻译后的文本(含插值)
    """
    # 无锁快速路径:lifespan 预加载后 _loaded 始终为 True
    if not _loaded:
        _load_messages()

    locale = _current_locale.get()

    # I18N-3: 三级降级
    text = _messages.get(locale, {}).get(key) or _messages.get(_FALLBACK_LOCALE, {}).get(key) or key

    # I18N-4: {name} 插值
    if kwargs:
        for k, v in kwargs.items():
            text = text.replace(f"{{{k}}}", str(v))

    return text


# ============================================================
# 工具 API
# ============================================================
def get_supported_locales() -> list[str]:
    """返回所有支持的语言列表(已排序)"""
    return sorted(_SUPPORTED_LOCALES)


def get_messages_stats() -> dict[str, Any]:
    """
    返回语言包统计信息(供调试和健康检查)
    """
    if not _loaded:
        _load_messages()

    zh_keys = set(_messages.get("zh", {}).keys())
    en_keys = set(_messages.get("en", {}).keys())

    return {
        "loaded": _loaded,
        "supported_locales": sorted(_SUPPORTED_LOCALES),
        "fallback_locale": _FALLBACK_LOCALE,
        "current_locale": _current_locale.get(),
        "messages_dir": str(_MESSAGES_DIR),
        "locale_stats": {locale: len(msgs) for locale, msgs in _messages.items()},
        "missing_in_en": sorted(zh_keys - en_keys),
        "missing_in_zh": sorted(en_keys - zh_keys),
    }


# ============================================================
# 热重载 API
# ============================================================
def reload_messages() -> dict[str, Any]:
    """
    I18N-6: 热重载语言包(不重启服务)
    Returns: 加载结果统计
    """
    logger.warning("i18n: 语言包热重载开始")
    _load_messages(force=True)
    stats = get_messages_stats()
    logger.info(f"i18n: 语言包热重载完成 | stats={stats}")
    return stats


# ============================================================
# 显式导出列表
# ============================================================
__all__: list[str] = [
    "set_locale",
    "get_locale",
    "msg",
    "get_supported_locales",
    "get_messages_stats",
    "reload_messages",
]
