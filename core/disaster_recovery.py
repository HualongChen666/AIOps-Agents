# -*- coding: utf-8 -*-
"""
Disaster Recovery Module
========================

Provides disaster recovery functionality for backup and restore operations.
Supports database backups, Redis backups, configuration backups, and cleanup operations.
"""

import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse


def _default_backup_dir() -> str:
    """Resolve the default backup directory from configuration.

    Uses ``config.BACKUP_LOCATION`` (``BACKUP_LOCATION`` env var) so no
    platform-specific absolute path is baked into the code.
    """
    try:
        from config import BACKUP_LOCATION

        return BACKUP_LOCATION or "/backups"
    except Exception:
        return os.getenv("BACKUP_LOCATION", "/backups")


class DisasterRecovery:
    """Disaster Recovery Manager for backup and restore operations."""

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize Disaster Recovery Manager.

        Args:
            backup_dir: Directory to store backups. Defaults to the configured
                ``BACKUP_LOCATION``.
        """
        self.backup_dir = Path(backup_dir or _default_backup_dir())
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _database_url() -> str:
        """Resolve the configured database URL (empty string when unavailable)."""
        try:
            from config import DATABASE_URL

            return DATABASE_URL or ""
        except Exception:
            return ""

    def backup_database(self) -> Optional[str]:
        """
        Backup the configured database with a real dump.

        * ``sqlite``   -> SQL text dump through the sqlite3 module
        * ``postgres`` -> logical dump through ``pg_dump``

        Returns:
            Path to backup file

        Raises:
            RuntimeError / FileNotFoundError: when no database is configured or
            the dump fails.  No placeholder file is ever produced.
        """
        url = self._database_url()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if url.startswith("sqlite"):
            db_path = Path(url.split("///", 1)[-1] or "aiops_agent.db")
            if not db_path.exists():
                raise FileNotFoundError(f"SQLite database not found: {db_path}")
            backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"
            conn = sqlite3.connect(str(db_path))
            try:
                with open(backup_file, "w", encoding="utf-8") as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
            except OSError as exc:
                raise RuntimeError(f"Failed to write backup file {backup_file}: {exc}") from exc
            finally:
                conn.close()
            return str(backup_file)

        if url.startswith("postgres"):
            parsed = urlparse(url)
            backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"
            env = dict(os.environ)
            if parsed.password:
                env["PGPASSWORD"] = unquote(parsed.password)
            cmd = [
                "pg_dump",
                "--no-owner",
                "--no-privileges",
                "--host",
                parsed.hostname or "localhost",
                "--port",
                str(parsed.port or 5432),
                "--username",
                unquote(parsed.username or "postgres"),
                "--dbname",
                (parsed.path or "/postgres").lstrip("/"),
                "--file",
                str(backup_file),
            ]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                if backup_file.exists():
                    backup_file.unlink()
                raise RuntimeError(
                    f"pg_dump failed ({result.returncode}): {result.stderr.strip()}"
                )
            return str(backup_file)

        raise RuntimeError(
            "No database configured for backup: set DATABASE_URL to a "
            "sqlite:///... or postgresql://... URL"
        )

    def backup_redis(self) -> Optional[str]:
        """
        Snapshot Redis (BGSAVE) and persist the resulting RDB file.

        Returns:
            Path to the copied backup file

        Raises:
            RuntimeError: when Redis is unreachable or its RDB file is not
            accessible from this host.  No placeholder file is ever produced.
        """
        import redis as redis_lib

        from config import REDIS_DB, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client = None
        try:
            client = redis_lib.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD or None,
                socket_connect_timeout=5,
            )
            client.ping()
            client.bgsave()

            deadline = datetime.now() + timedelta(seconds=30)
            while client.info("persistence").get("rdb_bgsave_in_progress", 0):
                if datetime.now() > deadline:
                    raise RuntimeError("Redis BGSAVE did not complete within 30s")
                time.sleep(0.2)

            dump_dir = Path(client.config_get("dir").get("dir", "."))
            dump_name = client.config_get("dbfilename").get("dbfilename", "dump.rdb")
            source = dump_dir / dump_name
            if not source.exists():
                raise RuntimeError(f"Redis RDB file not accessible on this host: {source}")

            backup_file = self.backup_dir / f"redis_backup_{timestamp}.rdb"
            shutil.copy2(source, backup_file)
            return str(backup_file)
        except redis_lib.RedisError as exc:
            raise RuntimeError(f"Redis backup failed: {exc}") from exc
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:  # pragma: no cover - best-effort close
                    pass

    def backup_configuration(self) -> Optional[str]:
        """
        Backup configuration files.

        Returns:
            Path to backup directory or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backup_dir / f"config_{timestamp}"
            backup_dir.mkdir(exist_ok=True)

            # Backup common config files
            config_files = ["config.py", "config.json", ".env", "pytest.ini"]
            for config_file in config_files:
                src = Path(config_file)
                if src.exists():
                    try:
                        shutil.copy2(src, backup_dir / config_file)
                    except (OSError, shutil.Error) as exc:
                        print(f"Failed to copy {config_file}: {exc}")

            # Create backup manifest
            manifest = {
                "timestamp": timestamp,
                "files": [f for f in config_files if Path(f).exists()],
                "backup_dir": str(backup_dir),
            }

            try:
                with open(backup_dir / "manifest.json", "w") as f:
                    json.dump(manifest, f, indent=2)
            except OSError as exc:
                print(f"Failed to write manifest file: {exc}")
                return None

            return str(backup_dir)
        except Exception as e:
            print(f"Configuration backup failed: {e}")
            return None

    def restore_database(self, backup_file: str) -> bool:
        """
        Restore database from backup.

        Args:
            backup_file: Path to backup file

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                print(f"Backup file not found: {backup_path}")
                return False

            url = self._database_url()
            if not url.startswith("sqlite"):
                print(
                    "restore_database only supports SQLite backups; use pg_restore "
                    "for PostgreSQL targets"
                )
                return False

            # 与 backup_database 使用同一 DATABASE_URL 推导的路径，避免恢复写入错误库
            db_path = Path(url.split("///", 1)[-1] or "aiops_agent.db")
            if not db_path.exists():
                print(f"Target SQLite database not found: {db_path}")
                return False

            try:
                with open(backup_path, "r") as f:
                    sql_script = f.read()
            except OSError as exc:
                print(f"Failed to read backup file {backup_path}: {exc}")
                return False

            conn = sqlite3.connect(str(db_path))
            try:
                conn.executescript(sql_script)
            except sqlite3.Error as exc:
                print(f"Failed to execute SQL script: {exc}")
                conn.close()
                return False
            conn.close()

            return True
        except Exception as e:
            print(f"Database restore failed: {e}")
            return False

    def cleanup_old_backups(self, retention_days: int = 30) -> bool:
        """
        Clean up old backups older than retention_days.

        Args:
            retention_days: Number of days to retain backups

        Returns:
            True if successful, False otherwise
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            # Clean up old database backups
            for backup_file in self.backup_dir.glob("db_backup_*.sql"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()

            # Clean up old Redis backups
            for backup_file in self.backup_dir.glob("redis_backup_*.rdb"):
                if backup_file.stat().st_mtime < cutoff_date.timestamp():
                    backup_file.unlink()

            # Clean up old configuration backups
            for backup_dir in self.backup_dir.glob("config_*"):
                if backup_dir.is_dir() and backup_dir.stat().st_mtime < cutoff_date.timestamp():
                    shutil.rmtree(backup_dir)

            return True
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
