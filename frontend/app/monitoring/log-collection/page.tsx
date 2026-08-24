'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface LogSource {
  name?: string;
  type?: string;
  status?: string;
  logs_per_minute?: number;
  total_logs?: number;
  last_log_time?: string;
  [key: string]: any;
}

interface LogCollectionData {
  total_sources?: number;
  active_sources?: number;
  inactive_sources?: number;
  total_logs_collected?: number;
  logs_per_minute?: number;
  sources?: LogSource[];
  [key: string]: any;
}

export default function LogCollectionPage() {
  const [timeRange, setTimeRange] = useState('1h');

  const { data: logData, isLoading, error, refetch } = useQuery<LogCollectionData>({
    queryKey: ['monitoring-log-collection', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/log-collection', {
        params: { time_range: timeRange }
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const handleSourceAction = async (sourceName: string, action: string) => {
    try {
      await api.post('/api/v1/monitoring/log-collection/source-action', {
        source_name: sourceName,
        action
      });
      refetch();
    } catch (err) {
      console.error('Failed to perform source action:', err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">日志采集</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总日志源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logData?.total_sources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{logData?.active_sources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">非活跃源</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{logData?.inactive_sources || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">采集速率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logData?.logs_per_minute?.toFixed(0) || '-'} logs/min</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总采集日志数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{logData?.total_logs_collected?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>日志源列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">名称</th>
                  <th className="px-4 py-2 text-left">类型</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">日志/分钟</th>
                  <th className="px-4 py-2 text-left">总日志数</th>
                  <th className="px-4 py-2 text-left">最后日志时间</th>
                  <th className="px-4 py-2 text-left">操作</th>
                </tr>
              </thead>
              <tbody>
                {logData?.sources?.map((source, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{source.name}</td>
                    <td className="px-4 py-2">{source.type}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        source.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {source.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{source.logs_per_minute?.toFixed(0) || '-'}</td>
                    <td className="px-4 py-2">{source.total_logs?.toLocaleString() || '-'}</td>
                    <td className="px-4 py-2">
                      {source.last_log_time ? new Date(source.last_log_time).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <Button
                        size="sm"
                        onClick={() => source.name && handleSourceAction(source.name, source.status === 'active' ? 'stop' : 'start')}
                      >
                        {source.status === 'active' ? '停止' : '启动'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
