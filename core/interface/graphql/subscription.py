# -*- coding: utf-8 -*-
"""
GraphQL Subscriptions
Implements WebSocket-based real-time subscriptions
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator, List, Optional

from loguru import logger

from .schema import Alert, SystemMetrics


class AlertSubscription:
    """Alert subscription for real-time alert streaming"""

    def __init__(self):
        """Initialize alert subscription"""
        self._subscribers: List[asyncio.Queue] = []
        self._running = False

    async def subscribe(self) -> AsyncGenerator[Alert, None]:
        """
        Subscribe to alert stream

        Yields:
            Alert updates
        """
        queue: asyncio.Queue[Alert] = asyncio.Queue()
        self._subscribers.append(queue)

        try:
            while True:
                alert = await queue.get()
                yield alert
        finally:
            self._subscribers.remove(queue)

    async def publish(self, alert: Alert) -> None:
        """
        Publish alert to all subscribers

        Args:
            alert: Alert to publish
        """
        for queue in self._subscribers:
            await queue.put(alert)

    async def start(self) -> None:
        """Start alert subscription service"""
        self._running = True
        logger.info("Alert subscription started")

    async def stop(self) -> None:
        """Stop alert subscription service"""
        self._running = False
        logger.info("Alert subscription stopped")


class MetricsSubscription:
    """Metrics subscription for real-time metrics streaming"""

    def __init__(self, interval: float = 5.0):
        """
        Initialize metrics subscription

        Args:
            interval: Update interval in seconds
        """
        self.interval = interval
        self._subscribers: List[asyncio.Queue] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def subscribe(self) -> AsyncGenerator[SystemMetrics, None]:
        """
        Subscribe to metrics stream

        Yields:
            SystemMetrics updates
        """
        queue: asyncio.Queue[SystemMetrics] = asyncio.Queue()
        self._subscribers.append(queue)

        try:
            while True:
                metrics = await queue.get()
                yield metrics
        finally:
            self._subscribers.remove(queue)

    async def publish(self, metrics: SystemMetrics) -> None:
        """
        Publish metrics to all subscribers

        Args:
            metrics: Metrics to publish
        """
        for queue in self._subscribers:
            await queue.put(metrics)

    async def start(self) -> None:
        """Start metrics subscription service"""
        self._running = True
        self._task = asyncio.create_task(self._metrics_loop())
        logger.info("Metrics subscription started")

    async def stop(self) -> None:
        """Stop metrics subscription service"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics subscription stopped")

    async def _metrics_loop(self) -> None:
        """Background task to collect and publish metrics"""
        while self._running:
            try:
                # Collect metrics
                from core.collector import collect_all

                data = collect_all()

                metrics = SystemMetrics(
                    cpu_usage=data.get("cpu", {}).get("usage_percent", 0),
                    memory_usage=data.get("memory", {}).get("usage_percent", 0),
                    disk_usage=data.get("disk", {}).get("usage_percent", 0),
                    network_rx=data.get("network", {}).get("rx_bytes", 0),
                    network_tx=data.get("network", {}).get("tx_bytes", 0),
                    timestamp=datetime.now(),
                )

                await self.publish(metrics)

            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")

            await asyncio.sleep(self.interval)


class SubscriptionManager:
    """
    Manages all GraphQL subscriptions
    """

    def __init__(self):
        """Initialize subscription manager"""
        self.alert_subscription = AlertSubscription()
        self.metrics_subscription = MetricsSubscription()

    async def start_all(self) -> None:
        """Start all subscriptions"""
        await self.alert_subscription.start()
        await self.metrics_subscription.start()

    async def stop_all(self) -> None:
        """Stop all subscriptions"""
        await self.alert_subscription.stop()
        await self.metrics_subscription.stop()

    async def alert_stream(self) -> AsyncGenerator[Alert, None]:
        """Get alert stream"""
        async for alert in self.alert_subscription.subscribe():
            yield alert

    async def metrics_stream(self) -> AsyncGenerator[SystemMetrics, None]:
        """Get metrics stream"""
        async for metrics in self.metrics_subscription.subscribe():
            yield metrics
