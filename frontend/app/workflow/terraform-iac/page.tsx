'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface TerraformState {
  id: string;
  resourceId: string;
  resourceType: string;
  resourceName: string;
  status: 'created' | 'updated' | 'deleted' | 'planned';
  lastModified: string;
}

interface TerraformStack {
  id: string;
  name: string;
  description: string;
  workspace: string;
  provider: string;
  region: string;
  statePath: string;
  status: 'idle' | 'planning' | 'applying' | 'destroying' | 'error';
  lastPlan?: string;
  lastApply?: string;
  resourcesCount: number;
  createdAt: string;
}

interface TerraformExecution {
  id: string;
  stackId: string;
  stackName: string;
  type: 'plan' | 'apply' | 'destroy';
  status: 'running' | 'success' | 'failed' | 'cancelled';
  startedAt: string;
  completedAt?: string;
  duration?: number;
  changesAdd: number;
  changesChange: number;
  changesDestroy: number;
  output?: string;
}

export default function TerraformIaCPage() {
  const [stacks, setStacks] = useState<TerraformStack[]>([]);
  const [executions, setExecutions] = useState<TerraformExecution[]>([]);
  const [selectedStack, setSelectedStack] = useState<TerraformStack | null>(null);
  const [states, setStates] = useState<TerraformState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [planDialogOpen, setPlanDialogOpen] = useState(false);
  const [editingStack, setEditingStack] = useState<TerraformStack | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    workspace: 'default',
    provider: 'aws',
    region: 'us-east-1',
    statePath: '',
  });

  const loadStacks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<TerraformStack[]>('/api/v1/terraform-iac/stacks');
      setStacks(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedStack(response.data[0]);
        loadStates(response.data[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载Stack失败');
      console.error('加载Stack失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      const response = await api.get<TerraformExecution[]>('/api/v1/terraform-iac/executions');
      setExecutions(response.data || []);
    } catch (err: any) {
      console.error('加载执行记录失败:', err);
    }
  };

  const loadStates = async (stackId: string) => {
    try {
      const response = await api.get<TerraformState[]>(`/api/v1/terraform-iac/stacks/${stackId}/state`);
      setStates(response.data || []);
    } catch (err: any) {
      console.error('加载状态失败:', err);
    }
  };

  useEffect(() => {
    loadStacks();
    loadExecutions();
    const interval = setInterval(() => {
      const hasRunning = stacks.some(s => ['planning', 'applying', 'destroying'].includes(s.status));
      if (hasRunning) {
        loadStacks();
        loadExecutions();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingStack(null);
    setFormData({
      name: '',
      description: '',
      workspace: 'default',
      provider: 'aws',
      region: 'us-east-1',
      statePath: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (stack: TerraformStack) => {
    setEditingStack(stack);
    setFormData({
      name: stack.name,
      description: stack.description,
      workspace: stack.workspace,
      provider: stack.provider,
      region: stack.region,
      statePath: stack.statePath,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingStack) {
        await api.put(`/api/v1/terraform-iac/stacks/${editingStack.id}`, formData);
      } else {
        await api.post('/api/v1/terraform-iac/stacks', formData);
      }
      setDialogOpen(false);
      await loadStacks();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个Stack吗？')) return;
    try {
      await api.delete(`/api/v1/terraform-iac/stacks/${id}`);
      if (selectedStack?.id === id) {
        setSelectedStack(null);
        setStates([]);
      }
      await loadStacks();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handlePlan = (stack: TerraformStack) => {
    setSelectedStack(stack);
    setPlanDialogOpen(true);
  };

  const handleExecutePlan = async () => {
    if (!selectedStack) return;
    try {
      await api.post(`/api/v1/terraform-iac/stacks/${selectedStack.id}/plan`);
      setPlanDialogOpen(false);
      await loadStacks();
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Plan失败');
      console.error('Plan失败:', err);
    }
  };

  const handleApply = async (id: string) => {
    if (!window.confirm('确定要应用变更吗？')) return;
    try {
      await api.post(`/api/v1/terraform-iac/stacks/${id}/apply`);
      await loadStacks();
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Apply失败');
      console.error('Apply失败:', err);
    }
  };

  const handleDestroy = async (id: string) => {
    if (!window.confirm('确定要销毁所有资源吗？此操作不可逆！')) return;
    try {
      await api.post(`/api/v1/terraform-iac/stacks/${id}/destroy`);
      await loadStacks();
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Destroy失败');
      console.error('Destroy失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      idle: 'secondary',
      planning: 'default',
      applying: 'default',
      destroying: 'destructive',
      error: 'destructive',
      planned: 'outline',
      running: 'default',
      success: 'default',
      failed: 'destructive',
      cancelled: 'outline',
    };
    const labels: Record<string, string> = {
      idle: '空闲',
      planning: '规划中',
      applying: '应用中',
      destroying: '销毁中',
      error: '错误',
      planned: '已规划',
      running: '运行中',
      success: '成功',
      failed: '失败',
      cancelled: '已取消',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Terraform IaC</h1>
          <p className="text-gray-600 mt-1">基础设施即代码管理和部署</p>
        </div>
        <Button onClick={handleCreate}>创建Stack</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Stack列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : stacks.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无Stack</div>
            ) : (
              <div className="space-y-2">
                {stacks.map((stack) => (
                  <div
                    key={stack.id}
                    onClick={() => {
                      setSelectedStack(stack);
                      loadStates(stack.id);
                    }}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedStack?.id === stack.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{stack.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusBadge(stack.status)}
                      <Badge variant="outline" className="text-xs">{stack.provider}</Badge>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {stack.region} · {stack.resourcesCount} 资源
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(stack); }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handlePlan(stack); }}
                        disabled={stack.status !== 'idle'}
                      >
                        Plan
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(stack.id); }}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedStack ? selectedStack.name : '选择Stack'}
              </CardTitle>
              {selectedStack && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => handleApply(selectedStack.id)}
                    disabled={selectedStack.status !== 'idle' && selectedStack.status !== 'planned'}
                  >
                    Apply
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => handleDestroy(selectedStack.id)}
                    disabled={selectedStack.status !== 'idle'}
                  >
                    Destroy
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedStack ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedStack.description}
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Workspace</span>
                    <div>{selectedStack.workspace}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Provider</span>
                    <div>{selectedStack.provider}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Region</span>
                    <div>{selectedStack.region}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">状态</span>
                    <div>{getStatusBadge(selectedStack.status)}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">资源数量</span>
                    <div>{selectedStack.resourcesCount}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">State路径</span>
                    <div className="font-mono text-sm">{selectedStack.statePath}</div>
                  </div>
                  {selectedStack.lastPlan && (
                    <div>
                      <span className="text-gray-500">最后Plan</span>
                      <div className="text-gray-600">
                        {new Date(selectedStack.lastPlan).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  )}
                  {selectedStack.lastApply && (
                    <div>
                      <span className="text-gray-500">最后Apply</span>
                      <div className="text-gray-600">
                        {new Date(selectedStack.lastApply).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-medium mb-2">资源状态</h3>
                  {states.length === 0 ? (
                    <div className="text-center py-4 text-gray-500">暂无资源</div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>资源类型</TableHead>
                          <TableHead>资源名称</TableHead>
                          <TableHead>状态</TableHead>
                          <TableHead>最后修改</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {states.map((state) => (
                          <TableRow key={state.id}>
                            <TableCell className="font-mono text-sm">{state.resourceType}</TableCell>
                            <TableCell className="font-medium">{state.resourceName}</TableCell>
                            <TableCell>{getStatusBadge(state.status)}</TableCell>
                            <TableCell className="text-gray-600">
                              {new Date(state.lastModified).toLocaleString('zh-CN')}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                请从左侧选择一个Stack
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>执行记录</CardTitle>
        </CardHeader>
        <CardContent>
          {executions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无执行记录</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Stack</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>变更</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>耗时</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.map((exec) => (
                  <TableRow key={exec.id}>
                    <TableCell className="font-mono text-sm">{exec.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{exec.stackName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{exec.type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{getStatusBadge(exec.status)}</TableCell>
                    <TableCell className="text-gray-600">
                      +{exec.changesAdd} ~{exec.changesChange} -{exec.changesDestroy}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(exec.startedAt).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {exec.duration ? `${exec.duration}s` : '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingStack ? '编辑Stack' : '创建Stack'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入Stack名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入Stack描述"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Workspace</label>
              <Input
                value={formData.workspace}
                onChange={(e) => setFormData({ ...formData, workspace: e.target.value })}
                placeholder="default"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Provider</label>
              <select
                value={formData.provider}
                onChange={(e) => setFormData({ ...formData, provider: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="aws">AWS</option>
                <option value="azure">Azure</option>
                <option value="gcp">GCP</option>
                <option value="alicloud">AliCloud</option>
                <option value="vsphere">vSphere</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Region</label>
              <Input
                value={formData.region}
                onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                placeholder="us-east-1"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">State路径</label>
              <Input
                value={formData.statePath}
                onChange={(e) => setFormData({ ...formData, statePath: e.target.value })}
                placeholder="/path/to/terraform.tfstate"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={planDialogOpen} onOpenChange={setPlanDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>执行Plan</DialogTitle>
          </DialogHeader>
          {selectedStack && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Stack</h3>
                <p className="font-medium">{selectedStack.name}</p>
              </div>
              <div className="text-sm text-gray-600">
                这将生成一个执行计划，显示将要进行的变更。不会实际修改基础设施。
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPlanDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleExecutePlan}>
              执行Plan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
