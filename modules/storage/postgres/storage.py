# -*- coding: utf-8 -*-
"""
PostgreSQL Storage Implementation for AIOps Platform
Provides ACID-compliant relational storage with connection pooling and transaction management
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

try:
    from psycopg2 import pool, sql
    from psycopg2.extras import Json, RealDictCursor

    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    pool = None
    sql = None

logger = logging.getLogger(__name__)


class PostgreSQLStorage:
    """
    PostgreSQL Storage Manager

    Provides ACID-compliant relational storage with connection pooling,
    transaction management, and query execution capabilities.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Username
        password: Password
        min_connections: Minimum pool connections
        max_connections: Maximum pool connections
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "aiops",
        user: str = "aiops",
        password: str = "changeme",
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        if not POSTGRESQL_AVAILABLE:
            raise ImportError("psycopg2 not installed. Install with: pip install psycopg2-binary")

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections

        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._is_initialized = False

        logger.info(f"PostgreSQL Storage initialized for {database}@{host}:{port}")

    def initialize(self) -> bool:
        """
        Initialize connection pool and create tables

        Returns:
            True if initialization successful
        """
        try:
            self._pool = pool.SimpleConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )

            # Create tables
            self._create_tables()

            self._is_initialized = True
            logger.info("PostgreSQL storage initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL storage: {e}")
            return False

    def _create_tables(self) -> None:
        """Create required tables"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metadata (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(255) UNIQUE NOT NULL,
                        value JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Policies table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS policies (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        type VARCHAR(100) NOT NULL,
                        policy JSONB NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Configuration table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS configuration (
                        id SERIAL PRIMARY KEY,
                        key VARCHAR(255) UNIQUE NOT NULL,
                        value TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Audit log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id SERIAL PRIMARY KEY,
                        action VARCHAR(100) NOT NULL,
                        actor VARCHAR(255) NOT NULL,
                        resource_type VARCHAR(100),
                        resource_id VARCHAR(255),
                        details JSONB,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_metadata_key ON metadata(key)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_policies_name ON policies(name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_policies_type ON policies(type)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_configuration_key ON configuration(key)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor)")

                conn.commit()
                logger.info("PostgreSQL tables created successfully")

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool

        Yields:
            Database connection
        """
        if not self._pool:
            raise RuntimeError("Storage not initialized. Call initialize() first.")

        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self._pool.putconn(conn)

    def store_metadata(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Store metadata

        Args:
            key: Metadata key
            value: Metadata value (will be stored as JSONB)

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO metadata (key, value, updated_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key)
                        DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
                    """,
                        (key, Json(value), Json(value)),
                    )

            logger.debug(f"Stored metadata: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store metadata {key}: {e}")
            return False

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata

        Args:
            key: Metadata key

        Returns:
            Metadata value or None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT value FROM metadata WHERE key = %s", (key,))
                    result = cursor.fetchone()

                    if result:
                        return dict(result["value"])
                    return None

        except Exception as e:
            logger.error(f"Failed to get metadata {key}: {e}")
            return None

    def delete_metadata(self, key: str) -> bool:
        """
        Delete metadata

        Args:
            key: Metadata key

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM metadata WHERE key = %s", (key,))

            logger.debug(f"Deleted metadata: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete metadata {key}: {e}")
            return False

    def store_policy(
        self, name: str, policy_type: str, policy: Dict[str, Any], enabled: bool = True
    ) -> bool:
        """
        Store policy

        Args:
            name: Policy name
            policy_type: Policy type
            policy: Policy content
            enabled: Whether policy is enabled

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO policies (name, type, policy, enabled, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (name)
                        DO UPDATE SET type = %s, policy = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP  # noqa: E501
                    """,
                        (
                            name,
                            policy_type,
                            Json(policy),
                            enabled,
                            policy_type,
                            Json(policy),
                            enabled,
                        ),
                    )

            logger.debug(f"Stored policy: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store policy {name}: {e}")
            return False

    def get_policy(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve policy

        Args:
            name: Policy name

        Returns:
            Policy data or None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT name, type, policy, enabled, created_at, updated_at FROM policies"
                        " WHERE name = %s",  # noqa: E501
                        (name,),
                    )
                    result = cursor.fetchone()

                    if result:
                        return {
                            "name": result["name"],
                            "type": result["type"],
                            "policy": dict(result["policy"]),
                            "enabled": result["enabled"],
                            "created_at": result["created_at"].isoformat(),
                            "updated_at": result["updated_at"].isoformat(),
                        }
                    return None

        except Exception as e:
            logger.error(f"Failed to get policy {name}: {e}")
            return None

    def list_policies(
        self, policy_type: Optional[str] = None, enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List policies

        Args:
            policy_type: Filter by policy type
            enabled_only: Only return enabled policies

        Returns:
            List of policies
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = "SELECT name, type, policy, enabled, created_at, updated_at FROM policies WHERE 1=1"  # noqa: E501
                    params = []

                    if policy_type:
                        query += " AND type = %s"
                        params.append(policy_type)

                    if enabled_only:
                        query += " AND enabled = TRUE"

                    query += " LIMIT 1000"

                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    return [
                        {
                            "name": r["name"],
                            "type": r["type"],
                            "policy": dict(r["policy"]),
                            "enabled": r["enabled"],
                            "created_at": r["created_at"].isoformat(),
                            "updated_at": r["updated_at"].isoformat(),
                        }
                        for r in results
                    ]

        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []

    def store_configuration(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """
        Store configuration

        Args:
            key: Configuration key
            value: Configuration value
            description: Optional description

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO configuration (key, value, description, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (key)
                        DO UPDATE SET value = %s, description = %s, updated_at = CURRENT_TIMESTAMP
                    """,
                        (key, value, description, value, description),
                    )

            logger.debug(f"Stored configuration: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store configuration {key}: {e}")
            return False

    def get_configuration(self, key: str) -> Optional[str]:
        """
        Retrieve configuration

        Args:
            key: Configuration key

        Returns:
            Configuration value or None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT value FROM configuration WHERE key = %s", (key,))
                    result = cursor.fetchone()

                    if result:
                        return str(result["value"])
                    return None

        except Exception as e:
            logger.error(f"Failed to get configuration {key}: {e}")
            return None

    def log_audit(
        self,
        action: str,
        actor: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log audit event

        Args:
            action: Action performed
            actor: Who performed the action
            resource_type: Type of resource
            resource_id: Resource identifier
            details: Additional details

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_log (action, actor, resource_type, resource_id, details)
                        VALUES (%s, %s, %s, %s, %s)
                    """,
                        (
                            action,
                            actor,
                            resource_type,
                            resource_id,
                            Json(details) if details else None,
                        ),
                    )

            logger.debug(f"Audit log: {action} by {actor}")
            return True

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return False

    def query_audit_log(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query audit log

        Args:
            actor: Filter by actor
            action: Filter by action
            resource_type: Filter by resource type
            limit: Maximum number of results

        Returns:
            List of audit log entries
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = (
                        "SELECT id, action, actor, resource_type, resource_id, "
                        "details, timestamp FROM audit_log WHERE 1=1"
                    )
                    params = []

                    if actor:
                        query += " AND actor = %s"
                        params.append(actor)

                    if action:
                        query += " AND action = %s"
                        params.append(action)

                    if resource_type:
                        query += " AND resource_type = %s"
                        params.append(resource_type)

                    query += " ORDER BY timestamp DESC LIMIT %s"
                    params.append(str(limit))

                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    return [
                        {
                            "id": r["id"],
                            "action": r["action"],
                            "actor": r["actor"],
                            "resource_type": r["resource_type"],
                            "resource_id": r["resource_id"],
                            "details": dict(r["details"]) if r["details"] else None,
                            "timestamp": r["timestamp"].isoformat(),
                        }
                        for r in results
                    ]

        except Exception as e:
            logger.error(f"Failed to query audit log: {e}")
            return []

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom query

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query results
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or ())
                    results = cursor.fetchall()

                    return [dict(r) for r in results]

        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []

    def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            self._pool.closeall()
            self._is_initialized = False
            logger.info("PostgreSQL storage closed")


def create_postgres_storage(
    host: str = "localhost",
    port: int = 5432,
    database: str = "aiops",
    user: str = "aiops",
    password: str = "changeme",
) -> Optional[PostgreSQLStorage]:
    """
    Factory function to create PostgreSQL Storage

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Username
        password: Password

    Returns:
        PostgreSQLStorage instance or None if SDK not available
    """
    if not POSTGRESQL_AVAILABLE:
        logger.warning("PostgreSQL SDK not available")
        return None

    try:
        storage = PostgreSQLStorage(host, port, database, user, password)
        if storage.initialize():
            return storage
        return None
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL storage: {e}")
        return None
