# -*- coding: utf-8 -*-
"""
Disaster Router Module
======================

Provides API endpoints for disaster recovery and backup management.
Supports 12 different disaster recovery and backup-related endpoints.

Endpoints:
- GET /api/disaster/backup-management - Backup management overview
- GET /api/disaster/disaster-recovery - Disaster recovery status
- GET /api/disaster/dr-scenarios - DR scenarios list
- GET /api/disaster/backup-recovery - Backup recovery status
- GET /api/disaster/backup-strategy - Backup strategy configuration
- GET /api/disaster/data-backup - Data backup status
- GET /api/disaster/dr-drill - DR drill execution status
- GET /api/disaster/dr-testing - DR testing results
- GET /api/disaster/ha-configuration - High availability configuration
- GET /api/disaster/pgbackrest - PgBackRest backup status
- GET /api/disaster/recovery-plan - Recovery plan details
- GET /api/disaster/velero - Velero backup status
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from core.auth_db import User, get_session
from core.auth_service import get_current_user
from core.disaster_recovery import DisasterRecovery
from core.disaster_recovery_drill import (
    DisasterRecoveryDrill,
    DrillScenario,
    DrillStatus,
    disaster_recovery_drill,
)

router = APIRouter(prefix="/api/disaster", tags=["灾难恢复和备份管理"])


def _get_backup_dir() -> Path:
    """Get backup directory from environment variable."""
    backup_dir = os.getenv("AIOPS_BACKUP_DIR", "C:/AIOps_Agent_bak/backups")
    return Path(backup_dir)


def _get_retention_days() -> int:
    """Get backup retention days from environment variable."""
    return int(os.getenv("AIOPS_BACKUP_RETENTION_DAYS", "30"))


def _get_dr_enabled() -> bool:
    """Check if disaster recovery is enabled."""
    return os.getenv("AIOPS_DR_ENABLED", "true").lower() == "true"


@router.get(
    "/backup-management",
    summary="备份管理概览",
    responses={
        200: {
            "description": "备份管理概览",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "backup_count": 10,
                        "total_size_mb": 1024,
                        "last_backup": "2026-07-02T10:30:00Z",
                        "retention_days": 30,
                        "backup_dir": "/backups",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_backup_management(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取备份管理概览信息

    Returns:
        备份管理概览数据
    """
    try:
        logger.info(f"User {current_user.username} requesting backup management overview")

        backup_dir = _get_backup_dir()
        retention_days = _get_retention_days()

        if not backup_dir.exists():
            return {
                "status": "success",
                "backup_count": 0,
                "total_size_mb": 0,
                "last_backup": None,
                "retention_days": retention_days,
                "backup_dir": str(backup_dir),
                "message": "Backup directory does not exist",
            }

        # Calculate backup statistics
        backup_files = list(backup_dir.glob("*"))
        backup_count = len(backup_files)
        total_size = sum(f.stat().st_size for f in backup_files if f.is_file())
        total_size_mb = round(total_size / (1024 * 1024), 2)

        # Find last backup
        last_backup = None
        if backup_files:
            latest_file = max(backup_files, key=lambda f: f.stat().st_mtime)
            last_backup = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()

        logger.info(f"Backup management overview retrieved: {backup_count} backups, {total_size_mb} MB")

        return {
            "status": "success",
            "backup_count": backup_count,
            "total_size_mb": total_size_mb,
            "last_backup": last_backup,
            "retention_days": retention_days,
            "backup_dir": str(backup_dir),
        }
    except Exception as e:
        logger.error(f"Failed to get backup management overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup management overview: {str(e)[:200]}"
        )


@router.get(
    "/disaster-recovery",
    summary="灾难恢复状态",
    responses={
        200: {
            "description": "灾难恢复状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "dr_enabled": True,
                        "last_dr_test": "2026-07-02T10:30:00Z",
                        "dr_status": "healthy",
                        "recovery_time_objective_minutes": 60,
                        "recovery_point_objective_minutes": 15,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_disaster_recovery_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取灾难恢复状态

    Returns:
        灾难恢复状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting disaster recovery status")

        dr_enabled = _get_dr_enabled()
        rto_minutes = int(os.getenv("AIOPS_RTO_MINUTES", "60"))
        rpo_minutes = int(os.getenv("AIOPS_RPO_MINUTES", "15"))

        # Check backup directory health
        backup_dir = _get_backup_dir()
        dr_status = "healthy"
        if not backup_dir.exists():
            dr_status = "unhealthy"
        elif not any(backup_dir.glob("*")):
            dr_status = "warning"

        # Get last DR test time from drill history
        last_dr_test = None
        try:
            from core.disaster_recovery_drill import disaster_recovery_drill
            history = disaster_recovery_drill.get_drill_history(limit=1)
            if history:
                last_dr_test = history[0].start_time.isoformat()
        except Exception as e:
            logger.warning(f"Failed to get DR drill history: {e}")

        logger.info(f"Disaster recovery status: {dr_status}, enabled: {dr_enabled}")

        return {
            "status": "success",
            "dr_enabled": dr_enabled,
            "last_dr_test": last_dr_test,
            "dr_status": dr_status,
            "recovery_time_objective_minutes": rto_minutes,
            "recovery_point_objective_minutes": rpo_minutes,
        }
    except Exception as e:
        logger.error(f"Failed to get disaster recovery status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get disaster recovery status: {str(e)[:200]}"
        )


@router.get(
    "/dr-scenarios",
    summary="DR场景列表",
    responses={
        200: {
            "description": "DR场景列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "scenarios": [
                            {
                                "name": "database_failover",
                                "description": "Database failover scenario",
                                "enabled": True,
                            }
                        ],
                        "count": 5,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_dr_scenarios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取DR场景列表

    Returns:
        DR场景列表
    """
    try:
        logger.info(f"User {current_user.username} requesting DR scenarios")

        scenarios = []
        for scenario in DrillScenario:
            scenario_info = {
                "name": scenario.value,
                "description": scenario.value.replace("_", " ").title(),
                "enabled": True,
            }
            scenarios.append(scenario_info)

        logger.info(f"Retrieved {len(scenarios)} DR scenarios")

        return {
            "status": "success",
            "scenarios": scenarios,
            "count": len(scenarios),
        }
    except Exception as e:
        logger.error(f"Failed to get DR scenarios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DR scenarios: {str(e)[:200]}"
        )


@router.get(
    "/backup-recovery",
    summary="备份恢复状态",
    responses={
        200: {
            "description": "备份恢复状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "recoverable_backups": 5,
                        "last_recovery": "2026-07-02T10:30:00Z",
                        "recovery_status": "ready",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_backup_recovery_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取备份恢复状态

    Returns:
        备份恢复状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting backup recovery status")

        backup_dir = _get_backup_dir()
        recoverable_backups = 0
        last_recovery = None
        recovery_status = "ready"

        if backup_dir.exists():
            # Count recoverable backups (SQL and RDB files)
            try:
                recoverable_backups = len(list(backup_dir.glob("*.sql"))) + len(list(backup_dir.glob("*.rdb")))
            except Exception:
                recoverable_backups = 0

            # Check for recent recovery by looking at restore logs
            try:
                restore_log = backup_dir / "restore.log"
                if restore_log.exists():
                    last_recovery = datetime.fromtimestamp(restore_log.stat().st_mtime).isoformat()
            except Exception:
                last_recovery = None

            if recoverable_backups == 0:
                recovery_status = "no_backups"
            elif recoverable_backups < 3:
                recovery_status = "warning"

        logger.info(f"Backup recovery status: {recovery_status}, recoverable: {recoverable_backups}")

        return {
            "status": "success",
            "recoverable_backups": recoverable_backups,
            "last_recovery": last_recovery,
            "recovery_status": recovery_status,
        }
    except Exception as e:
        logger.error(f"Failed to get backup recovery status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup recovery status: {str(e)[:200]}"
        )


@router.get(
    "/backup-strategy",
    summary="备份策略配置",
    responses={
        200: {
            "description": "备份策略配置",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "strategy": {
                            "backup_type": "full",
                            "schedule": "daily",
                            "retention_days": 30,
                            "compression_enabled": True,
                            "encryption_enabled": True,
                        },
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_backup_strategy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取备份策略配置

    Returns:
        备份策略配置数据
    """
    try:
        logger.info(f"User {current_user.username} requesting backup strategy")

        strategy = {
            "backup_type": os.getenv("AIOPS_BACKUP_TYPE", "full"),
            "schedule": os.getenv("AIOPS_BACKUP_SCHEDULE", "daily"),
            "retention_days": _get_retention_days(),
            "compression_enabled": os.getenv("AIOPS_BACKUP_COMPRESSION", "true").lower() == "true",
            "encryption_enabled": os.getenv("AIOPS_BACKUP_ENCRYPTION", "true").lower() == "true",
            "incremental_enabled": os.getenv("AIOPS_BACKUP_INCREMENTAL", "false").lower() == "true",
        }

        logger.info(f"Backup strategy retrieved: {strategy}")

        return {
            "status": "success",
            "strategy": strategy,
        }
    except Exception as e:
        logger.error(f"Failed to get backup strategy: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup strategy: {str(e)[:200]}"
        )


@router.get(
    "/data-backup",
    summary="数据备份状态",
    responses={
        200: {
            "description": "数据备份状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "database_backups": 5,
                        "redis_backups": 5,
                        "config_backups": 5,
                        "total_backups": 15,
                        "last_data_backup": "2026-07-02T10:30:00Z",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_data_backup_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取数据备份状态

    Returns:
        数据备份状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting data backup status")

        backup_dir = _get_backup_dir()
        database_backups = 0
        redis_backups = 0
        config_backups = 0
        last_data_backup = None

        if backup_dir.exists():
            database_backups = len(list(backup_dir.glob("db_backup_*.sql")))
            redis_backups = len(list(backup_dir.glob("redis_backup_*.rdb")))
            config_backups = len(list(backup_dir.glob("config_*")))

            # Find last data backup
            all_backups = list(backup_dir.glob("*"))
            if all_backups:
                latest_backup = max(all_backups, key=lambda f: f.stat().st_mtime)
                last_data_backup = datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()

        total_backups = database_backups + redis_backups + config_backups

        logger.info(f"Data backup status: {total_backups} total backups")

        return {
            "status": "success",
            "database_backups": database_backups,
            "redis_backups": redis_backups,
            "config_backups": config_backups,
            "total_backups": total_backups,
            "last_data_backup": last_data_backup,
        }
    except Exception as e:
        logger.error(f"Failed to get data backup status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data backup status: {str(e)[:200]}"
        )


@router.get(
    "/dr-drill",
    summary="DR演练执行状态",
    responses={
        200: {
            "description": "DR演练执行状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "current_drill": None,
                        "last_drill": {
                            "scenario": "database_failover",
                            "status": "completed",
                            "success": True,
                            "duration_seconds": 120,
                        },
                        "drill_count": 10,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_dr_drill_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取DR演练执行状态

    Returns:
        DR演练状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting DR drill status")

        from core.disaster_recovery_drill import disaster_recovery_drill

        history = disaster_recovery_drill.get_drill_history(limit=10)
        drill_count = len(history)

        current_drill = None
        last_drill = None

        if history:
            # Check if there's a running drill
            for drill in reversed(history):
                if drill.status == DrillStatus.RUNNING:
                    current_drill = {
                        "scenario": drill.scenario.value,
                        "status": drill.status.value,
                        "start_time": drill.start_time.isoformat(),
                        "duration_seconds": drill.duration_seconds,
                    }
                    break

            # Get last completed drill
            last_drill = history[-1]
            last_drill_data = {
                "scenario": last_drill.scenario.value,
                "status": last_drill.status.value,
                "success": last_drill.success,
                "duration_seconds": last_drill.duration_seconds,
                "start_time": last_drill.start_time.isoformat(),
                "end_time": last_drill.end_time.isoformat() if last_drill.end_time else None,
            }
        else:
            last_drill_data = None

        logger.info(f"DR drill status: {drill_count} drills, current: {current_drill is not None}")

        return {
            "status": "success",
            "current_drill": current_drill,
            "last_drill": last_drill_data,
            "drill_count": drill_count,
        }
    except Exception as e:
        logger.error(f"Failed to get DR drill status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DR drill status: {str(e)[:200]}"
        )


@router.get(
    "/dr-testing",
    summary="DR测试结果",
    responses={
        200: {
            "description": "DR测试结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "test_results": [
                            {
                                "scenario": "database_failover",
                                "success": True,
                                "last_test": "2026-07-02T10:30:00Z",
                            }
                        ],
                        "success_rate": 90.0,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_dr_testing_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取DR测试结果

    Returns:
        DR测试结果数据
    """
    try:
        logger.info(f"User {current_user.username} requesting DR testing results")

        from core.disaster_recovery_drill import disaster_recovery_drill

        stats = disaster_recovery_drill.get_drill_stats()
        history = disaster_recovery_drill.get_drill_history(limit=50)

        test_results = []
        for drill in history:
            test_results.append({
                "scenario": drill.scenario.value,
                "success": drill.success,
                "status": drill.status.value,
                "last_test": drill.start_time.isoformat(),
                "duration_seconds": drill.duration_seconds,
            })

        success_rate = stats.get("success_rate", 0.0)

        logger.info(f"DR testing results: {len(test_results)} tests, success rate: {success_rate}%")

        return {
            "status": "success",
            "test_results": test_results,
            "success_rate": success_rate,
            "total_tests": stats.get("total_drills", 0),
            "successful_tests": stats.get("successful_drills", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get DR testing results: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DR testing results: {str(e)[:200]}"
        )


@router.get(
    "/ha-configuration",
    summary="高可用配置",
    responses={
        200: {
            "description": "高可用配置",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "ha_enabled": True,
                        "ha_mode": "active_passive",
                        "nodes": 2,
                        "load_balancer": "nginx",
                        "health_check_interval_seconds": 30,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_ha_configuration(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取高可用配置

    Returns:
        高可用配置数据
    """
    try:
        logger.info(f"User {current_user.username} requesting HA configuration")

        ha_config = {
            "ha_enabled": os.getenv("AIOPS_HA_ENABLED", "false").lower() == "true",
            "ha_mode": os.getenv("AIOPS_HA_MODE", "active_passive"),
            "nodes": int(os.getenv("AIOPS_HA_NODES", "2")),
            "load_balancer": os.getenv("AIOPS_HA_LOAD_BALANCER", "nginx"),
            "health_check_interval_seconds": int(os.getenv("AIOPS_HA_HEALTH_CHECK_INTERVAL", "30")),
            "failover_timeout_seconds": int(os.getenv("AIOPS_HA_FAILOVER_TIMEOUT", "60")),
            "auto_failover_enabled": os.getenv("AIOPS_HA_AUTO_FAILOVER", "true").lower() == "true",
        }

        logger.info(f"HA configuration retrieved: enabled={ha_config['ha_enabled']}")

        return {
            "status": "success",
            "ha_configuration": ha_config,
        }
    except Exception as e:
        logger.error(f"Failed to get HA configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get HA configuration: {str(e)[:200]}"
        )


@router.get(
    "/pgbackrest",
    summary="PgBackRest备份状态",
    responses={
        200: {
            "description": "PgBackRest备份状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "pgbackrest_enabled": True,
                        "repo_count": 2,
                        "last_backup": "2026-07-02T10:30:00Z",
                        "backup_type": "full",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_pgbackrest_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取PgBackRest备份状态

    Returns:
        PgBackRest备份状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting PgBackRest status")

        pgbackrest_enabled = os.getenv("AIOPS_PGBACKREST_ENABLED", "false").lower() == "true"
        repo_count = int(os.getenv("AIOPS_PGBACKREST_REPO_COUNT", "2"))
        backup_type = os.getenv("AIOPS_PGBACKREST_BACKUP_TYPE", "full")

        # Check if PgBackRest is actually installed and configured
        pgbackrest_available = False
        try:
            import shutil
            pgbackrest_available = shutil.which("pgbackrest") is not None
        except Exception:
            pgbackrest_available = False

        last_backup = None
        if pgbackrest_available and pgbackrest_enabled:
            # Try to get last backup info from backup directory
            backup_dir = _get_backup_dir()
            pgbackrest_dir = backup_dir / "pgbackrest"
            if pgbackrest_dir.exists():
                backups = list(pgbackrest_dir.glob("*"))
                if backups:
                    latest_backup = max(backups, key=lambda f: f.stat().st_mtime)
                    last_backup = datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()

        logger.info(f"PgBackRest status: enabled={pgbackrest_enabled}, available={pgbackrest_available}")

        return {
            "status": "success",
            "pgbackrest_enabled": pgbackrest_enabled,
            "pgbackrest_available": pgbackrest_available,
            "repo_count": repo_count,
            "last_backup": last_backup,
            "backup_type": backup_type,
        }
    except Exception as e:
        logger.error(f"Failed to get PgBackRest status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PgBackRest status: {str(e)[:200]}"
        )


@router.get(
    "/recovery-plan",
    summary="恢复计划详情",
    responses={
        200: {
            "description": "恢复计划详情",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "recovery_plan": {
                            "name": "Production Recovery Plan",
                            "version": "1.0",
                            "steps": [
                                {
                                    "step": 1,
                                    "action": "Verify backup integrity",
                                    "estimated_time_minutes": 5,
                                }
                            ],
                            "total_estimated_time_minutes": 60,
                        },
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_recovery_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取恢复计划详情

    Returns:
        恢复计划数据
    """
    try:
        logger.info(f"User {current_user.username} requesting recovery plan")

        # Build recovery plan based on configuration
        recovery_plan = {
            "name": os.getenv("AIOPS_RECOVERY_PLAN_NAME", "Production Recovery Plan"),
            "version": os.getenv("AIOPS_RECOVERY_PLAN_VERSION", "1.0"),
            "steps": [
                {
                    "step": 1,
                    "action": "Verify backup integrity",
                    "estimated_time_minutes": 5,
                    "critical": True,
                },
                {
                    "step": 2,
                    "action": "Stop affected services",
                    "estimated_time_minutes": 2,
                    "critical": True,
                },
                {
                    "step": 3,
                    "action": "Restore database from backup",
                    "estimated_time_minutes": 15,
                    "critical": True,
                },
                {
                    "step": 4,
                    "action": "Restore Redis data",
                    "estimated_time_minutes": 5,
                    "critical": True,
                },
                {
                    "step": 5,
                    "action": "Restore configuration files",
                    "estimated_time_minutes": 3,
                    "critical": True,
                },
                {
                    "step": 6,
                    "action": "Verify data consistency",
                    "estimated_time_minutes": 10,
                    "critical": True,
                },
                {
                    "step": 7,
                    "action": "Restart services",
                    "estimated_time_minutes": 5,
                    "critical": True,
                },
                {
                    "step": 8,
                    "action": "Run health checks",
                    "estimated_time_minutes": 10,
                    "critical": True,
                },
                {
                    "step": 9,
                    "action": "Verify application functionality",
                    "estimated_time_minutes": 5,
                    "critical": True,
                },
            ],
            "total_estimated_time_minutes": 60,
            "last_updated": datetime.now().isoformat(),
        }

        # Calculate total estimated time
        total_time = sum(step["estimated_time_minutes"] for step in recovery_plan["steps"])
        recovery_plan["total_estimated_time_minutes"] = total_time

        logger.info(f"Recovery plan retrieved: {len(recovery_plan['steps'])} steps, {total_time} minutes")

        return {
            "status": "success",
            "recovery_plan": recovery_plan,
        }
    except Exception as e:
        logger.error(f"Failed to get recovery plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recovery plan: {str(e)[:200]}"
        )


@router.get(
    "/velero",
    summary="Velero备份状态",
    responses={
        200: {
            "description": "Velero备份状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "velero_enabled": True,
                        "backup_location": "s3://backups",
                        "last_backup": "2026-07-02T10:30:00Z",
                        "schedule": "daily",
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "服务器错误"},
    },
)
async def get_velero_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> Dict[str, Any]:
    """
    获取Velero备份状态

    Returns:
        Velero备份状态数据
    """
    try:
        logger.info(f"User {current_user.username} requesting Velero status")

        velero_enabled = os.getenv("AIOPS_VELERO_ENABLED", "false").lower() == "true"
        backup_location = os.getenv("AIOPS_VELERO_BACKUP_LOCATION", "s3://backups")
        schedule = os.getenv("AIOPS_VELERO_SCHEDULE", "daily")

        # Check if Velero is actually installed
        velero_available = False
        try:
            import shutil
            velero_available = shutil.which("velero") is not None
        except Exception:
            velero_available = False

        last_backup = None
        if velero_available and velero_enabled:
            # Try to get last backup info from backup directory
            backup_dir = _get_backup_dir()
            velero_dir = backup_dir / "velero"
            if velero_dir.exists():
                backups = list(velero_dir.glob("*"))
                if backups:
                    latest_backup = max(backups, key=lambda f: f.stat().st_mtime)
                    last_backup = datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()

        logger.info(f"Velero status: enabled={velero_enabled}, available={velero_available}")

        return {
            "status": "success",
            "velero_enabled": velero_enabled,
            "velero_available": velero_available,
            "backup_location": backup_location,
            "last_backup": last_backup,
            "schedule": schedule,
        }
    except Exception as e:
        logger.error(f"Failed to get Velero status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Velero status: {str(e)[:200]}"
        )
