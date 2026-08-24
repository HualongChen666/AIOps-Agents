'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RerankerConfig {
  id: string;
  name: string;
  model: string;
  top_n: number;
  threshold: number;
  created_at: string;
}

interface RerankingResult {
  original_rank: number;
  new_rank: number;
  score: number;
  content: string;
}

export default function RerankerPage() {
  const [configs, setConfigs] = useState<RerankerConfig[]>([]);
  const [results, setResults] = useState<RerankingResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [documents, setDocuments] = useState('');
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    model: 'cross-encoder',
    top_n: 5,
    threshold: 0.5
  });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/reranker/configs');
      setConfigs(res.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRerank = async () => {
    if (!query.trim() || !documents.trim() || !selectedConfig) return;
    try {
      const res = await api.post('/api/ai/reranker/rerank', {
        config_id: selectedConfig,
        query: query,
        documents: documents.split('\n').filter(d => d.trim())
      });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '重排序失败');
    }
  };

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/ai/reranker/configs', newConfig);
      setNewConfig({ name: '', model: 'cross-encoder', top_n: 5, threshold: 0.5 });
      fetchConfigs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建配置失败');
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
        <Button onClick={fetchConfigs} className="mt-2">重试</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">重排序器</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      {/* 重排序配置 */}
      <Card>
        <CardHeader>
          <CardTitle>重排序配置</CardTitle>
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
                <div className="text-sm text-gray-600">Top-N: {config.top_n}</div>
                <div className="text-sm text-gray-600">阈值: {config.threshold}</div>
              </div>
            ))}
          </div>

          {/* 创建新配置 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建重排序配置</h3>
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
                placeholder="Top-N"
                value={newConfig.top_n}
                onChange={(e) => setNewConfig({ ...newConfig, top_n: parseInt(e.target.value) || 5 })}
              />
              <Input
                type="number"
                step="0.1"
                placeholder="阈值"
                value={newConfig.threshold}
                onChange={(e) => setNewConfig({ ...newConfig, threshold: parseFloat(e.target.value) || 0.5 })}
              />
            </div>
            <Button onClick={handleCreateConfig} className="mt-4">创建配置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 重排序测试 */}
      <Card>
        <CardHeader>
          <CardTitle>重排序测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              placeholder="查询..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={!selectedConfig}
            />
            <textarea
              placeholder="文档列表 (每行一个文档)"
              value={documents}
              onChange={(e) => setDocuments(e.target.value)}
              className="w-full border rounded p-2 h-32"
              disabled={!selectedConfig}
            />
            <Button onClick={handleRerank} disabled={!selectedConfig || !query.trim() || !documents.trim()}>
              重排序
            </Button>

            {results.length > 0 && (
              <div className="space-y-2 mt-4">
                <h4 className="font-semibold">重排序结果</h4>
                {results.map((result, idx) => (
                  <div key={idx} className="border rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline">原排名: {result.original_rank}</Badge>
                      <Badge variant="default">新排名: {result.new_rank}</Badge>
                      <Badge variant="outline">分数: {result.score.toFixed(4)}</Badge>
                    </div>
                    <div className="text-sm">{result.content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
