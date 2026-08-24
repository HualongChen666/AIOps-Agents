'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CostData {
  service: string;
  current_cost: number;
  budget: number;
  forecast: number;
  trend: 'up' | 'down' | 'stable';
  period: string;
}

export default function CostMonitoringPage() {
  const [costs, setCosts] = useState<CostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCosts();
    const interval = setInterval(fetchCosts, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchCosts = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/cost-monitoring');
      setCosts(res.data.costs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载成本数据失败');
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

  const totalCost = costs.reduce((sum, c) => sum + c.current_cost, 0);
  const totalBudget = costs.reduce((sum, c) => sum + c.budget, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本监控</h1>
        <Button onClick={fetchCosts}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalCost.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总预算</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalBudget.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">预算使用率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{((totalCost / totalBudget) * 100).toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">预测成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${costs.reduce((sum, c) => sum + c.forecast, 0).toFixed(2)}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {costs.map((cost) => (
          <Card key={cost.service}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{cost.service}</CardTitle>
                <Badge variant={cost.trend === 'up' ? 'destructive' : cost.trend === 'down' ? 'default' : 'secondary'}>
                  {cost.trend === 'up' ? '上升' : cost.trend === 'down' ? '下降' : '稳定'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">当前成本</span>
                    <span className="font-semibold">${cost.current_cost.toFixed(2)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${cost.current_cost > cost.budget ? 'bg-red-500' : 'bg-green-500'}`}
                      style={{ width: `${Math.min((cost.current_cost / cost.budget) * 100, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">预算: ${cost.budget.toFixed(2)}</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">预测</div>
                    <div className="text-lg font-semibold">${cost.forecast.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">周期</div>
                    <div className="text-sm">{cost.period}</div>
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
