'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface WorkflowNode {
  id: string;
  name: string;
  type: 'start' | 'task' | 'condition' | 'end';
  position: { x: number; y: number };
  status: 'pending' | 'running' | 'completed' | 'failed';
  dependencies: string[];
}

interface WorkflowEdge {
  from: string;
  to: string;
  condition?: string;
}

interface WorkflowVisualization {
  id: string;
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  layout: 'horizontal' | 'vertical' | 'circular';
}

export default function WorkflowVisualizationPage() {
  const [visualizations, setVisualizations] = useState<WorkflowVisualization[]>([]);
  const [selectedViz, setSelectedViz] = useState<WorkflowVisualization | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [layout, setLayout] = useState<'horizontal' | 'vertical' | 'circular'>('horizontal');
  const [scale, setScale] = useState(1);

  const loadVisualizations = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<WorkflowVisualization[]>('/api/v1/workflow-visualization');
      setVisualizations(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedViz(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载可视化数据失败');
      console.error('加载可视化数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVisualizations();
  }, []);

  const handleLayoutChange = async (newLayout: 'horizontal' | 'vertical' | 'circular') => {
    setLayout(newLayout);
    if (selectedViz) {
      try {
        await api.patch(`/api/v1/workflow-visualization/${selectedViz.id}/layout`, { layout: newLayout });
        await loadVisualizations();
      } catch (err: any) {
        console.error('更新布局失败:', err);
      }
    }
  };

  const handleExport = async () => {
    if (!selectedViz) return;
    try {
      const response = await api.get(`/api/v1/workflow-visualization/${selectedViz.id}/export`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${selectedViz.name}-workflow.png`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      setError(err.response?.data?.message || '导出失败');
      console.error('导出失败:', err);
    }
  };

  const getNodeColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-gray-200 border-gray-400',
      running: 'bg-blue-100 border-blue-500',
      completed: 'bg-green-100 border-green-500',
      failed: 'bg-red-100 border-red-500',
    };
    return colors[status] || colors.pending;
  };

  const getNodeIcon = (type: string) => {
    const icons: Record<string, string> = {
      start: '⚡',
      task: '⚙️',
      condition: '❓',
      end: '🏁',
    };
    return icons[type] || '⚙️';
  };

  const renderWorkflowGraph = () => {
    if (!selectedViz) return null;

    const nodes = selectedViz.nodes;
    const edges = selectedViz.edges;

    return (
      <div 
        className="relative bg-white border rounded-lg overflow-hidden"
        style={{ height: '600px', transform: `scale(${scale})`, transformOrigin: 'top left' }}
      >
        <svg className="absolute inset-0 w-full h-full">
          {edges.map((edge, idx) => {
            const fromNode = nodes.find(n => n.id === edge.from);
            const toNode = nodes.find(n => n.id === edge.to);
            if (!fromNode || !toNode) return null;
            
            return (
              <g key={idx}>
                <line
                  x1={fromNode.position.x + 60}
                  y1={fromNode.position.y + 30}
                  x2={toNode.position.x}
                  y2={toNode.position.y + 30}
                  stroke="#94a3b8"
                  strokeWidth="2"
                  markerEnd="url(#arrowhead)"
                />
                {edge.condition && (
                  <text
                    x={(fromNode.position.x + toNode.position.x) / 2}
                    y={(fromNode.position.y + toNode.position.y) / 2 - 10}
                    fontSize="12"
                    fill="#64748b"
                  >
                    {edge.condition}
                  </text>
                )}
              </g>
            );
          })}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
            </marker>
          </defs>
        </svg>
        
        {nodes.map((node) => (
          <div
            key={node.id}
            className={`absolute border-2 rounded-lg p-3 cursor-pointer transition-shadow hover:shadow-lg ${getNodeColor(node.status)}`}
            style={{
              left: node.position.x,
              top: node.position.y,
              width: '120px',
            }}
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">{getNodeIcon(node.type)}</span>
              <span className="text-sm font-medium truncate">{node.name}</span>
            </div>
            <Badge variant="outline" className="mt-1 text-xs">
              {node.status}
            </Badge>
          </div>
        ))}
      </div>
    );
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">工作流可视化</h1>
          <p className="text-gray-600 mt-1">图形化展示工作流结构和执行状态</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setScale(Math.max(0.5, scale - 0.1))}>
            缩小
          </Button>
          <Button variant="outline" onClick={() => setScale(Math.min(2, scale + 0.1))}>
            放大
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={!selectedViz}>
            导出图片
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>工作流列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : visualizations.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无工作流</div>
            ) : (
              <div className="space-y-2">
                {visualizations.map((viz) => (
                  <div
                    key={viz.id}
                    onClick={() => setSelectedViz(viz)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedViz?.id === viz.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{viz.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {viz.nodes.length} 节点 · {viz.edges.length} 连接
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedViz ? selectedViz.name : '选择工作流'}
              </CardTitle>
              <div className="flex gap-2">
                <Button
                  variant={layout === 'horizontal' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleLayoutChange('horizontal')}
                >
                  水平
                </Button>
                <Button
                  variant={layout === 'vertical' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleLayoutChange('vertical')}
                >
                  垂直
                </Button>
                <Button
                  variant={layout === 'circular' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleLayoutChange('circular')}
                >
                  环形
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {selectedViz ? (
              <div className="space-y-4">
                {renderWorkflowGraph()}
                <div className="flex gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-gray-200 border border-gray-400 rounded"></div>
                    <span>待执行</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-blue-100 border border-blue-500 rounded"></div>
                    <span>运行中</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-green-100 border border-green-500 rounded"></div>
                    <span>已完成</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-red-100 border border-red-500 rounded"></div>
                    <span>失败</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个工作流
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
