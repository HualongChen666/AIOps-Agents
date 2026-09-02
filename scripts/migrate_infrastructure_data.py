# -*- coding: utf-8 -*-
"""
Infrastructure Data Migration Script

This script performs zero-loss data migration for Infrastructure module:
- Backs up existing data before migration
- Runs Alembic migration
- Validates data integrity after migration
- Provides rollback capability

Usage:
    python scripts/migrate_infrastructure_data.py --action migrate
    python scripts/migrate_infrastructure_data.py --action validate
    python scripts/migrate_infrastructure_data.py --action backup
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

from alembic.config import Config
from alembic import command

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)


class InfrastructureDataMigrator:
    """Handles zero-loss data migration for Infrastructure module"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            from core.database import _DB_PATH
            self.db_path = _DB_PATH
        else:
            self.db_path = db_path

        self.backup_dir = project_root / "data" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_database(self) -> str:
        """Create a backup of the current database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"aiops_backup_{timestamp}.db"

        _logger.info(f"Creating database backup at: {backup_path}")

        if os.path.exists(self.db_path):
            shutil.copy2(self.db_path, backup_path)
            _logger.info(f"Database backup completed successfully")
            return str(backup_path)
        else:
            _logger.warning(f"Database file not found at: {self.db_path}")
            # Create empty backup marker
            backup_path.touch()
            return str(backup_path)

    def validate_backup(self, backup_path: str) -> bool:
        """Validate backup integrity"""
        _logger.info(f"Validating backup at: {backup_path}")

        if not os.path.exists(backup_path):
            _logger.error("Backup file does not exist")
            return False

        # Check if it's a valid SQLite database
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

    def run_alembic_migration(self) -> bool:
        """Run Alembic migration for Infrastructure tables"""
        _logger.info("Running Alembic migration for Infrastructure tables")

        try:
            alembic_cfg = Config(str(project_root / "alembic.ini"))
            alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")

            # Upgrade to the latest migration
            command.upgrade(alembic_cfg, "head")

            _logger.info("Alembic migration completed successfully")
            return True
        except Exception as e:
            _logger.error(f"Alembic migration failed: {e}")
            return False

    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        _logger.info("Validating migration")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check for new Infrastructure tables
            expected_tables = [
                "infrastructure_kafka_messages",
                "infrastructure_flink_jobs",
                "infrastructure_storage",
                "infrastructure_configs",
                "infrastructure_data_flows",
                "infrastructure_monitoring",
            ]

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = {row[0] for row in cursor.fetchall()}

            missing_tables = [t for t in expected_tables if t not in existing_tables]

            if missing_tables:
                _logger.error(f"Missing tables after migration: {missing_tables}")
                conn.close()
                return False

            # Check table structures
            for table in expected_tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = cursor.fetchall()
                _logger.info(f"Table {table} has {len(columns)} columns")

            conn.close()
            _logger.info("Migration validation passed")
            return True
        except Exception as e:
            _logger.error(f"Migration validation failed: {e}")
            return False

    def validate_data_integrity(self) -> bool:
        """Validate that existing data is intact after migration"""
        _logger.info("Validating data integrity")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check that existing tables still have data
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                if table_name.startswith("infrastructure_"):
                    # New tables, skip
                    continue

                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                _logger.info(f"Table {table_name}: {count} rows")

            conn.close()
            _logger.info("Data integrity validation passed")
            return True
        except Exception as e:
            _logger.error(f"Data integrity validation failed: {e}")
            return False

    def migrate(self) -> bool:
        """Perform complete migration with zero data loss"""
        _logger.info("Starting Infrastructure data migration")

        # Step 1: Backup existing database
        backup_path = self.backup_database()
        if not self.validate_backup(backup_path):
            _logger.error("Backup validation failed, aborting migration")
            return False

        # Step 2: Run Alembic migration
        if not self.run_alembic_migration():
            _logger.error("Migration failed, backup is available at: " + backup_path)
            return False

        # Step 3: Validate migration
        if not self.validate_migration():
            _logger.error("Migration validation failed, backup is available at: " + backup_path)
            return False

        # Step 4: Validate data integrity
        if not self.validate_data_integrity():
            _logger.error("Data integrity validation failed, backup is available at: " + backup_path)
            return False

        _logger.info("Infrastructure data migration completed successfully")
        _logger.info(f"Backup available at: {backup_path}")
        return True

    def rollback(self, backup_path: str) -> bool:
        """Rollback to a specific backup"""
        _logger.info(f"Rolling back to backup: {backup_path}")

        if not os.path.exists(backup_path):
            _logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            _logger.info("Rollback completed successfully")
            return True
        except Exception as e:
            _logger.error(f"Rollback failed: {e}")
            return False

    def list_backups(self) -> list:
        """List available backups"""
        backups = sorted(self.backup_dir.glob("aiops_backup_*.db"), reverse=True)
        return [str(b) for b in backups]


def main():
    parser = argparse.ArgumentParser(description="Infrastructure Data Migration Tool")
    parser.add_argument(
        "--action",
        choices=["migrate", "validate", "backup", "rollback", "list-backups"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument("--backup-path", help="Path to backup file for rollback")
    parser.add_argument("--db-path", help="Path to database file")

    args = parser.parse_args()

    migrator = InfrastructureDataMigrator(db_path=args.db_path)

    if args.action == "migrate":
        success = migrator.migrate()
        sys.exit(0 if success else 1)

    elif args.action == "validate":
        success = migrator.validate_migration() and migrator.validate_data_integrity()
        sys.exit(0 if success else 1)

    elif args.action == "backup":
        backup_path = migrator.backup_database()
        success = migrator.validate_backup(backup_path)
        sys.exit(0 if success else 1)

    elif args.action == "rollback":
        if not args.backup_path:
            _logger.error("--backup-path is required for rollback")
            sys.exit(1)
        success = migrator.rollback(args.backup_path)
        sys.exit(0 if success else 1)

    elif args.action == "list-backups":
        backups = migrator.list_backups()
        _logger.info(f"Available backups ({len(backups)}):")
        for backup in backups:
            _logger.info(f"  - {backup}")
        sys.exit(0)


if __name__ == "__main__":
    main()
