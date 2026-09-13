# -*- coding: utf-8 -*-
"""
Data Lifecycle Manager Module
数据生命周期管理模块

提供数据生命周期管理功能，包括数据归档、清理和保留策略。
"""

import asyncio
import gzip
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DataRetentionPolicy(str, Enum):
    """数据保留策略"""

    IMMEDIATE_DELETE = "immediate_delete"  # 立即删除
    RETAIN_7_DAYS = "retain_7_days"  # 保留7天
    RETAIN_30_DAYS = "retain_30_days"  # 保留30天
    RETAIN_90_DAYS = "retain_90_days"  # 保留90天
    RETAIN_1_YEAR = "retain_1_year"  # 保留1年
    RETAIN_PERMANENT = "retain_permanent"  # 永久保留


class DataCategory(str, Enum):
    """数据类别"""

    ALERTS = "alerts"
    METRICS = "metrics"
    AUDIT_LOGS = "audit_logs"
    TEMPORARY = "temporary"
    BACKUP = "backup"
    CONFIGURATION = "configuration"


# ---------------------------------------------------------------------------
# Physical storage backing each data category.
#
# The table and timestamp-column names below are taken verbatim from
# ``core/models.py`` (``Alert.detected_at``, ``Metrics.timestamp``,
# ``AuditLog.created_at``) so the executed SQL always matches the live schema.
# Categories that are absent from this map are stored as files on disk and are
# resolved through :meth:`DataLifecycleManager._category_directory`.
# ---------------------------------------------------------------------------
_DB_BACKED_CATEGORIES: Dict[DataCategory, Tuple[str, str]] = {
    DataCategory.ALERTS: ("alerts", "detected_at"),
    DataCategory.METRICS: ("metrics", "timestamp"),
    DataCategory.AUDIT_LOGS: ("audit_logs", "created_at"),
}


@dataclass
class DataLifecycleRule:
    """数据生命周期规则"""

    category: DataCategory
    retention_policy: DataRetentionPolicy
    archive_enabled: bool = False
    archive_location: Optional[str] = None
    compression_enabled: bool = True
    description: str = ""


class DataLifecycleManager:
    """数据生命周期管理器"""

    def __init__(
        self,
        archive_root: Optional[str] = None,
        session_factory: Optional[Callable[[], Any]] = None,
    ):
        """初始化数据生命周期管理器

        Args:
            archive_root: Directory that receives the compressed archive files
                (defaults to ``DATA_ARCHIVE_DIR`` or ``archive``).
            session_factory: Async session factory used for database backed
                categories.  Defaults to the application engine
                (``core.db_engine.AsyncSessionLocal``).
        """
        self._archive_root = Path(archive_root or os.getenv("DATA_ARCHIVE_DIR", "archive"))
        self._session_factory = session_factory
        self._rules: Dict[DataCategory, DataLifecycleRule] = {}
        self._cleanup_stats: Dict[str, Any] = {
            "last_cleanup": None,
            "total_archived": 0,
            "total_deleted": 0,
            "total_size_freed": 0,
        }
        self._setup_default_rules()

    def _setup_default_rules(self):
        """设置默认规则"""
        self._rules[DataCategory.ALERTS] = DataLifecycleRule(
            category=DataCategory.ALERTS,
            retention_policy=DataRetentionPolicy.RETAIN_90_DAYS,
            archive_enabled=True,
            archive_location="archive/alerts",
            description="告警数据保留90天后归档",
        )

        self._rules[DataCategory.METRICS] = DataLifecycleRule(
            category=DataCategory.METRICS,
            retention_policy=DataRetentionPolicy.RETAIN_30_DAYS,
            archive_enabled=True,
            archive_location="archive/metrics",
            description="指标数据保留30天后归档",
        )

        self._rules[DataCategory.AUDIT_LOGS] = DataLifecycleRule(
            category=DataCategory.AUDIT_LOGS,
            retention_policy=DataRetentionPolicy.RETAIN_1_YEAR,
            archive_enabled=True,
            archive_location="archive/audit_logs",
            description="审计日志保留1年后归档",
        )

        self._rules[DataCategory.TEMPORARY] = DataLifecycleRule(
            category=DataCategory.TEMPORARY,
            retention_policy=DataRetentionPolicy.RETAIN_7_DAYS,
            archive_enabled=False,
            description="临时数据保留7天后删除",
        )

        self._rules[DataCategory.BACKUP] = DataLifecycleRule(
            category=DataCategory.BACKUP,
            retention_policy=DataRetentionPolicy.RETAIN_90_DAYS,
            archive_enabled=False,
            description="备份数据保留90天",
        )

        self._rules[DataCategory.CONFIGURATION] = DataLifecycleRule(
            category=DataCategory.CONFIGURATION,
            retention_policy=DataRetentionPolicy.RETAIN_PERMANENT,
            archive_enabled=False,
            description="配置数据永久保留",
        )

    def get_retention_days(self, policy: DataRetentionPolicy) -> int:
        """
        获取保留天数

        Args:
            policy: 保留策略

        Returns:
            保留天数
        """
        mapping = {
            DataRetentionPolicy.IMMEDIATE_DELETE: 0,
            DataRetentionPolicy.RETAIN_7_DAYS: 7,
            DataRetentionPolicy.RETAIN_30_DAYS: 30,
            DataRetentionPolicy.RETAIN_90_DAYS: 90,
            DataRetentionPolicy.RETAIN_1_YEAR: 365,
            DataRetentionPolicy.RETAIN_PERMANENT: -1,  # 永久保留
        }
        return mapping.get(policy, 30)

    async def archive_old_data(self, category: DataCategory) -> Dict[str, Any]:
        """
        归档旧数据

        Args:
            category: 数据类别

        Returns:
            归档结果
        """
        if category not in self._rules:
            return {"status": "error", "error": f"No rule for category: {category}"}

        rule = self._rules[category]

        if not rule.archive_enabled:
            logger.info(f"Archiving not enabled for {category}")
            return {"status": "skipped", "reason": "Archiving not enabled"}

        retention_days = self.get_retention_days(rule.retention_policy)
        if retention_days <= 0:
            logger.info(f"No archiving needed for {category} (policy: {rule.retention_policy})")
            return {"status": "skipped", "reason": "No retention period"}

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        logger.info(f"Archiving {category} data older than {cutoff_date}")

        try:
            archived_count, archive_file = await self._archive_expired_rows(category, cutoff_date)
        except Exception as exc:
            logger.error(f"Archiving {category} failed: {exc}")
            return {"status": "error", "category": category, "error": str(exc)}

        self._cleanup_stats["total_archived"] += archived_count
        self._cleanup_stats["last_cleanup"] = datetime.now(timezone.utc).isoformat()

        return {
            "status": "success",
            "category": category,
            "archived_count": archived_count,
            "cutoff_date": cutoff_date.isoformat(),
            "archive_location": rule.archive_location,
            "archive_file": archive_file,
        }

    # ------------------------------------------------------------------
    # Real storage backends
    # ------------------------------------------------------------------
    def _get_session_factory(self) -> Callable[[], Any]:
        """Return the async session factory used for database backed categories."""
        if self._session_factory is not None:
            return self._session_factory
        from core.db_engine import AsyncSessionLocal

        return AsyncSessionLocal

    @staticmethod
    def _category_directory(category: DataCategory) -> Optional[str]:
        """Filesystem location for categories that are stored as files."""
        if category is DataCategory.TEMPORARY:
            return os.getenv("TEMPORARY_DATA_DIR", "temp")
        if category is DataCategory.BACKUP:
            return os.getenv("BACKUP_LOCATION", "/backups")
        return None

    async def _archive_expired_rows(
        self, category: DataCategory, cutoff_date: datetime
    ) -> tuple:
        """Move every row/file older than ``cutoff_date`` into the archive store.

        Database backed categories are exported to a gzip-compressed JSONL file
        under ``<archive_root>/<category>/`` and then removed from the primary
        table (move semantics).  Filesystem backed categories (temporary data,
        backups) simply have their expired files removed.

        Returns:
            ``(archived_count, archive_file)``；``archive_file`` 仅在本类别实际
            写出归档文件时非空——按调用局返回，避免并发归档不同类别时互相串台。
        """
        db_target = _DB_BACKED_CATEGORIES.get(category)
        if db_target is None:
            return self._cleanup_directory_for(category, cutoff_date), None

        table, timestamp_column = db_target
        rows = await self._fetch_expired_rows(table, timestamp_column, cutoff_date)
        archive_file: Optional[str] = None
        if rows:
            archive_file = self._write_archive_file(category, table, rows)
            logger.info(f"Archived {len(rows)} {category.value} rows to {archive_file}")
        await self._delete_expired_rows(category, cutoff_date)
        return len(rows), archive_file

    async def _fetch_expired_rows(
        self, table: str, timestamp_column: str, cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """Read the rows that are due for archival."""
        from sqlalchemy import text

        session_factory = self._get_session_factory()
        # ``table``/``timestamp_column`` come from the static, code-owned
        # ``_DB_BACKED_CATEGORIES`` map -- never from user input.
        statement = text(f"SELECT * FROM {table} WHERE {timestamp_column} < :cutoff")  # noqa: S608
        async with session_factory() as session:
            result = await session.execute(statement, {"cutoff": cutoff_date})
            return [dict(row._mapping) for row in result.fetchall()]

    async def _delete_expired_rows(self, category: DataCategory, cutoff_date: datetime) -> int:
        """Delete rows (database) or files (filesystem) older than ``cutoff_date``."""
        db_target = _DB_BACKED_CATEGORIES.get(category)
        if db_target is None:
            return self._cleanup_directory_for(category, cutoff_date)

        table, timestamp_column = db_target
        from sqlalchemy import text

        session_factory = self._get_session_factory()
        # Static, code-owned identifiers -- see ``_DB_BACKED_CATEGORIES``.
        statement = text(f"DELETE FROM {table} WHERE {timestamp_column} < :cutoff")  # noqa: S608
        async with session_factory() as session:
            result = await session.execute(statement, {"cutoff": cutoff_date})
            await session.commit()
            return int(result.rowcount or 0)

    def _write_archive_file(
        self, category: DataCategory, table: str, rows: List[Dict[str, Any]]
    ) -> str:
        """Write ``rows`` as a gzip-compressed JSONL archive and return its path."""
        directory = self._archive_root / category.value
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{table}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl.gz"
        archive_path = directory / filename
        with gzip.open(archive_path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, default=str) + "\n")
        return str(archive_path)

    def _cleanup_directory_for(self, category: DataCategory, cutoff_date: datetime) -> int:
        """Purge expired files for a filesystem backed category."""
        directory = self._category_directory(category)
        if directory is None:
            logger.warning(f"No storage backend configured for category {category}")
            return 0
        return self._purge_directory(Path(directory), cutoff_date)

    @staticmethod
    def _purge_directory(root: Path, cutoff_date: datetime) -> int:
        """Remove files older than ``cutoff_date`` below ``root`` (recursively)."""
        if not root.exists():
            logger.info(f"Directory {root} does not exist, nothing to purge")
            return 0

        removed = 0
        # Deepest entries first so emptied directories can be pruned.
        for entry in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            try:
                if entry.is_dir():
                    if not any(entry.iterdir()):
                        entry.rmdir()
                    continue
                modified = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
                if modified < cutoff_date:
                    entry.unlink()
                    removed += 1
            except OSError as exc:
                logger.warning(f"Unable to purge {entry}: {exc}")
        logger.info(f"Purged {removed} expired entries from {root}")
        return removed

    async def cleanup_temp_data(self) -> Dict[str, Any]:
        """
        清理临时数据

        Returns:
            清理结果
        """
        category = DataCategory.TEMPORARY
        rule = self._rules[category]

        retention_days = self.get_retention_days(rule.retention_policy)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        logger.info(f"Cleaning up temporary data older than {cutoff_date}")

        # 清理临时文件
        deleted_count = await self._cleanup_temporary_files(cutoff_date)

        # 清理临时缓存
        cache_cleared = await self._cleanup_temporary_cache(cutoff_date)

        self._cleanup_stats["total_deleted"] += deleted_count
        self._cleanup_stats["last_cleanup"] = datetime.now(timezone.utc).isoformat()

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cache_cleared": cache_cleared,
            "cutoff_date": cutoff_date.isoformat(),
        }

    async def _cleanup_temporary_files(self, cutoff_date: datetime) -> int:
        """
        清理临时文件

        Args:
            cutoff_date: 截止日期

        Returns:
            删除的文件数
        """
        return self._cleanup_directory_for(DataCategory.TEMPORARY, cutoff_date)

    async def _cleanup_temporary_cache(self, cutoff_date: datetime) -> bool:
        """
        清理临时缓存

        Args:
            cutoff_date: 截止日期

        Returns:
            是否清理成功
        """
        try:
            from core.query_optimization import query_cache

            query_cache.cleanup_expired()
            logger.info("Temporary cache cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return False

    async def apply_retention_policy(self, category: DataCategory) -> Dict[str, Any]:
        """
        应用保留策略

        Args:
            category: 数据类别

        Returns:
            应用结果
        """
        if category not in self._rules:
            return {"status": "error", "error": f"No rule for category: {category}"}

        rule = self._rules[category]

        if rule.archive_enabled:
            # 先归档
            archive_result = await self.archive_old_data(category)
        else:
            archive_result = None

        # 然后删除过期数据
        retention_days = self.get_retention_days(rule.retention_policy)

        if retention_days > 0:
            delete_result = await self._delete_expired_data(category, retention_days)
        else:
            delete_result = None

        return {
            "status": "success",
            "category": category,
            "archive_result": archive_result,
            "delete_result": delete_result,
        }

    async def _delete_expired_data(
        self, category: DataCategory, retention_days: int
    ) -> Dict[str, Any]:
        """
        删除过期数据

        Args:
            category: 数据类别
            retention_days: 保留天数

        Returns:
            删除结果
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        logger.info(f"Deleting expired {category} data older than {cutoff_date}")

        try:
            deleted_count = await self._delete_expired_rows(category, cutoff_date)
        except Exception as exc:
            logger.error(f"Deleting expired {category} data failed: {exc}")
            return {"status": "error", "category": category, "error": str(exc)}

        self._cleanup_stats["total_deleted"] += deleted_count

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        获取清理统计信息

        Returns:
            统计信息
        """
        return self._cleanup_stats.copy()

    def get_rules(self) -> Dict[DataCategory, DataLifecycleRule]:
        """
        获取所有规则

        Returns:
            规则字典
        """
        return self._rules.copy()

    def add_rule(self, rule: DataLifecycleRule):
        """
        添加规则

        Args:
            rule: 数据生命周期规则
        """
        self._rules[rule.category] = rule
        logger.info(f"Added lifecycle rule for {rule.category}")


# 全局数据生命周期管理器实例
data_lifecycle_manager = DataLifecycleManager()


async def setup_data_lifecycle() -> Any:
    """
    设置数据生命周期管理

    Returns:
        设置结果
    """
    try:
        logger.info("Data lifecycle management setup completed")

        return {
            "status": "success",
            "rules_count": len(data_lifecycle_manager.get_rules()),
            "categories": [cat.value for cat in data_lifecycle_manager.get_rules().keys()],
        }

    except Exception as e:
        logger.error(f"Data lifecycle setup failed: {e}")
        return {"status": "error", "error": str(e)}


async def data_lifecycle_cleanup_task() -> Any:
    """
    定期数据生命周期清理任务
    """
    while True:
        try:
            logger.info("Starting data lifecycle cleanup")

            # 应用所有规则的保留策略
            for category in data_lifecycle_manager.get_rules().keys():
                result = await data_lifecycle_manager.apply_retention_policy(category)
                logger.info(f"Applied retention policy for {category}: {result}")

            # 清理临时数据
            temp_cleanup = await data_lifecycle_manager.cleanup_temp_data()
            logger.info(f"Temporary data cleanup: {temp_cleanup}")

            # 获取统计信息
            stats = data_lifecycle_manager.get_cleanup_stats()
            logger.info(f"Cleanup stats: {stats}")

            # 每天执行一次
            await asyncio.sleep(86400)

        except Exception as e:
            logger.error(f"Data lifecycle cleanup failed: {e}")
            await asyncio.sleep(3600)  # 出错后等待1小时再重试
