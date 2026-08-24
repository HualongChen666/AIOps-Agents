'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

interface FlowchartNode {
  id: string;
  text: string;
  type: 'start' | 'process' | 'decision' | 'end';
  x: number;
  y: number;
}

interface FlowchartConnection {
  from: string;
  to: string;
  label?: string;
}

interface Flowchart {
  id: string;
  name: string;
  description: string;
  nodes: FlowchartNode[];
  connections: FlowchartConnection[];
  createdAt: string;
  updatedAt: string;
}

export default function FlowchartPage() {
  const [flowcharts, setFlowcharts] = useState<Flowchart[]>([]);
  const [selectedFlowchart, setSelectedFlowchart] = useState<Flowchart | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [nodeDialogOpen, setNodeDialogOpen] = useState(false);
  const [editingFlowchart, setEditingFlowchart] = useState<Flowchart | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });
  const [nodeForm, setNodeForm] = useState({
    id: '',
    text: '',
    type: 'process' as const,
    x: 100,
    y: 100,
  });

  const loadFlowcharts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<Flowchart[]>('/api/v1/flowchart');
      setFlowcharts(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedFlowchart(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载流程图失败');
      console.error('加载流程图失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFlowcharts();
  }, []);

  const handleCreate = () => {
    setEditingFlowchart(null);
    setFormData({ name: '', description: '' });
    setDialogOpen(true);
  };

  const handleEdit = (flowchart: Flowchart) => {
    setEditingFlowchart(flowchart);
    setFormData({
      name: flowchart.name,
      description: flowchart.description,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingFlowchart) {
        await api.put(`/api/v1/flowchart/${editingFlowchart.id}`, formData);
      } else {
        await api.post('/api/v1/flowchart', formData);
      }
      setDialogOpen(false);
      await loadFlowcharts();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个流程图吗？')) return;
    try {
      await api.delete(`/api/v1/flowchart/${id}`);
      if (selectedFlowchart?.id === id) {
        setSelectedFlowchart(null);
      }
      await loadFlowcharts();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleAddNode = () => {
    setNodeForm({
      id: `node-${Date.now()}`,
      text: '',
      type: 'process',
      x: 100,
      y: 100,
    });
    setNodeDialogOpen(true);
  };

  const handleSaveNode = async () => {
    if (!selectedFlowchart) return;
    try {
      await api.post(`/api/v1/flowchart/${selectedFlowchart.id}/nodes`, nodeForm);
      setNodeDialogOpen(false);
      await loadFlowcharts();
    } catch (err: any) {
      setError(err.response?.data?.message || '添加节点失败');
      console.error('添加节点失败:', err);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    if (!selectedFlowchart) return;
    try {
      await api.delete(`/api/v1/flowchart/${selectedFlowchart.id}/nodes/${nodeId}`);
      await loadFlowcharts();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除节点失败');
      console.error('删除节点失败:', err);
    }
  };

  const getNodeShape = (type: string) => {
    switch (type) {
      case 'start':
        return 'rounded-full';
      case 'end':
        return 'rounded-full';
      case 'decision':
        return 'rounded-lg rotate-45';
      default:
        return 'rounded-md';
    }
  };

  const getNodeColor = (type: string) => {
    const colors: Record<string, string> = {
      start: 'bg-green-100 border-green-500',
      end: 'bg-red-100 border-red-500',
      decision: 'bg-yellow-100 border-yellow-500',
      process: 'bg-blue-100 border-blue-500',
    };
    return colors[type] || colors.process;
  };

  const renderFlowchart = () => {
    if (!selectedFlowchart) return null;

    return (
      <div className="relative bg-white border rounded-lg" style={{ height: '500px' }}>
        <svg className="absolute inset-0 w-full h-full">
          {selectedFlowchart.connections.map((conn, idx) => {
            const fromNode = selectedFlowchart.nodes.find(n => n.id === conn.from);
            const toNode = selectedFlowchart.nodes.find(n => n.id === conn.to);
            if (!fromNode || !toNode) return null;

            return (
              <g key={idx}>
                <line
                  x1={fromNode.x + 60}
                  y1={fromNode.y + 30}
                  x2={toNode.x}
                  y2={toNode.y + 30}
                  stroke="#64748b"
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                />
                {conn.label && (
                  <text
                    x={(fromNode.x + toNode.x) / 2}
                    y={(fromNode.y + toNode.y) / 2 - 10}
                    fontSize="12"
                    fill="#64748b"
                  >
                    {conn.label}
                  </text>
                )}
              </g>
            );
          })}
          <defs>
            <marker
              id="arrow"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
            </marker>
          </defs>
        </svg>

        {selectedFlowchart.nodes.map((node) => (
          <div
            key={node.id}
            className={`absolute border-2 p-3 cursor-move ${getNodeShape(node.type)} ${getNodeColor(node.type)}`}
            style={{
              left: node.x,
              top: node.y,
              width: '120px',
              height: '60px',
            }}
          >
            <div className="text-sm font-medium text-center">{node.text}</div>
            <button
              onClick={() => handleDeleteNode(node.id)}
              className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full text-xs hover:bg-red-600"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    );
  };

  return (
    <main className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">流程图展示</h1>
          <p className="text-gray-600 mt-1">创建和编辑工作流流程图</p>
        </div>
        <Button onClick={handleCreate}>创建流程图</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>流程图列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : flowcharts.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无流程图</div>
            ) : (
              <div className="space-y-2">
                {flowcharts.map((fc) => (
                  <div
                    key={fc.id}
                    onClick={() => setSelectedFlowchart(fc)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedFlowchart?.id === fc.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{fc.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {fc.nodes.length} 节点 · {fc.connections.length} 连接
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(fc); }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(fc.id); }}
                      >
                        删除
                      </Button>
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
                {selectedFlowchart ? selectedFlowchart.name : '选择流程图'}
              </CardTitle>
              {selectedFlowchart && (
                <Button onClick={handleAddNode}>添加节点</Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedFlowchart ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedFlowchart.description}
                </div>
                {renderFlowchart()}
                <div className="flex gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-green-100 border border-green-500 rounded-full"></div>
                    <span>开始</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-blue-100 border border-blue-500 rounded-md"></div>
                    <span>处理</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-yellow-100 border border-yellow-500 rounded-lg rotate-45"></div>
                    <span>决策</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-red-100 border border-red-500 rounded-full"></div>
                    <span>结束</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个流程图
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingFlowchart ? '编辑流程图' : '创建流程图'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入流程图名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入流程图描述"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={!formData.name}>
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={nodeDialogOpen} onOpenChange={setNodeDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>添加节点</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">节点文本</label>
              <Input
                value={nodeForm.text}
                onChange={(e) => setNodeForm({ ...nodeForm, text: e.target.value })}
                placeholder="输入节点文本"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">节点类型</label>
              <select
                value={nodeForm.type}
                onChange={(e) => setNodeForm({ ...nodeForm, type: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="start">开始</option>
                <option value="process">处理</option>
                <option value="decision">决策</option>
                <option value="end">结束</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">X 坐标</label>
                <Input
                  type="number"
                  value={nodeForm.x}
                  onChange={(e) => setNodeForm({ ...nodeForm, x: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Y 坐标</label>
                <Input
                  type="number"
                  value={nodeForm.y}
                  onChange={(e) => setNodeForm({ ...nodeForm, y: parseInt(e.target.value) })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNodeDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveNode} disabled={!nodeForm.text}>
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
