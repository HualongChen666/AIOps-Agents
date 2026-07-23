'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useTenantStore } from '@/store/tenant';

export default function TenantPage() {
  const { tenants, currentTenant, addTenant, updateTenant, removeTenant, setCurrentTenant } = useTenantStore();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showBillingDialog, setShowBillingDialog] = useState(false);
  const [newTenant, setNewTenant] = useState({
    name: '',
    plan: 'basic' as 'free' | 'basic' | 'pro' | 'enterprise',
  });

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return 'bg-purple-100 text-purple-800';
      case 'pro':
        return 'bg-blue-100 text-blue-800';
      case 'basic':
        return 'bg-green-100 text-green-800';
      case 'free':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'suspended':
        return 'bg-yellow-100 text-yellow-800';
      case 'expired':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleCreateTenant = () => {
    const tenant = {
      id: `tenant-${String(tenants.length + 1).padStart(3, '0')}`,
      name: newTenant.name,
      plan: newTenant.plan,
      status: 'active' as const,
      quota: {
        maxUsers: newTenant.plan === 'enterprise' ? 100 : newTenant.plan === 'pro' ? 50 : newTenant.plan === 'basic' ? 10 : 5,
        maxServices: newTenant.plan === 'enterprise' ? 50 : newTenant.plan === 'pro' ? 25 : newTenant.plan === 'basic' ? 5 : 2,
        maxAlerts: newTenant.plan === 'enterprise' ? 10000 : newTenant.plan === 'pro' ? 5000 : newTenant.plan === 'basic' ? 1000 : 100,
        maxStorage: newTenant.plan === 'enterprise' ? 1000 : newTenant.plan === 'pro' ? 500 : newTenant.plan === 'basic' ? 100 : 10,
      },
      usage: {
        users: 0,
        services: 0,
        alerts: 0,
        storage: 0,
      },
      billing: {
        cycle: 'monthly' as const,
        amount: newTenant.plan === 'enterprise' ? 5000 : newTenant.plan === 'pro' ? 2000 : newTenant.plan === 'basic' ? 500 : 0,
        currency: 'CNY',
        nextBillingDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      },
    };
    addTenant(tenant);
    setShowCreateDialog(false);
    setNewTenant({ name: '', plan: 'basic' });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">租户管理</h1>
        <Button onClick={() => setShowCreateDialog(true)}>创建租户</Button>
      </div>

      {/* 当前租户概览 */}
      {currentTenant && (
        <Card>
          <CardHeader>
            <CardTitle>当前租户: {currentTenant.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">套餐</p>
                <Badge className={getPlanColor(currentTenant.plan)}>{currentTenant.plan}</Badge>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">状态</p>
                <Badge className={getStatusColor(currentTenant.status)}>
                  {currentTenant.status === 'active' ? '活跃' : currentTenant.status === 'suspended' ? '暂停' : '过期'}
                </Badge>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">月度费用</p>
                <p className="text-2xl font-bold">¥{currentTenant.billing.amount}</p>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">下次账单日期</p>
                <p className="text-lg font-medium">{currentTenant.billing.nextBillingDate}</p>
              </div>
            </div>

            {/* 资源配额 */}
            <h3 className="text-lg font-semibold mb-4">资源配额</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">用户数</span>
                  <span className="text-sm text-gray-600">{currentTenant.usage.users} / {currentTenant.quota.maxUsers}</span>
                </div>
                <Progress value={(currentTenant.usage.users / currentTenant.quota.maxUsers) * 100} />
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">服务数</span>
                  <span className="text-sm text-gray-600">{currentTenant.usage.services} / {currentTenant.quota.maxServices}</span>
                </div>
                <Progress value={(currentTenant.usage.services / currentTenant.quota.maxServices) * 100} />
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">告警数</span>
                  <span className="text-sm text-gray-600">{currentTenant.usage.alerts} / {currentTenant.quota.maxAlerts}</span>
                </div>
                <Progress value={(currentTenant.usage.alerts / currentTenant.quota.maxAlerts) * 100} />
              </div>
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">存储空间 (GB)</span>
                  <span className="text-sm text-gray-600">{currentTenant.usage.storage} / {currentTenant.quota.maxStorage}</span>
                </div>
                <Progress value={(currentTenant.usage.storage / currentTenant.quota.maxStorage) * 100} />
              </div>
            </div>

            <div className="mt-6 flex gap-2">
              <Button onClick={() => setShowBillingDialog(true)}>查看账单</Button>
              <Button variant="outline">升级套餐</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 租户列表 */}
      <Card>
        <CardHeader>
          <CardTitle>所有租户</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>名称</TableHead>
                <TableHead>套餐</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>用户数</TableHead>
                <TableHead>服务数</TableHead>
                <TableHead>月度费用</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tenants.map((tenant) => (
                <TableRow key={tenant.id}>
                  <TableCell className="font-mono text-sm">{tenant.id}</TableCell>
                  <TableCell className="font-medium">{tenant.name}</TableCell>
                  <TableCell>
                    <Badge className={getPlanColor(tenant.plan)}>{tenant.plan}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(tenant.status)}>
                      {tenant.status === 'active' ? '活跃' : tenant.status === 'suspended' ? '暂停' : '过期'}
                    </Badge>
                  </TableCell>
                  <TableCell>{tenant.usage.users} / {tenant.quota.maxUsers}</TableCell>
                  <TableCell>{tenant.usage.services} / {tenant.quota.maxServices}</TableCell>
                  <TableCell>¥{tenant.billing.amount}</TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentTenant(tenant)}
                      >
                        切换
                      </Button>
                      <Button variant="outline" size="sm">
                        编辑
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 创建租户弹窗 */}
      {showCreateDialog && (
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>创建新租户</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">租户名称</label>
                <Input
                  value={newTenant.name}
                  onChange={(e) => setNewTenant({ ...newTenant, name: e.target.value })}
                  placeholder="例如：Production"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">套餐</label>
                <Select
                  value={newTenant.plan}
                  onChange={(e) => setNewTenant({ ...newTenant, plan: e.target.value as any })}
                >
                  <option value="free">免费版</option>
                  <option value="basic">基础版 (¥500/月)</option>
                  <option value="pro">专业版 (¥2000/月)</option>
                  <option value="enterprise">企业版 (¥5000/月)</option>
                </Select>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium mb-2">套餐配额</p>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>• 用户数: {newTenant.plan === 'enterprise' ? 100 : newTenant.plan === 'pro' ? 50 : newTenant.plan === 'basic' ? 10 : 5}</p>
                  <p>• 服务数: {newTenant.plan === 'enterprise' ? 50 : newTenant.plan === 'pro' ? 25 : newTenant.plan === 'basic' ? 5 : 2}</p>
                  <p>• 告警数: {newTenant.plan === 'enterprise' ? 10000 : newTenant.plan === 'pro' ? 5000 : newTenant.plan === 'basic' ? 1000 : 100}</p>
                  <p>• 存储: {newTenant.plan === 'enterprise' ? 1000 : newTenant.plan === 'pro' ? 500 : newTenant.plan === 'basic' ? 100 : 10} GB</p>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowCreateDialog(false)}>
                取消
              </Button>
              <Button onClick={handleCreateTenant}>创建</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* 账单弹窗 */}
      {showBillingDialog && currentTenant && (
        <Dialog open={showBillingDialog} onOpenChange={setShowBillingDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>账单详情 - {currentTenant.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-500">套餐</span>
                  <Badge className={getPlanColor(currentTenant.plan)}>{currentTenant.plan}</Badge>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-500">计费周期</span>
                  <span className="text-sm font-medium">{currentTenant.billing.cycle === 'monthly' ? '月度' : '年度'}</span>
                </div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-gray-500">费用</span>
                  <span className="text-lg font-bold">¥{currentTenant.billing.amount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">下次账单日期</span>
                  <span className="text-sm font-medium">{currentTenant.billing.nextBillingDate}</span>
                </div>
              </div>
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm font-medium mb-2">账单明细</p>
                <div className="text-sm text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>基础服务费</span>
                    <span>¥{currentTenant.billing.amount}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>额外存储费用</span>
                    <span>¥0</span>
                  </div>
                  <div className="flex justify-between">
                    <span>额外告警费用</span>
                    <span>¥0</span>
                  </div>
                  <div className="border-t border-gray-300 pt-2 mt-2 flex justify-between font-medium">
                    <span>总计</span>
                    <span>¥{currentTenant.billing.amount}</span>
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setShowBillingDialog(false)}>
                关闭
              </Button>
              <Button>下载账单</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
