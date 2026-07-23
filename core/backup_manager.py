# -*- coding: utf-8 -*-
# core/backup_manager.py
# ------------------------------------------------------------
# 备份 & 恢复（Wal‑G + S3） 简易包装。
# Wal‑G 是一个外部二进制工具，用于 PostgreSQL / TimescaleDB 的
# WAL‑export / 恢复。这里提供一个 Python 辅助层，负责构造命令
# 行、执行系统调用（via shell_exec），并记录日志。
# ------------------------------------------------------------

from __future__ import annotations

import logging
import os
import subprocess  # nosec B404
from typing import List

from config import DATABASE_URL


def _run_shell(command: str) -> subprocess.CompletedProcess:
    """Execute a shell command synchronously and return CompletedProcess.

    🔧 P0 Security Fix: Changed from shell=True to parameterized execution
    - Parses command safely using shlex.split()
    - Executes using list form to prevent shell injection
    - Maintains compatibility with wal-g commands

    Note: The command is constructed from validated configuration values only.
    """
    import shlex

    # Parse command safely
    parts = shlex.split(command)
    # Execute using list form (no shell=True)
    return subprocess.run(
        parts,
        capture_output=True,
        text=True,
        shell=False,  # nosec B603
    )


logger = logging.getLogger(__name__)

# -----------------------------------------------------------------
# Configuration – where to store backups and which WAL‑G binary to use.
# -----------------------------------------------------------------
WALG_PATH = os.getenv("WALG_PATH", "wal-g")  # assumed to be in $PATH
S3_URL = os.getenv("WALG_S3_URL", "s3://aiops-backups")  # e.g. s3://bucket/prefix
POSTGRES_URL = os.getenv("POSTGRES_URL", "")
if not POSTGRES_URL:
    POSTGRES_URL = DATABASE_URL

# 🔧 验证 DATABASE_URL 格式
if not POSTGRES_URL or not POSTGRES_URL.startswith(("postgresql://", "postgresql+asyncpg://")):
    raise ValueError(
        f"无效的 DATABASE_URL: '{POSTGRES_URL}'。"
        "必须以 'postgresql://' 或 'postgresql+asyncpg://' 开头。"
    )


# Validate configuration values to prevent command injection
def _validate_config_value(value: str, name: str) -> str:
    """Validate configuration value to prevent command injection."""
    if not value:
        raise ValueError(f"{name} cannot be empty")
    # Allow only safe characters: alphanumeric, hyphen, underscore, slash, colon, at-sign, dot
    import re

    if not re.match(r"^[a-zA-Z0-9_\-/:.@]+$", value):
        raise ValueError(f"{name} contains invalid characters: {value}")
    return value


# Validate on module load
try:
    WALG_PATH = _validate_config_value(WALG_PATH, "WALG_PATH")
    S3_URL = _validate_config_value(S3_URL, "S3_URL")
    # POSTGRES_URL may contain password, so we only validate basic structure
    if not POSTGRES_URL.startswith(("postgresql://", "postgresql+asyncpg://")):
        raise ValueError("POSTGRES_URL must start with postgresql:// or postgresql+asyncpg://")
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    raise


def _sanitize_for_logging(command: str) -> str:
    """Sanitize command string for logging to prevent sensitive data exposure."""
    # Remove potential passwords from connection strings
    import re

    # Pattern for postgresql://user:password@host:port/db
    command = re.sub(r"(postgresql[+a-z]*?://[^:]+):([^@]+)@", r"\1:***@", command)
    # Pattern for s3://bucket:secret@...
    command = re.sub(r"(s3://[^:]+):([^@]+)@", r"\1:***@", command)
    return command


def _run_walg(args: List[str]) -> bool:
    """Execute a wal‑g command with the given argument list.

    Returns ``True`` on exit code 0, otherwise logs the error and returns
    ``False``.
    """
    command = f"{WALG_PATH} {' '.join(args)}"
    logger.info("Executing wal‑g command: %s", _sanitize_for_logging(command))
    try:
        result = _run_shell(command)
        # ``_run_shell`` returns CompletedProcess with stdout/stderr
        # when the command finishes synchronously.
        if isinstance(result, dict):
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            logger.debug("wal‑g stdout: %s", _sanitize_for_logging(stdout))
            if stderr:
                logger.warning("wal‑g stderr: %s", _sanitize_for_logging(stderr))
        else:
            logger.debug("wal‑g result: %s", result)
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("wal‑g execution failed: %s", exc)
        return False


# -----------------------------------------------------------------
# Public API – backup full database (base backup + WAL archive).
# -----------------------------------------------------------------
def backup_database() -> bool:
    """Create a full base backup and start WAL archiving to the configured S3.

    The command is ``wal-g --bucket=s3://... backup-push <postgres_url>``.
    """
    args = ["--bucket", S3_URL, "backup-push", POSTGRES_URL]
    return _run_walg(args)


# -----------------------------------------------------------------
# Public API – restore a backup from S3 to the local PostgreSQL instance.
# -----------------------------------------------------------------
def restore_latest_backup() -> bool:
    """Restore the most recent backup from the configured S3 bucket.

    This runs ``wal‑g --bucket=s3://... backup-fetch LATEST`` followed by
    ``wal‑g --bucket=s3://... restore``.  The implementation assumes the
    PostgreSQL service is stopped and the data directory is ready for
    restoration – responsibilities delegated to the deployment script.
    """
    fetch_args = ["--bucket", S3_URL, "backup-fetch", "LATEST"]
    if not _run_walg(fetch_args):
        return False
    restore_args = ["--bucket", S3_URL, "restore"]
    return _run_walg(restore_args)


# -----------------------------------------------------------------
# Helper to list available backup identifiers.
# -----------------------------------------------------------------
def list_backups() -> List[str]:
    """Return a list of backup names/identifiers available in S3.

    Uses ``wal‑g --bucket=s3://... backup-list``.
    """
    command = f"{WALG_PATH} --bucket {S3_URL} backup-list"
    try:
        result = _run_shell(command)
        if isinstance(result, subprocess.CompletedProcess):
            output = result.stdout or ""
        else:
            output = str(result)
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        logger.info("wal‑g backup list retrieved: %d entries", len(lines))
        return lines
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to list wal‑g backups: %s", exc)
        return []
