# -*- coding: utf-8 -*-
"""Core service logic for the data access microservice."""

from __future__ import annotations

import logging
import asyncio
import hashlib
import json
import re
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import DateTime, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .cache import CacheManager
from .metrics import MetricsCollector
from .retry import RetryEngine
from .schemas import (
    DbRouteRequest,
    DbRouteResponse,
    IndexSuggestion,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    OptimizeRequest,
    OptimizeResponse,
    PoolStatus,
    QueryRequest,
    QueryResponse,
    RouteRequest,
    RouteResponse,
    ShardRequest,
    ShardResponse,
    SlowQueryAlert,
    SlowQueryReport,
    TransactionRequest,
    TransactionResponse,
)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""


class Item(Base):
    """Example ORM entity for the data access service."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(255), default="")
    metadata_json: Mapped[str] = mapped_column(String(1024), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DataAccessService:
    """Data access service implementing ORM, pooling, routing, monitoring and optimization."""

    def __init__(
        self,
        database_url: str = "",
        redis_url: str = "",
        metrics: Optional[MetricsCollector] = None,
        retry_engine: Optional[RetryEngine] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.database_url = database_url or "sqlite+aiosqlite:///:memory:"
        engine_kwargs: dict[str, Any] = {"echo": False}
        if not self.database_url.startswith("sqlite"):
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10
        self.engine = create_async_engine(self.database_url, **engine_kwargs)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.metrics = metrics or MetricsCollector("data_access")
        self.retry_engine = retry_engine or RetryEngine("exponential_fast", self.metrics)
        self.cache = cache or CacheManager(redis_url, self.metrics)
        self._slow_queries: List[SlowQueryAlert] = []
        self._slow_threshold_ms = 100.0
        self._round_robin_counter = 0
        self._initialized = False

    async def initialize(self) -> None:
        """Create database tables if not already present."""
        if self._initialized:
            return
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._initialized = True
        self.metrics.set_index_size(0)

    async def reset(self) -> None:
        """Drop and recreate tables; useful for tests."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self._slow_queries.clear()
        self._round_robin_counter = 0
        self.metrics.set_index_size(0)
        await self.cache.clear()

    def _to_response(self, item: Item) -> ItemResponse:
        return ItemResponse(
            id=item.id,
            name=item.name,
            value=item.value,
            metadata=json.loads(item.metadata_json or "{}"),
            created_at=item.created_at,
        )

    # 36.2 ORM
    async def create_item(self, request: ItemCreate) -> ItemResponse:
        self.metrics.inc_request("create_item")
        async with self.session_factory() as session:
            item = Item(
                name=request.name,
                value=request.value,
                metadata_json=json.dumps(request.metadata),
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            self.metrics.inc_operation("orm_create")
            self.metrics.set_index_size(await self.count_items())
            return self._to_response(item)

    async def get_item(self, item_id: int) -> Optional[ItemResponse]:
        self.metrics.inc_request("get_item")
        cache_key = f"item:{item_id}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return ItemResponse.model_validate(cached)
        async with self.session_factory() as session:
            item = await session.get(Item, item_id)
            if item is None:
                return None
            response = self._to_response(item)
        await self.cache.set(cache_key, response.model_dump(), ttl=self.cache_ttl)
        return response

    async def update_item(self, item_id: int, request: ItemUpdate) -> Optional[ItemResponse]:
        self.metrics.inc_request("update_item")
        async with self.session_factory() as session:
            item = await session.get(Item, item_id)
            if item is None:
                return None
            if request.name is not None:
                item.name = request.name
            if request.value is not None:
                item.value = request.value
            if request.metadata is not None:
                item.metadata_json = json.dumps(request.metadata)
            await session.commit()
            await session.refresh(item)
            self.metrics.inc_operation("orm_update")
            response = self._to_response(item)
        await self.cache.set(f"item:{item_id}", response.model_dump(), ttl=self.cache_ttl)
        return response

    async def delete_item(self, item_id: int) -> bool:
        self.metrics.inc_request("delete_item")
        async with self.session_factory() as session:
            item = await session.get(Item, item_id)
            if item is None:
                return False
            await session.delete(item)
            await session.commit()
            self.metrics.inc_operation("orm_delete")
            self.metrics.set_index_size(await self.count_items())
        await self.cache.delete(f"item:{item_id}")
        return True

    async def list_items(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = "id",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        self.metrics.inc_request("list_items")
        async with self.session_factory() as session:
            stmt = select(Item)
            if filters:
                for column, value in filters.items():
                    col = getattr(Item, column, None)
                    if col is not None:
                        stmt = stmt.where(col == value)
            sort_col = getattr(Item, sort_by or "id", Item.id)
            if sort_order == "desc":
                stmt = stmt.order_by(sort_col.desc())
            else:
                stmt = stmt.order_by(sort_col.asc())
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await session.execute(count_stmt)).scalar() or 0
            offset = max(0, (page - 1) * page_size)
            stmt = stmt.offset(offset).limit(page_size)
            rows = (await session.execute(stmt)).scalars().all()
            items = [self._to_response(row) for row in rows]
            self.metrics.inc_operation("orm_list")
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def count_items(self) -> int:
        async with self.session_factory() as session:
            result = await session.execute(select(func.count()).select_from(Item))
            return result.scalar() or 0

    # 36.3 Query builder
    def build_query(self, request: QueryRequest) -> QueryResponse:
        self.metrics.inc_request("build_query")
        stmt = select(Item)
        for column, value in request.filters.items():
            col = getattr(Item, column, None)
            if col is not None:
                stmt = stmt.where(col == value)
        sort_col = getattr(Item, request.sort_by or "id", Item.id)
        if request.sort_order == "desc":
            stmt = stmt.order_by(sort_col.desc())
        else:
            stmt = stmt.order_by(sort_col.asc())
        offset = max(0, (request.page - 1) * request.page_size)
        stmt = stmt.offset(offset).limit(request.page_size)
        compiled = str(
            stmt.compile(dialect=self.engine.dialect, compile_kwargs={"literal_binds": True})
        )
        self.metrics.inc_operation("query_builder")
        return QueryResponse(
            table=request.table,
            compiled=compiled,
            filter_count=len(request.filters),
            sort_by=request.sort_by,
            page=request.page,
            page_size=request.page_size,
        )

    # 36.4 Transaction management
    async def execute_transaction(self, request: TransactionRequest) -> TransactionResponse:
        self.metrics.inc_request("execute_transaction")
        results: List[Any] = []
        session: Optional[AsyncSession] = None
        try:
            session = self.session_factory()
            async with session.begin():
                for operation in request.operations:
                    if operation.op == "create":
                        item = Item(
                            name=operation.data.get("name", ""),
                            value=operation.data.get("value", ""),
                            metadata_json=json.dumps(operation.data.get("metadata", {})),
                        )
                        session.add(item)
                        await session.flush()
                        results.append(self._to_response(item).model_dump())
                    elif operation.op == "update":
                        item_id = operation.data.get("id")
                        update_item = await session.get(Item, item_id)
                        if update_item is not None:
                            update_item.name = operation.data.get("name", update_item.name)
                            update_item.value = operation.data.get("value", update_item.value)
                            if "metadata" in operation.data:
                                update_item.metadata_json = json.dumps(operation.data["metadata"])
                            await session.flush()
                            results.append(self._to_response(update_item).model_dump())
                        else:
                            results.append(None)
                    elif operation.op == "delete":
                        item_id = operation.data.get("id")
                        delete_item = await session.get(Item, item_id)
                        if delete_item is not None:
                            await session.delete(delete_item)
                            results.append(True)
                        else:
                            results.append(False)
                    else:
                        raise ValueError(f"Unknown operation: {operation.op}")
            self.metrics.inc_operation("transaction_commit")
            self.metrics.set_index_size(await self.count_items())
            return TransactionResponse(success=True, results=results, rolled_back=False)
        except Exception as exc:
            logger.error(f"Transaction failed: {exc}")
            if session is not None:
                await session.rollback()
            self.metrics.inc_failure("execute_transaction", type(exc).__name__)
            if request.rollback_on_error:
                return TransactionResponse(
                    success=False,
                    results=results,
                    rolled_back=True,
                    error=str(exc),
                )
            raise

    # 36.5 Connection pool
    def pool_status(self) -> PoolStatus:
        self.metrics.inc_request("pool_status")
        pool: Any = self.engine.pool
        try:
            return PoolStatus(
                size=pool.size() if callable(getattr(pool, "size", None)) else 0,
                checked_in=pool.checked_in() if callable(getattr(pool, "checked_in", None)) else 0,
                checked_out=(
                    pool.checked_out() if callable(getattr(pool, "checked_out", None)) else 0
                ),
                overflow=pool.overflow() if callable(getattr(pool, "overflow", None)) else 0,
            )
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            return PoolStatus(size=0, checked_in=0, checked_out=0, overflow=0)

    # 36.6 Slow query monitor
    def set_slow_query_threshold(self, threshold_ms: float) -> None:
        self._slow_threshold_ms = threshold_ms

    def record_slow_query(self, query: str, elapsed_ms: float) -> None:
        if elapsed_ms >= self._slow_threshold_ms:
            alert = SlowQueryAlert(
                query=query,
                elapsed_ms=elapsed_ms,
                threshold_ms=self._slow_threshold_ms,
            )
            self._slow_queries.append(alert)
            self.metrics.inc_operation("slow_query_alert")
            logger.warning(f"Slow query detected: {query} ({elapsed_ms}ms)")

    def get_slow_queries(self) -> SlowQueryReport:
        return SlowQueryReport(
            alerts=self._slow_queries[-100:],
            total=len(self._slow_queries),
            threshold_ms=self._slow_threshold_ms,
        )

    # 36.7 Read-write separation
    def route_read(self, request: RouteRequest) -> RouteResponse:
        self.metrics.inc_request("route_read")
        target = self.database_url
        strategy = "primary"
        if request.hints.get("prefer_replica", True):
            replica = target.replace("?role=write", "?role=read")
            target = replica if "?role=" in target else f"{target}?role=read"
            strategy = "replica"
        return RouteResponse(target=target, strategy=strategy, operation="read")

    def route_write(self, request: RouteRequest) -> RouteResponse:
        self.metrics.inc_request("route_write")
        target = self.database_url.split("?")[0] if "?" in self.database_url else self.database_url
        return RouteResponse(target=f"{target}?role=write", strategy="primary", operation="write")

    # 36.8 Sharding support
    def route_shard(self, request: ShardRequest) -> ShardResponse:
        self.metrics.inc_request("route_shard")
        key = str(request.key)
        if request.strategy == "hash":
            index = (
                int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)
                % request.shard_count
            )
        elif request.strategy == "range":
            try:
                numeric = int(key)
                chunk = max(1, (2**31 - 1) // request.shard_count)
                index = min(numeric // chunk, request.shard_count - 1)
            except ValueError:
                index = (
                    int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)
                    % request.shard_count
                )
        else:
            index = (
                int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)
                % request.shard_count
            )
        self.metrics.inc_operation("shard_route")
        return ShardResponse(
            shard_index=index,
            shard_key=key,
            strategy=request.strategy,
            shard_count=request.shard_count,
        )

    # 36.9 Database routing
    def route_database(self, request: DbRouteRequest) -> DbRouteResponse:
        self.metrics.inc_request("route_database")
        targets = request.targets or ["primary", "replica1", "replica2"]
        if not targets:
            raise ValueError("No database targets provided")
        if request.strategy == "round_robin":
            target = targets[self._round_robin_counter % len(targets)]
            self._round_robin_counter += 1
        elif request.strategy == "weighted":
            weights = request.weights or {t: 1 for t in targets}
            population = []
            for t in targets:
                population.extend([t] * weights.get(t, 1))
            target = secrets.choice(population)
        elif request.strategy == "random":
            target = secrets.choice(targets)
        else:
            target = targets[self._round_robin_counter % len(targets)]
            self._round_robin_counter += 1
        self.metrics.inc_operation("db_route")
        return DbRouteResponse(target=target, strategy=request.strategy, database=request.database)

    # 36.10 Query optimization
    def optimize_query(self, request: OptimizeRequest) -> OptimizeResponse:
        self.metrics.inc_request("optimize_query")
        suggestions: List[IndexSuggestion] = []
        query_lower = request.query.lower()
        where_match = re.search(r"where\s+(.+?)(?:order|group|limit|$)", query_lower)
        if where_match:
            columns = re.findall(
                r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|>|<|!=|in)", where_match.group(1)
            )
            if columns:
                suggestions.append(
                    IndexSuggestion(
                        columns=list(set(columns)),
                        reason="Filtering columns detected in WHERE clause",
                    )
                )
        order_match = re.search(r"order\s+by\s+(.+?)(?:asc|desc|limit|$)", query_lower)
        if order_match:
            order_cols = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", order_match.group(1))
            if order_cols:
                suggestions.append(
                    IndexSuggestion(
                        columns=list(set(order_cols)),
                        reason="Ordering columns detected in ORDER BY clause",
                    )
                )
        if not suggestions and request.table:
            suggestions.append(
                IndexSuggestion(
                    columns=["id"],
                    reason="Default primary key index suggested",
                )
            )
        rewritten = request.query.strip()
        if "limit" not in query_lower:
            rewritten += " LIMIT 1000"
        self.metrics.inc_operation("query_optimization")
        return OptimizeResponse(
            suggestions=suggestions,
            estimated_improvement="~20-40% latency reduction for filtered queries",
            rewritten_query=rewritten,
        )

    # Utilities
    @property
    def cache_ttl(self) -> int:
        return 300

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.metrics.request_count,
            "cache_hits": self.metrics.cache_hits_count,
            "cache_misses": self.metrics.cache_misses_count,
            "operations": {},
            "index_size": 0,
        }

    def list_methods(self) -> List[str]:
        return [
            "create_item",
            "get_item",
            "update_item",
            "delete_item",
            "list_items",
            "build_query",
            "execute_transaction",
            "pool_status",
            "get_slow_queries",
            "route_read",
            "route_write",
            "route_shard",
            "route_database",
            "optimize_query",
            "get_stats",
        ]

    async def call(self, method: str, **kwargs: Any) -> Any:
        fn = getattr(self, method, None)
        if not fn:
            raise ValueError(f"Unknown method: {method}")
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        return fn(**kwargs)

    async def __aenter__(self) -> "DataAccessService":
        await self.initialize()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.engine.dispose()
