'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';

interface DRStatus {
  status: string;
  dr_enabled: boolean;
  last_dr_test: string | null;
  dr_status: string;
  recovery_time_objective_minutes: number;
  recovery_point_objective_minutes: number;
}

interface Scenario {
  name: string;
  description: string;
  enabled: boolean;
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  healthy: 'default',
  warning: 'secondary',
  unhealthy: 'destructive',
};

export default function DisasterRecoveryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<DRStatus | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statusRes, scenarioRes] = await Promise.all([
        api.get('/api/disaster/disaster-recovery'),
        api.get('/api/disaster/dr-scenarios'),
      ]);
      setStatus(statusRes.data);
      setScenarios(scenarioRes.data.scenarios || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载灾难恢复状态失败');
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
        <h1 className="text-3xl font-bold text-gray-900">灾难恢复</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>DR 状态</CardTitle></CardHeader>
          <CardContent>
            <Badge variant={STATUS_VARIANT[status?.dr_status ?? ''] ?? 'secondary'}>{status?.dr_status ?? 'unknown'}</Badge>
            <div className="text-xs text-gray-500 mt-2">{status?.dr_enabled ? 'DR 已启用' : 'DR 已停用'}</div>
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">RTO（分钟）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{status?.recovery_time_objective_minutes ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">RPO（分钟）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{status?.recovery_point_objective_minutes ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">最近演练</CardTitle></CardHeader><CardContent><div className="text-sm">{status?.last_dr_test ? new Date(status.last_dr_test).toLocaleString() : '无'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>灾难恢复场景</CardTitle></CardHeader>
        <CardContent>
          {scenarios.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无场景</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {scenarios.map((s) => (
                <div key={s.name} className="border rounded-lg p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{s.name}</div>
                    <div className="text-sm text-gray-500">{s.description}</div>
                  </div>
                  <Badge variant={s.enabled ? 'default' : 'secondary'}>{s.enabled ? '启用' : '停用'}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
