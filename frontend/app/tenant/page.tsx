'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useTenantStore, type Tenant } from '@/store/tenant';

const API_BASE = '/api/v1/tenants';

export default function TenantPage() {
  const { tenants, currentTenant, addTenant, updateTenant, removeTenant, setCurrentTenant, setTenants } = useTenantStore();
  const [loading, setLoading] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showBillingDialog, setShowBillingDialog] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [newTenant, setNewTenant] = useState({
    name: '',
    contact: '',
    plan: 'basic' as 'free' | 'basic' | 'pro' | 'enterprise',
  });
  const [editForm, setEditForm] = useState({
    name: '',
    contact: '',
    plan: 'basic' as 'free' | 'basic' | 'pro' | 'enterprise',
    status: 'active' as 'active' | 'suspended' | 'expired',
  });

  const loadTenants = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/`);
      if (!res.ok) throw new Error('Failed to load tenants');
      const data: Tenant[] = await res.json();
      setTenants(data);
      if (data.length > 0) {
        setCurrentTenant(data[0]);
      }
    } catch (err) {
      console.error('load tenants error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

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

  const planPreview = (plan: string) => ({
    maxUsers: plan === 'enterprise' ? 100 : plan === 'pro' ? 50 : plan === 'basic' ? 10 : 5,
    maxServices: plan === 'enterprise' ? 50 : plan === 'pro' ? 25 : plan === 'basic' ? 5 : 2,
    maxAlerts: plan === 'enterprise' ? 10000 : plan === 'pro' ? 5000 : plan === 'basic' ? 1000 : 100,
    maxStorage: plan === 'enterprise' ? 1000 : plan === 'pro' ? 500 : plan === 'basic' ? 100 : 10,
    amount: plan === 'enterprise' ? 5000 : plan === 'pro' ? 2000 : plan === 'basic' ? 500 : 0,
  });

  const handleCreateTenant = async () => {
    if (!newTenant.name.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newTenant.name,
          contact: newTenant.contact,
          plan: newTenant.plan,
          status: 'active',
        }),
      });
      if (!res.ok) throw new Error('Create tenant failed');
      const data = await res.json();
      addTenant(data as Tenant);
      setShowCreateDialog(false);
      setNewTenant({ name: '', contact: '', plan: 'basic' });
    } catch (err) {
      console.error('create tenant error', err);
    }
  };

  const openEditDialog = (tenant: Tenant) => {
    setEditingTenant(tenant);
    setEditForm({
      name: tenant.name,
      contact: tenant.contact || '',
      plan: tenant.plan,
      status: tenant.status,
    });
  };

  const handleUpdateTenant = async () => {
    if (!editingTenant) return;
    try {
      const res = await fetch(`${API_BASE}/${editingTenant.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      });
      if (!res.ok) throw new Error('Update tenant failed');
      const data = await res.json();
      updateTenant(data.id, data as Partial<Tenant>);
      setEditingTenant(null);
    } catch (err) {
      console.error('update tenant error', err);
    }
  };

  const handleDeleteTenant = async (id: string) => {
    if (!confirm('确认删除该租户？')) return;
    try {
      const res = await fetch(`${API_BASE}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete tenant failed');
      removeTenant(id);
    } catch (err) {
      console.error('delete tenant error', err);
    }
  };

  const handleUpgradePlan = async () => {
    if (!currentTenant) return;
    const plan = window.prompt('选择新套餐 (free/basic/pro/enterprise):', currentTenant.plan);
    if (!plan || !['free', 'basic', 'pro', 'enterprise'].includes(plan)) return;
    try {
      const res = await fetch(`${API_BASE}/${currentTenant.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan }),
      });
      if (!res.ok) throw new Error('Upgrade failed');
      const data: Tenant = await res.json();
      updateTenant(data.id, data);
    } catch (err) {
      console.error('upgrade plan error', err);
    }
  };

  const preview = currentTenant ? planPreview(currentTenant.plan) : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">租户管理</h1>
        <Button onClick={() => setShowCreateDialog(true)}>创建租户</Button>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中...</p>}

      {/* 当前租户概览 */}
      {currentTenant && preview && (
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
              <Button variant="outline" onClick={handleUpgradePlan}>升级套餐</Button>
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
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(tenant)}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteTenant(tenant.id)}
                      >
                        删除
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
                <label className="block text-sm font-medium text-gray-700 mb-1">联系人</label>
                <Input
                  value={newTenant.contact}
                  onChange={(e) => setNewTenant({ ...newTenant, contact: e.target.value })}
                  placeholder="例如：admin@example.com"
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
                  <p>• 用户数: {planPreview(newTenant.plan).maxUsers}</p>
                  <p>• 服务数: {planPreview(newTenant.plan).maxServices}</p>
                  <p>• 告警数: {planPreview(newTenant.plan).maxAlerts}</p>
                  <p>• 存储: {planPreview(newTenant.plan).maxStorage} GB</p>
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

      {/* 编辑租户弹窗 */}
      {editingTenant && (
        <Dialog open={!!editingTenant} onOpenChange={() => setEditingTenant(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>编辑租户 - {editingTenant.name}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">租户名称</label>
                <Input
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">联系人</label>
                <Input
                  value={editForm.contact}
                  onChange={(e) => setEditForm({ ...editForm, contact: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">套餐</label>
                <Select
                  value={editForm.plan}
                  onChange={(e) => setEditForm({ ...editForm, plan: e.target.value as any })}
                >
                  <option value="free">免费版</option>
                  <option value="basic">基础版</option>
                  <option value="pro">专业版</option>
                  <option value="enterprise">企业版</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                <Select
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value as any })}
                >
                  <option value="active">活跃</option>
                  <option value="suspended">暂停</option>
                  <option value="expired">过期</option>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="secondary" onClick={() => setEditingTenant(null)}>
                取消
              </Button>
              <Button onClick={handleUpdateTenant}>保存</Button>
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
