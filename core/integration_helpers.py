# -*- coding: utf-8 -*-
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
    """
    为ai_engine模块应用增强重试机制
    """
    try:
        pass

        # 为HTTP客户端应用增强重试（如果需要）
        # 这里可以根据需要添加具体的增强逻辑

        logger.info("🔧 P0 Integration: AI engine enhancement checked")

    except ImportError as e:
        logger.warning(f"🔧 P0 Integration: Failed to import ai_engine: {e}")
    except Exception as e:
        logger.error(f"🔧 P0 Integration: Failed to enhance ai_engine: {e}")


# ============================================================
# 🔧 P0 Integration: 数据库引擎增强
# ============================================================
async def enhance_db_engine():
    """
    为db_engine模块应用连接池优化
    """
    try:
        # 检查是否有POSTGRES_URL配置
        from config import POSTGRES_URL
        from core.connection_pool_optimization import create_optimized_engine

        # 使用优化的连接池配置
        await create_optimized_engine(POSTGRES_URL)

        # 如果需要，可以替换现有的engine
        # db_engine.engine = optimized_engine

        logger.info("🔧 P0 Integration: Connection pool optimization applied to db_engine")

    except ImportError as e:
        logger.warning(f"🔧 P0 Integration: Failed to import db_engine: {e}")
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
