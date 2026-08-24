'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SLOMonitor {
  id: string;
  name: string;
  service: string;
  current_value: number;
  target: number;
  remaining_budget: number;
  error_budget_consumed: number;
  status: 'healthy' | 'warning' | 'critical';
  last_check: string;
}

export default function SLOMonitoringPage() {
  const [monitors, setMonitors] = useState<SLOMonitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMonitors();
    const interval = setInterval(fetchMonitors, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMonitors = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/monitoring');
      setMonitors(res.data.monitors || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载监控数据失败');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchMonitors} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO监控</h1>
        <Button onClick={fetchMonitors}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {monitors.map((monitor) => (
          <Card key={monitor.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{monitor.name}</CardTitle>
                <Badge className={getStatusColor(monitor.status)}>
                  {monitor.status}
                </Badge>
              </div>
              <div className="text-sm text-gray-500">{monitor.service}</div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">当前值</span>
                    <span className="font-semibold">{monitor.current_value.toFixed(2)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${monitor.status === 'healthy' ? 'bg-green-500' : monitor.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'}`}
                      style={{ width: `${monitor.current_value}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">目标: {monitor.target}%</div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-500">剩余预算</div>
                    <div className="text-lg font-semibold">{monitor.remaining_budget.toFixed(2)}%</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">已消耗</div>
                    <div className="text-lg font-semibold text-red-600">{monitor.error_budget_consumed.toFixed(2)}%</div>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  最后检查: {new Date(monitor.last_check).toLocaleString()}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
