# -*- coding: utf-8 -*-
# scripts/rollback_workflow_migration.py
# Workflow数据迁移回滚脚本
# 将数据库中的工作流定义回滚到内存存储

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


def rollback_workflow_definitions():
    """
    将数据库中的工作流定义回滚到内存存储
    """
    logger.info("=" * 60)
    logger.info("开始Workflow数据回滚")
    logger.info("=" * 60)
    
    # 创建Repository实例
    repo = WorkflowRepository()
    
    # 获取数据库中的工作流定义
    db_workflows = repo.list_workflow_definitions(status="active")
    logger.info(f"数据库中共有 {len(db_workflows)} 个工作流定义")
    
    # 打印数据库中的工作流定义
    for wf in db_workflows:
        logger.info(f"  - {wf.id}: {wf.name}")
    
    # 备份内存中的定义
    backup_memory = _WORKFLOW_DEFINITIONS_RAW.copy()
    logger.info(f"已备份内存中的 {len(backup_memory)} 个工作流定义")
    
    # 清空内存中的定义
    _WORKFLOW_DEFINITIONS_RAW.clear()
    logger.info("已清空内存中的工作流定义")
    
    # 从数据库恢复到内存
    success_count = 0
    for wf in db_workflows:
        try:
            _WORKFLOW_DEFINITIONS_RAW[wf.id] = wf.definition
            success_count += 1
            logger.info(f"已恢复工作流定义: {wf.id}")
        except Exception as e:
            logger.error(f"恢复工作流定义 {wf.id} 失败: {e}")
    
    logger.info("=" * 60)
    logger.info("回滚完成")
    logger.info(f"总计: {len(db_workflows)}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {len(db_workflows) - success_count}")
    logger.info("=" * 60)
    
    if success_count != len(db_workflows):
        logger.error("回滚过程中有失败，恢复备份")
        _WORKFLOW_DEFINITIONS_RAW.clear()
        _WORKFLOW_DEFINITIONS_RAW.update(backup_memory)
        return False
    
    # 验证回滚结果
    logger.info("开始验证回滚结果...")
    logger.info(f"内存中共有 {len(_WORKFLOW_DEFINITIONS_RAW)} 个工作流定义")
    
    for wf_key, definition in _WORKFLOW_DEFINITIONS_RAW.items():
        logger.info(f"  - {wf_key}: {definition.get('name', 'N/A')}")
    
    # 检查数量是否一致
    if len(_WORKFLOW_DEFINITIONS_RAW) != len(db_workflows):
        logger.error(f"数据不一致: 数据库 {len(db_workflows)} 个，内存 {len(_WORKFLOW_DEFINITIONS_RAW)} 个")
        return False
    
    logger.info("✓ 数据回滚验证通过")
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Workflow数据回滚脚本")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示将要回滚的数据，不实际执行回滚"
    )
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("Dry run模式 - 仅显示将要回滚的数据")
        repo = WorkflowRepository()
        db_workflows = repo.list_workflow_definitions(status="active")
        logger.info(f"数据库中共有 {len(db_workflows)} 个工作流定义")
        for wf in db_workflows:
            logger.info(f"  - {wf.id}: {wf.name}")
        sys.exit(0)
    
    success = rollback_workflow_definitions()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
