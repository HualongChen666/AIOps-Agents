# -*- coding: utf-8 -*-
"""
Actual Data Lifecycle Operations
实际数据生命周期操作

实现数据归档和清理的实际数据库操作。
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def archive_alerts(cutoff_date: datetime) -> int:
    """
    归档告警数据

    Args:
        cutoff_date: 截止日期

    Returns:
        归档记录数
    """
    try:
        from sqlalchemy import text

        from core.db_engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "UPDATE alerts SET archived = TRUE WHERE created_at < :cutoff AND archived = FALSE"  # noqa: E501
                ),
                {"cutoff": cutoff_date},
            )
            archived_count: int = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
            logger.info(f"Archived {archived_count} alerts before {cutoff_date}")
            return archived_count
    except Exception as e:
        logger.error(f"Failed to archive alerts: {e}")
        return 0


async def archive_metrics(cutoff_date: datetime) -> int:
    """
    归档指标数据

    Args:
        cutoff_date: 截止日期

    Returns:
        归档记录数
    """
    try:
        from sqlalchemy import text

        from core.db_engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "UPDATE metrics SET archived = TRUE WHERE timestamp < :cutoff AND archived = FALSE"  # noqa: E501
                ),
                {"cutoff": cutoff_date},
            )
            archived_count: int = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
            logger.info(f"Archived {archived_count} metrics before {cutoff_date}")
            return archived_count
    except Exception as e:
        logger.error(f"Failed to archive metrics: {e}")
        return 0


async def cleanup_temporary_files(cutoff_date: datetime) -> int:
    """
    清理临时文件

    Args:
        cutoff_date: 截止日期

    Returns:
        删除的文件数
    """
    try:
        import glob
        import os

        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            return 0

        deleted_count = 0
        for file_path in glob.glob(os.path.join(temp_dir, "*")):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff_date:
                os.remove(file_path)
                deleted_count += 1

        logger.info(f"Deleted {deleted_count} temporary files")
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup temporary files: {e}")
        return 0


async def cleanup_temporary_cache(cutoff_date: datetime) -> bool:
    """
    清理临时缓存

    Args:
        cutoff_date: 截止日期

    Returns:
        是否清理成功
    """
    try:
        import redis

        from config import REDIS_DB, REDIS_HOST, REDIS_PORT

        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

        # 清理带有temp:前缀的键
        temp_keys = r.keys("temp:*")
        if temp_keys:
            deleted = r.delete(*temp_keys)
            logger.info(f"Cleared {deleted} temporary cache entries")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to cleanup temporary cache: {e}")
        return False
