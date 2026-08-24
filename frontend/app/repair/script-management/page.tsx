'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import api from '@/lib/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ScriptExecution {
  id: string;
  scriptId: string;
  scriptName: string;
  targetHost: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startTime: string;
  endTime?: string;
  duration?: number;
  output?: string;
  error?: string;
  executedBy: string;
}

export default function ScriptManagementPage() {
  const [executions, setExecutions] = useState<ScriptExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadExecutions = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.get('/api/v1/repair/scripts/executions');
      const items = resp.data?.items || [];
      setExecutions(
        items.map((item: any) => ({
          id: item.id || String(Date.now()),
          scriptId: item.script_id || '',
          scriptName: item.script_name || '',
          targetHost: item.target_host || '',
          status: (item.status || 'pending') as ScriptExecution['status'],
          startTime: item.start_time || new Date().toISOString(),
          endTime: item.end_time,
          duration: item.duration,
          output: item.output,
          error: item.error,
          executedBy: item.executed_by || 'System',
        }))
      );
    } catch (err: any) {
      console.error('加载脚本执行记录失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExecutions();
  }, []);

  const handleCancelExecution = async (executionId: string) => {
    try {
      await api.post(`/api/v1/repair/scripts/executions/${executionId}/cancel`);
      await loadExecutions();
    } catch (err: any) {
      console.error('取消执行失败:', err);
      setError(err.message || '取消失败');
    }
  };

  const handleRetryExecution = async (executionId: string) => {
    try {
      await api.post(`/api/v1/repair/scripts/executions/${executionId}/retry`);
      await loadExecutions();
    } catch (err: any) {
      console.error('重试执行失败:', err);
      setError(err.message || '重试失败');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredExecutions = executions.filter((exec) => {
    const matchesStatus = filterStatus === 'all' || exec.status === filterStatus;
    const matchesSearch = exec.scriptName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         exec.targetHost.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">脚本管理</h1>
        <Button onClick={loadExecutions} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">总计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">待执行</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executions.filter(e => e.status === 'pending').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">运行中</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executions.filter(e => e.status === 'running').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">已完成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executions.filter(e => e.status === 'completed').length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">失败</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executions.filter(e => e.status === 'failed').length}</div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选和搜索 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Input
              placeholder="搜索脚本名称或目标主机..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-md"
            />
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="pending">待执行</SelectItem>
                <SelectItem value="running">运行中</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="cancelled">已取消</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 执行记录列表 */}
      <Card>
        <CardHeader>
          <CardTitle>脚本执行记录</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : filteredExecutions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">暂无数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>脚本名称</TableHead>
                  <TableHead>目标主机</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>开始时间</TableHead>
                  <TableHead>结束时间</TableHead>
                  <TableHead>持续时间</TableHead>
                  <TableHead>执行者</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredExecutions.map((exec) => (
                  <TableRow key={exec.id}>
                    <TableCell className="font-mono text-sm">{exec.id}</TableCell>
                    <TableCell className="font-medium">{exec.scriptName}</TableCell>
                    <TableCell className="font-mono text-sm">{exec.targetHost}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(exec.status)}>
                        {exec.status === 'pending' ? '待执行' :
                         exec.status === 'running' ? '运行中' :
                         exec.status === 'completed' ? '已完成' :
                         exec.status === 'failed' ? '失败' : '已取消'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {new Date(exec.startTime).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {exec.endTime ? new Date(exec.endTime).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {exec.duration ? `${exec.duration}s` : '-'}
                    </TableCell>
                    <TableCell>{exec.executedBy}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {exec.status === 'pending' && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancelExecution(exec.id)}
                          >
                            取消
                          </Button>
                        )}
                        {exec.status === 'running' && (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleCancelExecution(exec.id)}
                          >
                            停止
                          </Button>
                        )}
                        {exec.status === 'failed' && (
                          <Button
                            size="sm"
                            onClick={() => handleRetryExecution(exec.id)}
                          >
                            重试
                          </Button>
                        )}
                        {exec.status === 'completed' && (
                          <Button variant="ghost" size="sm">
                            查看日志
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
    </div>
  );
}
