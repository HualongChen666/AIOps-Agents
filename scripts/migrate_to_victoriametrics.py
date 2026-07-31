#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Migration Script: SQLite to VictoriaMetrics
Migrates historical metrics data from SQLite to VictoriaMetrics
"""

import argparse
import ast
import asyncio
import os
import sqlite3
import sys
from typing import Any, Dict, List

from loguru import logger

from core.metrics_converter import MetricsConverter
from core.storage.l4.storage_manager import init_l4_storage_manager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MetricsMigrator:
    """Migrates metrics from SQLite to VictoriaMetrics"""

    def __init__(
        self,
        sqlite_path: str = "data/aiops.sqlite",
        victoria_metrics_url: str = "http://localhost:8428",
        batch_size: int = 1000,
    ):
        """
        Initialize migrator

        Args:
            sqlite_path: Path to SQLite database
            victoria_metrics_url: VictoriaMetrics URL
            batch_size: Number of metrics to migrate per batch
        """
        self.sqlite_path = sqlite_path
        self.victoria_metrics_url = victoria_metrics_url
        self.batch_size = batch_size
        self.vm_storage = None

        self._stats = {"total_read": 0, "total_written": 0, "failed": 0, "batches": 0}

    async def initialize(self) -> bool:
        """Initialize VictoriaMetrics storage"""
        try:
            config = {"victoriametrics": {"enabled": True, "base_url": self.victoria_metrics_url}}

            manager = init_l4_storage_manager(config)
            self.vm_storage = manager.get_victoriametrics()

            if self.vm_storage and self.vm_storage.initialize():
                logger.info(f"VictoriaMetrics initialized: {self.victoria_metrics_url}")
                return True
            else:
                logger.error("Failed to initialize VictoriaMetrics")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize migrator: {e}")
            return False

    def read_sqlite_metrics(self) -> List[Dict[str, Any]]:
        """
        Read all metrics from SQLite database

        Returns:
            List of metric dictionaries
        """
        metrics = []

        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # Query all metrics (adjust table name as needed)
            # This is a default_value - actual query depends on database schema
            cursor.execute("SELECT name, value, labels, timestamp FROM metrics")

            rows = cursor.fetchall()
            for row in rows:
                metrics.append(
                    {
                        "name": row[0],
                        "value": row[1],
                        "labels": ast.literal_eval(row[2]) if isinstance(row[2], str) else row[2],
                        "timestamp": row[3],
                    }
                )

            conn.close()
            logger.info(f"Read {len(metrics)} metrics from SQLite")
            self._stats["total_read"] = len(metrics)
            return metrics

        except Exception as e:
            logger.error(f"Failed to read from SQLite: {e}")
            return []

    async def migrate_batch(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Migrate a batch of metrics to VictoriaMetrics

        Args:
            metrics: List of metric dictionaries

        Returns:
            True if migration succeeded
        """
        if not metrics:
            return True

        try:
            # Convert to Prometheus format
            prometheus_data = MetricsConverter.batch_sqlite_to_prometheus(metrics)

            # Write to VictoriaMetrics
            result = await self.vm_storage.store(
                "metrics_batch", prometheus_data, {"format": "prometheus"}
            )

            if result:
                self._stats["total_written"] += len(metrics)
                self._stats["batches"] += 1
                logger.debug(f"Migrated batch of {len(metrics)} metrics")
            else:
                self._stats["failed"] += len(metrics)
                logger.warning(f"Failed to migrate batch of {len(metrics)} metrics")

            return result

        except Exception as e:
            logger.error(f"Failed to migrate batch: {e}")
            self._stats["failed"] += len(metrics)
            return False

    async def migrate_all(self) -> Dict[str, Any]:
        """
        Migrate all metrics from SQLite to VictoriaMetrics

        Returns:
            Migration statistics
        """
        logger.info("Starting migration from SQLite to VictoriaMetrics")

        # Read all metrics from SQLite
        metrics = self.read_sqlite_metrics()

        if not metrics:
            logger.warning("No metrics found in SQLite database")
            return self._stats

        # Migrate in batches
        total_metrics = len(metrics)
        for i in range(0, total_metrics, self.batch_size):
            batch = metrics[i : i + self.batch_size]
            success = await self.migrate_batch(batch)

            if not success:
                logger.warning(f"Batch {i // self.batch_size + 1} failed")

            # Progress logging
            progress = min(i + self.batch_size, total_metrics)
            logger.info(f"Progress: {progress}/{total_metrics} metrics migrated")

        logger.info("Migration completed")
        logger.info(f"Statistics: {self._stats}")

        return self._stats

    def get_stats(self) -> Dict[str, Any]:
        """Get migration statistics"""
        return self._stats


async def main():
    """Main migration function"""

    parser = argparse.ArgumentParser(description="Migrate metrics from SQLite to VictoriaMetrics")
    parser.add_argument(
        "--sqlite-path", default="data/aiops.sqlite", help="Path to SQLite database"
    )
    parser.add_argument("--vm-url", default="http://localhost:8428", help="VictoriaMetrics URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for migration")

    args = parser.parse_args()

    # Initialize migrator
    migrator = MetricsMigrator(
        sqlite_path=args.sqlite_path, victoria_metrics_url=args.vm_url, batch_size=args.batch_size
    )

    # Initialize VictoriaMetrics
    if not await migrator.initialize():
        logger.error("Failed to initialize VictoriaMetrics")
        sys.exit(1)

    # Run migration
    stats = await migrator.migrate_all()

    # Print summary
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print(f"Total metrics read: {stats['total_read']}")
    print(f"Total metrics written: {stats['total_written']}")
    print(f"Failed: {stats['failed']}")
    print(f"Batches processed: {stats['batches']}")
    print("=" * 50)

    # Exit with error code if any failures
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
