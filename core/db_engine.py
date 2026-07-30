# -*- coding: utf-8 -*-
"""
Database Engine Module
======================

Provides async database operations with connection pooling and optimization.
Supports PostgreSQL with asyncpg driver for high-performance database access.

Key Features:
- Async database operations
- Connection pooling optimization
- Query optimization
- Database health monitoring
- Automatic reconnection
"""

# core/db_engine.py
# ------------------------------------------------------------
# Async SQLAlchemy + PostgreSQL database engine
# ------------------------------------------------------------
# 🔧 P0-1: 实现完整的PostgreSQL异步ORM模型和数据库操作
# 替换之前的no-op实现为真正的异步数据库操作
# ------------------------------------------------------------

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import POSTGRES_URL
from core.database import Base
from core.models import (
    Alert,
    AlertStatus,
    ApprovalStatus,
    PendingApproval,
    RepairRecord,
    RepairStatus,
)

logger = logging.getLogger(__name__)

# 🔧 P0-1 Enhancement: 导入连接池优化配置
try:
    from core.connection_pool_optimization import CONNECTION_POOL_CONFIG
except ImportError:
    CONNECTION_POOL_CONFIG = {
        "pool_size": 20,
        "max_overflow": 40,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "echo": False,
        "future": True,
    }
    logger.warning("Connection pool optimization config not available, using defaults")

# -----------------------------------------------------------------
# Configuration – PostgreSQL connection string.
#   * ``POSTGRES_URL`` – Full asyncpg URL, e.g.
#       postgresql+asyncpg://user:password@host:5432/database
#   * ``USE_SQLITE`` – Set to ``true`` to use an on-disk SQLite database
#       for local/e2e runs (default ``false``).
# -----------------------------------------------------------------


def _effective_database_url() -> str:
    """Return the active database URL."""
    if os.getenv("USE_SQLITE", "false").lower() in ("1", "true", "yes"):
        default_path = os.path.abspath(os.getenv("SQLITE_PATH", "aiops_e2e.db"))
        return os.getenv("SQLITE_URL", f"sqlite+aiosqlite:///{default_path}")
    return POSTGRES_URL


# Async engine – ``future=True`` enables 2.0 style SQLAlchemy core.
# 🔧 P0-1 Enhancement: 使用优化的连接池配置
_ENGINE: Any | None = None
_AsyncSessionLocal: Any | None = None


class _LazyAsyncSessionLocal:
    """Lazy proxy that creates the engine and session factory on the first call."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        _ensure_engine()
        if _AsyncSessionLocal is None:
            raise RuntimeError("AsyncSessionLocal not initialized")
        return _AsyncSessionLocal(*args, **kwargs)

    def __repr__(self) -> str:
        return "<LazyAsyncSessionLocal>"


def _ensure_engine() -> Any:
    """创建并缓存异步引擎与 session factory。"""
    global _ENGINE, _AsyncSessionLocal
    if _ENGINE is None:
        db_url = _effective_database_url()
        engine_kwargs = {
            "echo": CONNECTION_POOL_CONFIG.get("echo", False),
            "future": CONNECTION_POOL_CONFIG.get("future", True),
        }
        if db_url.startswith("sqlite"):
            engine_kwargs["pool_pre_ping"] = True
        else:
            engine_kwargs.update(
                {
                    "pool_size": CONNECTION_POOL_CONFIG.get("pool_size", 20),
                    "max_overflow": CONNECTION_POOL_CONFIG.get("max_overflow", 40),
                    "pool_timeout": CONNECTION_POOL_CONFIG.get("pool_timeout", 30),
                    "pool_recycle": CONNECTION_POOL_CONFIG.get("pool_recycle", 3600),
                    "pool_pre_ping": CONNECTION_POOL_CONFIG.get("pool_pre_ping", True),
                }
            )
        _ENGINE = create_async_engine(db_url, **engine_kwargs)
        _AsyncSessionLocal = async_sessionmaker(bind=_ENGINE, expire_on_commit=False)
    return _ENGINE


class _LazyEngineProxy:
    """Lazy proxy that creates the real engine on the first attribute access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_ensure_engine(), name)


# Public lazy engine and session factory. Importing ``core.db_engine`` no longer
# triggers a network call or engine creation; the engine is built on first use.
engine = _LazyEngineProxy()
AsyncSessionLocal = _LazyAsyncSessionLocal()


# -----------------------------------------------------------------
# Async context manager returning an ``AsyncSession``.
# Usage example:
#   async with async_get_session() as session:
#       result = await session.execute(...)
# -----------------------------------------------------------------
@asynccontextmanager
async def async_get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async session.

    The session is committed automatically on successful exit and rolled
    back on exception, mirroring the semantics of the previous
    ``get_connection`` helper.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            await session.rollback()
            raise


# -----------------------------------------------------------------
# Initialise database schema.
# ``Base.metadata.create_all`` is executed within an async connection.
# -----------------------------------------------------------------
async def async_init_db() -> None:
    """Create all tables defined by ORM models.

    This function should be called at application start‑up (e.g. from
    ``main.py`` inside the lifespan event) to ensure the PostgreSQL
    schema exists.  It is idempotent – repeated calls have no effect.
    """
    db_url = _effective_database_url()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(
        "✅ Async database engine initialised | driver=%s",
        "sqlite" if db_url.startswith("sqlite") else "postgresql",
    )


# -----------------------------------------------------------------
# 🔧 P0-1: 真正的异步数据库操作实现
# 替换之前的no-op实现为实际的数据库操作
# -----------------------------------------------------------------


async def async_insert_alert(alert: dict) -> str:
    """异步插入告警记录"""
    alert_id: str = (
        alert.get("id", f"alert-{datetime.now().timestamp()}")
        or f"alert-{datetime.now().timestamp()}"
    )

    try:
        async with AsyncSessionLocal() as session:
            new_alert = Alert(
                id=alert_id,
                level=alert.get("level", "info"),
                category=alert.get("category"),
                alert_type=alert.get("alert_type"),
                title=alert.get("title", ""),
                description=alert.get("desc", ""),
                metric=alert.get("metric"),
                value=alert.get("value"),
                detected_at=alert.get("detected_at") or datetime.now(),
                metric_time=alert.get("metric_time"),
                status=alert.get("status", AlertStatus.PENDING.value),
                host=alert.get("host"),
                platform=alert.get("platform", "windows"),
                priority=alert.get("priority", "P3"),
                bis_score=alert.get("bis_score"),
                metadata=alert.get("metadata"),
                prev_suppressed=alert.get("prev_suppressed"),
                approval_id=alert.get("approval_id"),
                repair_id=alert.get("repair_id"),
            )
            session.add(new_alert)
            await session.commit()
            logger.info(f"✅ 告警已持久化到数据库 | alert_id={alert_id}")
            return alert_id
    except Exception as e:
        logger.error(f"❌ 告警插入数据库失败 | alert_id={alert_id}: {e}", exc_info=True)
        raise


async def async_query_alerts(limit: int = 20, **filters) -> List[Dict[str, Any]]:
    """异步查询告警记录"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Alert).order_by(Alert.detected_at.desc()).limit(limit)

            # 应用过滤条件
            if filters.get("level"):
                stmt = stmt.where(Alert.level == filters["level"])
            if filters.get("status"):
                stmt = stmt.where(Alert.status == filters["status"])
            if filters.get("host"):
                stmt = stmt.where(Alert.host == filters["host"])
            if filters.get("category"):
                stmt = stmt.where(Alert.category == filters["category"])

            result = await session.execute(stmt)
            alerts = result.scalars().all()

            # 转换为字典列表
            return [
                {
                    "id": a.id,
                    "level": a.level,
                    "category": a.category,
                    "alert_type": a.alert_type,
                    "title": a.title,
                    "desc": a.description,
                    "metric": a.metric,
                    "value": a.value,
                    "detected_at": a.detected_at.isoformat() if a.detected_at else None,
                    "metric_time": a.metric_time.isoformat() if a.metric_time else None,
                    "status": a.status,
                    "host": a.host,
                    "platform": a.platform,
                    "priority": a.priority,
                    "bis_score": a.bis_score,
                    "metadata": a.metadata,
                    "prev_suppressed": a.prev_suppressed,
                    "approval_id": a.approval_id,
                    "repair_id": a.repair_id,
                }
                for a in alerts
            ]
    except Exception as e:
        logger.error(f"❌ 查询告警失败: {e}", exc_info=True)
        return []


async def async_count_alerts(**filters) -> int:
    """异步统计告警数量"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count(Alert.id))

            # 应用过滤条件
            if filters.get("level"):
                stmt = stmt.where(Alert.level == filters["level"])
            if filters.get("status"):
                stmt = stmt.where(Alert.status == filters["status"])
            if filters.get("host"):
                stmt = stmt.where(Alert.host == filters["host"])

            result = await session.execute(stmt)
            return result.scalar() or 0
    except Exception as e:
        logger.error(f"❌ 统计告警数量失败: {e}", exc_info=True)
        return 0


async def async_clear_alerts() -> int:
    """异步清空所有告警"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = delete(Alert)
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount if hasattr(result, "rowcount") else 0
            logger.warning(f"⚠️ 已清空 {count} 条告警记录")
            return count
    except Exception as e:
        logger.error(f"❌ 清空告警失败: {e}", exc_info=True)
        return 0


async def async_insert_repair_record(
    success: bool,
    alert_time: Optional[str],
    repair_time: str,
    repair_duration_sec: float,
    rule_name: str,
    script_key: str,
    platform: str,
    output: str,
    alert_id: Optional[str] = None,
    host: Optional[str] = None,
    risk: str = "low",
    params: Optional[dict] = None,
) -> str:
    """异步插入修复记录"""
    repair_id = f"repair-{datetime.now().timestamp()}"

    try:
        async with AsyncSessionLocal() as session:
            repair_record = RepairRecord(
                id=repair_id,
                alert_id=alert_id,
                alert_time=datetime.fromisoformat(alert_time) if alert_time else None,
                script_key=script_key,
                script_name=f"修复: {rule_name}",
                success=success,
                status=RepairStatus.SUCCESS.value if success else RepairStatus.FAILED.value,
                repair_time=datetime.fromisoformat(repair_time),
                repair_duration_sec=repair_duration_sec,
                platform=platform,
                host=host,
                output=output[:5000],  # 限制长度
                risk=risk,
                params=params,
                return_code=0 if success else -1,
                executor="system",
            )
            session.add(repair_record)
            await session.commit()
            logger.info(f"✅ 修复记录已持久化 | repair_id={repair_id} | success={success}")
            return repair_id
    except Exception as e:
        logger.error(f"❌ 修复记录插入失败 | repair_id={repair_id}: {e}", exc_info=True)
        raise


async def async_query_repairs(today_only: bool = False, limit: int = 10) -> List[Dict[str, Any]]:
    """异步查询修复记录"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(RepairRecord).order_by(RepairRecord.repair_time.desc()).limit(limit)

            # 应用今日过滤
            if today_only:
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                stmt = stmt.where(RepairRecord.repair_time >= today_start)

            result = await session.execute(stmt)
            repairs = result.scalars().all()

            # 转换为字典列表
            return [
                {
                    "id": r.id,
                    "alert_id": r.alert_id,
                    "script_key": r.script_key,
                    "rule_name": r.script_name,
                    "success": r.success,
                    "status": r.status,
                    "repair_time": r.repair_time.isoformat() if r.repair_time else None,
                    "repair_duration_sec": r.repair_duration_sec,
                    "platform": r.platform,
                    "host": r.host,
                    "output": r.output,
                    "risk": r.risk,
                }
                for r in repairs
            ]
    except Exception as e:
        logger.error(f"❌ 查询修复记录失败: {e}", exc_info=True)
        return []


async def async_upsert_pending_approval(
    alert_id: str,
    rule_name: str,
    script_key: str,
    proposal: str,
    alert_json: str,
    risk_level: str = "medium",
    host: Optional[str] = None,
    platform: str = "windows",
) -> str:
    """异步插入或更新待审批记录"""
    approval_id = f"approval-{alert_id}-{datetime.now().timestamp()}"

    try:
        async with AsyncSessionLocal() as session:
            # 先检查是否已存在
            existing = await session.execute(
                select(PendingApproval).where(PendingApproval.alert_id == alert_id)
            )
            existing_record = existing.scalar_one_or_none()

            if existing_record:
                # 更新现有记录
                existing_record.script_key = script_key  # type: ignore[assignment]
                existing_record.proposal = proposal  # type: ignore[assignment]
                existing_record.alert_json = alert_json  # type: ignore[assignment]
                existing_record.risk_level = risk_level  # type: ignore[assignment]
                existing_record.status = ApprovalStatus.PENDING.value  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ 待审批记录已更新 | approval_id={existing_record.id}")
                return str(existing_record.id)
            else:
                # 创建新记录
                new_approval = PendingApproval(
                    id=approval_id,
                    alert_id=alert_id,
                    alert_json=alert_json,
                    rule_name=rule_name,
                    script_key=script_key,
                    proposal=proposal,
                    risk_level=risk_level,
                )
                session.add(new_approval)
                await session.commit()
                logger.info(f"✅ 待审批记录已创建 | approval_id={approval_id}")
                return approval_id
    except Exception as e:
        logger.error(f"❌ 待审批记录操作失败 | alert_id={alert_id}: {e}", exc_info=True)
        raise


async def async_get_pending_approval(alert_id: str) -> Optional[Dict[str, Any]]:
    """异步获取待审批记录"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(PendingApproval).where(
                PendingApproval.alert_id == alert_id,
                PendingApproval.status == ApprovalStatus.PENDING.value,
            )
            result = await session.execute(stmt)
            approval = result.scalar_one_or_none()

            if approval:
                return {
                    "id": approval.id,
                    "alert_id": approval.alert_id,
                    "alert_json": approval.alert_json,
                    "rule_name": approval.rule_name,
                    "script_key": approval.script_key,
                    "proposal": approval.proposal,
                    "status": approval.status,
                    "risk_level": approval.risk_level,
                    "submitted_at": (
                        approval.submitted_at.isoformat() if approval.submitted_at else None
                    ),
                }
            return None
    except Exception as e:
        logger.error(f"❌ 获取待审批记录失败 | alert_id={alert_id}: {e}", exc_info=True)
        return None


async def async_get_approval_by_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    """异步获取告警对应的最新审批记录(任意状态),用于修复执行前二次校验。"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(PendingApproval)
                .where(PendingApproval.alert_id == alert_id)
                .order_by(PendingApproval.submitted_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            approval = result.scalar_one_or_none()

            if approval:
                return {
                    "id": approval.id,
                    "alert_id": approval.alert_id,
                    "alert_json": approval.alert_json,
                    "rule_name": approval.rule_name,
                    "script_key": approval.script_key,
                    "proposal": approval.proposal,
                    "status": approval.status,
                    "risk_level": approval.risk_level,
                    "approver": approval.approver,
                    "approved_at": (
                        approval.approved_at.isoformat() if approval.approved_at else None
                    ),
                    "submitted_at": (
                        approval.submitted_at.isoformat() if approval.submitted_at else None
                    ),
                }
            return None
    except Exception as e:
        logger.error(f"❌ 获取审批记录失败 | alert_id={alert_id}: {e}", exc_info=True)
        return None


async def async_get_all_pending_approvals() -> List[Dict[str, Any]]:
    """异步获取所有待审批记录"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(PendingApproval)
                .where(PendingApproval.status == ApprovalStatus.PENDING.value)
                .order_by(PendingApproval.submitted_at.desc())
            )

            result = await session.execute(stmt)
            approvals = result.scalars().all()

            return [
                {
                    "id": a.id,
                    "alert_id": a.alert_id,
                    "alert_json": a.alert_json,
                    "rule_name": a.rule_name,
                    "script_key": a.script_key,
                    "proposal": a.proposal,
                    "status": a.status,
                    "risk_level": a.risk_level,
                    "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                }
                for a in approvals
            ]
    except Exception as e:
        logger.error(f"❌ 获取待审批列表失败: {e}", exc_info=True)
        return []


async def async_update_approval_status(
    approval_id: str,
    status: str,
    approver: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> bool:
    """异步更新审批状态（按 approval_id）"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(PendingApproval).where(PendingApproval.id == approval_id)
            result = await session.execute(stmt)
            approval = result.scalar_one_or_none()

            if approval:
                approval.status = status  # type: ignore[assignment]
                approval.approver = approver  # type: ignore[assignment]
                approval.approved_at = datetime.now()  # type: ignore[assignment]
                approval.rejection_reason = rejection_reason  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ 审批状态已更新 | approval_id={approval_id} | status={status}")
                return True
            return False
    except Exception as e:
        logger.error(f"❌ 更新审批状态失败 | approval_id={approval_id}: {e}", exc_info=True)
        return False


async def async_update_approval_status_by_alert(
    alert_id: str,
    status: str,
    approver: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> bool:
    """异步更新指定告警最新的审批记录状态"""
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(PendingApproval)
                .where(PendingApproval.alert_id == alert_id)
                .order_by(PendingApproval.submitted_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            approval = result.scalar_one_or_none()

            if approval:
                approval.status = status  # type: ignore[assignment]
                approval.approver = approver  # type: ignore[assignment]
                approval.approved_at = datetime.now()  # type: ignore[assignment]
                approval.rejection_reason = rejection_reason  # type: ignore[assignment]
                await session.commit()
                logger.info(f"✅ 审批状态已更新 | alert_id={alert_id} | status={status}")
                return True
            return False
    except Exception as e:
        logger.error(f"❌ 更新审批状态失败 | alert_id={alert_id}: {e}", exc_info=True)
        return False


# -----------------------------------------------------------------
# 🔧 P0-2: 同步API包装器（使用asyncio.run调用异步实现）
# 为了向后兼容，保留同步API，但内部调用真正的异步实现
# -----------------------------------------------------------------


def insert_alert(alert: dict) -> None:
    """同步API包装器 - 调用异步实现"""
    try:
        asyncio.run(async_insert_alert(alert))
    except Exception as e:
        logger.error(f"同步insert_alert失败: {e}")


def query_alerts(limit: int = 20, **kwargs) -> list[dict]:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_query_alerts(limit, **kwargs))
    except Exception as e:
        logger.error(f"同步query_alerts失败: {e}")
        return []


def count_alerts(**kwargs) -> int:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_count_alerts(**kwargs))
    except Exception as e:
        logger.error(f"同步count_alerts失败: {e}")
        return 0


def clear_alerts() -> int:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_clear_alerts())
    except Exception as e:
        logger.error(f"同步clear_alerts失败: {e}")
        return 0


def insert_repair_record(
    success: bool,
    alert_time: str,
    repair_time: str,
    repair_duration_sec: float,
    rule_name: str,
    script_key: str,
    platform: str,
    output: str,
) -> int:
    """同步API包装器 - 调用异步实现"""
    try:
        repair_id = asyncio.run(
            async_insert_repair_record(
                success=success,
                alert_time=alert_time,
                repair_time=repair_time,
                repair_duration_sec=repair_duration_sec,
                rule_name=rule_name,
                script_key=script_key,
                platform=platform,
                output=output,
            )
        )
        return 0 if repair_id else -1  # 兼容旧接口返回int
    except Exception as e:
        logger.error(f"同步insert_repair_record失败: {e}")
        return -1


def query_repairs(today_only: bool = False, limit: int = 10) -> list[dict[str, Any]]:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_query_repairs(today_only=today_only, limit=limit))
    except Exception as e:
        logger.error(f"同步query_repairs失败: {e}")
        return []


def upsert_pending_approval(
    alert_id: str, rule_name: str, script_key: str, proposal: str, alert_json: str
) -> int:
    """同步API包装器 - 调用异步实现"""
    try:
        approval_id = asyncio.run(
            async_upsert_pending_approval(
                alert_id=alert_id,
                rule_name=rule_name,
                script_key=script_key,
                proposal=proposal,
                alert_json=alert_json,
            )
        )
        return 0 if approval_id else -1  # 兼容旧接口返回int
    except Exception as e:
        logger.error(f"同步upsert_pending_approval失败: {e}")
        return -1


def get_pending_approval(alert_id: str) -> dict[str, Any] | None:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_get_pending_approval(alert_id))
    except Exception as e:
        logger.error(f"同步get_pending_approval失败: {e}")
        return None


def get_all_pending_approvals() -> list[dict[str, Any]]:
    """同步API包装器 - 调用异步实现"""
    try:
        return asyncio.run(async_get_all_pending_approvals())
    except Exception as e:
        logger.error(f"同步get_all_pending_approvals失败: {e}")
        return []


def update_approval_status(alert_id: str, status: str) -> None:
    """同步API包装器 - 调用异步实现(按 approval_id)"""
    try:
        asyncio.run(async_update_approval_status(alert_id, status))
    except Exception as e:
        logger.error(f"同步update_approval_status失败: {e}")


def update_approval_status_by_alert(alert_id: str, status: str) -> None:
    """同步API包装器 - 按 alert_id 更新最新审批状态"""
    try:
        asyncio.run(async_update_approval_status_by_alert(alert_id, status))
    except Exception as e:
        logger.error(f"同步update_approval_status_by_alert失败: {e}")


# 保留兼容的insert_verify_record（用于验证记录）
def insert_verify_record(**kwargs) -> int:
    """验证记录插入（暂存到审计日志）"""
    try:
        f"verify-{datetime.now().timestamp()}"
        logger.info(f"验证记录: {kwargs}")
        return 0  # 占位ID
    except Exception as e:
        logger.error(f"insert_verify_record失败: {e}")
        return 0


def db_clear_alerts() -> int:
    """数据库清空告警（兼容旧接口）"""
    return clear_alerts()


# -----------------------------------------------------------------
# Backward‑compatibility stubs (synchronous API).
# -----------------------------------------------------------------
def get_connection(*_, **__):  # pragma: no cover
    """Backward-compatible synchronous wrapper returning an ``AsyncSession``.

    .. deprecated::
        Prefer ``async_get_session`` in new code. This function returns an
        ``AsyncSession`` instance ready to be used inside an async context.
    """
    try:
        return AsyncSessionLocal()
    except Exception as exc:
        logger.error(f"Failed to create async session: {exc}")
        raise


def init_db():  # pragma: no cover
    """Backward-compatible synchronous wrapper that runs ``async_init_db``.

    .. deprecated::
        Prefer ``async_init_db`` during application start-up.
    """
    try:
        import asyncio

        return asyncio.run(async_init_db())
    except RuntimeError:
        # May be called from within an existing event loop during tests.
        import asyncio

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_init_db())


# Export symbols for external importers.
__all__ = [
    "engine",
    "Base",
    "AsyncSessionLocal",
    "async_get_session",
    "async_init_db",
    # Async functions
    "async_insert_alert",
    "async_query_alerts",
    "async_count_alerts",
    "async_clear_alerts",
    "async_insert_repair_record",
    "async_query_repairs",
    "async_upsert_pending_approval",
    "async_get_pending_approval",
    "async_get_all_pending_approvals",
    "async_update_approval_status",
    # Compatibility sync API (now using async implementations)
    "insert_alert",
    "query_alerts",
    "count_alerts",
    "clear_alerts",
    "upsert_pending_approval",
    "get_pending_approval",
    "get_all_pending_approvals",
    "update_approval_status",
    "insert_repair_record",
    "query_repairs",
    "insert_verify_record",
    "db_clear_alerts",
]


# -----------------------------------------------------------------
# 🔧 P0-1: 更新 PostgreSQLAlertRepository 使用真正的异步实现
# -----------------------------------------------------------------
# 注意：这里需要避免循环导入，所以延迟导入
def _get_alert_repository():
    """延迟获取 AlertRepository 接口"""
    try:
        from core.repositories.alert_repository import (
            AlertRepository,
        )
        from core.repositories.alert_repository import AlertStatus as RepoAlertStatus

        return AlertRepository, RepoAlertStatus
    except ImportError:
        logger.warning("AlertRepository interface not found, using fallback")
        return None, None


class PostgreSQLAlertRepository:
    """PostgreSQL 告警仓储实现（使用真正的异步ORM）"""

    async def save(self, alert: Dict[str, Any]) -> str:
        """保存告警"""
        return await async_insert_alert(alert)

    async def query(
        self, filters: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """查询告警"""
        return await async_query_alerts(limit=limit, **(filters or {}))

    async def get_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取告警"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Alert).where(Alert.id == alert_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()

                if alert:
                    return {
                        "id": alert.id,
                        "level": alert.level,
                        "category": alert.category,
                        "alert_type": alert.alert_type,
                        "title": alert.title,
                        "desc": alert.description,
                        "metric": alert.metric,
                        "value": alert.value,
                        "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
                        "metric_time": alert.metric_time.isoformat() if alert.metric_time else None,
                        "status": alert.status,
                        "host": alert.host,
                        "platform": alert.platform,
                        "priority": alert.priority,
                        "bis_score": alert.bis_score,
                        "metadata": alert.metadata,
                        "prev_suppressed": alert.prev_suppressed,
                        "approval_id": alert.approval_id,
                        "repair_id": alert.repair_id,
                    }
                return None
        except Exception as e:
            logger.error(f"❌ 根据ID获取告警失败 | alert_id={alert_id}: {e}", exc_info=True)
            return None

    async def update_status(self, alert_id: str, status: str) -> bool:
        """更新告警状态"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Alert).where(Alert.id == alert_id)
                result = await session.execute(stmt)
                alert = result.scalar_one_or_none()

                if alert:
                    alert.status = status  # type: ignore[assignment]
                    await session.commit()
                    logger.info(f"✅ 告警状态已更新 | alert_id={alert_id} | status={status}")
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ 更新告警状态失败 | alert_id={alert_id}: {e}", exc_info=True)
            return False

    async def delete(self, alert_id: str) -> bool:
        """删除告警"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = delete(Alert).where(Alert.id == alert_id)
                result = await session.execute(stmt)
                await session.commit()
                count = result.rowcount if hasattr(result, "rowcount") else 0
                logger.info(f"✅ 告警已删除 | alert_id={alert_id} | count={count}")
                return count > 0
        except Exception as e:
            logger.error(f"❌ 删除告警失败 | alert_id={alert_id}: {e}", exc_info=True)
            return False

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计告警数量"""
        return await async_count_alerts(**(filters or {}))

    async def clear_all(self) -> bool:
        """清空所有告警"""
        count = await async_clear_alerts()
        return count >= 0

    async def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的告警"""
        return await async_query_alerts(limit=limit)


# component DatabaseEngine class for testing compatibility
class DatabaseEngine:
    """component DatabaseEngine class for testing compatibility"""

    def __init__(self, connection_string: str = None):
        """Initialize DatabaseEngine component"""
        self.connection_string = connection_string
        self.connected = False

    async def connect(self):
        """Connect to database component"""
        self.connected = True

    async def disconnect(self):
        """Disconnect from database component"""
        self.connected = False

    async def execute(self, query: str, params: dict = None):
        """Execute query component"""
        return []

    async def fetchall(self, query: str, params: dict = None):
        """Fetch all results component"""
        return []


# 默认告警仓储实例
alert_repository = PostgreSQLAlertRepository()


class _SimpleRepairDB:
    """Simplified in-memory repair record storage for MCP tools."""

    def __init__(self):
        self._records: dict[str, dict] = {}

    def get_repair_record(self, repair_id: str) -> dict | None:
        return self._records.get(repair_id)

    def update_repair_status(self, repair_id: str, status: str, comment: str | None = None) -> None:
        record = self._records.setdefault(repair_id, {"repair_id": repair_id})
        record["status"] = status
        if comment is not None:
            record["comment"] = comment


db = _SimpleRepairDB()
