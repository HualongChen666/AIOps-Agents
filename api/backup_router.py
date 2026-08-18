# -*- coding: utf-8 -*-
"""
Backup Router Module
====================

Provides API endpoints for backup management.
Supports database backups, full system backups, and backup cleanup.

Endpoints:
- GET /api/v1/backup/list - List all backups
- POST /api/v1/backup/database - Create database backup
- POST /api/v1/backup/full - Create full system backup
- DELETE /api/v1/backup/cleanup - Clean up old backups

🔧 P1-6: Disaster Recovery - Backup and Restore API
提供备份和恢复的API端点
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

router = APIRouter(prefix="/api/v1/backup", tags=["备份和恢复"])


@router.post(
    "/database",
    summary="备份数据库",
    responses={
        200: {
            "description": "数据库备份成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backup_file": "/backups/db_backup_20260702.sql",
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Database backup completed successfully",
                    }
                }
            },
        },
        500: {"description": "备份数据库失败"},
    },
)
async def backup_database(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    🔧 P1-6: 备份数据库

    Returns:
        备份结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()
        backup_file = dr.backup_database()

        if backup_file:
            background_tasks.add_task(dr.cleanup_old_backups, 30)
            return {
                "status": "success",
                "backup_file": backup_file,
                "timestamp": datetime.now().isoformat(),
                "message": "Database backup completed successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Database backup failed")
    except Exception as e:
        logger.error(f"备份数据库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"备份数据库失败: {str(e)[:200]}")


@router.post(
    "/redis",
    summary="备份Redis",
    responses={
        200: {
            "description": "Redis备份成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backup_file": "/backups/redis_backup_20260702.rdb",
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Redis backup completed successfully",
                    }
                }
            },
        },
        500: {"description": "备份Redis失败"},
    },
)
async def backup_redis(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    🔧 P1-6: 备份Redis

    Returns:
        备份结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()
        backup_file = dr.backup_redis()

        if backup_file:
            return {
                "status": "success",
                "backup_file": backup_file,
                "timestamp": datetime.now().isoformat(),
                "message": "Redis backup completed successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Redis backup failed")
    except Exception as e:
        logger.error(f"备份Redis失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"备份Redis失败: {str(e)[:200]}")


@router.post(
    "/configuration",
    summary="备份配置",
    responses={
        200: {
            "description": "配置备份成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backup_dir": "/backups/config_20260702",
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Configuration backup completed successfully",
                    }
                }
            },
        },
        500: {"description": "备份配置失败"},
    },
)
async def backup_configuration() -> Dict[str, Any]:
    """
    🔧 P1-6: 备份配置文件

    Returns:
        备份结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()
        backup_dir = dr.backup_configuration()

        if backup_dir:
            return {
                "status": "success",
                "backup_dir": backup_dir,
                "timestamp": datetime.now().isoformat(),
                "message": "Configuration backup completed successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Configuration backup failed")
    except Exception as e:
        logger.error(f"备份配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"备份配置失败: {str(e)[:200]}")


@router.post(
    "/full",
    summary="完整备份",
    responses={
        200: {
            "description": "完整备份成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backups": {
                            "database": "/backups/db_backup_20260702.sql",
                            "redis": "/backups/redis_backup_20260702.rdb",
                            "configuration": "/backups/config_20260702",
                        },
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Full backup completed successfully",
                    }
                }
            },
        },
        500: {"description": "完整备份失败"},
    },
)
async def full_backup(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    🔧 P1-6: 完整备份（数据库+Redis+配置）

    Returns:
        完整备份结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()

        # 并行执行备份
        db_backup, redis_backup, config_backup = await asyncio.gather(
            asyncio.to_thread(dr.backup_database),
            asyncio.to_thread(dr.backup_redis),
            asyncio.to_thread(dr.backup_configuration),
        )

        background_tasks.add_task(dr.cleanup_old_backups, 30)

        return {
            "status": "success",
            "backups": {
                "database": db_backup,
                "redis": redis_backup,
                "configuration": config_backup,
            },
            "timestamp": datetime.now().isoformat(),
            "message": "Full backup completed successfully",
        }
    except Exception as e:
        logger.error(f"完整备份失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"完整备份失败: {str(e)[:200]}")


@router.post(
    "/restore/database",
    summary="恢复数据库",
    responses={
        200: {
            "description": "数据库恢复成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backup_file": "/backups/db_backup_20260702.sql",
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Database restore completed successfully",
                    }
                }
            },
        },
        500: {"description": "恢复数据库失败"},
    },
)
async def restore_database(backup_file: str) -> Dict[str, Any]:
    """
    🔧 P1-6: 恢复数据库

    Args:
        backup_file: 备份文件路径

    Returns:
        恢复结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()
        success = dr.restore_database(backup_file)

        if success:
            return {
                "status": "success",
                "backup_file": backup_file,
                "timestamp": datetime.now().isoformat(),
                "message": "Database restore completed successfully",
            }
        else:
            raise HTTPException(status_code=500, detail="Database restore failed")
    except Exception as e:
        logger.error(f"恢复数据库失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复数据库失败: {str(e)[:200]}")


@router.get(
    "/list",
    summary="列出备份文件",
    responses={
        200: {
            "description": "备份文件列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backups": [
                            {
                                "name": "db_backup_20260702.sql",
                                "size": 1024000,
                                "created": "2026-07-02T10:30:00Z",
                                "modified": "2026-07-02T10:30:00Z",
                            }
                        ],
                        "count": 1,
                        "timestamp": "2026-07-02T10:30:00Z",
                    }
                }
            },
        },
        500: {"description": "列出备份文件失败"},
    },
)
async def list_backups() -> Dict[str, Any]:
    """
    🔧 P1-6: 列出所有备份文件

    Returns:
        备份文件列表
    """
    try:
        backup_dir = Path("C:/AIOps_Agent_bak/backups")
        if not backup_dir.exists():
            return {"status": "success", "backups": [], "message": "No backups found"}

        backups = []
        for backup_file in backup_dir.iterdir():
            if backup_file.is_file():
                stat = backup_file.stat()
                backups.append(
                    {
                        "name": backup_file.name,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        # 按修改时间排序
        backups.sort(key=lambda x: str(x["modified"]), reverse=True)

        return {
            "status": "success",
            "backups": backups,
            "count": len(backups),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"列出备份文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出备份文件失败: {str(e)[:200]}")


@router.delete(
    "/cleanup",
    summary="清理旧备份",
    responses={
        200: {
            "description": "清理成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "retention_days": 30,
                        "timestamp": "2026-07-02T10:30:00Z",
                        "message": "Old backups cleaned up (retention: 30 days)",
                    }
                }
            },
        },
        500: {"description": "清理旧备份失败"},
    },
)
async def cleanup_old_backups(retention_days: int = 30) -> Dict[str, Any]:
    """
    🔧 P1-6: 清理旧备份

    Args:
        retention_days: 保留天数

    Returns:
        清理结果
    """
    try:
        from core.disaster_recovery import DisasterRecovery

        dr = DisasterRecovery()
        success = dr.cleanup_old_backups(retention_days)

        if success:
            return {
                "status": "success",
                "retention_days": retention_days,
                "timestamp": datetime.now().isoformat(),
                "message": f"Old backups cleaned up (retention: {retention_days} days)",
            }
        else:
            raise HTTPException(status_code=500, detail="Cleanup failed")
    except Exception as e:
        logger.error(f"清理旧备份失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清理旧备份失败: {str(e)[:200]}")
