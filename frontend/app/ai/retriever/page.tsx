'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RetrievalConfig {
  id: string;
  name: string;
  knowledge_base_id: string;
  top_k: number;
  similarity_threshold: number;
  reranking_enabled: boolean;
  created_at: string;
}

interface RetrievalResult {
  document_id: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export default function RetrieverPage() {
  const [configs, setConfigs] = useState<RetrievalConfig[]>([]);
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    knowledge_base_id: '',
    top_k: 5,
    similarity_threshold: 0.7,
    reranking_enabled: true
  });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/retriever/configs');
      setConfigs(res.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRetrieve = async () => {
    if (!query.trim() || !selectedConfig) return;
    try {
      const res = await api.post('/api/ai/retriever/retrieve', {
        config_id: selectedConfig,
        query: query
      });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '检索失败');
    }
  };

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/ai/retriever/configs', newConfig);
      setNewConfig({
        name: '',
        knowledge_base_id: '',
        top_k: 5,
        similarity_threshold: 0.7,
        reranking_enabled: true
      });
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
        <h1 className="text-3xl font-bold text-gray-900">检索器</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      {/* 检索配置 */}
      <Card>
        <CardHeader>
          <CardTitle>检索配置</CardTitle>
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
                  <Badge variant="outline">Top-K: {config.top_k}</Badge>
                </div>
                <div className="text-sm text-gray-600">知识库: {config.knowledge_base_id}</div>
                <div className="text-sm text-gray-600">相似度阈值: {config.similarity_threshold}</div>
                <div className="text-sm text-gray-600">
                  重排序: {config.reranking_enabled ? '启用' : '禁用'}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新配置 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建检索配置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="配置名称"
                value={newConfig.name}
                onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
              />
              <Input
                placeholder="知识库ID"
                value={newConfig.knowledge_base_id}
                onChange={(e) => setNewConfig({ ...newConfig, knowledge_base_id: e.target.value })}
              />
              <Input
                type="number"
                placeholder="Top-K"
                value={newConfig.top_k}
                onChange={(e) => setNewConfig({ ...newConfig, top_k: parseInt(e.target.value) || 5 })}
              />
              <Input
                type="number"
                step="0.1"
                placeholder="相似度阈值"
                value={newConfig.similarity_threshold}
                onChange={(e) => setNewConfig({ ...newConfig, similarity_threshold: parseFloat(e.target.value) || 0.7 })}
              />
            </div>
            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                id="reranking"
                checked={newConfig.reranking_enabled}
                onChange={(e) => setNewConfig({ ...newConfig, reranking_enabled: e.target.checked })}
              />
              <label htmlFor="reranking">启用重排序</label>
            </div>
            <Button onClick={handleCreateConfig} className="mt-4">创建配置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 检索测试 */}
      <Card>
        <CardHeader>
          <CardTitle>检索测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Input
              placeholder="输入查询..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleRetrieve()}
              disabled={!selectedConfig}
            />
            <Button onClick={handleRetrieve} disabled={!selectedConfig || !query.trim()}>
              检索
            </Button>
          </div>
          <div className="space-y-2">
            {results.map((result, idx) => (
              <div key={idx} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="outline">相似度: {result.score.toFixed(4)}</Badge>
                  <Badge variant="outline">文档ID: {result.document_id}</Badge>
                </div>
                <div className="text-sm">{result.content}</div>
                {Object.keys(result.metadata).length > 0 && (
                  <div className="mt-2 text-xs text-gray-500">
                    元数据: {JSON.stringify(result.metadata)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
