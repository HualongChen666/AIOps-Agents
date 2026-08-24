'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface ExecutorTask {
  id: string;
  name: string;
  type: 'sync' | 'async';
  status: 'pending' | 'running' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  workflowId: string;
  workflowName: string;
  startedAt: string;
  completedAt?: string;
  duration?: number;
  retryCount: number;
  maxRetries: number;
  error?: string;
}

interface ExecutorStats {
  totalTasks: number;
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
  avgDuration: number;
  successRate: number;
}

export default function ExecutorPage() {
  const [tasks, setTasks] = useState<ExecutorTask[]>([]);
  const [stats, setStats] = useState<ExecutorStats>({
    totalTasks: 0,
    runningTasks: 0,
    completedTasks: 0,
    failedTasks: 0,
    avgDuration: 0,
    successRate: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');

  const loadTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<{ tasks: ExecutorTask[]; stats: ExecutorStats }>('/api/v1/executor');
      setTasks(response.data?.tasks || []);
      setStats(response.data?.stats || stats);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载任务失败');
      console.error('加载任务失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
    const interval = setInterval(() => {
      const hasRunning = tasks.some(t => t.status === 'running');
      if (hasRunning) {
        loadTasks();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleRetry = async (taskId: string) => {
    try {
      await api.post(`/api/v1/executor/${taskId}/retry`);
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '重试失败');
      console.error('重试失败:', err);
    }
  };

  const handleCancel = async (taskId: string) => {
    if (!window.confirm('确定要取消这个任务吗？')) return;
    try {
      await api.post(`/api/v1/executor/${taskId}/cancel`);
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '取消失败');
      console.error('取消失败:', err);
    }
  };

  const handlePause = async () => {
    try {
      await api.post('/api/v1/executor/pause');
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '暂停失败');
      console.error('暂停失败:', err);
    }
  };

  const handleResume = async () => {
    try {
      await api.post('/api/v1/executor/resume');
      await loadTasks();
    } catch (err: any) {
      setError(err.response?.data?.message || '恢复失败');
      console.error('恢复失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      pending: 'secondary',
      running: 'default',
      completed: 'default',
      failed: 'destructive',
    };
    const labels: Record<string, string> = {
      pending: '待执行',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
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

  const filteredTasks = tasks.filter(task => {
    const matchesStatus = filterStatus === 'all' || task.status === filterStatus;
    const matchesPriority = filterPriority === 'all' || task.priority === filterPriority;
    return matchesStatus && matchesPriority;
  });

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">执行器</h1>
          <p className="text-gray-600 mt-1">管理工作流执行任务和调度</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePause}>暂停执行</Button>
          <Button variant="outline" onClick={handleResume}>恢复执行</Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
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
            <CardTitle className="text-sm font-medium text-gray-600">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{stats.runningTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.completedTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{stats.failedTasks}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">平均耗时</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{stats.avgDuration}s</div>
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
          <div className="flex items-center justify-between">
            <CardTitle>执行任务</CardTitle>
            <div className="flex gap-2">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="all">全部状态</option>
                <option value="pending">待执行</option>
                <option value="running">运行中</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
              </select>
              <select
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="all">全部优先级</option>
                <option value="low">低</option>
                <option value="medium">中</option>
                <option value="high">高</option>
                <option value="critical">紧急</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredTasks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无任务</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>任务ID</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>工作流</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>重试</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="font-mono text-sm">{task.id.slice(0, 8)}</TableCell>
                    <TableCell className="font-medium">{task.name}</TableCell>
                    <TableCell className="text-gray-600">{task.workflowName}</TableCell>
                    <TableCell>{getStatusBadge(task.status)}</TableCell>
                    <TableCell>{getPriorityBadge(task.priority)}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{task.type === 'sync' ? '同步' : '异步'}</Badge>
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {task.retryCount}/{task.maxRetries}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {task.duration ? `${task.duration}s` : '-'}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(task.startedAt).toLocaleString('zh-CN')}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {task.status === 'failed' && task.retryCount < task.maxRetries && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRetry(task.id)}
                          >
                            重试
                          </Button>
                        )}
                        {task.status === 'running' && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancel(task.id)}
                          >
                            取消
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {tasks.some(t => t.status === 'failed') && (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">失败任务</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>任务</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>重试次数</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.filter(t => t.status === 'failed').map((task) => (
                  <TableRow key={task.id}>
                    <TableCell className="font-medium">{task.name}</TableCell>
                    <TableCell className="text-red-600 text-sm max-w-md truncate">
                      {task.error || '未知错误'}
                    </TableCell>
                    <TableCell className="text-gray-600">
                      {task.retryCount}/{task.maxRetries}
                    </TableCell>
                    <TableCell>
                      {task.retryCount < task.maxRetries && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRetry(task.id)}
                        >
                          重试
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </main>
  );
}
