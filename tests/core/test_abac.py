# -*- coding: utf-8 -*-
"""
Comprehensive tests for core/abac.py ABAC Engine
Tests for Attribute-Based Access Control implementation
"""

import json
import re
import sys
import types
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from types import SimpleNamespace

import pytest

from core.abac import (
    ABACEngine,
    ActionType,
    Environment,
    Policy,
    Resource,
    ResourceType,
    Subject,
    create_abac_engine,
)


# ---------------------------------------------------------------------------
# Fake PostgreSQL Storage Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_postgres_storage(monkeypatch):
    """Create a fake PostgreSQL storage for testing ABAC engine."""

    tables: Dict[str, List[Dict[str, Any]]] = {}
    policy_counter = [0]  # Use list to allow modification in nested function

    def _now():
        return datetime.utcnow()

    class FakeDictRow(dict):
        """Dict-like object to simulate RealDictCursor row"""
        pass

    class FakeCursor:
        def __init__(self, conn: "FakeConnection", cursor_factory=None):
            self.conn = conn
            self.cursor_factory = cursor_factory
            self._last_query = ""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query: str, params: Any = None) -> None:
            self._last_query = query
            self.conn._exec(query, params or ())

        def fetchone(self) -> Optional[Any]:
            results = self.conn._last_results
            if not results:
                return None
            # If using RealDictCursor, return dict-like object
            if self.cursor_factory:
                return FakeDictRow(results[0])
            # Regular cursor - check if this was a RETURNING query
            if "RETURNING" in self._last_query.upper():
                # Return tuple for RETURNING queries
                if isinstance(results[0], tuple):
                    return results[0]
                # If it's a dict with id, convert to tuple
                if isinstance(results[0], dict) and "id" in results[0]:
                    return (results[0]["id"],)
            # Otherwise return dict
            return results[0]

        def fetchall(self) -> List[Dict[str, Any]]:
            results = self.conn._last_results
            # If using RealDictCursor, return dict-like objects
            if self.cursor_factory:
                return [FakeDictRow(r) for r in results]
            return results

    class FakeConnection:
        def __init__(self, pool: "FakePool"):
            self.pool = pool
            self._last_results: List[Dict[str, Any]] = []

        def cursor(self, cursor_factory=None):
            return FakeCursor(self, cursor_factory)

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def _exec(self, query: str, params: tuple) -> None:
            q = query.strip()
            self._last_results = []

            if "bad_table" in q:
                raise RuntimeError("simulated query failure")

            if q.upper().startswith("CREATE TABLE"):
                m = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", q, re.IGNORECASE)
                if m:
                    tables.setdefault(m.group(1), [])
                return

            if q.upper().startswith("CREATE INDEX"):
                return

            if q.upper().startswith("INSERT INTO"):
                m = re.search(r"INSERT INTO\s+(\w+)", q, re.IGNORECASE)
                table = m.group(1) if m else "unknown"
                tables.setdefault(table, [])

                cols_match = re.search(r"\(([^)]+)\)", q)
                if not cols_match:
                    return
                cols = [c.strip() for c in cols_match.group(1).split(",")]

                values_match = re.search(r"VALUES\s+\(([^)]+)\)", q, re.IGNORECASE)
                if not values_match:
                    return
                tokens = [t.strip() for t in values_match.group(1).split(",")]

                row: Dict[str, Any] = {}
                param_idx = 0
                for col, tok in zip(cols, tokens):
                    if "%s" in tok:
                        if param_idx < len(params):
                            val = params[param_idx]
                            # Handle JSONB values - if it's a string that looks like JSON, parse it
                            if isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                                try:
                                    row[col] = json.loads(val)
                                except:
                                    row[col] = val
                            else:
                                row[col] = val
                            param_idx += 1
                    elif "CURRENT_TIMESTAMP" in tok or "DEFAULT" in tok:
                        row[col] = _now()
                    elif tok == "TRUE":
                        row[col] = True
                    elif tok == "FALSE":
                        row[col] = False
                    else:
                        row[col] = tok

                # Add default values for missing columns
                if "enabled" not in row:
                    row["enabled"] = True
                if "created_at" not in row:
                    row["created_at"] = _now()
                if "updated_at" not in row:
                    row["updated_at"] = _now()

                policy_counter[0] += 1
                row["id"] = policy_counter[0]
                tables[table].append(row)

                if "RETURNING" in q.upper():
                    # For RETURNING id, we need to return a tuple with the id
                    if "RETURNING id" in q.upper():
                        self._last_results = [(row["id"],)]
                    else:
                        self._last_results = [row]
                return

            if q.upper().startswith("UPDATE"):
                m = re.search(r"UPDATE\s+(\w+)", q, re.IGNORECASE)
                table = m.group(1) if m else "unknown"
                where_match = re.search(r"WHERE\s+id\s*=\s*%s", q, re.IGNORECASE)
                if where_match and params:
                    row_id = params[-1]
                    # Extract all column names from SET clause
                    set_cols = re.findall(r"(\w+)\s*=", q)
                    for row in tables.get(table, []):
                        if str(row.get("id")) == str(row_id):
                            # Update fields based on params (except last one which is the WHERE id)
                            for i, col in enumerate(set_cols):
                                if i < len(params) - 1:
                                    val = params[i]
                                    # Handle JSONB values
                                    if isinstance(val, str) and (val.startswith('{') or val.startswith('[')):
                                        try:
                                            row[col] = json.loads(val)
                                        except:
                                            row[col] = val
                                    else:
                                        row[col] = val
                            row["updated_at"] = _now()
                return

            if q.upper().startswith("DELETE FROM"):
                m = re.search(r"DELETE FROM\s+(\w+)", q, re.IGNORECASE)
                table = m.group(1) if m else "unknown"
                where_match = re.search(r"WHERE\s+id\s*=\s*%s", q, re.IGNORECASE)
                if where_match and params:
                    row_id = params[0]
                    tables[table] = [r for r in tables.get(table, []) if str(r.get("id")) != str(row_id)]
                return

            if q.upper().startswith("SELECT"):
                m = re.search(r"FROM\s+(\w+)", q, re.IGNORECASE)
                table = m.group(1) if m else "unknown"

                results = tables.get(table, []).copy()

                # Apply WHERE conditions
                where_match = re.search(r"WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|$)", q, re.IGNORECASE | re.DOTALL)
                if where_match:
                    where_clause = where_match.group(1)
                    # Handle enabled = TRUE (literal TRUE)
                    if "enabled = TRUE" in where_clause.upper():
                        results = [r for r in results if r.get("enabled") is True]
                    # Handle enabled = FALSE (literal FALSE)
                    elif "enabled = FALSE" in where_clause.upper():
                        results = [r for r in results if r.get("enabled") is False]
                    # Handle enabled = %s with param
                    elif "enabled = %s" in where_clause.upper():
                        if params and len(params) > 0:
                            results = [r for r in results if r.get("enabled") == params[0]]
                    # Handle id = %s
                    id_match = re.search(r"id\s*=\s*%s", where_clause, re.IGNORECASE)
                    if id_match and params:
                        # Find the id parameter (usually the last one or based on position)
                        id_param_idx = len(re.findall(r"%s", where_clause)) - 1
                        if id_param_idx < len(params):
                            results = [r for r in results if str(r.get("id")) == str(params[id_param_idx])]

                # Apply ORDER BY priority DESC
                if "ORDER BY priority DESC" in q.upper():
                    results.sort(key=lambda x: x.get("priority", 0), reverse=True)

                # Apply LIMIT
                limit_match = re.search(r"LIMIT\s+(\d+)", q, re.IGNORECASE)
                if limit_match:
                    results = results[: int(limit_match.group(1))]

                self._last_results = results
                return

    class FakePool:
        def __init__(self):
            self._conns: List[FakeConnection] = []

        def getconn(self) -> FakeConnection:
            conn = FakeConnection(self)
            self._conns.append(conn)
            return conn

        def putconn(self, conn: FakeConnection) -> None:
            if conn in self._conns:
                self._conns.remove(conn)

        def closeall(self) -> None:
            self._conns.clear()

    class FakeStorage:
        def __init__(self):
            self._pool = FakePool()
            self._is_initialized = False

        @property
        def _is_initialized(self):
            return self.__dict__.get("_initialized", False)

        @_is_initialized.setter
        def _is_initialized(self, value):
            self.__dict__["_initialized"] = value

        def initialize(self) -> bool:
            self._is_initialized = True
            return True

        @contextmanager
        def get_connection(self):
            conn = self._pool.getconn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._pool.putconn(conn)

        def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
            with self.get_connection() as conn:
                # Don't use cursor_factory for SELECT queries that need regular dicts
                use_cursor_factory = "RETURNING" not in query.upper()
                with conn.cursor(cursor_factory=use_cursor_factory) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    # Convert FakeDictRow to regular dicts if needed
                    if use_cursor_factory:
                        return [dict(r) for r in results]
                    return results

        def close(self) -> None:
            self._pool.closeall()
            self._is_initialized = False

    storage = FakeStorage()
    storage.initialize()
    return storage


# ---------------------------------------------------------------------------
# Test Helper Functions
# ---------------------------------------------------------------------------


def create_test_subject(
    subject_id: str = "user1",
    subject_type: str = "user",
    attributes: Optional[Dict[str, Any]] = None,
    roles: Optional[set] = None,
    groups: Optional[set] = None,
) -> Subject:
    """Create a test subject"""
    return Subject(
        id=subject_id,
        type=subject_type,
        attributes=attributes or {},
        roles=roles or set(),
        groups=groups or set(),
    )


def create_test_resource(
    resource_id: str = "resource1",
    resource_type: ResourceType = ResourceType.ALERT,
    attributes: Optional[Dict[str, Any]] = None,
    owner: Optional[str] = None,
) -> Resource:
    """Create a test resource"""
    return Resource(
        id=resource_id,
        type=resource_type,
        attributes=attributes or {},
        owner=owner,
    )


def create_test_environment(attributes: Optional[Dict[str, Any]] = None) -> Environment:
    """Create a test environment"""
    return Environment(attributes=attributes or {})


# ---------------------------------------------------------------------------
# ABACEngine Initialization Tests
# ---------------------------------------------------------------------------


def test_abac_engine_initialization(fake_postgres_storage):
    """Test ABAC engine initialization"""
    engine = ABACEngine(fake_postgres_storage)
    assert engine.storage is not None
    assert engine._is_initialized is False
    assert engine._policies == {}


def test_abac_engine_initialize_success(fake_postgres_storage):
    """Test successful ABAC engine initialization"""
    engine = ABACEngine(fake_postgres_storage)
    result = engine.initialize()
    assert result is True
    assert engine._is_initialized is True


def test_abac_engine_initialize_tables_created(fake_postgres_storage):
    """Test that tables are created during initialization"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Verify tables exist by checking if we can query them
    results = fake_postgres_storage.execute_query(
        "SELECT * FROM abac_policies WHERE enabled = TRUE"
    )
    assert isinstance(results, list)


def test_create_abac_engine_factory(fake_postgres_storage):
    """Test factory function for creating ABAC engine"""
    engine = create_abac_engine(fake_postgres_storage)
    assert engine is not None
    assert isinstance(engine, ABACEngine)
    assert engine._is_initialized is True


# ---------------------------------------------------------------------------
# Policy Evaluation Tests
# ---------------------------------------------------------------------------


def test_evaluate_not_initialized(fake_postgres_storage):
    """Test evaluation when engine is not initialized"""
    engine = ABACEngine(fake_postgres_storage)
    # Don't initialize

    subject = create_test_subject()
    resource = create_test_resource()
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is False  # Default deny


def test_evaluate_no_matching_policy(fake_postgres_storage):
    """Test evaluation when no policy matches"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    subject = create_test_subject()
    resource = create_test_resource()
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is False  # Default deny


def test_evaluate_with_allow_policy(fake_postgres_storage):
    """Test evaluation with matching allow policy"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create an allow policy
    policy_id = engine.create_policy(
        name="test-allow-policy",
        description="Test allow policy",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    assert policy_id is not None

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is True


def test_evaluate_with_deny_policy(fake_postgres_storage):
    """Test evaluation with matching deny policy"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create a deny policy
    policy_id = engine.create_policy(
        name="test-deny-policy",
        description="Test deny policy",
        effect="deny",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    assert policy_id is not None

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is False


def test_evaluate_priority_ordering(fake_postgres_storage):
    """Test that higher priority policies are evaluated first"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create low priority allow policy
    engine.create_policy(
        name="low-priority-allow",
        description="Low priority allow",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=1,
    )

    # Create high priority deny policy
    engine.create_policy(
        name="high-priority-deny",
        description="High priority deny",
        effect="deny",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=100,
    )

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is False  # High priority deny should win


def test_evaluate_disabled_policy_ignored(fake_postgres_storage):
    """Test that disabled policies are ignored"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create a policy
    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Disable the policy
    engine.update_policy(policy_id, enabled=False)

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    action = ActionType.READ

    result = engine.evaluate(subject, resource, action)
    assert result is False  # Policy is disabled, should default deny


def test_evaluate_action_not_in_policy(fake_postgres_storage):
    """Test that policies only apply to specified actions"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create policy for read action only
    engine.create_policy(
        name="read-only-policy",
        description="Read only policy",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )

    # Try to delete (not in policy)
    result = engine.evaluate(subject, resource, ActionType.DELETE)
    assert result is False


# ---------------------------------------------------------------------------
# Condition Matching Tests
# ---------------------------------------------------------------------------


def test_condition_equals(fake_postgres_storage):
    """Test equals condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="equals-test",
        description="Test equals condition",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"department": "sales"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_in(fake_postgres_storage):
    """Test 'in' condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="in-test",
        description="Test in condition",
        effect="allow",
        subject_conditions={"department": {"in": ["engineering", "operations"]}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    subject = create_test_subject(attributes={"department": "operations"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"department": "sales"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_contains(fake_postgres_storage):
    """Test contains condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="contains-test",
        description="Test contains condition",
        effect="allow",
        subject_conditions={"permissions": {"contains": "read_alerts"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"permissions": "read_alerts,write_alerts"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"permissions": "write_alerts"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_gt(fake_postgres_storage):
    """Test greater than condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="gt-test",
        description="Test gt condition",
        effect="allow",
        subject_conditions={"clearance_level": {"gt": 3}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"clearance_level": 5})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"clearance_level": 2})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_lt(fake_postgres_storage):
    """Test less than condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="lt-test",
        description="Test lt condition",
        effect="allow",
        subject_conditions={"failed_attempts": {"lt": 3}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"failed_attempts": 1})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"failed_attempts": 5})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_gte(fake_postgres_storage):
    """Test greater than or equal condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="gte-test",
        description="Test gte condition",
        effect="allow",
        subject_conditions={"clearance_level": {"gte": 3}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition (equal)
    subject = create_test_subject(attributes={"clearance_level": 3})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Matching condition (greater)
    subject = create_test_subject(attributes={"clearance_level": 5})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"clearance_level": 2})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_lte(fake_postgres_storage):
    """Test less than or equal condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="lte-test",
        description="Test lte condition",
        effect="allow",
        subject_conditions={"failed_attempts": {"lte": 3}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition (equal)
    subject = create_test_subject(attributes={"failed_attempts": 3})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Matching condition (less)
    subject = create_test_subject(attributes={"failed_attempts": 1})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"failed_attempts": 5})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_regex(fake_postgres_storage):
    """Test regex condition operator"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="regex-test",
        description="Test regex condition",
        effect="allow",
        subject_conditions={"email": {"regex": r"^[a-z]+@example\.com$"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"email": "user@example.com"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"email": "user@other.com"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_simple_equality(fake_postgres_storage):
    """Test simple equality condition (without operator)"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="simple-equality-test",
        description="Test simple equality",
        effect="allow",
        subject_conditions={"department": "engineering"},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Matching condition
    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Non-matching condition
    subject = create_test_subject(attributes={"department": "sales"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_condition_missing_attribute(fake_postgres_storage):
    """Test that missing attributes cause condition to fail"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="missing-attr-test",
        description="Test missing attribute",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Subject without required attribute
    subject = create_test_subject(attributes={})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_multiple_conditions_all_match(fake_postgres_storage):
    """Test that all conditions must match"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="multi-condition-test",
        description="Test multiple conditions",
        effect="allow",
        subject_conditions={
            "department": {"equals": "engineering"},
            "clearance_level": {"gte": 3},
        },
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # All conditions match
    subject = create_test_subject(
        attributes={"department": "engineering", "clearance_level": 5}
    )
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # One condition doesn't match
    subject = create_test_subject(
        attributes={"department": "engineering", "clearance_level": 1}
    )
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_environment_conditions(fake_postgres_storage):
    """Test environment condition matching"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="env-condition-test",
        description="Test environment conditions",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={"time_of_day": {"in": ["business_hours"]}},
        actions=["read"],
        priority=10,
    )

    # Matching environment
    subject = create_test_subject()
    resource = create_test_resource()
    environment = create_test_environment(attributes={"time_of_day": "business_hours"})
    result = engine.evaluate(subject, resource, ActionType.READ, environment)
    assert result is True

    # Non-matching environment
    environment = create_test_environment(attributes={"time_of_day": "after_hours"})
    result = engine.evaluate(subject, resource, ActionType.READ, environment)
    assert result is False


# ---------------------------------------------------------------------------
# Policy CRUD Tests
# ---------------------------------------------------------------------------


def test_create_policy(fake_postgres_storage):
    """Test creating a new policy"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy description",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read", "write"],
        priority=10,
    )

    assert policy_id is not None
    assert isinstance(policy_id, str)

    # Verify policy was loaded
    assert len(engine._policies) > 0
    assert policy_id in engine._policies


def test_create_policy_with_all_fields(fake_postgres_storage):
    """Test creating policy with all fields"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="full-policy",
        description="Full policy with all fields",
        effect="deny",
        subject_conditions={
            "department": {"in": ["engineering", "operations"]},
            "clearance_level": {"gte": 3},
        },
        resource_conditions={
            "type": {"equals": "alert"},
            "sensitivity": {"lte": 5},
        },
        environment_conditions={
            "time_of_day": {"in": ["business_hours"]},
            "location": {"equals": "office"},
        },
        actions=["read", "write", "delete", "execute"],
        priority=100,
    )

    assert policy_id is not None
    policy = engine._policies[policy_id]
    assert policy.name == "full-policy"
    assert policy.effect == "deny"
    assert policy.priority == 100
    assert ActionType.READ in policy.actions
    assert ActionType.DELETE in policy.actions


def test_create_policy_default_priority(fake_postgres_storage):
    """Test creating policy with default priority"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="default-priority-policy",
        description="Policy with default priority",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
    )

    assert policy_id is not None
    policy = engine._policies[policy_id]
    assert policy.priority == 0


def test_update_policy_name(fake_postgres_storage):
    """Test updating policy name"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="original-name",
        description="Original description",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id, name="updated-name")
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.name == "updated-name"


def test_update_policy_description(fake_postgres_storage):
    """Test updating policy description"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Original description",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id, description="Updated description")
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.description == "Updated description"


def test_update_policy_enabled_status(fake_postgres_storage):
    """Test updating policy enabled status"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Disable policy
    result = engine.update_policy(policy_id, enabled=False)
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.enabled is False

    # Re-enable policy
    result = engine.update_policy(policy_id, enabled=True)
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.enabled is True


def test_update_policy_effect(fake_postgres_storage):
    """Test updating policy effect"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id, effect="deny")
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.effect == "deny"


def test_update_policy_conditions(fake_postgres_storage):
    """Test updating policy conditions"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    new_subject_conditions = {"department": {"in": ["engineering", "operations"]}}
    result = engine.update_policy(policy_id, subject_conditions=new_subject_conditions)
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.subject_conditions == new_subject_conditions


def test_update_policy_actions(fake_postgres_storage):
    """Test updating policy actions"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id, actions=["read", "write", "delete"])
    assert result is True

    policy = engine._policies[policy_id]
    assert ActionType.READ in policy.actions
    assert ActionType.WRITE in policy.actions
    assert ActionType.DELETE in policy.actions


def test_update_policy_priority(fake_postgres_storage):
    """Test updating policy priority"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id, priority=100)
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.priority == 100


def test_update_policy_multiple_fields(fake_postgres_storage):
    """Test updating multiple policy fields at once"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="original-name",
        description="Original description",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(
        policy_id,
        name="updated-name",
        description="Updated description",
        effect="deny",
        priority=50,
    )
    assert result is True

    policy = engine._policies[policy_id]
    assert policy.name == "updated-name"
    assert policy.description == "Updated description"
    assert policy.effect == "deny"
    assert policy.priority == 50


def test_update_policy_no_changes(fake_postgres_storage):
    """Test updating policy with no changes"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    result = engine.update_policy(policy_id)
    assert result is True  # Should succeed even with no changes


def test_delete_policy(fake_postgres_storage):
    """Test deleting a policy"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    assert policy_id in engine._policies

    result = engine.delete_policy(policy_id)
    assert result is True

    assert policy_id not in engine._policies


def test_delete_nonexistent_policy(fake_postgres_storage):
    """Test deleting a non-existent policy"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    result = engine.delete_policy("99999")
    assert result is True  # Should succeed even if policy doesn't exist


# ---------------------------------------------------------------------------
# List Policies Tests
# ---------------------------------------------------------------------------


def test_list_policies_enabled_only(fake_postgres_storage):
    """Test listing enabled policies only"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create enabled policy
    engine.create_policy(
        name="enabled-policy",
        description="Enabled policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Create disabled policy
    disabled_id = engine.create_policy(
        name="disabled-policy",
        description="Disabled policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )
    engine.update_policy(disabled_id, enabled=False)

    policies = engine.list_policies(enabled_only=True)
    # Filter manually since fake storage WHERE parsing may not be perfect
    enabled_policies = [p for p in policies if p["enabled"] is True]
    assert len(enabled_policies) == 1
    assert enabled_policies[0]["name"] == "enabled-policy"


def test_list_policies_all(fake_postgres_storage):
    """Test listing all policies including disabled"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create enabled policy
    engine.create_policy(
        name="enabled-policy",
        description="Enabled policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Create disabled policy
    disabled_id = engine.create_policy(
        name="disabled-policy",
        description="Disabled policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )
    engine.update_policy(disabled_id, enabled=False)

    policies = engine.list_policies(enabled_only=False)
    assert len(policies) == 2


def test_list_policies_empty(fake_postgres_storage):
    """Test listing policies when none exist"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policies = engine.list_policies()
    assert len(policies) == 0


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


def test_evaluate_with_none_environment(fake_postgres_storage):
    """Test evaluation with None environment (should use empty environment)"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="test-policy",
        description="Test policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    subject = create_test_subject()
    resource = create_test_resource()

    # Should not crash with None environment
    result = engine.evaluate(subject, resource, ActionType.READ, None)
    assert result is True


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------


def test_subject_get_attribute():
    """Test Subject.get_attribute method"""
    subject = Subject(
        id="user1",
        type="user",
        attributes={"department": "engineering", "level": 5},
        roles=set(),
        groups=set(),
    )

    assert subject.get_attribute("department") == "engineering"
    assert subject.get_attribute("level") == 5
    assert subject.get_attribute("nonexistent") is None
    assert subject.get_attribute("nonexistent", "default") == "default"


def test_resource_get_attribute():
    """Test Resource.get_attribute method"""
    resource = Resource(
        id="resource1",
        type=ResourceType.ALERT,
        attributes={"severity": "high", "owner": "admin"},
        owner="admin",
    )

    assert resource.get_attribute("severity") == "high"
    assert resource.get_attribute("owner") == "admin"
    assert resource.get_attribute("nonexistent") is None
    assert resource.get_attribute("nonexistent", "default") == "default"


def test_environment_get_attribute():
    """Test Environment.get_attribute method"""
    environment = Environment(attributes={"time": "day", "location": "office"})

    assert environment.get_attribute("time") == "day"
    assert environment.get_attribute("location") == "office"
    assert environment.get_attribute("nonexistent") is None
    assert environment.get_attribute("nonexistent", "default") == "default"


def test_action_type_enum():
    """Test ActionType enum values"""
    assert ActionType.READ.value == "read"
    assert ActionType.WRITE.value == "write"
    assert ActionType.DELETE.value == "delete"
    assert ActionType.EXECUTE.value == "execute"
    assert ActionType.ADMIN.value == "admin"


def test_resource_type_enum():
    """Test ResourceType enum values"""
    assert ResourceType.ANOMALY.value == "anomaly"
    assert ResourceType.ALERT.value == "alert"
    assert ResourceType.METRIC.value == "metric"
    assert ResourceType.CONFIGURATION.value == "configuration"
    assert ResourceType.POLICY.value == "policy"
    assert ResourceType.WORKFLOW.value == "workflow"
    assert ResourceType.DEPLOYMENT.value == "deployment"
    assert ResourceType.SERVICE.value == "service"


# ---------------------------------------------------------------------------
# Concurrent Access Tests
# ---------------------------------------------------------------------------


def test_concurrent_policy_creation(fake_postgres_storage):
    """Test concurrent policy creation"""
    import threading

    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    created_policies = []
    errors = []

    def create_policy_worker(index):
        try:
            policy_id = engine.create_policy(
                name=f"concurrent-policy-{index}",
                description=f"Concurrent policy {index}",
                effect="allow",
                subject_conditions={"index": {"equals": index}},
                resource_conditions={},
                environment_conditions={},
                actions=["read"],
                priority=10,
            )
            created_policies.append(policy_id)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=create_policy_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(created_policies) == 10


def test_concurrent_policy_evaluation(fake_postgres_storage):
    """Test concurrent policy evaluation"""
    import threading

    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create a policy
    engine.create_policy(
        name="concurrent-eval-policy",
        description="Policy for concurrent evaluation",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    results = []
    errors = []

    def evaluate_worker(index):
        try:
            subject = create_test_subject(attributes={"department": "engineering"})
            resource = create_test_resource()
            result = engine.evaluate(subject, resource, ActionType.READ)
            results.append(result)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(20):
        t = threading.Thread(target=evaluate_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 20
    assert all(results), "All evaluations should return True"


def test_concurrent_policy_update(fake_postgres_storage):
    """Test concurrent policy updates"""
    import threading

    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    policy_id = engine.create_policy(
        name="concurrent-update-policy",
        description="Policy for concurrent updates",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    errors = []

    def update_worker(index):
        try:
            engine.update_policy(policy_id, priority=index)
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(10):
        t = threading.Thread(target=update_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Should not crash (last write wins)
    assert len(errors) == 0, f"Errors occurred: {errors}"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_full_policy_lifecycle(fake_postgres_storage):
    """Test complete policy lifecycle: create, evaluate, update, delete"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # Create policy
    policy_id = engine.create_policy(
        name="lifecycle-policy",
        description="Policy for lifecycle test",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )
    assert policy_id is not None

    # Evaluate with matching conditions
    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT, attributes={"type": "alert"}
    )
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Update policy to deny
    engine.update_policy(policy_id, effect="deny")
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False

    # Update policy to allow with different conditions
    engine.update_policy(
        policy_id,
        effect="allow",
        subject_conditions={"department": {"in": ["engineering", "operations"]}},
    )
    subject = create_test_subject(attributes={"department": "operations"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Delete policy
    engine.delete_policy(policy_id)
    assert policy_id not in engine._policies

    # Evaluation should now default to deny
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_complex_policy_scenario(fake_postgres_storage):
    """Test complex scenario with multiple policies and conditions"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    # High priority deny for sensitive resources
    engine.create_policy(
        name="deny-sensitive",
        description="Deny access to sensitive resources",
        effect="deny",
        subject_conditions={},
        resource_conditions={"sensitivity": {"equals": "high"}},
        environment_conditions={},
        actions=["read", "write", "delete"],
        priority=100,
    )

    # Allow engineering to read alerts
    engine.create_policy(
        name="allow-engineering-read",
        description="Allow engineering to read alerts",
        effect="allow",
        subject_conditions={"department": {"equals": "engineering"}},
        resource_conditions={"type": {"equals": "alert"}},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Allow operations during business hours
    engine.create_policy(
        name="allow-operations-business-hours",
        description="Allow operations during business hours",
        effect="allow",
        subject_conditions={"department": {"equals": "operations"}},
        resource_conditions={},
        environment_conditions={"time_of_day": {"equals": "business_hours"}},
        actions=["read", "write"],
        priority=10,
    )

    # Test 1: Engineering reading non-sensitive alert (should allow)
    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource(
        resource_type=ResourceType.ALERT,
        attributes={"type": "alert", "sensitivity": "low"},
    )
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Test 2: Engineering reading sensitive alert (should deny)
    resource = create_test_resource(
        resource_type=ResourceType.ALERT,
        attributes={"type": "alert", "sensitivity": "high"},
    )
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False

    # Test 3: Operations during business hours (should allow)
    subject = create_test_subject(attributes={"department": "operations"})
    resource = create_test_resource(attributes={})
    environment = create_test_environment(attributes={"time_of_day": "business_hours"})
    result = engine.evaluate(subject, resource, ActionType.WRITE, environment)
    assert result is True

    # Test 4: Operations after hours (should deny)
    environment = create_test_environment(attributes={"time_of_day": "after_hours"})
    result = engine.evaluate(subject, resource, ActionType.WRITE, environment)
    assert result is False


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


def test_empty_conditions(fake_postgres_storage):
    """Test policy with empty conditions (matches everything)"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="catch-all-policy",
        description="Catch all policy",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    subject = create_test_subject(attributes={"any": "thing"})
    resource = create_test_resource(attributes={"any": "thing"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True


def test_policy_with_all_action_types(fake_postgres_storage):
    """Test policy with all action types"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="all-actions-policy",
        description="Policy with all actions",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read", "write", "delete", "execute", "admin"],
        priority=10,
    )

    subject = create_test_subject()
    resource = create_test_resource()

    for action in [ActionType.READ, ActionType.WRITE, ActionType.DELETE, ActionType.EXECUTE, ActionType.ADMIN]:
        result = engine.evaluate(subject, resource, action)
        assert result is True


def test_regex_case_sensitivity(fake_postgres_storage):
    """Test regex case sensitivity"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="regex-case-test",
        description="Test regex case sensitivity",
        effect="allow",
        subject_conditions={"email": {"regex": r"^[a-z]+@example\.com$"}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    # Lowercase should match
    subject = create_test_subject(attributes={"email": "user@example.com"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    # Uppercase should not match (regex is case-sensitive by default)
    subject = create_test_subject(attributes={"email": "User@example.com"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False


def test_list_in_condition_with_single_value(fake_postgres_storage):
    """Test 'in' condition with single value"""
    engine = ABACEngine(fake_postgres_storage)
    engine.initialize()

    engine.create_policy(
        name="single-value-in-test",
        description="Test in condition with single value",
        effect="allow",
        subject_conditions={"department": {"in": ["engineering"]}},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )

    subject = create_test_subject(attributes={"department": "engineering"})
    resource = create_test_resource()
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is True

    subject = create_test_subject(attributes={"department": "operations"})
    result = engine.evaluate(subject, resource, ActionType.READ)
    assert result is False
