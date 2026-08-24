'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface QueryResult {
  timestamp?: string;
  service?: string;
  metric?: string;
  value?: number;
  labels?: Record<string, string>;
  [key: string]: any;
}

interface ObservabilityQueryData {
  query?: string;
  query_type?: string;
  time_range?: string;
  execution_time_ms?: number;
  total_results?: number;
  results?: QueryResult[];
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
      if (!query.trim()) return { results: [] };
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
                <option value="events">事件查询</option>
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
                <CardTitle className="text-sm">查询结果</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{queryResults.total_results || 0}</div>
                <div className="text-sm text-gray-500">条记录</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">执行时间</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{queryResults.execution_time_ms?.toFixed(2) || '-'} ms</div>
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
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="px-4 py-2 text-left">时间</th>
                      <th className="px-4 py-2 text-left">服务</th>
                      <th className="px-4 py-2 text-left">指标</th>
                      <th className="px-4 py-2 text-left">值</th>
                      <th className="px-4 py-2 text-left">标签</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queryResults.results?.map((result, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-4 py-2">
                          {result.timestamp ? new Date(result.timestamp).toLocaleString() : '-'}
                        </td>
                        <td className="px-4 py-2">{result.service}</td>
                        <td className="px-4 py-2">{result.metric}</td>
                        <td className="px-4 py-2">{result.value?.toFixed(2)}</td>
                        <td className="px-4 py-2">
                          <div className="flex flex-wrap gap-1">
                            {result.labels && Object.entries(result.labels).map(([key, value], j) => (
                              <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                {key}={value}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
