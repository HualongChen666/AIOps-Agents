# -*- coding: utf-8 -*-
"""
L4 Storage Layer - Retry and Connection Pool Utilities
Provides retry logic, connection pooling, and fallback mechanisms
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

import httpx
from loguru import logger


class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ConnectionPoolConfig:
    """Configuration for HTTP connection pool"""

    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
        timeout: float = 30.0,
    ):
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff

    Args:
        config: Retry configuration
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on last attempt
                    if attempt == config.max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_retries} "
                            f"retries: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base**attempt), config.max_delay
                    )

                    # Add jitter to avoid thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + (0.5 * asyncio.get_event_loop().time() % 1))

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/"
                        f"{config.max_retries + 1}), retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class FallbackStorage:
    """
    Provides fallback mechanism when primary storage is unavailable
    """

    def __init__(
        self,
        primary_storage: Any,
        fallback_storage: Optional[Any] = None,
        fallback_enabled: bool = True,
    ):
        """
        Initialize fallback storage

        Args:
            primary_storage: Primary storage backend
            fallback_storage: Fallback storage backend
            fallback_enabled: Whether to enable fallback
        """
        self.primary_storage = primary_storage
        self.fallback_storage = fallback_storage
        self.fallback_enabled = fallback_enabled
        self._use_fallback = False
        self._last_primary_check = 0.0
        self._primary_check_interval = 60  # seconds
        self._primary_available = True

    async def _try_primary_store(
        self, key: str, value: Any, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Try storing in primary storage"""
        try:
            result = await self.primary_storage.store(key, value, metadata)
            if result:
                self._primary_available = True
                return True
        except Exception as e:
            logger.warning(f"Primary storage failed: {e}")
            self._primary_available = False
            if self.fallback_enabled and self.fallback_storage:
                self._use_fallback = True
                logger.info("Switching to fallback storage")
        return False

    async def _try_fallback_store(
        self, key: str, value: Any, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Try storing in fallback storage"""
        if self.fallback_storage is None:
            return False
        try:
            result = await self.fallback_storage.store(key, value, metadata)
            if result:
                return True
        except Exception as e:
            logger.error(f"Fallback storage also failed: {e}")
        return False

    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data with fallback

        Args:
            key: Storage key
            value: Value to store
            metadata: Optional metadata

        Returns:
            True if successful
        """
        # Try primary storage first
        if not self._use_fallback:
            if await self._try_primary_store(key, value, metadata):
                return True

        # Use fallback if enabled and primary failed
        if self._use_fallback and self.fallback_storage:
            return await self._try_fallback_store(key, value, metadata)

        return False

    async def _try_primary_retrieve(self, key: str) -> Optional[Any]:
        """Try retrieving from primary storage"""
        try:
            result = await self.primary_storage.retrieve(key)
            if result is not None:
                self._primary_available = True
                return result
        except Exception as e:
            logger.warning(f"Primary storage retrieve failed: {e}")
            self._primary_available = False
            if self.fallback_enabled and self.fallback_storage:
                self._use_fallback = True
        return None

    async def _try_fallback_retrieve(self, key: str) -> Optional[Any]:
        """Try retrieving from fallback storage"""
        if self.fallback_storage is None:
            return None
        try:
            result = await self.fallback_storage.retrieve(key)
            return result
        except Exception as e:
            logger.error(f"Fallback storage retrieve failed: {e}")
        return None

    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve data with fallback

        Args:
            key: Storage key

        Returns:
            Retrieved value or None
        """
        # Try primary storage first
        if not self._use_fallback:
            result = await self._try_primary_retrieve(key)
            if result is not None:
                return result

        # Use fallback if enabled
        if self._use_fallback and self.fallback_storage:
            return await self._try_fallback_retrieve(key)

        return None

    def _should_check_primary(self) -> bool:
        """Check if it's time to check primary availability"""
        current_time = time.time()
        return current_time - self._last_primary_check >= self._primary_check_interval

    def _check_primary_status(self) -> bool:
        """Check primary storage status via get_status method"""
        try:
            if hasattr(self.primary_storage, "get_status"):
                status = self.primary_storage.get_status()
                if status.get("initialized") and status.get("connected"):
                    self._primary_available = True
                    if self._use_fallback:
                        logger.info("Primary storage recovered, switching back")
                        self._use_fallback = False
                    return True
        except Exception as e:
            logger.warning(f"Primary storage status check failed: {e}")
        return False

    async def check_primary_availability(self) -> bool:
        """
        Check if primary storage is available

        Returns:
            True if primary storage is available
        """
        # Only check periodically
        if not self._should_check_primary():
            return self._primary_available

        self._last_primary_check = time.time()

        # Try to check primary status
        if self._check_primary_status():
            return True

        self._primary_available = False
        return False


class BufferedWriter:
    """
    Provides buffered batch writing for improved performance
    """

    def __init__(
        self,
        storage: Any,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        max_buffer_size: int = 1000,
    ):
        """
        Initialize buffered writer

        Args:
            storage: Storage backend
            buffer_size: Number of items to buffer before flush
            flush_interval: Time interval between flushes (seconds)
            max_buffer_size: Maximum buffer size before forced flush
        """
        self.storage = storage
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.max_buffer_size = max_buffer_size
        self._buffer: list[Tuple[str, Any, Optional[Dict[str, Any]]]] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the background flush task"""
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Buffered writer started")

    async def stop(self) -> None:
        """Stop the buffered writer and flush remaining items"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        logger.info("Buffered writer stopped")

    async def _should_flush_buffer(self) -> bool:
        """Check if buffer should be flushed"""
        return len(self._buffer) >= self.buffer_size

    async def _should_force_flush(self) -> bool:
        """Check if buffer should be force-flushed due to max size"""
        return len(self._buffer) >= self.max_buffer_size

    async def write(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Write item to buffer

        Args:
            key: Storage key
            value: Value to store
            metadata: Optional metadata

        Returns:
            True if buffered successfully
        """
        async with self._lock:
            self._buffer.append((key, value, metadata))
            should_flush = await self._should_flush_buffer()
            should_force = await self._should_force_flush()

        # Flush outside the lock to avoid reentrant deadlock
        if should_flush:
            await self.flush()

        if should_force:
            await self.flush()
            logger.warning("Buffer exceeded max size, forced flush")

        return True

    async def _get_buffer_items(self) -> list:
        """Get and clear buffer items"""
        async with self._lock:
            items_to_flush = self._buffer.copy()
            self._buffer.clear()
        return items_to_flush

    async def _write_item_to_storage(
        self, key: str, value: Any, metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Write single item to storage"""
        try:
            result = await self.storage.store(key, value, metadata)
            return result if result else False
        except Exception as e:
            logger.error(f"Failed to write item {key}: {e}")
            return False

    async def flush(self) -> None:
        """Flush all buffered items to storage"""
        items_to_flush = await self._get_buffer_items()

        if not items_to_flush:
            return

        try:
            # Batch write all items
            success_count = 0
            for key, value, metadata in items_to_flush:
                if await self._write_item_to_storage(key, value, metadata):
                    success_count += 1

            logger.debug(f"Flushed {success_count}/{len(items_to_flush)} items to storage")

        except Exception as e:
            logger.error(f"Error during flush: {e}")

    async def _flush_loop(self) -> None:
        """Background task to periodically flush buffer"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")


def create_http_client(config: Optional[ConnectionPoolConfig] = None) -> httpx.AsyncClient:
    """
    Create HTTP client with connection pool configuration

    Args:
        config: Connection pool configuration

    Returns:
        Configured HTTP client
    """
    if config is None:
        config = ConnectionPoolConfig()

    limits = httpx.Limits(
        max_connections=config.max_connections,
        max_keepalive_connections=config.max_keepalive_connections,
        keepalive_expiry=config.keepalive_expiry,
    )

    return httpx.AsyncClient(limits=limits, timeout=config.timeout)
