# -*- coding: utf-8 -*-
"""
Base Analyzer Abstract Class
Provides common interface for all analyzers (anomaly detection, root cause analysis, forecasting, etc.)  # noqa: E501
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Abstract base class for all analyzers

    All analyzers must implement the analyze, initialize, and close methods.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize base analyzer

        Args:
            name: Analyzer name
            config: Analyzer configuration
        """
        self.name = name
        self.config = config or {}
        self._is_initialized = False
        self._is_fitted = False

        logger.info(f"BaseAnalyzer initialized: {name}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the analyzer

        Returns:
            True if initialization successful
        """

    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data and return results

        Args:
            data: Input data for analysis

        Returns:
            Analysis results dictionary
        """

    @abstractmethod
    def close(self) -> None:
        """Close the analyzer and release resources"""

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
        Get analyzer status

        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "initialized": self._is_initialized,
            "fitted": self._is_fitted,
            "config": self.config,
        }

    def __enter__(self):
        """Context manager entry"""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
