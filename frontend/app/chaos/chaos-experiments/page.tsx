'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select-shadcn';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface ExperimentResult {
  experiment: string;
  status: string;
  success: boolean;
  duration_seconds: number;
  start_time: string;
  end_time: string | null;
}

interface Template {
  id: string;
  name: string;
  type: string;
  description: string;
  severity: string;
  parameters: string[];
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  completed: 'default',
  running: 'secondary',
  failed: 'destructive',
};

export default function ChaosExperimentsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [experiments, setExperiments] = useState<ExperimentResult[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [experimentType, setExperimentType] = useState('latency_injection');
  const [running, setRunning] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [expRes, tplRes] = await Promise.all([
        api.get('/api/v1/chaos/experiments'),
        api.get('/api/v1/chaos/templates'),
      ]);
      setExperiments(expRes.data.data?.experiments || []);
      setTemplates(tplRes.data.data?.templates || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌实验失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const runExperiment = async () => {
    try {
      setRunning(true);
      const res = await api.post(`/api/v1/chaos/experiment/${experimentType}`, {});
      const payload = res.data.data ?? res.data;
      if (payload?.success === false) {
        toast.error('实验执行未成功，请查看引擎日志');
      } else {
        toast.success(`实验 ${experimentType} 已执行（${payload?.status ?? 'unknown'}）`);
      }
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '执行实验失败');
    } finally {
      setRunning(false);
    }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">混沌实验</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>执行实验</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="w-64">
            <label className="text-sm text-gray-600">实验类型</label>
            <Select value={experimentType} onValueChange={setExperimentType}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                {(templates.length ? templates : [{ id: 'latency_injection', name: '网络延迟注入' } as Template]).map((t) => (
                  <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={runExperiment} disabled={running}>{running ? '执行中...' : '执行实验'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>实验历史（{experiments.length}）</CardTitle></CardHeader>
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
                </tr>
              </thead>
              <tbody>
                {experiments.map((e, i) => (
                  <tr key={`${e.experiment}-${i}`} className="border-b">
                    <td className="py-2 font-mono">{e.experiment}</td>
                    <td className="py-2"><Badge variant={STATUS_VARIANT[e.status] ?? 'secondary'}>{e.status}</Badge></td>
                    <td className="py-2"><Badge variant={e.success ? 'default' : 'destructive'}>{e.success ? '成功' : '失败'}</Badge></td>
                    <td className="py-2">{e.duration_seconds?.toFixed(2) ?? '—'}s</td>
                    <td className="py-2">{e.start_time ? new Date(e.start_time).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>实验模板</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {templates.map((t) => (
              <div key={t.id} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary">{t.type}</Badge>
                  <span className="font-medium">{t.name}</span>
                </div>
                <div className="text-sm text-gray-600">{t.description}</div>
                <div className="text-xs text-gray-400 mt-1">参数: {t.parameters.join(', ')}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
