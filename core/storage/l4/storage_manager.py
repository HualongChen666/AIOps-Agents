# -*- coding: utf-8 -*-
"""
L4 Storage Layer Manager
Coordinates all L4 storage backends (VictoriaMetrics, Loki, Tempo)
"""

from typing import Any, Dict, Optional

from loguru import logger

from .loki import LokiStorage
from .tempo import TempoStorage
from .victoriametrics import VictoriaMetricsStorage


class L4StorageManager:
    """
    Manages all L4 storage backends

    Provides unified interface for:
    - VictoriaMetrics: Metrics storage
    - Loki: Log aggregation
    - Tempo: Distributed tracing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config

        # Initialize storage backends
        self.victoriametrics: Optional[VictoriaMetricsStorage] = None
        self.loki: Optional[LokiStorage] = None
        self.tempo: Optional[TempoStorage] = None

        # In-memory key/value store for lightweight persistence used by
        # managers such as data_lineage, feature_flag, and plugin_marketplace.
        self._memory_store: Dict[str, Any] = {}

        self._is_initialized = False

    def initialize(self) -> bool:
        """Initialize all enabled storage backends"""
        try:
            # Initialize VictoriaMetrics if enabled
            if self.config.get("victoriametrics", {}).get("enabled", False):
                self.victoriametrics = VictoriaMetricsStorage(
                    self.config.get("victoriametrics", {})
                )
                if self.victoriametrics.initialize():
                    logger.info("VictoriaMetrics storage backend initialized")
                else:
                    logger.warning("Failed to initialize VictoriaMetrics")

            # Initialize Loki if enabled
            if self.config.get("loki", {}).get("enabled", False):
                self.loki = LokiStorage(self.config.get("loki", {}))
                if self.loki.initialize():
                    logger.info("Loki storage backend initialized")
                else:
                    logger.warning("Failed to initialize Loki")

            # Initialize Tempo if enabled
            if self.config.get("tempo", {}).get("enabled", False):
                self.tempo = TempoStorage(self.config.get("tempo", {}))
                if self.tempo.initialize():
                    logger.info("Tempo storage backend initialized")
                else:
                    logger.warning("Failed to initialize Tempo")

            self._is_initialized = True
            logger.info("L4 Storage Manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize L4 Storage Manager: {e}")
            return False

    def get_victoriametrics(self) -> Optional[VictoriaMetricsStorage]:
        """Get VictoriaMetrics storage backend"""
        return self.victoriametrics

    def get_loki(self) -> Optional[LokiStorage]:
        """Get Loki storage backend"""
        return self.loki

    def get_tempo(self) -> Optional[TempoStorage]:
        """Get Tempo storage backend"""
        return self.tempo

    def get_status(self) -> Dict[str, Any]:
        """Get status of all storage backends"""
        return {
            "initialized": self._is_initialized,
            "victoriametrics": self.victoriametrics.get_status() if self.victoriametrics else None,
            "loki": self.loki.get_status() if self.loki else None,
            "tempo": self.tempo.get_status() if self.tempo else None,
        }

    def load(self, key: str, default: Any = None) -> Any:
        """Load a value from the in-memory store.

        This lightweight key/value API is used by core managers (data lineage,
        feature flags, plugin marketplace) that expect ``storage.load`` while the
        persistent backend (VictoriaMetrics/Loki/Tempo) is not configured.
        """
        return self._memory_store.get(key, default)

    def save(self, key: str, value: Any) -> bool:
        """Save a value to the in-memory store.

        Returns True on success, False if an error occurred.
        """
        try:
            self._memory_store[key] = value
            return True
        except Exception as exc:
            logger.error(f"Failed to save key '{key}' to L4 in-memory store: {exc}")
            return False

    def close(self) -> None:
        """Close all storage backends"""
        try:
            if self.victoriametrics:
                self.victoriametrics.close()
            if self.loki:
                self.loki.close()
            if self.tempo:
                self.tempo.close()

            self._is_initialized = False
            logger.info("L4 Storage Manager closed")

        except Exception as e:
            logger.error(f"Error closing L4 Storage Manager: {e}")


# Global singleton instance
_l4_storage_manager: Optional[L4StorageManager] = None


def get_l4_storage_manager() -> Optional[L4StorageManager]:
    """Get global L4 Storage Manager instance"""
    return _l4_storage_manager


def init_l4_storage_manager(config: Dict[str, Any]) -> L4StorageManager:
    """Initialize global L4 Storage Manager"""
    global _l4_storage_manager
    _l4_storage_manager = L4StorageManager(config)
    _l4_storage_manager.initialize()
    return _l4_storage_manager
