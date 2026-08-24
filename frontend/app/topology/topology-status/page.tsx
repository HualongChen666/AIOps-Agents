'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface TopologyStatus {
  id: string;
  name: string;
  health: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    total: number;
    healthy: number;
    unhealthy: number;
  };
  last_check: string;
  issues: string[];
}

export default function TopologyStatusPage() {
  const [statuses, setStatuses] = useState<TopologyStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStatuses();
  }, []);

  const fetchStatuses = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/status');
      setStatuses(res.data.statuses || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载拓扑状态失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchStatuses} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑状态</h1>
        <Button onClick={fetchStatuses}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {statuses.map((status) => (
          <Card key={status.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{status.name}</CardTitle>
                <Badge variant={status.health === 'healthy' ? 'default' : status.health === 'degraded' ? 'secondary' : 'destructive'}>
                  {status.health}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-2xl font-bold">{status.services.total}</div>
                  <div className="text-sm text-gray-500">总服务</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{status.services.healthy}</div>
                  <div className="text-sm text-gray-500">健康</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{status.services.unhealthy}</div>
                  <div className="text-sm text-gray-500">异常</div>
                </div>
              </div>
              <div className="text-sm text-gray-500 mb-2">最后检查: {new Date(status.last_check).toLocaleString()}</div>
              {status.issues.length > 0 && (
                <div>
                  <h4 className="font-semibold text-sm mb-2">问题</h4>
                  <ul className="text-sm text-red-600 list-disc list-inside">
                    {status.issues.map((issue) => (
                      <li key={issue}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
