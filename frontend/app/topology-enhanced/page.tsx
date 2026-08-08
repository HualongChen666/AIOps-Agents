'use client'

import { useState, useEffect, useRef } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import G6, { Graph } from '@antv/g6';

interface ServiceNode {
  id: string;
  name: string;
  type: string;
  status: 'healthy' | 'warning' | 'critical';
  requests: number;
}

interface Edge {
  source: string;
  target: string;
  traffic: number;
  latency: number;
}

export default function TopologyEnhancedPage() {
  const [selectedView, setSelectedView] = useState('traffic');
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [nodes, setNodes] = useState<ServiceNode[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadTopology = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/v1/topologies/full-link');
      const data = response.data || {};

      const mappedNodes = (data.nodes || []).map((node: { id: string; label?: string; pagerank?: number; status?: string }) => ({
        id: node.id,
        name: node.label || node.id,
        type: 'service',
        status: (node.status || 'healthy') as ServiceNode['status'],
        requests: Math.round((node.pagerank ?? 1) * 1000),
      }));

      const mappedEdges = (data.edges || []).map((edge: { source: string; target: string; weight?: number; latency?: number }) => ({
        source: edge.source,
        target: edge.target,
        traffic: edge.weight ?? 0,
        latency: edge.latency ?? 0,
      }));

      setNodes(mappedNodes);
      setEdges(mappedEdges);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || '拓扑加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopology();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!graphRef.current) {
      graphRef.current = new G6.Graph({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
        fitView: true,
        defaultNode: {
          size: 30,
          style: {
            fill: '#1f4b99',
            stroke: '#fff',
            lineWidth: 2,
          },
          labelCfg: {
            style: { fill: '#1f2937', fontSize: 12 },
          },
        },
        defaultEdge: {
          style: { stroke: '#9ca3af', lineWidth: 1 },
          labelCfg: { style: { fill: '#6b7280', fontSize: 10 } },
        },
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
        },
      });
      graphRef.current.on('node:click', (e: any) => {
        const model = e.item?.getModel?.();
        if (model?.id) setSelectedService(model.id);
      });
    }
    const graph = graphRef.current;
    const graphNodes = nodes.map((n) => ({
      id: n.id,
      label: n.name,
      style: {
        fill:
          n.status === 'critical'
            ? '#ef4444'
            : n.status === 'warning'
              ? '#f59e0b'
              : '#22c55e',
      },
    }));
    const graphEdges = edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: String(e.traffic ?? ''),
    }));
    graph.changeData({ nodes: graphNodes, edges: graphEdges });
    graph.fitView();
  }, [nodes, edges]);

  useEffect(() => {
    return () => {
      graphRef.current?.destroy();
      graphRef.current = null;
    };
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'critical':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedService) || null;
  const totalTraffic = edges.reduce((sum, e) => sum + e.traffic, 0);
  const avgLatency =
    edges.length > 0
      ? Math.round(edges.reduce((sum, e) => sum + e.latency, 0) / edges.length)
      : '—';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">服务地图增强</h1>
        <div className="flex gap-2">
          <Select value={selectedView} onChange={(e) => setSelectedView(e.target.value)}>
            <option value="traffic">流量视图</option>
            <option value="latency">延迟视图</option>
            <option value="error">错误视图</option>
          </Select>
          <Button onClick={loadTopology} disabled={loading}>
            刷新
          </Button>
        </div>
      </div>

      {/* 服务拓扑图 */}
      <Card>
        <CardHeader>
          <CardTitle>服务拓扑图</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={containerRef}
            className="h-96 bg-gray-50 rounded-lg relative"
          >
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-gray-500">加载中...</p>
              </div>
            )}
            {error && !loading && (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-red-500">{error}</p>
              </div>
            )}
            {!loading && !error && nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-gray-500">暂无拓扑数据</p>
              </div>
            )}
            <div className="absolute top-4 right-4 space-x-2">
              <Badge className="bg-green-100 text-green-800">健康</Badge>
              <Badge className="bg-yellow-100 text-yellow-800">警告</Badge>
              <Badge className="bg-red-100 text-red-800">严重</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 服务详情 */}
      {selectedNode && (
        <Card>
          <CardHeader>
            <CardTitle>服务详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">服务名称</div>
                <div className="text-2xl font-bold">{selectedNode.name}</div>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">状态</div>
                <Badge className={getStatusColor(selectedNode.status)}>
                  {selectedNode.status === 'healthy' ? '健康' : selectedNode.status === 'warning' ? '警告' : '严重'}
                </Badge>
              </div>
              <div className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">请求量</div>
                <div className="text-2xl font-bold">{selectedNode.requests}/s</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 服务列表 */}
      <Card>
        <CardHeader>
          <CardTitle>服务列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {nodes.map((node) => (
              <div
                key={node.id}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                onClick={() => setSelectedService(node.id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{node.name}</h3>
                      <Badge className={getStatusColor(node.status)}>
                        {node.status === 'healthy' ? '健康' : node.status === 'warning' ? '警告' : '严重'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">{node.type}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm">请求: {node.requests}/s</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 流量统计 */}
      <Card>
        <CardHeader>
          <CardTitle>流量统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">总流量</div>
              <div className="text-2xl font-bold">{totalTraffic}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">平均延迟</div>
              <div className="text-2xl font-bold">{avgLatency}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">错误率</div>
              <div className="text-2xl font-bold">—</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">P99延迟</div>
              <div className="text-2xl font-bold">—</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
