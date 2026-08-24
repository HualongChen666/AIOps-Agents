'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface HistoryData {
  timestamps?: string[];
  cpu?: number[];
  memory?: number[];
  network_in?: number[];
  network_out?: number[];
  disk?: number[];
  [key: string]: any;
}

export default function MetricsHistoryPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const [metricType, setMetricType] = useState('cpu');

  const { data: historyData, isLoading, error, refetch } = useQuery<HistoryData>({
    queryKey: ['monitoring-metrics-history', timeRange, metricType],
    queryFn: async () => {
      const resp = await api.get('/api/v1/monitoring/metrics-history', {
        params: { time_range: timeRange, metric_type: metricType }
      });
      return resp.data;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="text-center text-gray-500 py-8">加载中...</div>;
  if (error) return <div className="text-center text-red-500 py-8">加载失败: {(error as Error).message}</div>;

  const renderChart = () => {
    if (!historyData?.timestamps || !historyData[metricType]) {
      return <p className="text-gray-500">暂无数据</p>;
    }

    const data = historyData[metricType] as number[];
    const timestamps = historyData.timestamps;
    const width = 800;
    const height = 300;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((v, i) => {
      const x = padding + (i / (data.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((v - min) / range) * chartHeight;
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-80" preserveAspectRatio="xMidYMid meet">
        <rect x={padding} y={padding} width={chartWidth} height={chartHeight} fill="#f9fafb" />
        <line x1={padding} y1={padding + chartHeight} x2={padding + chartWidth} y2={padding + chartHeight} stroke="#d1d5db" />
        <line x1={padding} y1={padding} x2={padding} y2={padding + chartHeight} stroke="#d1d5db" />
        <polyline fill="none" stroke="#2563eb" strokeWidth={2} points={points} />
      </svg>
    );
  };

  const calculateStats = (data: number[] | undefined) => {
    if (!data || data.length === 0) return { avg: '-', max: '-', min: '-' };
    const sum = data.reduce((a, b) => a + b, 0);
    return {
      avg: (sum / data.length).toFixed(2),
      max: Math.max(...data).toFixed(2),
      min: Math.min(...data).toFixed(2),
    };
  };

  const stats = calculateStats(historyData?.[metricType] as number[]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">历史数据</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
            <option value="30d">30天</option>
          </Select>
          <Select value={metricType} onChange={(e) => setMetricType(e.target.value)}>
            <option value="cpu">CPU</option>
            <option value="memory">内存</option>
            <option value="network_in">网络入</option>
            <option value="network_out">网络出</option>
            <option value="disk">磁盘</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>历史趋势图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
            {renderChart()}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均值</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avg}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">最大值</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.max}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">最小值</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.min}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>数据详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">时间</th>
                  <th className="px-4 py-2 text-left">值</th>
                </tr>
              </thead>
              <tbody>
                {historyData?.timestamps?.map((ts, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{new Date(ts).toLocaleString()}</td>
                    <td className="px-4 py-2">{((historyData[metricType] as number[])[i])?.toFixed(2) || '-'}</td>
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
