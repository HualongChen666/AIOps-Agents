'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface ChaosMetrics {
  experiments: { total: number; running: number; completed: number; failed: number; success_rate: number };
  scenarios: { total: number; enabled: number };
  faults: { total: number; by_type: Record<string, number> };
  engine: Record<string, unknown>;
}

interface ChaosStatus {
  enabled: boolean;
  stats: Record<string, unknown>;
}

export default function ChaosDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<ChaosMetrics | null>(null);
  const [status, setStatus] = useState<ChaosStatus | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [mRes, sRes] = await Promise.all([
        api.get('/api/v1/chaos/metrics'),
        api.get('/api/v1/chaos/status'),
      ]);
      setMetrics(mRes.data.data);
      setStatus(sRes.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌仪表盘失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">混沌仪表盘</h1>
          <Badge variant={status?.enabled ? 'default' : 'secondary'}>{status?.enabled ? '引擎已启用' : '引擎已停用'}</Badge>
        </div>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>成功率</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={metrics?.experiments.success_rate ?? 0} title="实验成功率" unit="%" color="#10b981" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">实验总数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.experiments.total ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">运行中</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-blue-600">{metrics?.experiments.running ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">失败</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{metrics?.experiments.failed ?? 0}</div></CardContent></Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已完成</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.experiments.completed ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">场景（启用/总）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.scenarios.enabled ?? 0} / {metrics?.scenarios.total ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">故障注入</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics?.faults.total ?? 0}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>故障类型分布</CardTitle></CardHeader>
        <CardContent>
          {!metrics || Object.keys(metrics.faults.by_type || {}).length === 0 ? (
            <div className="text-gray-500 text-center py-6">暂无故障注入数据</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(metrics.faults.by_type).map(([k, v]) => (
                <div key={k} className="border rounded p-3">
                  <div className="text-sm text-gray-600">{k}</div>
                  <div className="text-xl font-bold">{v}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
