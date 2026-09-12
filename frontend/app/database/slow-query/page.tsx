'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
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

interface QueryMetric {
  query_id: string;
  query_text: string;
  execution_time_ms: number;
  execution_count: number;
  avg_execution_time: number;
  optimization_score: number;
  recommendations: string[];
}

export default function SlowQueryPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [slowQueries, setSlowQueries] = useState<DatabaseQuery[]>([]);
  const [metrics, setMetrics] = useState<QueryMetric[]>([]);
  const [threshold, setThreshold] = useState(100);
  const [queryText, setQueryText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [qRes, mRes] = await Promise.all([
        api.get('/api/v1/database/queries', { params: { limit: 100, slow_only: true } }),
        api.get('/api/v1/database-optimization/query-metrics'),
      ]);
      setSlowQueries(Array.isArray(qRes.data) ? qRes.data : []);
      setMetrics(Object.values(mRes.data || {}));
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const analyze = async () => {
    if (!queryText.trim()) {
      toast.error('请输入要分析的 SQL');
      return;
    }
    try {
      setAnalyzing(true);
      const res = await api.post('/api/v1/database-optimization/analyze-query', null, {
        params: { query_text: queryText },
      });
      toast.success(`分析完成，优化分数 ${res.data.optimization_score}`);
      await fetchAll();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const filtered = slowQueries.filter((q) => q.avg_duration_ms >= threshold);

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
        <h1 className="text-3xl font-bold text-gray-900">慢查询分析</h1>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600">
            阈值(ms):
            <input
              type="number"
              className="border rounded px-2 py-1 ml-2 w-24"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value) || 0)}
            />
          </label>
          <Button onClick={fetchAll}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">慢查询总数</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-red-600">{slowQueries.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">高于阈值</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{filtered.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已分析指标</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics.length}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>SQL 分析器</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="粘贴慢查询 SQL，使用真实 EXPLAIN 分析执行计划"
            rows={3}
          />
          <Button onClick={analyze} disabled={analyzing}>{analyzing ? '分析中...' : '分析'}</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>慢查询列表</CardTitle></CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无超过 {threshold}ms 的慢查询</div>
          ) : (
            <div className="space-y-3">
              {filtered.map((q) => (
                <div key={q.query_id} className="border rounded-lg p-4 bg-red-50">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="destructive">慢查询</Badge>
                    <div className="text-sm text-gray-500">
                      执行 {q.execution_count} 次 | 平均 {q.avg_duration_ms.toFixed(1)}ms
                    </div>
                  </div>
                  <div className="font-mono text-sm bg-white p-2 rounded">{q.query_text}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    数据库: {q.database} | 表: {q.table_name}
                  </div>
                  <Button size="sm" variant="secondary" className="mt-2" onClick={() => setQueryText(q.query_text)}>
                    载入分析
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>已分析查询指标</CardTitle></CardHeader>
        <CardContent>
          {metrics.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无查询指标，先在上方分析 SQL</div>
          ) : (
            <div className="space-y-2">
              {metrics.map((m) => (
                <div key={m.query_id} className="border rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs text-gray-500">{m.query_id}</span>
                    <Badge variant={m.optimization_score < 60 ? 'destructive' : 'secondary'}>
                      分数 {m.optimization_score}
                    </Badge>
                  </div>
                  <div className="font-mono text-sm bg-gray-50 p-2 rounded">{m.query_text}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    执行 {m.execution_count} 次 | 平均 {m.avg_execution_time.toFixed(2)}ms
                  </div>
                  {m.recommendations?.length > 0 && (
                    <ul className="list-disc ml-5 text-sm text-amber-700 mt-1">
                      {m.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
