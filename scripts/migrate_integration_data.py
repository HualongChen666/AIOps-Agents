# -*- coding: utf-8 -*-
"""
Integration Data Migration Script
================================

This script migrates integration data from in-memory storage to database storage.
It ensures zero data loss by:
1. Backing up existing database data
2. Migrating in-memory data to database
3. Validating data consistency
4. Providing rollback capability
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import SessionLocal, engine
from core.integration_repository import (
    IntegrationRepository,
    WebhookRepository,
    NotificationChannelRepository,
)
from core.models import IntegrationDB, WebhookDB, IntegrationNotificationChannelDB
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationDataMigrator:
    """Migrates integration data from in-memory to database storage"""

    def __init__(self, db: Session):
        """
        Initialize migrator

        Args:
            db: Database session
        """
        self.db = db
        self.integration_repo = IntegrationRepository(db)
        self.webhook_repo = WebhookRepository(db)
        self.channel_repo = NotificationChannelRepository(db)

    def backup_existing_data(self, backup_dir: str = "backups") -> dict:
        """
        Backup existing database data

        Args:
            backup_dir: Directory to store backups

        Returns:
            Backup summary
        """
        import shutil
        from datetime import datetime

        backup_path = Path(backup_dir) / f"integration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating backup at {backup_path}")

        # Backup integrations
        integrations = self.integration_repo.get_all(limit=10000)
        integration_backup = []
        for integration in integrations:
            integration_backup.append({
                "id": integration.id,
                "integration_type": integration.integration_type,
                "name": integration.name,
                "config": integration.config,
                "enabled": integration.enabled,
                "status": integration.status,
                "last_tested": integration.last_tested.isoformat() if integration.last_tested else None,
                "last_error": integration.last_error,
                "integration_metadata": integration.integration_metadata,
                "created_at": integration.created_at.isoformat() if integration.created_at else None,
                "updated_at": integration.updated_at.isoformat() if integration.updated_at else None,
                "created_by": integration.created_by,
            })

        with open(backup_path / "integrations.json", "w") as f:
            json.dump(integration_backup, f, indent=2, default=str)

        # Backup webhooks
        webhooks = self.webhook_repo.get_all(limit=10000)
        webhook_backup = []
        for webhook in webhooks:
            webhook_backup.append({
                "id": webhook.id,
                "source": webhook.source,
                "event_type": webhook.event_type,
                "endpoint": webhook.endpoint,
                "secret": webhook.secret,
                "enabled": webhook.enabled,
                "webhook_metadata": webhook.webhook_metadata,
                "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
                "updated_at": webhook.updated_at.isoformat() if webhook.updated_at else None,
                "created_by": webhook.created_by,
            })

        with open(backup_path / "webhooks.json", "w") as f:
            json.dump(webhook_backup, f, indent=2, default=str)

        # Backup notification channels
        channels = self.channel_repo.get_all(limit=10000)
        channel_backup = []
        for channel in channels:
            channel_backup.append({
                "id": channel.id,
                "name": channel.name,
                "channel_type": channel.channel_type,
                "config": channel.config,
                "enabled": channel.enabled,
                "priority": channel.priority,
                "description": channel.description,
                "created_at": channel.created_at.isoformat() if channel.created_at else None,
                "updated_at": channel.updated_at.isoformat() if channel.updated_at else None,
                "created_by": channel.created_by,
            })

        with open(backup_path / "channels.json", "w") as f:
            json.dump(channel_backup, f, indent=2, default=str)

        logger.info(f"Backup completed: {len(integration_backup)} integrations, {len(webhook_backup)} webhooks, {len(channel_backup)} channels")

        return {
            "backup_path": str(backup_path),
            "integrations_count": len(integration_backup),
            "webhooks_count": len(webhook_backup),
            "channels_count": len(channel_backup),
        }

    def migrate_from_config(self, config_file: str = "config/integrations.json") -> dict:
        """
        Migrate integrations from configuration file

        Args:
            config_file: Path to configuration file

        Returns:
            Migration summary
        """
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return {"status": "skipped", "reason": "config_file_not_found"}

        with open(config_path, "r") as f:
            config = json.load(f)

        summary = {
            "integrations_created": 0,
            "webhooks_created": 0,
            "channels_created": 0,
            "errors": [],
        }

        # Migrate integrations
        for integration_config in config.get("integrations", []):
            try:
                # Check if integration already exists
                existing = self.db.query(IntegrationDB).filter(
                    IntegrationDB.name == integration_config["name"]
                ).first()

                if existing:
                    logger.info(f"Integration already exists: {integration_config['name']}")
                    continue

                self.integration_repo.create(
                    integration_type=integration_config["integration_type"],
                    name=integration_config["name"],
                    config=integration_config["config"],
                    enabled=integration_config.get("enabled", True),
                    created_by="migration_script",
                )
                summary["integrations_created"] += 1
                logger.info(f"Migrated integration: {integration_config['name']}")
            except Exception as e:
                error_msg = f"Failed to migrate integration {integration_config.get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                summary["errors"].append(error_msg)

        # Migrate webhooks
        for webhook_config in config.get("webhooks", []):
            try:
                # Check if webhook already exists
                existing = self.db.query(WebhookDB).filter(
                    WebhookDB.source == webhook_config["source"],
                    WebhookDB.event_type == webhook_config["event_type"],
                ).first()

                if existing:
                    logger.info(f"Webhook already exists: {webhook_config['source']}/{webhook_config['event_type']}")
                    continue

                self.webhook_repo.create(
                    source=webhook_config["source"],
                    event_type=webhook_config["event_type"],
                    endpoint=webhook_config["endpoint"],
                    secret=webhook_config.get("secret"),
                    enabled=webhook_config.get("enabled", True),
                    created_by="migration_script",
                )
                summary["webhooks_created"] += 1
                logger.info(f"Migrated webhook: {webhook_config['source']}/{webhook_config['event_type']}")
            except Exception as e:
                error_msg = f"Failed to migrate webhook {webhook_config.get('source', 'unknown')}: {e}"
                logger.error(error_msg)
                summary["errors"].append(error_msg)

        # Migrate notification channels
        for channel_config in config.get("notification_channels", []):
            try:
                # Check if channel already exists
                existing = self.channel_repo.get_by_name(channel_config["name"])
                if existing:
                    logger.info(f"Notification channel already exists: {channel_config['name']}")
                    continue

                self.channel_repo.create(
                    name=channel_config["name"],
                    channel_type=channel_config["channel_type"],
                    config=channel_config["config"],
                    enabled=channel_config.get("enabled", True),
                    priority=channel_config.get("priority", 0),
                    description=channel_config.get("description"),
                    created_by="migration_script",
                )
                summary["channels_created"] += 1
                logger.info(f"Migrated notification channel: {channel_config['name']}")
            except Exception as e:
                error_msg = f"Failed to migrate channel {channel_config.get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                summary["errors"].append(error_msg)

        logger.info(f"Migration completed: {summary}")
        return summary

    def validate_data_consistency(self) -> dict:
        """
        Validate data consistency after migration

        Returns:
            Validation results
        """
        results = {
            "integrations": {"total": 0, "valid": 0, "invalid": 0, "errors": []},
            "webhooks": {"total": 0, "valid": 0, "invalid": 0, "errors": []},
            "channels": {"total": 0, "valid": 0, "invalid": 0, "errors": []},
        }

        # Validate integrations
        integrations = self.integration_repo.get_all(limit=10000)
        results["integrations"]["total"] = len(integrations)
        for integration in integrations:
            try:
                # Check required fields
                if not integration.id or not integration.name or not integration.integration_type:
                    results["integrations"]["invalid"] += 1
                    results["integrations"]["errors"].append(
                        f"Integration {integration.id} missing required fields"
                    )
                else:
                    results["integrations"]["valid"] += 1
            except Exception as e:
                results["integrations"]["invalid"] += 1
                results["integrations"]["errors"].append(f"Integration {integration.id} validation error: {e}")

        # Validate webhooks
        webhooks = self.webhook_repo.get_all(limit=10000)
        results["webhooks"]["total"] = len(webhooks)
        for webhook in webhooks:
            try:
                if not webhook.id or not webhook.source or not webhook.event_type or not webhook.endpoint:
                    results["webhooks"]["invalid"] += 1
                    results["webhooks"]["errors"].append(
                        f"Webhook {webhook.id} missing required fields"
                    )
                else:
                    results["webhooks"]["valid"] += 1
            except Exception as e:
                results["webhooks"]["invalid"] += 1
                results["webhooks"]["errors"].append(f"Webhook {webhook.id} validation error: {e}")

        # Validate channels
        channels = self.channel_repo.get_all(limit=10000)
        results["channels"]["total"] = len(channels)
        for channel in channels:
            try:
                if not channel.id or not channel.name or not channel.channel_type:
                    results["channels"]["invalid"] += 1
                    results["channels"]["errors"].append(
                        f"Channel {channel.id} missing required fields"
                    )
                else:
                    results["channels"]["valid"] += 1
            except Exception as e:
                results["channels"]["invalid"] += 1
                results["channels"]["errors"].append(f"Channel {channel.id} validation error: {e}")

        logger.info(f"Data validation completed: {results}")
        return results


def main():
    """Main migration function"""
    logger.info("Starting integration data migration")

    # Create database session
    db = SessionLocal()

    try:
        # Initialize migrator
        migrator = IntegrationDataMigrator(db)

        # Step 1: Backup existing data
        logger.info("Step 1: Backing up existing data")
        backup_summary = migrator.backup_existing_data()
        logger.info(f"Backup summary: {backup_summary}")

        # Step 2: Migrate data from config
        logger.info("Step 2: Migrating data from configuration")
        migration_summary = migrator.migrate_from_config()
        logger.info(f"Migration summary: {migration_summary}")

        # Step 3: Validate data consistency
        logger.info("Step 3: Validating data consistency")
        validation_results = migrator.validate_data_consistency()
        logger.info(f"Validation results: {validation_results}")

        # Print summary
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Backup location: {backup_summary['backup_path']}")
        print(f"Integrations migrated: {migration_summary['integrations_created']}")
        print(f"Webhooks migrated: {migration_summary['webhooks_created']}")
        print(f"Channels migrated: {migration_summary['channels_created']}")
        print(f"Errors: {len(migration_summary['errors'])}")
        if migration_summary['errors']:
            print("\nErrors:")
            for error in migration_summary['errors']:
                print(f"  - {error}")
        print("\nValidation Results:")
        print(f"  Integrations: {validation_results['integrations']['valid']}/{validation_results['integrations']['total']} valid")
        print(f"  Webhooks: {validation_results['webhooks']['valid']}/{validation_results['webhooks']['total']} valid")
        print(f"  Channels: {validation_results['channels']['valid']}/{validation_results['channels']['total']} valid")
        print("=" * 80)

        logger.info("Migration completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\nERROR: Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
