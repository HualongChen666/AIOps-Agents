# -*- coding: utf-8 -*-
"""
Base Executor Abstract Class
Provides common interface for all executors (auto-heal, autoscaler, workflow, etc.)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """
    Abstract base class for all executors

    All executors must implement the execute, initialize, and close methods.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base executor

        Args:
            name: Executor name
            config: Executor configuration
        """
        self.name = name
        self.config = config or {}
        self._is_initialized = False
        self._is_running = False

        logger.info(f"BaseExecutor initialized: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the executor

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action

        Args:
            action: Action to execute
            params: Action parameters

        Returns:
            Execution result dictionary
        """

    @abstractmethod
    def close(self) -> None:
        """Close the executor and release resources"""

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
        Get executor status

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "initialized": self._is_initialized,
            "running": self._is_running,
            "config": self.config,
        }

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
