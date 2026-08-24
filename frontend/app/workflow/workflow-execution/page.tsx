'use client'

import React, { useEffect, useState, useRef } from 'react';
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

interface Execution {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: string;
  completedAt?: string;
  duration?: number;
  currentStep?: string;
  totalSteps: number;
  progress: number;
  inputParams: Record<string, any>;
  output?: Record<string, any>;
  error?: string;
}

export default function WorkflowExecutionPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  const loadExecutions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Execution[]>('/api/v1/workflow-execution');
      setExecutions(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.message || '加载执行记录失败');
      console.error('加载执行记录失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecflows();
    const interval = setInterval(() => {
      const hasRunning = executions.some(e => e.status === 'running');
      if (hasRunning) {
        loadExecutions();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleExecute = async (workflowId: string, params: Record<string, any> = {}) => {
    try {
      await api.post('/api/v1/workflow-execution', { workflowId, params });
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || '启动工作流失败');
      console.error('启动工作流失败:', err);
    }
  };

  const handleCancel = async (executionId: string) => {
    if (!window.confirm('确定要取消这个执行吗？')) return;
    try {
      await api.post(`/api/v1/workflow-execution/${executionId}/cancel`);
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || '取消执行失败');
      console.error('取消执行失败:', err);
    }
  };

  const handleRetry = async (executionId: string) => {
    try {
      await api.post(`/api/v1/workflow-execution/${executionId}/retry`);
      await loadExecutions();
    } catch (err: any) {
      setError(err.response?.data?.message || '重试执行失败');
      console.error('重试执行失败:', err);
    }
  };

  const loadLogs = async (executionId: string) => {
    try {
      const response = await api.get<{ logs: string[] }>(`/api/v1/workflow-execution/${executionId}/logs`);
      setLogs(response.data?.logs || []);
    } catch (err: any) {
      console.error('加载日志失败:', err);
    }
  };

  const handleViewDetails = (execution: Execution) => {
    setSelectedExecution(execution);
    loadLogs(execution.id);
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      running: 'default',
      completed: 'secondary',
      failed: 'destructive',
      cancelled: 'outline',
    };
    const labels: Record<string, string> = {
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const filteredExecutions = executions.filter(exec => {
    const matchesStatus = filterStatus === 'all' || exec.status === filterStatus;
    const matchesSearch = searchTerm === '' || 
      exec.workflowName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      exec.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">工作流执行</h1>
          <p className="text-gray-600 mt-1">监控和管理工作流执行实例</p>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="搜索工作流..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-64"
          />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="all">全部状态</option>
            <option value="running">运行中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
            <option value="cancelled">已取消</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>执行记录</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-gray-500">加载中...</div>
            ) : filteredExecutions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">暂无执行记录</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>工作流</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>进度</TableHead>
                    <TableHead>开始时间</TableHead>
                    <TableHead>耗时</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredExecutions.map((exec) => (
                    <TableRow key={exec.id}>
                      <TableCell className="font-mono text-sm">{exec.id.slice(0, 8)}</TableCell>
                      <TableCell className="font-medium">{exec.workflowName}</TableCell>
                      <TableCell>{getStatusBadge(exec.status)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${exec.progress}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600">{exec.progress}%</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {new Date(exec.startedAt).toLocaleString('zh-CN')}
                      </TableCell>
                      <TableCell className="text-gray-600">
                        {exec.duration ? `${exec.duration}s` : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewDetails(exec)}
                          >
                            详情
                          </Button>
                          {exec.status === 'running' && (
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleCancel(exec.id)}
                            >
                              取消
                            </Button>
                          )}
                          {exec.status === 'failed' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRetry(exec.id)}
                            >
                              重试
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

        <Card>
          <CardHeader>
            <CardTitle>执行详情</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedExecution ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">执行ID</h3>
                  <p className="font-mono text-sm">{selectedExecution.id}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">工作流</h3>
                  <p>{selectedExecution.workflowName}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">状态</h3>
                  {getStatusBadge(selectedExecution.status)}
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">进度</h3>
                  <p>{selectedExecution.progress}% ({selectedExecution.currentStep || 'N/A'})</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">开始时间</h3>
                  <p className="text-sm">{new Date(selectedExecution.startedAt).toLocaleString('zh-CN')}</p>
                </div>
                {selectedExecution.completedAt && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">完成时间</h3>
                    <p className="text-sm">{new Date(selectedExecution.completedAt).toLocaleString('zh-CN')}</p>
                  </div>
                )}
                {selectedExecution.error && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">错误信息</h3>
                    <p className="text-sm text-red-600">{selectedExecution.error}</p>
                  </div>
                )}
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">执行日志</h3>
                  <div className="h-48 overflow-auto bg-gray-900 text-gray-100 p-3 rounded-md text-xs font-mono">
                    {logs.length > 0 ? (
                      logs.map((log, i) => (
                        <div key={i} className="mb-1">{log}</div>
                      ))
                    ) : (
                      <div className="text-gray-500">暂无日志</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                选择一个执行记录查看详情
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
