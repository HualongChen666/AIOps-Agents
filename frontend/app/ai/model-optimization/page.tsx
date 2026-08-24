'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface OptimizationTask {
  id: string;
  model_id: string;
  model_name: string;
  optimization_type: 'quantization' | 'pruning' | 'distillation' | 'knowledge_distillation';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  metrics: {
    original_size: number;
    optimized_size: number;
    compression_ratio: number;
    accuracy_delta: number;
  };
  created_at: string;
}

interface ModelPerformance {
  model_id: string;
  model_name: string;
  latency: number;
  throughput: number;
  memory_usage: number;
  accuracy: number;
}

export default function ModelOptimizationPage() {
  const [tasks, setTasks] = useState<OptimizationTask[]>([]);
  const [performances, setPerformances] = useState<ModelPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [tasksRes, perfRes] = await Promise.all([
        api.get('/api/ai/model-optimization/tasks'),
        api.get('/api/ai/model-optimization/performance')
      ]);
      setTasks(tasksRes.data.tasks || []);
      setPerformances(perfRes.data.performances || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStartOptimization = async (modelId: string, type: string) => {
    try {
      await api.post('/api/ai/model-optimization/optimize', {
        model_id: modelId,
        optimization_type: type
      });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '启动优化失败');
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
        <h1 className="text-3xl font-bold text-gray-900">模型优化</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 模型性能 */}
      <Card>
        <CardHeader>
          <CardTitle>模型性能</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {performances.map((perf) => (
              <div key={perf.model_id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{perf.model_name}</h3>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600">延迟</div>
                    <div className="font-semibold">{perf.latency}ms</div>
                  </div>
                  <div>
                    <div className="text-gray-600">吞吐量</div>
                    <div className="font-semibold">{perf.throughput}/s</div>
                  </div>
                  <div>
                    <div className="text-gray-600">内存</div>
                    <div className="font-semibold">{(perf.memory_usage / 1024).toFixed(1)}MB</div>
                  </div>
                  <div>
                    <div className="text-gray-600">准确率</div>
                    <div className="font-semibold">{(perf.accuracy * 100).toFixed(1)}%</div>
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleStartOptimization(perf.model_id, 'quantization')}
                  >
                    量化
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleStartOptimization(perf.model_id, 'pruning')}
                  >
                    剪枝
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleStartOptimization(perf.model_id, 'distillation')}
                  >
                    蒸馏
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 优化任务 */}
      <Card>
        <CardHeader>
          <CardTitle>优化任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {tasks.map((task) => (
              <div key={task.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{task.model_name}</h3>
                    <Badge variant="outline">{task.optimization_type}</Badge>
                    <Badge variant={
                      task.status === 'completed' ? 'default' :
                      task.status === 'running' ? 'secondary' :
                      task.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {task.status}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-600">{task.progress.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                {task.status === 'completed' && task.metrics && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-gray-600">原始大小</div>
                      <div>{(task.metrics.original_size / 1024 / 1024).toFixed(2)}MB</div>
                    </div>
                    <div>
                      <div className="text-gray-600">优化后</div>
                      <div>{(task.metrics.optimized_size / 1024 / 1024).toFixed(2)}MB</div>
                    </div>
                    <div>
                      <div className="text-gray-600">压缩比</div>
                      <div>{task.metrics.compression_ratio.toFixed(2)}x</div>
                    </div>
                    <div>
                      <div className="text-gray-600">准确率变化</div>
                      <div>{task.metrics.accuracy_delta > 0 ? '+' : ''}{(task.metrics.accuracy_delta * 100).toFixed(2)}%</div>
                    </div>
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-2">
                  创建于: {new Date(task.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
