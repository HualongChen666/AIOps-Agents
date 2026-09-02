# -*- coding: utf-8 -*-
"""
Rollback Script for Database Monitoring Module
================================================

This script handles the rollback of the database monitoring module migration.
It removes all database monitoring related data and schema changes.

Features:
- Safe rollback with confirmation prompt
- Data backup before deletion
- Transaction rollback on error
- Comprehensive logging
- Validation of rollback completion
"""

import asyncio
import logging
import sys
from typing import Optional

# Add parent directory to path
sys.path.insert(0, "..")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from loguru import logger

from config import DATABASE_URL
from core.repositories.database_monitoring_repository import DatabaseMonitoringRepository


# Configure logging
logging.basicConfig(level=logging.INFO)
logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")


class DatabaseMonitoringRollback:
    """Rollback handler for database monitoring module"""

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

    async def backup_data(self, db: AsyncSession) -> dict:
        """Backup existing data before deletion"""
        repo = DatabaseMonitoringRepository(db)

        config = await repo.get_config()
        thresholds = await repo.get_all_thresholds()
        baselines = await repo.get_all_baselines()
        alert_rules = await repo.get_all_alert_rules()
        status = await repo.get_status()

        backup = {
            "config": {
                "exists": config is not None,
                "data": config.__dict__ if config else None
            },
            "thresholds": {
                "count": len(thresholds),
                "data": [t.__dict__ for t in thresholds]
            },
            "baselines": {
                "count": len(baselines),
                "data": [b.__dict__ for b in baselines]
            },
            "alert_rules": {
                "count": len(alert_rules),
                "data": [r.__dict__ for r in alert_rules]
            },
            "status": {
                "exists": status is not None,
                "data": status.__dict__ if status else None
            },
        }

        logger.info(f"Data backup completed: {len(thresholds)} thresholds, {len(alert_rules)} alert rules")
        return backup

    async def drop_tables(self, db: AsyncSession) -> bool:
        """Drop database monitoring tables"""
        tables = [
            "database_monitoring_status",
            "database_alert_rules",
            "database_performance_baselines",
            "database_monitoring_configs",
            "database_metric_thresholds",
        ]

        try:
            for table in tables:
                try:
                    await db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"Failed to drop table {table}: {e}")

            await db.commit()
            logger.info("All database monitoring tables dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            await db.rollback()
            return False

    async def validate_rollback(self, db: AsyncSession) -> bool:
        """Validate that rollback was successful"""
        repo = DatabaseMonitoringRepository(db)

        config = await repo.get_config()
        thresholds = await repo.get_all_thresholds()
        baselines = await repo.get_all_baselines()
        alert_rules = await repo.get_all_alert_rules()
        status = await repo.get_status()

        validation_passed = True

        if config:
            logger.error("Validation failed: Monitoring configuration still exists")
            validation_passed = False
        else:
            logger.info("Validation passed: Monitoring configuration removed")

        if len(thresholds) > 0:
            logger.error("Validation failed: Metric thresholds still exist")
            validation_passed = False
        else:
            logger.info("Validation passed: Metric thresholds removed")

        if len(baselines) > 0:
            logger.error("Validation failed: Performance baselines still exist")
            validation_passed = False
        else:
            logger.info("Validation passed: Performance baselines removed")

        if len(alert_rules) > 0:
            logger.error("Validation failed: Alert rules still exist")
            validation_passed = False
        else:
            logger.info("Validation passed: Alert rules removed")

        if status:
            logger.error("Validation failed: Monitoring status still exists")
            validation_passed = False
        else:
            logger.info("Validation passed: Monitoring status removed")

        return validation_passed

    async def run_rollback(self, force: bool = False) -> bool:
        """Run the complete rollback process"""
        logger.info("=" * 60)
        logger.info("Starting Database Monitoring Rollback")
        logger.info("=" * 60)

        # Confirmation prompt
        if not force:
            response = input("This will delete all database monitoring data. Are you sure? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Rollback cancelled by user")
                return False

        try:
            await self.initialize()

            async with self.async_session() as db:
                # Backup existing data
                logger.info("Backing up existing data...")
                backup = await self.backup_data(db)

                # Log backup summary
                logger.info(f"Backup summary:")
                logger.info(f"  - Config: {'exists' if backup['config']['exists'] else 'none'}")
                logger.info(f"  - Thresholds: {backup['thresholds']['count']}")
                logger.info(f"  - Baselines: {backup['baselines']['count']}")
                logger.info(f"  - Alert Rules: {backup['alert_rules']['count']}")
                logger.info(f"  - Status: {'exists' if backup['status']['exists'] else 'none'}")

                # Drop tables
                logger.info("Dropping database monitoring tables...")
                if not await self.drop_tables(db):
                    raise Exception("Failed to drop tables")

                # Validate rollback
                logger.info("Validating rollback...")
                if not await self.validate_rollback(db):
                    raise Exception("Rollback validation failed")

                logger.info("=" * 60)
                logger.info("Rollback completed successfully")
                logger.info("=" * 60)
                logger.info("Note: To restore the database schema, run:")
                logger.info("  alembic downgrade 018")
                return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            logger.error("Transaction will be rolled back")
            return False
        finally:
            await self.close()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Rollback database monitoring module")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    db_url = DATABASE_URL
    logger.info(f"Using database URL: {db_url}")

    rollback = DatabaseMonitoringRollback(db_url)
    success = await rollback.run_rollback(force=args.force)

    if success:
        logger.info("Rollback completed successfully")
        sys.exit(0)
    else:
        logger.error("Rollback failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
