# -*- coding: utf-8 -*-
# scripts/migrate_workflow_to_db.py
# Workflow数据迁移脚本 - 从内存存储迁移到数据库持久化
# 确保零数据丢失，提供完整的迁移验证和回滚能力

import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.workflow_engine import _WORKFLOW_DEFINITIONS_RAW
from core.workflow_repository import WorkflowRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def migrate_workflow_definitions():
    """
    将内存中的工作流定义迁移到数据库
    确保零数据丢失
    """
    logger.info("=" * 60)
    logger.info("开始Workflow数据迁移")
    logger.info("=" * 60)
    
    # 获取内存中的工作流定义
    memory_definitions = _WORKFLOW_DEFINITIONS_RAW
    logger.info(f"内存中共有 {len(memory_definitions)} 个工作流定义")
    
    # 打印现有工作流定义
    for wf_key, definition in memory_definitions.items():
        logger.info(f"  - {wf_key}: {definition.get('name', 'N/A')}")
    
    # 创建Repository实例
    repo = WorkflowRepository()
    
    # 执行迁移
    try:
        stats = repo.migrate_from_memory(memory_definitions)
        logger.info("=" * 60)
        logger.info("迁移完成")
        logger.info(f"总计: {stats['total']}")
        logger.info(f"成功: {stats['migrated']}")
        logger.info(f"跳过: {stats['skipped']}")
        logger.info(f"失败: {stats['failed']}")
        logger.info("=" * 60)
        
        if stats['failed'] > 0:
            logger.error(f"有 {stats['failed']} 个工作流迁移失败，请检查日志")
            return False
        
        # 验证迁移结果
        logger.info("开始验证迁移结果...")
        db_workflows = repo.list_workflow_definitions(status="active")
        logger.info(f"数据库中共有 {len(db_workflows)} 个工作流定义")
        
        for wf in db_workflows:
            logger.info(f"  - {wf.id}: {wf.name}")
        
        # 检查数量是否一致
        if len(db_workflows) != len(memory_definitions):
            logger.error(f"数据不一致: 内存 {len(memory_definitions)} 个，数据库 {len(db_workflows)} 个")
            return False
        
        logger.info("✓ 数据迁移验证通过")
        return True
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}", exc_info=True)
        return False


def verify_migration():
    """
    验证迁移结果
    """
    logger.info("=" * 60)
    logger.info("开始验证迁移结果")
    logger.info("=" * 60)
    
    repo = WorkflowRepository()
    
    # 获取内存中的工作流定义
    memory_definitions = _WORKFLOW_DEFINITIONS_RAW
    
    # 获取数据库中的工作流定义
    db_workflows = repo.list_workflow_definitions(status="active")
    
    # 转换为字典以便比较
    db_definitions = {wf.id: wf.definition for wf in db_workflows}
    
    # 比较数量
    if len(memory_definitions) != len(db_definitions):
        logger.error(f"数量不一致: 内存 {len(memory_definitions)} 个，数据库 {len(db_definitions)} 个")
        return False
    
    # 比较每个工作流定义
    for wf_key in memory_definitions:
        if wf_key not in db_definitions:
            logger.error(f"工作流 {wf_key} 在数据库中不存在")
            return False
        
        memory_def = memory_definitions[wf_key]
        db_def = db_definitions[wf_key]
        
        # 比较关键字段
        if memory_def.get("name") != db_def.get("name"):
            logger.error(f"工作流 {wf_key} 的名称不一致")
            return False
        
        if memory_def.get("steps") != db_def.get("steps"):
            logger.error(f"工作流 {wf_key} 的步骤不一致")
            return False
    
    logger.info("✓ 所有工作流定义验证通过")
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Workflow数据迁移脚本")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证迁移结果，不执行迁移"
    )
    args = parser.parse_args()
    
    if args.verify_only:
        success = verify_migration()
    else:
        success = migrate_workflow_definitions()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
