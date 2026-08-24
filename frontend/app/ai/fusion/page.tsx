'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface FusionConfig {
  id: string;
  name: string;
  strategy: 'rrf' | 'weighted' | 'condorcet' | 'comb_sum';
  weights: Record<string, number>;
  created_at: string;
}

interface FusionResult {
  document_id: string;
  content: string;
  fused_score: number;
  source_scores: Record<string, number>;
}

export default function FusionPage() {
  const [configs, setConfigs] = useState<FusionConfig[]>([]);
  const [results, setResults] = useState<FusionResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    strategy: 'rrf' as const,
    weights: {}
  });

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/ai/fusion/configs');
      setConfigs(res.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleFusion = async () => {
    if (!query.trim() || !selectedConfig) return;
    try {
      const res = await api.post('/api/ai/fusion/fuse', {
        config_id: selectedConfig,
        query: query
      });
      setResults(res.data.results || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '融合失败');
    }
  };

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/ai/fusion/configs', newConfig);
      setNewConfig({ name: '', strategy: 'rrf', weights: {} });
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
        <h1 className="text-3xl font-bold text-gray-900">结果融合</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      {/* 融合配置 */}
      <Card>
        <CardHeader>
          <CardTitle>融合配置</CardTitle>
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
                  <Badge variant="outline">{config.strategy}</Badge>
                </div>
                <div className="text-sm text-gray-600">
                  权重: {Object.entries(config.weights).map(([k, v]) => `${k}:${v}`).join(', ')}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新配置 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建融合配置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                placeholder="配置名称"
                value={newConfig.name}
                onChange={(e) => setNewConfig({ ...newConfig, name: e.target.value })}
              />
              <select
                className="border rounded px-3 py-2"
                value={newConfig.strategy}
                onChange={(e) => setNewConfig({ ...newConfig, strategy: e.target.value as any })}
              >
                <option value="rrf">RRF (Reciprocal Rank Fusion)</option>
                <option value="weighted">加权融合</option>
                <option value="condorcet">Condorcet</option>
                <option value="comb_sum">CombSUM</option>
              </select>
            </div>
            <Button onClick={handleCreateConfig} className="mt-4">创建配置</Button>
          </div>
        </CardContent>
      </Card>

      {/* 融合测试 */}
      <Card>
        <CardHeader>
          <CardTitle>融合测试</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="查询..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleFusion()}
                disabled={!selectedConfig}
              />
              <Button onClick={handleFusion} disabled={!selectedConfig || !query.trim()}>
                融合
              </Button>
            </div>

            {results.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-semibold">融合结果</h4>
                {results.map((result, idx) => (
                  <div key={idx} className="border rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="default">融合分数: {result.fused_score.toFixed(4)}</Badge>
                      <Badge variant="outline">文档ID: {result.document_id}</Badge>
                    </div>
                    <div className="text-sm mb-2">{result.content}</div>
                    <div className="text-xs text-gray-500">
                      源分数: {Object.entries(result.source_scores).map(([k, v]) => `${k}:${v.toFixed(4)}`).join(', ')}
                    </div>
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
