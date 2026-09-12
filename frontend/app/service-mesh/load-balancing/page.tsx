'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface TrafficRule {
  id: string;
  name: string;
  service_name: string;
  weight: number;
  timeout_seconds: number;
  enabled: boolean;
  destination: Record<string, unknown>;
}

export default function LoadBalancingPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rules, setRules] = useState<TrafficRule[]>([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/v1/service-mesh/traffic');
      setRules(res.data.data?.traffic_rules || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载负载均衡规则失败');
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
        <h1 className="text-3xl font-bold text-gray-900">负载均衡</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      <Card>
        <CardHeader><CardTitle>流量权重分配（{rules.length}）</CardTitle></CardHeader>
        <CardContent>
          {rules.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无流量规则，权重分配基于已配置的流量规则</div>
          ) : (
            <div className="space-y-3">
              {rules.map((r) => (
                <div key={r.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{r.name}</span>
                      <Badge variant="secondary">{r.service_name}</Badge>
                      <Badge variant={r.enabled ? 'default' : 'secondary'}>{r.enabled ? '启用' : '停用'}</Badge>
                    </div>
                    <span className="text-lg font-bold">{r.weight}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded h-2">
                    <div className="bg-blue-500 h-2 rounded" style={{ width: `${Math.min(100, r.weight)}%` }} />
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    目的地: {JSON.stringify(r.destination)} | 超时: {r.timeout_seconds}s
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
