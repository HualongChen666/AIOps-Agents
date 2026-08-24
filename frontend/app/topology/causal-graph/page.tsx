'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CausalNode {
  id: string;
  name: string;
  type: 'event' | 'metric' | 'log';
  timestamp: string;
}

interface CausalEdge {
  source: string;
  target: string;
  confidence: number;
  delay: number;
}

interface CausalGraph {
  nodes: CausalNode[];
  edges: CausalEdge[];
}

export default function CausalGraphPage() {
  const [graph, setGraph] = useState<CausalGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGraph();
  }, []);

  const fetchGraph = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/causal-graph');
      setGraph(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载因果图失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
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
              <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-gray-500">因果图可视化区域</div>
              </div>
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
                    <div className="text-sm text-gray-500">{new Date(node.timestamp).toLocaleString()}</div>
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
                      <Badge variant="secondary">置信度: {(edge.confidence * 100).toFixed(1)}%</Badge>
                      <Badge variant="outline">延迟: {edge.delay}ms</Badge>
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
