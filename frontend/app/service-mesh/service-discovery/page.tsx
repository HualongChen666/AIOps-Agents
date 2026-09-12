'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface MeshService {
  id: string;
  name: string;
  mesh_type: string;
  namespace: string;
  status: string;
  mesh_id: string;
  mtls_enabled: boolean;
}

interface ServiceInstance {
  instance_id: string;
  host: string;
  port: number;
  status: string;
  weight: number;
  active_connections: number;
}

export default function ServiceDiscoveryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [services, setServices] = useState<MeshService[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [instances, setInstances] = useState<ServiceInstance[]>([]);
  const [instLoading, setInstLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/services');
      setServices(res.data.data?.services || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载服务失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const loadInstances = async (name: string) => {
    try {
      setSelected(name);
      setInstLoading(true);
      const res = await api.get(`/api/v1/service-mesh/services/${encodeURIComponent(name)}/instances`);
      setInstances(res.data.data?.instances || []);
    } catch (err: any) {
      setInstances([]);
    } finally {
      setInstLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  if (error) return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务发现</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>网格服务（{services.length}）</CardTitle></CardHeader>
        <CardContent>
          {services.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无已注册服务</div>
          ) : (
            <div className="space-y-2">
              {services.map((s) => (
                <div key={s.id} className="border rounded-lg p-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{s.name}</span>
                      <Badge variant="secondary">{s.mesh_type}</Badge>
                      <Badge variant={s.status === 'active' ? 'default' : 'secondary'}>{s.status}</Badge>
                    </div>
                    <div className="text-xs text-gray-500">命名空间: {s.namespace} | mTLS: {s.mtls_enabled ? '启用' : '关闭'}</div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => loadInstances(s.name)}>查看实例</Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selected && (
        <Card>
          <CardHeader><CardTitle>{selected} 的实例</CardTitle></CardHeader>
          <CardContent>
            {instLoading ? (
              <div className="text-gray-500 text-center py-6">加载中...</div>
            ) : instances.length === 0 ? (
              <div className="text-gray-500 text-center py-6">该服务暂无已注册实例</div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-600">
                    <th className="py-2">实例</th><th className="py-2">地址</th><th className="py-2">端口</th>
                    <th className="py-2">状态</th><th className="py-2">权重</th><th className="py-2">连接</th>
                  </tr>
                </thead>
                <tbody>
                  {instances.map((i) => (
                    <tr key={i.instance_id} className="border-b">
                      <td className="py-2 font-mono">{i.instance_id}</td>
                      <td className="py-2">{i.host}</td>
                      <td className="py-2">{i.port}</td>
                      <td className="py-2"><Badge variant={i.status === 'healthy' ? 'default' : 'destructive'}>{i.status}</Badge></td>
                      <td className="py-2">{i.weight}</td>
                      <td className="py-2">{i.active_connections}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
