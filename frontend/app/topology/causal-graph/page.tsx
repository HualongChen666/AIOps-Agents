'use client'

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import G6, { Graph } from '@antv/g6';

interface CausalNode {
  id: string;
  name: string;
  type: string;
}

interface CausalEdge {
  source: string;
  target: string;
  causal_strength: number;
  type?: string;
}

interface CausalGraph {
  nodes: CausalNode[];
  edges: CausalEdge[];
  metrics?: { total_nodes: number; total_edges: number; avg_causal_strength: number };
}

export default function CausalGraphPage() {
  const [graph, setGraph] = useState<CausalGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    fetchGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, []);

  const fetchGraph = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/topology/causal-graph');
      setGraph({
        nodes: res.data?.nodes ?? [],
        edges: res.data?.edges ?? [],
        metrics: res.data?.metrics,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载因果图失败');
    } finally {
      setLoading(false);
    }
  };

  // Draw the real causal graph returned by the backend.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !graph) return;

    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container,
        width: container.offsetWidth || 800,
        height: container.offsetHeight || 384,
        fitView: true,
        layout: { type: 'dagre', rankdir: 'LR' },
        defaultNode: {
          size: 30,
          style: { fill: '#6366f1', stroke: '#fff', lineWidth: 2 },
          labelCfg: { style: { fill: '#111827', fontSize: 12 } },
        },
        defaultEdge: {
          style: { stroke: '#94a3b8', lineWidth: 1, endArrow: true },
        },
        modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
      });
    }

    const g = graphRef.current;
    g.changeData({
      nodes: graph.nodes.map((n) => ({ id: n.id, label: n.name })),
      edges: graph.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: `${Math.round((e.causal_strength ?? 0) * 100)}%`,
      })),
    });
    g.fitView();
  }, [graph]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error && !graph) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchGraph} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">因果图</h1>
        <Button onClick={fetchGraph}>刷新</Button>
      </div>

      {graph && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>因果图可视化</CardTitle>
            </CardHeader>
            <CardContent>
              <div
                ref={containerRef}
                data-testid="causal-graph-canvas"
                className="h-96 w-full bg-gray-50 rounded-lg"
              />
              {graph.nodes.length === 0 && (
                <div className="text-sm text-gray-500 mt-2">暂无因果关系数据</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>节点 ({graph.nodes.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {graph.nodes.map((node) => (
                  <div key={node.id} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{node.name}</span>
                      <Badge variant="outline">{node.type}</Badge>
                    </div>
                    <div className="text-sm text-gray-500">{node.id}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>因果关系 ({graph.edges.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {graph.edges.map((edge, idx) => (
                  <div key={idx} className="border rounded-lg p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{edge.source}</span>
                      <span className="text-gray-400">→</span>
                      <span className="font-semibold">{edge.target}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">
                        因果强度: {(Number(edge.causal_strength) * 100).toFixed(1)}%
                      </Badge>
                      {edge.type && <Badge variant="outline">{edge.type}</Badge>}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
