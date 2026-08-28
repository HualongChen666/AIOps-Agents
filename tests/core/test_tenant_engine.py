# -*- coding: utf-8 -*-
"""
租户引擎测试文件
测试租户的CRUD操作、配额计算、计费计算、并发安全和数据持久化
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from core.tenant_engine import (
    Billing,
    Quota,
    Tenant,
    Usage,
    _compute_billing,
    _compute_quota,
    _dict_to_tenant,
    _load,
    _next_billing_date,
    _save,
    create_tenant,
    delete_tenant,
    get_tenant,
    list_tenants,
    update_tenant,
)


@pytest.fixture(scope="function")
def temp_data_file():
    """创建临时数据文件用于每个测试"""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="tenants_test_")
    os.close(fd)
    original_data_file = None
    try:
        from core import tenant_engine
        original_data_file = tenant_engine.DATA_FILE
        tenant_engine.DATA_FILE = Path(path)
        # 初始化空文件
        with open(path, "w") as f:
            json.dump([], f)
        tenant_engine._TENANTS = []
        yield path
    finally:
        if original_data_file:
            from core import tenant_engine
            tenant_engine.DATA_FILE = original_data_file
            tenant_engine._TENANTS = []
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass


@pytest.fixture(scope="function")
def reset_tenant_state():
    """重置租户引擎状态的fixture"""
    from core import tenant_engine

    original_data_file = tenant_engine.DATA_FILE
    original_tenants = tenant_engine._TENANTS.copy()
    
    # 创建临时文件
    fd, path = tempfile.mkstemp(suffix=".json", prefix="tenants_reset_")
    os.close(fd)
    
    try:
        with open(path, "w") as f:
            json.dump([], f)
        tenant_engine.DATA_FILE = Path(path)
        tenant_engine._TENANTS = []
        yield
    finally:
        tenant_engine.DATA_FILE = original_data_file
        tenant_engine._TENANTS = original_tenants
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass


class TestQuota:
    """测试Quota数据类"""

    def test_quota_creation_default(self):
        """测试使用默认值创建Quota"""
        quota = Quota()
        assert quota.cpu == 0.0
        assert quota.memory == 0.0
        assert quota.disk == 0.0
        assert quota.maxUsers == 0
        assert quota.maxServices == 0
        assert quota.maxAlerts == 0
        assert quota.maxStorage == 0

    def test_quota_creation_with_values(self):
        """测试使用指定值创建Quota"""
        quota = Quota(
            cpu=40.0,
            memory=80.0,
            disk=500.0,
            maxUsers=10,
            maxServices=5,
            maxAlerts=1000,
            maxStorage=100,
        )
        assert quota.cpu == 40.0
        assert quota.memory == 80.0
        assert quota.disk == 500.0
        assert quota.maxUsers == 10
        assert quota.maxServices == 5
        assert quota.maxAlerts == 1000
        assert quota.maxStorage == 100


class TestUsage:
    """测试Usage数据类"""

    def test_usage_creation_default(self):
        """测试使用默认值创建Usage"""
        usage = Usage()
        assert usage.cpu == 0.0
        assert usage.memory == 0.0
        assert usage.disk == 0.0
        assert usage.users == 0
        assert usage.services == 0
        assert usage.alerts == 0
        assert usage.storage == 0

    def test_usage_creation_with_values(self):
        """测试使用指定值创建Usage"""
        usage = Usage(
            cpu=20.0,
            memory=40.0,
            disk=200.0,
            users=5,
            services=3,
            alerts=500,
            storage=50,
        )
        assert usage.cpu == 20.0
        assert usage.memory == 40.0
        assert usage.disk == 200.0
        assert usage.users == 5
        assert usage.services == 3
        assert usage.alerts == 500
        assert usage.storage == 50


class TestBilling:
    """测试Billing数据类"""

    def test_billing_creation_default(self):
        """测试使用默认值创建Billing"""
        billing = Billing()
        assert billing.cycle == "monthly"
        assert billing.amount == 0.0
        assert billing.currency == "CNY"
        assert billing.nextBillingDate == ""

    def test_billing_creation_with_values(self):
        """测试使用指定值创建Billing"""
        billing = Billing(
            cycle="yearly", amount=6000.0, currency="USD", nextBillingDate="2026-12-31"
        )
        assert billing.cycle == "yearly"
        assert billing.amount == 6000.0
        assert billing.currency == "USD"
        assert billing.nextBillingDate == "2026-12-31"


class TestTenant:
    """测试Tenant数据类"""

    def test_tenant_creation_minimal(self):
        """测试使用最小参数创建Tenant"""
        tenant = Tenant(id="tenant-123", name="Test Tenant")
        assert tenant.id == "tenant-123"
        assert tenant.name == "Test Tenant"
        assert tenant.status == "active"
        assert tenant.contact == ""
        assert tenant.plan == "basic"
        assert isinstance(tenant.quota, Quota)
        assert isinstance(tenant.usage, Usage)
        assert isinstance(tenant.billing, Billing)
        assert tenant.created_at is not None

    def test_tenant_creation_full(self):
        """测试使用完整参数创建Tenant"""
        quota = Quota(cpu=40.0, memory=80.0, disk=500.0, maxUsers=10)
        usage = Usage(cpu=20.0, memory=40.0, disk=200.0, users=5)
        billing = Billing(amount=500.0, nextBillingDate="2026-12-31")
        tenant = Tenant(
            id="tenant-456",
            name="Full Tenant",
            status="active",
            contact="test@example.com",
            plan="pro",
            quota=quota,
            usage=usage,
            billing=billing,
            created_at="2026-01-01T00:00:00",
        )
        assert tenant.id == "tenant-456"
        assert tenant.name == "Full Tenant"
        assert tenant.status == "active"
        assert tenant.contact == "test@example.com"
        assert tenant.plan == "pro"
        assert tenant.quota.cpu == 40.0
        assert tenant.usage.cpu == 20.0
        assert tenant.billing.amount == 500.0
        assert tenant.created_at == "2026-01-01T00:00:00"


class TestComputeQuota:
    """测试配额计算函数"""

    def test_compute_quota_free_plan(self):
        """测试免费计划的配额计算"""
        quota = _compute_quota("free")
        assert quota.cpu == 20.0
        assert quota.memory == 40.0
        assert quota.disk == 100.0
        assert quota.maxUsers == 5
        assert quota.maxServices == 2
        assert quota.maxAlerts == 100
        assert quota.maxStorage == 10

    def test_compute_quota_basic_plan(self):
        """测试基础计划的配额计算"""
        quota = _compute_quota("basic")
        assert quota.cpu == 40.0
        assert quota.memory == 80.0
        assert quota.disk == 500.0
        assert quota.maxUsers == 10
        assert quota.maxServices == 5
        assert quota.maxAlerts == 1000
        assert quota.maxStorage == 100

    def test_compute_quota_pro_plan(self):
        """测试专业计划的配额计算"""
        quota = _compute_quota("pro")
        assert quota.cpu == 80.0
        assert quota.memory == 160.0
        assert quota.disk == 1000.0
        assert quota.maxUsers == 50
        assert quota.maxServices == 25
        assert quota.maxAlerts == 5000
        assert quota.maxStorage == 500

    def test_compute_quota_enterprise_plan(self):
        """测试企业计划的配额计算"""
        quota = _compute_quota("enterprise")
        assert quota.cpu == 200.0
        assert quota.memory == 400.0
        assert quota.disk == 5000.0
        assert quota.maxUsers == 100
        assert quota.maxServices == 50
        assert quota.maxAlerts == 10000
        assert quota.maxStorage == 1000

    def test_compute_quota_unknown_plan(self):
        """测试未知计划的配额计算（应回退到basic）"""
        quota = _compute_quota("unknown")
        assert quota.cpu == 40.0
        assert quota.memory == 80.0
        assert quota.disk == 500.0
        assert quota.maxUsers == 10
        assert quota.maxServices == 5
        assert quota.maxAlerts == 1000
        assert quota.maxStorage == 100


class TestComputeBilling:
    """测试计费计算函数"""

    def test_compute_billing_free_plan(self):
        """测试免费计划的计费计算"""
        billing = _compute_billing("free")
        assert billing.amount == 0
        assert billing.currency == "CNY"
        assert billing.cycle == "monthly"
        assert billing.nextBillingDate is not None
        # 验证nextBillingDate是有效的日期格式
        try:
            datetime.fromisoformat(billing.nextBillingDate)
        except ValueError:
            pytest.fail("nextBillingDate is not a valid ISO date")

    def test_compute_billing_basic_plan(self):
        """测试基础计划的计费计算"""
        billing = _compute_billing("basic")
        assert billing.amount == 500
        assert billing.currency == "CNY"
        assert billing.cycle == "monthly"
        assert billing.nextBillingDate is not None

    def test_compute_billing_pro_plan(self):
        """测试专业计划的计费计算"""
        billing = _compute_billing("pro")
        assert billing.amount == 2000
        assert billing.currency == "CNY"
        assert billing.cycle == "monthly"
        assert billing.nextBillingDate is not None

    def test_compute_billing_enterprise_plan(self):
        """测试企业计划的计费计算"""
        billing = _compute_billing("enterprise")
        assert billing.amount == 5000
        assert billing.currency == "CNY"
        assert billing.cycle == "monthly"
        assert billing.nextBillingDate is not None

    def test_compute_billing_unknown_plan(self):
        """测试未知计划的计费计算（应回退到basic）"""
        billing = _compute_billing("unknown")
        assert billing.amount == 500
        assert billing.currency == "CNY"
        assert billing.cycle == "monthly"
        assert billing.nextBillingDate is not None


class TestNextBillingDate:
    """测试下一个计费日期计算"""

    def test_next_billing_date_format(self):
        """测试下一个计费日期格式"""
        date_str = _next_billing_date()
        try:
            date = datetime.fromisoformat(date_str)
            assert isinstance(date, datetime)
        except ValueError:
            pytest.fail("next_billing_date returned invalid ISO format")

    def test_next_billing_date_future(self):
        """测试下一个计费日期是未来日期"""
        date_str = _next_billing_date()
        date = datetime.fromisoformat(date_str)
        now = datetime.utcnow()
        future_date = now + timedelta(days=29)
        assert date >= future_date


class TestDictToTenant:
    """测试字典转换为Tenant"""

    def test_dict_to_tenant_minimal(self):
        """测试最小字典转换为Tenant"""
        d = {"id": "tenant-123", "name": "Test Tenant"}
        tenant = _dict_to_tenant(d)
        assert tenant.id == "tenant-123"
        assert tenant.name == "Test Tenant"
        assert tenant.status == "active"
        assert tenant.contact == ""
        assert tenant.plan == "basic"

    def test_dict_to_tenant_full(self):
        """测试完整字典转换为Tenant"""
        d = {
            "id": "tenant-456",
            "name": "Full Tenant",
            "status": "active",
            "contact": "test@example.com",
            "plan": "pro",
            "quota": {"cpu": 80.0, "memory": 160.0, "disk": 1000.0},
            "usage": {"cpu": 40.0, "memory": 80.0, "disk": 500.0},
            "billing": {"amount": 2000.0, "currency": "CNY"},
            "created_at": "2026-01-01T00:00:00",
        }
        tenant = _dict_to_tenant(d)
        assert tenant.id == "tenant-456"
        assert tenant.name == "Full Tenant"
        assert tenant.status == "active"
        assert tenant.contact == "test@example.com"
        assert tenant.plan == "pro"
        assert tenant.quota.cpu == 80.0
        assert tenant.usage.cpu == 40.0
        assert tenant.billing.amount == 2000.0
        assert tenant.created_at == "2026-01-01T00:00:00"

    def test_dict_to_tenant_missing_fields(self):
        """测试缺失字段的字典转换为Tenant"""
        d = {"name": "Test"}
        tenant = _dict_to_tenant(d)
        assert tenant.name == "Test"
        assert tenant.id is not None  # 应该生成默认ID
        assert tenant.status == "active"
        assert tenant.plan == "basic"


class TestDataPersistence:
    """测试数据持久化"""

    def test_save_and_load_empty(self, temp_data_file):
        """测试保存和加载空租户列表"""
        from core import tenant_engine

        # 清空租户列表
        tenant_engine._TENANTS = []
        _save()

        # 重新加载
        _load()
        assert len(tenant_engine._TENANTS) == 0

    def test_save_and_load_with_tenants(self, temp_data_file):
        """测试保存和加载租户列表"""
        from core import tenant_engine

        # 创建测试租户
        tenant1 = Tenant(
            id="tenant-001", name="Tenant 1", plan="basic", status="active"
        )
        tenant2 = Tenant(
            id="tenant-002", name="Tenant 2", plan="pro", status="active"
        )
        tenant_engine._TENANTS = [tenant1, tenant2]
        _save()

        # 重新加载
        _load()
        assert len(tenant_engine._TENANTS) == 2
        assert tenant_engine._TENANTS[0].id == "tenant-001"
        assert tenant_engine._TENANTS[1].id == "tenant-002"

    def test_load_nonexistent_file(self, temp_data_file):
        """测试加载不存在的文件"""
        # 删除文件
        if os.path.exists(temp_data_file):
            os.remove(temp_data_file)

        from core import tenant_engine

        _load()
        assert len(tenant_engine._TENANTS) == 0

    def test_load_invalid_json(self, temp_data_file):
        """测试加载无效的JSON文件"""
        # 写入无效JSON
        with open(temp_data_file, "w") as f:
            f.write("invalid json content")

        from core import tenant_engine

        _load()
        assert len(tenant_engine._TENANTS) == 0

    def test_load_invalid_structure(self, temp_data_file):
        """测试加载无效结构的JSON文件"""
        # 写入非列表结构
        with open(temp_data_file, "w") as f:
            json.dump({"not": "a list"}, f)

        from core import tenant_engine

        _load()
        assert len(tenant_engine._TENANTS) == 0


class TestListTenants:
    """测试租户列表功能"""

    def test_list_tenants_empty(self, reset_tenant_state):
        """测试列出空租户列表"""
        tenants = list_tenants()
        assert isinstance(tenants, list)
        assert len(tenants) == 0

    def test_list_tenants_with_data(self, reset_tenant_state):
        """测试列出有数据的租户列表"""
        # 创建测试租户
        tenant1 = create_tenant(name="Tenant 1", plan="basic")
        tenant2 = create_tenant(name="Tenant 2", plan="pro")

        tenants = list_tenants()
        assert len(tenants) == 2
        assert tenants[0].id == tenant1.id
        assert tenants[1].id == tenant2.id

    def test_list_tenants_returns_copy(self, reset_tenant_state):
        """测试list_tenants返回副本而非引用"""
        # 创建测试租户
        tenant = create_tenant(name="Tenant 1", plan="basic")

        tenants = list_tenants()
        tenants.append(Tenant(id="tenant-002", name="Tenant 2", plan="pro"))

        # 原始列表不应被修改
        from core import tenant_engine
        assert len(tenant_engine._TENANTS) == 1
        assert tenant_engine._TENANTS[0].id == tenant.id


class TestGetTenant:
    """测试获取租户功能"""

    def test_get_tenant_exists(self, reset_tenant_state):
        """测试获取存在的租户"""
        # 创建测试租户
        tenant = create_tenant(name="Test Tenant", plan="basic")

        result = get_tenant(tenant.id)
        assert result is not None
        assert result.id == tenant.id
        assert result.name == "Test Tenant"

    def test_get_tenant_not_exists(self, reset_tenant_state):
        """测试获取不存在的租户"""
        # 创建测试租户
        tenant = create_tenant(name="Test Tenant", plan="basic")

        result = get_tenant("tenant-999")
        assert result is None

    def test_get_tenant_empty_list(self, reset_tenant_state):
        """测试在空列表中获取租户"""
        result = get_tenant("tenant-001")
        assert result is None


class TestCreateTenant:
    """测试创建租户功能"""

    def test_create_tenant_basic(self, reset_tenant_state):
        """测试创建基础租户"""
        tenant = create_tenant(name="Test Tenant")
        assert tenant is not None
        assert tenant.name == "Test Tenant"
        assert tenant.status == "active"
        assert tenant.plan == "basic"
        assert tenant.id.startswith("tenant-")
        assert isinstance(tenant.quota, Quota)
        assert isinstance(tenant.usage, Usage)
        assert isinstance(tenant.billing, Billing)

    def test_create_tenant_with_plan(self, reset_tenant_state):
        """测试创建指定计划的租户"""
        tenant = create_tenant(name="Pro Tenant", plan="pro")
        assert tenant.plan == "pro"
        assert tenant.quota.cpu == 80.0
        assert tenant.quota.maxUsers == 50
        assert tenant.billing.amount == 2000

    def test_create_tenant_with_status(self, reset_tenant_state):
        """测试创建指定状态的租户"""
        tenant = create_tenant(name="Inactive Tenant", status="inactive")
        assert tenant.status == "inactive"

    def test_create_tenant_with_contact(self, reset_tenant_state):
        """测试创建带联系信息的租户"""
        tenant = create_tenant(name="Contact Tenant", contact="test@example.com")
        assert tenant.contact == "test@example.com"

    def test_create_tenant_free_plan(self, reset_tenant_state):
        """测试创建免费计划租户"""
        tenant = create_tenant(name="Free Tenant", plan="free")
        assert tenant.plan == "free"
        assert tenant.quota.cpu == 20.0
        assert tenant.quota.maxUsers == 5
        assert tenant.billing.amount == 0

    def test_create_tenant_enterprise_plan(self, reset_tenant_state):
        """测试创建企业计划租户"""
        tenant = create_tenant(name="Enterprise Tenant", plan="enterprise")
        assert tenant.plan == "enterprise"
        assert tenant.quota.cpu == 200.0
        assert tenant.quota.maxUsers == 100
        assert tenant.billing.amount == 5000

    def test_create_tenant_persistence(self, reset_tenant_state):
        """测试创建租户后数据持久化"""
        from core import tenant_engine

        tenant = create_tenant(name="Persistent Tenant")
        assert tenant is not None

        # 验证数据已保存
        with open(tenant_engine.DATA_FILE, "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == tenant.id
        assert data[0]["name"] == "Persistent Tenant"


class TestUpdateTenant:
    """测试更新租户功能"""

    def test_update_tenant_name(self, reset_tenant_state):
        """测试更新租户名称"""
        # 创建测试租户
        tenant = create_tenant(name="Old Name", plan="basic")

        updated = update_tenant(tenant.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.id == tenant.id

    def test_update_tenant_status(self, reset_tenant_state):
        """测试更新租户状态"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic", status="active")

        updated = update_tenant(tenant.id, status="inactive")
        assert updated is not None
        assert updated.status == "inactive"

    def test_update_tenant_contact(self, reset_tenant_state):
        """测试更新租户联系信息"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic", contact="")

        updated = update_tenant(tenant.id, contact="new@example.com")
        assert updated is not None
        assert updated.contact == "new@example.com"

    def test_update_tenant_plan(self, reset_tenant_state):
        """测试更新租户计划"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        updated = update_tenant(tenant.id, plan="pro")
        assert updated is not None
        assert updated.plan == "pro"
        # 验证配额和计费已更新
        assert updated.quota.cpu == 80.0
        assert updated.billing.amount == 2000

    def test_update_tenant_quota(self, reset_tenant_state):
        """测试更新租户配额"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        updated = update_tenant(tenant.id, quota={"cpu": 50.0, "memory": 100.0})
        assert updated is not None
        assert updated.quota.cpu == 50.0
        assert updated.quota.memory == 100.0

    def test_update_tenant_usage(self, reset_tenant_state):
        """测试更新租户使用量"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        updated = update_tenant(tenant.id, usage={"cpu": 10.0, "users": 3})
        assert updated is not None
        assert updated.usage.cpu == 10.0
        assert updated.usage.users == 3

    def test_update_tenant_billing(self, reset_tenant_state):
        """测试更新租户计费信息"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        updated = update_tenant(tenant.id, billing={"amount": 600.0})
        assert updated is not None
        assert updated.billing.amount == 600.0

    def test_update_tenant_multiple_fields(self, reset_tenant_state):
        """测试同时更新多个字段"""
        # 创建测试租户
        tenant = create_tenant(name="Old", plan="basic", status="active")

        updated = update_tenant(
            tenant.id,
            name="New Name",
            status="inactive",
            contact="test@example.com",
        )
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.status == "inactive"
        assert updated.contact == "test@example.com"

    def test_update_tenant_not_exists(self, reset_tenant_state):
        """测试更新不存在的租户"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        updated = update_tenant("tenant-999", name="New Name")
        assert updated is None

    def test_update_tenant_plan_change_recomputes_quota_billing(self, reset_tenant_state):
        """测试计划变更时重新计算配额和计费"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 从basic升级到pro
        updated = update_tenant(tenant.id, plan="pro")
        assert updated.plan == "pro"
        assert updated.quota.cpu == 80.0
        assert updated.quota.maxUsers == 50
        assert updated.billing.amount == 2000

        # 从pro降级到free
        updated = update_tenant(tenant.id, plan="free")
        assert updated.plan == "free"
        assert updated.quota.cpu == 20.0
        assert updated.quota.maxUsers == 5
        assert updated.billing.amount == 0


class TestDeleteTenant:
    """测试删除租户功能"""

    def test_delete_tenant_exists(self, reset_tenant_state):
        """测试删除存在的租户"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        result = delete_tenant(tenant.id)
        assert result is True

    def test_delete_tenant_not_exists(self, reset_tenant_state):
        """测试删除不存在的租户"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        result = delete_tenant("tenant-999")
        assert result is False

    def test_delete_tenant_from_multiple(self, reset_tenant_state):
        """测试从多个租户中删除一个"""
        # 创建测试租户
        tenant1 = create_tenant(name="Test 1", plan="basic")
        tenant2 = create_tenant(name="Test 2", plan="pro")
        tenant3 = create_tenant(name="Test 3", plan="enterprise")

        result = delete_tenant(tenant2.id)
        assert result is True

        # 验证剩余租户
        tenants = list_tenants()
        assert len(tenants) == 2
        assert tenants[0].id == tenant1.id
        assert tenants[1].id == tenant3.id

    def test_delete_tenant_empty_list(self, reset_tenant_state):
        """测试从空列表中删除租户"""
        result = delete_tenant("tenant-001")
        assert result is False


class TestConcurrencySafety:
    """测试并发安全性"""

    def test_concurrent_create_tenants(self, reset_tenant_state):
        """测试并发创建租户"""
        from core import tenant_engine

        num_threads = 10
        threads = []
        created_tenants = []
        lock = threading.Lock()

        def create_tenant_thread(index):
            tenant = create_tenant(name=f"Concurrent Tenant {index}")
            with lock:
                created_tenants.append(tenant)

        for i in range(num_threads):
            thread = threading.Thread(target=create_tenant_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有租户都已创建
        assert len(created_tenants) == num_threads
        assert len(tenant_engine._TENANTS) == num_threads

        # 验证所有ID都是唯一的
        ids = [t.id for t in created_tenants]
        assert len(ids) == len(set(ids))

    def test_concurrent_read_tenants(self, reset_tenant_state):
        """测试并发读取租户"""
        # 创建测试租户
        for i in range(5):
            create_tenant(name=f"Tenant {i}", plan="basic")

        num_threads = 10
        threads = []
        read_results = []
        lock = threading.Lock()

        def read_tenants_thread():
            tenants = list_tenants()
            with lock:
                read_results.append(len(tenants))

        for _ in range(num_threads):
            thread = threading.Thread(target=read_tenants_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有读取都返回了正确的数量
        assert all(result == 5 for result in read_results)

    def test_concurrent_update_tenants(self, reset_tenant_state):
        """测试并发更新租户"""
        # 创建测试租户
        tenant = create_tenant(name="Original Name", plan="basic")

        num_threads = 10
        threads = []

        def update_tenant_thread(index):
            update_tenant(tenant.id, name=f"Updated Name {index}")

        for i in range(num_threads):
            thread = threading.Thread(target=update_tenant_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证租户仍然存在
        updated = get_tenant(tenant.id)
        assert updated is not None
        assert updated.id == tenant.id

    def test_concurrent_delete_tenants(self, reset_tenant_state):
        """测试并发删除租户"""
        # 创建多个测试租户
        tenant_ids = []
        for i in range(10):
            tenant = create_tenant(name=f"Tenant {i}", plan="basic")
            tenant_ids.append(tenant.id)

        num_threads = 5
        threads = []

        def delete_tenant_thread(index):
            delete_tenant(tenant_ids[index])

        for i in range(num_threads):
            thread = threading.Thread(target=delete_tenant_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证剩余租户数量
        from core import tenant_engine
        assert len(tenant_engine._TENANTS) == 5

    def test_concurrent_mixed_operations(self, reset_tenant_state):
        """测试并发混合操作"""
        # 创建初始租户
        tenant = create_tenant(name="Original", plan="basic")

        num_threads = 10
        threads = []

        def mixed_operations(index):
            if index % 3 == 0:
                create_tenant(name=f"New Tenant {index}")
            elif index % 3 == 1:
                update_tenant(tenant.id, name=f"Updated {index}")
            else:
                list_tenants()

        for i in range(num_threads):
            thread = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证操作没有导致错误
        from core import tenant_engine
        assert len(tenant_engine._TENANTS) >= 1


class TestErrorHandling:
    """测试错误处理"""

    def test_update_tenant_invalid_quota_field(self, reset_tenant_state):
        """测试更新租户时使用无效的配额字段"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 无效字段应该被忽略
        updated = update_tenant(tenant.id, quota={"invalid_field": 100})
        assert updated is not None
        # 原始配额应该保持不变
        assert updated.quota.cpu == 40.0

    def test_update_tenant_invalid_usage_field(self, reset_tenant_state):
        """测试更新租户时使用无效的使用量字段"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 无效字段应该被忽略
        updated = update_tenant(tenant.id, usage={"invalid_field": 100})
        assert updated is not None
        # 原始使用量应该保持不变
        assert updated.usage.cpu == 0.0

    def test_update_tenant_invalid_billing_field(self, reset_tenant_state):
        """测试更新租户时使用无效的计费字段"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 无效字段应该被忽略
        updated = update_tenant(tenant.id, billing={"invalid_field": 100})
        assert updated is not None
        # 原始计费应该保持不变
        assert updated.billing.amount == 500

    def test_update_tenant_non_dict_quota(self, reset_tenant_state):
        """测试更新租户时使用非字典类型的配额"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 非字典类型应该被忽略
        updated = update_tenant(tenant.id, quota="invalid")
        assert updated is not None
        # 原始配额应该保持不变
        assert updated.quota.cpu == 40.0

    def test_update_tenant_non_dict_usage(self, reset_tenant_state):
        """测试更新租户时使用非字典类型的使用量"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 非字典类型应该被忽略
        updated = update_tenant(tenant.id, usage=123)
        assert updated is not None
        # 原始使用量应该保持不变
        assert updated.usage.cpu == 0.0

    def test_update_tenant_non_dict_billing(self, reset_tenant_state):
        """测试更新租户时使用非字典类型的计费"""
        # 创建测试租户
        tenant = create_tenant(name="Test", plan="basic")

        # 非字典类型应该被忽略
        updated = update_tenant(tenant.id, billing=["invalid"])
        assert updated is not None
        # 原始计费应该保持不变
        assert updated.billing.amount == 500


class TestIntegrationScenarios:
    """测试集成场景"""

    def test_full_lifecycle(self, reset_tenant_state):
        """测试租户完整生命周期"""
        # 创建
        tenant = create_tenant(name="Lifecycle Tenant", plan="basic")
        assert tenant is not None
        tenant_id = tenant.id

        # 读取
        retrieved = get_tenant(tenant_id)
        assert retrieved is not None
        assert retrieved.name == "Lifecycle Tenant"

        # 更新
        updated = update_tenant(tenant_id, name="Updated Tenant", status="inactive")
        assert updated is not None
        assert updated.name == "Updated Tenant"
        assert updated.status == "inactive"

        # 删除
        deleted = delete_tenant(tenant_id)
        assert deleted is True

        # 验证删除
        retrieved_after_delete = get_tenant(tenant_id)
        assert retrieved_after_delete is None

    def test_plan_upgrade_lifecycle(self, reset_tenant_state):
        """测试计划升级生命周期"""
        # 创建免费计划租户
        tenant = create_tenant(name="Upgrade Tenant", plan="free")
        assert tenant.plan == "free"
        assert tenant.quota.cpu == 20.0
        assert tenant.billing.amount == 0

        # 升级到基础计划
        updated = update_tenant(tenant.id, plan="basic")
        assert updated.plan == "basic"
        assert updated.quota.cpu == 40.0
        assert updated.billing.amount == 500

        # 升级到专业计划
        updated = update_tenant(tenant.id, plan="pro")
        assert updated.plan == "pro"
        assert updated.quota.cpu == 80.0
        assert updated.billing.amount == 2000

        # 升级到企业计划
        updated = update_tenant(tenant.id, plan="enterprise")
        assert updated.plan == "enterprise"
        assert updated.quota.cpu == 200.0
        assert updated.billing.amount == 5000

    def test_usage_tracking_lifecycle(self, reset_tenant_state):
        """测试使用量跟踪生命周期"""
        # 创建租户
        tenant = create_tenant(name="Usage Tenant", plan="basic")
        assert tenant.usage.cpu == 0.0
        assert tenant.usage.users == 0

        # 更新使用量
        updated = update_tenant(
            tenant.id, usage={"cpu": 15.0, "memory": 30.0, "users": 3, "services": 2}
        )
        assert updated.usage.cpu == 15.0
        assert updated.usage.memory == 30.0
        assert updated.usage.users == 3
        assert updated.usage.services == 2

        # 进一步更新使用量
        updated = update_tenant(tenant.id, usage={"alerts": 500, "storage": 25})
        assert updated.usage.cpu == 15.0  # 之前的值应该保留
        assert updated.usage.alerts == 500
        assert updated.usage.storage == 25

    def test_multiple_tenants_management(self, reset_tenant_state):
        """测试多租户管理"""
        # 创建多个租户
        tenant1 = create_tenant(name="Tenant 1", plan="free")
        tenant2 = create_tenant(name="Tenant 2", plan="basic")
        tenant3 = create_tenant(name="Tenant 3", plan="pro")

        # 列出所有租户
        tenants = list_tenants()
        assert len(tenants) == 3

        # 获取特定租户
        retrieved = get_tenant(tenant2.id)
        assert retrieved is not None
        assert retrieved.name == "Tenant 2"

        # 更新特定租户
        updated = update_tenant(tenant1.id, status="inactive")
        assert updated.status == "inactive"

        # 删除特定租户
        deleted = delete_tenant(tenant3.id)
        assert deleted is True

        # 验证剩余租户
        tenants = list_tenants()
        assert len(tenants) == 2
