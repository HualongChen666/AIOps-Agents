'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { TrendChart } from '@/components/charts/TrendChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseOptimization {
  optimization_id: string;
  status: string;
  connection_optimizations: number;
  performance_improvement: number;
  timestamp: string;
}

interface DatabasePerformance {
  query_latency: number;
  connection_count: number;
  active_queries: number;
  cpu_usage: number;
  memory_usage: number;
  timestamp: string;
}

export default function ConnectionOptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [history, setHistory] = useState<DatabaseOptimization[]>([]);
  const [enableConnection, setEnableConnection] = useState(true);
  const [running, setRunning] = useState(false);
  const [connHistory, setConnHistory] = useState<number[]>([]);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [perfRes, optRes] = await Promise.all([
        api.get('/api/v1/database/performance'),
        api.get('/api/v1/database/optimization', { params: { limit: 20 } }),
      ]);
      setPerformance(perfRes.data);
      setConnHistory((prev) => [...prev.slice(-19), perfRes.data?.connection_count ?? 0]);
      setHistory(Array.isArray(optRes.data) ? optRes.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const optimizeConnections = async () => {
    try {
      setRunning(true);
      const res = await api.post('/api/v1/database/optimization', {
        enable_query_optimization: false,
        enable_connection_optimization: enableConnection,
        enable_cache_optimization: false,
        target_tables: null,
      });
      toast.success(`连接优化完成：${res.data.connection_optimizations} 项，性能提升 ${res.data.performance_improvement}%`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '连接优化失败');
    } finally {
      setRunning(false);
    }
  };

  const totalConnOpt = history.reduce((s, h) => s + (h.connection_optimizations || 0), 0);
  const connCount = performance?.connection_count ?? 0;
  const activeQueries = performance?.active_queries ?? 0;
  const utilization = connCount > 0 ? Math.min(100, (activeQueries / connCount) * 100) : 0;

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchAll} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">连接优化</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">连接池占用</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{connCount}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">活跃查询</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{activeQueries}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">利用率</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{utilization.toFixed(0)}%</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">累计连接优化</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{totalConnOpt}</div></CardContent></Card>
      </div>

      {connHistory.length > 1 && (
        <Card>
          <CardHeader><CardTitle>连接数趋势</CardTitle></CardHeader>
          <CardContent>
            <TrendChart data={connHistory} color="#8b5cf6" height={180} title="连接数" />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>连接池优化</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="conn">启用连接池优化</Label>
            <input id="conn" type="checkbox" checked={enableConnection} onChange={(e) => setEnableConnection(e.target.checked)} />
          </div>
          <Button onClick={optimizeConnections} disabled={running}>{running ? '执行中...' : '执行连接优化'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>连接优化历史</CardTitle></CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无连接优化记录</div>
          ) : (
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.optimization_id} className="border rounded p-3 flex items-center justify-between text-sm">
                  <span className="font-mono text-xs text-gray-500">{h.optimization_id}</span>
                  <span>连接项: {h.connection_optimizations}</span>
                  <span className="text-green-600">提升 {h.performance_improvement}%</span>
                  <Badge variant="secondary">{h.status}</Badge>
                  <span className="text-gray-400 text-xs">{new Date(h.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
