'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface ObservabilityConfig {
  id: string;
  name: string;
  tracing_enabled: boolean;
  metrics_enabled: boolean;
  access_logging_enabled: boolean;
  sampling_rate: number;
  prometheus_enabled: boolean;
  grafana_enabled: boolean;
  enabled: boolean;
}

export default function MeshObservabilityPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [configs, setConfigs] = useState<ObservabilityConfig[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', sampling_rate: 1.0, tracing: true, metrics: true, logging: true, prometheus: true, grafana: false });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/observability');
      setConfigs(res.data.data?.observability_configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载可观测性配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const create = async () => {
    if (!form.name.trim()) {
      toast.error('请填写配置名称');
      return;
    }
    try {
      setCreating(true);
      await api.post('/api/v1/service-mesh/observability', {
        name: form.name,
        tracing_enabled: form.tracing,
        metrics_enabled: form.metrics,
        access_logging_enabled: form.logging,
        sampling_rate: form.sampling_rate,
        prometheus_enabled: form.prometheus,
        grafana_enabled: form.grafana,
      });
      toast.success('可观测性配置已创建');
      setForm({ name: '', sampling_rate: 1.0, tracing: true, metrics: true, logging: true, prometheus: true, grafana: false });
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">网格可观测性</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>新建可观测性配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div><Label htmlFor="ob-name">名称</Label><Input id="ob-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1" /></div>
            <div><Label htmlFor="ob-sr">采样率 (0-1)</Label><Input id="ob-sr" type="number" step="0.1" value={form.sampling_rate} onChange={(e) => setForm({ ...form, sampling_rate: Number(e.target.value) || 0 })} className="mt-1" /></div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {([['tracing', '链路追踪'], ['metrics', '指标'], ['logging', '访问日志'], ['prometheus', 'Prometheus'], ['grafana', 'Grafana']] as const).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between border rounded px-3 py-2">
                <span className="text-sm">{label}</span>
                <input type="checkbox" checked={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />
              </div>
            ))}
          </div>
          <Button onClick={create} disabled={creating}>{creating ? '创建中...' : '创建配置'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>配置列表（{configs.length}）</CardTitle></CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无可观测性配置</div>
          ) : (
            <div className="space-y-3">
              {configs.map((c) => (
                <div key={c.id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold">{c.name}</span>
                    <Badge variant={c.enabled ? 'default' : 'secondary'}>{c.enabled ? '启用' : '停用'}</Badge>
                    <span className="text-xs text-gray-500">采样率 {c.sampling_rate}</span>
                  </div>
                  <div className="flex gap-2 flex-wrap text-xs">
                    {c.tracing_enabled && <Badge variant="secondary">Tracing</Badge>}
                    {c.metrics_enabled && <Badge variant="secondary">Metrics</Badge>}
                    {c.access_logging_enabled && <Badge variant="secondary">AccessLog</Badge>}
                    {c.prometheus_enabled && <Badge variant="secondary">Prometheus</Badge>}
                    {c.grafana_enabled && <Badge variant="secondary">Grafana</Badge>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
