# -*- coding: utf-8 -*-
# scripts/migrate_users_data.py
# 用户数据迁移脚本 - 确保零数据丢失

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, ".")

from core.db_engine import AsyncSessionLocal, engine
from core.models import User
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/user_migration.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class UserMigration:
    """用户数据迁移类"""

    def __init__(self):
        """初始化迁移"""
        self.migration_start = datetime.now()
        self.migrated_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    async def backup_existing_data(self) -> bool:
        """备份现有用户数据
        
        Returns:
            是否备份成功
        """
        try:
            logger.info("开始备份现有用户数据...")
            
            async with AsyncSessionLocal() as session:
                # 查询所有用户
                result = await session.execute(text("SELECT * FROM users"))
                users = result.fetchall()
                
                if not users:
                    logger.info("没有现有用户数据需要备份")
                    return True
                
                # 创建备份表
                await session.execute(
                    text("""
                        CREATE TABLE IF NOT EXISTS users_backup_{} AS 
                        SELECT * FROM users
                    """.format(self.migration_start.strftime("%Y%m%d_%H%M%S"))
                )
                await session.commit()
                
                logger.info(f"✅ 备份完成，备份表: users_backup_{self.migration_start.strftime('%Y%m%d_%H%M%S')}")
                logger.info(f"备份用户数量: {len(users)}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 备份失败: {e}", exc_info=True)
            return False

    async def validate_data_integrity(self) -> bool:
        """验证数据完整性
        
        Returns:
            数据是否完整
        """
        try:
            logger.info("开始验证数据完整性...")
            
            async with AsyncSessionLocal() as session:
                # 检查users表是否存在
                result = await session.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'users'
                        )
                    """)
                )
                table_exists = result.scalar()
                
                if not table_exists:
                    logger.warning("users表不存在，跳过验证")
                    return True
                
                # 检查用户数量
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                
                logger.info(f"当前用户数量: {user_count}")
                
                # 检查必填字段
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) FROM users 
                        WHERE username IS NULL OR hashed_password IS NULL
                    """)
                )
                invalid_count = result.scalar()
                
                if invalid_count > 0:
                    logger.error(f"❌ 发现{invalid_count}条记录缺少必填字段")
                    return False
                
                logger.info("✅ 数据完整性验证通过")
                return True
                
        except Exception as e:
            logger.error(f"❌ 数据完整性验证失败: {e}", exc_info=True)
            return False

    async def migrate_user_data(self) -> bool:
        """迁移用户数据
        
        Returns:
            是否迁移成功
        """
        try:
            logger.info("开始迁移用户数据...")
            
            async with AsyncSessionLocal() as session:
                # 获取所有用户
                result = await session.execute(text("SELECT * FROM users"))
                users_data = result.fetchall()
                columns = result.keys()
                
                logger.info(f"找到 {len(users_data)} 条用户记录")
                
                for user_row in users_data:
                    user_dict = dict(zip(columns, user_row))
                    
                    try:
                        # 检查用户是否已存在（避免重复）
                        existing = await session.execute(
                            text("SELECT id FROM users WHERE username = :username"),
                            {"username": user_dict.get("username")}
                        )
                        if existing.scalar():
                            logger.debug(f"跳过已存在的用户: {user_dict.get('username')}")
                            self.skipped_count += 1
                            continue
                        
                        # 确保必填字段存在
                        if not user_dict.get("username") or not user_dict.get("hashed_password"):
                            logger.warning(f"跳过不完整的用户记录: {user_dict}")
                            self.failed_count += 1
                            continue
                        
                        # 更新用户数据（如果需要添加新字段）
                        update_data = {
                            "username": user_dict.get("username"),
                            "hashed_password": user_dict.get("hashed_password"),
                            "email": user_dict.get("email"),
                            "full_name": user_dict.get("full_name"),
                            "role": user_dict.get("role", "user"),
                            "disabled": user_dict.get("disabled", False),
                            "mfa_enabled": user_dict.get("mfa_enabled", False),
                        }
                        
                        # 执行更新
                        await session.execute(
                            text("""
                                UPDATE users 
                                SET email = :email,
                                    full_name = :full_name,
                                    role = :role,
                                    disabled = :disabled,
                                    mfa_enabled = :mfa_enabled
                                WHERE username = :username
                            """),
                            update_data
                        )
                        
                        self.migrated_count += 1
                        logger.debug(f"✅ 迁移用户: {user_dict.get('username')}")
                        
                    except Exception as e:
                        logger.error(f"❌ 迁移用户失败 {user_dict.get('username')}: {e}")
                        self.failed_count += 1
                        continue
                
                await session.commit()
                logger.info(f"✅ 用户数据迁移完成")
                logger.info(f"迁移成功: {self.migrated_count}")
                logger.info(f"跳过: {self.skipped_count}")
                logger.info(f"失败: {self.failed_count}")
                
                return self.failed_count == 0
                
        except Exception as e:
            logger.error(f"❌ 用户数据迁移失败: {e}", exc_info=True)
            return False

    async def verify_migration(self) -> bool:
        """验证迁移结果
        
        Returns:
            迁移是否成功
        """
        try:
            logger.info("开始验证迁移结果...")
            
            async with AsyncSessionLocal() as session:
                # 检查用户数量
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                
                logger.info(f"迁移后用户数量: {user_count}")
                
                # 检查是否有无效数据
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) FROM users 
                        WHERE username IS NULL OR hashed_password IS NULL
                    """)
                )
                invalid_count = result.scalar()
                
                if invalid_count > 0:
                    logger.error(f"❌ 迁移后仍有{invalid_count}条无效记录")
                    return False
                
                logger.info("✅ 迁移验证通过")
                return True
                
        except Exception as e:
            logger.error(f"❌ 迁移验证失败: {e}", exc_info=True)
            return False

    async def rollback(self) -> bool:
        """回滚到备份
        
        Returns:
            是否回滚成功
        """
        try:
            logger.info("开始回滚到备份...")
            
            backup_table = f"users_backup_{self.migration_start.strftime('%Y%m%d_%H%M%S')}"
            
            async with AsyncSessionLocal() as session:
                # 检查备份表是否存在
                result = await session.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = :backup_table
                        )
                    """),
                    {"backup_table": backup_table}
                )
                backup_exists = result.scalar()
                
                if not backup_exists:
                    logger.error(f"❌ 备份表不存在: {backup_table}")
                    return False
                
                # 删除当前数据
                await session.execute(text("DELETE FROM users"))
                
                # 从备份恢复
                await session.execute(
                    text(f"INSERT INTO users SELECT * FROM {backup_table}")
                )
                
                await session.commit()
                logger.info(f"✅ 回滚成功，从 {backup_table} 恢复")
                return True
                
        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}", exc_info=True)
            return False

    async def run_migration(self) -> bool:
        """执行完整的迁移流程
        
        Returns:
            迁移是否成功
        """
        try:
            logger.info("=" * 60)
            logger.info("开始用户数据迁移")
            logger.info(f"开始时间: {self.migration_start}")
            logger.info("=" * 60)
            
            # 1. 备份现有数据
            if not await self.backup_existing_data():
                logger.error("❌ 备份失败，终止迁移")
                return False
            
            # 2. 验证数据完整性
            if not await self.validate_data_integrity():
                logger.error("❌ 数据完整性验证失败，终止迁移")
                return False
            
            # 3. 执行迁移
            if not await self.migrate_user_data():
                logger.error("❌ 数据迁移失败")
                return False
            
            # 4. 验证迁移结果
            if not await self.verify_migration():
                logger.error("❌ 迁移验证失败")
                return False
            
            migration_end = datetime.now()
            duration = (migration_end - self.migration_start).total_seconds()
            
            logger.info("=" * 60)
            logger.info("✅ 用户数据迁移成功完成")
            logger.info(f"结束时间: {migration_end}")
            logger.info(f"总耗时: {duration:.2f}秒")
            logger.info(f"迁移成功: {self.migrated_count}")
            logger.info(f"跳过: {self.skipped_count}")
            logger.info(f"失败: {self.failed_count}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 迁移流程失败: {e}", exc_info=True)
            return False


async def main():
    """主函数"""
    migration = UserMigration()
    
    # 执行迁移
    success = await migration.run_migration()
    
    if not success:
        logger.error("❌ 迁移失败，请检查日志")
        sys.exit(1)
    
    logger.info("✅ 迁移成功完成")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
