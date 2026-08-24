'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface DeepLearningModel {
  id: string;
  name: string;
  architecture: 'transformer' | 'cnn' | 'rnn' | 'gnn' | 'custom';
  framework: 'pytorch' | 'tensorflow' | 'jax' | 'onnx';
  parameters: number;
  status: 'training' | 'ready' | 'deployed' | 'error';
  accuracy: number;
  created_at: string;
}

interface TrainingJob {
  id: string;
  model_id: string;
  model_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  epoch: number;
  total_epochs: number;
  loss: number;
  accuracy: number;
  created_at: string;
}

export default function DeepLearningPage() {
  const [models, setModels] = useState<DeepLearningModel[]>([]);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [modelsRes, jobsRes] = await Promise.all([
        api.get('/api/ai/deep-learning/models'),
        api.get('/api/ai/deep-learning/jobs')
      ]);
      setModels(modelsRes.data.models || []);
      setJobs(jobsRes.data.jobs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeployModel = async (modelId: string) => {
    try {
      await api.post(`/api/ai/deep-learning/models/${modelId}/deploy`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '部署模型失败');
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
        <h1 className="text-3xl font-bold text-gray-900">深度学习模型</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 模型列表 */}
      <Card>
        <CardHeader>
          <CardTitle>深度学习模型</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{model.name}</h3>
                  <Badge variant={
                    model.status === 'deployed' ? 'default' :
                    model.status === 'ready' ? 'secondary' :
                    model.status === 'training' ? 'outline' : 'destructive'
                  }>
                    {model.status}
                  </Badge>
                </div>
                <div className="space-y-1 text-sm text-gray-600 mb-3">
                  <div>架构: {model.architecture}</div>
                  <div>框架: {model.framework}</div>
                  <div>参数: {(model.parameters / 1000000).toFixed(2)}M</div>
                  <div>准确率: {(model.accuracy * 100).toFixed(1)}%</div>
                </div>
                {model.status === 'ready' && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => handleDeployModel(model.id)}
                  >
                    部署
                  </Button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 训练任务 */}
      <Card>
        <CardHeader>
          <CardTitle>训练任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{job.model_name}</h3>
                    <Badge variant={
                      job.status === 'completed' ? 'default' :
                      job.status === 'running' ? 'secondary' :
                      job.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {job.status}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-600">
                    Epoch: {job.epoch}/{job.total_epochs}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(job.epoch / job.total_epochs) * 100}%` }}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Loss: </span>
                    <span className="font-semibold">{job.loss.toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Accuracy: </span>
                    <span className="font-semibold">{(job.accuracy * 100).toFixed(2)}%</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-2">
                  创建于: {new Date(job.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
