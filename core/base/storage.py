# -*- coding: utf-8 -*-
"""
Base Storage Abstract Class
Provides common interface for all storage components (PostgreSQL, TimescaleDB, Qdrant, etc.)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """
    Abstract base class for all storage components

    All storage components must implement the store, retrieve, initialize, and close methods.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base storage

        Args:
            name: Storage name
            config: Storage configuration
        """
        self.name = name
        self.config = config or {}
        self._is_initialized = False
        self._is_connected = False

        logger.info(f"BaseStorage initialized: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the storage

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data

        Args:
            key: Storage key
            value: Value to store
            metadata: Optional metadata

        Returns:
            True if successful
        """

    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve data

        Args:
            key: Storage key

        Returns:
            Retrieved value or None
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete data

        Args:
            key: Storage key

        Returns:
            True if successful
        """

    @abstractmethod
    async def query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query data

        Args:
            query: Query parameters

        Returns:
            List of matching records
        """

    @abstractmethod
    def close(self) -> None:
        """Close the storage and release resources"""

    def validate_config(self, required_keys: List[str]) -> bool:
        """
        Validate configuration has required keys

        Args:
            required_keys: List of required configuration keys

        Returns:
            True if configuration is valid
        """
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            logger.error(f"Missing required config keys: {missing_keys}")
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get storage status

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "initialized": self._is_initialized,
            "connected": self._is_connected,
            "config": self.config,
        }

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
