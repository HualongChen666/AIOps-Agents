'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface TempoTrace {
  trace_id?: string;
  root_span_name?: string;
  root_service?: string;
  duration_ms?: number;
  span_count?: number;
  start_time?: string;
  status?: string;
  [key: string]: any;
}

interface TempoData {
  tempo_url?: string;
  tempo_version?: string;
  total_traces?: number;
  total_spans?: number;
  ingestion_rate?: number;
  retention_days?: number;
  traces?: TempoTrace[];
  query?: string;
  [key: string]: any;
}

export default function TempoPage() {
  const [query, setQuery] = useState('');
  const [timeRange, setTimeRange] = useState('1h');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: tempoData, refetch } = useQuery<TempoData>({
    queryKey: ['monitoring-tempo', query, timeRange],
    queryFn: async () => {
      if (!query.trim()) return { traces: [] };
      const resp = await api.get('/api/v1/monitoring/tempo', {
        params: { query, time_range: timeRange }
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

  if (!tempoData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Tempo追踪存储</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>TraceQL查询</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="输入TraceQL查询或Trace ID..."
                  className="flex-1"
                  onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                />
                <Button onClick={handleQuery} disabled={isQuerying}>
                  {isQuerying ? '查询中...' : '查询'}
                </Button>
              </div>
              <div className="text-sm text-gray-500">
                示例查询: {`.traceId="xxx"`}, {`{ .service = "api" }`}, {`{ .duration > 1000 }`}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Tempo追踪存储</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tempo信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">URL:</span>
              <span className="font-medium">{tempoData?.tempo_url || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{tempoData?.tempo_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总追踪数:</span>
              <span className="font-medium">{tempoData?.total_traces?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总Span数:</span>
              <span className="font-medium">{tempoData?.total_spans?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">摄入速率:</span>
              <span className="font-medium">{tempoData?.ingestion_rate?.toFixed(2) || '-'} spans/s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">保留期:</span>
              <span className="font-medium">{tempoData?.retention_days || '-'} 天</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>TraceQL查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入TraceQL查询或Trace ID..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              />
              <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
                <option value="5m">5分钟</option>
                <option value="1h">1小时</option>
                <option value="24h">24小时</option>
                <option value="7d">7天</option>
              </Select>
              <Button onClick={handleQuery} disabled={isQuerying}>
                {isQuerying ? '查询中...' : '查询'}
              </Button>
            </div>
            <div className="text-sm text-gray-500">
              示例查询: {`.traceId="xxx"`}, {`{ .service = "api" }`}, {`{ .duration > 1000 }`}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>追踪结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">Trace ID</th>
                  <th className="px-4 py-2 text-left">根服务</th>
                  <th className="px-4 py-2 text-left">根Span</th>
                  <th className="px-4 py-2 text-left">持续时间</th>
                  <th className="px-4 py-2 text-left">Span数</th>
                  <th className="px-4 py-2 text-left">开始时间</th>
                  <th className="px-4 py-2 text-left">状态</th>
                </tr>
              </thead>
              <tbody>
                {tempoData?.traces?.map((trace, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2 font-mono text-xs">{trace.trace_id}</td>
                    <td className="px-4 py-2">{trace.root_service}</td>
                    <td className="px-4 py-2">{trace.root_span_name}</td>
                    <td className="px-4 py-2">{trace.duration_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">{trace.span_count}</td>
                    <td className="px-4 py-2">
                      {trace.start_time ? new Date(trace.start_time).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        trace.status === 'success' ? 'bg-green-100 text-green-800' : 
                        trace.status === 'error' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {trace.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
