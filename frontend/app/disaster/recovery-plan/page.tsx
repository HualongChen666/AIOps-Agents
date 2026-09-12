'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface PlanStep {
  step: number;
  action: string;
  estimated_time_minutes: number;
  critical: boolean;
}

interface RecoveryPlan {
  name: string;
  version: string;
  steps: PlanStep[];
  total_estimated_time_minutes: number;
  last_updated: string;
}

export default function RecoveryPlanPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<RecoveryPlan | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/disaster/recovery-plan');
      setPlan(res.data.recovery_plan);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载恢复计划失败');
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

  if (error || !plan) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error || '无恢复计划'}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">恢复计划</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">计划名称</CardTitle></CardHeader><CardContent><div className="text-lg font-bold">{plan.name}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">版本</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{plan.version}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">预计总耗时</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{plan.total_estimated_time_minutes} 分钟</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>恢复步骤</CardTitle></CardHeader>
        <CardContent>
          <ol className="space-y-3">
            {plan.steps.map((s) => (
              <li key={s.step} className="border rounded-lg p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm">{s.step}</span>
                  <span>{s.action}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-500">{s.estimated_time_minutes} 分钟</span>
                  {s.critical && <Badge variant="destructive">关键</Badge>}
                </div>
              </li>
            ))}
          </ol>
          <div className="text-xs text-gray-400 mt-4">最后更新: {new Date(plan.last_updated).toLocaleString()}</div>
        </CardContent>
      </Card>
    </div>
  );
}
