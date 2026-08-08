'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface Tenant {
  id: string;
  name: string;
  status: 'active' | 'suspended' | 'pending';
  users: number;
  resources: {
    cpu: number;
    memory: number;
    storage: number;
  };
  quota: {
    cpu: number;
    memory: number;
    storage: number;
  };
  billing: {
    plan: string;
    monthlyCost: number;
  };
}

interface ResourceUsage {
  tenantId: string;
  resource: string;
  used: number;
  total: number;
}

const mapStatus = (status: string): Tenant['status'] => {
  if (status === 'suspended' || status === 'expired') return 'suspended';
  if (status === 'pending') return 'pending';
  return 'active';
};

const mapBackendTenant = (t: any): Tenant => ({
  id: t.id,
  name: t.name,
  status: mapStatus(t.status),
  users: t.usage?.users ?? 0,
  resources: {
    cpu: t.usage?.cpu ?? 0,
    memory: t.usage?.memory ?? 0,
    storage: t.usage?.storage ?? t.usage?.disk ?? 0,
  },
  quota: {
    cpu: t.quota?.cpu ?? 0,
    memory: t.quota?.memory ?? 0,
    storage: t.quota?.maxStorage ?? t.quota?.disk ?? 0,
  },
  billing: {
    plan: t.plan,
    monthlyCost: t.billing?.amount ?? 0,
  },
});

export default function MultiTenantPage() {
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadTenants = async () => {
      setLoading(true);
      try {
        const { data } = await api.get('/api/v1/tenants/');
        if (cancelled) return;
        const mapped = Array.isArray(data) ? data.map(mapBackendTenant) : [];
        setTenants(mapped);
      } catch (err) {
        // api interceptor already shows a toast on error
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadTenants();
    return () => { cancelled = true; };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'suspended':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getUsagePercentage = (used: number, total: number) => {
    if (total === 0) return 0;
    return Math.round((used / total) * 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const loadTenants = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/api/v1/tenants/');
      const mapped = Array.isArray(data) ? data.map(mapBackendTenant) : [];
      setTenants(mapped);
      if (selectedTenant) {
        const refreshed = mapped.find((t) => t.id === selectedTenant.id);
        if (refreshed) setSelectedTenant(refreshed);
      }
    } catch (err) {
      // api interceptor already shows a toast on error
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTenant = async () => {
    const name = window.prompt('租户名称：');
    if (!name) return;
    const plan = window.prompt('套餐 (free/basic/pro/enterprise)：', 'basic');
    if (!plan || !['free', 'basic', 'pro', 'enterprise'].includes(plan)) return;
    const contact = window.prompt('联系人：', '') || '';
    try {
      await api.post('/api/v1/tenants/', {
        name,
        plan,
        contact,
        status: 'active',
      });
      await loadTenants();
    } catch (err) {
      window.alert('创建租户失败');
    }
  };

  const handleToggleSuspend = async (tenant: Tenant) => {
    const newStatus = tenant.status === 'suspended' ? 'active' : 'suspended';
    try {
      await api.put(`/api/v1/tenants/${tenant.id}`, { status: newStatus });
      await loadTenants();
    } catch (err) {
      window.alert('状态更新失败');
    }
  };

  const handleAdjustQuota = async (tenant: Tenant) => {
    const cpu = window.prompt('CPU 配额：', String(tenant.quota.cpu || 0));
    if (cpu === null) return;
    const memory = window.prompt('内存 配额：', String(tenant.quota.memory || 0));
    if (memory === null) return;
    const storage = window.prompt('存储 配额 (GB)：', String(tenant.quota.storage || 0));
    if (storage === null) return;
    try {
      await api.put(`/api/v1/tenants/${tenant.id}`, {
        quota: {
          cpu: Number(cpu) || 0,
          memory: Number(memory) || 0,
          maxStorage: Number(storage) || 0,
        },
      });
      await loadTenants();
    } catch (err) {
      window.alert('配额调整失败');
    }
  };

  const handleRefreshBilling = async (tenant: Tenant) => {
    try {
      const { data } = await api.get(`/api/v1/tenants/${tenant.id}`);
      const mapped = mapBackendTenant(data);
      setSelectedTenant(mapped);
    } catch (err) {
      window.alert('刷新账单失败');
    }
  };

  const handleSwitchTenant = (tenant: Tenant) => {
    setSelectedTenant(tenant);
  };

  const totalCpu = tenants.reduce((sum, t) => sum + t.quota.cpu, 0);
  const usedCpu = tenants.reduce((sum, t) => sum + t.resources.cpu, 0);
  const totalMemory = tenants.reduce((sum, t) => sum + t.quota.memory, 0);
  const usedMemory = tenants.reduce((sum, t) => sum + t.resources.memory, 0);
  const totalStorage = tenants.reduce((sum, t) => sum + t.quota.storage, 0);
  const usedStorage = tenants.reduce((sum, t) => sum + t.resources.storage, 0);

  const cpuPct = getUsagePercentage(usedCpu, totalCpu);
  const memoryPct = getUsagePercentage(usedMemory, totalMemory);
  const storagePct = getUsagePercentage(usedStorage, totalStorage);

  const selectedUsages: ResourceUsage[] = selectedTenant
    ? [
      { tenantId: selectedTenant.id, resource: 'CPU', used: selectedTenant.resources.cpu, total: selectedTenant.quota.cpu },
      { tenantId: selectedTenant.id, resource: 'Memory', used: selectedTenant.resources.memory, total: selectedTenant.quota.memory },
      { tenantId: selectedTenant.id, resource: 'Storage', used: selectedTenant.resources.storage, total: selectedTenant.quota.storage },
    ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">多租户管理</h1>
        <Button onClick={handleCreateTenant}>创建租户</Button>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中...</p>}

      {/* 租户概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tenants.map((tenant) => (
          <Card
            key={tenant.id}
            className={`cursor-pointer transition hover:shadow-md ${selectedTenant?.id === tenant.id ? 'border-blue-500 ring-2 ring-blue-200' : ''
              }`}
            onClick={() => setSelectedTenant(tenant)}
          >
            <CardHeader>
              <div className="flex items-center justify-between mb-2">
                <CardTitle className="text-lg">{tenant.name}</CardTitle>
                <Badge className={getStatusColor(tenant.status)}>
                  {tenant.status === 'active' ? '活跃' : tenant.status === 'suspended' ? '暂停' : '待激活'}
                </Badge>
              </div>
              <p className="text-sm text-gray-500">ID: {tenant.id}</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">用户数</span>
                  <span className="font-medium">{tenant.users}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">套餐</span>
                  <span className="font-medium">{tenant.billing.plan}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">月费用</span>
                  <span className="font-medium">${tenant.billing.monthlyCost}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 租户详情 */}
      {selectedTenant && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{selectedTenant.name} - 详细信息</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  编辑
                </Button>
                <Button variant="outline" size="sm">
                  切换到此租户
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {/* 资源配额 */}
              <div>
                <h4 className="font-medium mb-4">资源配额使用情况</h4>
                <div className="space-y-4">
                  {selectedUsages.map((usage) => {
                    const percentage = getUsagePercentage(usage.used, usage.total);
                    return (
                      <div key={`${usage.tenantId}-${usage.resource}`}>
                        <div className="flex justify-between text-sm mb-1">
                          <span>{usage.resource}</span>
                          <span>
                            {usage.used} / {usage.total} ({percentage}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${getUsageColor(percentage)}`}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 计费信息 */}
              <div>
                <h4 className="font-medium mb-4">计费信息</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500">当前套餐</p>
                    <p className="font-medium">{selectedTenant.billing.plan}</p>
                  </div>
                  <div className="p-4 border border-gray-200 rounded-lg">
                    <p className="text-sm text-gray-500">月费用</p>
                    <p className="font-medium">${selectedTenant.billing.monthlyCost}</p>
                  </div>
                </div>
              </div>

              {/* 操作 */}
              <div className="flex gap-2 pt-4 border-t">
                <Button variant="outline" size="sm" onClick={() => selectedTenant && handleAdjustQuota(selectedTenant)}>
                  调整配额
                </Button>
                <Button variant="outline" size="sm" onClick={() => selectedTenant && handleRefreshBilling(selectedTenant)}>
                  查看账单
                </Button>
                <Button variant="outline" size="sm" className="text-red-600" onClick={() => selectedTenant && handleToggleSuspend(selectedTenant)}>
                  {selectedTenant?.status === 'suspended' ? '激活租户' : '暂停租户'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 全局资源概览 */}
      <Card>
        <CardHeader>
          <CardTitle>全局资源概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500">总CPU</p>
              <p className="text-2xl font-bold">{usedCpu} / {totalCpu}</p>
              <p className="text-xs text-gray-400">{cpuPct}% 使用</p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500">总内存</p>
              <p className="text-2xl font-bold">{usedMemory} / {totalMemory}</p>
              <p className="text-xs text-gray-400">{memoryPct}% 使用</p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500">总存储</p>
              <p className="text-2xl font-bold">{usedStorage} / {totalStorage}</p>
              <p className="text-xs text-gray-400">{storagePct}% 使用</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 租户切换 */}
      <Card>
        <CardHeader>
          <CardTitle>租户切换</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {tenants.map((tenant) => (
              <div
                key={tenant.id}
                className="p-4 border border-gray-200 rounded-lg flex items-center justify-between hover:bg-gray-50 cursor-pointer"
              >
                <div>
                  <h4 className="font-medium">{tenant.name}</h4>
                  <p className="text-sm text-gray-500">{tenant.id}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleSwitchTenant(tenant)}>
                  切换
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
