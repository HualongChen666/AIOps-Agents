'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface ChaosStatus {
  enabled: boolean;
  stats: Record<string, unknown>;
}

export default function ChaosConfigurationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<ChaosStatus | null>(null);
  const [toggling, setToggling] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/chaos/status');
      setStatus(res.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载混沌配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggle = async (enable: boolean) => {
    try {
      setToggling(true);
      await api.post(enable ? '/api/v1/chaos/enable' : '/api/v1/chaos/disable');
      toast.success(enable ? '混沌工程已启用' : '混沌工程已停用');
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '操作失败');
    } finally {
      setToggling(false);
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

  const stats = status?.stats ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold text-gray-900">混沌配置</h1>
          <Badge variant={status?.enabled ? 'default' : 'secondary'}>{status?.enabled ? '已启用' : '已停用'}</Badge>
        </div>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>引擎开关</CardTitle></CardHeader>
        <CardContent className="flex gap-3">
          <Button onClick={() => toggle(true)} disabled={toggling || status?.enabled}>启用混沌工程</Button>
          <Button variant="secondary" onClick={() => toggle(false)} disabled={toggling || !status?.enabled}>停用混沌工程</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>引擎统计</CardTitle></CardHeader>
        <CardContent>
          {Object.keys(stats).length === 0 ? (
            <div className="text-gray-500 text-center py-6">暂无统计数据</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(stats).map(([k, v]) => (
                <div key={k} className="border rounded p-3">
                  <div className="text-sm text-gray-600">{k}</div>
                  <div className="text-xl font-bold">{String(v)}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>安全约束</CardTitle></CardHeader>
        <CardContent className="text-sm text-gray-600 space-y-1">
          <div>· 混沌实验默认在生产环境禁用，仅在 development / staging 允许。</div>
          <div>· 实验执行前会进行依赖与资源可用性检查（见「安全检查」）。</div>
          <div>· 注入后端为 Chaos Mesh（chaos-mesh.org/v1alpha1）。</div>
        </CardContent>
      </Card>
    </div>
  );
}
