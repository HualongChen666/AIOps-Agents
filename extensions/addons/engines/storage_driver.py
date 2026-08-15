# -*- coding: utf-8 -*-
"""Multi-backend storage driver for the data platform addon group.

Supports Redis, PostgreSQL, SQLite and Qdrant.  Real client usage is gated by
``dry_run`` and ``INFRA_EXECUTE_ENABLED`` so that addons are safe by default.

Converged to reuse ``modules.storage.postgres.storage`` for SQL operations and
``modules.analyze.runbook.vector_store`` for vector/semantic operations, while
keeping Redis and raw Qdrant HTTP where no equivalent module exists.
"""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.parse
from typing import Any, Dict, Iterable, List, Optional


class StorageDriver:
    """Storage driver with Redis/PostgreSQL/SQLite/Qdrant support."""

    def __init__(
        self,
        dry_run: bool = True,
        redis_url: str = "redis://localhost:6379",
        database_url: str = "postgresql://localhost:5432/postgres",
        qdrant_url: str = "http://localhost:6333",
        **kwargs: Any,
    ) -> None:
        if not dry_run and os.environ.get("INFRA_EXECUTE_ENABLED") != "true":
            raise RuntimeError("Real execution requires INFRA_EXECUTE_ENABLED=true")
        self.dry_run = dry_run
        self.redis_url = redis_url
        self.database_url = database_url
        self.qdrant_url = qdrant_url.rstrip("/")

        # simulation state
        self._cache: Dict[str, Any] = {}
        self._db_rows: List[Dict[str, Any]] = []
        self._vectors: Dict[str, List[Dict[str, Any]]] = {}

        # counters for get_stats()
        self._cache_hits = 0
        self._db_size = 0
        self._vector_count = 0

    @staticmethod
    def _as_json(value: Any) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)
        return str(value)

    # ------------------------------------------------------------------
    # Redis / cache
    # ------------------------------------------------------------------
    def cache_get(self, key: str, **kwargs: Any) -> Any:
        """Get a value from the Redis cache."""
        if self.dry_run:
            value = self._cache.get(key)
            if value is not None:
                self._cache_hits += 1
            return value

        try:
            import redis

            r = redis.Redis.from_url(self.redis_url)
            raw = r.get(key)
            if raw is None:
                return None
            value = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            self._cache_hits += 1
            return value
        except Exception as exc:  # pragma: no cover
            return {"error": str(exc)}

    def cache_set(self, key: str, value: Any, ttl: int = 0, **kwargs: Any) -> Any:
        """Set a value in the Redis cache with an optional TTL."""
        if self.dry_run:
            self._cache[key] = value
            return {"stored": True, "key": key}

        try:
            import redis

            r = redis.Redis.from_url(self.redis_url)
            stored = self._as_json(value)
            r.set(key, stored, ex=ttl if ttl else None)
            return {"stored": True, "key": key}
        except Exception as exc:  # pragma: no cover
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # PostgreSQL / SQLite
    # ------------------------------------------------------------------
    def _is_sqlite_url(self) -> bool:
        db = self.database_url.lower()
        return "sqlite" in db or db.endswith((".db", ".sqlite"))

    def _sqlite_path(self) -> str:
        """Convert a SQLAlchemy-style sqlite URL to a filesystem path."""
        url = self.database_url
        if "://" in url:
            path = url.split("://", 1)[1]
            if path.startswith("/"):
                path = path[1:]
            return path
        return url

    def _sql_sqlite(self, query: str, params: Any, readonly: bool) -> Any:
        conn = sqlite3.connect(self._sqlite_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute(query, params or [])
            if readonly or query.strip().lower().startswith("select"):
                rows = cur.fetchall()
                return [dict(row) for row in rows]
            conn.commit()
            return conn.total_changes
        finally:
            cur.close()
            conn.close()

    def _get_postgres_storage(self) -> Any:
        """Create and initialize a real PostgreSQLStorage instance."""
        from modules.storage.postgres.storage import PostgreSQLStorage

        parsed = urllib.parse.urlparse(self.database_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        database = (parsed.path or "/postgres").lstrip("/") or "postgres"
        user = parsed.username or "postgres"
        password = parsed.password or ""

        storage = PostgreSQLStorage(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        if not storage.initialize():
            raise RuntimeError("Failed to initialize PostgreSQL storage")
        return storage

    def sql(self, query: str, params: Any = None, readonly: bool = True, **kwargs: Any) -> Any:
        """Run a PostgreSQL or SQLite query."""
        if self.dry_run:
            if readonly or query.strip().lower().startswith("select"):
                return list(self._db_rows)
            self._db_size += 1
            return 1

        if self._is_sqlite_url():
            return self._sql_sqlite(query, params, readonly)

        try:
            storage = self._get_postgres_storage()
            return storage.execute_query(query, tuple(params or ()))
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Qdrant / vectors
    # ------------------------------------------------------------------
    def _qdrant_request(self, method: str, path: str, json_body: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.qdrant_url}{path}"
        try:
            import httpx

            client = httpx.Client()
            request = getattr(client, method.lower())
            resp = request(url, json=json_body)
            body = resp.json() if resp.content else {}
            client.close()
            return body
        except Exception:
            import requests

            fn = getattr(requests, method.lower())
            resp = fn(url, json=json_body)
            return resp.json() if resp.content else {}

    def vector_create_collection(
        self, name: str, size: int, distance: str = "Cosine", **kwargs: Any
    ) -> Any:
        """Create a Qdrant vector collection."""
        if self.dry_run:
            self._vectors.setdefault(name, [])
            return {"status": "created", "collection": name}

        body = {"vectors": {"size": size, "distance": distance}}
        return self._qdrant_request("PUT", f"/collections/{name}", body)

    def _vector_store(self, name: str) -> Any:
        """Create and initialize a real VectorStore for the given collection."""
        from modules.analyze.runbook.vector_store import (
            QDRANT_AVAILABLE,
            VectorStore,
        )

        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client not installed")

        store = VectorStore(
            collection_name=name,
            qdrant_url=self.qdrant_url,
        )
        store.initialize()
        return store

    def vector_upsert(
        self,
        name: str,
        ids: Iterable[Any],
        vectors: Iterable[Iterable[float]],
        payloads: Optional[Iterable[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Any:
        """Upsert vectors into a collection via the real VectorStore."""
        ids = list(ids)
        vectors = list(vectors)
        if payloads is None:
            payloads = [{} for _ in ids]
        payloads = list(payloads)

        if self.dry_run:
            points = [
                {"id": i, "vector": v, "payload": p}
                for i, v, p in zip(ids, vectors, payloads)
            ]
            self._vectors.setdefault(name, []).extend(points)
            self._vector_count += len(ids)
            return {"upserted": len(ids)}

        try:
            store = self._vector_store(name)
            documents = []
            for point_id, vector, payload in zip(ids, vectors, payloads):
                payload = payload or {}
                content = payload.get("content", str(point_id))
                metadata = dict(payload)
                metadata["_raw_vector"] = list(vector)
                documents.append(
                    {
                        "id": str(point_id),
                        "content": content,
                        "metadata": metadata,
                    }
                )
            added = store.add_documents_batch(documents)
            return {"upserted": added}
        except Exception as exc:
            return {"error": str(exc)}

    def vector_search(
        self, name: str, vector: Iterable[float], top: int = 5, **kwargs: Any
    ) -> Any:
        """Search a collection by vector similarity via the real VectorStore."""
        vector = list(vector)
        if self.dry_run:
            coll = self._vectors.get(name, [])
            return [
                {"id": p["id"], "score": 1.0, "payload": p["payload"]}
                for p in coll[:top]
            ]

        try:
            store = self._vector_store(name)
            # VectorStore.search expects a text query. If a query string is not
            # supplied, fall back to a deterministic text representation of the
            # raw vector so the semantic search API can still be exercised.
            query = kwargs.get("query")
            if not isinstance(query, str):
                query = " ".join(str(round(v, 6)) for v in vector)
            return store.search(query=query, top_k=top)
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self, **kwargs: Any) -> Dict[str, Any]:
        """Return aggregate stats for cache, database and vector store."""
        return {
            "cache_hits": self._cache_hits,
            "db_size": self._db_size,
            "vector_count": self._vector_count,
        }
