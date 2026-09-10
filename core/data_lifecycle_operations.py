# -*- coding: utf-8 -*-
"""
Actual Data Lifecycle Operations
实际数据生命周期操作

实现数据归档和清理的实际数据库操作。

归档语义（与 ``core.data_lifecycle_manager`` 保持一致）：把早于截止时间的行
以 gzip 压缩的 JSONL 文件导出到归档目录，删除后再从主表移除（move 语义）。
表名与时间列名全部取自 ``core/models.py``：

* ``alerts``      -> ``Alert.detected_at``  （业务时间，非 ``created_at``）
* ``metrics``     -> ``Metrics.timestamp``
* ``audit_logs``  -> ``AuditLog.created_at``

任何一项归档失败都会记录 error 级日志并返回 0（调用方据此判断是否成功），
不会静默吞掉异常。
"""

import gzip
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical storage backing each archived category.
# ``table`` / ``timestamp_column`` are the *only* identifiers interpolated into
# the executed SQL; both are static, code-owned constants taken verbatim from
# ``core/models.py`` -- never from user input.
# ---------------------------------------------------------------------------
_DB_BACKED_CATEGORIES: Dict[str, Tuple[str, str]] = {
    "alerts": ("alerts", "detected_at"),
    "metrics": ("metrics", "timestamp"),
    "audit_logs": ("audit_logs", "created_at"),
}


def _archive_root() -> Path:
    """归档根目录（默认 ``DATA_ARCHIVE_DIR`` 或 ``archive``）。"""
    return Path(os.getenv("DATA_ARCHIVE_DIR", "archive"))


def _write_archive_file(category: str, table: str, rows: List[Dict[str, Any]]) -> str:
    """把 ``rows`` 写成 gzip 压缩的 JSONL 归档文件并返回其路径。"""
    directory = _archive_root() / category
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{table}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl.gz"
    archive_path = directory / filename
    with gzip.open(archive_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, default=str) + "\n")
    return str(archive_path)


async def _archive_table(category: str, cutoff_date: datetime) -> int:
    """导出并删除 ``category`` 中早于 ``cutoff_date`` 的行。

    Returns:
        被归档（并从主表移除）的行数。
    """
    from sqlalchemy import text

    from core.db_engine import AsyncSessionLocal

    table, timestamp_column = _DB_BACKED_CATEGORIES[category]

    # ``table``/``timestamp_column`` 来自静态白名单映射，非用户输入。
    select_stmt = text(f"SELECT * FROM {table} WHERE {timestamp_column} < :cutoff")  # noqa: S608, E501
    delete_stmt = text(f"DELETE FROM {table} WHERE {timestamp_column} < :cutoff")  # noqa: S608

    async with AsyncSessionLocal() as session:
        result = await session.execute(select_stmt, {"cutoff": cutoff_date})
        rows: List[Dict[str, Any]] = [dict(row._mapping) for row in result.fetchall()]

        if not rows:
            logger.info(f"No {category} rows older than {cutoff_date}, nothing to archive")
            return 0

        archive_file = _write_archive_file(category, table, rows)

        await session.execute(delete_stmt, {"cutoff": cutoff_date})
        await session.commit()

    logger.info(f"Archived {len(rows)} {category} rows to {archive_file}")
    return len(rows)


async def archive_alerts(cutoff_date: datetime) -> int:
    """
    归档告警数据

    Args:
        cutoff_date: 截止日期

    Returns:
        归档记录数
    """
    try:
        return await _archive_table("alerts", cutoff_date)
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
        return await _archive_table("metrics", cutoff_date)
    except Exception as e:
        logger.error(f"Failed to archive metrics: {e}")
        return 0


async def archive_audit_logs(cutoff_date: datetime) -> int:
    """
    归档审计日志

    Args:
        cutoff_date: 截止日期

    Returns:
        归档记录数
    """
    try:
        return await _archive_table("audit_logs", cutoff_date)
    except Exception as e:
        logger.error(f"Failed to archive audit logs: {e}")
        return 0


def _temporary_directory() -> Path:
    """临时文件目录（默认 ``TEMPORARY_DATA_DIR`` 或 ``temp``）。"""
    return Path(os.getenv("TEMPORARY_DATA_DIR", "temp"))


async def cleanup_temporary_files(cutoff_date: datetime) -> int:
    """
    清理临时文件

    Args:
        cutoff_date: 截止日期

    Returns:
        删除的文件数
    """
    try:
        directory = _temporary_directory()
        if not directory.exists():
            return 0

        deleted_count = 0
        # 深度优先遍历，先删文件再回收空目录。
        for entry in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            try:
                if entry.is_dir():
                    if not any(entry.iterdir()):
                        entry.rmdir()
                    continue
                file_mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                if file_mtime < cutoff_date:
                    entry.unlink()
                    deleted_count += 1
            except Exception as exc:  # noqa: BLE001 - 单个文件失败不应中断整体清理
                logger.warning(f"Unable to remove {entry}: {exc}")

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
