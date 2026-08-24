'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'draft';
  node_count: number;
  last_executed: string;
  created_at: string;
}

interface WorkflowNode {
  id: string;
  workflow_id: string;
  name: string;
  type: 'llm' | 'tool' | 'condition' | 'action';
  config: Record<string, any>;
}

export default function LangGraphWorkflowPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [newWorkflow, setNewWorkflow] = useState({ name: '', description: '' });

  useEffect(() => {
    fetchWorkflows();
  }, []);

  useEffect(() => {
    if (selectedWorkflow) {
      fetchNodes(selectedWorkflow);
    }
  }, [selectedWorkflow]);

  const fetchWorkflows = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/langgraph-workflow/workflows');
      setWorkflows(res.data.workflows || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载工作流失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchNodes = async (workflowId: string) => {
    try {
      const res = await api.get(`/api/ai/langgraph-workflow/workflows/${workflowId}/nodes`);
      setNodes(res.data.nodes || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载节点失败');
    }
  };

  const handleCreateWorkflow = async () => {
    try {
      await api.post('/api/ai/langgraph-workflow/workflows', newWorkflow);
      setNewWorkflow({ name: '', description: '' });
      fetchWorkflows();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建工作流失败');
    }
  };

  const handleActivateWorkflow = async (id: string) => {
    try {
      await api.patch(`/api/ai/langgraph-workflow/workflows/${id}`, { status: 'active' });
      fetchWorkflows();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '激活工作流失败');
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
        <Button onClick={fetchWorkflows} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">LangGraph工作流</h1>
        <Button onClick={fetchWorkflows}>刷新</Button>
      </div>

      {/* 工作流列表 */}
      <Card>
        <CardHeader>
          <CardTitle>工作流列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedWorkflow === workflow.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedWorkflow(workflow.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{workflow.name}</h3>
                  <Badge variant={
                    workflow.status === 'active' ? 'default' :
                    workflow.status === 'inactive' ? 'secondary' : 'outline'
                  }>
                    {workflow.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 mb-2">{workflow.description}</p>
                <div className="text-sm text-gray-600">节点数: {workflow.node_count}</div>
                <div className="text-xs text-gray-500 mt-1">
                  最后执行: {workflow.last_executed ? new Date(workflow.last_executed).toLocaleString() : '从未'}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新工作流 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建新工作流</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="工作流名称"
                value={newWorkflow.name}
                onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
              />
              <Input
                placeholder="描述"
                value={newWorkflow.description}
                onChange={(e) => setNewWorkflow({ ...newWorkflow, description: e.target.value })}
              />
            </div>
            <Button onClick={handleCreateWorkflow} className="mt-4">创建工作流</Button>
          </div>
        </CardContent>
      </Card>

      {/* 节点列表 */}
      {selectedWorkflow && (
        <Card>
          <CardHeader>
            <CardTitle>工作流节点</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {nodes.map((node) => (
                <div key={node.id} className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold">{node.name}</h3>
                    <Badge variant="outline">{node.type}</Badge>
                  </div>
                  <div className="text-xs text-gray-500">
                    配置: {JSON.stringify(node.config)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
