'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface WorkflowNode {
  id: string;
  type: 'start' | 'condition' | 'action' | 'end';
  name: string;
  description: string;
  position: { x: number; y: number };
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'draft';
  nodes: WorkflowNode[];
  triggers: string[];
  lastRun: Date;
}

interface Schedule {
  id: string;
  workflowId: string;
  cron: string;
  nextRun: Date;
  enabled: boolean;
}

interface BackendStep {
  key: string;
  title: string;
  desc: string;
}

interface BackendWorkflow {
  name: string;
  nodes: number;
  time: string;
  rate: string;
  steps: BackendStep[];
}

export default function WorkflowOrchestrationPage() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);

  const [schedules, setSchedules] = useState<Schedule[]>([
    {
      id: 'S-001',
      workflowId: 'WF-001',
      cron: '0 */5 * * *',
      nextRun: new Date(Date.now() + 300000),
      enabled: true,
    },
    {
      id: 'S-002',
      workflowId: 'WF-002',
      cron: '0 * * * *',
      nextRun: new Date(Date.now() + 60000),
      enabled: true,
    },
  ]);

  useEffect(() => {
    let canceled = false;
    async function loadWorkflows() {
      try {
        const { data } = await api.get<Record<string, BackendWorkflow>>('/api/v1/workflows/definitions');
        if (canceled) return;
        const definitions = data ?? {};
        const mapped = Object.entries(definitions).map(([key, def], _idx) => {
          const steps = def.steps ?? [];
          const nodes: WorkflowNode[] = steps.map((step, i) => ({
            id: step.key || `${key}-node-${i}`,
            type: i === 0 ? 'start' : i === steps.length - 1 ? 'end' : 'action',
            name: step.title,
            description: step.desc,
            position: { x: 100 + (i % 2) * 140, y: 50 + i * 90 },
          }));
          return {
            id: key,
            name: def.name || key,
            description: `平均耗时 ${def.time || 'N/A'} · 成功率 ${def.rate || 'N/A'}`,
            status: 'active' as const,
            nodes,
            triggers: [] as string[],
            lastRun: new Date(),
          };
        });
        setWorkflows(mapped);
      } catch (error) {
        // api interceptor already surfaces toast messages
        console.error('加载工作流定义失败', error);
      }
    }
    loadWorkflows();
    return () => {
      canceled = true;
    };
  }, []);

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
      case 'start':
        return 'bg-green-500';
      case 'end':
        return 'bg-red-500';
      case 'condition':
        return 'bg-yellow-500';
      case 'action':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleCreateWorkflow = () => {
    const newWorkflow: Workflow = {
      id: `WF-${Date.now()}`,
      name: '新工作流',
      description: '工作流描述',
      status: 'draft',
      nodes: [
        { id: 'N-001', type: 'start', name: '开始', description: '开始节点', position: { x: 100, y: 50 } },
        { id: 'N-002', type: 'end', name: '结束', description: '结束节点', position: { x: 100, y: 150 } },
      ],
      triggers: [],
      lastRun: new Date(),
    };
    setWorkflows([...workflows, newWorkflow]);
    setSelectedWorkflow(newWorkflow);
    setIsEditing(true);
  };

  const handleToggleSchedule = (scheduleId: string) => {
    setSchedules(schedules.map((s) =>
      s.id === scheduleId ? { ...s, enabled: !s.enabled } : s
    ));
  };

  const handleRunSimulation = (workflow: Workflow) => {
    // TODO: wire /api/v1/workflows/simulate/{workflow.id} SSE to drive node state and logs
    console.log('TODO: run SSE simulation for', workflow.id);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">工作流编排</h1>
        <Button onClick={handleCreateWorkflow}>创建工作流</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 工作流列表 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>工作流列表</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {workflows.map((workflow) => (
                <div
                  key={workflow.id}
                  className={`p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedWorkflow?.id === workflow.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                    }`}
                  onClick={() => setSelectedWorkflow(workflow)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">{workflow.name}</h4>
                    <Badge className={getStatusColor(workflow.status)}>
                      {workflow.status === 'active' ? '活跃' : workflow.status === 'inactive' ? '停用' : '草稿'}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-500 mb-2">{workflow.description}</p>
                  <div className="text-xs text-gray-400">
                    最后运行: {workflow.lastRun.toLocaleString()}
                  </div>
                </div>
              ))}
              {workflows.length === 0 && (
                <div className="text-sm text-gray-500">暂无工作流定义</div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 工作流编辑器 */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>
                {selectedWorkflow ? selectedWorkflow.name : '选择工作流'}
              </CardTitle>
              {selectedWorkflow && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(!isEditing)}>
                    {isEditing ? '完成编辑' : '编辑'}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => handleRunSimulation(selectedWorkflow)}>
                    运行
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedWorkflow ? (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请选择一个工作流或创建新工作流
              </div>
            ) : (
              <div className="space-y-4">
                {/* 可视化工作流编辑器 */}
                <div className="h-96 bg-gray-50 rounded-lg relative overflow-hidden">
                  {selectedWorkflow.nodes.map((node) => (
                    <div
                      key={node.id}
                      className="absolute p-3 rounded-lg shadow-md cursor-move hover:shadow-lg transition"
                      style={{
                        left: node.position.x,
                        top: node.position.y,
                        minWidth: '120px',
                      }}
                    >
                      <div className={`w-3 h-3 rounded-full ${getNodeTypeColor(node.type)} mb-2`} />
                      <p className="text-sm font-medium">{node.name}</p>
                      <p className="text-xs text-gray-500">{node.description}</p>
                    </div>
                  ))}
                  {isEditing && (
                    <div className="absolute bottom-4 right-4 flex gap-2">
                      <Button variant="outline" size="sm">
                        + 条件节点
                      </Button>
                      <Button variant="outline" size="sm">
                        + 动作节点
                      </Button>
                    </div>
                  )}
                </div>

                {/* 工作流详情 */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">触发器</label>
                    <div className="flex flex-wrap gap-1">
                      {selectedWorkflow.triggers.map((trigger, index) => (
                        <Badge key={index} variant="outline">
                          {trigger}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">节点数量</label>
                    <p className="text-sm">{selectedWorkflow.nodes.length}</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 定时触发配置 */}
      <Card>
        <CardHeader>
          <CardTitle>定时触发</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {schedules.map((schedule) => {
              const workflow = workflows.find((w) => w.id === schedule.workflowId);
              return (
                <div key={schedule.id} className="p-4 border border-gray-200 rounded-lg flex items-center justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium">{workflow?.name || '未知工作流'}</h4>
                    <p className="text-sm text-gray-500">Cron: {schedule.cron}</p>
                    <p className="text-xs text-gray-400">下次运行: {schedule.nextRun.toLocaleString()}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={schedule.enabled ? 'default' : 'secondary'}>
                      {schedule.enabled ? '已启用' : '已禁用'}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggleSchedule(schedule.id)}
                    >
                      {schedule.enabled ? '禁用' : '启用'}
                    </Button>
                  </div>
                </div>
              );
            })}
            <Button variant="outline" className="w-full">
              + 添加定时触发
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 条件分支说明 */}
      <Card>
        <CardHeader>
          <CardTitle>条件分支</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">简单条件</h4>
              <p className="text-sm text-gray-600 mb-3">基于单一条件的分支判断</p>
              <div className="bg-gray-50 rounded p-2 text-xs font-mono">
                if (cpu &gt; 80) {'{'} scale_up() {'}'}
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">多条件分支</h4>
              <p className="text-sm text-gray-600 mb-3">支持多个条件的复杂分支</p>
              <div className="bg-gray-50 rounded p-2 text-xs font-mono">
                if (cpu &gt; 80 &amp;&amp; memory &gt; 70) {'{'} scale_up() {'}'}
              </div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">并行分支</h4>
              <p className="text-sm text-gray-600 mb-3">同时执行多个分支</p>
              <div className="bg-gray-50 rounded p-2 text-xs font-mono">
                parallel {`{`} notify(); log(); {`}`}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
