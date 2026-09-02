# -*- coding: utf-8 -*-
"""
Plugin Migration Rollback Script

This script rolls back the plugin migration by removing migrated data
from the database. Ensures safe rollback with proper validation.
"""

import sys
import os
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import Base, Plugin, PluginConfig, PluginExecution


def validate_rollback_safety(db: Session) -> Dict[str, Any]:
    """
    Validate that rollback is safe to perform.
    
    Args:
        db: Database session
        
    Returns:
        Validation results
    """
    results = {
        "safe_to_rollback": True,
        "warnings": [],
        "plugin_count": 0,
        "config_count": 0,
        "execution_count": 0,
    }
    
    try:
        # Count records
        results["plugin_count"] = db.query(Plugin).count()
        results["config_count"] = db.query(PluginConfig).count()
        results["execution_count"] = db.query(PluginExecution).count()
        
        # Check for potential issues
        if results["execution_count"] > 0:
            results["warnings"].append(
                f"{results['execution_count']} plugin execution records will be deleted"
            )
        
        if results["plugin_count"] > 100:
            results["warnings"].append(
                f"Large number of plugins ({results['plugin_count']}) will be deleted"
            )
        
        # Check for plugins created by migration script
        migrated_plugins = db.query(Plugin).filter(
            Plugin.created_by == "migration_script"
        ).count()
        
        if migrated_plugins < results["plugin_count"]:
            results["warnings"].append(
                f"{results['plugin_count'] - migrated_plugins} plugins were not created by migration script"
            )
            results["safe_to_rollback"] = False
        
        return results
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        results["safe_to_rollback"] = False
        results["warnings"].append(str(e))
        return results


def rollback_plugin_data(db: Session, force: bool = False) -> Dict[str, Any]:
    """
    Rollback plugin migration by deleting migrated data.
    
    Args:
        db: Database session
        force: Force rollback even if validation fails
        
    Returns:
        Rollback statistics
    """
    stats = {
        "plugins_deleted": 0,
        "configs_deleted": 0,
        "executions_deleted": 0,
        "errors": [],
    }
    
    try:
        # Validate rollback safety
        validation = validate_rollback_safety(db)
        
        if not validation["safe_to_rollback"] and not force:
            logger.error("Rollback validation failed. Use --force to proceed anyway.")
            stats["errors"].extend(validation["warnings"])
            return stats
        
        # Print warnings
        if validation["warnings"]:
            logger.warning("Rollback warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")
        
        # Step 1: Delete plugin executions (due to foreign key constraints)
        logger.info("Step 1: Deleting plugin executions...")
        try:
            execution_count = db.query(PluginExecution).count()
            db.query(PluginExecution).delete()
            db.commit()
            stats["executions_deleted"] = execution_count
            logger.info(f"Deleted {execution_count} plugin execution records")
        except Exception as e:
            error_msg = f"Failed to delete plugin executions: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            db.rollback()
        
        # Step 2: Delete plugin configs
        logger.info("Step 2: Deleting plugin configs...")
        try:
            config_count = db.query(PluginConfig).count()
            db.query(PluginConfig).delete()
            db.commit()
            stats["configs_deleted"] = config_count
            logger.info(f"Deleted {config_count} plugin config records")
        except Exception as e:
            error_msg = f"Failed to delete plugin configs: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            db.rollback()
        
        # Step 3: Delete plugins
        logger.info("Step 3: Deleting plugins...")
        try:
            # Only delete plugins created by migration script unless forced
            if force:
                plugin_count = db.query(Plugin).count()
                db.query(Plugin).delete()
            else:
                plugin_count = db.query(Plugin).filter(
                    Plugin.created_by == "migration_script"
                ).count()
                db.query(Plugin).filter(
                    Plugin.created_by == "migration_script"
                ).delete()
            
            db.commit()
            stats["plugins_deleted"] = plugin_count
            logger.info(f"Deleted {plugin_count} plugin records")
        except Exception as e:
            error_msg = f"Failed to delete plugins: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            db.rollback()
        
        return stats
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        stats["errors"].append(str(e))
        return stats


def verify_rollback(db: Session) -> Dict[str, Any]:
    """
    Verify that rollback was successful.
    
    Args:
        db: Database session
        
    Returns:
        Verification results
    """
    results = {
        "plugin_count": 0,
        "config_count": 0,
        "execution_count": 0,
        "rollback_complete": True,
    }
    
    try:
        results["plugin_count"] = db.query(Plugin).count()
        results["config_count"] = db.query(PluginConfig).count()
        results["execution_count"] = db.query(PluginExecution).count()
        
        # Check if any records remain
        if results["plugin_count"] > 0 or results["config_count"] > 0 or results["execution_count"] > 0:
            results["rollback_complete"] = False
        
        return results
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        results["rollback_complete"] = False
        return results


def main():
    """Main rollback function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Rollback plugin migration")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rollback even if validation fails",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    
    args = parser.parse_args()
    
    logger.info("Starting plugin migration rollback...")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be deleted")
    
    db = SessionLocal()
    
    try:
        # Validate rollback safety
        logger.info("Validating rollback safety...")
        validation = validate_rollback_safety(db)
        
        logger.info("=" * 50)
        logger.info("Rollback Validation")
        logger.info("=" * 50)
        logger.info(f"Plugins to delete: {validation['plugin_count']}")
        logger.info(f"Configs to delete: {validation['config_count']}")
        logger.info(f"Executions to delete: {validation['execution_count']}")
        logger.info(f"Safe to rollback: {validation['safe_to_rollback']}")
        
        if validation['warnings']:
            logger.warning("Warnings:")
            for warning in validation['warnings']:
                logger.warning(f"  - {warning}")
        
        if not validation['safe_to_rollback'] and not args.force:
            logger.error("Rollback validation failed. Use --force to proceed anyway.")
            sys.exit(1)
        
        if args.dry_run:
            logger.info("Dry run completed. No data was deleted.")
            sys.exit(0)
        
        # Perform rollback
        logger.info("Performing rollback...")
        rollback_stats = rollback_plugin_data(db, force=args.force)
        
        # Verify rollback
        logger.info("Verifying rollback...")
        verification = verify_rollback(db)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("Rollback Summary")
        logger.info("=" * 50)
        logger.info(f"Plugins deleted: {rollback_stats['plugins_deleted']}")
        logger.info(f"Configs deleted: {rollback_stats['configs_deleted']}")
        logger.info(f"Executions deleted: {rollback_stats['executions_deleted']}")
        logger.info(f"Errors: {len(rollback_stats['errors'])}")
        
        if rollback_stats['errors']:
            logger.error("Rollback errors:")
            for error in rollback_stats['errors']:
                logger.error(f"  - {error}")
        
        logger.info("=" * 50)
        logger.info("Verification Results")
        logger.info("=" * 50)
        logger.info(f"Remaining plugins: {verification['plugin_count']}")
        logger.info(f"Remaining configs: {verification['config_count']}")
        logger.info(f"Remaining executions: {verification['execution_count']}")
        logger.info(f"Rollback complete: {verification['rollback_complete']}")
        
        # Exit with appropriate code
        if verification['rollback_complete'] and not rollback_stats['errors']:
            logger.info("Rollback completed successfully!")
            sys.exit(0)
        else:
            logger.error("Rollback completed with errors!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Rollback failed with exception: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
