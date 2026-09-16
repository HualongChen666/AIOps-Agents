'use client'

import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';
import G6, { Graph } from '@antv/g6';

interface TopologyNode {
  id: string;
  label: string;
  pagerank?: number;
}

interface TopologyEdge {
  source: string;
  target: string;
  weight?: number;
}

interface TopologyView {
  layout: string;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

// G6 built-in layout registered for each selectable option.
const G6_LAYOUT: Record<string, string> = {
  tree: 'compactBox',
  force: 'force',
  circular: 'circular',
};

export default function TopologyViewPage() {
  const [view, setView] = useState<TopologyView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layout, setLayout] = useState('tree');

  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

  // The canvas container is always mounted, so the graph's lifetime is exactly
  // the component's lifetime; this effect owns teardown to avoid leaks.
  useEffect(() => {
    return () => {
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    fetchView();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  const fetchView = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get(`/api/topology/view?layout=${layout}`);
      setView({
        layout: res.data?.layout ?? layout,
        nodes: res.data?.nodes ?? [],
        edges: res.data?.edges ?? [],
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载拓扑视图失败');
    } finally {
      setLoading(false);
    }
  };

  // Render the real graph whenever the fetched topology or layout changes.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !view) return;

    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container,
        width: container.offsetWidth || 800,
        height: container.offsetHeight || 384,
        fitView: true,
        defaultNode: {
          size: 30,
          labelCfg: { style: { fill: '#111827', fontSize: 12 } },
        },
        defaultEdge: {
          style: { stroke: '#94a3b8', lineWidth: 1 },
          labelCfg: { style: { fill: '#64748b', fontSize: 10 } },
        },
        modes: { default: ['drag-canvas', 'zoom-canvas', 'drag-node'] },
      });
    }

    const graph = graphRef.current;
    const nodes = view.nodes.map((n) => ({ id: n.id, label: n.label }));
    const edges = view.edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.weight != null ? String(e.weight) : undefined,
    }));

    graph.changeData({ nodes, edges });
    try {
      graph.updateLayout({ type: G6_LAYOUT[view.layout] ?? 'force' });
    } catch {
      // Unknown/unsupported layout: keep the graph's current layout.
    }
    graph.fitView();
  }, [view]);

  const nodeCount = view?.nodes.length ?? 0;
  const edgeCount = view?.edges.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">拓扑视图</h1>
        <div className="flex gap-2">
          <Select value={layout} onChange={(e) => setLayout(e.target.value)}>
            <option value="tree">树形布局</option>
            <option value="force">力导向布局</option>
            <option value="circular">环形布局</option>
          </Select>
          <Button onClick={fetchView}>刷新</Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <div className="text-red-800">{error}</div>
          <Button onClick={fetchView}>重试</Button>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>
            拓扑图（{nodeCount} 节点 / {edgeCount} 边）
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={containerRef}
            data-testid="topology-view-canvas"
            className="h-96 w-full bg-gray-50 rounded-lg"
          />
          {loading && <div className="text-sm text-gray-500 mt-2">加载中...</div>}
          {!loading && nodeCount === 0 && (
            <div className="text-sm text-gray-500 mt-2">暂无拓扑数据</div>
          )}
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">当前布局</label>
              <div className="text-sm">{view?.layout ?? layout}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">规模</label>
              <div className="text-sm">{nodeCount} 节点 / {edgeCount} 边</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
