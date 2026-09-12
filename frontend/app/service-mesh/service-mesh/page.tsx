'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MeshSummary {
  mesh_type: string;
  mesh_status: string;
  istio_configs_count: number;
  traffic_configs_count: number;
  security_configs_count: number;
  total_configs_generated: number;
  configs_applied: number;
  supported_features: string[];
}

export default function ServiceMeshPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<MeshSummary | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/service-mesh/status');
      setSummary(res.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载服务网格状态失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">服务网格</h1>
          <Badge variant={summary?.mesh_status === 'active' ? 'default' : 'secondary'}>{summary?.mesh_status}</Badge>
        </div>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">网格类型</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary?.mesh_type}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">配置总数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary?.total_configs_generated ?? 0}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已应用</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{summary?.configs_applied ?? 0}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>支持特性</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {(summary?.supported_features || []).map((f) => <Badge key={f} variant="secondary">{f}</Badge>)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>配置构成</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div><span className="text-gray-600">Istio 配置:</span> {summary?.istio_configs_count ?? 0}</div>
          <div><span className="text-gray-600">流量配置:</span> {summary?.traffic_configs_count ?? 0}</div>
          <div><span className="text-gray-600">安全配置:</span> {summary?.security_configs_count ?? 0}</div>
        </CardContent>
      </Card>
    </div>
  );
}
