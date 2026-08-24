'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface MetricsData {
  cpu?: { usage_percent?: number };
  memory?: { usage_percent?: number };
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  disk?: { usage_percent?: number };
  [key: string]: any;
}

export default function MetricsPage() {
  const [selectedMetric, setSelectedMetric] = useState('cpu');
  const [timeRange, setTimeRange] = useState('1h');

  const { data: metricsData, isLoading, error, refetch } = useQuery<MetricsData>({
    queryKey: ['monitoring-metrics', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics', {
        params: { time_range: timeRange }
      });
      return resp.data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const metrics = [
    { key: 'cpu', label: 'CPU使用率', value: metricsData?.cpu?.usage_percent, unit: '%' },
    { key: 'memory', label: '内存使用率', value: metricsData?.memory?.usage_percent, unit: '%' },
    { key: 'network_in', label: '网络入流量', value: metricsData?.network?.recv_speed_mb, unit: 'MB/s' },
    { key: 'network_out', label: '网络出流量', value: metricsData?.network?.sent_speed_mb, unit: 'MB/s' },
    { key: 'disk', label: '磁盘使用率', value: metricsData?.disk?.usage_percent, unit: '%' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">系统指标</h1>
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.key}>
            <CardHeader>
              <CardTitle className="text-sm">{metric.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metric.value !== undefined ? metric.value.toFixed(2) : '-'}
              </div>
              <div className="text-sm text-gray-500">{metric.unit}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>指标详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">选择指标</label>
              <Select value={selectedMetric} onChange={(e) => setSelectedMetric(e.target.value)}>
                {metrics.map((m) => (
                  <option key={m.key} value={m.key}>{m.label}</option>
                ))}
              </Select>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <pre className="text-sm overflow-auto">
                {JSON.stringify(metricsData, null, 2)}
              </pre>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
