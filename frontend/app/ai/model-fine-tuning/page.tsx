'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface FineTuningJob {
  id: string;
  base_model: string;
  model_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  epoch: number;
  total_epochs: number;
  loss: number;
  learning_rate: number;
  created_at: string;
  completed_at?: string;
}

interface FineTunedModel {
  id: string;
  name: string;
  base_model: string;
  job_id: string;
  accuracy: number;
  file_size: number;
  created_at: string;
  deployed: boolean;
}

interface TrainingDataset {
  id: string;
  name: string;
  size: number;
  samples: number;
  format: string;
  created_at: string;
}

export default function ModelFineTuningPage() {
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [models, setModels] = useState<FineTunedModel[]>([]);
  const [datasets, setDatasets] = useState<TrainingDataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newJob, setNewJob] = useState({
    base_model: '',
    model_name: '',
    dataset_id: '',
    learning_rate: 0.0001,
    epochs: 3
  });

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [jobsRes, modelsRes, datasetsRes] = await Promise.all([
        api.get('/api/ai/model-fine-tuning/jobs'),
        api.get('/api/ai/model-fine-tuning/models'),
        api.get('/api/ai/model-fine-tuning/datasets')
      ]);
      setJobs(jobsRes.data.jobs || []);
      setModels(modelsRes.data.models || []);
      setDatasets(datasetsRes.data.datasets || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleStartFineTuning = async () => {
    try {
      await api.post('/api/ai/model-fine-tuning/jobs', newJob);
      setNewJob({
        base_model: '',
        model_name: '',
        dataset_id: '',
        learning_rate: 0.0001,
        epochs: 3
      });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '启动微调失败');
    }
  };

  const handleDeployModel = async (modelId: string) => {
    try {
      await api.post(`/api/ai/model-fine-tuning/models/${modelId}/deploy`);
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
        <h1 className="text-3xl font-bold text-gray-900">模型微调</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 启动微调 */}
      <Card>
        <CardHeader>
          <CardTitle>启动微调任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              placeholder="基础模型"
              value={newJob.base_model}
              onChange={(e) => setNewJob({ ...newJob, base_model: e.target.value })}
            />
            <Input
              placeholder="模型名称"
              value={newJob.model_name}
              onChange={(e) => setNewJob({ ...newJob, model_name: e.target.value })}
            />
            <Input
              placeholder="数据集ID"
              value={newJob.dataset_id}
              onChange={(e) => setNewJob({ ...newJob, dataset_id: e.target.value })}
            />
            <Input
              type="number"
              step="0.00001"
              placeholder="学习率"
              value={newJob.learning_rate}
              onChange={(e) => setNewJob({ ...newJob, learning_rate: parseFloat(e.target.value) || 0.0001 })}
            />
            <Input
              type="number"
              placeholder="训练轮数"
              value={newJob.epochs}
              onChange={(e) => setNewJob({ ...newJob, epochs: parseInt(e.target.value) || 3 })}
            />
          </div>
          <Button onClick={handleStartFineTuning} className="mt-4">启动微调</Button>
        </CardContent>
      </Card>

      {/* 微调任务 */}
      <Card>
        <CardHeader>
          <CardTitle>微调任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{job.model_name}</h3>
                    <Badge variant="outline">{job.base_model}</Badge>
                    <Badge variant={
                      job.status === 'completed' ? 'default' :
                      job.status === 'running' ? 'secondary' :
                      job.status === 'failed' ? 'destructive' : 'outline'
                    }>
                      {job.status}
                    </Badge>
                  </div>
                  <span className="text-sm text-gray-600">{job.progress.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Epoch: </span>
                    <span>{job.epoch}/{job.total_epochs}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Loss: </span>
                    <span>{job.loss.toFixed(4)}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">学习率: </span>
                    <span>{job.learning_rate}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">创建于: </span>
                    <span>{new Date(job.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 微调模型 */}
      <Card>
        <CardHeader>
          <CardTitle>微调模型</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{model.name}</h3>
                  <Badge variant={model.deployed ? 'default' : 'secondary'}>
                    {model.deployed ? '已部署' : '未部署'}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600 mb-1">基础模型: {model.base_model}</div>
                <div className="text-sm text-gray-600 mb-1">准确率: {(model.accuracy * 100).toFixed(1)}%</div>
                <div className="text-sm text-gray-600 mb-1">
                  大小: {(model.file_size / 1024 / 1024).toFixed(2)}MB
                </div>
                <div className="text-xs text-gray-500 mb-2">
                  创建于: {new Date(model.created_at).toLocaleString()}
                </div>
                {!model.deployed && (
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

      {/* 训练数据集 */}
      <Card>
        <CardHeader>
          <CardTitle>训练数据集</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{dataset.name}</h3>
                    <div className="text-sm text-gray-600">
                      格式: {dataset.format} | 样本数: {dataset.samples}
                    </div>
                    <div className="text-sm text-gray-600">
                      大小: {(dataset.size / 1024 / 1024).toFixed(2)}MB
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(dataset.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
