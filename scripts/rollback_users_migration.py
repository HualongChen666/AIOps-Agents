# -*- coding: utf-8 -*-
# scripts/rollback_users_migration.py
# 用户数据回滚脚本 - 从备份恢复数据

import asyncio
import logging
import sys
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, ".")

from core.db_engine import AsyncSessionLocal
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/user_rollback.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class UserRollback:
    """用户数据回滚类"""

    def __init__(self, backup_table: Optional[str] = None):
        """初始化回滚
        
        Args:
            backup_table: 指定备份表名，如果为None则使用最新的备份
        """
        self.backup_table = backup_table
        self.rollback_start = datetime.now()

    async def list_backup_tables(self) -> list[str]:
        """列出所有备份表
        
        Returns:
            备份表名列表
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name LIKE 'users_backup_%'
                        ORDER BY table_name DESC
                    """)
                )
                backup_tables = [row[0] for row in result.fetchall()]
                return backup_tables
        except Exception as e:
            logger.error(f"❌ 获取备份表列表失败: {e}", exc_info=True)
            return []

    async def get_latest_backup(self) -> Optional[str]:
        """获取最新的备份表
        
        Returns:
            最新备份表名或None
        """
        backup_tables = await self.list_backup_tables()
        if backup_tables:
            return backup_tables[0]
        return None

    async def verify_backup(self, backup_table: str) -> bool:
        """验证备份表
        
        Args:
            backup_table: 备份表名
            
        Returns:
            备份是否有效
        """
        try:
            async with AsyncSessionLocal() as session:
                # 检查表是否存在
                result = await session.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = :backup_table
                        )
                    """),
                    {"backup_table": backup_table}
                )
                table_exists = result.scalar()
                
                if not table_exists:
                    logger.error(f"❌ 备份表不存在: {backup_table}")
                    return False
                
                # 检查表是否有数据
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {backup_table}")
                )
                count = result.scalar()
                
                if count == 0:
                    logger.error(f"❌ 备份表为空: {backup_table}")
                    return False
                
                logger.info(f"✅ 备份表验证通过: {backup_table} (记录数: {count})")
                return True
                
        except Exception as e:
            logger.error(f"❌ 备份表验证失败: {e}", exc_info=True)
            return False

    async def create_rollback_backup(self) -> str:
        """在回滚前创建当前数据的备份
        
        Returns:
            新备份表名
        """
        try:
            logger.info("在回滚前创建当前数据的备份...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_rollback_backup = f"users_pre_rollback_{timestamp}"
            
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(f"CREATE TABLE {pre_rollback_backup} AS SELECT * FROM users")
                )
                await session.commit()
                
                logger.info(f"✅ 创建回滚前备份: {pre_rollback_backup}")
                return pre_rollback_backup
                
        except Exception as e:
            logger.error(f"❌ 创建回滚前备份失败: {e}", exc_info=True)
            raise

    async def perform_rollback(self, backup_table: str) -> bool:
        """执行回滚
        
        Args:
            backup_table: 备份表名
            
        Returns:
            回滚是否成功
        """
        try:
            logger.info(f"开始从 {backup_table} 回滚...")
            
            async with AsyncSessionLocal() as session:
                # 创建回滚前备份
                pre_rollback_backup = await self.create_rollback_backup()
                
                # 删除当前数据
                result = await session.execute(text("DELETE FROM users"))
                deleted_count = result.rowcount
                logger.info(f"删除当前数据: {deleted_count} 条")
                
                # 从备份恢复
                await session.execute(
                    text(f"INSERT INTO users SELECT * FROM {backup_table}")
                )
                await session.commit()
                
                # 验证恢复的数据
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                restored_count = result.scalar()
                
                logger.info(f"✅ 回滚成功，恢复数据: {restored_count} 条")
                logger.info(f"回滚前备份: {pre_rollback_backup}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}", exc_info=True)
            return False

    async def run_rollback(self) -> bool:
        """执行完整的回滚流程
        
        Returns:
            回滚是否成功
        """
        try:
            logger.info("=" * 60)
            logger.info("开始用户数据回滚")
            logger.info(f"开始时间: {self.rollback_start}")
            logger.info("=" * 60)
            
            # 确定要使用的备份表
            if self.backup_table:
                backup_table = self.backup_table
                logger.info(f"使用指定的备份表: {backup_table}")
            else:
                backup_table = await self.get_latest_backup()
                if not backup_table:
                    logger.error("❌ 没有找到可用的备份表")
                    return False
                logger.info(f"使用最新的备份表: {backup_table}")
            
            # 验证备份表
            if not await self.verify_backup(backup_table):
                logger.error("❌ 备份表验证失败")
                return False
            
            # 执行回滚
            if not await self.perform_rollback(backup_table):
                logger.error("❌ 回滚执行失败")
                return False
            
            rollback_end = datetime.now()
            duration = (rollback_end - self.rollback_start).total_seconds()
            
            logger.info("=" * 60)
            logger.info("✅ 用户数据回滚成功完成")
            logger.info(f"结束时间: {rollback_end}")
            logger.info(f"总耗时: {duration:.2f}秒")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 回滚流程失败: {e}", exc_info=True)
            return False


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="用户数据回滚脚本")
    parser.add_argument(
        "--backup-table",
        type=str,
        default=None,
        help="指定要回滚的备份表名（默认使用最新的备份）"
    )
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="列出所有可用的备份表"
    )
    
    args = parser.parse_args()
    
    # 如果只是列出备份
    if args.list_backups:
        rollback = UserRollback()
        backup_tables = await rollback.list_backup_tables()
        
        if backup_tables:
            logger.info("可用的备份表:")
            for table in backup_tables:
                logger.info(f"  - {table}")
        else:
            logger.info("没有找到可用的备份表")
        
        sys.exit(0)
    
    # 执行回滚
    rollback = UserRollback(backup_table=args.backup_table)
    success = await rollback.run_rollback()
    
    if not success:
        logger.error("❌ 回滚失败，请检查日志")
        sys.exit(1)
    
    logger.info("✅ 回滚成功完成")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
