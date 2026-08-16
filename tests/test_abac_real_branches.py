# -*- coding: utf-8 -*-
"""Real-branch coverage tests for core.abac without mocks or monkeypatching."""

import datetime as dt
import json
import re
from typing import Any, Dict, List, Optional, Set

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


class _FakeCursor:
    def __init__(self, storage: "FakePostgresStorage") -> None:
        self.storage = storage
        self._last: Any = None

    def execute(self, query: str, params: Any = None) -> None:
        params = params or ()
        self._last = self.storage._handle_execute(query, params)

    def fetchone(self) -> Any:
        return self._last

    def fetchall(self) -> Any:
        return self._last if isinstance(self._last, list) else []

    def close(self) -> None:
        pass

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: Any) -> Optional[bool]:
        return None


class _FakeConnection:
    def __init__(self, storage: "FakePostgresStorage") -> None:
        self.storage = storage

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.storage)

    def commit(self) -> None:
        pass

    def __enter__(self) -> "_FakeConnection":
        if "connection" in self.storage.raise_on:
            raise RuntimeError("connection failure")
        return self

    def __exit__(self, *args: Any) -> Optional[bool]:
        return False


class FakePostgresStorage:
    """A minimal, real in-memory storage that satisfies the ABACEngine contract."""

    JSON_FIELDS = {
        "subject_conditions",
        "resource_conditions",
        "environment_conditions",
        "actions",
    }

    def __init__(
        self,
        policies: Optional[List[Dict[str, Any]]] = None,
        raise_on: Optional[Set[str]] = None,
    ) -> None:
        self.policies = list(policies or [])
        self.evaluations: List[tuple] = []
        self.raise_on = set(raise_on or [])
        self.queries: List[tuple] = []

    def get_connection(self) -> _FakeConnection:
        return _FakeConnection(self)

    def execute_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        if "query" in self.raise_on:
            raise RuntimeError("query failed")
        self.queries.append((query, params or ()))
        rows = list(self.policies)
        if "enabled = TRUE" in query:
            rows = [r for r in rows if r.get("enabled", True)]
        out: List[Dict[str, Any]] = []
        now = dt.datetime.now()
        for r in rows:
            row = dict(r)
            for f in self.JSON_FIELDS:
                if f in row and isinstance(row[f], str):
                    row[f] = json.loads(row[f])
            if "created_at" not in row or row["created_at"] is None:
                row["created_at"] = now
            if "updated_at" not in row or row["updated_at"] is None:
                row["updated_at"] = now
            out.append(row)
        return out

    def _handle_execute(self, query: str, params: Any) -> Any:
        self.queries.append((query, params))
        if "execute" in self.raise_on:
            raise RuntimeError("execute failed")
        q = query.strip().upper()
        if q.startswith("CREATE"):
            return None
        if "ABAC_POLICY_EVALUATIONS" in q and "log" in self.raise_on:
            raise RuntimeError("log insert failed")
        if "INSERT" in q and "ABAC_POLICY_EVALUATIONS" in q:
            self.evaluations.append(tuple(params))
            return None
        if "insert" in self.raise_on and "ABAC_POLICIES" in q and q.startswith("INSERT"):
            raise RuntimeError("policy insert failed")
        if q.startswith("INSERT"):
            return self._do_insert(query, params)
        if "update" in self.raise_on and q.startswith("UPDATE"):
            raise RuntimeError("policy update failed")
        if q.startswith("UPDATE"):
            return self._do_update(query, params)
        if "delete" in self.raise_on and q.startswith("DELETE"):
            raise RuntimeError("policy delete failed")
        if q.startswith("DELETE"):
            return self._do_delete(query, params)
        return None

    def _do_insert(self, query: str, params: tuple) -> tuple:
        m = re.search(
            r"INSERT\s+INTO\s+abac_policies\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
            query,
            re.I | re.S,
        )
        if not m:
            raise RuntimeError("could not parse insert")
        cols = [c.strip() for c in m.group(1).split(",")]
        row: Dict[str, Any] = {}
        for i, c in enumerate(cols):
            val = params[i]
            if c in self.JSON_FIELDS and isinstance(val, str):
                val = json.loads(val)
            row[c] = val
        row["id"] = len(self.policies) + 1
        now = dt.datetime.now()
        if "created_at" not in row or row["created_at"] is None:
            row["created_at"] = now
        if "updated_at" not in row or row["updated_at"] is None:
            row["updated_at"] = now
        if "enabled" not in row:
            row["enabled"] = True
        self.policies.append(row)
        return (row["id"],)

    def _do_update(self, query: str, params: tuple) -> tuple:
        m = re.search(
            r"UPDATE\s+abac_policies\s+SET\s+(.+?)\s+WHERE\s+id\s*=\s*%s",
            query,
            re.I | re.S,
        )
        if not m:
            raise RuntimeError("could not parse update")
        set_part = m.group(1).strip()
        policy_id = str(params[-1])
        row = next((p for p in self.policies if str(p["id"]) == policy_id), None)
        if row is None:
            return None
        idx = 0
        for clause in set_part.split(", "):
            clause = clause.strip()
            if clause.endswith("= %s"):
                key = clause.replace("= %s", "").strip()
                if idx >= len(params) - 1:
                    break
                val = params[idx]
                idx += 1
                if key in self.JSON_FIELDS and isinstance(val, str):
                    val = json.loads(val)
                row[key] = val
            elif "= CURRENT_TIMESTAMP" in clause:
                key = clause.split("=")[0].strip()
                row[key] = dt.datetime.now()
        return (row["id"],)

    def _do_delete(self, query: str, params: tuple) -> None:
        if "WHERE id = %s" in query:
            pid = str(params[0])
            self.policies = [p for p in self.policies if str(p["id"]) != pid]
        return None


def test_action_and_resource_type_enum_values() -> None:
    assert {a.value for a in ActionType} == {"read", "write", "delete", "execute", "admin"}
    assert {r.value for r in ResourceType} == {
        "anomaly", "alert", "metric", "configuration", "policy", "workflow", "deployment", "service"
    }


def test_subject_get_attribute() -> None:
    subject = Subject(
        id="u1",
        type="user",
        attributes={"department": "sre", "level": 3},
        roles={"admin"},
        groups={"platform"},
    )
    assert subject.get_attribute("department") == "sre"
    assert subject.get_attribute("missing") is None
    assert subject.get_attribute("missing", "default") == "default"


def test_resource_get_attribute() -> None:
    resource = Resource(
        id="r1",
        type=ResourceType.ALERT,
        attributes={"severity": "critical"},
        owner="u1",
    )
    assert resource.get_attribute("severity") == "critical"
    assert resource.get_attribute("missing") is None


def test_environment_get_attribute() -> None:
    env = Environment(attributes={"time_of_day": "day", "ip_range": "10.0.0.0/8"})
    assert env.get_attribute("time_of_day") == "day"
    assert env.get_attribute("missing") is None


def test_policy_dataclass() -> None:
    now = dt.datetime.now()
    policy = Policy(
        id="p1",
        name="read-only",
        description="allows read",
        enabled=True,
        effect="allow",
        subject_conditions={"department": "sre"},
        resource_conditions={"severity": "critical"},
        environment_conditions={"time_of_day": "day"},
        actions={ActionType.READ},
        priority=10,
        created_at=now,
        updated_at=now,
    )
    assert policy.name == "read-only"
    assert ActionType.READ in policy.actions


def test_abac_engine_initialize_success() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    assert engine.initialize() is True
    assert engine._is_initialized is True
    # _load_policies returned empty; cache is empty
    assert engine._policies == {}


def test_abac_engine_initialize_failure() -> None:
    storage = FakePostgresStorage(raise_on={"connection"})
    engine = ABACEngine(storage)
    assert engine.initialize() is False
    assert engine._is_initialized is False


def test_create_abac_engine_success_and_failure() -> None:
    good = create_abac_engine(FakePostgresStorage())
    assert isinstance(good, ABACEngine)
    assert good._is_initialized is True

    bad = create_abac_engine(FakePostgresStorage(raise_on={"connection"}))
    assert bad is None


def test_evaluate_not_initialized() -> None:
    engine = ABACEngine(FakePostgresStorage())
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ) is False


def test_evaluate_no_policies() -> None:
    engine = ABACEngine(FakePostgresStorage())
    assert engine.initialize() is True
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ) is False


def test_evaluate_action_not_in_policy() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "read-only",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 0,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            }
        ]
    )
    engine = ABACEngine(storage)
    assert engine.initialize() is True
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.WRITE) is False


def test_evaluate_disabled_policy_skipped_and_deny_effect() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "disabled",
                "description": "",
                "enabled": False,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 100,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            },
            {
                "id": 2,
                "name": "deny",
                "description": "",
                "enabled": True,
                "effect": "deny",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 50,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            },
        ]
    )
    engine = ABACEngine(storage)
    engine.initialize()
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    # Disabled policy is skipped, deny policy matches -> False
    assert engine.evaluate(subject, resource, ActionType.READ) is False


def test_evaluate_allow_and_environment_none() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "allow",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 0,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            }
        ]
    )
    engine = ABACEngine(storage)
    engine.initialize()
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ, environment=None) is True


def test_evaluate_non_matching_then_allow() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "wrong",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {"department": "not-it"},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 100,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            },
            {
                "id": 2,
                "name": "match",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 0,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            },
        ]
    )
    engine = ABACEngine(storage)
    engine.initialize()
    subject = Subject("u1", "user", {"department": "sre"}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ) is True


def test_matches_policy_components() -> None:
    engine = ABACEngine(FakePostgresStorage())
    subject = Subject("u1", "user", {"dept": "sre"}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {"severity": "critical"})
    env = Environment({"time": "day"})

    policy_match = Policy(
        id="p",
        name="p",
        description="",
        enabled=True,
        effect="allow",
        subject_conditions={"dept": "sre"},
        resource_conditions={"severity": "critical"},
        environment_conditions={"time": "day"},
        actions={ActionType.READ},
        priority=0,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )
    assert engine._matches_policy(subject, resource, env, policy_match) is True

    policy_subj = policy_match
    policy_subj = Policy(
        id="p2",
        name="p2",
        description="",
        enabled=True,
        effect="allow",
        subject_conditions={"dept": "wrong"},
        resource_conditions={},
        environment_conditions={},
        actions={ActionType.READ},
        priority=0,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )
    assert engine._matches_policy(subject, resource, env, policy_subj) is False

    policy_res = Policy(
        id="p3",
        name="p3",
        description="",
        enabled=True,
        effect="allow",
        subject_conditions={"dept": "sre"},
        resource_conditions={"severity": "low"},
        environment_conditions={},
        actions={ActionType.READ},
        priority=0,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )
    assert engine._matches_policy(subject, resource, env, policy_res) is False

    policy_env = Policy(
        id="p4",
        name="p4",
        description="",
        enabled=True,
        effect="allow",
        subject_conditions={"dept": "sre"},
        resource_conditions={"severity": "critical"},
        environment_conditions={"time": "night"},
        actions={ActionType.READ},
        priority=0,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )
    assert engine._matches_policy(subject, resource, env, policy_env) is False


@pytest.mark.parametrize(
    "condition, value, expected",
    [
        ("sre", "sre", True),
        ("sre", "dev", False),
        ({"equals": "sre"}, "sre", True),
        ({"equals": "sre"}, "dev", False),
        ({"in": ["sre", "dev"]}, "sre", True),
        ({"in": ["sre", "dev"]}, "qa", False),
        ({"contains": "warn"}, "warning", True),
        ({"contains": "crit"}, "warning", False),
        ({"gt": 2}, 3, True),
        ({"gt": 2}, 2, False),
        ({"lt": 5}, 3, True),
        ({"lt": 5}, 6, False),
        ({"gte": 3}, 3, True),
        ({"gte": 3}, 2, False),
        ({"lte": 3}, 3, True),
        ({"lte": 3}, 4, False),
        ({"regex": r"^ABC"}, "ABC-123", True),
        ({"regex": r"^ABC"}, "XYZ-123", False),
    ],
)
def test_matches_conditions_variants(condition: Any, value: Any, expected: bool) -> None:
    engine = ABACEngine(FakePostgresStorage())
    attrs = {"key": value}
    conditions = {"key": condition}
    assert engine._matches_conditions(attrs, conditions) is expected


def test_matches_conditions_missing_key() -> None:
    engine = ABACEngine(FakePostgresStorage())
    assert engine._matches_conditions({}, {"key": "value"}) is False


def test_matches_conditions_empty_and_unknown_dict() -> None:
    engine = ABACEngine(FakePostgresStorage())
    assert engine._matches_conditions({"a": 1}, {}) is True
    # Unknown dict operators are ignored and treated as matched
    assert engine._matches_conditions({"a": 1}, {"a": {"unknown": 2}}) is True


def test_log_evaluation_failure() -> None:
    storage = FakePostgresStorage(policies=[], raise_on={"log"})
    engine = ABACEngine(storage)
    engine._is_initialized = True
    # _log_evaluation failure is caught, no exception propagated
    engine._log_evaluation("1", "u1", "r1", "read", True)
    assert storage.evaluations == []


def test_create_policy_success_and_evaluation() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    pid = engine.create_policy(
        name="allow-read",
        description="",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
        priority=10,
    )
    assert pid is not None
    # _load_policies reloaded the new policy
    assert pid in engine._policies
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ) is True


def test_create_policy_failure() -> None:
    storage = FakePostgresStorage(raise_on={"insert"})
    engine = ABACEngine(storage)
    engine.initialize()
    pid = engine.create_policy(
        name="fail",
        description="",
        effect="allow",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions=["read"],
    )
    assert pid is None


def test_update_policy_no_updates() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("p", "", "allow", {}, {}, {}, ["read"], 0)
    assert engine.update_policy("1") is True


def test_update_policy_multiple_fields_and_list() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("p", "", "allow", {}, {}, {}, ["read"], 0)
    ok = engine.update_policy(
        policy_id="1",
        name="renamed",
        enabled=False,
        priority=99,
        actions=["write"],
    )
    assert ok is True
    # Reloaded policies: the disabled policy should be excluded from _policies
    assert "1" not in engine._policies


def test_update_policy_failure() -> None:
    storage = FakePostgresStorage(raise_on={"update"})
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("p", "", "allow", {}, {}, {}, ["read"], 0)
    ok = engine.update_policy(
        policy_id="1",
        name="renamed",
    )
    assert ok is False


def test_delete_policy_success_and_failure() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("p", "", "allow", {}, {}, {}, ["read"], 0)
    assert engine.delete_policy("1") is True
    assert "1" not in engine._policies

    fail_storage = FakePostgresStorage(raise_on={"delete"})
    fail_engine = ABACEngine(fail_storage)
    fail_engine.initialize()
    assert fail_engine.delete_policy("1") is False


def test_list_policies_enabled_and_all_and_failure() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("enabled", "", "allow", {}, {}, {}, ["read"], 0)
    engine.create_policy("disabled", "", "allow", {}, {}, {}, ["read"], 0)
    engine.update_policy("2", enabled=False)

    enabled = engine.list_policies(enabled_only=True)
    assert len(enabled) == 1
    all_policies = engine.list_policies(enabled_only=False)
    assert len(all_policies) == 2

    fail_storage = FakePostgresStorage(raise_on={"query"})
    fail_engine = ABACEngine(fail_storage)
    fail_engine._is_initialized = True
    assert fail_engine.list_policies() == []


def test_evaluate_with_explicit_environment() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "allow",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {"trusted": True},
                "actions": ["read"],
                "priority": 0,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            }
        ]
    )
    engine = ABACEngine(storage)
    engine.initialize()
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    env = Environment({"trusted": True})
    assert engine.evaluate(subject, resource, ActionType.READ, environment=env) is True


def test_evaluate_disabled_policy_continue() -> None:
    storage = FakePostgresStorage(
        policies=[
            {
                "id": 1,
                "name": "allow",
                "description": "",
                "enabled": True,
                "effect": "allow",
                "subject_conditions": {},
                "resource_conditions": {},
                "environment_conditions": {},
                "actions": ["read"],
                "priority": 0,
                "created_at": dt.datetime.now(),
                "updated_at": dt.datetime.now(),
            }
        ]
    )
    engine = ABACEngine(storage)
    engine.initialize()
    # Inject a disabled higher-priority policy to exercise the continue branch.
    engine._policies["99"] = Policy(
        id="99",
        name="disabled",
        description="",
        enabled=False,
        effect="deny",
        subject_conditions={},
        resource_conditions={},
        environment_conditions={},
        actions={ActionType.READ},
        priority=100,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )
    subject = Subject("u1", "user", {}, set(), set())
    resource = Resource("r1", ResourceType.ALERT, {})
    assert engine.evaluate(subject, resource, ActionType.READ) is True


def test_update_policy_all_fields() -> None:
    storage = FakePostgresStorage()
    engine = ABACEngine(storage)
    engine.initialize()
    engine.create_policy("p", "", "allow", {}, {}, {}, ["read"], 0)
    ok = engine.update_policy(
        policy_id="1",
        name="full",
        description="updated",
        enabled=True,
        effect="deny",
        subject_conditions={"dept": "sre"},
        resource_conditions={"severity": "high"},
        environment_conditions={"time": "day"},
        actions=["delete"],
        priority=42,
    )
    assert ok is True
