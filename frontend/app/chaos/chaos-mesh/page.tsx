'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MeshStatus {
  injector: string;
  api_group: string | null;
  api_version: string | null;
  namespace: string | null;
  kubernetes_client_available: boolean;
  enabled: boolean;
}

export default function ChaosMeshPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mesh, setMesh] = useState<MeshStatus | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/chaos/mesh');
      setMesh(res.data.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载 Chaos Mesh 状态失败');
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
        <h1 className="text-3xl font-bold text-gray-900">Chaos Mesh</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">注入后端</CardTitle></CardHeader><CardContent><div className="text-lg font-bold">{mesh?.injector}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">CRD 版本</CardTitle></CardHeader><CardContent><div className="text-lg font-bold">{mesh?.api_group}/{mesh?.api_version}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">命名空间</CardTitle></CardHeader><CardContent><div className="text-lg font-bold">{mesh?.namespace ?? '—'}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>集群客户端</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">kubernetes Python 客户端</span>
            <Badge variant={mesh?.kubernetes_client_available ? 'default' : 'destructive'}>
              {mesh?.kubernetes_client_available ? '可用' : '不可用'}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">混沌引擎</span>
            <Badge variant={mesh?.enabled ? 'default' : 'secondary'}>{mesh?.enabled ? '已启用' : '已停用'}</Badge>
          </div>
          {!mesh?.kubernetes_client_available && (
            <div className="text-sm text-amber-600">
              未检测到 kubernetes 客户端：实验会记录 requires-backend 错误而非伪造注入。请安装集群客户端并配置 kubeconfig。
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>注入资源类型</CardTitle></CardHeader>
        <CardContent className="text-sm text-gray-600 space-y-1">
          <div>· NetworkChaos — 网络延迟 / 分区（network_latency、network_partition）</div>
          <div>· PodChaos — 服务故障（service_crash、service_failure）</div>
          <div>· StressChaos — 资源限制（cpu_overload、memory_leak）</div>
          <div>· IOChaos — 磁盘故障（disk_failure、database_error、cache_failure）</div>
        </CardContent>
      </Card>
    </div>
  );
}
