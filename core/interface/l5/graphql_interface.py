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

        if STRAWBERRY_AVAILABLE:
            self._build_schema()
        else:
            logger.warning("GraphQL not available, using REST fallback")

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
                    """Get host by ID"""
                    # Implementation would query actual data
                    return Host(
                        id=id, name=f"Host-{id}", status="healthy", metrics=[], alerts=[]
                    )  # type: ignore[call-arg]

                @strawberry.field
                def hosts(self) -> List[Host]:
                    """Get all hosts"""
                    # Implementation would query actual data
                    return []

            @strawberry.type
            class Mutation:
                @strawberry.mutation
                def trigger_repair(self, alert_id: str, user: str) -> str:
                    """Trigger repair for alert"""
                    # Implementation would call repair engine
                    return f"Repair triggered for alert {alert_id}"

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
