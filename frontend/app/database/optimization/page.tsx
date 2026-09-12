'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TrendChart } from '@/components/charts/TrendChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseOptimization {
  optimization_id: string;
  status: string;
  query_optimizations: number;
  connection_optimizations: number;
  cache_optimizations: number;
  performance_improvement: number;
  timestamp: string;
}

interface DatabasePerformance {
  cpu_usage: number;
  memory_usage: number;
  disk_io: number;
  network_io: number;
  query_latency: number;
  connection_count: number;
  active_queries: number;
  timestamp: string;
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  completed: 'default',
  partial: 'secondary',
  failed: 'destructive',
};

export default function OptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [optimizations, setOptimizations] = useState<DatabaseOptimization[]>([]);
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [running, setRunning] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [targetTables, setTargetTables] = useState('');
  const [config, setConfig] = useState({
    enable_query_optimization: true,
    enable_connection_optimization: true,
    enable_cache_optimization: true,
  });
  const [latencyHistory, setLatencyHistory] = useState<number[]>([]);

  const fetchPerformance = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/database/performance');
      setPerformance(res.data);
      setLatencyHistory((prev) => [...prev.slice(-19), res.data?.query_latency ?? 0]);
    } catch (err: any) {
      // A single metric probe failing must not blank the whole page.
      console.error('performance probe failed', err);
    }
  }, []);

  const fetchOptimizations = useCallback(async () => {
    const res = await api.get('/api/v1/database/optimization', {
      params: { limit: 50, ...(statusFilter ? { status_filter: statusFilter } : {}) },
    });
    setOptimizations(Array.isArray(res.data) ? res.data : []);
  }, [statusFilter]);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([fetchPerformance(), fetchOptimizations()]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, [fetchPerformance, fetchOptimizations]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const runOptimization = async () => {
    try {
      setRunning(true);
      const tables = targetTables
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await api.post('/api/v1/database/optimization', {
        ...config,
        target_tables: tables.length ? tables : null,
      });
      toast.success(
        `优化完成：查询 ${res.data.query_optimizations} 项，连接 ${res.data.connection_optimizations} 项，缓存 ${res.data.cache_optimizations} 项`,
      );
      await Promise.all([fetchOptimizations(), fetchPerformance()]);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '优化执行失败');
    } finally {
      setRunning(false);
    }
  };

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
        <h1 className="text-3xl font-bold text-gray-900">数据库优化</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">查询延迟</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(performance?.query_latency ?? 0).toFixed(1)} ms</div>
            <div className="text-xs text-gray-500 mt-1">实时往返探测</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">活跃连接</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{performance?.connection_count ?? 0}</div>
            <div className="text-xs text-gray-500 mt-1">连接池占用</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">CPU / 内存</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(performance?.cpu_usage ?? 0).toFixed(0)}% / {(performance?.memory_usage ?? 0).toFixed(0)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">主机资源</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">优化记录</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{optimizations.length}</div>
            <div className="text-xs text-gray-500 mt-1">
              累计提升 {optimizations.reduce((s, o) => s + (o.performance_improvement || 0), 0).toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {latencyHistory.length > 1 && (
        <Card>
          <CardHeader><CardTitle>查询延迟趋势</CardTitle></CardHeader>
          <CardContent>
            <TrendChart data={latencyHistory} color="#3b82f6" height={180} title="延迟 (ms)" />
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="run" className="space-y-4">
        <TabsList>
          <TabsTrigger value="run">执行优化</TabsTrigger>
          <TabsTrigger value="history">优化历史</TabsTrigger>
        </TabsList>

        <TabsContent value="run">
          <Card>
            <CardHeader><CardTitle>配置优化项</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {(
                [
                  ['enable_query_optimization', '查询优化'],
                  ['enable_connection_optimization', '连接池优化'],
                  ['enable_cache_optimization', '缓存优化'],
                ] as const
              ).map(([key, label]) => (
                <div key={key} className="flex items-center justify-between">
                  <Label htmlFor={key}>{label}</Label>
                  <input
                    id={key}
                    type="checkbox"
                    checked={config[key]}
                    onChange={(e) => setConfig({ ...config, [key]: e.target.checked })}
                  />
                </div>
              ))}
              <div>
                <Label htmlFor="tables">目标表（逗号分隔，留空表示全部）</Label>
                <Input
                  id="tables"
                  value={targetTables}
                  onChange={(e) => setTargetTables(e.target.value)}
                  placeholder="users, orders"
                  className="mt-1"
                />
              </div>
              <Button onClick={runOptimization} disabled={running}>
                {running ? '执行中...' : '开始优化'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>优化历史</CardTitle>
              <select
                className="border rounded px-2 py-1 text-sm"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">全部状态</option>
                <option value="completed">已完成</option>
                <option value="partial">部分完成</option>
                <option value="failed">失败</option>
              </select>
            </CardHeader>
            <CardContent>
              {optimizations.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无优化记录</div>
              ) : (
                <div className="space-y-3">
                  {optimizations.map((opt) => (
                    <div key={opt.optimization_id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-gray-500">{opt.optimization_id}</span>
                        <Badge variant={STATUS_VARIANT[opt.status] ?? 'secondary'}>{opt.status}</Badge>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                        <div>查询优化: {opt.query_optimizations}</div>
                        <div>连接优化: {opt.connection_optimizations}</div>
                        <div>缓存优化: {opt.cache_optimizations}</div>
                        <div className="text-green-600">提升: {opt.performance_improvement}%</div>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(opt.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
