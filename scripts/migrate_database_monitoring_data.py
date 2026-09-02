# -*- coding: utf-8 -*-
"""
Data Migration Script for Database Monitoring Module
====================================================

This script handles the migration of database monitoring data from in-memory storage
to persistent database storage. Since the previous implementation used in-memory storage,
this script initializes the database with default data and ensures data consistency.

Features:
- Zero data loss guarantee (no existing data to lose from in-memory storage)
- Data consistency validation
- Transaction rollback on error
- Comprehensive logging
- Batch processing for performance
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, "..")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from config import DATABASE_URL
from core.db_engine import get_db
from core.repositories.database_monitoring_repository import DatabaseMonitoringRepository
from core.models import (
    DatabaseMetricThresholdDB,
    DatabaseMonitoringConfigDB,
    DatabasePerformanceBaselineDB,
    DatabaseAlertRuleDB,
    DatabaseMonitoringStatusDB,
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")


class DatabaseMonitoringDataMigrator:
    """Data migrator for database monitoring module"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine = None
        self.async_session = None

    async def initialize(self):
        """Initialize database connection"""
        self.engine = create_async_engine(self.db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Database connection initialized")

    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
        logger.info("Database connection closed")

    async def check_existing_data(self, db: AsyncSession) -> dict:
        """Check if data already exists in the database"""
        repo = DatabaseMonitoringRepository(db)

        config = await repo.get_config()
        thresholds = await repo.get_all_thresholds()
        baselines = await repo.get_all_baselines()
        alert_rules = await repo.get_all_alert_rules()
        status = await repo.get_status()

        return {
            "config_exists": config is not None,
            "thresholds_count": len(thresholds),
            "baselines_count": len(baselines),
            "alert_rules_count": len(alert_rules),
            "status_exists": status is not None,
        }

    async def migrate_default_config(self, db: AsyncSession) -> bool:
        """Migrate default monitoring configuration"""
        repo = DatabaseMonitoringRepository(db)

        # Check if config already exists
        existing = await repo.get_config()
        if existing:
            logger.info("Monitoring configuration already exists, skipping")
            return True

        # Create default configuration
        try:
            config = await repo.create_config(
                enabled=True,
                collection_interval=60,
                retention_days=30,
                enable_realtime=True,
                enable_slow_query_log=True,
                slow_query_threshold=1.0,
                enable_connection_monitoring=True,
                max_connections_threshold=100,
                enable_deadlock_detection=True,
                updated_by="migration_script",
            )
            logger.info(f"Default monitoring configuration created: id={config.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
            return False

    async def migrate_default_thresholds(self, db: AsyncSession) -> bool:
        """Migrate default metric thresholds"""
        repo = DatabaseMonitoringRepository(db)

        # Check if thresholds already exist
        existing = await repo.get_all_thresholds()
        if existing:
            logger.info(f"Metric thresholds already exist ({len(existing)}), skipping")
            return True

        # Default thresholds
        default_thresholds = [
            {
                "metric_type": "query_time",
                "warning_threshold": 100.0,
                "critical_threshold": 500.0,
                "enabled": True,
                "description": "查询时间阈值"
            },
            {
                "metric_type": "connection_count",
                "warning_threshold": 80.0,
                "critical_threshold": 95.0,
                "enabled": True,
                "description": "连接数阈值"
            },
            {
                "metric_type": "cache_hit_ratio",
                "warning_threshold": 0.8,
                "critical_threshold": 0.5,
                "enabled": True,
                "description": "缓存命中率阈值"
            },
            {
                "metric_type": "slow_query_count",
                "warning_threshold": 10.0,
                "critical_threshold": 50.0,
                "enabled": True,
                "description": "慢查询数量阈值"
            },
        ]

        try:
            for threshold_data in default_thresholds:
                await repo.create_threshold(
                    metric_type=threshold_data["metric_type"],
                    warning_threshold=threshold_data["warning_threshold"],
                    critical_threshold=threshold_data["critical_threshold"],
                    enabled=threshold_data["enabled"],
                    description=threshold_data["description"],
                    created_by="migration_script",
                )
            logger.info(f"Default metric thresholds created: {len(default_thresholds)}")
            return True
        except Exception as e:
            logger.error(f"Failed to create default thresholds: {e}")
            return False

    async def migrate_default_alert_rules(self, db: AsyncSession) -> bool:
        """Migrate default alert rules"""
        repo = DatabaseMonitoringRepository(db)

        # Check if alert rules already exist
        existing = await repo.get_all_alert_rules()
        if existing:
            logger.info(f"Alert rules already exist ({len(existing)}), skipping")
            return True

        # Default alert rules
        default_rules = [
            {
                "rule_id": "slow_query_alert",
                "rule_name": "慢查询告警",
                "metric_type": "query_time",
                "condition": "query_time > 500",
                "severity": "warning",
                "enabled": True,
                "notification_channels": ["email", "slack"],
                "cooldown_minutes": 5,
                "description": "当查询时间超过500ms时触发告警"
            },
            {
                "rule_id": "connection_alert",
                "rule_name": "连接数告警",
                "metric_type": "connection_count",
                "condition": "connection_count > 90",
                "severity": "error",
                "enabled": True,
                "notification_channels": ["email", "slack"],
                "cooldown_minutes": 10,
                "description": "当连接数超过90时触发告警"
            },
            {
                "rule_id": "deadlock_alert",
                "rule_name": "死锁告警",
                "metric_type": "deadlock_count",
                "condition": "deadlock_count > 0",
                "severity": "critical",
                "enabled": True,
                "notification_channels": ["email", "slack", "pagerduty"],
                "cooldown_minutes": 1,
                "description": "当检测到死锁时立即触发告警"
            },
        ]

        try:
            for rule_data in default_rules:
                await repo.create_alert_rule(
                    rule_id=rule_data["rule_id"],
                    rule_name=rule_data["rule_name"],
                    metric_type=rule_data["metric_type"],
                    condition=rule_data["condition"],
                    severity=rule_data["severity"],
                    enabled=rule_data["enabled"],
                    notification_channels=rule_data["notification_channels"],
                    cooldown_minutes=rule_data["cooldown_minutes"],
                    description=rule_data["description"],
                    created_by="migration_script",
                )
            logger.info(f"Default alert rules created: {len(default_rules)}")
            return True
        except Exception as e:
            logger.error(f"Failed to create default alert rules: {e}")
            return False

    async def migrate_default_status(self, db: AsyncSession) -> bool:
        """Migrate default monitoring status"""
        repo = DatabaseMonitoringRepository(db)

        # Check if status already exists
        existing = await repo.get_status()
        if existing:
            logger.info("Monitoring status already exists, skipping")
            return True

        # Create default status
        try:
            status = await repo.create_status(
                monitoring_enabled=True,
                active_alerts=0,
                total_metrics_collected=0,
                database_health="healthy",
                uptime_percentage=100.0,
            )
            logger.info(f"Default monitoring status created: id={status.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create default status: {e}")
            return False

    async def validate_migration(self, db: AsyncSession) -> bool:
        """Validate that migration was successful"""
        repo = DatabaseMonitoringRepository(db)

        config = await repo.get_config()
        thresholds = await repo.get_all_thresholds()
        alert_rules = await repo.get_all_alert_rules()
        status = await repo.get_status()

        validation_passed = True

        if not config:
            logger.error("Validation failed: No monitoring configuration found")
            validation_passed = False
        else:
            logger.info(f"Validation passed: Monitoring configuration exists (id={config.id})")

        if len(thresholds) == 0:
            logger.error("Validation failed: No metric thresholds found")
            validation_passed = False
        else:
            logger.info(f"Validation passed: {len(thresholds)} metric thresholds found")

        if len(alert_rules) == 0:
            logger.error("Validation failed: No alert rules found")
            validation_passed = False
        else:
            logger.info(f"Validation passed: {len(alert_rules)} alert rules found")

        if not status:
            logger.error("Validation failed: No monitoring status found")
            validation_passed = False
        else:
            logger.info(f"Validation passed: Monitoring status exists (id={status.id})")

        return validation_passed

    async def run_migration(self) -> bool:
        """Run the complete migration process"""
        logger.info("=" * 60)
        logger.info("Starting Database Monitoring Data Migration")
        logger.info("=" * 60)

        try:
            await self.initialize()

            async with self.async_session() as db:
                # Check existing data
                logger.info("Checking existing data...")
                existing_data = await self.check_existing_data(db)
                logger.info(f"Existing data: {existing_data}")

                # If data already exists, skip migration
                if existing_data["config_exists"] and existing_data["thresholds_count"] > 0:
                    logger.info("Data already exists, skipping migration")
                    return True

                # Run migration in transaction
                async with db.begin():
                    logger.info("Starting migration transaction...")

                    # Migrate default configuration
                    if not await self.migrate_default_config(db):
                        raise Exception("Failed to migrate default configuration")

                    # Migrate default thresholds
                    if not await self.migrate_default_thresholds(db):
                        raise Exception("Failed to migrate default thresholds")

                    # Migrate default alert rules
                    if not await self.migrate_default_alert_rules(db):
                        raise Exception("Failed to migrate default alert rules")

                    # Migrate default status
                    if not await self.migrate_default_status(db):
                        raise Exception("Failed to migrate default status")

                    logger.info("Migration transaction completed successfully")

                # Validate migration
                logger.info("Validating migration...")
                if not await self.validate_migration(db):
                    raise Exception("Migration validation failed")

                logger.info("=" * 60)
                logger.info("Migration completed successfully")
                logger.info("=" * 60)
                return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            logger.error("Transaction will be rolled back")
            return False
        finally:
            await self.close()


async def main():
    """Main entry point"""
    db_url = DATABASE_URL
    logger.info(f"Using database URL: {db_url}")

    migrator = DatabaseMonitoringDataMigrator(db_url)
    success = await migrator.run_migration()

    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
