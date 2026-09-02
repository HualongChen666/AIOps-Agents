# -*- coding: utf-8 -*-
"""
Plugin Data Migration Script

This script migrates existing plugin data from the plugin manager
to the new database schema. Ensures zero data loss during migration.
"""

import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from sqlalchemy.orm import Session

from core.database import SessionLocal, engine
from core.models import Base, Plugin, PluginConfig, PluginStatus
from core.plugin_manager import get_plugin, list_plugins as list_plugin_manager_plugins


def migrate_plugins_from_manager(db: Session) -> Dict[str, Any]:
    """
    Migrate plugins from plugin manager to database.
    
    Args:
        db: Database session
        
    Returns:
        Migration statistics
    """
    stats = {
        "total_found": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": [],
    }
    
    try:
        # Get plugins from plugin manager
        manager_plugins = list_plugin_manager_plugins()
        stats["total_found"] = len(manager_plugins)
        
        logger.info(f"Found {stats['total_found']} plugins in plugin manager")
        
        for plugin_info in manager_plugins:
            try:
                plugin_name = plugin_info["metadata"]["name"]
                plugin_version = plugin_info["metadata"].get("version", "1.0.0")
                plugin_description = plugin_info["metadata"].get("description", "")
                plugin_author = plugin_info["metadata"].get("author", "Unknown")
                plugin_type = plugin_info["metadata"].get("plugin_type", "collector")
                
                # Check if plugin already exists in database
                existing = db.query(Plugin).filter(Plugin.name == plugin_name).first()
                
                if existing:
                    logger.info(f"Plugin '{plugin_name}' already exists, skipping")
                    stats["skipped"] += 1
                    continue
                
                # Create new plugin record
                plugin = Plugin(
                    id=f"plugin-{plugin_name}-{int(datetime.utcnow().timestamp())}",
                    name=plugin_name,
                    version=plugin_version,
                    description=plugin_description,
                    author=plugin_author,
                    plugin_type=plugin_type,
                    status=PluginStatus.ACTIVE.value,
                    config_schema=plugin_info["metadata"].get("config_schema"),
                    default_config=plugin_info["metadata"].get("default_config"),
                    dependencies=plugin_info["metadata"].get("dependencies", []),
                    plugin_metadata=plugin_info["metadata"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    installed_at=datetime.utcnow(),
                    last_loaded_at=datetime.utcnow(),
                    created_by="migration_script",
                )
                
                db.add(plugin)
                db.commit()
                
                logger.info(f"Migrated plugin: {plugin_name}")
                stats["migrated"] += 1
                
            except Exception as e:
                error_msg = f"Failed to migrate plugin {plugin_info.get('metadata', {}).get('name', 'unknown')}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                db.rollback()
        
        return stats
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        stats["errors"].append(str(e))
        return stats


def create_default_plugin_configs(db: Session) -> Dict[str, Any]:
    """
    Create default configurations for migrated plugins.
    
    Args:
        db: Database session
        
    Returns:
        Configuration creation statistics
    """
    stats = {
        "total_plugins": 0,
        "configs_created": 0,
        "errors": [],
    }
    
    try:
        # Get all plugins without configs
        plugins = db.query(Plugin).filter(~Plugin.id.in_(
            db.query(PluginConfig.plugin_id)
        )).all()
        
        stats["total_plugins"] = len(plugins)
        logger.info(f"Found {stats['total_plugins']} plugins without configs")
        
        for plugin in plugins:
            try:
                import uuid
                config = PluginConfig(
                    id=str(uuid.uuid4()),
                    plugin_id=plugin.id,
                    plugin_name=plugin.name,
                    config_data=plugin.default_config or {},
                    config_version=1,
                    is_active=True,
                    description=f"Default configuration for {plugin.name}",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    updated_by="migration_script",
                )
                
                db.add(config)
                db.commit()
                
                logger.info(f"Created config for plugin: {plugin.name}")
                stats["configs_created"] += 1
                
            except Exception as e:
                error_msg = f"Failed to create config for plugin {plugin.name}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
                db.rollback()
        
        return stats
        
    except Exception as e:
        logger.error(f"Config creation failed: {e}")
        stats["errors"].append(str(e))
        return stats


def validate_migration(db: Session) -> Dict[str, Any]:
    """
    Validate migration results.
    
    Args:
        db: Database session
        
    Returns:
        Validation results
    """
    results = {
        "total_plugins": 0,
        "active_plugins": 0,
        "plugins_with_configs": 0,
        "plugins_without_configs": 0,
        "validation_passed": True,
        "issues": [],
    }
    
    try:
        # Count plugins
        results["total_plugins"] = db.query(Plugin).count()
        results["active_plugins"] = db.query(Plugin).filter(
            Plugin.status == PluginStatus.ACTIVE.value
        ).count()
        
        # Count configs
        results["plugins_with_configs"] = db.query(PluginConfig).count()
        results["plugins_without_configs"] = results["total_plugins"] - results["plugins_with_configs"]
        
        # Check for issues
        if results["plugins_without_configs"] > 0:
            results["issues"].append(f"{results['plugins_without_configs']} plugins without configs")
            results["validation_passed"] = False
        
        if results["active_plugins"] == 0 and results["total_plugins"] > 0:
            results["issues"].append("No active plugins found")
            results["validation_passed"] = False
        
        return results
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        results["validation_passed"] = False
        results["issues"].append(str(e))
        return results


def main():
    """Main migration function."""
    logger.info("Starting plugin data migration...")
    
    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Step 1: Migrate plugins from plugin manager
        logger.info("Step 1: Migrating plugins from plugin manager...")
        migration_stats = migrate_plugins_from_manager(db)
        
        # Step 2: Create default configurations
        logger.info("Step 2: Creating default plugin configurations...")
        config_stats = create_default_plugin_configs(db)
        
        # Step 3: Validate migration
        logger.info("Step 3: Validating migration results...")
        validation_results = validate_migration(db)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("Migration Summary")
        logger.info("=" * 50)
        logger.info(f"Plugins found: {migration_stats['total_found']}")
        logger.info(f"Plugins migrated: {migration_stats['migrated']}")
        logger.info(f"Plugins skipped: {migration_stats['skipped']}")
        logger.info(f"Configs created: {config_stats['configs_created']}")
        logger.info(f"Errors: {len(migration_stats['errors']) + len(config_stats['errors'])}")
        
        if migration_stats['errors']:
            logger.error("Migration errors:")
            for error in migration_stats['errors']:
                logger.error(f"  - {error}")
        
        if config_stats['errors']:
            logger.error("Config creation errors:")
            for error in config_stats['errors']:
                logger.error(f"  - {error}")
        
        logger.info("=" * 50)
        logger.info("Validation Results")
        logger.info("=" * 50)
        logger.info(f"Total plugins: {validation_results['total_plugins']}")
        logger.info(f"Active plugins: {validation_results['active_plugins']}")
        logger.info(f"Plugins with configs: {validation_results['plugins_with_configs']}")
        logger.info(f"Plugins without configs: {validation_results['plugins_without_configs']}")
        logger.info(f"Validation passed: {validation_results['validation_passed']}")
        
        if validation_results['issues']:
            logger.warning("Validation issues:")
            for issue in validation_results['issues']:
                logger.warning(f"  - {issue}")
        
        # Exit with appropriate code
        if validation_results['validation_passed'] and not migration_stats['errors']:
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("Migration completed with errors!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration failed with exception: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
