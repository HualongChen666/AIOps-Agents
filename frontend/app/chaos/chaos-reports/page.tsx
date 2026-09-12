'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface ExperimentResult {
  experiment: string;
  status: string;
  success: boolean;
  duration_seconds: number;
  start_time: string;
  end_time: string | null;
}

interface ChaosMetrics {
  experiments: { total: number; running: number; completed: number; failed: number; success_rate: number };
  scenarios: { total: number; enabled: number };
  faults: { total: number };
}

export default function ChaosReportsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [experiments, setExperiments] = useState<ExperimentResult[]>([]);
  const [metrics, setMetrics] = useState<ChaosMetrics | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [expRes, mRes] = await Promise.all([
        api.get('/api/v1/chaos/experiments', { params: { limit: 50 } }),
        api.get('/api/v1/chaos/metrics'),
      ]);
      setExperiments(expRes.data.data?.experiments || []);
      setMetrics(mRes.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌报告失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const exportReport = () => {
    const payload = { generated_at: new Date().toISOString(), metrics, experiments };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chaos-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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

  const successCount = experiments.filter((e) => e.success).length;
  const avgDuration = experiments.length
    ? experiments.reduce((s, e) => s + (e.duration_seconds || 0), 0) / experiments.length
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">混沌报告</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={exportReport}>导出报告</Button>
          <Button onClick={fetchData}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>成功率</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={metrics?.experiments.success_rate ?? 0} title="实验成功率" unit="%" color="#3b82f6" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">实验记录</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{experiments.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">成功</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-green-600">{successCount}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">平均耗时</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{avgDuration.toFixed(2)}s</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>实验明细</CardTitle></CardHeader>
        <CardContent>
          {experiments.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无实验记录</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-600">
                  <th className="py-2">实验</th>
                  <th className="py-2">状态</th>
                  <th className="py-2">结果</th>
                  <th className="py-2">耗时</th>
                  <th className="py-2">开始时间</th>
                  <th className="py-2">结束时间</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((e, i) => (
                  <tr key={`${e.experiment}-${i}`} className="border-b">
                    <td className="py-2 font-mono">{e.experiment}</td>
                    <td className="py-2"><Badge variant="secondary">{e.status}</Badge></td>
                    <td className="py-2"><Badge variant={e.success ? 'default' : 'destructive'}>{e.success ? '成功' : '失败'}</Badge></td>
                    <td className="py-2">{e.duration_seconds?.toFixed(2) ?? '—'}s</td>
                    <td className="py-2">{e.start_time ? new Date(e.start_time).toLocaleString() : '—'}</td>
                    <td className="py-2">{e.end_time ? new Date(e.end_time).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
