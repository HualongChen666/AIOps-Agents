'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface TraceNode {
  id?: string;
  service?: string;
  operation?: string;
  duration_ms?: number;
  start_time?: string;
  status?: string;
  children?: TraceNode[];
  [key: string]: any;
}

interface TracingVisualizationData {
  trace_id?: string;
  total_duration_ms?: number;
  total_spans?: number;
  services?: string[];
  trace_tree?: TraceNode;
  [key: string]: any;
}

export default function TracingVisualizationPage() {
  const [traceId, setTraceId] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const { data: vizData, refetch } = useQuery<TracingVisualizationData>({
    queryKey: ['monitoring-tracing-visualization', traceId],
    queryFn: async () => {
      if (!traceId.trim()) return null;
      const resp = await api.get('/api/v1/monitoring/tracing-visualization', {
        params: { trace_id: traceId }
      });
      return resp.data;
    },
    enabled: traceId.length > 0,
    refetchInterval: false,
  });

  const handleSearch = async () => {
    setIsSearching(true);
    await refetch();
    setIsSearching(false);
  };

  const renderTraceTree = (node: TraceNode, depth: number = 0) => {
    if (!node) return null;
    const paddingLeft = depth * 20;
    return (
      <div key={node.id} style={{ paddingLeft: `${paddingLeft}px` }}>
        <div className="flex items-center gap-2 py-2 border-l-2 border-gray-300 pl-4">
          <div className={`w-3 h-3 rounded-full ${
            node.status === 'success' ? 'bg-green-500' : 
            node.status === 'error' ? 'bg-red-500' :
            'bg-yellow-500'
          }`} />
          <div className="flex-1">
            <div className="font-medium">{node.service}</div>
            <div className="text-sm text-gray-500">{node.operation}</div>
          </div>
          <div className="text-sm">{node.duration_ms?.toFixed(2)} ms</div>
        </div>
        {node.children?.map(child => renderTraceTree(child, depth + 1))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">追踪可视化</h1>
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
                {isSearching ? '搜索中...' : '可视化'}
              </Button>
            </div>
            <div className="text-sm text-gray-500">
              输入Trace ID查看追踪树形结构
            </div>
          </div>
        </CardContent>
      </Card>

      {vizData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Trace ID</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm font-mono">{vizData.trace_id}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总时长</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{vizData.total_duration_ms?.toFixed(2)} ms</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总Span数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{vizData.total_spans}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>涉及服务</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {vizData.services?.map((service, i) => (
                  <span key={i} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                    {service}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>追踪树</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-96 overflow-auto">
                {vizData.trace_tree ? renderTraceTree(vizData.trace_tree) : <p className="text-gray-500">无追踪数据</p>}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
