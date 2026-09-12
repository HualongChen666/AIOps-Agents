'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseQuery {
  query_id: string;
  query_text: string;
  execution_count: number;
  avg_duration_ms: number;
  last_executed: string;
  database: string;
  table_name: string;
}

interface DatabaseOptimization {
  optimization_id: string;
  status: string;
  cache_optimizations: number;
  performance_improvement: number;
  timestamp: string;
}

export default function QueryCachePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queries, setQueries] = useState<DatabaseQuery[]>([]);
  const [history, setHistory] = useState<DatabaseOptimization[]>([]);
  const [enableCache, setEnableCache] = useState(true);
  const [running, setRunning] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [qRes, oRes] = await Promise.all([
        api.get('/api/v1/database/queries', { params: { limit: 50, slow_only: false } }),
        api.get('/api/v1/database/optimization', { params: { limit: 20 } }),
      ]);
      setQueries(Array.isArray(qRes.data) ? qRes.data : []);
      setHistory(Array.isArray(oRes.data) ? oRes.data : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const enableQueryCache = async () => {
    try {
      setRunning(true);
      const res = await api.post('/api/v1/database/optimization', {
        enable_query_optimization: true,
        enable_connection_optimization: false,
        enable_cache_optimization: enableCache,
        target_tables: null,
      });
      toast.success(`查询缓存已配置：缓存优化 ${res.data.cache_optimizations} 项`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '配置查询缓存失败');
    } finally {
      setRunning(false);
    }
  };

  const repeatable = queries.filter((q) => q.execution_count > 1);
  const totalExec = queries.reduce((s, q) => s + (q.execution_count || 0), 0);
  const cacheCandidates = repeatable.length;

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
        <h1 className="text-3xl font-bold text-gray-900">查询缓存</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已记录查询</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{queries.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">可缓存（重复执行）</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{cacheCandidates}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">总执行次数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{totalExec}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>查询缓存开关</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="qcache">启用查询结果缓存</Label>
            <input id="qcache" type="checkbox" checked={enableCache} onChange={(e) => setEnableCache(e.target.checked)} />
          </div>
          <Button onClick={enableQueryCache} disabled={running}>{running ? '配置中...' : '应用缓存配置'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>候选缓存查询</CardTitle></CardHeader>
        <CardContent>
          {cacheCandidates === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无重复执行的查询，无需缓存</div>
          ) : (
            <div className="space-y-2">
              {repeatable.map((q) => (
                <div key={q.query_id} className="border rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs text-gray-500">{q.query_id}</span>
                    <Badge variant="secondary">执行 {q.execution_count} 次</Badge>
                  </div>
                  <div className="font-mono text-sm bg-gray-50 p-2 rounded">{q.query_text}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    表: {q.table_name} | 平均耗时: {q.avg_duration_ms.toFixed(1)}ms | 最后执行: {new Date(q.last_executed).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>缓存优化记录</CardTitle></CardHeader>
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
