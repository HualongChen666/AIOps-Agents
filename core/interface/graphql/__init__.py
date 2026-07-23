# -*- coding: utf-8 -*-
"""
GraphQL Interface Module
"""

from .auth import AuthContext, Permission, Role, get_current_user, require_permission, require_role
from .dataloader import (
    AlertDataLoader,
    DataLoader,
    DataLoaderRegistry,
    MetricsDataLoader,
    RepairDataLoader,
)
from .resolvers import AlertResolver, MetricsResolver, ProcessResolver, RepairResolver
from .schema import Mutation, Query, Subscription
from .subscription import AlertSubscription, MetricsSubscription, SubscriptionManager

__all__ = [
    "Query",
    "Mutation",
    "Subscription",
    "MetricsResolver",
    "AlertResolver",
    "ProcessResolver",
    "RepairResolver",
    "DataLoader",
    "DataLoaderRegistry",
    "AlertDataLoader",
    "RepairDataLoader",
    "MetricsDataLoader",
    "SubscriptionManager",
    "AlertSubscription",
    "MetricsSubscription",
    "AuthContext",
    "Permission",
    "Role",
    "get_current_user",
    "require_permission",
    "require_role",
]
