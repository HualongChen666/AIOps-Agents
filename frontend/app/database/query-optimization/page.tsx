'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import api from '@/lib/api';
import toast from 'react-hot-toast';

interface DatabaseQuery {
  query_id: string;
  query_text: string;
  execution_count: number;
  avg_duration_ms: number;
  last_executed: string;
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

interface TuningRecommendation {
  recommendation_id: string;
  category: string;
  title: string;
  description: string;
  priority: string;
  estimated_benefit: string;
}

export default function QueryOptimizationPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queries, setQueries] = useState<DatabaseQuery[]>([]);
  const [metrics, setMetrics] = useState<QueryMetric[]>([]);
  const [recommendations, setRecommendations] = useState<TuningRecommendation[]>([]);
  const [queryText, setQueryText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [qRes, mRes, rRes] = await Promise.all([
        api.get('/api/v1/database/queries', { params: { limit: 100, slow_only: false } }),
        api.get('/api/v1/database-optimization/query-metrics'),
        api.get('/api/v1/database-optimization/tuning-recommendations'),
      ]);
      setQueries(Array.isArray(qRes.data) ? qRes.data : []);
      setMetrics(Object.values(mRes.data || {}));
      setRecommendations(Object.values(rRes.data || {}));
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
        <h1 className="text-3xl font-bold text-gray-900">查询优化</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">记录查询</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{queries.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">已分析指标</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{metrics.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">调优建议</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{recommendations.length}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>SQL 分析器</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="SELECT * FROM users WHERE email = %s"
            rows={3}
          />
          <Button onClick={analyze} disabled={analyzing}>{analyzing ? '分析中...' : '分析查询'}</Button>
        </CardContent>
      </Card>

      <Tabs defaultValue="queries" className="space-y-4">
        <TabsList>
          <TabsTrigger value="queries">查询列表</TabsTrigger>
          <TabsTrigger value="metrics">分析指标</TabsTrigger>
          <TabsTrigger value="recs">调优建议</TabsTrigger>
        </TabsList>

        <TabsContent value="queries">
          <Card>
            <CardHeader><CardTitle>查询记录</CardTitle></CardHeader>
            <CardContent>
              {queries.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无查询记录</div>
              ) : (
                <div className="space-y-2">
                  {queries.map((q) => (
                    <div key={q.query_id} className="border rounded p-3">
                      <div className="font-mono text-sm bg-gray-50 p-2 rounded">{q.query_text}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        表: {q.table_name} | 执行 {q.execution_count} 次 | 平均 {q.avg_duration_ms.toFixed(1)}ms
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics">
          <Card>
            <CardHeader><CardTitle>查询性能指标</CardTitle></CardHeader>
            <CardContent>
              {metrics.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无指标，先分析 SQL</div>
              ) : (
                <div className="space-y-2">
                  {metrics.map((m) => (
                    <div key={m.query_id} className="border rounded p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs text-gray-500">{m.query_id}</span>
                        <Badge variant={m.optimization_score < 60 ? 'destructive' : 'secondary'}>分数 {m.optimization_score}</Badge>
                      </div>
                      <div className="font-mono text-sm bg-gray-50 p-2 rounded">{m.query_text}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        执行 {m.execution_count} 次 | 平均 {m.avg_execution_time.toFixed(2)}ms
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="recs">
          <Card>
            <CardHeader><CardTitle>性能调优建议</CardTitle></CardHeader>
            <CardContent>
              {recommendations.length === 0 ? (
                <div className="text-gray-500 text-center py-8">暂无调优建议</div>
              ) : (
                <div className="space-y-3">
                  {recommendations.map((r) => (
                    <div key={r.recommendation_id} className="border rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary">{r.category}</Badge>
                        <span className="font-semibold">{r.title}</span>
                      </div>
                      <div className="text-sm text-gray-600">{r.description}</div>
                      <div className="text-sm text-green-600 mt-1">预计收益: {r.estimated_benefit}</div>
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
