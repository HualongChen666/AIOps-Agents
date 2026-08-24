'use client'

import React, { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface DAGNode {
  id: string;
  name: string;
  type: 'task' | 'condition' | 'subdag';
  dependencies: string[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  retryCount: number;
  maxRetries: number;
}

interface DAGEdge {
  from: string;
  to: string;
  condition?: string;
}

interface DAG {
  id: string;
  name: string;
  description: string;
  nodes: DAGNode[];
  edges: DAGEdge[];
  status: 'idle' | 'running' | 'completed' | 'failed';
  schedule?: string;
  createdAt: string;
  updatedAt: string;
}

export default function DAGPage() {
  const [dags, setDags] = useState<DAG[]>([]);
  const [selectedDAG, setSelectedDAG] = useState<DAG | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [nodeDialogOpen, setNodeDialogOpen] = useState(false);
  const [editingDAG, setEditingDAG] = useState<DAG | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    schedule: '',
  });
  const [nodeForm, setNodeForm] = useState({
    id: '',
    name: '',
    type: 'task' as const,
    dependencies: [] as string[],
  });

  const loadDAGs = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<DAG[]>('/api/v1/dag');
      setDags(response.data || []);
      if (response.data && response.data.length > 0) {
        setSelectedDAG(response.data[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '加载DAG失败');
      console.error('加载DAG失败:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDAGs();
  }, []);

  const handleCreate = () => {
    setEditingDAG(null);
    setFormData({ name: '', description: '', schedule: '' });
    setDialogOpen(true);
  };

  const handleEdit = (dag: DAG) => {
    setEditingDAG(dag);
    setFormData({
      name: dag.name,
      description: dag.description,
      schedule: dag.schedule || '',
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingDAG) {
        await api.put(`/api/v1/dag/${editingDAG.id}`, formData);
      } else {
        await api.post('/api/v1/dag', formData);
      }
      setDialogOpen(false);
      await loadDAGs();
    } catch (err: any) {
      setError(err.response?.data?.message || '保存失败');
      console.error('保存失败:', err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除这个DAG吗？')) return;
    try {
      await api.delete(`/api/v1/dag/${id}`);
      if (selectedDAG?.id === id) {
        setSelectedDAG(null);
      }
      await loadDAGs();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除失败');
      console.error('删除失败:', err);
    }
  };

  const handleAddNode = () => {
    setNodeForm({
      id: `node-${Date.now()}`,
      name: '',
      type: 'task',
      dependencies: [],
    });
    setNodeDialogOpen(true);
  };

  const handleSaveNode = async () => {
    if (!selectedDAG) return;
    try {
      await api.post(`/api/v1/dag/${selectedDAG.id}/nodes`, nodeForm);
      setNodeDialogOpen(false);
      await loadDAGs();
    } catch (err: any) {
      setError(err.response?.data?.message || '添加节点失败');
      console.error('添加节点失败:', err);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    if (!selectedDAG) return;
    try {
      await api.delete(`/api/v1/dag/${selectedDAG.id}/nodes/${nodeId}`);
      await loadDAGs();
    } catch (err: any) {
      setError(err.response?.data?.message || '删除节点失败');
      console.error('删除节点失败:', err);
    }
  };

  const handleRunDAG = async () => {
    if (!selectedDAG) return;
    try {
      await api.post(`/api/v1/dag/${selectedDAG.id}/run`);
      await loadDAGs();
    } catch (err: any) {
      setError(err.response?.data?.message || '运行DAG失败');
      console.error('运行DAG失败:', err);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      idle: 'secondary',
      running: 'default',
      completed: 'default',
      failed: 'destructive',
      pending: 'outline',
      skipped: 'outline',
    };
    const labels: Record<string, string> = {
      idle: '空闲',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
      pending: '待执行',
      skipped: '已跳过',
    };
    return <Badge variant={variants[status] || 'outline'}>{labels[status] || status}</Badge>;
  };

  const renderDAGGraph = () => {
    if (!selectedDAG) return null;

    return (
      <div className="relative bg-white border rounded-lg" style={{ height: '400px' }}>
        <svg className="absolute inset-0 w-full h-full">
          {selectedDAG.edges.map((edge, idx) => {
            const fromNode = selectedDAG.nodes.find(n => n.id === edge.from);
            const toNode = selectedDAG.nodes.find(n => n.id === edge.to);
            if (!fromNode || !toNode) return null;

            return (
              <g key={idx}>
                <line
                  x1={fromNode.id.length * 20 + 80}
                  y1={30}
                  x2={toNode.id.length * 20}
                  y2={30}
                  stroke="#64748b"
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                />
                {edge.condition && (
                  <text
                    x={(fromNode.id.length * 20 + toNode.id.length * 20) / 2 + 40}
                    y={20}
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

        {selectedDAG.nodes.map((node, idx) => (
          <div
            key={node.id}
            className={`absolute border-2 rounded-lg p-3 cursor-pointer ${
              node.status === 'running' ? 'border-blue-500 bg-blue-50' :
              node.status === 'completed' ? 'border-green-500 bg-green-50' :
              node.status === 'failed' ? 'border-red-500 bg-red-50' :
              'border-gray-300 bg-gray-50'
            }`}
            style={{
              left: idx * 150 + 20,
              top: 10,
              width: '120px',
            }}
          >
            <div className="text-sm font-medium">{node.name}</div>
            <Badge variant="outline" className="mt-1 text-xs">
              {node.type}
            </Badge>
            <Badge variant="outline" className="mt-1 text-xs ml-1">
              {getStatusBadge(node.status)}
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
          <h1 className="text-3xl font-bold text-gray-900">DAG图</h1>
          <p className="text-gray-600 mt-1">有向无环图工作流管理</p>
        </div>
        <Button onClick={handleCreate}>创建DAG</Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>DAG列表</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : dags.length === 0 ? (
              <div className="text-center py-4 text-gray-500">暂无DAG</div>
            ) : (
              <div className="space-y-2">
                {dags.map((dag) => (
                  <div
                    key={dag.id}
                    onClick={() => setSelectedDAG(dag)}
                    className={`p-3 border rounded-lg cursor-pointer transition hover:bg-gray-50 ${
                      selectedDAG?.id === dag.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium">{dag.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusBadge(dag.status)}
                      {dag.schedule && (
                        <Badge variant="outline" className="text-xs">
                          {dag.schedule}
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {dag.nodes.length} 节点
                    </div>
                    <div className="flex gap-2 mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleEdit(dag); }}
                      >
                        编辑
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); handleDelete(dag.id); }}
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
                {selectedDAG ? selectedDAG.name : '选择DAG'}
              </CardTitle>
              {selectedDAG && (
                <div className="flex gap-2">
                  <Button onClick={handleAddNode}>添加节点</Button>
                  <Button onClick={handleRunDAG}>运行</Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {selectedDAG ? (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  {selectedDAG.description}
                </div>
                {renderDAGGraph()}
                <div>
                  <h3 className="text-sm font-medium mb-2">节点列表</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>节点</TableHead>
                        <TableHead>类型</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>依赖</TableHead>
                        <TableHead>重试</TableHead>
                        <TableHead>操作</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedDAG.nodes.map((node) => (
                        <TableRow key={node.id}>
                          <TableCell className="font-medium">{node.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{node.type}</Badge>
                          </TableCell>
                          <TableCell>{getStatusBadge(node.status)}</TableCell>
                          <TableCell className="text-gray-600">
                            {node.dependencies.length > 0 ? node.dependencies.join(', ') : '-'}
                          </TableCell>
                          <TableCell className="text-gray-600">
                            {node.retryCount}/{node.maxRetries}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDeleteNode(node.id)}
                            >
                              删除
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            ) : (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请从左侧选择一个DAG
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingDAG ? '编辑DAG' : '创建DAG'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入DAG名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">描述</label>
              <Textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入DAG描述"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">调度表达式（可选）</label>
              <Input
                value={formData.schedule}
                onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                placeholder="0 0 * * *"
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
              <label className="block text-sm font-medium mb-1">节点名称</label>
              <Input
                value={nodeForm.name}
                onChange={(e) => setNodeForm({ ...nodeForm, name: e.target.value })}
                placeholder="输入节点名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">节点类型</label>
              <select
                value={nodeForm.type}
                onChange={(e) => setNodeForm({ ...nodeForm, type: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="task">任务</option>
                <option value="condition">条件</option>
                <option value="subdag">子DAG</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">依赖节点（逗号分隔）</label>
              <Input
                value={nodeForm.dependencies.join(',')}
                onChange={(e) => setNodeForm({ 
                  ...nodeForm, 
                  dependencies: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                })}
                placeholder="node1, node2"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNodeDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveNode} disabled={!nodeForm.name}>
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
