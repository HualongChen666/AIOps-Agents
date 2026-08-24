'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Runbook {
  id: string;
  name: string;
  description: string;
  category: string;
  status: 'draft' | 'published' | 'deprecated';
  steps: Array<{
    order: number;
    title: string;
    description: string;
    commands: string[];
    expected_result: string;
  }>;
  created_at: string;
  updated_at: string;
}

interface GenerationTask {
  id: string;
  incident_type: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  runbook_id?: string;
  error_message?: string;
  created_at: string;
}

export default function RunbookGeneratorPage() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [tasks, setTasks] = useState<GenerationTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRunbook, setSelectedRunbook] = useState<Runbook | null>(null);
  const [newGeneration, setNewGeneration] = useState({ incident_type: '', context: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [runbooksRes, tasksRes] = await Promise.all([
        api.get('/api/ai/runbook-generator/runbooks'),
        api.get('/api/ai/runbook-generator/tasks')
      ]);
      setRunbooks(runbooksRes.data.runbooks || []);
      setTasks(tasksRes.data.tasks || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    try {
      await api.post('/api/ai/runbook-generator/generate', newGeneration);
      setNewGeneration({ incident_type: '', context: '' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '生成失败');
    }
  };

  const handlePublishRunbook = async (id: string) => {
    try {
      await api.patch(`/api/ai/runbook-generator/runbooks/${id}`, { status: 'published' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '发布失败');
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
        <h1 className="text-3xl font-bold text-gray-900">Runbook生成器</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 生成Runbook */}
      <Card>
        <CardHeader>
          <CardTitle>生成Runbook</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              placeholder="事件类型"
              value={newGeneration.incident_type}
              onChange={(e) => setNewGeneration({ ...newGeneration, incident_type: e.target.value })}
            />
            <textarea
              placeholder="上下文信息..."
              value={newGeneration.context}
              onChange={(e) => setNewGeneration({ ...newGeneration, context: e.target.value })}
              className="w-full border rounded p-2 h-24"
            />
            <Button onClick={handleGenerate}>生成Runbook</Button>
          </div>
        </CardContent>
      </Card>

      {/* 生成任务 */}
      <Card>
        <CardHeader>
          <CardTitle>生成任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {tasks.map((task) => (
              <div key={task.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{task.incident_type}</h3>
                    <Badge variant={
                      task.status === 'completed' ? 'default' :
                      task.status === 'generating' ? 'secondary' :
                      task.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {task.status}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(task.created_at).toLocaleString()}
                  </span>
                </div>
                {task.error_message && (
                  <div className="text-sm text-red-600">{task.error_message}</div>
                )}
                {task.runbook_id && (
                  <div className="text-sm text-gray-600">Runbook ID: {task.runbook_id}</div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Runbook列表 */}
      <Card>
        <CardHeader>
          <CardTitle>Runbook列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {runbooks.map((runbook) => (
              <div
                key={runbook.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedRunbook?.id === runbook.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedRunbook(runbook)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{runbook.name}</h3>
                    <Badge variant="outline">{runbook.category}</Badge>
                    <Badge variant={
                      runbook.status === 'published' ? 'default' :
                      runbook.status === 'deprecated' ? 'destructive' : 'secondary'
                    }>
                      {runbook.status}
                    </Badge>
                  </div>
                  {runbook.status === 'draft' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePublishRunbook(runbook.id);
                      }}
                    >
                      发布
                    </Button>
                  )}
                </div>
                <p className="text-sm text-gray-600">{runbook.description}</p>
                <div className="text-xs text-gray-500 mt-1">
                  步骤: {runbook.steps.length} | 更新于: {new Date(runbook.updated_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Runbook详情 */}
      {selectedRunbook && (
        <Card>
          <CardHeader>
            <CardTitle>Runbook详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {selectedRunbook.steps.map((step, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">步骤 {step.order}</Badge>
                    <h4 className="font-semibold">{step.title}</h4>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{step.description}</p>
                  {step.commands.length > 0 && (
                    <div className="mb-2">
                      <div className="text-sm font-medium mb-1">命令:</div>
                      <div className="bg-gray-100 p-2 rounded text-xs font-mono">
                        {step.commands.join('\n')}
                      </div>
                    </div>
                  )}
                  <div className="text-sm text-gray-600">
                    预期结果: {step.expected_result}
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
