'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface WorkflowVisualization {
  id: string;
  workflow_id: string;
  workflow_name: string;
  nodes: Array<{
    id: string;
    name: string;
    type: string;
    position: { x: number; y: number };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    label?: string;
  }>;
  layout: 'hierarchical' | 'force' | 'circular';
  created_at: string;
}

interface VisualizationConfig {
  id: string;
  workflow_id: string;
  theme: 'light' | 'dark';
  show_labels: boolean;
  node_size: number;
  edge_width: number;
}

export default function LangGraphVisualizerPage() {
  const [visualizations, setVisualizations] = useState<WorkflowVisualization[]>([]);
  const [configs, setConfigs] = useState<VisualizationConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedViz, setSelectedViz] = useState<WorkflowVisualization | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [vizRes, configRes] = await Promise.all([
        api.get('/api/ai/langgraph-visualizer/visualizations'),
        api.get('/api/ai/langgraph-visualizer/configs')
      ]);
      setVisualizations(vizRes.data.visualizations || []);
      setConfigs(configRes.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateVisualization = async (workflowId: string) => {
    try {
      await api.post('/api/ai/langgraph-visualizer/generate', { workflow_id });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '生成可视化失败');
    }
  };

  const handleExportVisualization = async (vizId: string) => {
    try {
      await api.post(`/api/ai/langgraph-visualizer/visualizations/${vizId}/export`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '导出失败');
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
        <h1 className="text-3xl font-bold text-gray-900">工作流可视化</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 可视化列表 */}
      <Card>
        <CardHeader>
          <CardTitle>可视化列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {visualizations.map((viz) => (
              <div
                key={viz.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedViz?.id === viz.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedViz(viz)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{viz.workflow_name}</h3>
                  <Badge variant="outline">{viz.layout}</Badge>
                </div>
                <div className="text-sm text-gray-600">节点: {viz.nodes.length}</div>
                <div className="text-sm text-gray-600">边: {viz.edges.length}</div>
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(viz.created_at).toLocaleString()}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2 w-full"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleExportVisualization(viz.id);
                  }}
                >
                  导出
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 可视化详情 */}
      {selectedViz && (
        <Card>
          <CardHeader>
            <CardTitle>可视化详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-2">节点</h4>
                <div className="space-y-2">
                  {selectedViz.nodes.map((node) => (
                    <div key={node.id} className="border rounded p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{node.type}</Badge>
                        <span className="font-medium">{node.name}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        位置: ({node.position.x}, {node.position.y})
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-semibold mb-2">边</h4>
                <div className="space-y-2">
                  {selectedViz.edges.map((edge) => (
                    <div key={edge.id} className="border rounded p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span>{edge.source}</span>
                        <span>→</span>
                        <span>{edge.target}</span>
                        {edge.label && <Badge variant="outline">{edge.label}</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 可视化配置 */}
      <Card>
        <CardHeader>
          <CardTitle>可视化配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {configs.map((config) => (
              <div key={config.id} className="border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-semibold">工作流: {config.workflow_id}</h3>
                  <Badge variant="outline">{config.theme}</Badge>
                </div>
                <div className="text-sm text-gray-600">
                  显示标签: {config.show_labels ? '是' : '否'}
                </div>
                <div className="text-sm text-gray-600">
                  节点大小: {config.node_size}
                </div>
                <div className="text-sm text-gray-600">
                  边宽度: {config.edge_width}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
