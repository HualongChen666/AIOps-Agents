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

interface ScheduledTask {
  id: string;
  name: string;
  description: string;
  workflowId: string;
  workflowName: string;
  schedule: string;
  timezone: string;
  enabled: boolean;
  lastRun?: string;
  nextRun: string;
  runCount: number;
  successCount: number;
  failureCount: number;
  createdAt: string;
}

interface SchedulerStats {
  totalTasks: number;
  enabledTasks: number;
  disabledTasks: number;
  totalRuns: number;
  successRate: number;
}

export default function TaskSchedulerPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [stats, setStats] = useState<SchedulerStats>({
    totalTasks: 0,
    enabledTasks: 0,
    disabledTasks: 0,
    totalRuns: 0,
    successRate: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    workflowId: '',
    schedule: '',
    timezone: 'Asia/Shanghai',
  });

  const loadTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<{ tasks: ScheduledTask[]; stats: SchedulerStats }>('/api/v1/task-scheduler');
      setTasks(response.data?.tasks || []);
      setStats(response.data?.stats || stats);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载调度任务失败');
      console.error('加载调度任务失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCreate = () => {
    setEditingTask(null);
    setFormData({
      name: '',
      description: '',
      workflowId: '',
      schedule: '',
      timezone: 'Asia/Shanghai',
    });
    setDialogOpen(true);
  };

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task);
    setFormData({
      name: task.name,
      description: task.description,
      workflowId: task.workflowId,
      schedule: task.schedule,
      timezone: task.timezone,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingTask) {
        await api.put(`/api/v1/task-scheduler/${editingTask.id}`, formData);
      } else {
        await api.post('/api/v1/task-scheduler', formData);
      }
      setDialogOpen(false);
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个调度任务吗？')) return;
    try {
      await api.delete(`/api/v1/task-scheduler/${id}`);
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/task-scheduler/${id}/toggle`, { enabled });
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '切换状态失败');
      console.error('切换状态失败:', err);
    }
  };

  const handleRunNow = async (id: string) => {
    try {
      await api.post(`/api/v1/task-scheduler/${id}/run-now`);
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '立即执行失败');
      console.error('立即执行失败:', err);
    }
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">任务调度器</h1>
          <p className="text-gray-600 mt-1">配置和管理定时任务调度</p>
        </div>
        <Button onClick={handleCreate}>创建调度任务</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总任务</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已启用</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.enabledTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已禁用</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-600">{stats.disabledTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总执行次数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.totalRuns}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">成功率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.successRate}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>调度任务列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无调度任务</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>任务名称</TableHead>
                  <TableHead>工作流</TableHead>
                  <TableHead>调度表达式</TableHead>
                  <TableHead>时区</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>下次运行</TableHead>
                  <TableHead>执行统计</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="font-medium">{task.name}</TableCell>
                    <TableCell className="text-gray-600">{task.workflowName}</TableCell>
                    <TableCell className="font-mono text-sm">{task.schedule}</TableCell>
                    <TableCell className="text-gray-600">{task.timezone}</TableCell>
                    <TableCell>
                      <Badge variant={task.enabled ? 'default' : 'secondary'}>
                        {task.enabled ? '已启用' : '已禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(task.nextRun).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>总计: {task.runCount}</div>
                        <div className="text-green-600">成功: {task.successCount}</div>
                        <div className="text-red-600">失败: {task.failureCount}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(task)}
                        >
                          编辑
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggle(task.id, !task.enabled)}
                        >
                          {task.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRunNow(task.id)}
                        >
                          立即执行
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(task.id)}
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
            <DialogTitle>{editingTask ? '编辑调度任务' : '创建调度任务'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">任务名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入任务名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入任务描述"
                rows={2}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">工作流ID</label>
              <Input
                value={formData.workflowId}
                onChange={(e) => setFormData({ ...formData, workflowId: e.target.value })}
                placeholder="输入工作流ID"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Cron表达式</label>
              <Input
                value={formData.schedule}
                onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                placeholder="0 0 * * *"
              />
              <p className="text-xs text-gray-500 mt-1">例如: 0 0 * * * (每天午夜), */5 * * * * (每5分钟)</p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">时区</label>
              <select
                value={formData.timezone}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="Asia/Shanghai">Asia/Shanghai</option>
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name || !formData.schedule}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
