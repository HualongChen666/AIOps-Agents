'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

// The backend answers per `query_type`:
//   metrics → `data` is { cpu: [...], memory: [...], network: [...] }
//   logs    → `data` is an array of log entries (Loki)
//   traces  → `data` is an array of traces (Tempo)
interface ObservabilityQueryData {
  query?: string;
  query_type?: string;
  time_range?: string;
  data?: Record<string, number[]> | unknown[];
  [key: string]: any;
}

export default function ObservabilityQueryPage() {
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState('metrics');
  const [timeRange, setTimeRange] = useState('1h');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: queryResults, refetch } = useQuery<ObservabilityQueryData>({
    queryKey: ['monitoring-observability-query', query, queryType, timeRange],
    queryFn: async () => {
      if (!query.trim()) return { data: [] };
      const resp = await api.get('/api/v1/monitoring/observability-query', {
        params: { query, query_type: queryType, time_range: timeRange }
      });
      return resp.data;
    },
    enabled: query.length > 0,
    refetchInterval: false,
  });

  const handleQuery = async () => {
    setIsQuerying(true);
    await refetch();
    setIsQuerying(false);
  };

  const isMetricSeries = queryResults?.data && !Array.isArray(queryResults.data);
  const metricSeries = isMetricSeries
    ? Object.entries(queryResults!.data as Record<string, number[]>)
    : [];
  const listResults = Array.isArray(queryResults?.data) ? (queryResults!.data as any[]) : [];
  const resultCount = isMetricSeries ? metricSeries.length : listResults.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">可观测性查询</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>查询构建器</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入查询条件..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              />
              <Button onClick={handleQuery} disabled={isQuerying}>
                {isQuerying ? '查询中...' : '查询'}
              </Button>
            </div>
            <div className="flex gap-2">
              <Select value={queryType} onChange={(e) => setQueryType(e.target.value)}>
                <option value="metrics">指标查询</option>
                <option value="logs">日志查询</option>
                <option value="traces">追踪查询</option>
              </Select>
              <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
                <option value="5m">5分钟</option>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
              </Select>
            </div>
            <div className="text-sm text-gray-500">
              示例查询: service="api" AND metric="cpu_usage", level="error", trace_id="xxx"
            </div>
          </div>
        </CardContent>
      </Card>

      {queryResults && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">结果数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{resultCount}</div>
                <div className="text-sm text-gray-500">{isMetricSeries ? '个指标序列' : '条记录'}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">时间范围</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{queryResults.time_range || '-'}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">查询类型</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">{queryResults.query_type || '-'}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>查询结果</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-auto">
                {isMetricSeries ? (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left">指标</th>
                        <th className="px-4 py-2 text-left">最新值</th>
                        <th className="px-4 py-2 text-left">样本数</th>
                        <th className="px-4 py-2 text-left">序列</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metricSeries.map(([metric, values]) => (
                        <tr key={metric} className="border-t">
                          <td className="px-4 py-2">{metric}</td>
                          <td className="px-4 py-2">
                            {values.length ? values[values.length - 1].toFixed(2) : '-'}
                          </td>
                          <td className="px-4 py-2">{values.length}</td>
                          <td className="px-4 py-2 break-all text-xs">{values.map(v => v.toFixed(1)).join(', ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left">#</th>
                        <th className="px-4 py-2 text-left">内容</th>
                      </tr>
                    </thead>
                    <tbody>
                      {listResults.map((result, i) => (
                        <tr key={i} className="border-t">
                          <td className="px-4 py-2">{i + 1}</td>
                          <td className="px-4 py-2 break-all text-xs font-mono">
                            {typeof result === 'string' ? result : JSON.stringify(result)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
