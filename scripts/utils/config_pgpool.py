# -*- coding: utf-8 -*-
"""
PgPool-II Database HA Configuration
🔧 P1-2: PgPool-II Database HA Configuration

使用PgPool-II作为数据库负载均衡器，提供高可用性
"""

import os

from loguru import logger

# =============================
# PgPool-II Database HA Configuration
# =============================
# 使用PgPool-II作为数据库负载均衡器，提供高可用性
PGPOOL_ENABLED: bool = os.getenv("PGPOOL_ENABLED", "false").strip().lower() in ("true", "1", "yes")
PGPOOL_HOST: str = os.getenv("PGPOOL_HOST", "localhost").strip()
PGPOOL_PORT: int = int(os.getenv("PGPOOL_PORT", "5434").strip())
PGPOOL_ADMIN_PORT: int = int(os.getenv("PGPOOL_ADMIN_PORT", "9999").strip())
PGPOOL_MAX_CONNECTIONS: int = int(os.getenv("PGPOOL_MAX_CONNECTIONS", "100").strip())
PGPOOL_MIN_CONNECTIONS: int = int(os.getenv("PGPOOL_MIN_CONNECTIONS", "10").strip())


def get_database_url(use_pgpool: bool = None) -> str:
    """
    获取数据库连接URL

    Args:
        use_pgpool: 是否使用PgPool，None表示根据配置自动判断

    Returns:
        数据库连接URL字符串
    """
    from config import POSTGRES_DB, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER

    enabled = use_pgpool if use_pgpool is not None else PGPOOL_ENABLED

    if enabled:
        url = (  # noqa: E501
            f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{PGPOOL_HOST}:{PGPOOL_PORT}/{POSTGRES_DB}"
        )
        logger.info(
            f"🔧 PgPool-II enabled: Using {PGPOOL_HOST}:{PGPOOL_PORT} for database connection"  # noqa: E501
        )
        return url
    else:
        url = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"  # noqa: E501
        logger.info(
            f"🔧 Using direct database connection: {POSTGRES_HOST}:{POSTGRES_PORT}"
        )  # noqa: F541
        return url


# 自动更新数据库URL
if PGPOOL_ENABLED:
    POSTGRES_URL = get_database_url(use_pgpool=True)
    logger.info(f"🔧 PgPool-II configuration applied to database connection")  # noqa: F541
