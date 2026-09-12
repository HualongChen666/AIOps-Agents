'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface MeshMetrics {
  time_range: string;
  total_requests: number;
  success_rate: number;
  error_rate: number;
  configurations?: { total: number; active: number };
  traffic_rules?: { total: number; enabled: number };
  collected_at: string;
}

export default function ServiceMonitoringPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MeshMetrics | null>(null);
  const [timeRange, setTimeRange] = useState('1h');

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/metrics', { params: { time_range: timeRange } });
      setMetrics(res.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载网格指标失败');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务监控</h1>
        <div className="flex items-center gap-2">
          <select className="border rounded px-2 py-1 text-sm" value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="1h">近 1 小时</option>
            <option value="24h">近 24 小时</option>
            <option value="7d">近 7 天</option>
          </select>
          <Button onClick={fetchData}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>成功率</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={metrics?.success_rate ?? 0} title="请求成功率" unit="%" color="#10b981" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">总请求数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.total_requests ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">错误率</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{(metrics?.error_rate ?? 0).toFixed(2)}%</div></CardContent></Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">配置（活跃/总）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.configurations?.active ?? 0} / {metrics?.configurations?.total ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">流量规则（启用/总）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.traffic_rules?.enabled ?? 0} / {metrics?.traffic_rules?.total ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">采集时间</CardTitle></CardHeader><CardContent><div className="text-sm">{metrics?.collected_at ? new Date(metrics.collected_at).toLocaleString() : '—'}</div></CardContent></Card>
      </div>
    </div>
  );
}
