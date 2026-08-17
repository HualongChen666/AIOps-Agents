# -*- coding: utf-8 -*-
"""
GraphQL Data Loaders
Implements N+1 query optimization with batching
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional

from loguru import logger


class DataLoader:
    """
    Generic data loader for batching requests
    """

    def __init__(
        self,
        batch_load_fn: Callable[[List[Any]], Awaitable[List[Any]]],
        max_batch_size: int = 100,
        cache: bool = True,
    ):
        """
        Initialize data loader

        Args:
            batch_load_fn: Async function to load batch of items
            max_batch_size: Maximum batch size
            cache: Whether to cache results
        """
        self.batch_load_fn = batch_load_fn
        self.max_batch_size = max_batch_size
        self.cache = cache
        self._cache: Dict[Any, Any] = {}
        self._batch: List[Any] = []
        self._callbacks: List[asyncio.Future[Any]] = []
        self._scheduled = False

    async def load(self, key: Any) -> Any:
        """
        Load a single item

        Args:
            key: Item key

        Returns:
            Loaded item
        """
        if self.cache and key in self._cache:
            return self._cache[key]

        # Create a promise for this item
        future: asyncio.Future[Any] = asyncio.Future()
        self._batch.append(key)
        self._callbacks.append(future)

        # Schedule batch loading
        if not self._scheduled:
            self._scheduled = True
            asyncio.create_task(self._dispatch_batch())

        result = await future

        if self.cache:
            self._cache[key] = result

        return result

    async def load_many(self, keys: List[Any]) -> List[Any]:
        """
        Load multiple items

        Args:
            keys: List of item keys

        Returns:
            List of loaded items
        """
        results = await asyncio.gather(*[self.load(key) for key in keys])
        return results

    async def _dispatch_batch(self) -> None:
        """Dispatch batch for loading"""
        try:
            # Split into batches if needed
            batch_size = len(self._batch)
            for i in range(0, batch_size, self.max_batch_size):
                batch_keys = self._batch[i : i + self.max_batch_size]
                batch_callbacks = self._callbacks[i : i + self.max_batch_size]

                try:
                    results = await self.batch_load_fn(batch_keys)

                    # Resolve futures
                    for callback, result in zip(batch_callbacks, results):
                        if not callback.done():
                            callback.set_result(result)
                except Exception as e:
                    logger.error(f"Batch load failed: {e}")
                    for callback in batch_callbacks:
                        if not callback.done():
                            callback.set_exception(e)

        finally:
            # Reset batch state
            self._batch = []
            self._callbacks = []
            self._scheduled = False

    def clear(self, key: Optional[Any] = None) -> None:
        """
        Clear cache

        Args:
            key: Specific key to clear, or None to clear all
        """
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def prime(self, key: Any, value: Any) -> None:
        """
        Prime cache with value

        Args:
            key: Item key
            value: Item value
        """
        if self.cache:
            self._cache[key] = value


class AlertDataLoader(DataLoader):
    """Data loader for alerts"""

    def __init__(self):
        """Initialize alert data loader"""

        async def batch_load_fn(alert_ids: List[str]) -> List[Any]:
            from core.alert_engine import get_alerts_by_ids  # type: ignore

            return await get_alerts_by_ids(alert_ids)  # type: ignore

        super().__init__(batch_load_fn)


class RepairDataLoader(DataLoader):
    """Data loader for repair actions"""

    def __init__(self):
        """Initialize repair data loader"""

        async def batch_load_fn(repair_ids: List[str]) -> List[Any]:
            from core.repair_engine import get_repairs_by_ids  # type: ignore

            return await get_repairs_by_ids(repair_ids)  # type: ignore

        super().__init__(batch_load_fn)


class MetricsDataLoader(DataLoader):
    """Data loader for metrics"""

    def __init__(self):
        """Initialize metrics data loader"""

        async def batch_load_fn(timestamps: List[float]) -> List[Any]:
            from core.metrics_history import get_metrics_at_timestamps  # type: ignore

            return await get_metrics_at_timestamps(timestamps)  # type: ignore

        super().__init__(batch_load_fn)


class DataLoaderRegistry:
    """
    Registry for data loaders
    """

    def __init__(self):
        """Initialize data loader registry"""
        self._alert_loader: Optional[AlertDataLoader] = None
        self._repair_loader: Optional[RepairDataLoader] = None
        self._metrics_loader: Optional[MetricsDataLoader] = None

    def get_alert_loader(self) -> AlertDataLoader:
        """Get or create alert data loader"""
        if self._alert_loader is None:
            self._alert_loader = AlertDataLoader()
        return self._alert_loader

    def get_repair_loader(self) -> RepairDataLoader:
        """Get or create repair data loader"""
        if self._repair_loader is None:
            self._repair_loader = RepairDataLoader()
        return self._repair_loader

    def get_metrics_loader(self) -> MetricsDataLoader:
        """Get or create metrics data loader"""
        if self._metrics_loader is None:
            self._metrics_loader = MetricsDataLoader()
        return self._metrics_loader

    def clear_all(self) -> None:
        """Clear all data loader caches"""
        if self._alert_loader:
            self._alert_loader.clear()
        if self._repair_loader:
            self._repair_loader.clear()
        if self._metrics_loader:
            self._metrics_loader.clear()
