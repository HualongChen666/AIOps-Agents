'use client'

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';
import G6, { Graph } from '@antv/g6';

interface VisualizationConfig {
  id: string;
  name: string;
  node_color: string;
  edge_color: string;
  show_labels: boolean;
  show_metrics: boolean;
  auto_refresh: boolean;
}

interface GraphNode {
  id: string;
  label: string;
  pagerank?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  weight?: number;
}

export default function TopologyVisualizationPage() {
  const [config, setConfig] = useState<VisualizationConfig | null>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    fetchConfig();
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

  const fetchConfig = async () => {
    try {
      const res = await api.get('/api/topology/visualization');
      setConfig(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载可视化配置失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchGraph = async () => {
    try {
      const res = await api.get('/api/topology/topology-graph');
      setNodes(res.data?.graph?.nodes ?? []);
      setEdges(res.data?.graph?.edges ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载拓扑图失败');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    try {
      await api.put('/api/topology/visualization', config);
      setError(null);
      await fetchConfig();
      alert('配置已保存');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '保存配置失败');
    }
  };

  // Draw the real graph, styled from the persisted visualization configuration.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const nodeColor = config?.node_color || '#3b82f6';
    const edgeColor = config?.edge_color || '#94a3b8';
    const showLabels = config?.show_labels !== false;

    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container,
        width: container.offsetWidth || 800,
        height: container.offsetHeight || 384,
        fitView: true,
        defaultNode: {
          size: 30,
          style: { fill: nodeColor, stroke: '#fff', lineWidth: 2 },
          labelCfg: { style: { fill: '#111827', fontSize: 12 } },
        },
        defaultEdge: {
          style: { stroke: edgeColor, lineWidth: 1 },
        },
        modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
      });
    }

    const graph = graphRef.current;
    graph.changeData({
      nodes: nodes.map((n) => ({
        id: n.id,
        label: showLabels ? n.label : '',
        style: { fill: nodeColor },
      })),
      edges: edges.map((e) => ({ source: e.source, target: e.target })),
    });
    graph.fitView();
  }, [nodes, edges, config]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑可视化</h1>
        <Button onClick={() => { fetchConfig(); fetchGraph(); }}>刷新</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800">{error}</div>
        </div>
      )}

      {config && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>可视化配置</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span>显示标签</span>
                  <Badge variant={config.show_labels ? 'default' : 'secondary'}>
                    {config.show_labels ? '是' : '否'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>显示指标</span>
                  <Badge variant={config.show_metrics ? 'default' : 'secondary'}>
                    {config.show_metrics ? '是' : '否'}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span>自动刷新</span>
                  <Badge variant={config.auto_refresh ? 'default' : 'secondary'}>
                    {config.auto_refresh ? '是' : '否'}
                  </Badge>
                </div>
                <Button onClick={handleSave}>保存配置</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                拓扑图（{nodes.length} 节点 / {edges.length} 边）
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                ref={containerRef}
                data-testid="topology-visualization-canvas"
                className="h-96 w-full bg-gray-50 rounded-lg"
              />
              {nodes.length === 0 && (
                <div className="text-sm text-gray-500 mt-2">暂无拓扑数据</div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
