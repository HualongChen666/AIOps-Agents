# -*- coding: utf-8 -*-
"""``integration_helpers`` module.

Top-level functions: apply_enhanced_retry_to_function, enhance_notify_engine, enhance_ai_engine, enhance_db_engine, apply_all_enhancements"""

# core/integration_helpers.py
# P0/P1/P2增强功能集成辅助模块
#
# 此模块提供增强版本的函数，用于集成到现有7层架构中
# 不修改原有代码，通过替换函数引用的方式集成增强功能

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ============================================================
# 🔧 P0 Integration: 增强重试机制包装器
# ============================================================
def apply_enhanced_retry_to_function(
    original_func: Callable,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retry_on_exceptions: Optional[tuple] = None,
) -> Callable:
    """
    为函数应用增强重试机制的包装器

    Args:
        original_func: 原始函数
        max_attempts: 最大重试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        retry_on_exceptions: 需要重试的异常类型

    Returns:
        增强重试版本的函数
    """
    try:
        from core.retry_enhanced import EnhancedRetry, RetryStrategy

        # 创建增强重试实例
        retry_instance = EnhancedRetry(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            jitter=True,
            retry_on_exceptions=retry_on_exceptions,
        )

        # 应用增强重试
        enhanced_func = retry_instance(original_func)

        logger.info(f"🔧 P0 Integration: Enhanced retry applied to {original_func.__name__}")
        return enhanced_func

    except ImportError:
        logger.warning(
            f"🔧 P0 Integration: Enhanced retry not available for {original_func.__name__}"
        )
        return original_func
    except Exception as e:
        logger.error(f"🔧 P0 Integration: Failed to apply retry to {original_func.__name__}: {e}")
        return original_func


# ============================================================
# 🔧 P0 Integration: 通知引擎增强
# ============================================================
def enhance_notify_engine():
    """
    为notify_engine模块应用增强重试机制
    """
    try:
        from core import notify_engine

        # 检查是否有_post_webhook函数
        if hasattr(notify_engine, "_post_webhook"):
            original_func = notify_engine._post_webhook

            # 应用增强重试
            import httpx

            enhanced_func = apply_enhanced_retry_to_function(
                original_func,
                max_attempts=3,
                base_delay=1.0,
                max_delay=10.0,
                retry_on_exceptions=(
                    ConnectionError,
                    TimeoutError,
                    httpx.ConnectError,
                    httpx.TimeoutException,
                ),
            )

            # 替换函数引用
            notify_engine._post_webhook = enhanced_func
            logger.info("🔧 P0 Integration: Enhanced retry applied to notify_engine._post_webhook")

    except ImportError as e:
        logger.warning(f"🔧 P0 Integration: Failed to import notify_engine: {e}")
    except Exception as e:
        logger.error(f"🔧 P0 Integration: Failed to enhance notify_engine: {e}")


# ============================================================
# 🔧 P0 Integration: AI引擎增强
# ============================================================
def enhance_ai_engine():
    """为 ai_engine 的全局 HTTP 客户端注入传输层重试（P0 增强）。

    真正生效：monkey-patch ``core.ai_engine._get_http_client``，使其返回带
    ``httpx.AsyncHTTPTransport(retries=N)`` 的客户端，从而对瞬时网络错误
    自动重试；对已增强的客户端保持幂等。
    """
    try:
        import httpx

        import core.ai_engine as ai_engine
    except ImportError as e:
        logger.warning(f"🔧 P0 Integration: Failed to import ai_engine: {e}")
        return

    original = getattr(ai_engine, "_get_http_client", None)
    if original is None:
        logger.warning("🔧 P0 Integration: ai_engine 未暴露 _get_http_client，跳过增强")
        return
    if getattr(original, "_aiops_retry_enhanced", False):
        logger.info("🔧 P0 Integration: AI engine HTTP client already enhanced")
        return

    max_attempts = 3

    def _enhanced_get_http_client():
        client = getattr(ai_engine, "_http_client", None)
        if client is None or getattr(client, "is_closed", False):
            client = httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=max_attempts),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
            ai_engine._http_client = client
        return client

    _enhanced_get_http_client._aiops_retry_enhanced = True  # type: ignore[attr-defined]
    ai_engine._get_http_client = _enhanced_get_http_client

    logger.info(
        f"🔧 P0 Integration: AI engine HTTP client enhanced with transport retries={max_attempts}"
    )


# ============================================================
# 🔧 P0 Integration: 数据库引擎增强
# ============================================================
async def enhance_db_engine():
    """将优化后的连接池引擎真正接入 db_engine（P0 性能增强）。

    此前仅创建 ``create_optimized_engine`` 却丢弃返回值，db_engine 实际未变。
    现在：校验当前引擎连接池是否已符合优化配置，若不符则重建并热替换
    ``db_engine`` 的引擎与 session factory，同时对旧引擎做 dispose。
    """
    try:
        from config import POSTGRES_URL
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from core import db_engine
        from core.connection_pool_optimization import (
            CONNECTION_POOL_CONFIG,
            create_optimized_engine,
        )
    except ImportError as e:
        logger.warning(f"🔧 P0 Integration: Failed to import db_engine: {e}")
        return

    try:
        db_url = db_engine._effective_database_url()
        if db_url.startswith("sqlite"):
            logger.info(
                "🔧 P0 Integration: db_engine 使用 SQLite，连接池参数不适用，跳过优化"
            )
            return

        current = db_engine._ensure_engine()
        pool = getattr(current, "pool", None)
        expected_size = CONNECTION_POOL_CONFIG.get("pool_size")
        already_optimized = False
        if pool is not None and hasattr(pool, "size"):
            try:
                already_optimized = pool.size() == expected_size
            except Exception:  # pragma: no cover - 池实现差异
                already_optimized = False

        if already_optimized:
            logger.info(
                "🔧 P0 Integration: db_engine 连接池已符合优化配置，无需替换"
            )
            return

        optimized = await create_optimized_engine(POSTGRES_URL)
        old_engine = db_engine._ENGINE
        db_engine._ENGINE = optimized
        db_engine._AsyncSessionLocal = async_sessionmaker(
            bind=optimized, expire_on_commit=False
        )
        if old_engine is not None and old_engine is not optimized:
            try:
                await old_engine.dispose()
            except Exception as exc:  # pragma: no cover - dispose 容错
                logger.warning(f"🔧 P0 Integration: 释放旧引擎失败: {exc}")

        logger.info(
            f"🔧 P0 Integration: db_engine 已切换为优化连接池引擎 | pool_size={expected_size}"
        )

    except Exception as e:
        logger.error(f"🔧 P0 Integration: Failed to enhance db_engine: {e}")


# ============================================================
# 🔧 P0 Integration: 批量应用所有增强
# ============================================================
async def apply_all_enhancements():
    """
    应用所有P0/P1增强功能到现有模块
    """
    logger.info("🔧 P0 Integration: Starting to apply all enhancements...")

    # 应用通知引擎增强
    enhance_notify_engine()

    # 应用AI引擎增强
    enhance_ai_engine()

    # 应用数据库引擎增强
    await enhance_db_engine()

    logger.info("🔧 P0 Integration: All enhancements applied successfully")
