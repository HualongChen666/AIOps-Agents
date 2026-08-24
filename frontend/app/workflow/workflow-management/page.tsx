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

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'draft';
  version: string;
  createdAt: string;
  updatedAt: string;
  steps: number;
}

export default function WorkflowManagementPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    status: 'draft' as const,
  });

  const loadWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Workflow[]>('/api/v1/workflow-management');
      setWorkflows(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载工作流失败');
      console.error('加载工作流失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  const handleCreate = () => {
    setEditingWorkflow(null);
    setFormData({ name: '', description: '', status: 'draft' });
    setDialogOpen(true);
  };

  const handleEdit = (workflow: Workflow) => {
    setEditingWorkflow(workflow);
    setFormData({
      name: workflow.name,
      description: workflow.description,
      status: workflow.status,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingWorkflow) {
        await api.put(`/api/v1/workflow-management/${editingWorkflow.id}`, formData);
      } else {
        await api.post('/api/v1/workflow-management', formData);
      }
      setDialogOpen(false);
      await loadWorkflows();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个工作流吗？')) return;
    try {
      await api.delete(`/api/v1/workflow-management/${id}`);
      await loadWorkflows();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleStatusChange = async (id: string, status: 'active' | 'inactive') => {
    try {
      await api.patch(`/api/v1/workflow-management/${id}/status`, { status });
      await loadWorkflows();
    } catch (err: any) {
      setError(err.response?.data?.message || '状态更新失败');
      console.error('状态更新失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      active: 'default',
      inactive: 'secondary',
      draft: 'outline',
    };
    const labels: Record<string, string> = {
      active: '活跃',
      inactive: '停用',
      draft: '草稿',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">工作流管理</h1>
          <p className="text-gray-600 mt-1">管理和配置所有工作流定义</p>
        </div>
        <Button onClick={handleCreate}>创建工作流</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>工作流列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : workflows.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无工作流</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>步骤数</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workflows.map((workflow) => (
                  <TableRow key={workflow.id}>
                    <TableCell className="font-medium">{workflow.name}</TableCell>
                    <TableCell className="text-gray-600 max-w-xs truncate">
                      {workflow.description}
                    </TableCell>
                    <TableCell>{getStatusBadge(workflow.status)}</TableCell>
                    <TableCell>{workflow.version}</TableCell>
                    <TableCell>{workflow.steps}</TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(workflow.createdAt).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(workflow)}
                        >
                          编辑
                        </Button>
                        {workflow.status === 'active' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleStatusChange(workflow.id, 'inactive')}
                          >
                            停用
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleStatusChange(workflow.id, 'active')}
                          >
                            启用
                          </Button>
                        )}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(workflow.id)}
                        >
                          删除
                        </Button>
                      </div>
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
            <DialogTitle>{editingWorkflow ? '编辑工作流' : '创建工作流'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入工作流名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入工作流描述"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">状态</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="draft">草稿</option>
                <option value="active">活跃</option>
                <option value="inactive">停用</option>
              </select>
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
    </main>
  );
}
