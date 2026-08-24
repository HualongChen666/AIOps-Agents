'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface WorkflowStatus {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'idle' | 'running' | 'paused' | 'error' | 'completed';
  currentStep: string;
  totalSteps: number;
  completedSteps: number;
  lastExecution: string;
  successRate: number;
  avgDuration: number;
  errorMessage?: string;
}

interface StatusSummary {
  total: number;
  running: number;
  idle: number;
  error: number;
  completed: number;
}

export default function WorkflowStatusPage() {
  const [statuses, setStatuses] = useState<WorkflowStatus[]>([]);
  const [summary, setSummary] = useState<StatusSummary>({
    total: 0,
    running: 0,
    idle: 0,
    error: 0,
    completed: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatuses = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<{ statuses: WorkflowStatus[]; summary: StatusSummary }>('/api/v1/workflow-status');
      setStatuses(response.data?.statuses || []);
      setSummary(response.data?.summary || summary);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载状态失败');
      console.error('加载状态失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatuses();
    const interval = setInterval(loadStatuses, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      idle: 'secondary',
      running: 'default',
      paused: 'outline',
      error: 'destructive',
      completed: 'default',
    };
    const labels: Record<string, string> = {
      idle: '空闲',
      running: '运行中',
      paused: '已暂停',
      error: '错误',
      completed: '已完成',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      idle: 'bg-gray-500',
      running: 'bg-blue-500',
      paused: 'bg-yellow-500',
      error: 'bg-red-500',
      completed: 'bg-green-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">工作流状态</h1>
        <p className="text-gray-600 mt-1">实时监控所有工作流的运行状态</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总工作流</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">{summary.running}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">空闲</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-gray-600">{summary.idle}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">错误</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{summary.error}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{summary.completed}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>工作流状态详情</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : statuses.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无工作流状态</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>工作流</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>当前步骤</TableHead>
                  <TableHead>进度</TableHead>
                  <TableHead>成功率</TableHead>
                  <TableHead>平均耗时</TableHead>
                  <TableHead>最后执行</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statuses.map((status) => (
                  <TableRow key={status.id}>
                    <TableCell className="font-medium">{status.workflowName}</TableCell>
                    <TableCell>{getStatusBadge(status.status)}</TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {status.currentStep} / {status.totalSteps}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className={`${getStatusColor(status.status)} h-2 rounded-full transition-all`}
                            style={{ width: `${(status.completedSteps / status.totalSteps) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-600">
                          {Math.round((status.completedSteps / status.totalSteps) * 100)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={status.successRate >= 90 ? 'text-green-600' : status.successRate >= 70 ? 'text-yellow-600' : 'text-red-600'}>
                        {status.successRate}%
                      </span>
                    </TableCell>
                    <TableCell className="text-gray-600">{status.avgDuration}s</TableCell>
                    <TableCell className="text-gray-600">
                      {new Date(status.lastExecution).toLocaleString('zh-CN')}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {statuses.some(s => s.status === 'error') && (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">错误工作流</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>工作流</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {statuses.filter(s => s.status === 'error').map((status) => (
                  <TableRow key={status.id}>
                    <TableCell className="font-medium">{status.workflowName}</TableCell>
                    <TableCell className="text-red-600 text-sm">{status.errorMessage || '未知错误'}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.location.href = `/workflow/workflow-execution`}
                      >
                        查看详情
                      </Button>
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
