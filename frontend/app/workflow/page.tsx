'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface WorkflowNode {
  id: string;
  name: string;
  type: 'trigger' | 'action' | 'condition' | 'end';
  position: { x: number; y: number };
}

interface Workflow {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'draft';
  lastRun: string;
}

export default function WorkflowPage() {
  // 🔧 P1-4: State Management
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [selectedWorkflow, setSelectedWorkflow] = useState('WF-001');
  const [isEditing, setIsEditing] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  const [nodes, setNodes] = useState<WorkflowNode[]>([
    { id: 'NODE-001', name: '告警触发', type: 'trigger', position: { x: 100, y: 100 } },
    { id: 'NODE-002', name: '条件判断', type: 'condition', position: { x: 300, y: 100 } },
    { id: 'NODE-003', name: '执行修复', type: 'action', position: { x: 500, y: 50 } },
    { id: 'NODE-004', name: '通知团队', type: 'action', position: { x: 500, y: 150 } },
    { id: 'NODE-005', name: '结束', type: 'end', position: { x: 700, y: 100 } },
  ]);

  const loadWorkflows = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/workflows/definitions', {
        headers: { Accept: 'application/json', Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
      });
      const data = await res.json();
      const items = Object.entries(data).map(([key, value]: [string, any]) => ({
        id: key,
        name: value?.name || key,
        status: 'active' as const,
        lastRun: value?.time || '-',
      }));
      setWorkflows(items);
      setLoading(false);
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  };

  const handleRunWorkflow = async (workflowId: string) => {
    try {
      // 后端使用 SSE 流式仿真，这里以文本方式消费流并提示启动
      await api.get(`/api/v1/workflows/simulate/${workflowId}`, { responseType: 'text' });
      success("Workflow simulation started");
    } catch (err) {
      showError("Failed to start workflow");
    }
  };

  useEffect(() => {
    loadWorkflows();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'draft':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getNodeTypeColor = (type: string) => {
    switch (type) {
      case 'trigger':
        return 'bg-blue-100 border-blue-500';
      case 'action':
        return 'bg-green-100 border-green-500';
      case 'condition':
        return 'bg-yellow-100 border-yellow-500';
      case 'end':
        return 'bg-red-100 border-red-500';
      default:
        return 'bg-gray-100 border-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">工作流编排</h1>
        <div className="flex gap-2">
          <Button variant="outline">导入</Button>
          <Button>创建工作流</Button>
        </div>
      </div>

      {/* 工作流列表 */}
      <Card>
        <CardHeader>
          <CardTitle>工作流列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {workflows.length > 0 ? workflows.map((workflow) => (
              <div
                key={workflow.id}
                className={`p-4 border-2 rounded-lg cursor-pointer transition ${selectedWorkflow === workflow.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}
                onClick={() => setSelectedWorkflow(workflow.id)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{workflow.name}</h3>
                      <Badge className={getStatusColor(workflow.status)}>
                        {workflow.status === 'active' ? '运行中' : workflow.status === 'inactive' ? '已停用' : '草稿'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">最后运行: {workflow.lastRun}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">编辑</Button>
                    <Button variant="outline" size="sm" onClick={() => handleRunWorkflow(workflow.id)}>运行</Button>
                  </div>
                </div>
              </div>
            )) : (
              <div className="text-center text-gray-500 py-4">No workflows found</div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 可视化编辑器 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>可视化编辑器</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsEditing(!isEditing)}>
                {isEditing ? '完成编辑' : '编辑模式'}
              </Button>
              <Button>保存</Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-gray-50 rounded-lg relative overflow-hidden">
            <p className="text-gray-500 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
              工作流可视化编辑器 (使用@antv/g6渲染)
            </p>
            {isEditing && (
              <div className="absolute top-4 left-4 space-y-2">
                <Button variant="outline" size="sm">添加触发器</Button>
                <Button variant="outline" size="sm">添加条件</Button>
                <Button variant="outline" size="sm">添加动作</Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 节点配置 */}
      <Card>
        <CardHeader>
          <CardTitle>节点配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {nodes.map((node) => (
              <div key={node.id} className={`p-4 border-2 rounded-lg ${getNodeTypeColor(node.type)}`}>
                <div className="font-medium mb-2">{node.name}</div>
                <div className="text-sm text-gray-600">类型: {node.type}</div>
                <div className="text-sm text-gray-600">位置: ({node.position.x}, {node.position.y})</div>
                <Button variant="outline" size="sm" className="mt-2">
                  配置
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 执行历史 */}
      <Card>
        <CardHeader>
          <CardTitle>执行历史</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">告警自动响应流程</div>
                  <div className="text-sm text-gray-500">触发: CPU告警 (严重)</div>
                </div>
                <div className="text-right">
                  <Badge className="bg-green-100 text-green-800">成功</Badge>
                  <div className="text-sm text-gray-500 mt-1">5分钟前</div>
                </div>
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">容量自动扩容流程</div>
                  <div className="text-sm text-gray-500">触发: 内存使用率 {'>'} 85%</div>
                </div>
                <div className="text-right">
                  <Badge className="bg-green-100 text-green-800">成功</Badge>
                  <div className="text-sm text-gray-500 mt-1">1小时前</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
