'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface VectorizerConfig {
  id: string;
  name: string;
  model: string;
  dimensions: number;
  batch_size: number;
  created_at: string;
}

interface EmbeddingJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_items: number;
  processed_items: number;
  error_message?: string;
  created_at: string;
}

export default function VectorizerPage() {
  const [configs, setConfigs] = useState<VectorizerConfig[]>([]);
  const [jobs, setJobs] = useState<EmbeddingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    model: 'text-embedding-ada-002',
    batch_size: 100
  });
  const [textInput, setTextInput] = useState('');
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [embeddingResult, setEmbeddingResult] = useState<number[] | null>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [configsRes, jobsRes] = await Promise.all([
        api.get('/api/ai/vectorizer/configs'),
        api.get('/api/ai/vectorizer/jobs')
      ]);
      setConfigs(configsRes.data.configs || []);
      setJobs(jobsRes.data.jobs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/ai/vectorizer/configs', newConfig);
      setNewConfig({ name: '', model: 'text-embedding-ada-002', batch_size: 100 });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建配置失败');
    }
  };

  const handleEmbedText = async () => {
    if (!textInput.trim() || !selectedConfig) return;
    try {
      const res = await api.post('/api/ai/vectorizer/embed', {
        config_id: selectedConfig,
        text: textInput
      });
      setEmbeddingResult(res.data.embedding);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '向量化失败');
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
        <h1 className="text-3xl font-bold text-gray-900">向量化处理</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 向量化配置 */}
      <Card>
        <CardHeader>
          <CardTitle>向量化配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {configs.map((config) => (
              <div
                key={config.id}
                className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                  selectedConfig === config.id ? 'border-blue-500 bg-blue-50' : ''
                }`}
                onClick={() => setSelectedConfig(config.id)}
              >
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{config.name}</h3>
                  <Badge variant="outline">{config.model}</Badge>
                </div>
                <div className="text-sm text-gray-600">维度: {config.dimensions}</div>
                <div className="text-sm text-gray-600">批处理大小: {config.batch_size}</div>
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(config.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新配置 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建向量化配置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="配置名称"
                value={newConfig.name}
                onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
              />
              <Input
                placeholder="模型"
                value={newConfig.model}
                onChange={(e) => setNewConfig({ ...newConfig, model: e.target.value })}
              />
              <Input
                type="number"
                placeholder="批处理大小"
                value={newConfig.batch_size}
                onChange={(e) => setNewConfig({ ...newConfig, batch_size: parseInt(e.target.value) || 100 })}
              />
            </div>
            <Button onClick={handleCreateConfig} className="mt-4">创建配置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 文本向量化测试 */}
      <Card>
        <CardHeader>
          <CardTitle>文本向量化测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="输入要向量化的文本..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                disabled={!selectedConfig}
              />
              <Button onClick={handleEmbedText} disabled={!selectedConfig || !textInput.trim()}>
                向量化
              </Button>
            </div>
            {embeddingResult && (
              <div className="border rounded-lg p-4">
                <h4 className="font-semibold mb-2">向量结果 (维度: {embeddingResult.length})</h4>
                <div className="text-xs font-mono bg-gray-100 p-2 rounded max-h-40 overflow-auto">
                  [{embeddingResult.slice(0, 50).map(v => v.toFixed(4)).join(', ')}
                  {embeddingResult.length > 50 && '...'}]
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 嵌入任务 */}
      <Card>
        <CardHeader>
          <CardTitle>嵌入任务</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant={
                    job.status === 'completed' ? 'default' :
                    job.status === 'processing' ? 'secondary' :
                    job.status === 'failed' ? 'destructive' : 'outline'
                  }>
                    {job.status}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    {job.processed_items} / {job.total_items}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(job.processed_items / job.total_items) * 100}%` }}
                  />
                </div>
                {job.error_message && (
                  <div className="text-sm text-red-600 mt-2">{job.error_message}</div>
                )}
                <div className="text-xs text-gray-500 mt-1">
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
