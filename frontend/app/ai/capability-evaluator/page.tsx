'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface ModelCapability {
  model_id: string;
  model_name: string;
  capabilities: {
    reasoning: number;
    coding: number;
    math: number;
    writing: number;
    analysis: number;
  };
  overall_score: number;
  last_evaluated: string;
}

interface EvaluationTask {
  id: string;
  name: string;
  description: string;
  category: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  results?: {
    model_id: string;
    score: number;
    details: string;
  }[];
}

export default function CapabilityEvaluatorPage() {
  const [capabilities, setCapabilities] = useState<ModelCapability[]>([]);
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTask, setNewTask] = useState({ name: '', description: '', category: 'general' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [capsRes, tasksRes] = await Promise.all([
        api.get('/api/ai/capability-evaluator/capabilities'),
        api.get('/api/ai/capability-evaluator/tasks')
      ]);
      setCapabilities(capsRes.data.capabilities || []);
      setTasks(tasksRes.data.tasks || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async () => {
    try {
      await api.post('/api/ai/capability-evaluator/tasks', newTask);
      setNewTask({ name: '', description: '', category: 'general' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建任务失败');
    }
  };

  const handleRunEvaluation = async (modelId: string) => {
    try {
      await api.post('/api/ai/capability-evaluator/evaluate', { model_id: modelId });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '运行评估失败');
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
        <h1 className="text-3xl font-bold text-gray-900">能力评估器</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 模型能力评估 */}
      <Card>
        <CardHeader>
          <CardTitle>模型能力评估</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {capabilities.map((cap) => (
              <div key={cap.model_id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-semibold">{cap.model_name}</h3>
                    <div className="text-sm text-gray-600">最后评估: {new Date(cap.last_evaluated).toLocaleString()}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">总分: {cap.overall_score.toFixed(2)}</Badge>
                    <Button size="sm" onClick={() => handleRunEvaluation(cap.model_id)}>
                      重新评估
                    </Button>
                  </div>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  {Object.entries(cap.capabilities).map(([key, value]) => (
                    <div key={key} className="text-center">
                      <div className="text-sm text-gray-600 capitalize">{key}</div>
                      <div className="text-2xl font-bold">{(value * 100).toFixed(0)}%</div>
                      <div className="bg-gray-200 rounded-full h-2 mt-1">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${value * 100}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 评估任务 */}
      <Card>
        <CardHeader>
          <CardTitle>评估任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {tasks.map((task) => (
              <div key={task.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{task.name}</h3>
                    <Badge variant="outline">{task.category}</Badge>
                    <Badge variant={
                      task.status === 'completed' ? 'default' :
                      task.status === 'running' ? 'secondary' :
                      task.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {task.status}
                    </Badge>
                  </div>
                </div>
                <div className="text-sm text-gray-600 mb-2">{task.description}</div>
                {task.results && task.results.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <h4 className="font-semibold mb-2">评估结果</h4>
                    <div className="space-y-2">
                      {task.results.map((result, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <span>{result.model_id}</span>
                          <Badge variant="outline">{result.score.toFixed(2)}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* 创建新任务 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建评估任务</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="任务名称"
                value={newTask.name}
                onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
              />
              <Input
                placeholder="类别"
                value={newTask.category}
                onChange={(e) => setNewTask({ ...newTask, category: e.target.value })}
              />
              <Input
                placeholder="描述"
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                className="md:col-span-2"
              />
            </div>
            <Button onClick={handleCreateTask} className="mt-4">创建任务</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
