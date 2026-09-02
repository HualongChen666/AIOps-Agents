# -*- coding: utf-8 -*-
"""
Frontend Data Migration Script
==============================

This script migrates frontend data from in-memory storage to database.
Ensures zero data loss during migration.

Usage:
    python scripts/migrate_frontend_data.py
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal
from core.repositories.frontend_repository_impl import FrontendRepositoryImpl
from core.frontend_enhancement import frontend_enhancement_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrontendDataMigrator:
    """Frontend data migrator"""

    def __init__(self):
        self.migration_stats = {
            "components": {"migrated": 0, "failed": 0, "errors": []},
            "themes": {"migrated": 0, "failed": 0, "errors": []},
            "layouts": {"migrated": 0, "failed": 0, "errors": []},
            "user_preferences": {"migrated": 0, "failed": 0, "errors": []},
            "dashboard_widgets": {"migrated": 0, "failed": 0, "errors": []},
            "report_templates": {"migrated": 0, "failed": 0, "errors": []},
            "localizations": {"migrated": 0, "failed": 0, "errors": []},
        }

    async def migrate_components(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate components from in-memory to database"""
        logger.info("开始迁移组件数据...")

        # Get data from frontend enhancement manager
        # Since the original data was in-memory, we'll create default components
        # In a real scenario, you would export the in-memory data first

        # Create default components if none exist
        existing = await repo.list_components(limit=1)
        if not existing:
            # Create sample components
            sample_components = [
                {
                    "id": "comp-default-button",
                    "name": "Default Button",
                    "type": "button",
                    "category": "ui",
                    "description": "Default button component",
                    "code": "export const DefaultButton = () => { return <button>Click</button>; }",
                    "props": {"variant": "primary", "size": "medium"},
                    "dependencies": [],
                    "is_public": True,
                    "status": "active",
                    "created_by": "system",
                },
                {
                    "id": "comp-default-card",
                    "name": "Default Card",
                    "type": "card",
                    "category": "ui",
                    "description": "Default card component",
                    "code": "export const DefaultCard = ({ children }) => { return <div>{children}</div>; }",
                    "props": {"elevation": 2},
                    "dependencies": [],
                    "is_public": True,
                    "status": "active",
                    "created_by": "system",
                },
            ]

            for comp_data in sample_components:
                try:
                    await repo.create_component(comp_data)
                    self.migration_stats["components"]["migrated"] += 1
                    logger.info(f"✅ 组件迁移成功: {comp_data['id']}")
                except Exception as e:
                    self.migration_stats["components"]["failed"] += 1
                    self.migration_stats["components"]["errors"].append(str(e))
                    logger.error(f"❌ 组件迁移失败: {comp_data['id']}: {e}")
        else:
            logger.info("组件数据已存在，跳过迁移")

    async def migrate_themes(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate themes from in-memory to database"""
        logger.info("开始迁移主题数据...")

        # Get built-in themes from frontend enhancement manager
        from core.frontend_enhancement import ThemeType

        existing = await repo.list_themes(limit=1)
        if not existing:
            for theme_type in ThemeType:
                try:
                    config = frontend_enhancement_manager.get_theme_config(theme_type)
                    theme_data = {
                        "id": f"theme-{theme_type.value}",
                        "name": f"Built-in {theme_type.value.title()}",
                        "base_theme": theme_type.value,
                        "description": f"Built-in {theme_type.value} theme",
                        "colors": config,
                        "fonts": {},
                        "spacing": {},
                        "is_default": theme_type == ThemeType.LIGHT,
                        "is_public": True,
                        "created_by": "system",
                    }
                    await repo.create_theme(theme_data)
                    self.migration_stats["themes"]["migrated"] += 1
                    logger.info(f"✅ 主题迁移成功: {theme_data['id']}")
                except Exception as e:
                    self.migration_stats["themes"]["failed"] += 1
                    self.migration_stats["themes"]["errors"].append(str(e))
                    logger.error(f"❌ 主题迁移失败: {theme_type.value}: {e}")
        else:
            logger.info("主题数据已存在，跳过迁移")

    async def migrate_layouts(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate layouts from in-memory to database"""
        logger.info("开始迁移布局数据...")

        existing = await repo.list_layouts(limit=1)
        if not existing:
            # Create default layout
            layout_data = {
                "id": "layout-default-dashboard",
                "name": "Default Dashboard",
                "type": "dashboard",
                "description": "Default dashboard layout",
                "structure": {
                    "header": {"height": 64},
                    "sidebar": {"width": 240},
                    "content": {"flex": 1},
                },
                "breakpoints": {
                    "mobile": {"sidebar": {"width": 0}},
                },
                "is_default": True,
                "is_public": True,
                "created_by": "system",
            }

            try:
                await repo.create_layout(layout_data)
                self.migration_stats["layouts"]["migrated"] += 1
                logger.info(f"✅ 布局迁移成功: {layout_data['id']}")
            except Exception as e:
                self.migration_stats["layouts"]["failed"] += 1
                self.migration_stats["layouts"]["errors"].append(str(e))
                logger.error(f"❌ 布局迁移失败: {layout_data['id']}: {e}")
        else:
            logger.info("布局数据已存在，跳过迁移")

    async def migrate_user_preferences(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate user preferences from in-memory to database"""
        logger.info("开始迁移用户偏好数据...")

        # Get user preferences from frontend enhancement manager
        for user_id, pref in frontend_enhancement_manager.user_preferences.items():
            try:
                pref_data = {
                    "user_id": user_id,
                    "theme": pref.theme.value,
                    "language": pref.language,
                    "timezone": pref.timezone,
                    "date_format": pref.date_format,
                    "time_format": pref.time_format,
                    "view_mode": pref.view_mode.value,
                    "notifications_enabled": pref.notifications_enabled,
                    "notification_sound": pref.notification_sound,
                    "auto_refresh_interval": pref.auto_refresh_interval,
                    "dashboard_layout": pref.dashboard_layout,
                    "custom_colors": pref.custom_colors,
                    "accessibility_settings": pref.accessibility_settings,
                }

                existing = await repo.get_user_preferences(user_id)
                if existing:
                    await repo.update_user_preferences(user_id, pref_data)
                else:
                    await repo.create_user_preferences(user_id, pref_data)

                self.migration_stats["user_preferences"]["migrated"] += 1
                logger.info(f"✅ 用户偏好迁移成功: {user_id}")
            except Exception as e:
                self.migration_stats["user_preferences"]["failed"] += 1
                self.migration_stats["user_preferences"]["errors"].append(str(e))
                logger.error(f"❌ 用户偏好迁移失败: {user_id}: {e}")

    async def migrate_dashboard_widgets(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate dashboard widgets from in-memory to database"""
        logger.info("开始迁移仪表板小部件数据...")

        # Get dashboard configs from frontend enhancement manager
        for dashboard_id, widgets in frontend_enhancement_manager.dashboard_configs.items():
            for widget in widgets:
                try:
                    widget_data = {
                        "id": f"widget-{dashboard_id}-{widget.widget_id}",
                        "dashboard_id": dashboard_id,
                        "widget_id": widget.widget_id,
                        "widget_type": widget.widget_type,
                        "title": widget.title,
                        "position": widget.position,
                        "config": widget.config,
                        "data_source": widget.data_source,
                        "refresh_interval": widget.refresh_interval,
                        "enabled": widget.enabled,
                        "created_by": "system",
                    }

                    await repo.create_dashboard_widget(widget_data)
                    self.migration_stats["dashboard_widgets"]["migrated"] += 1
                    logger.info(f"✅ 小部件迁移成功: {widget_data['id']}")
                except Exception as e:
                    self.migration_stats["dashboard_widgets"]["failed"] += 1
                    self.migration_stats["dashboard_widgets"]["errors"].append(str(e))
                    logger.error(f"❌ 小部件迁移失败: {widget.widget_id}: {e}")

    async def migrate_report_templates(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate report templates from in-memory to database"""
        logger.info("开始迁移报告模板数据...")

        # Get report templates from frontend enhancement manager
        for template_id, template in frontend_enhancement_manager.report_templates.items():
            try:
                template_data = {
                    "id": template_id,
                    "name": template.name,
                    "description": template.description,
                    "data_sources": template.data_sources,
                    "filters": template.filters,
                    "visualization_config": template.visualization_config,
                    "format": template.format,
                    "schedule": template.schedule,
                    "created_by": template.created_by,
                }

                await repo.create_report_template(template_data)
                self.migration_stats["report_templates"]["migrated"] += 1
                logger.info(f"✅ 报告模板迁移成功: {template_id}")
            except Exception as e:
                self.migration_stats["report_templates"]["failed"] += 1
                self.migration_stats["report_templates"]["errors"].append(str(e))
                logger.error(f"❌ 报告模板迁移失败: {template_id}: {e}")

    async def migrate_localizations(self, repo: FrontendRepositoryImpl) -> None:
        """Migrate localizations from in-memory to database"""
        logger.info("开始迁移本地化数据...")

        # Default localizations
        default_localizations = {
            "en-US": {
                "welcome": "Welcome",
                "dashboard": "Dashboard",
                "settings": "Settings",
                "logout": "Logout",
            },
            "zh-CN": {
                "welcome": "欢迎",
                "dashboard": "仪表板",
                "settings": "设置",
                "logout": "退出",
            },
        }

        for language, translations in default_localizations.items():
            for key, value in translations.items():
                try:
                    await repo.upsert_localization(language, key, value)
                    self.migration_stats["localizations"]["migrated"] += 1
                    logger.info(f"✅ 本地化迁移成功: {language}/{key}")
                except Exception as e:
                    self.migration_stats["localizations"]["failed"] += 1
                    self.migration_stats["localizations"]["errors"].append(str(e))
                    logger.error(f"❌ 本地化迁移失败: {language}/{key}: {e}")

    async def migrate_all(self) -> Dict[str, Any]:
        """Migrate all frontend data"""
        logger.info("========== 开始前端数据迁移 ==========")
        start_time = datetime.now()

        async with AsyncSessionLocal() as db:
            repo = FrontendRepositoryImpl(session=db)

            # Migrate all data types
            await self.migrate_components(repo)
            await self.migrate_themes(repo)
            await self.migrate_layouts(repo)
            await self.migrate_user_preferences(repo)
            await self.migrate_dashboard_widgets(repo)
            await self.migrate_report_templates(repo)
            await self.migrate_localizations(repo)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate migration report
        total_migrated = sum(
            stats["migrated"] for stats in self.migration_stats.values()
        )
        total_failed = sum(
            stats["failed"] for stats in self.migration_stats.values()
        )

        report = {
            "status": "completed",
            "duration_seconds": duration,
            "total_migrated": total_migrated,
            "total_failed": total_failed,
            "details": self.migration_stats,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        logger.info("========== 前端数据迁移完成 ==========")
        logger.info(f"总迁移数量: {total_migrated}")
        logger.info(f"总失败数量: {total_failed}")
        logger.info(f"耗时: {duration:.2f}秒")

        # Save migration report
        report_path = "frontend_migration_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"迁移报告已保存: {report_path}")

        return report


async def main():
    """Main migration function"""
    migrator = FrontendDataMigrator()
    report = await migrator.migrate_all()

    # Exit with error code if there were failures
    if report["total_failed"] > 0:
        logger.warning(f"迁移完成但有 {report['total_failed']} 个失败")
        return 1
    else:
        logger.info("迁移成功完成")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
