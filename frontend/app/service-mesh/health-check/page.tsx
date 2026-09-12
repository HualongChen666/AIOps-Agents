'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

interface HealthSummary {
  total_configurations: number;
  active_configurations: number;
  total_traffic_rules: number;
  enabled_traffic_rules: number;
  total_policies: number;
  enabled_policies: number;
  checked_at: string;
}

export default function HealthCheckPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<HealthSummary | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/health/summary');
      setSummary(res.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载健康汇总失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  const cards = [
    { label: '配置（活跃/总）', value: `${summary?.active_configurations ?? 0} / ${summary?.total_configurations ?? 0}` },
    { label: '流量规则（启用/总）', value: `${summary?.enabled_traffic_rules ?? 0} / ${summary?.total_traffic_rules ?? 0}` },
    { label: '策略（启用/总）', value: `${summary?.enabled_policies ?? 0} / ${summary?.total_policies ?? 0}` },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">健康检查</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">{c.label}</CardTitle></CardHeader>
            <CardContent><div className="text-2xl font-bold">{c.value}</div></CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>检查时间</CardTitle></CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600">{summary?.checked_at ? new Date(summary.checked_at).toLocaleString() : '—'}</div>
        </CardContent>
      </Card>
    </div>
  );
}
