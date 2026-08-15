# -*- coding: utf-8 -*-
"""Kafka Event service thin wrapper around the ConnectorBus engine."""

from __future__ import annotations

from typing import Any, Dict

from extensions.addons.engines.connector_bus import ConnectorBus

OPERATIONS = [
    "implement_kafka_producer",
    "implement_kafka_consumer",
]

_DISPATCH = {
    "implement_kafka_producer": "produce",
    "implement_kafka_consumer": "consume",
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
