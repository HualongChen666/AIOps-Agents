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

interface ChangeRequest {
  id: string;
  title: string;
  description: string;
  type: 'routine' | 'emergency' | 'standard';
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'draft' | 'pending' | 'approved' | 'rejected' | 'in_progress' | 'completed' | 'rolled_back';
  requester: string;
  approver?: string;
  scheduledStart?: string;
  scheduledEnd?: string;
  actualStart?: string;
  actualEnd?: string;
  riskLevel: 'low' | 'medium' | 'high';
  rollbackPlan: string;
  createdAt: string;
  updatedAt: string;
}

export default function ChangeManagementPage() {
  const [changes, setChanges] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingChange, setEditingChange] = useState<ChangeRequest | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    type: 'standard' as const,
    priority: 'medium' as const,
    scheduledStart: '',
    scheduledEnd: '',
    riskLevel: 'medium' as const,
    rollbackPlan: '',
  });

  const loadChanges = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<ChangeRequest[]>('/api/v1/change-management');
      setChanges(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载变更请求失败');
      console.error('加载变更请求失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChanges();
  }, []);

  const handleCreate = () => {
    setEditingChange(null);
    setFormData({
      title: '',
      description: '',
      type: 'standard',
      priority: 'medium',
      scheduledStart: '',
      scheduledEnd: '',
      riskLevel: 'medium',
      rollbackPlan: '',
    });
    setDialogOpen(true);
  };

  const handleEdit = (change: ChangeRequest) => {
    setEditingChange(change);
    setFormData({
      title: change.title,
      description: change.description,
      type: change.type,
      priority: change.priority,
      scheduledStart: change.scheduledStart || '',
      scheduledEnd: change.scheduledEnd || '',
      riskLevel: change.riskLevel,
      rollbackPlan: change.rollbackPlan,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingChange) {
        await api.put(`/api/v1/change-management/${editingChange.id}`, formData);
      } else {
        await api.post('/api/v1/change-management', formData);
      }
      setDialogOpen(false);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个变更请求吗？')) return;
    try {
      await api.delete(`/api/v1/change-management/${id}`);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleSubmit = async (id: string) => {
    try {
      await api.post(`/api/v1/change-management/${id}/submit`);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '提交失败');
      console.error('提交失败:', err);
    }
  };

  const handleStart = async (id: string) => {
    try {
      await api.post(`/api/v1/change-management/${id}/start`);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '启动失败');
      console.error('启动失败:', err);
    }
  };

  const handleComplete = async (id: string) => {
    try {
      await api.post(`/api/v1/change-management/${id}/complete`);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '完成失败');
      console.error('完成失败:', err);
    }
  };

  const handleRollback = async (id: string) => {
    if (!window.confirm('确定要回滚这个变更吗？')) return;
    try {
      await api.post(`/api/v1/change-management/${id}/rollback`);
      await loadChanges();
    } catch (err: any) {
      setError(err.response?.data?.message || '回滚失败');
      console.error('回滚失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      draft: 'secondary',
      pending: 'outline',
      approved: 'default',
      rejected: 'destructive',
      in_progress: 'default',
      completed: 'default',
      rolled_back: 'destructive',
    };
    const labels: Record<string, string> = {
      draft: '草稿',
      pending: '待审批',
      approved: '已批准',
      rejected: '已拒绝',
      in_progress: '进行中',
      completed: '已完成',
      rolled_back: '已回滚',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getTypeBadge = (type: string) => {
    const variants: Record<string, any> = {
      routine: 'secondary',
      emergency: 'destructive',
      standard: 'default',
    };
    const labels: Record<string, string> = {
      routine: '常规',
      emergency: '紧急',
      standard: '标准',
    };
    return <Badge variant={variants[type] || 'outline'}>{labels[type] || type}</Badge>;
  };

  const getPriorityBadge = (priority: string) => {
    const variants: Record<string, any> = {
      low: 'secondary',
      medium: 'outline',
      high: 'default',
      critical: 'destructive',
    };
    const labels: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '紧急',
    };
    return <Badge variant={variants[priority] || 'outline'}>{labels[priority] || priority}</Badge>;
  };

  const filteredChanges = changes.filter(change => {
    return filterStatus === 'all' || change.status === filterStatus;
  });

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">变更管理</h1>
          <p className="text-gray-600 mt-1">管理和跟踪系统变更请求</p>
        </div>
        <div className="flex gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="all">全部状态</option>
            <option value="draft">草稿</option>
            <option value="pending">待审批</option>
            <option value="approved">已批准</option>
            <option value="in_progress">进行中</option>
            <option value="completed">已完成</option>
          </select>
          <Button onClick={handleCreate}>创建变更</Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>变更请求列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredChanges.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无变更请求</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>标题</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>风险等级</TableHead>
                  <TableHead>请求人</TableHead>
                  <TableHead>计划开始</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredChanges.map((change) => (
                  <TableRow key={change.id}>
                    <TableCell className="font-mono text-sm">{change.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{change.title}</TableCell>
                    <TableCell>{getTypeBadge(change.type)}</TableCell>
                    <TableCell>{getPriorityBadge(change.priority)}</TableCell>
                    <TableCell>{getStatusBadge(change.status)}</TableCell>
                    <TableCell>
                      <Badge variant={change.riskLevel === 'high' ? 'destructive' : 'outline'}>
                        {change.riskLevel === 'low' ? '低' : change.riskLevel === 'medium' ? '中' : '高'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">{change.requester}</TableCell>
                    <TableCell className="text-gray-600">
                      {change.scheduledStart ? new Date(change.scheduledStart).toLocaleString('zh-CN') : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(change)}
                        >
                          编辑
                        </Button>
                        {change.status === 'draft' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSubmit(change.id)}
                          >
                            提交
                          </Button>
                        )}
                        {change.status === 'approved' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleStart(change.id)}
                          >
                            启动
                          </Button>
                        )}
                        {change.status === 'in_progress' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleComplete(change.id)}
                          >
                            完成
                          </Button>
                        )}
                        {(change.status === 'in_progress' || change.status === 'completed') && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleRollback(change.id)}
                          >
                            回滚
                          </Button>
                        )}
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(change.id)}
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
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>{editingChange ? '编辑变更' : '创建变更'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">标题</label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="输入变更标题"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入变更描述"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">类型</label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="routine">常规</option>
                  <option value="standard">标准</option>
                  <option value="emergency">紧急</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">优先级</label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: e.target.value as any })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                  <option value="critical">紧急</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">计划开始时间</label>
                <Input
                  type="datetime-local"
                  value={formData.scheduledStart}
                  onChange={(e) => setFormData({ ...formData, scheduledStart: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">计划结束时间</label>
                <Input
                  type="datetime-local"
                  value={formData.scheduledEnd}
                  onChange={(e) => setFormData({ ...formData, scheduledEnd: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">风险等级</label>
              <select
                value={formData.riskLevel}
                onChange={(e) => setFormData({ ...formData, riskLevel: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">回滚计划</label>
              <Textarea
                value={formData.rollbackPlan}
                onChange={(e) => setFormData({ ...formData, rollbackPlan: e.target.value })}
                placeholder="输入回滚计划"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.title}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
