'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

// The backend builds a real service graph from Tempo spans: `nodes` are the
// distinct services, `edges` carry the parent→child call plus its latency.
interface TraceGraphNode {
  id: string;
  label?: string;
  type?: string;
}

interface TraceGraphEdge {
  source: string;
  target: string;
  label?: string;
  latency_ms?: number;
}

interface TracingVisualizationData {
  trace_id?: string;
  total_duration_ms?: number;
  total_spans?: number;
  services?: string[];
  nodes?: TraceGraphNode[];
  edges?: TraceGraphEdge[];
  [key: string]: any;
}

interface TraceTreeNode {
  id: string;
  service: string;
  operation?: string;
  duration_ms?: number;
  children: TraceTreeNode[];
}

function buildTraceTree(nodes: TraceGraphNode[] | undefined, edges: TraceGraphEdge[] | undefined): TraceTreeNode | null {
  if (!nodes || nodes.length === 0) return null;
  const edgeList = edges || [];
  const childrenBySource: Record<string, TraceGraphEdge[]> = {};
  const hasParent = new Set<string>();
  for (const edge of edgeList) {
    (childrenBySource[edge.source] ||= []).push(edge);
    hasParent.add(edge.target);
  }

  const labelOf = (id: string) => nodes.find(n => n.id === id)?.label || id;

  const build = (id: string, visited: Set<string>): TraceTreeNode => {
    visited.add(id);
    const children = (childrenBySource[id] || [])
      .filter(edge => !visited.has(edge.target))
      .map(edge => ({
        ...build(edge.target, visited),
        operation: edge.label,
        duration_ms: edge.latency_ms,
      }));
    return { id, service: labelOf(id), children };
  };

  const root = nodes.find(n => !hasParent.has(n.id)) || nodes[0];
  return build(root.id, new Set());
}

function TraceNodeRow({ node, depth = 0 }: { node: TraceTreeNode; depth?: number }) {
  return (
    <div style={{ paddingLeft: `${depth * 20}px` }}>
      <div className="flex items-center gap-2 py-2 border-l-2 border-gray-300 pl-4">
        <div className="w-3 h-3 rounded-full bg-blue-500" />
        <div className="flex-1">
          <div className="font-medium">{node.service}</div>
          <div className="text-sm text-gray-500">{node.operation || '-'}</div>
        </div>
        <div className="text-sm">
          {typeof node.duration_ms === 'number' ? `${node.duration_ms.toFixed(2)} ms` : '-'}
        </div>
      </div>
      {node.children.map(child => (
        <TraceNodeRow key={`${child.id}-${child.operation ?? ''}`} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export default function TracingVisualizationPage() {
  const [traceId, setTraceId] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const { data: vizData, refetch } = useQuery<TracingVisualizationData | null>({
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

  const traceTree = vizData ? buildTraceTree(vizData.nodes, vizData.edges) : null;

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
                <div className="text-sm font-mono break-all">{vizData.trace_id}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总时长</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {typeof vizData.total_duration_ms === 'number' ? `${vizData.total_duration_ms.toFixed(2)} ms` : '-'}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">总Span数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{vizData.total_spans ?? '-'}</div>
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
                {traceTree ? <TraceNodeRow node={traceTree} /> : <p className="text-gray-500">无追踪数据</p>}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
