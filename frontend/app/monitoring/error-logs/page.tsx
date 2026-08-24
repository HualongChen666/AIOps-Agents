'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface ErrorLog {
  id?: string;
  timestamp?: string;
  level?: string;
  service?: string;
  message?: string;
  stack_trace?: string;
  count?: number;
  [key: string]: any;
}

interface ErrorLogsData {
  total_errors?: number;
  critical_errors?: number;
  warning_errors?: number;
  info_errors?: number;
  errors?: ErrorLog[];
  time_range?: string;
  [key: string]: any;
}

export default function ErrorLogsPage() {
  const [timeRange, setTimeRange] = useState('1h');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('all');

  const { data: errorData, isLoading, error, refetch } = useQuery<ErrorLogsData>({
    queryKey: ['monitoring-error-logs', timeRange, selectedLevel],
    queryFn: async () => {
      const params: any = { time_range: timeRange };
      if (selectedLevel !== 'all') params.level = selectedLevel;
      const resp = await api.get('/api/v1/monitoring/error-logs', { params });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const filteredErrors = errorData?.errors?.filter(e =>
    e.message?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.service?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handleResolveError = async (errorId: string) => {
    try {
      await api.post('/api/v1/monitoring/error-logs/resolve', { error_id: errorId });
      refetch();
    } catch (err) {
      console.error('Failed to resolve error:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">错误日志</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)}>
            <option value="all">所有级别</option>
            <option value="critical">严重</option>
            <option value="warning">警告</option>
            <option value="info">信息</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总错误数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{errorData?.total_errors || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">严重错误</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{errorData?.critical_errors || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">警告错误</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{errorData?.warning_errors || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">信息错误</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{errorData?.info_errors || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>错误列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索错误消息或服务..."
              className="mb-4"
            />
            <div className="max-h-96 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left">时间</th>
                    <th className="px-4 py-2 text-left">级别</th>
                    <th className="px-4 py-2 text-left">服务</th>
                    <th className="px-4 py-2 text-left">消息</th>
                    <th className="px-4 py-2 text-left">次数</th>
                    <th className="px-4 py-2 text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredErrors.map((errorLog, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-4 py-2">
                        {errorLog.timestamp ? new Date(errorLog.timestamp).toLocaleString() : '-'}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          errorLog.level === 'critical' ? 'bg-red-100 text-red-800' : 
                          errorLog.level === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {errorLog.level}
                        </span>
                      </td>
                      <td className="px-4 py-2">{errorLog.service}</td>
                      <td className="px-4 py-2 max-w-xs truncate">{errorLog.message}</td>
                      <td className="px-4 py-2">{errorLog.count || 1}</td>
                      <td className="px-4 py-2">
                        <Button
                          size="sm"
                          onClick={() => errorLog.id && handleResolveError(errorLog.id)}
                        >
                          标记已解决
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
