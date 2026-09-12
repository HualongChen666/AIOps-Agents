'use client'

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { GaugeChart } from '@/components/charts/GaugeChart';
import api from '@/lib/api';
import toast from 'react-hot-toast';

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

interface PerformanceSummary {
  total_queries_analyzed: number;
  slow_queries: number;
  index_recommendations: number;
  optimization_tasks: number;
  tables_monitored: number;
  last_analysis: string | null;
  performance_score: number;
}

interface TuningRecommendation {
  recommendation_id: string;
  category: string;
  title: string;
  description: string;
  impact: string;
  effort: string;
  priority: string;
  estimated_benefit: string;
  implementation_steps: string[];
}

interface QueryAnalysis {
  query_id: string;
  query_text: string;
  execution_time_ms: number;
  rows_affected: number;
  execution_count: number;
  avg_execution_time: number;
  optimization_score: number;
  recommendations: string[];
}

const PRIORITY_VARIANT: Record<string, 'default' | 'secondary' | 'destructive'> = {
  high: 'destructive',
  critical: 'destructive',
  medium: 'default',
  low: 'secondary',
};

export default function PerformanceTuningPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [performance, setPerformance] = useState<DatabasePerformance | null>(null);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [recommendations, setRecommendations] = useState<TuningRecommendation[]>([]);
  const [queryText, setQueryText] = useState('SELECT * FROM users WHERE email = %s');
  const [analysis, setAnalysis] = useState<QueryAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [perfRes, summaryRes, recRes] = await Promise.all([
        api.get('/api/v1/database/performance'),
        api.get('/api/v1/database-optimization/performance-summary'),
        api.get('/api/v1/database-optimization/tuning-recommendations'),
      ]);
      setPerformance(perfRes.data);
      setSummary(summaryRes.data);
      setRecommendations(Object.values(recRes.data || {}) as TuningRecommendation[]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const analyzeQuery = async () => {
    if (!queryText.trim()) {
      toast.error('请输入要分析的 SQL');
      return;
    }
    try {
      setAnalyzing(true);
      const res = await api.post('/api/v1/database-optimization/analyze-query', null, {
        params: { query_text: queryText },
      });
      setAnalysis(res.data);
      toast.success('查询分析完成');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '查询分析失败');
    } finally {
      setAnalyzing(false);
    }
  };

  const generateRecommendations = async () => {
    try {
      setGenerating(true);
      await api.post('/api/v1/database-optimization/tuning-recommendations/generate');
      const recRes = await api.get('/api/v1/database-optimization/tuning-recommendations');
      const recs = Object.values(recRes.data || {}) as TuningRecommendation[];
      setRecommendations(recs);
      toast.success(recs.length ? `生成 ${recs.length} 条调优建议` : '当前数据库状态良好，无调优建议');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || '生成调优建议失败');
    } finally {
      setGenerating(false);
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
        <h1 className="text-3xl font-bold text-gray-900">性能调优</h1>
        <Button onClick={fetchAll}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader><CardTitle>性能评分</CardTitle></CardHeader>
          <CardContent className="flex justify-center">
            <GaugeChart value={summary?.performance_score ?? 0} title="综合评分" unit="分" color="#3b82f6" />
          </CardContent>
        </Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">查询延迟</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{(performance?.query_latency ?? 0).toFixed(1)} ms</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">CPU / 内存</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{(performance?.cpu_usage ?? 0).toFixed(0)}% / {(performance?.memory_usage ?? 0).toFixed(0)}%</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-gray-600">磁盘 / 网络 IO</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{(performance?.disk_io ?? 0).toFixed(0)} / {(performance?.network_io ?? 0).toFixed(0)}</div><div className="text-xs text-gray-500 mt-1">KiB/s</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>SQL 性能分析</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="输入要分析的 SQL（仅支持只读语句）"
            rows={3}
          />
          <Button onClick={analyzeQuery} disabled={analyzing}>{analyzing ? '分析中...' : '分析查询'}</Button>
          {analysis && (
            <div className="border rounded-lg p-4 space-y-2">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                <div>执行时间: {analysis.execution_time_ms.toFixed(2)} ms</div>
                <div>影响行数: {analysis.rows_affected}</div>
                <div>执行次数: {analysis.execution_count}</div>
                <div>优化分数: {analysis.optimization_score}</div>
              </div>
              {analysis.recommendations?.length > 0 && (
                <ul className="list-disc ml-5 text-sm text-amber-700">
                  {analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>性能调优建议</CardTitle>
          <Button size="sm" onClick={generateRecommendations} disabled={generating}>
            {generating ? '生成中...' : '生成建议'}
          </Button>
        </CardHeader>
        <CardContent>
          {recommendations.length === 0 ? (
            <div className="text-gray-500 text-center py-8">暂无调优建议，点击“生成建议”基于数据库真实状态分析</div>
          ) : (
            <div className="space-y-3">
              {recommendations.map((r) => (
                <div key={r.recommendation_id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={PRIORITY_VARIANT[r.priority] ?? 'secondary'}>{r.priority}</Badge>
                    <Badge variant="secondary">{r.category}</Badge>
                    <span className="font-semibold">{r.title}</span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">{r.description}</div>
                  <div className="text-sm text-green-600 mb-2">预计收益: {r.estimated_benefit}（影响 {r.impact} / 难度 {r.effort}）</div>
                  {r.implementation_steps?.length > 0 && (
                    <ol className="list-decimal ml-5 text-sm text-gray-500">
                      {r.implementation_steps.map((s, i) => <li key={i}>{s}</li>)}
                    </ol>
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
