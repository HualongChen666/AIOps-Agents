'use client'

import { useState } from 'react';
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

export default function MultiTenantPage() {
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [tenants, setTenants] = useState<Tenant[]>([
    {
      id: 'T-001',
      name: 'Production',
      status: 'active',
      users: 150,
      resources: { cpu: 80, memory: 64, storage: 500 },
      quota: { cpu: 100, memory: 128, storage: 1000 },
      billing: { plan: 'Enterprise', monthlyCost: 5000 },
    },
    {
      id: 'T-002',
      name: 'Staging',
      status: 'active',
      users: 45,
      resources: { cpu: 30, memory: 24, storage: 200 },
      quota: { cpu: 50, memory: 64, storage: 500 },
      billing: { plan: 'Professional', monthlyCost: 2000 },
    },
    {
      id: 'T-003',
      name: 'Development',
      status: 'active',
      users: 20,
      resources: { cpu: 15, memory: 16, storage: 100 },
      quota: { cpu: 20, memory: 32, storage: 200 },
      billing: { plan: 'Standard', monthlyCost: 500 },
    },
  ]);

  const [resourceUsage, setResourceUsage] = useState<ResourceUsage[]>([
    { tenantId: 'T-001', resource: 'CPU', used: 80, total: 100 },
    { tenantId: 'T-001', resource: 'Memory', used: 64, total: 128 },
    { tenantId: 'T-001', resource: 'Storage', used: 500, total: 1000 },
    { tenantId: 'T-002', resource: 'CPU', used: 30, total: 50 },
    { tenantId: 'T-002', resource: 'Memory', used: 24, total: 64 },
    { tenantId: 'T-002', resource: 'Storage', used: 200, total: 500 },
  ]);

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
    return Math.round((used / total) * 100);
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">多租户管理</h1>
        <Button onClick={() => setShowCreateModal(true)}>创建租户</Button>
      </div>

      {/* 租户概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {tenants.map((tenant) => (
          <Card
            key={tenant.id}
            className={`cursor-pointer transition hover:shadow-md ${
              selectedTenant?.id === tenant.id ? 'border-blue-500 ring-2 ring-blue-200' : ''
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
                  {resourceUsage
                    .filter((ru) => ru.tenantId === selectedTenant.id)
                    .map((usage) => {
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
                <Button variant="outline" size="sm">
                  调整配额
                </Button>
                <Button variant="outline" size="sm">
                  查看账单
                </Button>
                <Button variant="outline" size="sm" className="text-red-600">
                  暂停租户
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
              <p className="text-2xl font-bold">170 / 170</p>
              <p className="text-xs text-gray-400">100% 使用</p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500">总内存</p>
              <p className="text-2xl font-bold">104 / 224</p>
              <p className="text-xs text-gray-400">46% 使用</p>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-sm text-gray-500">总存储</p>
              <p className="text-2xl font-bold">800 / 1700</p>
              <p className="text-xs text-gray-400">47% 使用</p>
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
                <Button variant="outline" size="sm">
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
