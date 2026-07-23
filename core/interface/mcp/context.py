# -*- coding: utf-8 -*-
"""
MCP Context Management
Manages model context exchange and sharing
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ContextEntry:
    """Context entry"""

    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl


class ContextManager:
    """
    Manages MCP context storage and retrieval
    """

    def __init__(self, max_entries: int = 1000):
        """
        Initialize context manager

        Args:
            max_entries: Maximum number of context entries
        """
        self.max_entries = max_entries
        self._contexts: Dict[str, Dict[str, ContextEntry]] = {}
        self._lock = None

    async def set_context(
        self,
        context_id: str,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[float] = None,
    ) -> bool:
        """
        Set context value

        Args:
            context_id: Context identifier
            key: Context key
            value: Context value
            metadata: Metadata
            ttl: Time to live in seconds

        Returns:
            True if successful
        """
        if context_id not in self._contexts:
            self._contexts[context_id] = {}

        # Check max entries
        if len(self._contexts[context_id]) >= self.max_entries:
            # Remove oldest entry
            oldest_key = min(
                self._contexts[context_id].keys(),
                key=lambda k: self._contexts[context_id][k].timestamp,
            )
            del self._contexts[context_id][oldest_key]

        self._contexts[context_id][key] = ContextEntry(
            key=key, value=value, metadata=metadata or {}, ttl=ttl
        )

        logger.debug(f"Set context: {context_id}/{key}")
        return True

    async def get_context(self, context_id: str, key: str) -> Optional[Any]:
        """
        Get context value

        Args:
            context_id: Context identifier
            key: Context key

        Returns:
            Context value or None
        """
        if context_id not in self._contexts:
            return None

        entry = self._contexts[context_id].get(key)
        if entry is None:
            return None

        # Check expiration
        if entry.is_expired():
            del self._contexts[context_id][key]
            return None

        return entry.value

    async def delete_context(self, context_id: str, key: Optional[str] = None) -> bool:
        """
        Delete context value

        Args:
            context_id: Context identifier
            key: Context key (if None, delete entire context)

        Returns:
            True if successful
        """
        if context_id not in self._contexts:
            return False

        if key is None:
            del self._contexts[context_id]
            logger.debug(f"Deleted entire context: {context_id}")
            return True

        if key in self._contexts[context_id]:
            del self._contexts[context_id][key]
            logger.debug(f"Deleted context key: {context_id}/{key}")
            return True

        return False

    async def list_contexts(self) -> List[str]:
        """
        List all context IDs

        Returns:
            List of context identifiers
        """
        return list(self._contexts.keys())

    async def get_context_keys(self, context_id: str) -> List[str]:
        """
        List keys in a context

        Args:
            context_id: Context identifier

        Returns:
            List of keys
        """
        if context_id not in self._contexts:
            return []

        # Clean expired entries
        expired_keys = [
            key for key, entry in self._contexts[context_id].items() if entry.is_expired()
        ]
        for key in expired_keys:
            del self._contexts[context_id][key]

        return list(self._contexts[context_id].keys())

    async def get_full_context(self, context_id: str) -> Dict[str, Any]:
        """
        Get full context as dictionary

        Args:
            context_id: Context identifier

        Returns:
            Dictionary of all context values
        """
        keys = await self.get_context_keys(context_id)
        context = {}

        for key in keys:
            value = await self.get_context(context_id, key)
            if value is not None:
                context[key] = value

        return context

    async def cleanup_expired(self) -> int:
        """
        Clean up all expired entries

        Returns:
            Number of entries cleaned up
        """
        cleaned = 0

        for context_id in list(self._contexts.keys()):
            keys = await self.get_context_keys(context_id)
            for key in keys:
                entry = self._contexts[context_id].get(key)
                if entry and entry.is_expired():
                    del self._contexts[context_id][key]
                    cleaned += 1

            # Remove empty contexts
            if not self._contexts[context_id]:
                del self._contexts[context_id]

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired context entries")

        return cleaned
