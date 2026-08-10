# -*- coding: utf-8 -*-
"""
Backup and Recovery Manager for AIOps Platform
Provides automated backup and recovery using Wal-G for PostgreSQL and S3 for storage
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from config import POSTGRES_DATABASE, POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER
from core.security import subprocess_runner

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Backup type enumeration"""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """Backup status enumeration"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BackupInfo:
    """Represents a backup information"""

    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    size_bytes: int = 0
    location: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "size_bytes": self.size_bytes,
            "location": self.location,
            "error": self.error,
        }


class BackupManager:
    """
    Backup and Recovery Manager

    Manages automated backups using Wal-G for PostgreSQL and S3 for storage.
    Supports full, incremental, and differential backups with retention policies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Backup Manager

        Args:
            config: Configuration dictionary containing:
                - wal_g_path: Path to Wal-G binary
                - pg_host: PostgreSQL host
                - pg_port: PostgreSQL port
                - pg_database: PostgreSQL database
                - pg_user: PostgreSQL user
                - s3_bucket: S3 bucket name
                - s3_endpoint: S3 endpoint URL
                - aws_access_key: AWS access key
                - aws_secret_key: AWS secret key
                - retention_days: Number of days to retain backups
        """
        self.config = config
        self.wal_g_path = config.get("wal_g_path", "wal-g")
        self.pg_host = config.get("pg_host", POSTGRES_HOST)
        self.pg_port = config.get("pg_port", POSTGRES_PORT)
        self.pg_database = config.get("pg_database", POSTGRES_DATABASE)
        self.pg_user = config.get("pg_user", POSTGRES_USER)
        self.pg_password = config.get("pg_password", POSTGRES_PASSWORD)
        self.s3_bucket = config.get("s3_bucket", os.getenv("S3_BUCKET", "aiops-backups"))
        self.s3_endpoint = config.get(
            "s3_endpoint", os.getenv("S3_ENDPOINT", "https://s3.amazonaws.com")
        )
        self.aws_access_key = config.get("aws_access_key", os.getenv("AWS_ACCESS_KEY"))
        self.aws_secret_key = config.get("aws_secret_key", os.getenv("AWS_SECRET_KEY"))
        self.retention_days = config.get("retention_days", 7)

        self._backups: Dict[str, BackupInfo] = {}
        self._is_initialized = False

        logger.info(f"Backup Manager initialized for database: {self.pg_database}")

    def initialize(self) -> bool:
        """
        Initialize backup manager

        Returns:
            True if initialization successful
        """
        try:
            # Set environment variables for Wal-G
            os.environ["WALG_S3_PREFIX"] = f"s3://{self.s3_bucket}"
            os.environ["AWS_ACCESS_KEY_ID"] = self.aws_access_key or ""
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.aws_secret_key or ""
            os.environ["AWS_ENDPOINT"] = self.s3_endpoint
            os.environ["PGHOST"] = self.pg_host
            os.environ["PGPORT"] = str(self.pg_port)
            os.environ["PGDATABASE"] = self.pg_database
            os.environ["PGUSER"] = self.pg_user

            # Check Wal-G availability
            result = subprocess_runner.run(
                [self.wal_g_path, "version"], capture_output=True, text=True, shell=False
            )

            if result.returncode == 0:
                self._is_initialized = True
                logger.info("Backup Manager initialized successfully")
                return True
            else:
                logger.error(f"Wal-G not available: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize backup manager: {e}")
            return False

    async def create_backup(self, backup_type: BackupType = BackupType.FULL) -> BackupInfo:
        """
        Create a backup

        Args:
            backup_type: Type of backup to create

        Returns:
            BackupInfo object
        """
        if not self._is_initialized:
            raise RuntimeError("Backup manager not initialized")

        backup_id = f"{backup_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_info = BackupInfo(
            backup_id=backup_id,
            backup_type=backup_type,
            status=BackupStatus.RUNNING,
            start_time=datetime.now(),
        )

        self._backups[backup_id] = backup_info

        try:
            logger.info(f"Starting {backup_type.value} backup: {backup_id}")

            # Build Wal-G backup command
            cmd = [self.wal_g_path, "backup-push"]

            if backup_type == BackupType.FULL:
                cmd.append("--full")
            elif backup_type == BackupType.DIFFERENTIAL:
                cmd.append("--detail")

            # Execute backup
            result = subprocess_runner.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                backup_info.status = BackupStatus.COMPLETED
                backup_info.end_time = datetime.now()
                backup_info.location = f"s3://{self.s3_bucket}/{backup_id}"

                # Get backup size
                backup_info.size_bytes = self._get_backup_size(backup_id)

                logger.info(f"Backup completed successfully: {backup_id}")
            else:
                backup_info.status = BackupStatus.FAILED
                backup_info.end_time = datetime.now()
                backup_info.error = result.stderr
                logger.error(f"Backup failed: {backup_id} - {result.stderr}")

        except subprocess_runner.TimeoutExpired:
            backup_info.status = BackupStatus.FAILED
            backup_info.end_time = datetime.now()
            backup_info.error = "Backup timeout"
            logger.error(f"Backup timeout: {backup_id}")
        except Exception as e:
            backup_info.status = BackupStatus.FAILED
            backup_info.end_time = datetime.now()
            backup_info.error = str(e)
            logger.error(f"Backup error: {backup_id} - {e}")

        return backup_info

    def _get_backup_size(self, backup_id: str) -> int:
        """
        Get backup size from S3

        Args:
            backup_id: Backup ID

        Returns:
            Size in bytes
        """
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.aws_access_key or "",
                aws_secret_access_key=self.aws_secret_key or "",
            )
            total = 0
            prefix = backup_id
            if not prefix.endswith("/"):
                prefix += "/"
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    total += obj.get("Size", 0)
            return total
        except Exception as e:
            logger.error(f"Failed to get backup size: {e}")
            return 0

    async def restore_backup(self, backup_id: str, target_time: Optional[datetime] = None) -> bool:
        """
        Restore from backup

        Args:
            backup_id: Backup ID to restore
            target_time: Optional point-in-time recovery target

        Returns:
            True if restore successful
        """
        if not self._is_initialized:
            raise RuntimeError("Backup manager not initialized")

        if backup_id not in self._backups:
            logger.error(f"Backup not found: {backup_id}")
            return False

        backup_info = self._backups[backup_id]

        if backup_info.status != BackupStatus.COMPLETED:
            logger.error(f"Backup not completed: {backup_id}")
            return False

        try:
            logger.info(f"Starting restore from backup: {backup_id}")

            # Build Wal-G restore command
            cmd = [self.wal_g_path, "backup-fetch", backup_info.location]

            if target_time:
                cmd.extend(["--target-time", target_time.isoformat()])

            # Execute restore
            result = subprocess_runner.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,
                timeout=7200,  # 2 hour timeout
            )

            if result.returncode == 0:
                logger.info(f"Restore completed successfully: {backup_id}")
                return True
            else:
                logger.error(f"Restore failed: {backup_id} - {result.stderr}")
                return False

        except subprocess_runner.TimeoutExpired:
            logger.error(f"Restore timeout: {backup_id}")
            return False
        except Exception as e:
            logger.error(f"Restore error: {backup_id} - {e}")
            return False

    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all backups

        Returns:
            List of backup information dictionaries
        """
        try:
            # Build Wal-G list command
            cmd = [self.wal_g_path, "backup-list"]

            result = subprocess_runner.run(
                cmd,
                capture_output=True,
                text=True,
                shell=False,
            )

            if result.returncode == 0:
                # Parse JSON output
                backups = json.loads(result.stdout)
                return backups if isinstance(backups, list) else []
            else:
                logger.error(f"Failed to list backups: {result.stderr}")
                return []

        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    async def cleanup_old_backups(self) -> int:
        """
        Clean up old backups based on retention policy

        Returns:
            Number of backups cleaned up
        """
        if not self._is_initialized:
            raise RuntimeError("Backup manager not initialized")

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        cleaned_count = 0

        try:
            backups = await self.list_backups()

            for backup in backups:
                backup_time = datetime.fromisoformat(backup.get("start_time", ""))

                if backup_time < cutoff_date:
                    # Delete old backup
                    backup_name = backup.get("backup_name")
                    cmd = [self.wal_g_path, "backup-delete", backup_name, "--confirm"]

                    result = subprocess_runner.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        shell=False,
                    )

                    if result.returncode == 0:
                        cleaned_count += 1
                        logger.info(f"Deleted old backup: {backup_name}")
                    else:
                        logger.error(f"Failed to delete backup: {backup_name}")

            logger.info(f"Cleaned up {cleaned_count} old backups")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0

    def get_backup_status(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Get backup status

        Args:
            backup_id: Backup ID

        Returns:
            Backup status dictionary or None
        """
        if backup_id in self._backups:
            return self._backups[backup_id].to_dict()
        return None

    def get_all_backup_statuses(self) -> List[Dict[str, Any]]:
        """
        Get all backup statuses

        Returns:
            List of backup status dictionaries
        """
        return [backup.to_dict() for backup in self._backups.values()]

    def schedule_backup(
        self, backup_type: BackupType = BackupType.FULL, schedule: str = "0 2 * * *"
    ) -> bool:
        """
        Schedule automated backup using the task scheduler.

        Args:
            backup_type: Type of backup to schedule
            schedule: Cron schedule expression

        Returns:
            True if scheduled successfully
        """
        try:
            from core.task_scheduler import scheduler

            async def _backup_job() -> None:
                await self.create_backup(backup_type)

            scheduler.schedule_task(
                f"backup_{backup_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                _backup_job,
                cron=schedule,
            )
            logger.info(f"Scheduled {backup_type.value} backup with schedule: {schedule}")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule backup: {e}")
            return False


def create_backup_manager(config: Dict[str, Any]) -> Optional[BackupManager]:
    """
    Factory function to create Backup Manager

    Args:
        config: Configuration dictionary

    Returns:
        BackupManager instance or None if failed
    """
    try:
        manager = BackupManager(config)
        if manager.initialize():
            return manager
        return None
    except Exception as e:
        logger.error(f"Failed to create backup manager: {e}")
        return None
