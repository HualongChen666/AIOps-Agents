# -*- coding: utf-8 -*-
"""
Rollback Script for Testing Module Migration
Provides safe rollback in case of issues
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import engine


def rollback_migration():
    """
    Rollback the Testing module migration by dropping the new tables
    This is a safe operation that only affects the new testing tables
    """
    logger.warning("Starting rollback of Testing module migration")

    db = SessionLocal()

    try:
        # Tables to drop (in reverse order of creation to handle dependencies)
        tables_to_drop = [
            "testing_notification_configs",
            "testing_cicd_pipeline_configs",
            "testing_automation_jobs",
            "testing_coverage_thresholds",
            "testing_coverages",
            "testing_reports",
            "testing_cases",
            "testing_suites",
        ]

        # Drop each table
        for table_name in tables_to_drop:
            try:
                # Check if table exists
                inspector = engine.dialect.get_inspector(engine.connect())
                existing_tables = inspector.get_table_names()

                if table_name in existing_tables:
                    logger.info(f"Dropping table: {table_name}")
                    db.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    db.commit()
                    logger.info(f"✓ Dropped table: {table_name}")
                else:
                    logger.info(f"Table {table_name} does not exist, skipping")
            except Exception as e:
                logger.error(f"Error dropping table {table_name}: {e}")
                db.rollback()

        logger.warning("Rollback completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during rollback: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_rollback():
    """
    Verify that rollback was successful
    """
    logger.info("Verifying rollback...")

    try:
        inspector = engine.dialect.get_inspector(engine.connect())
        tables = inspector.get_table_names()

        testing_tables = [
            "testing_suites",
            "testing_cases",
            "testing_reports",
            "testing_coverages",
            "testing_coverage_thresholds",
            "testing_automation_jobs",
            "testing_cicd_pipeline_configs",
            "testing_notification_configs",
        ]

        all_dropped = True
        for table in testing_tables:
            if table in tables:
                logger.error(f"✗ Table {table} still exists")
                all_dropped = False
            else:
                logger.info(f"✓ Table {table} dropped")

        if all_dropped:
            logger.info("Rollback verification completed successfully")
            return True
        else:
            logger.error("Rollback verification failed: some tables still exist")
            return False

    except Exception as e:
        logger.error(f"Error during verification: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rollback Testing module migration")
    parser.add_argument("--verify", action="store_true", help="Only verify rollback")
    args = parser.parse_args()

    if args.verify:
        success = verify_rollback()
    else:
        logger.warning("WARNING: This will drop all Testing module tables!")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Rollback cancelled")
            sys.exit(0)

        success = rollback_migration()
        if success:
            verify_rollback()

    sys.exit(0 if success else 1)
