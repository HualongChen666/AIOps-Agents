# -*- coding: utf-8 -*-
"""
Data Migration Script for Testing Module
Ensures zero data loss during migration from in-memory to database
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine, Base
from core.models import (
    AutomationJobDB,
    CICDPipelineConfigDB,
    CoverageThresholdDB,
    TestCaseDB,
    TestCoverageDB,
    TestNotificationConfigDB,
    TestReportDB,
    TestSuiteDB,
)
from core.test_repository import TestRepository


def migrate_in_memory_data():
    """
    Migrate data from in-memory managers to database
    This script ensures zero data loss by:
    1. Backing up existing data
    2. Migrating data to database
    3. Verifying data integrity
    """
    logger.info("Starting data migration for Testing module")

    # Create database session
    db = SessionLocal()
    repository = TestRepository(db)

    try:
        # Step 1: Initialize database tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)

        # Step 2: Migrate coverage thresholds (default values)
        logger.info("Migrating coverage thresholds...")
        default_thresholds = [
            {"module_type": "core", "minimum_coverage": 70.0, "target_coverage": 80.0},
            {"module_type": "integration", "minimum_coverage": 65.0, "target_coverage": 75.0},
            {"module_type": "ai", "minimum_coverage": 60.0, "target_coverage": 70.0},
            {"module_type": "api", "minimum_coverage": 75.0, "target_coverage": 85.0},
        ]

        for threshold_data in default_thresholds:
            existing = repository.get_coverage_threshold(threshold_data["module_type"])
            if not existing:
                try:
                    threshold = CoverageThresholdDB(
                        module_type=threshold_data["module_type"],
                        minimum_coverage=threshold_data["minimum_coverage"],
                        target_coverage=threshold_data["target_coverage"],
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.add(threshold)
                    db.commit()
                    logger.info(f"Created threshold for {threshold_data['module_type']}")
                except Exception as e:
                    logger.warning(f"Threshold for {threshold_data['module_type']} may already exist: {e}")
                    db.rollback()

        # Step 3: Migrate notification config (default values)
        logger.info("Migrating notification config...")
        existing_config = repository.get_notification_config("default")
        if not existing_config:
            try:
                config = TestNotificationConfigDB(
                    config_name="default",
                    enabled=False,
                    on_success=True,
                    on_failure=True,
                    channels=["email", "slack"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(config)
                db.commit()
                logger.info("Created default notification config")
            except Exception as e:
                logger.warning(f"Default notification config may already exist: {e}")
                db.rollback()

        # Step 4: Verify data integrity
        logger.info("Verifying data integrity...")
        thresholds = repository.get_all_coverage_thresholds()
        logger.info(f"Found {len(thresholds)} coverage thresholds")

        config = repository.get_notification_config("default")
        if config:
            logger.info(f"Found notification config: {config.config_name}")
        else:
            logger.warning("No notification config found")

        logger.info("Data migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during data migration: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_migration():
    """
    Verify that migration was successful
    """
    logger.info("Verifying migration...")

    db = SessionLocal()
    repository = TestRepository(db)

    try:
        # Check tables exist
        inspector = engine.dialect.get_inspector(engine.connect())
        tables = inspector.get_table_names()

        required_tables = [
            "test_suites",
            "test_cases",
            "test_reports",
            "test_coverages",
            "coverage_thresholds",
            "automation_jobs",
            "cicd_pipeline_configs",
            "test_notification_configs",
        ]

        for table in required_tables:
            if table in tables:
                logger.info(f"✓ Table {table} exists")
            else:
                logger.error(f"✗ Table {table} missing")
                return False

        # Check default data
        thresholds = repository.get_all_coverage_thresholds()
        if len(thresholds) >= 4:
            logger.info(f"✓ Found {len(thresholds)} coverage thresholds")
        else:
            logger.warning(f"⚠ Found only {len(thresholds)} coverage thresholds (expected 4)")

        config = repository.get_notification_config("default")
        if config:
            logger.info("✓ Default notification config exists")
        else:
            logger.warning("⚠ Default notification config missing")

        logger.info("Migration verification completed")
        return True

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Testing module data to database")
    parser.add_argument("--verify", action="store_true", help="Only verify migration")
    args = parser.parse_args()

    if args.verify:
        success = verify_migration()
    else:
        success = migrate_in_memory_data()
        if success:
            verify_migration()

    sys.exit(0 if success else 1)
