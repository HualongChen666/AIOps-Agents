# -*- coding: utf-8 -*-
"""Message Queue service thin wrapper around the ConnectorBus engine."""

from __future__ import annotations

from typing import Any, Dict

from extensions.addons.engines.connector_bus import ConnectorBus

OPERATIONS = [
    "implement_message_producer",
    "implement_message_consumer",
]

_DISPATCH = {
    "implement_message_producer": "publish_queue",
    "implement_message_consumer": "subscribe_queue",
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
