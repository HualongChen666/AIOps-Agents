# -*- coding: utf-8 -*-
"""Shared FastAPI service contract for the addon microservice wrappers.

Every ``extensions/addons/<group>/<service>/main_app.py`` template expects the
matching ``service.py`` to expose the same runtime surface:

* ``_state`` – the service's live state store (read by ``GET /health``);
* async lifecycle endpoints ``get_state`` / ``backup_state`` / ``restore_state``
  / ``get_stats`` / ``list_methods`` (``get_stats`` feeds ``/stats`` and
  ``list_methods`` feeds ``POST /rpc/list_methods``);
* an async handler for every name in ``OPERATIONS`` (reached through
  ``getattr(service, operation)`` in the ``/{service}/{path}`` dispatcher);
* ``call(method, request=...)`` – the generic ``POST /rpc/{method}`` dispatcher.

Historically most wrappers implemented only ``execute_operation`` and therefore
raised ``AttributeError`` / ``TypeError`` at request time, so every endpoint of
those 28 microservices answered HTTP 500.  ``ServiceStateContract`` supplies the
missing surface exactly once and delegates the real work back to the wrapper's
family-specific ``execute_operation`` implementation.
"""

from __future__ import annotations

import copy
import os
import time
from typing import Any, Callable, Dict, List

#: Lifecycle methods every addon service exposes in addition to ``OPERATIONS``.
BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]


class ServiceStateContract:
    """Reusable implementation of the addon microservice service contract."""

    #: Feature operations exposed by the concrete service (set by subclasses).
    OPERATIONS: List[str] = []
    BASE_METHODS: List[str] = BASE_METHODS

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Accept the (redis_url, metrics, cache, ...) keyword arguments the
        # FastAPI templates pass; only the ones we can use are retained.
        self.metrics = kwargs.get("metrics")
        self.cache = kwargs.get("cache")
        self._state: Dict[str, Any] = {}
        self._backups: Dict[str, Any] = {}
        self._operations: Dict[str, int] = {}
        self._started_at = time.time()

    # ------------------------------------------------------------------
    # request helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_config(request: Any) -> Dict[str, Any]:
        """Extract the operation payload from a request/feature object."""
        if request is None:
            return {}
        if hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            return {}
        if not isinstance(data, dict):
            return {}
        return data.get("config", data) if "config" in data else data

    def _touch(self, name: str) -> None:
        self._operations[name] = self._operations.get(name, 0) + 1

    # ------------------------------------------------------------------
    # operation dispatch
    # ------------------------------------------------------------------
    def _invoke_operation(self, name: str, config: Dict[str, Any]) -> Any:
        """Run an ``OPERATIONS`` entry through the wrapper's ``execute_operation``.

        ``self.execute_operation(name, config)`` works for both class/static
        method wrappers and instance-method wrappers (e.g. ``BaseInfraService``).
        """
        return self.execute_operation(name, config)

    def _feature_response(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a ``FeatureResponse`` payload for an operation."""
        result = self._invoke_operation(name, config)
        self._touch(name)
        if isinstance(result, dict) and "feature" in result and "success" in result:
            # Family-specific payloads (infra / security) already carry the
            # response envelope; only normalise the inner ``result`` so the
            # Pydantic model (``result: Dict[str, Any]``) can always validate.
            payload = dict(result)
            if not isinstance(payload.get("result"), dict):
                payload["result"] = {"items": payload.get("result")}
            payload.setdefault("config", config)
            payload.setdefault("status", "ok" if payload.get("success") else "error")
            payload.setdefault("message", f"{name} completed")
            return payload
        if not isinstance(result, dict):
            result = {"items": result}
        return {
            "feature": name,
            "success": True,
            "status": "ok",
            "config": config,
            "result": result,
            "message": f"{name} completed",
        }

    # ------------------------------------------------------------------
    # lifecycle endpoints
    # ------------------------------------------------------------------
    async def get_state(self, request: Any = None) -> Dict[str, Any]:
        config = self._get_config(request)
        feature = config.get("feature")
        state = self._state if not feature else {feature: self._state.get(feature)}
        return {
            "feature": "get_state",
            "success": True,
            "status": "ok",
            "config": config,
            "result": {"state": copy.deepcopy(state)},
            "message": "Current state",
        }

    async def backup_state(self, request: Any = None) -> Dict[str, Any]:
        config = self._get_config(request)
        name = config.get("name", "default")
        self._backups[name] = copy.deepcopy(self._state)
        self._touch("backup_state")
        return {
            "feature": "backup_state",
            "success": True,
            "status": "backed_up",
            "config": {"name": name},
            "result": {"snapshot": name, "backup_id": name},
            "message": f"Backup {name} created",
        }

    async def restore_state(self, request: Any = None) -> Dict[str, Any]:
        config = self._get_config(request)
        name = config.get("name", "default")
        data = self._backups.get(name)
        if data is None:
            return {
                "feature": "restore_state",
                "success": False,
                "status": "not_found",
                "config": {"name": name},
                "result": {},
                "message": f"Backup {name} not found",
            }
        self._state = copy.deepcopy(data)
        self._touch("restore_state")
        return {
            "feature": "restore_state",
            "success": True,
            "status": "restored",
            "config": {"name": name},
            "result": {"snapshot": name, "restored": True},
            "message": f"Backup {name} restored",
        }

    async def get_stats(self, request: Any = None) -> Dict[str, Any]:
        config = self._get_config(request)
        total = sum(self._operations.values())
        return {
            "feature": "get_stats",
            "success": True,
            "status": "ok",
            "config": config,
            "result": {
                "total_requests": total,
                "cache_hits": getattr(self.metrics, "cache_hits_count", 0) or 0,
                "cache_misses": getattr(self.metrics, "cache_misses_count", 0) or 0,
                "operations": dict(self._operations),
                "index_size": len(self._state),
                "feature_count": len(type(self).OPERATIONS),
            },
            "message": "Statistics",
        }

    async def list_methods(self, request: Any = None) -> Dict[str, Any]:
        return {
            "feature": "list_methods",
            "success": True,
            "status": "ok",
            "config": {},
            "result": {"methods": list(type(self).OPERATIONS) + list(self.BASE_METHODS)},
            "message": "Methods listed",
        }

    # ------------------------------------------------------------------
    # generic RPC dispatcher + per-operation handlers
    # ------------------------------------------------------------------
    async def call(self, method: str, **kwargs: Any) -> Any:
        request = kwargs.get("request")
        if method in self.BASE_METHODS:
            return await getattr(self, method)(request)
        if method in type(self).OPERATIONS:
            return self._feature_response(method, self._get_config(request))
        raise ValueError(f"Unknown method: {method}")

    def __getattr__(self, name: str) -> Any:
        if name in getattr(type(self), "OPERATIONS", []):
            async def _handler(request: Any = None, _name: str = name):
                return self._feature_response(_name, self._get_config(request))

            return _handler
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class BasePolicyService(ServiceStateContract):
    """Service wrapper base for engine-driven governance addons.

    Concrete wrappers declare ``ENGINE`` (a dry-run capable engine exposing
    ``record`` plus the ``get_state`` / ``backup_state`` / ``restore_state`` /
    ``get_stats`` / ``list_methods`` state layer) and map every ``OPERATIONS``
    entry to an engine call through ``OP_MAP``.  The FastAPI service contract is
    inherited from :class:`ServiceStateContract`, while ``execute_operation``
    keeps the governance-wrapper payload shape (``success`` / ``operation`` /
    ``dry_run`` / ``result``) that the addon tests and templates rely on.
    """

    ENGINE: Any = None
    OPERATIONS: List[str] = []
    OP_MAP: Dict[str, Callable[[Any, Dict[str, Any]], Any]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.ENGINE is not None:
            # Own engine per wrapper (no cross-service state bleed), exposed as
            # a *class* attribute so tests / tooling can tweak
            # ``ServiceClass._engine.dry_run`` before invoking operations.
            cls._engine = cls.ENGINE(dry_run=os.environ.get("INFRA_EXECUTE_ENABLED") != "true")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cls = type(self)
        dry_run = kwargs.get("dry_run")
        if cls.__dict__.get("_engine") is None:
            default = dry_run if dry_run is not None else (
                os.environ.get("INFRA_EXECUTE_ENABLED") != "true"
            )
            cls._engine = cls.ENGINE(dry_run=default)
        elif dry_run is not None:
            # Honour an explicit per-service configuration (the engine is shared
            # at class level for these stateless workers).
            cls._engine.dry_run = dry_run
        self._engine = cls._engine

    @classmethod
    def _dispatch(cls, name: str, params: Dict[str, Any]) -> Any:
        engine = cls._engine
        if name not in cls.OPERATIONS and name not in cls.BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        engine.record(name)
        if name == "get_state":
            return engine.get_state()
        if name == "backup_state":
            return engine.backup_state(params.get("label", ""))
        if name == "restore_state":
            return engine.restore_state(params.get("backup_id", ""))
        if name == "get_stats":
            return engine.get_stats()
        if name == "list_methods":
            return engine.list_methods()
        handler = cls.OP_MAP.get(name)
        if handler is None:  # pragma: no cover - guarded by the OPERATIONS check above
            raise NotImplementedError(f"{cls.__name__}: no handler for operation {name!r}")
        return handler(engine, params)

    @classmethod
    def execute_operation(cls, name: str, params: Any = None) -> Dict[str, Any]:
        """Dispatch to the engine and return a governance-wrapper payload."""
        params = params if isinstance(params, dict) else {}
        return {
            "success": True,
            "operation": name,
            "dry_run": cls._engine.dry_run,
            "result": cls._dispatch(name, params),
        }
