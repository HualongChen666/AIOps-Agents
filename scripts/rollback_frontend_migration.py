# -*- coding: utf-8 -*-
"""
Frontend Migration Rollback Script
==================================

This script rolls back the frontend data migration by reverting the database changes.
It provides a safe rollback mechanism to restore the system to its previous state.

Usage:
    python scripts/rollback_frontend_migration.py
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_engine import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrontendMigrationRollback:
    """Frontend migration rollback handler"""

    def __init__(self):
        self.rollback_stats = {
            "tables_dropped": 0,
            "errors": [],
        }

    async def drop_frontend_tables(self, db: AsyncSession) -> None:
        """Drop all frontend-related tables"""
        tables_to_drop = [
            "frontend_localizations",
            "frontend_report_templates",
            "frontend_dashboard_widgets",
            "frontend_user_preferences",
            "frontend_layouts",
            "frontend_themes",
            "frontend_components",
        ]

        for table_name in tables_to_drop:
            try:
                # Check if table exists
                check_sql = text(
                    f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = '{table_name}'
                    )
                """
                )
                result = await db.execute(check_sql)
                exists = result.scalar()

                if exists:
                    drop_sql = text(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                    await db.execute(drop_sql)
                    await db.commit()
                    self.rollback_stats["tables_dropped"] += 1
                    logger.info(f"✅ 表已删除: {table_name}")
                else:
                    logger.info(f"表不存在，跳过: {table_name}")
            except Exception as e:
                self.rollback_stats["errors"].append(f"{table_name}: {str(e)}")
                logger.error(f"❌ 删除表失败: {table_name}: {e}")
                await db.rollback()

    async def rollback_migration(self) -> dict:
        """Rollback the frontend migration"""
        logger.info("========== 开始回滚前端迁移 ==========")
        start_time = datetime.now()

        async with AsyncSessionLocal() as db:
            await self.drop_frontend_tables(db)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        report = {
            "status": "completed",
            "duration_seconds": duration,
            "tables_dropped": self.rollback_stats["tables_dropped"],
            "errors": self.rollback_stats["errors"],
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
        }

        logger.info("========== 前端迁移回滚完成 ==========")
        logger.info(f"删除表数量: {report['tables_dropped']}")
        logger.info(f"错误数量: {len(report['errors'])}")
        logger.info(f"耗时: {duration:.2f}秒")

        if report["errors"]:
            logger.warning("回滚完成但有错误:")
            for error in report["errors"]:
                logger.warning(f"  - {error}")
        else:
            logger.info("回滚成功完成")

        return report


async def main():
    """Main rollback function"""
    rollback_handler = FrontendMigrationRollback()
    report = await rollback_handler.rollback_migration()

    # Exit with error code if there were errors
    if report["errors"]:
        logger.warning(f"回滚完成但有 {len(report['errors'])} 个错误")
        return 1
    else:
        logger.info("回滚成功完成")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
