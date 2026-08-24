'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SLOMetric {
  name: string;
  service: string;
  metric_type: string;
  current: number;
  target: number;
  trend: 'up' | 'down' | 'stable';
  history: number[];
}

export default function SLOMetricsPage() {
  const [metrics, setMetrics] = useState<SLOMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/metrics');
      setMetrics(res.data.metrics || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载指标失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchMetrics} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO指标</h1>
        <Button onClick={fetchMetrics}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.name}>
            <CardHeader>
              <CardTitle>{metric.name}</CardTitle>
              <div className="text-sm text-gray-500">{metric.service}</div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm text-gray-500">当前值</div>
                    <div className="text-2xl font-bold">{metric.current.toFixed(2)}%</div>
                  </div>
                  <Badge variant="outline">{metric.metric_type}</Badge>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">目标: {metric.target}%</div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${metric.current >= metric.target ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(metric.current, 100)}%` }}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={metric.trend === 'up' ? 'default' : metric.trend === 'down' ? 'destructive' : 'secondary'}>
                    趋势: {metric.trend === 'up' ? '上升' : metric.trend === 'down' ? '下降' : '稳定'}
                  </Badge>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-2">历史趋势</div>
                  <div className="flex items-end gap-1 h-16">
                    {metric.history.map((val, idx) => (
                      <div
                        key={idx}
                        className="flex-1 bg-blue-500 rounded-t"
                        style={{ height: `${val}%` }}
                      />
                    ))}
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
