'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface GraphNode {
  id: string;
  label: string;
  type: 'entity' | 'concept' | 'relation';
  properties: Record<string, any>;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
}

interface GraphStats {
  nodes: number;
  edges: number;
  entity_types: Record<string, number>;
}

export default function KnowledgeGraphPage() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [newNode, setNewNode] = useState({ label: '', type: 'entity' as const, properties: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [nodesRes, edgesRes, statsRes] = await Promise.all([
        api.get('/api/ai/knowledge-graph/nodes'),
        api.get('/api/ai/knowledge-graph/edges'),
        api.get('/api/ai/knowledge-graph/stats')
      ]);
      setNodes(nodesRes.data.nodes || []);
      setEdges(edgesRes.data.edges || []);
      setStats(statsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    try {
      const res = await api.get(`/api/ai/knowledge-graph/search?q=${encodeURIComponent(query)}`);
      setNodes(res.data.nodes || []);
      setEdges(res.data.edges || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '搜索失败');
    }
  };

  const handleAddNode = async () => {
    try {
      const properties = newNode.properties ? JSON.parse(newNode.properties) : {};
      await api.post('/api/ai/knowledge-graph/nodes', {
        label: newNode.label,
        type: newNode.type,
        properties
      });
      setNewNode({ label: '', type: 'entity', properties: '' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '添加节点失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">{error}</div>
        <Button onClick={fetchData} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">知识图谱</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 图谱统计 */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>节点数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.nodes}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>边数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.edges}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>实体类型</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {Object.entries(stats.entity_types).map(([type, count]) => (
                  <div key={type} className="flex justify-between text-sm">
                    <span>{type}</span>
                    <span>{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 搜索 */}
      <Card>
        <CardHeader>
          <CardTitle>图谱搜索</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="搜索节点或关系..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch}>搜索</Button>
          </div>
        </CardContent>
      </Card>

      {/* 节点列表 */}
      <Card>
        <CardHeader>
          <CardTitle>节点列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {nodes.slice(0, 20).map((node) => (
              <div key={node.id} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold">{node.label}</h3>
                  <Badge variant="outline">{node.type}</Badge>
                </div>
                <div className="text-sm text-gray-600">
                  属性: {Object.entries(node.properties).map(([k, v]) => `${k}:${v}`).join(', ')}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 添加节点 */}
      <Card>
        <CardHeader>
          <CardTitle>添加节点</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="节点标签"
              value={newNode.label}
              onChange={(e) => setNewNode({ ...newNode, label: e.target.value })}
            />
            <select
              className="border rounded px-3 py-2"
              value={newNode.type}
              onChange={(e) => setNewNode({ ...newNode, type: e.target.value as any })}
            >
              <option value="entity">实体</option>
              <option value="concept">概念</option>
              <option value="relation">关系</option>
            </select>
            <Input
              placeholder="属性 (JSON格式)"
              value={newNode.properties}
              onChange={(e) => setNewNode({ ...newNode, properties: e.target.value })}
              className="md:col-span-2"
            />
          </div>
          <Button onClick={handleAddNode} className="mt-4">添加节点</Button>
        </CardContent>
      </Card>
    </div>
  );
}
