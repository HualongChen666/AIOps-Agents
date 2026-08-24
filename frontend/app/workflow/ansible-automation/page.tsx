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

interface AnsiblePlaybook {
  id: string;
  name: string;
  description: string;
  playbookPath: string;
  inventoryPath: string;
  vaultEnabled: boolean;
  status: 'idle' | 'running' | 'success' | 'failed';
  lastRun?: string;
  lastRunStatus?: 'success' | 'failed';
  runCount: number;
  successCount: number;
  failureCount: number;
  createdAt: string;
}

interface AnsibleExecution {
  id: string;
  playbookId: string;
  playbookName: string;
  status: 'running' | 'success' | 'failed' | 'cancelled';
  startedAt: string;
  completedAt?: string;
  duration?: number;
  targetHosts: string;
  tasksTotal: number;
  tasksCompleted: number;
  tasksFailed: number;
  output?: string;
}

export default function AnsibleAutomationPage() {
  const [playbooks, setPlaybooks] = useState<AnsiblePlaybook[]>([]);
  const [executions, setExecutions] = useState<AnsibleExecution[]>([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState<AnsiblePlaybook | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [editingPlaybook, setEditingPlaybook] = useState<AnsiblePlaybook | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    playbookPath: '',
    inventoryPath: '',
    vaultEnabled: false,
  });
  const [runForm, setRunForm] = useState({
    targetHosts: '',
    extraVars: '',
  });

  const loadPlaybooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<AnsiblePlaybook[]>('/api/v1/ansible-automation/playbooks');
      setPlaybooks(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedPlaybook(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载Playbook失败');
      console.error('加载Playbook失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      const response = await api.get<AnsibleExecution[]>('/api/v1/ansible-automation/executions');
      setExecutions(response.data || []);
    } catch (err: any) {
      console.error('加载执行记录失败:', err);
    }
  };

  useEffect(() => {
    loadPlaybooks();
    loadExecutions();
    const interval = setInterval(() => {
      const hasRunning = executions.some(e => e.status === 'running');
      if (hasRunning) {
        loadExecutions();
        loadPlaybooks();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingPlaybook(null);
    setFormData({
      name: '',
      description: '',
      playbookPath: '',
      inventoryPath: '',
      vaultEnabled: false,
    });
    setDialogOpen(true);
  };

  const handleEdit = (playbook: AnsiblePlaybook) => {
    setEditingPlaybook(playbook);
    setFormData({
      name: playbook.name,
      description: playbook.description,
      playbookPath: playbook.playbookPath,
      inventoryPath: playbook.inventoryPath,
      vaultEnabled: playbook.vaultEnabled,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingPlaybook) {
        await api.put(`/api/v1/ansible-automation/playbooks/${editingPlaybook.id}`, formData);
      } else {
        await api.post('/api/v1/ansible-automation/playbooks', formData);
      }
      setDialogOpen(false);
      await loadPlaybooks();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个Playbook吗？')) return;
    try {
      await api.delete(`/api/v1/ansible-automation/playbooks/${id}`);
      if (selectedPlaybook?.id === id) {
        setSelectedPlaybook(null);
      }
      await loadPlaybooks();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleRun = (playbook: AnsiblePlaybook) => {
    setSelectedPlaybook(playbook);
    setRunForm({
      targetHosts: '',
      extraVars: '',
    });
    setRunDialogOpen(true);
  };

  const handleExecute = async () => {
    if (!selectedPlaybook) return;
    try {
      await api.post(`/api/v1/ansible-automation/playbooks/${selectedPlaybook.id}/run`, runForm);
      setRunDialogOpen(false);
      await loadPlaybooks();
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || '执行失败');
      console.error('执行失败:', err);
    }
  };

  const handleCancelExecution = async (executionId: string) => {
    try {
      await api.post(`/api/v1/ansible-automation/executions/${executionId}/cancel`);
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || '取消失败');
      console.error('取消失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      idle: 'secondary',
      running: 'default',
      success: 'default',
      failed: 'destructive',
      cancelled: 'outline',
    };
    const labels: Record<string, string> = {
      idle: '空闲',
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
          <h1 className="text-3xl font-bold text-gray-900">Ansible自动化</h1>
          <p className="text-gray-600 mt-1">管理和执行Ansible Playbook自动化任务</p>
        </div>
        <Button onClick={handleCreate}>添加Playbook</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Playbook列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : playbooks.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无Playbook</div>
            ) : (
              <div className="space-y-2">
                {playbooks.map((playbook) => (
                  <div
                    key={playbook.id}
                    onClick={() => setSelectedPlaybook(playbook)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedPlaybook?.id === playbook.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{playbook.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusBadge(playbook.status)}
                      {playbook.vaultEnabled && (
                        <Badge variant="outline" className="text-xs">Vault</Badge>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      运行: {playbook.runCount} · 成功: {playbook.successCount}
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(playbook); }}
                      >
                        编辑
                      </Button>
                      <Button
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleRun(playbook); }}
                        disabled={playbook.status === 'running'}
                      >
                        运行
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(playbook.id); }}
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
            <CardTitle>
              {selectedPlaybook ? selectedPlaybook.name : '选择Playbook'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedPlaybook ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedPlaybook.description}
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Playbook路径</span>
                    <div className="font-mono">{selectedPlaybook.playbookPath}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Inventory路径</span>
                    <div className="font-mono">{selectedPlaybook.inventoryPath}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">状态</span>
                    <div>{getStatusBadge(selectedPlaybook.status)}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Vault加密</span>
                    <div>
                      <Badge variant={selectedPlaybook.vaultEnabled ? 'default' : 'secondary'}>
                        {selectedPlaybook.vaultEnabled ? '已启用' : '未启用'}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-500">运行次数</span>
                    <div>{selectedPlaybook.runCount}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">成功率</span>
                    <div>
                      {selectedPlaybook.runCount > 0 
                        ? `${Math.round((selectedPlaybook.successCount / selectedPlaybook.runCount) * 100)}%`
                        : '-'}
                    </div>
                  </div>
                  {selectedPlaybook.lastRun && (
                    <div>
                      <span className="text-gray-500">最后运行</span>
                      <div className="text-gray-600">
                        {new Date(selectedPlaybook.lastRun).toLocaleString('zh-CN')}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">
                请从左侧选择一个Playbook
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
                  <TableHead>Playbook</TableHead>
                  <TableHead>目标主机</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>任务进度</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.map((exec) => (
                  <TableRow key={exec.id}>
                    <TableCell className="font-mono text-sm">{exec.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{exec.playbookName}</TableCell>
                    <TableCell className="text-gray-600">{exec.targetHosts}</TableCell>
                    <TableCell>{getStatusBadge(exec.status)}</TableCell>
                    <TableCell className="text-gray-600">
                      {exec.tasksCompleted}/{exec.tasksTotal}
                      {exec.tasksFailed > 0 && (
                        <span className="text-red-600 ml-2">({exec.tasksFailed} 失败)</span>
                      )}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(exec.startedAt).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {exec.duration ? `${exec.duration}s` : '-'}
                    </TableCell>
                    <TableCell>
                      {exec.status === 'running' && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleCancelExecution(exec.id)}
                        >
                          取消
                        </Button>
                      )}
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
            <DialogTitle>{editingPlaybook ? '编辑Playbook' : '添加Playbook'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入Playbook名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入Playbook描述"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Playbook路径</label>
              <Input
                value={formData.playbookPath}
                onChange={(e) => setFormData({ ...formData, playbookPath: e.target.value })}
                placeholder="/path/to/playbook.yml"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Inventory路径</label>
              <Input
                value={formData.inventoryPath}
                onChange={(e) => setFormData({ ...formData, inventoryPath: e.target.value })}
                placeholder="/path/to/inventory"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.vaultEnabled}
                onChange={(e) => setFormData({ ...formData, vaultEnabled: e.target.checked })}
              />
              <span className="text-sm">启用Vault加密</span>
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.playbookPath}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>运行Playbook</DialogTitle>
          </DialogHeader>
          {selectedPlaybook && (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Playbook</h3>
                <p className="font-medium">{selectedPlaybook.name}</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">目标主机</label>
                <Input
                  value={runForm.targetHosts}
                  onChange={(e) => setRunForm({ ...runForm, targetHosts: e.target.value })}
                  placeholder="all 或特定主机"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">额外变量（JSON格式）</label>
                <Textarea
                  value={runForm.extraVars}
                  onChange={(e) => setRunForm({ ...runForm, extraVars: e.target.value })}
                  placeholder='{"key": "value"}'
                  rows={3}
                  className="font-mono text-sm"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRunDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleExecute}>
              执行
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
