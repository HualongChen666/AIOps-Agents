# -*- coding: utf-8 -*-
"""ELK Stack service thin wrapper around the ConnectorBus engine."""

from __future__ import annotations

from typing import Any, Dict

from extensions.addons.engines.connector_bus import ConnectorBus

OPERATIONS = [
    "search_query",
]

_DISPATCH = {
    "search_query": "webhook_send",
}


class Service:
    OPERATIONS = OPERATIONS

    @staticmethod
    def execute_operation(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in Service.OPERATIONS:
            raise ValueError(f"Unknown operation: {name}")
        method = _DISPATCH[name]
        dry_run = params.pop("dry_run", True)
        bus = ConnectorBus(dry_run=dry_run)
        return getattr(bus, method)(**params)
