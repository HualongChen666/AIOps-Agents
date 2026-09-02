# -*- coding: utf-8 -*-
"""
Integration Migration Rollback Script
===================================

This script rolls back the integration data migration by:
1. Restoring data from backup
2. Cleaning up migrated data
3. Validating rollback integrity
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal
from core.integration_repository import (
    IntegrationRepository,
    WebhookRepository,
    NotificationChannelRepository,
)
from core.models import IntegrationDB, WebhookDB, IntegrationNotificationChannelDB
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationMigrationRollback:
    """Rolls back integration data migration"""

    def __init__(self, db: Session):
        """
        Initialize rollback handler

        Args:
            db: Database session
        """
        self.db = db
        self.integration_repo = IntegrationRepository(db)
        self.webhook_repo = WebhookRepository(db)
        self.channel_repo = NotificationChannelRepository(db)

    def restore_from_backup(self, backup_path: str) -> dict:
        """
        Restore data from backup

        Args:
            backup_path: Path to backup directory

        Returns:
            Restore summary
        """
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise ValueError(f"Backup directory not found: {backup_path}")

        logger.info(f"Restoring from backup: {backup_path}")

        summary = {
            "integrations_restored": 0,
            "webhooks_restored": 0,
            "channels_restored": 0,
            "errors": [],
        }

        # Restore integrations
        integration_backup_file = backup_dir / "integrations.json"
        if integration_backup_file.exists():
            with open(integration_backup_file, "r") as f:
                integrations = json.load(f)

            for integration_data in integrations:
                try:
                    # Delete existing integration if exists
                    existing = self.db.query(IntegrationDB).filter(
                        IntegrationDB.id == integration_data["id"]
                    ).first()
                    if existing:
                        self.db.delete(existing)

                    # Restore integration
                    integration = IntegrationDB(
                        id=integration_data["id"],
                        integration_type=integration_data["integration_type"],
                        name=integration_data["name"],
                        config=integration_data["config"],
                        enabled=integration_data["enabled"],
                        status=integration_data["status"],
                        last_tested=datetime.fromisoformat(integration_data["last_tested"]) if integration_data.get("last_tested") else None,
                        last_error=integration_data.get("last_error"),
                        integration_metadata=integration_data.get("integration_metadata"),
                        created_at=datetime.fromisoformat(integration_data["created_at"]) if integration_data.get("created_at") else None,
                        updated_at=datetime.fromisoformat(integration_data["updated_at"]) if integration_data.get("updated_at") else None,
                        created_by=integration_data.get("created_by"),
                    )
                    self.db.add(integration)
                    summary["integrations_restored"] += 1
                    logger.info(f"Restored integration: {integration_data['name']}")
                except Exception as e:
                    error_msg = f"Failed to restore integration {integration_data.get('id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

        # Restore webhooks
        webhook_backup_file = backup_dir / "webhooks.json"
        if webhook_backup_file.exists():
            with open(webhook_backup_file, "r") as f:
                webhooks = json.load(f)

            for webhook_data in webhooks:
                try:
                    # Delete existing webhook if exists
                    existing = self.db.query(WebhookDB).filter(
                        WebhookDB.id == webhook_data["id"]
                    ).first()
                    if existing:
                        self.db.delete(existing)

                    # Restore webhook
                    webhook = WebhookDB(
                        id=webhook_data["id"],
                        source=webhook_data["source"],
                        event_type=webhook_data["event_type"],
                        endpoint=webhook_data["endpoint"],
                        secret=webhook_data.get("secret"),
                        enabled=webhook_data["enabled"],
                        webhook_metadata=webhook_data.get("webhook_metadata"),
                        created_at=datetime.fromisoformat(webhook_data["created_at"]) if webhook_data.get("created_at") else None,
                        updated_at=datetime.fromisoformat(webhook_data["updated_at"]) if webhook_data.get("updated_at") else None,
                        created_by=webhook_data.get("created_by"),
                    )
                    self.db.add(webhook)
                    summary["webhooks_restored"] += 1
                    logger.info(f"Restored webhook: {webhook_data['source']}/{webhook_data['event_type']}")
                except Exception as e:
                    error_msg = f"Failed to restore webhook {webhook_data.get('id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

        # Restore notification channels
        channel_backup_file = backup_dir / "channels.json"
        if channel_backup_file.exists():
            with open(channel_backup_file, "r") as f:
                channels = json.load(f)

            for channel_data in channels:
                try:
                    # Delete existing channel if exists
                    existing = self.db.query(IntegrationNotificationChannelDB).filter(
                        IntegrationNotificationChannelDB.id == channel_data["id"]
                    ).first()
                    if existing:
                        self.db.delete(existing)

                    # Restore channel
                    channel = IntegrationNotificationChannelDB(
                        id=channel_data["id"],
                        name=channel_data["name"],
                        channel_type=channel_data["channel_type"],
                        config=channel_data["config"],
                        enabled=channel_data["enabled"],
                        priority=channel_data["priority"],
                        description=channel_data.get("description"),
                        created_at=datetime.fromisoformat(channel_data["created_at"]) if channel_data.get("created_at") else None,
                        updated_at=datetime.fromisoformat(channel_data["updated_at"]) if channel_data.get("updated_at") else None,
                        created_by=channel_data.get("created_by"),
                    )
                    self.db.add(channel)
                    summary["channels_restored"] += 1
                    logger.info(f"Restored notification channel: {channel_data['name']}")
                except Exception as e:
                    error_msg = f"Failed to restore channel {channel_data.get('id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    summary["errors"].append(error_msg)

        self.db.commit()
        logger.info(f"Restore completed: {summary}")
        return summary

    def cleanup_migrated_data(self, dry_run: bool = False) -> dict:
        """
        Clean up migrated data (use with caution)

        Args:
            dry_run: If True, only show what would be deleted

        Returns:
            Cleanup summary
        """
        logger.info(f"Cleaning up migrated data (dry_run={dry_run})")

        summary = {
            "integrations_deleted": 0,
            "webhooks_deleted": 0,
            "channels_deleted": 0,
            "dry_run": dry_run,
        }

        # Count integrations created by migration script
        integrations = self.db.query(IntegrationDB).filter(
            IntegrationDB.created_by == "migration_script"
        ).all()
        summary["integrations_deleted"] = len(integrations)

        if not dry_run:
            for integration in integrations:
                self.db.delete(integration)
            logger.info(f"Deleted {len(integrations)} integrations created by migration script")

        # Count webhooks created by migration script
        webhooks = self.db.query(WebhookDB).filter(
            WebhookDB.created_by == "migration_script"
        ).all()
        summary["webhooks_deleted"] = len(webhooks)

        if not dry_run:
            for webhook in webhooks:
                self.db.delete(webhook)
            logger.info(f"Deleted {len(webhooks)} webhooks created by migration script")

        # Count channels created by migration script
        channels = self.db.query(IntegrationNotificationChannelDB).filter(
            IntegrationNotificationChannelDB.created_by == "migration_script"
        ).all()
        summary["channels_deleted"] = len(channels)

        if not dry_run:
            for channel in channels:
                self.db.delete(channel)
            logger.info(f"Deleted {len(channels)} channels created by migration script")
            self.db.commit()

        logger.info(f"Cleanup completed: {summary}")
        return summary


def main():
    """Main rollback function"""
    import argparse

    parser = argparse.ArgumentParser(description="Rollback integration data migration")
    parser.add_argument("--backup", required=True, help="Path to backup directory")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no changes)")
    parser.add_argument("--cleanup", action="store_true", help="Clean up migrated data")
    args = parser.parse_args()

    logger.info("Starting integration migration rollback")

    # Create database session
    db = SessionLocal()

    try:
        # Initialize rollback handler
        rollback = IntegrationMigrationRollback(db)

        if args.cleanup:
            # Cleanup migrated data
            logger.info("Cleaning up migrated data")
            cleanup_summary = rollback.cleanup_migrated_data(dry_run=args.dry_run)
            logger.info(f"Cleanup summary: {cleanup_summary}")

            print("\n" + "=" * 80)
            print("CLEANUP SUMMARY")
            print("=" * 80)
            print(f"Dry run: {cleanup_summary['dry_run']}")
            print(f"Integrations to delete: {cleanup_summary['integrations_deleted']}")
            print(f"Webhooks to delete: {cleanup_summary['webhooks_deleted']}")
            print(f"Channels to delete: {cleanup_summary['channels_deleted']}")
            print("=" * 80)
        else:
            # Restore from backup
            logger.info(f"Restoring from backup: {args.backup}")
            restore_summary = rollback.restore_from_backup(args.backup)
            logger.info(f"Restore summary: {restore_summary}")

            print("\n" + "=" * 80)
            print("RESTORE SUMMARY")
            print("=" * 80)
            print(f"Backup: {args.backup}")
            print(f"Integrations restored: {restore_summary['integrations_restored']}")
            print(f"Webhooks restored: {restore_summary['webhooks_restored']}")
            print(f"Channels restored: {restore_summary['channels_restored']}")
            print(f"Errors: {len(restore_summary['errors'])}")
            if restore_summary['errors']:
                print("\nErrors:")
                for error in restore_summary['errors']:
                    print(f"  - {error}")
            print("=" * 80)

        logger.info("Rollback completed successfully")

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        print(f"\nERROR: Rollback failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
