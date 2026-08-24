'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface AuditLog {
  id: string;
  timestamp: string;
  userId: string;
  action: string;
  resource: string;
  ipAddress: string;
  userAgent: string;
  result: 'success' | 'failure' | 'warning';
  details: string;
  category: string;
}

interface AuditSummary {
  totalLogs: number;
  successCount: number;
  failureCount: number;
  warningCount: number;
  topUsers: { userId: string; count: number }[];
  topActions: { action: string; count: number }[];
}

export default function SecurityAuditPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<AuditSummary>({
    totalLogs: 0,
    successCount: 0,
    failureCount: 0,
    warningCount: 0,
    topUsers: [],
    topActions: [],
  });
  const [filters, setFilters] = useState({
    userId: '',
    action: '',
    category: '',
    result: '',
    startDate: '',
    endDate: '',
  });

  const loadAuditData = async () => {
    setLoading(true);
    try {
      const [logsRes, summaryRes] = await Promise.all([
        api.get('/api/v1/security/audit/logs', { params: filters }),
        api.get('/api/v1/security/audit/summary'),
      ]);

      const logsData = logsRes.data?.logs || [];
      const summaryData = summaryRes.data || {};

      setLogs(logsData);
      setSummary({
        totalLogs: summaryData.totalLogs || logsData.length,
        successCount: summaryData.successCount || logsData.filter((l: AuditLog) => l.result === 'success').length,
        failureCount: summaryData.failureCount || logsData.filter((l: AuditLog) => l.result === 'failure').length,
        warningCount: summaryData.warningCount || logsData.filter((l: AuditLog) => l.result === 'warning').length,
        topUsers: summaryData.topUsers || [],
        topActions: summaryData.topActions || [],
      });
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleExportLogs = async () => {
    try {
      const response = await api.get('/api/v1/security/audit/export', {
        params: filters,
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-logs-${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      success('审计日志导出成功');
    } catch (err) {
      showError('导出失败');
    }
  };

  const handleSearch = () => {
    loadAuditData();
  };

  const handleResetFilters = () => {
    setFilters({
      userId: '',
      action: '',
      category: '',
      result: '',
      startDate: '',
      endDate: '',
    });
  };

  useEffect(() => {
    loadAuditData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getResultColor = (result: string) => {
    switch (result) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failure':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">安全审计</h1>
        <div className="flex gap-2">
          <Button onClick={loadAuditData}>刷新数据</Button>
          <Button onClick={handleExportLogs}>导出日志</Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总日志数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{summary.totalLogs}</p>
            <p className="text-sm text-gray-500">审计记录</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">成功操作</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{summary.successCount}</p>
            <p className="text-sm text-gray-500">执行成功</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">失败操作</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{summary.failureCount}</p>
            <p className="text-sm text-gray-500">执行失败</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告操作</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{summary.warningCount}</p>
            <p className="text-sm text-gray-500">需要关注</p>
          </CardContent>
        </Card>
      </div>

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <Input
              placeholder="用户ID"
              value={filters.userId}
              onChange={(e) => setFilters({ ...filters, userId: e.target.value })}
            />
            <Input
              placeholder="操作类型"
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
            />
            <Input
              placeholder="分类"
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            />
            <Select
              value={filters.result}
              onChange={(e) => setFilters({ ...filters, result: e.target.value })}
            >
              <option value="">所有结果</option>
              <option value="success">成功</option>
              <option value="failure">失败</option>
              <option value="warning">警告</option>
            </Select>
            <Input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
            />
            <Input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
            />
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={handleSearch}>搜索</Button>
            <Button variant="outline" onClick={handleResetFilters}>重置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 审计日志列表 */}
      <Card>
        <CardHeader>
          <CardTitle>审计日志</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>用户</TableHead>
                <TableHead>操作</TableHead>
                <TableHead>资源</TableHead>
                <TableHead>分类</TableHead>
                <TableHead>结果</TableHead>
                <TableHead>IP地址</TableHead>
                <TableHead>详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length > 0 ? logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{log.userId}</TableCell>
                  <TableCell>{log.action}</TableCell>
                  <TableCell>{log.resource}</TableCell>
                  <TableCell>{log.category}</TableCell>
                  <TableCell>
                    <Badge className={getResultColor(log.result)}>{log.result}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{log.ipAddress}</TableCell>
                  <TableCell className="text-sm text-gray-500 max-w-xs truncate">{log.details}</TableCell>
                </TableRow>
              )) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-gray-500">
                    No audit logs found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 统计图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>活跃用户排行</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {summary.topUsers.length > 0 ? summary.topUsers.map((user, idx) => (
                <div key={user.userId} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                  <span className="font-medium">{user.userId}</span>
                  <Badge>{user.count} 次操作</Badge>
                </div>
              )) : (
                <p className="text-center text-gray-500 py-4">暂无数据</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>热门操作排行</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {summary.topActions.length > 0 ? summary.topActions.map((action, idx) => (
                <div key={action.action} className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded">
                  <span className="font-medium">{action.action}</span>
                  <Badge>{action.count} 次</Badge>
                </div>
              )) : (
                <p className="text-center text-gray-500 py-4">暂无数据</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
