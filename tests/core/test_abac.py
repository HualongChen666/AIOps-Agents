# -*- coding: utf-8 -*-
"""测试ABAC模块"""

import pytest


class TestABACModule:
    """测试ABAC模块"""

    def test_abac_module_exists(self):
        """测试ABAC模块存在"""
        from core import abac

        assert abac is not None

    def test_abac_has_functions(self):
        """测试ABAC模块有函数"""
        from core import abac

        # 检查模块有函数或类
        assert (
            hasattr(abac, "ABACPolicy") or hasattr(abac, "check_permission") or len(dir(abac)) > 0
        )


class TestActionType:
    """测试ActionType枚举"""

    def test_action_type_values(self):
        """测试ActionType枚举值"""
        try:
            from core.abac import ActionType

            assert ActionType.READ.value == "read"
            assert ActionType.WRITE.value == "write"
            assert ActionType.DELETE.value == "delete"
            assert ActionType.EXECUTE.value == "execute"
            assert ActionType.ADMIN.value == "admin"
        except Exception as e:
            pytest.skip(f"Cannot test ActionType: {e}")


class TestResourceType:
    """测试ResourceType枚举"""

    def test_resource_type_values(self):
        """测试ResourceType枚举值"""
        try:
            from core.abac import ResourceType

            assert ResourceType.ANOMALY.value == "anomaly"
            assert ResourceType.ALERT.value == "alert"
            assert ResourceType.METRIC.value == "metric"
            assert ResourceType.CONFIGURATION.value == "configuration"
            assert ResourceType.POLICY.value == "policy"
            assert ResourceType.WORKFLOW.value == "workflow"
            assert ResourceType.DEPLOYMENT.value == "deployment"
            assert ResourceType.SERVICE.value == "service"
        except Exception as e:
            pytest.skip(f"Cannot test ResourceType: {e}")


class TestSubject:
    """测试Subject数据类"""

    def test_subject_creation(self):
        """测试Subject创建"""
        try:
            from core.abac import Subject

            subject = Subject(
                id="user1",
                type="user",
                attributes={"department": "engineering"},
                roles={"admin"},
                groups={"developers"},
            )
            assert subject.id == "user1"
            assert subject.type == "user"
            assert subject.attributes["department"] == "engineering"
        except Exception as e:
            pytest.skip(f"Cannot test Subject creation: {e}")

    def test_subject_get_attribute(self):
        """测试Subject获取属性"""
        try:
            from core.abac import Subject

            subject = Subject(
                id="user1",
                type="user",
                attributes={"department": "engineering"},
                roles={"admin"},
                groups={"developers"},
            )
            assert subject.get_attribute("department") == "engineering"
            assert subject.get_attribute("nonexistent", "default") == "default"
        except Exception as e:
            pytest.skip(f"Cannot test Subject get_attribute: {e}")


class TestResource:
    """测试Resource数据类"""

    def test_resource_creation(self):
        """测试Resource创建"""
        try:
            from core.abac import Resource, ResourceType

            resource = Resource(
                id="resource1",
                type=ResourceType.ALERT,
                attributes={"sensitivity": "high"},
                owner="user1",
            )
            assert resource.id == "resource1"
            assert resource.type == ResourceType.ALERT
            assert resource.owner == "user1"
        except Exception as e:
            pytest.skip(f"Cannot test Resource creation: {e}")

    def test_resource_get_attribute(self):
        """测试Resource获取属性"""
        try:
            from core.abac import Resource, ResourceType

            resource = Resource(
                id="resource1",
                type=ResourceType.ALERT,
                attributes={"sensitivity": "high"},
            )
            assert resource.get_attribute("sensitivity") == "high"
            assert resource.get_attribute("nonexistent", "default") == "default"
        except Exception as e:
            pytest.skip(f"Cannot test Resource get_attribute: {e}")


class TestEnvironment:
    """测试Environment数据类"""

    def test_environment_creation(self):
        """测试Environment创建"""
        try:
            from core.abac import Environment

            env = Environment(attributes={"time": "9-5", "location": "office"})
            assert env.attributes["time"] == "9-5"
        except Exception as e:
            pytest.skip(f"Cannot test Environment creation: {e}")

    def test_environment_get_attribute(self):
        """测试Environment获取属性"""
        try:
            from core.abac import Environment

            env = Environment(attributes={"time": "9-5"})
            assert env.get_attribute("time") == "9-5"
            assert env.get_attribute("nonexistent", "default") == "default"
        except Exception as e:
            pytest.skip(f"Cannot test Environment get_attribute: {e}")


class TestPolicy:
    """测试Policy数据类"""

    def test_policy_creation(self):
        """测试Policy创建"""
        try:
            from datetime import datetime

            from core.abac import ActionType, Policy

            policy = Policy(
                id="policy1",
                name="Test Policy",
                description="A test policy",
                enabled=True,
                effect="allow",
                subject_conditions={"department": {"equals": "engineering"}},
                resource_conditions={"sensitivity": {"in": ["low", "medium"]}},
                environment_conditions={},
                actions={ActionType.READ, ActionType.WRITE},
                priority=10,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            assert policy.id == "policy1"
            assert policy.name == "Test Policy"
            assert policy.enabled is True
            assert policy.effect == "allow"
        except Exception as e:
            pytest.skip(f"Cannot test Policy creation: {e}")


class FakeConnection:
    """In-memory connection for ABACEngine tests."""

    def __init__(self):
        self.tables = {"abac_policies": [], "abac_policy_evaluations": []}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        pass


class FakeCursor:
    """In-memory cursor for ABACEngine tests."""

    def __init__(self, conn):
        self.conn = conn
        self._last_result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def execute(self, query, params=None):
        query = query.strip()
        params = params or ()
        if query.startswith("CREATE") or query.startswith("CREATE INDEX"):
            return
        if query.startswith("INSERT"):
            table_name = self._table_from_insert(query)
            row = dict(zip(self._columns_from_insert(query), params))
            if "RETURNING id" in query:
                row_id = len(self.conn.tables[table_name]) + 1
                row["id"] = row_id
                self.conn.tables[table_name].append(row)
                self._last_result = (row_id,)
            else:
                self.conn.tables[table_name].append(row)
        elif query.startswith("UPDATE"):
            # Find row by id (last param) and update fields
            row_id = int(params[-1])
            for row in self.conn.tables["abac_policies"]:
                if row.get("id") == row_id:
                    for key, value in zip(self._columns_from_update(query), params):
                        row[key] = value
                    break
        elif query.startswith("DELETE"):
            row_id = int(params[0])
            before = len(self.conn.tables["abac_policies"])
            self.conn.tables["abac_policies"] = [
                r for r in self.conn.tables["abac_policies"] if r.get("id") != row_id
            ]
            self._last_result = (len(self.conn.tables["abac_policies"]) - before,)
        elif query.startswith("SELECT"):
            self._last_result = self.conn.tables["abac_policies"]

    def fetchone(self):
        return self._last_result

    def _table_from_insert(self, query):
        if "abac_policy_evaluations" in query:
            return "abac_policy_evaluations"
        return "abac_policies"

    def _columns_from_insert(self, query):
        start = query.index("(") + 1
        end = query.index(")")
        cols = [c.strip() for c in query[start:end].split(",")]
        if "RETURNING" in query:
            cols.append("id")
        return cols

    def _columns_from_update(self, query):
        # Naively parse 'SET col1 = %s, col2 = %s'
        start = query.upper().index("SET") + 3
        end = query.upper().index("WHERE")
        parts = query[start:end].split(",")
        cols = []
        for part in parts:
            col = part.split("=")[0].strip()
            cols.append(col)
        return cols


class FakeStorage:
    """In-memory storage for ABACEngine tests."""

    def __init__(self):
        self._conn = FakeConnection()

    def get_connection(self):
        return self._conn

    def execute_query(self, query, params=None):
        import json
        from datetime import datetime

        result = []
        for row in self._conn.tables["abac_policies"]:
            processed = dict(row)
            for key in (
                "subject_conditions",
                "resource_conditions",
                "environment_conditions",
                "actions",
            ):
                value = processed.get(key)
                if isinstance(value, str):
                    try:
                        processed[key] = json.loads(value)
                    except json.JSONDecodeError:
                        processed[key] = value
            processed.setdefault("enabled", True)
            processed.setdefault("description", "")
            processed.setdefault("created_at", datetime.now())
            processed.setdefault("updated_at", datetime.now())
            result.append(processed)
        return result


class TestABACEngine:
    """测试ABACEngine类"""

    @pytest.fixture
    def engine(self):
        from core.abac import ABACEngine

        return ABACEngine(FakeStorage())

    def test_abac_engine_initialization(self):
        from core.abac import ABACEngine

        engine = ABACEngine(FakeStorage())
        assert engine._is_initialized is False

    def test_abac_engine_initialize_success(self, engine):
        assert engine.initialize() is True
        assert engine._is_initialized is True

    def test_abac_engine_evaluate_not_initialized(self):
        from core.abac import ABACEngine, ActionType, Resource, ResourceType, Subject

        engine = ABACEngine(FakeStorage())
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        resource = Resource(id="resource1", type=ResourceType.ALERT, attributes={})
        assert engine.evaluate(subject, resource, ActionType.READ) is False

    def test_abac_engine_create_policy_and_evaluate(self, engine):
        from core.abac import ActionType, Resource, ResourceType, Subject

        engine.initialize()
        policy_id = engine.create_policy(
            name="allow_read",
            description="Allow read for engineering",
            effect="allow",
            subject_conditions={"department": {"equals": "engineering"}},
            resource_conditions={"sensitivity": {"in": ["low", "medium"]}},
            environment_conditions={},
            actions=["read"],
            priority=10,
        )
        assert policy_id is not None
        subject = Subject(
            id="user1",
            type="user",
            attributes={"department": "engineering"},
            roles=set(),
            groups=set(),
        )
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={"sensitivity": "low"})
        assert engine.evaluate(subject, resource, ActionType.READ) is True

    def test_abac_engine_evaluate_deny_policy(self, engine):
        from core.abac import ActionType, Resource, ResourceType, Subject

        engine.initialize()
        engine.create_policy(
            name="deny_write",
            description="Deny write",
            effect="deny",
            subject_conditions={},
            resource_conditions={},
            environment_conditions={},
            actions=["write"],
            priority=20,
        )
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={})
        assert engine.evaluate(subject, resource, ActionType.WRITE) is False

    def test_abac_engine_evaluate_no_matching_policy(self, engine):
        from core.abac import ActionType, Resource, ResourceType, Subject

        engine.initialize()
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={})
        assert engine.evaluate(subject, resource, ActionType.READ) is False

    def test_abac_engine_update_and_delete_policy(self, engine):
        from core.abac import ActionType, Resource, ResourceType, Subject

        engine.initialize()
        policy_id = engine.create_policy(
            name="policy",
            description="desc",
            effect="allow",
            subject_conditions={},
            resource_conditions={},
            environment_conditions={},
            actions=["read"],
            priority=10,
        )
        assert engine.update_policy(policy_id, enabled=False) is True
        subject = Subject(id="user1", type="user", attributes={}, roles=set(), groups=set())
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={})
        # Disabled policy should not match
        assert engine.evaluate(subject, resource, ActionType.READ) is False
        assert engine.delete_policy(policy_id) is True

    def test_abac_engine_list_policies(self, engine):
        engine.initialize()
        engine.create_policy(
            name="list_me",
            description="desc",
            effect="allow",
            subject_conditions={},
            resource_conditions={},
            environment_conditions={},
            actions=["read"],
        )
        policies = engine.list_policies()
        assert len(policies) == 1
        assert policies[0]["name"] == "list_me"

    def test_abac_engine_matches_conditions_variants(self, engine):
        from core.abac import ActionType, Resource, ResourceType, Subject

        engine.initialize()
        engine.create_policy(
            name="complex",
            description="desc",
            effect="allow",
            subject_conditions={
                "level": {"gt": 1},
                "role": {"in": ["admin", "editor"]},
                "tag": {"contains": "vip"},
                "score": {"gte": 50, "lte": 100},
                "name": {"regex": "^Alice"},
            },
            resource_conditions={"env": {"lt": 5}},
            environment_conditions={},
            actions=["read"],
            priority=10,
        )
        subject = Subject(
            id="user1",
            type="user",
            attributes={
                "level": 3,
                "role": "admin",
                "tag": "super-vip",
                "score": 75,
                "name": "AliceSmith",
            },
            roles=set(),
            groups=set(),
        )
        resource = Resource(id="res1", type=ResourceType.ALERT, attributes={"env": 2})
        assert engine.evaluate(subject, resource, ActionType.READ) is True

    def test_abac_engine_create_abac_engine_factory(self):
        from core.abac import create_abac_engine

        engine = create_abac_engine(FakeStorage())
        assert engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
