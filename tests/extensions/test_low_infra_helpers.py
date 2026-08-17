# -*- coding: utf-8 -*-
"""Smoke tests for low-coverage infrastructure helper modules.

These modules are loaded with ``importlib.util.spec_from_file_location`` under
unique package names.  External I/O dependencies (``httpx``, ``requests``,
``subprocess``, ``redis``, ``aiohttp``, etc.) are monkey-patched through the
existing ``conftest`` autouse fixture and module-level stubs created here.
"""

from __future__ import annotations

import importlib.util
import sys  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"
INFRA = ROOT / "infrastructure"
OPS = ROOT / "operations"


# ---------------------------------------------------------------------------
# Minimal schema/dependency stubs
# ---------------------------------------------------------------------------


class _Step:
    def __init__(self, action: str = "", result=None, status: str = "pending"):
        self.action = action
        self.result = result  # noqa: F841  # Variable for test verification
        self.status = status


class _SagaTx:
    def __init__(self, steps=None, status: str = "pending", saga_id: str = "s-1"):
        self.steps = steps or []
        self.status = status
        self.saga_id = saga_id


class _ConfigValue:
    def __init__(
        self,
        config_id: str = "",
        key: str = "",
        value: str = "",
        namespace: str = "",
        encrypted: bool = False,
    ):
        self.config_id = config_id
        self.key = key
        self.value = value
        self.namespace = namespace
        self.encrypted = encrypted


class _ConfigSnapshot:
    def __init__(
        self,
        snapshot_id: str = "",
        namespace: str = "",
        version: str = "1.0.0",
        configs=None,
    ):
        self.snapshot_id = snapshot_id
        self.namespace = namespace
        self.version = version
        self.configs = configs or {}


class _ConfigUpdateEvent:
    def __init__(
        self,
        event_id: str = "",
        config_id: str = "",
        namespace: str = "",
        old_value: str = "",
        new_value: str = "",
    ):
        self.event_id = event_id
        self.config_id = config_id
        self.namespace = namespace
        self.old_value = old_value
        self.new_value = new_value

    def model_dump(self):
        return self.__dict__.copy()


class _ConfigVersion:
    def __init__(
        self,
        version_id: str = "",
        namespace: str = "",
        message: str = "",
        author: str = "system",
    ):
        self.version_id = version_id
        self.namespace = namespace
        self.message = message
        self.author = author


class _User:
    def __init__(
        self,
        user_id: str = "",
        username: str = "",
        email: str = "",
        full_name: str = "",
        role: str = "viewer",
        organization_id: str = "",
        tenant_id: str = "default",
        created_at=None,
        updated_at=None,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email  # noqa: F841  # Variable for test verification
        self.full_name = full_name
        self.role = role
        self.organization_id = organization_id
        self.tenant_id = tenant_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class _UserCreate:
    def __init__(
        self,
        username: str = "",
        email: str = "",
        full_name: str = "",
        role: str = "viewer",
        organization_id: str = "",
        tenant_id: str = "default",
    ):
        self.username = username
        self.email = email  # noqa: F841  # Variable for test verification
        self.full_name = full_name
        self.role = role
        self.organization_id = organization_id
        self.tenant_id = tenant_id


class _UserUpdate:
    def __init__(
        self,
        full_name: str | None = None,
        email: str | None = None,
        role: str | None = None,
    ):
        self.full_name = full_name
        self.email = email  # noqa: F841  # Variable for test verification
        self.role = role

    def model_dump(self, exclude_none: bool = False):
        d = self.__dict__.copy()
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        return d


class _Organization:
    def __init__(
        self,
        org_id: str = "",
        name: str = "",
        parent_id: str | None = None,
        tenant_id: str = "default",
    ):
        self.org_id = org_id
        self.name = name
        self.parent_id = parent_id
        self.tenant_id = tenant_id


class _Role:
    def __init__(
        self,
        role_id: str = "",
        name: str = "",
        tenant_id: str = "default",
        permissions=None,
    ):
        self.role_id = role_id
        self.name = name
        self.tenant_id = tenant_id
        self.permissions = permissions or []


class _Permission:
    def __init__(
        self,
        permission_id: str = "",
        resource: str = "",
        action: str = "",
        description: str = "",
    ):
        self.permission_id = permission_id
        self.resource = resource
        self.action = action
        self.description = description


class _Session:
    def __init__(self, session_id: str = "", user_id: str = "", token: str = ""):
        self.session_id = session_id
        self.user_id = user_id
        self.token = token


class _AuditLogEntry:
    def __init__(self, log_id: str = "", user_id: str = "", action: str = ""):
        self.log_id = log_id
        self.user_id = user_id
        self.action = action


class _AuthToken:
    def __init__(
        self,
        access_token: str = "",
        token_type: str = "bearer",
        expires_in: int = 0,
        refresh_token: str = "",
    ):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token


class _FakeConfigRepo:
    """Fake config repository for config-service helpers."""

    def __init__(self):
        self._configs = {}
        self._snapshots = {}
        self._sagas = {}

    async def save_saga(self, saga):
        self._sagas[saga.saga_id] = saga
        return saga.saga_id

    async def get_saga(self, saga_id):
        return self._sagas.get(saga_id)

    async def list_configs(self, namespace: str, limit: int = 100):
        return [
            c for c in list(self._configs.values()) if getattr(c, "namespace", "") == namespace
        ][:limit]

    async def save_config(self, config):
        self._configs[config.config_id] = config
        return config.config_id

    async def save_snapshot(self, snapshot):
        self._snapshots[snapshot.snapshot_id] = snapshot
        return snapshot.snapshot_id

    async def get_snapshot(self, snapshot_id):
        return self._snapshots.get(snapshot_id)


class _ConfigManager:
    def __init__(self, repo):
        self._repo = repo

    async def create(self, config):
        self._repo._configs[config.config_id] = config
        return config

    async def get(self, config_id):
        return self._repo._configs.get(config_id)

    async def update(self, config_id, value, updated_by="system"):
        c = self._repo._configs.get(config_id)
        if c:
            c.value = value
            return c
        return None


class _ConfigVersionControl:
    def __init__(self, repo):
        self._repo = repo

    async def commit(self, namespace, message, author="system"):
        return _ConfigVersion(
            version_id=f"v-{namespace}",
            namespace=namespace,
            message=message,
            author=author,
        )


class _ConfigAuditLogger:
    def __init__(self, repo):
        self._repo = repo

    async def log(self, entity_id, action, meta=None):
        return "ok"


class _ConfigEncryption:
    def __init__(self, key):
        self.key = key

    def encrypt(self, value):
        return f"enc-{value}"


class _HotUpdateManager:
    def __init__(self):
        self._subscribers = {}

    async def subscribe(self, namespace, connection):
        self._subscribers.setdefault(namespace, []).append(connection)

    async def publish(self, event):
        for conn in self._subscribers.get(getattr(event, "namespace", ""), []):
            if hasattr(conn, "send_json"):
                await conn.send_json(event.model_dump())
        return 0


class _RollbackManager:
    def __init__(self, repo):
        self.repo = repo

    async def snapshot(self, namespace):
        configs = await self.repo.list_configs(namespace, limit=10000)
        snap = _ConfigSnapshot(
            snapshot_id=f"snap-{namespace}",
            namespace=namespace,
            version="1.0.0",
            configs={getattr(c, "key", ""): getattr(c, "value", "") for c in configs},
        )
        await self.repo.save_snapshot(snap)
        return snap

    async def restore(self, snapshot_id):
        snap = await self.repo.get_snapshot(snapshot_id)
        if not snap:
            return []
        restored = []
        for key, value in snap.configs.items():
            c = _ConfigValue(
                config_id=f"{snap.namespace}-{key}",
                key=key,
                value=value,
                namespace=snap.namespace,
            )
            await self.repo.save_config(c)
            restored.append(c.config_id)
        return restored


class _ConfigSagaOrchestrator:
    def __init__(self, repo):
        self.repo = repo

    async def execute(self, saga):
        return saga


class _NamespaceManager:
    def __init__(self, repo):
        self.repo = repo


class _LockCacheManager:
    def __init__(self, *args, **kwargs):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def set(self, key, value, ttl=None):
        self._store[key] = value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = []
    return mod


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Per-test stub fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _low_infra_stubs(monkeypatch):
    """Provide fake ``services.*`` and ``jose`` modules for the addon files."""
    # jose stub (auth.py depends on it)
    jose_mod = types.ModuleType("jose")

    class _JWTError(Exception):
        pass

    jose_mod.JWTError = _JWTError
    jwt_mod = types.ModuleType("jose.jwt")

    def _jwt_encode(*args, **kwargs):
        return "test-token"

    def _jwt_decode(token, *args, **kwargs):
        if token == "bad":
            raise _JWTError("bad token")
        return {"sub": "u1", "role": "admin", "tenant": "t1", "exp": 1234567890}

    jwt_mod.encode = _jwt_encode
    jwt_mod.decode = _jwt_decode
    jose_mod.jwt = jwt_mod
    monkeypatch.setitem(sys.modules, "jose", jose_mod)

    # services.config_service namespace
    cfg_pkg = _make_module("services.config_service")
    monkeypatch.setitem(sys.modules, "services.config_service", cfg_pkg)

    cfg_schemas = _make_module("services.config_service.schemas")
    cfg_schemas.ConfigValue = _ConfigValue
    cfg_schemas.ConfigSnapshot = _ConfigSnapshot
    cfg_schemas.ConfigUpdateEvent = _ConfigUpdateEvent
    cfg_schemas.ConfigVersion = _ConfigVersion
    cfg_schemas.SagaTransaction = _SagaTx
    cfg_schemas.SagaStep = _Step
    cfg_schemas.Step = _Step
    monkeypatch.setitem(sys.modules, "services.config_service.schemas", cfg_schemas)

    cfg_repo = _make_module("services.config_service.repository")
    cfg_repo.ConfigRepository = _FakeConfigRepo
    monkeypatch.setitem(sys.modules, "services.config_service.repository", cfg_repo)

    for mod_name, attrs in {
        "audit_logger": {"ConfigAuditLogger": _ConfigAuditLogger},
        "config_manager": {"ConfigManager": _ConfigManager},
        "encryption": {"ConfigEncryption": _ConfigEncryption},
        "hot_update": {"HotUpdateManager": _HotUpdateManager},
        "namespace": {"NamespaceManager": _NamespaceManager},
        "rollback": {"RollbackManager": _RollbackManager},
        "saga": {"ConfigSagaOrchestrator": _ConfigSagaOrchestrator},
        "version_control": {"ConfigVersionControl": _ConfigVersionControl},
    }.items():
        mod = _make_module(f"services.config_service.{mod_name}")
        for attr_name, value in attrs.items():
            setattr(mod, attr_name, value)
        monkeypatch.setitem(sys.modules, mod.__name__, mod)

    # services.user_service namespace
    usr_pkg = _make_module("services.user_service")
    monkeypatch.setitem(sys.modules, "services.user_service", usr_pkg)

    usr_schemas = _make_module("services.user_service.schemas")
    usr_schemas.User = _User
    usr_schemas.UserCreate = _UserCreate
    usr_schemas.UserUpdate = _UserUpdate
    usr_schemas.Organization = _Organization
    usr_schemas.Role = _Role
    usr_schemas.Permission = _Permission
    usr_schemas.Session = _Session
    usr_schemas.AuditLogEntry = _AuditLogEntry
    usr_schemas.AuthToken = _AuthToken
    usr_schemas.SagaTransaction = _SagaTx
    usr_schemas.SagaStep = _Step
    usr_schemas.Step = _Step
    monkeypatch.setitem(sys.modules, "services.user_service.schemas", usr_schemas)

    usr_config = _make_module("services.user_service.config")
    usr_config.settings = types.SimpleNamespace(
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
    )
    monkeypatch.setitem(sys.modules, "services.user_service.config", usr_config)

    # Load the real in-memory user repository under the fake package namespace.
    repo_path = INFRA / "user_service" / "repository.py"
    spec = importlib.util.spec_from_file_location("__user_repository", str(repo_path))
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {repo_path}")
    repo_mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "services.user_service.repository", repo_mod)
    spec.loader.exec_module(repo_mod)


# ---------------------------------------------------------------------------
# Config service helpers
# ---------------------------------------------------------------------------


async def test_config_saga():
    path = INFRA / "config_service" / "saga.py"
    mod = _load_module("__cfg_saga", path)
    repo = mod.ConfigRepository()
    orchestrator = mod.ConfigSagaOrchestrator(repo)

    async def handler(step):
        return "ok"

    async def comp(step):
        return "undone"

    step = _Step(action="a1")
    saga = _SagaTx(steps=[step])
    orchestrator.register("a1", handler, comp)
    result = await orchestrator.execute(saga)  # noqa: F841  # Variable for test verification
    assert result.status == "success"
    assert step.status == "success"
    assert step.result == "ok"  # noqa: F841  # Variable for test verification

    async def fail(step):
        raise ValueError("boom")

    orchestrator2 = mod.ConfigSagaOrchestrator(repo)
    good_step = _Step(action="ok")
    bad_step = _Step(action="fail")
    saga2 = _SagaTx(steps=[good_step, bad_step])
    orchestrator2.register("ok", handler, comp)
    orchestrator2.register("fail", fail, comp)
    with pytest.raises(ValueError):
        await orchestrator2.execute(saga2)
    assert good_step.status == "compensated"
    assert bad_step.status == "pending"


async def test_config_hot_update():
    path = INFRA / "config_service" / "hot_update.py"
    mod = _load_module("__cfg_hot_update", path)
    mgr = mod.HotUpdateManager()

    class Conn:
        def __init__(self):
            self.sent = None

        async def send_json(self, msg):
            self.sent = msg

    conn = Conn()
    await mgr.subscribe("ns1", conn)
    event = _ConfigUpdateEvent(
        event_id="e1",
        config_id="c1",
        namespace="ns1",
        old_value="old",
        new_value="new",
    )
    assert await mgr.publish(event) == 1
    assert conn.sent == event.model_dump()
    assert await mgr.broadcast("ns1", {"hello": "world"}) == 1


async def test_config_rollback():
    path = INFRA / "config_service" / "rollback.py"
    mod = _load_module("__cfg_rollback", path)
    repo = mod.ConfigRepository()
    repo._configs = {
        "c1": _ConfigValue(config_id="c1", key="k1", value="v1", namespace="ns1"),
        "c2": _ConfigValue(config_id="c2", key="k2", value="v2", namespace="ns1"),
    }
    mgr = mod.RollbackManager(repo)
    snapshot = await mgr.snapshot("ns1")
    assert snapshot.snapshot_id.startswith("snap-ns1-")
    assert snapshot.configs == {"k1": "v1", "k2": "v2"}
    restored = await mgr.restore(snapshot.snapshot_id)
    assert len(restored) == 2


async def test_config_orchestrator():
    path = INFRA / "config_service" / "orchestrator.py"
    mod = _load_module("__cfg_orchestrator", path)
    repo = mod.ConfigRepository()
    orch = mod.ConfigOrchestrator(repo, encryption_key="key")

    config = mod.ConfigValue(
        config_id="c1",
        key="k1",
        value="plain",
        namespace="ns1",
        encrypted=False,
    )
    created = await orch.create_config(config)
    assert created.value == "plain"

    updated = await orch.update_config("c1", "new-value")
    assert updated is not None
    assert updated.value == "new-value"

    encrypted_config = mod.ConfigValue(
        config_id="c2",
        key="k2",
        value="secret",
        namespace="ns1",
        encrypted=True,
    )
    await orch.create_config(encrypted_config)
    assert encrypted_config.value.startswith("enc-")

    snapshot = await orch.snapshot("ns1")
    assert snapshot.snapshot_id
    restored = await orch.restore(snapshot.snapshot_id)
    assert len(restored) >= 1

    version = await orch.commit_version("ns1", "msg")
    assert version.version_id

    step = _Step(action="x")
    saga = _SagaTx(steps=[step], saga_id="s1")
    result = await orch.run_saga(saga)  # noqa: F841  # Variable for test verification
    assert result is saga


# ---------------------------------------------------------------------------
# User service helpers
# ---------------------------------------------------------------------------


async def test_user_saga():
    path = INFRA / "user_service" / "saga.py"
    mod = _load_module("__user_saga", path)
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    orchestrator = mod.UserSagaOrchestrator(repo)

    async def handler(step):
        return "ok"

    async def comp(step):
        return "undone"

    step = _Step(action="a1")
    saga = _SagaTx(steps=[step], saga_id="us1")
    orchestrator.register("a1", handler, comp)
    result = await orchestrator.execute(saga)  # noqa: F841  # Variable for test verification
    assert result.status == "success"


async def test_user_organization():
    path = INFRA / "user_service" / "organization.py"
    mod = _load_module("__user_organization", path)
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    mgr = mod.OrganizationManager(repo)

    root = _Organization(org_id="o1", name="Root", tenant_id="t1")
    child = _Organization(org_id="o2", name="Child", parent_id="o1", tenant_id="t1")
    await mgr.create(root)
    await mgr.create(child)

    assert (await mgr.get("o1")) is root
    assert len(await mgr.list("t1")) == 2

    tree = await mgr.tree("t1")
    assert len(tree) == 1
    assert tree[0]["org_id"] == "o1"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["org_id"] == "o2"


async def test_user_rbac():
    path = INFRA / "user_service" / "rbac.py"
    mod = _load_module("__user_rbac", path)
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    mgr = mod.RBACManager(repo)
    role = _Role(role_id="r1", name="admin", tenant_id="t1")

    created = await mgr.create_role(role)
    assert created.role_id == "r1"
    assert (await mgr.get_role("r1")) is created
    assert len(await mgr.list_roles("t1")) == 1

    updated = await mgr.assign_permissions("r1", ["p1", "p99"])
    assert updated is not None
    assert "p1" in updated.permissions
    assert "p99" not in updated.permissions

    admin = _User(role="admin")
    viewer = _User(role="viewer")
    assert mgr.check_permission(admin, "x", "write") is True
    assert mgr.check_permission(viewer, "x", "write") is False
    assert mgr.check_permission(viewer, "x", "read") is True


async def test_user_auth(monkeypatch):
    path = INFRA / "user_service" / "auth.py"
    mod = _load_module("__user_auth", path)
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    mgr = mod.AuthManager(repo)
    monkeypatch.setenv("AIOPS_DEMO_PASSWORD", "secret")

    user = _User(
        user_id="u1",
        username="alice",
        role="admin",
        tenant_id="t1",
    )
    await repo.save_user(user)

    assert await mgr.authenticate("alice", "secret") is user
    assert await mgr.authenticate("alice", "wrong") is None

    token = mgr.create_access_token(user)
    assert token == "test-token"
    decoded = mgr.decode_token(token)
    assert decoded["sub"] == "u1"
    assert mgr.decode_token("bad") is None

    login = await mgr.login("alice", "secret")
    assert login.access_token == "test-token"
    assert login.token_type == "bearer"

    monkeypatch.setenv("DEFAULT_TOKEN_TYPE", "jwt")
    login2 = await mgr.login("alice", "secret")
    assert login2.token_type == "jwt"


async def test_user_repository():
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()

    user = _User(user_id="u1", username="alice", tenant_id="t1")
    assert await repo.save_user(user) == "u1"
    assert (await repo.get_user("u1")) is user
    assert (await repo.get_user_by_username("alice")) is user
    assert len(await repo.list_users("t1")) == 1
    assert await repo.delete_user("u1") is True
    assert await repo.delete_user("u1") is False

    role = _Role(role_id="r1", tenant_id="t1")
    await repo.save_role(role)
    assert (await repo.get_role("r1")) is role
    assert len(await repo.list_roles("t1")) == 1

    org = _Organization(org_id="o1", tenant_id="t1")
    await repo.save_organization(org)
    assert (await repo.get_organization("o1")) is org
    assert len(await repo.list_organizations("t1")) == 1

    session = _Session(session_id="s1", user_id="u1")
    await repo.save_session(session)
    assert (await repo.get_session("s1")) is session
    assert await repo.delete_session("s1") is True

    entry = _AuditLogEntry(log_id="l1", user_id="u1", action="login")
    await repo.save_audit_log(entry)
    assert len(await repo.list_audit_logs("u1")) == 1

    saga = _SagaTx(saga_id="sg1")
    await repo.save_saga(saga)
    assert (await repo.get_saga("sg1")) is saga


async def test_user_manager():
    path = INFRA / "user_service" / "user_manager.py"
    mod = _load_module("__user_manager", path)
    from services.user_service.repository import InMemoryUserRepository

    repo = InMemoryUserRepository()
    mgr = mod.UserManager(repo)

    data = _UserCreate(
        username="alice",
        email="a@b.com",
        full_name="Alice",
        role="admin",
        organization_id="o1",
        tenant_id="t1",
    )
    user = await mgr.create(data)
    assert user.user_id == "user-alice"
    assert (await mgr.get("user-alice")) is user
    assert len(await mgr.list("t1")) == 1

    updated = await mgr.update("user-alice", _UserUpdate(full_name="Alice Smith"))
    assert updated is not None
    assert updated.full_name == "Alice Smith"
    assert await mgr.delete("user-alice") is True
    assert await mgr.delete("user-alice") is False


# ---------------------------------------------------------------------------
# Lock helpers (many addon lock modules)
# ---------------------------------------------------------------------------


LOCK_PATHS = [
    INFRA / "ansible_automation_service" / "lock.py",
    INFRA / "cloud_monitoring_service" / "lock.py",
    INFRA / "kubernetes_orchestration_service" / "lock.py",
    INFRA / "terraform_iac_service" / "lock.py",
]


@pytest.mark.parametrize("lock_path", LOCK_PATHS, ids=lambda p: p.parent.name)
async def test_lock_module(lock_path, monkeypatch):
    pkg_name = f"__lock_{lock_path.parent.name}"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(lock_path.parent)]
    monkeypatch.setitem(sys.modules, pkg_name, pkg)

    cache_mod = _make_module(f"{pkg_name}.cache")
    cache_mod.CacheManager = _LockCacheManager
    monkeypatch.setitem(sys.modules, f"{pkg_name}.cache", cache_mod)

    config_mod = _make_module(f"{pkg_name}.config")
    config_mod.settings = types.SimpleNamespace(
        redis_url=None,
        enable_distributed_lock=False,
        lock_ttl_seconds=30,
        service_name=lock_path.parent.name,
        idempotency_ttl_seconds=3600,
    )
    monkeypatch.setitem(sys.modules, f"{pkg_name}.config", config_mod)

    mod = _load_module(f"{pkg_name}.lock", lock_path)
    lock_mgr = mod.LockManager()
    async with lock_mgr.acquire("res-1", request_id="req-1"):
        pass

    idem = mod.IdempotencyManager()
    assert idem.get_key({"idempotency_key": "abc"}, "op") == "op:abc"
    assert idem.get_key({"config": {"idempotency_key": "def"}}, "op") == "op:def"
    assert "op:" in idem.get_key({"foo": "bar"}, "op")

    class Obj:
        def model_dump(self):
            return {"idempotency_key": "obj"}

    assert idem.get_key(Obj(), "op") == "op:obj"

    assert await idem.is_processed("k1") is False
    await idem.mark_processed("k1")
    assert await idem.is_processed("k1") is True


# ---------------------------------------------------------------------------
# Operations / incident response
# ---------------------------------------------------------------------------


async def test_incident_response_service(monkeypatch):
    path = OPS / "incident_response_service" / "service.py"
    pkg_name = "__incident_response"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(path.parent)]
    monkeypatch.setitem(sys.modules, pkg_name, pkg)

    cache_mod = _make_module(f"{pkg_name}.cache")
    cache_mod.CacheManager = _LockCacheManager
    monkeypatch.setitem(sys.modules, f"{pkg_name}.cache", cache_mod)

    config_mod = _make_module(f"{pkg_name}.config")
    config_mod.settings = types.SimpleNamespace(
        service_name="incident-response-test",
        redis_url=None,
    )
    monkeypatch.setitem(sys.modules, f"{pkg_name}.config", config_mod)

    metrics_mod = _make_module(f"{pkg_name}.metrics")

    class _MetricsCollector:
        def __init__(self, service_name):
            self.request_count = 0
            self.cache_hits_count = 0
            self.cache_misses_count = 0
            self.service_name = service_name

        def inc_request(self, name):
            self.request_count += 1

        def inc_cache_hit(self, name=None):
            self.cache_hits_count += 1

        def inc_cache_miss(self, name=None):
            self.cache_misses_count += 1

        def inc_operation(self, name):
            pass

    metrics_mod.MetricsCollector = _MetricsCollector
    monkeypatch.setitem(sys.modules, f"{pkg_name}.metrics", metrics_mod)

    retry_mod = _make_module(f"{pkg_name}.retry")

    class _RetryEngine:
        def __init__(self, policy, metrics):
            self.policy = policy
            self.metrics = metrics

    retry_mod.RetryEngine = _RetryEngine
    monkeypatch.setitem(sys.modules, f"{pkg_name}.retry", retry_mod)

    mod = _load_module(f"{pkg_name}.service", path)
    svc = mod.IncidentResponseService()

    assert (await svc.list_methods())["status"] == "ok"
    assert (await svc.get_stats())["status"] == "ok"
    assert (await svc.get_state())["status"] == "not_found"

    await svc.design_response_framework(
        {"config": {"feature": "design_response_framework", "x": 1}}
    )
    state = await svc.get_state({"config": {"feature": "design_response_framework"}})
    assert state["status"] == "found"

    backup = await svc.backup_state({"config": {"name": "snap1"}})
    assert backup["status"] == "backed_up"
    restore = await svc.restore_state({"config": {"name": "snap1"}})
    assert restore["status"] == "restored"

    assert (await svc.call("list_methods"))["status"] == "ok"
    assert (await svc.call("get_stats"))["status"] == "ok"
    assert (await svc.call("design_response_framework"))["status"] == "configured"
