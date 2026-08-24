'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface RetrievalResult {
  id: string;
  content: string;
  source: string;
  relevance_score: number;
  metadata: Record<string, any>;
}

interface RetrievalConfig {
  id: string;
  name: string;
  knowledge_base_id: string;
  retrieval_method: 'vector' | 'keyword' | 'hybrid';
  max_results: number;
}

export default function KnowledgeRetrievalPage() {
  const [configs, setConfigs] = useState<RetrievalConfig[]>([]);
  const [results, setResults] = useState<RetrievalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/knowledge-retrieval/configs');
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
      const res = await api.post('/api/ai/knowledge-retrieval/retrieve', {
        config_id: selectedConfig,
        query: query
      });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '检索失败');
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
        <h1 className="text-3xl font-bold text-gray-900">知识库检索</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      {/* 检索配置 */}
      <Card>
        <CardHeader>
          <CardTitle>检索配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
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
                  <Badge variant="outline">{config.retrieval_method}</Badge>
                </div>
                <div className="text-sm text-gray-600">知识库: {config.knowledge_base_id}</div>
                <div className="text-sm text-gray-600">最大结果: {config.max_results}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 检索界面 */}
      <Card>
        <CardHeader>
          <CardTitle>知识检索</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="输入检索查询..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleRetrieve()}
                disabled={!selectedConfig}
              />
              <Button onClick={handleRetrieve} disabled={!selectedConfig || !query.trim()}>
                检索
              </Button>
            </div>

            {results.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-semibold">检索结果</h4>
                {results.map((result, idx) => (
                  <div key={idx} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="outline">相关性: {result.relevance_score.toFixed(4)}</Badge>
                      <Badge variant="outline">{result.source}</Badge>
                    </div>
                    <p className="text-sm mb-2">{result.content}</p>
                    {Object.keys(result.metadata).length > 0 && (
                      <div className="text-xs text-gray-500">
                        元数据: {JSON.stringify(result.metadata)}
                      </div>
                    )}
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
