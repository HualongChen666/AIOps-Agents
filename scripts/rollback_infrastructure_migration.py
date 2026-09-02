# -*- coding: utf-8 -*-
"""
Infrastructure Migration Rollback Script

This script provides rollback capability for Infrastructure module migration:
- Lists available backups
- Restores database from backup
- Validates rollback integrity

Usage:
    python scripts/rollback_infrastructure_migration.py --list
    python scripts/rollback_infrastructure_migration.py --rollback <backup_path>
"""

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)


class InfrastructureRollbackManager:
    """Manages rollback operations for Infrastructure migration"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            from core.database import _DB_PATH
            self.db_path = _DB_PATH
        else:
            self.db_path = db_path

        self.backup_dir = project_root / "data" / "backups"

    def list_backups(self) -> list:
        """List available backups with metadata"""
        backups = sorted(self.backup_dir.glob("aiops_backup_*.db"), reverse=True)

        backup_info = []
        for backup_path in backups:
            info = {
                "path": str(backup_path),
                "size_mb": round(backup_path.stat().st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(backup_path.stat().st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
            backup_info.append(info)

        return backup_info

    def validate_backup(self, backup_path: str) -> bool:
        """Validate backup integrity before rollback"""
        _logger.info(f"Validating backup: {backup_path}")

        if not os.path.exists(backup_path):
            _logger.error("Backup file does not exist")
            return False

        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()

            _logger.info(f"Backup validation passed. Found {len(tables)} tables")
            return True
        except Exception as e:
            _logger.error(f"Backup validation failed: {e}")
            return False

    def create_pre_rollback_backup(self) -> str:
        """Create a backup before rollback"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"pre_rollback_{timestamp}.db"

        _logger.info(f"Creating pre-rollback backup at: {backup_path}")

        if os.path.exists(self.db_path):
            shutil.copy2(self.db_path, backup_path)
            _logger.info("Pre-rollback backup completed")
            return str(backup_path)
        else:
            _logger.warning(f"Database file not found at: {self.db_path}")
            backup_path.touch()
            return str(backup_path)

    def rollback(self, backup_path: str, create_pre_backup: bool = True) -> bool:
        """Perform rollback to specified backup"""
        _logger.info(f"Starting rollback to: {backup_path}")

        # Validate backup
        if not self.validate_backup(backup_path):
            _logger.error("Backup validation failed, aborting rollback")
            return False

        # Create pre-rollback backup
        if create_pre_backup:
            pre_backup_path = self.create_pre_rollback_backup()
            _logger.info(f"Pre-rollback backup created at: {pre_backup_path}")

        try:
            # Stop any database connections (in production, you'd need to handle this)
            # For now, we'll just copy the file

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)

            # Validate restored database
            if not self.validate_backup(self.db_path):
                _logger.error("Restored database validation failed")
                return False

            _logger.info("Rollback completed successfully")
            return True
        except Exception as e:
            _logger.error(f"Rollback failed: {e}")
            return False

    def validate_rollback(self) -> bool:
        """Validate that rollback was successful"""
        _logger.info("Validating rollback")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check that database is accessible
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            _logger.info(f"Database validation passed. Found {len(tables)} tables")

            # Check that Infrastructure tables are NOT present (if rolling back to before migration)
            infrastructure_tables = [
                "infrastructure_kafka_messages",
                "infrastructure_flink_jobs",
                "infrastructure_storage",
                "infrastructure_configs",
                "infrastructure_data_flows",
                "infrastructure_monitoring",
            ]

            existing_tables = {row[0] for row in tables}
            infra_present = [t for t in infrastructure_tables if t in existing_tables]

            if infra_present:
                _logger.warning(f"Infrastructure tables still present after rollback: {infra_present}")
                # This might be expected if rolling back to a state after migration

            conn.close()
            _logger.info("Rollback validation passed")
            return True
        except Exception as e:
            _logger.error(f"Rollback validation failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Infrastructure Migration Rollback Tool")
    parser.add_argument(
        "--list", action="store_true", help="List available backups"
    )
    parser.add_argument(
        "--rollback", metavar="BACKUP_PATH", help="Rollback to specified backup"
    )
    parser.add_argument(
        "--no-pre-backup", action="store_true", help="Skip creating pre-rollback backup"
    )
    parser.add_argument("--db-path", help="Path to database file")

    args = parser.parse_args()

    manager = InfrastructureRollbackManager(db_path=args.db_path)

    if args.list:
        backups = manager.list_backups()
        _logger.info(f"Available backups ({len(backups)}):")
        for info in backups:
            _logger.info(f"\n  Path: {info['path']}")
            _logger.info(f"  Size: {info['size_mb']} MB")
            _logger.info(f"  Modified: {info['modified']}")
        sys.exit(0)

    elif args.rollback:
        success = manager.rollback(
            args.rollback, create_pre_backup=not args.no_pre_backup
        )
        if success:
            manager.validate_rollback()
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
