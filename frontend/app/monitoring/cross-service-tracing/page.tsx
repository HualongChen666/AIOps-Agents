'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface TraceSpan {
  trace_id?: string;
  span_id?: string;
  service?: string;
  operation?: string;
  start_time?: string;
  duration_ms?: number;
  status?: string;
  parent_span_id?: string;
  [key: string]: any;
}

interface CrossServiceTracingData {
  total_traces?: number;
  total_spans?: number;
  avg_trace_duration?: number;
  error_rate?: number;
  traces?: TraceSpan[];
  time_range?: string;
  [key: string]: any;
}

export default function CrossServiceTracingPage() {
  const [traceId, setTraceId] = useState('');
  const [timeRange, setTimeRange] = useState('1h');
  const [isSearching, setIsSearching] = useState(false);

  const { data: tracingData, refetch } = useQuery<CrossServiceTracingData>({
    queryKey: ['monitoring-cross-service-tracing', traceId, timeRange],
    queryFn: async () => {
      const params: any = { time_range: timeRange };
      if (traceId) params.trace_id = traceId;
      const resp = await api.get('/api/v1/monitoring/cross-service-tracing', { params });
      return resp.data;
    },
    refetchInterval: false,
  });

  const handleSearch = async () => {
    setIsSearching(true);
    await refetch();
    setIsSearching(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">跨服务追踪</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={() => refetch()}>刷新</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>追踪搜索</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={traceId}
                onChange={(e) => setTraceId(e.target.value)}
                placeholder="输入Trace ID..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} disabled={isSearching}>
                {isSearching ? '搜索中...' : '搜索'}
              </Button>
            </div>
            <div className="text-sm text-gray-500">
              输入Trace ID查看完整的跨服务调用链
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总追踪数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tracingData?.total_traces?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总Span数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tracingData?.total_spans?.toLocaleString() || '-'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均追踪时长</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{tracingData?.avg_trace_duration?.toFixed(2) || '-'} ms</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">错误率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(tracingData?.error_rate || 0).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>追踪详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">Trace ID</th>
                  <th className="px-4 py-2 text-left">Span ID</th>
                  <th className="px-4 py-2 text-left">服务</th>
                  <th className="px-4 py-2 text-left">操作</th>
                  <th className="px-4 py-2 text-left">开始时间</th>
                  <th className="px-4 py-2 text-left">持续时间</th>
                  <th className="px-4 py-2 text-left">状态</th>
                  <th className="px-4 py-2 text-left">父Span</th>
                </tr>
              </thead>
              <tbody>
                {tracingData?.traces?.map((trace, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2 font-mono text-xs">{trace.trace_id}</td>
                    <td className="px-4 py-2 font-mono text-xs">{trace.span_id}</td>
                    <td className="px-4 py-2">{trace.service}</td>
                    <td className="px-4 py-2">{trace.operation}</td>
                    <td className="px-4 py-2">
                      {trace.start_time ? new Date(trace.start_time).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-2">{trace.duration_ms?.toFixed(2)} ms</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        trace.status === 'success' ? 'bg-green-100 text-green-800' : 
                        trace.status === 'error' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {trace.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{trace.parent_span_id || '-'}</td>
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
