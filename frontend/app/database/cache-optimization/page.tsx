'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseOptimization {
  optimization_id: string;
  status: string;
  cache_optimizations: number;
  performance_improvement: number;
  timestamp: string;
}

interface DatabasePerformance {
  query_latency: number;
  connection_count: number;
  cpu_usage: number;
  memory_usage: number;
  timestamp: string;
}

export default function CacheOptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [history, setHistory] = useState<DatabaseOptimization[]>([]);
  const [enableCache, setEnableCache] = useState(true);
  const [enableQuery, setEnableQuery] = useState(true);
  const [running, setRunning] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [perfRes, optRes] = await Promise.all([
        api.get('/api/v1/database/performance'),
        api.get('/api/v1/database/optimization', { params: { limit: 20 } }),
      ]);
      setPerformance(perfRes.data);
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

  const optimizeCache = async () => {
    try {
      setRunning(true);
      const res = await api.post('/api/v1/database/optimization', {
        enable_query_optimization: enableQuery,
        enable_connection_optimization: false,
        enable_cache_optimization: enableCache,
        target_tables: null,
      });
      toast.success(`缓存优化完成：${res.data.cache_optimizations} 项，性能提升 ${res.data.performance_improvement}%`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '缓存优化失败');
    } finally {
      setRunning(false);
    }
  };

  const cacheOptimizations = history.reduce((s, h) => s + (h.cache_optimizations || 0), 0);
  const latency = performance?.query_latency ?? 0;
  // A lower query latency implies a healthier cache; surface it as a 0-100 gauge.
  const cacheHealth = Math.max(0, Math.min(100, 100 - latency));

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
        <h1 className="text-3xl font-bold text-gray-900">缓存优化</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle>缓存健康度</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={cacheHealth} title="缓存效率" unit="分" color="#10b981" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">当前查询延迟</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latency.toFixed(1)} ms</div>
            <div className="text-xs text-gray-500 mt-1">{latency > 20 ? '延迟偏高，建议启用缓存' : '延迟正常'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">累计缓存优化</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cacheOptimizations}</div>
            <div className="text-xs text-gray-500 mt-1">来自 {history.length} 次优化记录</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>缓存优化配置</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="cache">启用缓存优化</Label>
            <input id="cache" type="checkbox" checked={enableCache} onChange={(e) => setEnableCache(e.target.checked)} />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="query">同时优化查询</Label>
            <input id="query" type="checkbox" checked={enableQuery} onChange={(e) => setEnableQuery(e.target.checked)} />
          </div>
          <Button onClick={optimizeCache} disabled={running}>{running ? '执行中...' : '执行缓存优化'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>缓存优化历史</CardTitle></CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无缓存优化记录</div>
          ) : (
            <div className="space-y-2">
              {history.map((h) => (
                <div key={h.optimization_id} className="border rounded p-3 flex items-center justify-between text-sm">
                  <span className="font-mono text-xs text-gray-500">{h.optimization_id}</span>
                  <span>缓存项: {h.cache_optimizations}</span>
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
