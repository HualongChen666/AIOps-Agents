# -*- coding: utf-8 -*-
"""
L5 Interface Layer - GraphQL Interface
GraphQL interface for L5 Interface Layer
Provides flexible query capabilities for frontend and external systems
"""

from typing import Any, Dict, List, Optional

from loguru import logger

# GraphQL imports
try:
    from strawberry import Schema, strawberry  # type: ignore
    from strawberry.fastapi import GraphQLRouter

    STRAWBERRY_AVAILABLE = True
except ImportError:
    STRAWBERRY_AVAILABLE = False
    logger.warning("Strawberry GraphQL not available - GraphQL interface will use fallback")


class GraphQLInterface:
    """
    GraphQL interface for L5 Layer

    This interface provides:
    - Flexible query capabilities
    - Type-safe schema
    - Efficient data fetching
    - Real-time subscriptions
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config
        self.router: Optional[Any] = None
        self._is_initialized = False
        # Real data-source hooks (set via config or the setters below).
        self._host_provider: Optional[Any] = config.get("host_provider")
        self._repair_trigger: Optional[Any] = config.get("repair_trigger")

        if STRAWBERRY_AVAILABLE:
            self._build_schema()
        else:
            logger.warning("GraphQL not available, using REST fallback")

    def set_host_provider(self, provider: Any) -> None:
        """Register a real host data provider (must expose get_host/list_hosts)."""
        self._host_provider = provider

    def set_repair_trigger(self, trigger: Any) -> None:
        """Register a real repair trigger callable ``(alert_id, user) -> str``."""
        self._repair_trigger = trigger

    @staticmethod
    def _host_from_dict(host_cls, metric_cls, alert_cls, data: Dict[str, Any]):
        metrics = [
            metric_cls(name=m.get("name", ""), value=float(m.get("value", 0.0)),
                       timestamp=str(m.get("timestamp", "")))
            for m in (data.get("metrics") or [])
        ]
        alerts = [
            alert_cls(id=a.get("id", ""), severity=a.get("severity", ""),
                      message=a.get("message", ""), timestamp=str(a.get("timestamp", "")))
            for a in (data.get("alerts") or [])
        ]
        return host_cls(
            id=str(data.get("id")),
            name=data.get("name", str(data.get("id"))),
            status=data.get("status", "unknown"),
            metrics=metrics,
            alerts=alerts,
        )

    def _build_schema(self) -> None:
        """Build GraphQL schema"""
        try:

            @strawberry.type
            class Metric:
                name: str
                value: float
                timestamp: str

            @strawberry.type
            class Alert:
                id: str
                severity: str
                message: str
                timestamp: str

            @strawberry.type
            class Host:
                id: str
                name: str
                status: str
                metrics: List[Metric]
                alerts: List[Alert]

            @strawberry.type
            class Query:
                @strawberry.field
                def host(self, id: str) -> Optional[Host]:
                    """Get host by ID from the registered host provider."""
                    if self._host_provider is None:
                        logger.warning("No host provider registered; cannot resolve host %s", id)
                        return None
                    get_host = getattr(self._host_provider, "get_host", None)
                    if get_host is None:
                        provider_map = getattr(self._host_provider, "hosts", None)
                        data = provider_map.get(id) if isinstance(provider_map, dict) else None
                    else:
                        data = get_host(id)
                    if not data:
                        return None
                    return GraphQLInterface._host_from_dict(Host, Metric, Alert, data)  # type: ignore[call-arg]

                @strawberry.field
                def hosts(self) -> List[Host]:
                    """Get all hosts from the registered host provider."""
                    if self._host_provider is None:
                        return []
                    list_hosts = getattr(self._host_provider, "list_hosts", None)
                    if list_hosts is not None:
                        raw = list_hosts()
                    elif isinstance(getattr(self._host_provider, "hosts", None), dict):
                        raw = list(self._host_provider.hosts.values())
                    else:
                        raw = []
                    return [
                        GraphQLInterface._host_from_dict(Host, Metric, Alert, d)
                        for d in raw
                    ]

            @strawberry.type
            class Mutation:
                @strawberry.mutation
                def trigger_repair(self, alert_id: str, user: str) -> str:
                    """Trigger repair for an alert via the registered repair trigger."""
                    if self._repair_trigger is None:
                        raise RuntimeError(
                            "No repair trigger registered; cannot trigger repair"
                        )
                    result = self._repair_trigger(alert_id, user)
                    if hasattr(result, "__await__"):
                        raise RuntimeError(
                            "Repair trigger must be synchronous; got a coroutine"
                        )
                    return str(result)

            schema = Schema(query=Query, mutation=Mutation)
            self.router = GraphQLRouter(schema, graphiql=True)
            self._is_initialized = True
            logger.info("GraphQL interface initialized successfully")

        except Exception as e:
            logger.error(f"Failed to build GraphQL schema: {e}")
            self._is_initialized = False

    def get_router(self):
        """Get the GraphQL router"""
        return self.router

    def get_status(self) -> Dict[str, Any]:
        """Get interface status"""
        return {
            "initialized": self._is_initialized,
            "strawberry_available": STRAWBERRY_AVAILABLE,
            "has_router": self.router is not None,
        }


# Global singleton instance
_graphql_interface: Optional[GraphQLInterface] = None


def get_graphql_interface() -> Optional[GraphQLInterface]:
    """Get global GraphQL interface instance"""
    return _graphql_interface


def init_graphql_interface(config: Dict[str, Any]) -> GraphQLInterface:
    """Initialize global GraphQL interface"""
    global _graphql_interface
    _graphql_interface = GraphQLInterface(config)
    return _graphql_interface
