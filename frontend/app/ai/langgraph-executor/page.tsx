'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  input: Record<string, any>;
  output?: Record<string, any>;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

interface ExecutionLog {
  execution_id: string;
  node_id: string;
  node_name: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
}

export default function LangGraphExecutorPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const [newExecution, setNewExecution] = useState({ workflow_id: '', input: '{}' });

  useEffect(() => {
    fetchExecutions();
    const interval = setInterval(fetchExecutions, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedExecution) {
      fetchLogs(selectedExecution);
    }
  }, [selectedExecution]);

  const fetchExecutions = async () => {
    try {
      const res = await api.get('/api/ai/langgraph-executor/executions');
      setExecutions(res.data.executions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载执行记录失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async (executionId: string) => {
    try {
      const res = await api.get(`/api/ai/langgraph-executor/executions/${executionId}/logs`);
      setLogs(res.data.logs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载日志失败');
    }
  };

  const handleStartExecution = async () => {
    try {
      const input = JSON.parse(newExecution.input);
      await api.post('/api/ai/langgraph-executor/executions', {
        workflow_id: newExecution.workflow_id,
        input
      });
      setNewExecution({ workflow_id: '', input: '{}' });
      fetchExecutions();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '启动执行失败');
    }
  };

  const handleCancelExecution = async (id: string) => {
    try {
      await api.post(`/api/ai/langgraph-executor/executions/${id}/cancel`);
      fetchExecutions();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '取消执行失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchExecutions} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">工作流执行器</h1>
        <Button onClick={fetchExecutions}>刷新</Button>
      </div>

      {/* 启动执行 */}
      <Card>
        <CardHeader>
          <CardTitle>启动执行</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="工作流ID"
              value={newExecution.workflow_id}
              onChange={(e) => setNewExecution({ ...newExecution, workflow_id: e.target.value })}
            />
            <Input
              placeholder="输入 (JSON格式)"
              value={newExecution.input}
              onChange={(e) => setNewExecution({ ...newExecution, input: e.target.value })}
            />
          </div>
          <Button onClick={handleStartExecution} className="mt-4">启动执行</Button>
        </CardContent>
      </Card>

      {/* 执行记录 */}
      <Card>
        <CardHeader>
          <CardTitle>执行记录</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {executions.map((execution) => (
              <div
                key={execution.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedExecution === execution.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedExecution(execution.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{execution.workflow_name}</h3>
                    <Badge variant={
                      execution.status === 'completed' ? 'default' :
                      execution.status === 'running' ? 'secondary' :
                      execution.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {execution.status}
                    </Badge>
                  </div>
                  {execution.status === 'running' && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCancelExecution(execution.id);
                      }}
                    >
                      取消
                    </Button>
                  )}
                </div>
                <div className="text-sm text-gray-600 mb-1">
                  开始时间: {new Date(execution.started_at).toLocaleString()}
                </div>
                {execution.duration_ms && (
                  <div className="text-sm text-gray-600">
                    耗时: {execution.duration_ms}ms
                  </div>
                )}
                {execution.error_message && (
                  <div className="text-sm text-red-600 mt-1">{execution.error_message}</div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 执行日志 */}
      {selectedExecution && (
        <Card>
          <CardHeader>
            <CardTitle>执行日志</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-96 overflow-auto">
              {logs.map((log, idx) => (
                <div key={idx} className="border-l-2 pl-3 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={
                      log.level === 'error' ? 'destructive' :
                      log.level === 'warning' ? 'secondary' : 'outline'
                    }>
                      {log.level}
                    </Badge>
                    <span className="font-medium">{log.node_name}</span>
                    <span className="text-gray-500">{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="text-gray-700">{log.message}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
