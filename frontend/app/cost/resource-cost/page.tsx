'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface ResourceCost {
  resource_type: string;
  resource_id: string;
  name: string;
  hourly_cost: number;
  daily_cost: number;
  monthly_cost: number;
  utilization: number;
  efficiency_score: number;
}

export default function ResourceCostPage() {
  const [costs, setCosts] = useState<ResourceCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCosts();
  }, []);

  const fetchCosts = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/resource-cost');
      setCosts(res.data.costs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载资源成本失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchCosts} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">资源成本</h1>
        <Button onClick={fetchCosts}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {costs.map((cost) => (
          <Card key={cost.resource_id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{cost.name}</CardTitle>
                <Badge variant="outline">{cost.resource_type}</Badge>
              </div>
              <div className="text-sm text-gray-500 font-mono">{cost.resource_id}</div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <div className="text-xs text-gray-500">小时</div>
                    <div className="font-semibold">${cost.hourly_cost.toFixed(4)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">天</div>
                    <div className="font-semibold">${cost.daily_cost.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500">月</div>
                    <div className="font-semibold">${cost.monthly_cost.toFixed(2)}</div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">利用率</span>
                    <span className="font-semibold">{cost.utilization.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${cost.utilization > 70 ? 'bg-green-500' : cost.utilization > 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                      style={{ width: `${cost.utilization}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">效率评分</span>
                    <span className="font-semibold">{cost.efficiency_score.toFixed(1)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-blue-500"
                      style={{ width: `${cost.efficiency_score * 10}%` }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
