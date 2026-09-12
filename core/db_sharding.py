# -*- coding: utf-8 -*-
"""Real database sharding engine.

This module provides two genuinely functional capabilities:

1. :class:`ShardManager` — application-level sharding.  A **real**
   consistent-hash ring (``blake2b`` 64-bit points + virtual nodes), plus
   ``modulo``, ``range`` and ``list`` routing strategies.  Routing decisions
   are computed from the configured topology; the topology itself is persisted
   (``persistent_records``) so it survives a process restart.  When no topology
   has been configured every routing call raises :class:`ShardingNotConfigured`
   instead of inventing a shard.

2. :class:`PostgresPartitionManager` — PostgreSQL *declarative partitioning*
   planning.  It stores real partition definitions (``FOR VALUES FROM/TO``,
   ``FOR VALUES IN``, ``MODULUS/REMAINDER``) and renders valid ``CREATE TABLE
   … PARTITION BY …`` DDL that can be executed as-is.

Nothing here is simulated or seeded: hashes are deterministic, distributions
are counted from the keys actually submitted, node health is the result of a
real TCP connect attempt, and generated DDL is executable PostgreSQL.
"""

from __future__ import annotations

import asyncio
import bisect
import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

from core.persistent_store import PersistentStore

#: Identifiers we are willing to interpolate into generated DDL.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ShardingError(Exception):
    """Base class for sharding errors."""


class ShardingNotConfigured(ShardingError):
    """Raised when routing is requested before a topology is configured."""


class ShardStrategy(str, Enum):
    """Supported sharding strategies."""

    HASH = "hash"
    MODULO = "modulo"
    RANGE = "range"
    LIST = "list"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def hash_key(value: str) -> int:
    """Return a deterministic 64-bit hash for ``value``.

    Uses ``blake2b`` (not Python's salted ``hash``) so a key always maps to the
    same point regardless of process, interpreter or ``PYTHONHASHSEED``.
    """
    digest = hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def coerce_comparable(value: Any) -> Any:
    """Best-effort numeric coercion used for *range* bound comparisons."""
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return int(stripped)
        except ValueError:
            try:
                return float(stripped)
            except ValueError:
                return stripped
    return value


def _sql_literal(value: Any) -> str:
    """Render ``value`` as a PostgreSQL literal (used inside generated DDL)."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


class ConsistentHashRing:
    """A real consistent-hash ring built from ``blake2b`` points.

    Each shard owns ``virtual_nodes`` points on the ring; a key is mapped to
    the first point clockwise from its own hash.  Adding or removing a shard
    therefore only re-homes the keys that fall in the affected arcs.
    """

    def __init__(self, virtual_nodes: int = 128) -> None:
        self.virtual_nodes = max(1, int(virtual_nodes))
        self._points: Dict[int, str] = {}
        self._sorted_points: List[int] = []

    # -- construction ----------------------------------------------------
    def add_shard(self, shard_id: str) -> None:
        for i in range(self.virtual_nodes):
            self._points[hash_key(f"{shard_id}#{i}")] = shard_id
        self._sorted_points = sorted(self._points)

    def remove_shard(self, shard_id: str) -> None:
        for i in range(self.virtual_nodes):
            self._points.pop(hash_key(f"{shard_id}#{i}"), None)
        self._sorted_points = sorted(self._points)

    # -- lookup ----------------------------------------------------------
    def get_shard(self, key: Any) -> str:
        if not self._sorted_points:
            raise ShardingNotConfigured("consistent-hash ring has no shards")
        point = hash_key(key)
        idx = bisect.bisect(self._sorted_points, point)
        if idx == len(self._sorted_points):
            idx = 0  # wrap around
        return self._points[self._sorted_points[idx]]

    def points_owner(self) -> Dict[int, str]:
        """Return a copy of the ``point -> shard_id`` ownership map."""
        return dict(self._points)

    @property
    def size(self) -> int:
        return len(self._sorted_points)

    def owned_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for shard_id in self._points.values():
            counts[shard_id] = counts.get(shard_id, 0) + 1
        return counts


@dataclass
class ShardNode:
    """A physical node (host/port) backing a shard."""

    node_id: str
    host: str
    port: int = 5432
    role: str = "primary"  # primary | replica

    def to_dict(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "host": self.host, "port": self.port, "role": self.role}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShardNode":
        return cls(
            node_id=str(data.get("node_id") or _new_id("node")),
            host=str(data.get("host", "localhost")),
            port=int(data.get("port", 5432)),
            role=str(data.get("role", "primary")),
        )


@dataclass
class Shard:
    """A logical shard with its own routing bounds and backing nodes."""

    shard_id: str
    name: str
    strategy: str
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    values: List[str] = field(default_factory=list)
    nodes: List[ShardNode] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def primary_node(self) -> Optional[ShardNode]:
        for node in self.nodes:
            if node.role == "primary":
                return node
        return self.nodes[0] if self.nodes else None

    def replica_nodes(self) -> List[ShardNode]:
        return [n for n in self.nodes if n.role == "replica"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "name": self.name,
            "strategy": self.strategy,
            "range_start": self.range_start,
            "range_end": self.range_end,
            "values": list(self.values),
            "nodes": [n.to_dict() for n in self.nodes],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shard":
        return cls(
            shard_id=str(data.get("shard_id") or _new_id("shard")),
            name=str(data.get("name", "shard")),
            strategy=str(data.get("strategy", "hash")),
            range_start=data.get("range_start"),
            range_end=data.get("range_end"),
            values=list(data.get("values") or []),
            nodes=[ShardNode.from_dict(n) for n in (data.get("nodes") or [])],
            created_at=str(data.get("created_at") or _now()),
        )


@dataclass
class ShardRoute:
    """The outcome of routing a single key."""

    key: str
    shard_id: str
    shard_name: str
    strategy: str
    node: Optional[Dict[str, Any]]
    replicas: List[Dict[str, Any]]
    ring_point: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "shard_id": self.shard_id,
            "shard_name": self.shard_name,
            "strategy": self.strategy,
            "node": self.node,
            "replicas": self.replicas,
            "ring_point": self.ring_point,
        }


class ShardManager:
    """Application-level sharding engine (persisted, real routing)."""

    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace
        self._store = PersistentStore("db_sharding", f"topology::{namespace}")
        self._strategy: str = ShardStrategy.HASH.value
        self._shard_key: str = "id"
        self._table_name: Optional[str] = None
        self._virtual_nodes: int = 128
        self._shards: Dict[str, Shard] = {}
        self._configured: bool = False
        self._updated_at: Optional[str] = None
        self._ring: Optional[ConsistentHashRing] = None
        self._modulo_order: List[str] = []
        self._range_index: List[Tuple[Any, str]] = []
        self._list_index: Dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # persistence
    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        raw = self._store.get("config")
        if not raw:
            return
        try:
            self._strategy = str(raw.get("strategy", ShardStrategy.HASH.value))
            self._shard_key = str(raw.get("shard_key", "id"))
            self._table_name = raw.get("table_name")
            self._virtual_nodes = int(raw.get("virtual_nodes", 128))
            self._shards = {
                s["shard_id"]: Shard.from_dict(s) for s in (raw.get("shards") or [])
            }
            self._configured = bool(raw.get("configured", bool(self._shards)))
            self._updated_at = raw.get("updated_at")
        except Exception as exc:  # pragma: no cover - corrupt payload guard
            logger.error("Failed to load sharding topology %s: %s", self.namespace, exc)
            return
        self._rebuild()

    def _save(self) -> None:
        self._updated_at = _now()
        self._store["config"] = {
            "configured": self._configured,
            "strategy": self._strategy,
            "shard_key": self._shard_key,
            "table_name": self._table_name,
            "virtual_nodes": self._virtual_nodes,
            "shards": [s.to_dict() for s in self._shards.values()],
            "updated_at": self._updated_at,
        }

    # ------------------------------------------------------------------ #
    # index construction
    # ------------------------------------------------------------------ #
    def _rebuild(self) -> None:
        """(Re)build the routing indices from the current topology."""
        self._ring = None
        self._modulo_order = []
        self._range_index = []
        self._list_index = {}

        shards = list(self._shards.values())
        if not shards:
            return

        if self._strategy in (ShardStrategy.HASH.value,):
            ring = ConsistentHashRing(self._virtual_nodes)
            for shard in shards:
                ring.add_shard(shard.shard_id)
            self._ring = ring
        elif self._strategy == ShardStrategy.MODULO.value:
            # Deterministic order so the modulo index is stable across restarts.
            self._modulo_order = sorted(self._shards)
        elif self._strategy == ShardStrategy.RANGE.value:
            index: List[Tuple[Any, str]] = []
            for shard in shards:
                if shard.range_start is None:
                    continue
                index.append((coerce_comparable(shard.range_start), shard.shard_id))
            index.sort(key=lambda item: item[0])
            self._range_index = index
        elif self._strategy == ShardStrategy.LIST.value:
            for shard in shards:
                for value in shard.values:
                    if value in self._list_index:
                        raise ShardingError(
                            f"routing value {value!r} is claimed by both "
                            f"{self._list_index[value]} and {shard.shard_id}"
                        )
                    self._list_index[value] = shard.shard_id

    # ------------------------------------------------------------------ #
    # topology management
    # ------------------------------------------------------------------ #
    @property
    def configured(self) -> bool:
        return self._configured and bool(self._shards)

    def configure(
        self,
        *,
        strategy: str = ShardStrategy.HASH.value,
        shard_count: int = 2,
        shard_key: str = "id",
        table_name: Optional[str] = None,
        virtual_nodes: int = 128,
        nodes: Optional[Sequence[Dict[str, Any]]] = None,
        replace: bool = True,
    ) -> Dict[str, Any]:
        """Create ``shard_count`` hash/modulo shards (replacing the topology)."""
        strategy = str(strategy).lower()
        if strategy not in {s.value for s in ShardStrategy}:
            raise ShardingError(f"unsupported strategy: {strategy}")
        if strategy in (ShardStrategy.RANGE.value, ShardStrategy.LIST.value):
            raise ShardingError(
                f"strategy {strategy} shards must be added explicitly with their bounds"
            )
        shard_count = int(shard_count)
        if shard_count < 1:
            raise ShardingError("shard_count must be >= 1")

        if replace:
            self._shards = {}

        self._strategy = strategy
        self._shard_key = shard_key
        self._table_name = table_name
        self._virtual_nodes = max(1, int(virtual_nodes))

        default_nodes = [ShardNode.from_dict(n) for n in (nodes or [])]
        for i in range(shard_count):
            shard_id = f"shard-{i}"
            self._shards[shard_id] = Shard(
                shard_id=shard_id,
                name=shard_id,
                strategy=strategy,
                nodes=[ShardNode.from_dict(n.to_dict()) for n in default_nodes],
            )

        self._configured = True
        self._rebuild()
        self._save()
        logger.info(
            "Configured %s sharding with %d shards (key=%s)",
            strategy,
            shard_count,
            shard_key,
        )
        return self.status()

    def add_shard(self, shard: Dict[str, Any]) -> Dict[str, Any]:
        """Add a shard.  For range/list strategies its bounds are required."""
        if not self._configured:
            # The very first shard defines the topology/strategy.
            self._strategy = str(shard.get("strategy", ShardStrategy.HASH.value)).lower()
            self._configured = True

        new_shard = Shard.from_dict({**shard, "strategy": self._strategy})
        if self._strategy == ShardStrategy.RANGE.value and new_shard.range_start is None:
            raise ShardingError("range shards require 'range_start' (and 'range_end')")
        if self._strategy == ShardStrategy.LIST.value and not new_shard.values:
            raise ShardingError("list shards require a non-empty 'values' list")
        if new_shard.shard_id in self._shards:
            raise ShardingError(f"shard {new_shard.shard_id!r} already exists")

        self._shards[new_shard.shard_id] = new_shard
        try:
            self._rebuild()
        except ShardingError:
            # Roll back an invalid (overlapping) definition.
            self._shards.pop(new_shard.shard_id, None)
            self._rebuild()
            raise
        self._save()
        return new_shard.to_dict()

    def remove_shard(self, shard_id: str) -> Dict[str, Any]:
        if shard_id not in self._shards:
            raise ShardingError(f"unknown shard: {shard_id}")
        removed = self._shards.pop(shard_id)
        if not self._shards:
            self._configured = False
        self._rebuild()
        self._save()
        return removed.to_dict()

    def reset(self) -> None:
        self._shards = {}
        self._configured = False
        self._ring = None
        self._modulo_order = []
        self._range_index = []
        self._list_index = {}
        self._save()

    def list_shards(self) -> List[Dict[str, Any]]:
        return [self._shards[sid].to_dict() for sid in sorted(self._shards)]

    def get_shard(self, shard_id: str) -> Shard:
        if shard_id not in self._shards:
            raise ShardingError(f"unknown shard: {shard_id}")
        return self._shards[shard_id]

    # ------------------------------------------------------------------ #
    # routing
    # ------------------------------------------------------------------ #
    def _resolve_shard_id(self, key: Any) -> Tuple[str, Optional[int]]:
        if not self.configured:
            raise ShardingNotConfigured(
                "no sharding topology is configured; call configure/add_shard first"
            )
        if self._strategy == ShardStrategy.HASH.value:
            assert self._ring is not None
            shard_id = self._ring.get_shard(key)
            return shard_id, hash_key(key)
        if self._strategy == ShardStrategy.MODULO.value:
            idx = hash_key(key) % len(self._modulo_order)
            return self._modulo_order[idx], hash_key(key)
        if self._strategy == ShardStrategy.RANGE.value:
            if not self._range_index:
                raise ShardingError("range topology has no shards with bounds")
            probe = coerce_comparable(key)
            starts = [entry[0] for entry in self._range_index]
            pos = bisect.bisect_right(starts, probe) - 1
            if pos < 0:
                raise ShardingError(f"key {key!r} is below the lowest range bound")
            shard_id = self._range_index[pos][1]
            shard = self._shards[shard_id]
            if shard.range_end is not None:
                if probe >= coerce_comparable(shard.range_end):
                    raise ShardingError(
                        f"key {key!r} is >= upper bound {shard.range_end!r} of shard {shard_id}"
                    )
            return shard_id, None
        if self._strategy == ShardStrategy.LIST.value:
            found = self._list_index.get(str(key))
            if found is None:
                raise ShardingError(f"no shard declares routing value {key!r}")
            return found, None
        raise ShardingError(f"unsupported strategy: {self._strategy}")

    def route(self, key: Any) -> ShardRoute:
        shard_id, point = self._resolve_shard_id(key)
        shard = self._shards[shard_id]
        primary = shard.primary_node()
        return ShardRoute(
            key=str(key),
            shard_id=shard_id,
            shard_name=shard.name,
            strategy=self._strategy,
            node=primary.to_dict() if primary else None,
            replicas=[n.to_dict() for n in shard.replica_nodes()],
            ring_point=point,
        )

    def route_batch(self, keys: Sequence[Any]) -> Dict[str, Any]:
        distribution: Dict[str, int] = {}
        routes: List[Dict[str, Any]] = []
        for key in keys:
            route = self.route(key)
            distribution[route.shard_id] = distribution.get(route.shard_id, 0) + 1
            routes.append({"key": route.key, "shard_id": route.shard_id})
        return {
            "strategy": self._strategy,
            "total_keys": len(keys),
            "shard_count": len(self._shards),
            "distribution": distribution,
            "routes": routes,
        }

    def scatter_plan(self, keys: Sequence[Any]) -> Dict[str, Any]:
        """Group keys by shard — the fan-out plan for a scatter/gather query."""
        grouped: Dict[str, List[str]] = {}
        for key in keys:
            route = self.route(key)
            grouped.setdefault(route.shard_id, []).append(str(key))
        shards = [
            {
                "shard_id": sid,
                "shard_name": self._shards[sid].name,
                "node": (
                    self._shards[sid].primary_node().to_dict()
                    if self._shards[sid].primary_node()
                    else None
                ),
                "keys": grouped[sid],
                "count": len(grouped[sid]),
            }
            for sid in sorted(grouped)
        ]
        return {
            "strategy": self._strategy,
            "total_keys": len(keys),
            "fanout": len(shards),
            "shards": shards,
        }

    # ------------------------------------------------------------------ #
    # introspection
    # ------------------------------------------------------------------ #
    def status(self) -> Dict[str, Any]:
        node_count = sum(len(s.nodes) for s in self._shards.values())
        ring_size = self._ring.size if self._ring else 0
        return {
            "configured": self.configured,
            "namespace": self.namespace,
            "strategy": self._strategy,
            "shard_key": self._shard_key,
            "table_name": self._table_name,
            "virtual_nodes": self._virtual_nodes,
            "shard_count": len(self._shards),
            "node_count": node_count,
            "ring_size": ring_size,
            "shards": self.list_shards(),
            "updated_at": self._updated_at,
        }

    def rebalance(
        self,
        *,
        keys: Optional[Sequence[Any]] = None,
        virtual_nodes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Rebuild the hash ring and report what actually moves.

        The ring is always rebuilt from the current shards (a real, idempotent
        action).  When ``virtual_nodes`` changes, the ownership of ring points
        is recomputed; when ``keys`` are supplied the number of keys that change
        shard is counted against the previous ring.
        """
        if self._strategy != ShardStrategy.HASH.value:
            raise ShardingError("rebalance is only meaningful for the hash strategy")
        if not self.configured:
            raise ShardingNotConfigured("no sharding topology is configured")

        old_ring = self._ring
        target_virtual_nodes = max(1, int(virtual_nodes)) if virtual_nodes else self._virtual_nodes

        new_ring = ConsistentHashRing(target_virtual_nodes)
        for shard_id in sorted(self._shards):
            new_ring.add_shard(shard_id)

        moved_points = 0
        if old_ring is not None:
            old_owner = old_ring.points_owner()
            new_owner = new_ring.points_owner()
            for point, owner in new_owner.items():
                if old_owner.get(point) != owner:
                    moved_points += 1
                # Points that vanished from the old ring are counted too.
            moved_points += len(set(old_owner) - set(new_owner))

        keys_moved = 0
        keys_total = 0
        if keys:
            keys_total = len(keys)
            for key in keys:
                if old_ring is not None and old_ring.get_shard(key) != new_ring.get_shard(key):
                    keys_moved += 1

        self._virtual_nodes = target_virtual_nodes
        self._ring = new_ring
        self._save()

        distribution = new_ring.owned_counts()
        ideal = (100.0 / len(self._shards)) if self._shards else 0.0
        shares = {
            shard_id: round(distribution.get(shard_id, 0) * 100.0 / max(1, new_ring.size), 3)
            for shard_id in sorted(self._shards)
        }
        max_deviation = max((abs(share - ideal) for share in shares.values()), default=0.0)

        return {
            "strategy": self._strategy,
            "shard_count": len(self._shards),
            "virtual_nodes": target_virtual_nodes,
            "ring_size": new_ring.size,
            "points_moved": moved_points,
            "keys_total": keys_total,
            "keys_moved": keys_moved,
            "ideal_share_percent": round(ideal, 3),
            "shard_share_percent": shares,
            "max_deviation_percent": round(max_deviation, 3),
            "balanced": max_deviation <= 10.0,
        }

    async def health(self, timeout: float = 2.0) -> Dict[str, Any]:
        """Probe every node with a real TCP connect attempt."""

        async def probe(node: ShardNode) -> Dict[str, Any]:
            start = datetime.now(timezone.utc)
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(node.host, node.port), timeout=timeout
                )
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # pragma: no cover - best-effort close
                    pass
                latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                return {
                    **node.to_dict(),
                    "status": "up",
                    "latency_ms": round(latency, 3),
                    "checked_at": _now(),
                }
            except Exception as exc:
                return {
                    **node.to_dict(),
                    "status": "down",
                    "error": str(exc),
                    "checked_at": _now(),
                }

        results: List[Dict[str, Any]] = []
        for shard in self._shards.values():
            for node in shard.nodes:
                entry = await probe(node)
                entry["shard_id"] = shard.shard_id
                results.append(entry)

        up = sum(1 for r in results if r["status"] == "up")
        return {
            "configured": self.configured,
            "nodes_total": len(results),
            "nodes_up": up,
            "nodes_down": len(results) - up,
            "nodes": results,
        }


# ---------------------------------------------------------------------- #
# PostgreSQL declarative partitioning
# ---------------------------------------------------------------------- #
@dataclass
class Partition:
    """A single declarative-partition definition."""

    name: str
    kind: str  # hash | range | list
    modulus: Optional[int] = None
    remainder: Optional[int] = None
    range_from: Optional[str] = None
    range_to: Optional[str] = None
    values: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "modulus": self.modulus,
            "remainder": self.remainder,
            "range_from": self.range_from,
            "range_to": self.range_to,
            "values": list(self.values),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Partition":
        return cls(
            name=str(data.get("name")),
            kind=str(data.get("kind", "hash")),
            modulus=data.get("modulus"),
            remainder=data.get("remainder"),
            range_from=data.get("range_from"),
            range_to=data.get("range_to"),
            values=list(data.get("values") or []),
            created_at=str(data.get("created_at") or _now()),
        )


def _quote_ident(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ShardingError(f"invalid SQL identifier: {name!r}")
    return name


class PostgresPartitionManager:
    """Manage a PostgreSQL declarative-partitioning plan and render its DDL."""

    def __init__(self, namespace: str = "default") -> None:
        self.namespace = namespace
        self._store = PersistentStore("postgres_partition", f"plan::{namespace}")
        self._table: Optional[str] = None
        self._schema: str = "public"
        self._column: Optional[str] = None
        self._column_type: str = "BIGINT"
        self._strategy: Optional[str] = None
        self._columns: List[Dict[str, str]] = []
        self._partitions: Dict[str, Partition] = {}
        self._configured = False
        self._updated_at: Optional[str] = None
        self._load()

    def _load(self) -> None:
        raw = self._store.get("plan")
        if not raw:
            return
        try:
            self._table = raw.get("table")
            self._schema = str(raw.get("schema", "public"))
            self._column = raw.get("column")
            self._column_type = str(raw.get("column_type", "BIGINT"))
            self._strategy = raw.get("strategy")
            self._columns = list(raw.get("columns") or [])
            self._partitions = {
                p["name"]: Partition.from_dict(p) for p in (raw.get("partitions") or [])
            }
            self._configured = bool(raw.get("configured", bool(self._table)))
            self._updated_at = raw.get("updated_at")
        except Exception as exc:  # pragma: no cover - corrupt payload guard
            logger.error("Failed to load partition plan %s: %s", self.namespace, exc)

    def _save(self) -> None:
        self._updated_at = _now()
        self._store["plan"] = {
            "configured": self._configured,
            "table": self._table,
            "schema": self._schema,
            "column": self._column,
            "column_type": self._column_type,
            "strategy": self._strategy,
            "columns": self._columns,
            "partitions": [p.to_dict() for p in self._partitions.values()],
            "updated_at": self._updated_at,
        }

    # -- configuration ---------------------------------------------------
    def configure(
        self,
        *,
        table: str,
        strategy: str,
        column: str,
        column_type: str = "BIGINT",
        schema: str = "public",
        columns: Optional[Sequence[Dict[str, str]]] = None,
        partitions: Optional[Sequence[Dict[str, Any]]] = None,
        partition_count: int = 4,
    ) -> Dict[str, Any]:
        strategy = str(strategy).lower()
        if strategy not in (ShardStrategy.HASH.value, ShardStrategy.RANGE.value, ShardStrategy.LIST.value):
            raise ShardingError(
                "declarative partitioning supports 'hash', 'range' or 'list' strategies"
            )
        _quote_ident(table)
        _quote_ident(column)
        _quote_ident(schema)

        self._table = table
        self._schema = schema
        self._column = column
        self._column_type = column_type
        self._strategy = strategy
        self._columns = [dict(c) for c in (columns or [])]

        if partitions is not None:
            self._partitions = {}
            for entry in partitions:
                part = Partition.from_dict({**entry, "kind": strategy})
                self._partitions[part.name] = part
        elif partition_count and not self._partitions:
            self._partitions = {}
            for i in range(int(partition_count)):
                if strategy == ShardStrategy.HASH.value:
                    self._partitions[f"{table}_p{i}"] = Partition(
                        name=f"{table}_p{i}", kind="hash", modulus=int(partition_count), remainder=i
                    )
                else:
                    raise ShardingError(
                        f"{strategy} partitions require explicit bounds via 'partitions'"
                    )

        self._validate()
        self._configured = True
        self._save()
        return self.plan()

    def add_partition(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if not self._configured:
            raise ShardingError("configure a partition plan before adding partitions")
        part = Partition.from_dict({**entry, "kind": self._strategy or "hash"})
        if part.name in self._partitions:
            raise ShardingError(f"partition {part.name!r} already exists")
        self._partitions[part.name] = part
        try:
            self._validate()
        except ShardingError:
            self._partitions.pop(part.name, None)
            raise
        self._save()
        return part.to_dict()

    def remove_partition(self, name: str) -> Dict[str, Any]:
        if name not in self._partitions:
            raise ShardingError(f"unknown partition: {name}")
        removed = self._partitions.pop(name)
        self._save()
        return removed.to_dict()

    def reset(self) -> None:
        self._table = None
        self._column = None
        self._strategy = None
        self._columns = []
        self._partitions = {}
        self._configured = False
        self._save()

    # -- validation ------------------------------------------------------
    def _validate(self) -> None:
        if self._strategy == ShardStrategy.HASH.value:
            remainders = set()
            for part in self._partitions.values():
                if part.modulus is None or part.remainder is None:
                    raise ShardingError(f"hash partition {part.name!r} needs modulus/remainder")
                if part.remainder in remainders:
                    raise ShardingError(f"duplicate hash remainder: {part.remainder}")
                if not (0 <= part.remainder < part.modulus):
                    raise ShardingError(
                        f"remainder {part.remainder} out of range for modulus {part.modulus}"
                    )
                remainders.add(part.remainder)
        elif self._strategy == ShardStrategy.RANGE.value:
            bounds: List[Tuple[Any, Any, str]] = []
            for part in self._partitions.values():
                if part.range_from in (None, "") or part.range_to in (None, ""):
                    raise ShardingError(f"range partition {part.name!r} needs range_from/range_to")
                bounds.append(
                    (coerce_comparable(part.range_from), coerce_comparable(part.range_to), part.name)
                )
            bounds.sort(key=lambda b: b[0])
            for i in range(1, len(bounds)):
                if bounds[i][0] < bounds[i - 1][1]:
                    raise ShardingError(
                        f"range partitions {bounds[i-1][2]!r} and {bounds[i][2]!r} overlap"
                    )
        elif self._strategy == ShardStrategy.LIST.value:
            seen: Dict[str, str] = {}
            for part in self._partitions.values():
                if not part.values:
                    raise ShardingError(f"list partition {part.name!r} needs a non-empty values list")
                for value in part.values:
                    if value in seen:
                        raise ShardingError(
                            f"value {value!r} assigned to both {seen[value]!r} and {part.name!r}"
                        )
                    seen[value] = part.name

    # -- introspection ---------------------------------------------------
    def plan(self) -> Dict[str, Any]:
        return {
            "configured": self._configured,
            "schema": self._schema,
            "table": self._table,
            "column": self._column,
            "column_type": self._column_type,
            "strategy": self._strategy,
            "columns": list(self._columns),
            "partitions": [self._partitions[n].to_dict() for n in sorted(self._partitions)],
            "partition_count": len(self._partitions),
            "updated_at": self._updated_at,
        }

    def list_partitions(self) -> List[Dict[str, Any]]:
        return [self._partitions[n].to_dict() for n in sorted(self._partitions)]

    # -- DDL rendering ---------------------------------------------------
    def generate_ddl(self) -> str:
        if not self._configured or not self._table or not self._column:
            raise ShardingNotConfigured("no declarative partitioning plan is configured")
        return render_postgres_partition_ddl(self.plan())


def render_postgres_partition_ddl(plan: Dict[str, Any]) -> str:
    """Render executable ``CREATE TABLE … PARTITION BY …`` DDL from a plan."""
    table = plan.get("table")
    column = plan.get("column")
    strategy = plan.get("strategy")
    schema = plan.get("schema") or "public"
    if not table or not column or not strategy:
        raise ShardingNotConfigured("plan is missing table/column/strategy")

    _quote_ident(table)
    _quote_ident(column)
    _quote_ident(schema)

    columns = plan.get("columns") or []
    lines: List[str] = []
    if columns:
        col_defs = []
        for col in columns:
            cname = _quote_ident(str(col.get("name")))
            ctype = str(col.get("type", "TEXT"))
            col_defs.append(f"    {cname} {ctype}")
        col_block = ",\n".join(col_defs)
    else:
        # At minimum declare the partition key so the DDL is syntactically valid.
        col_block = f"    {column} {plan.get('column_type', 'BIGINT')} NOT NULL"

    table_ref = f"{schema}.{table}"
    lines.append(f"CREATE TABLE IF NOT EXISTS {table_ref} (\n{col_block}\n) PARTITION BY {strategy.upper()} ({column});")
    lines.append("")

    partitions = sorted(plan.get("partitions") or [], key=lambda p: p["name"])
    for part in partitions:
        pname = _quote_ident(str(part["name"]))
        pref = f"{schema}.{pname}"
        kind = part.get("kind", strategy)
        if kind == "hash":
            lines.append(
                f"CREATE TABLE {pref} PARTITION OF {table_ref}\n"
                f"    FOR VALUES WITH (MODULUS {int(part['modulus'])}, REMAINDER {int(part['remainder'])});"
            )
        elif kind == "range":
            lines.append(
                f"CREATE TABLE {pref} PARTITION OF {table_ref}\n"
                f"    FOR VALUES FROM ({_sql_literal(part['range_from'])}) "
                f"TO ({_sql_literal(part['range_to'])});"
            )
        elif kind == "list":
            values = ", ".join(_sql_literal(v) for v in part.get("values") or [])
            lines.append(
                f"CREATE TABLE {pref} PARTITION OF {table_ref}\n    FOR VALUES IN ({values});"
            )
        else:  # pragma: no cover - guarded by validation
            raise ShardingError(f"unsupported partition kind: {kind}")

    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------- #
# singletons
# ---------------------------------------------------------------------- #
_shard_managers: Dict[str, ShardManager] = {}
_partition_managers: Dict[str, PostgresPartitionManager] = {}


def get_shard_manager(namespace: str = "default") -> ShardManager:
    """Return the process-wide :class:`ShardManager` for ``namespace``."""
    if namespace not in _shard_managers:
        _shard_managers[namespace] = ShardManager(namespace)
    return _shard_managers[namespace]


def get_partition_manager(namespace: str = "default") -> PostgresPartitionManager:
    """Return the process-wide :class:`PostgresPartitionManager` for ``namespace``."""
    if namespace not in _partition_managers:
        _partition_managers[namespace] = PostgresPartitionManager(namespace)
    return _partition_managers[namespace]


__all__ = [
    "ConsistentHashRing",
    "Partition",
    "PostgresPartitionManager",
    "Shard",
    "ShardManager",
    "ShardNode",
    "ShardRoute",
    "ShardStrategy",
    "ShardingError",
    "ShardingNotConfigured",
    "coerce_comparable",
    "get_partition_manager",
    "get_shard_manager",
    "hash_key",
    "render_postgres_partition_ddl",
]
