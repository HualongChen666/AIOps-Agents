'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CostData {
  period: string;
  total_cost: number;
  by_model: Array<{
    model: string;
    cost: number;
    requests: number;
  }>;
  by_service: Array<{
    service: string;
    cost: number;
    requests: number;
  }>;
}

interface OptimizationSuggestion {
  id: string;
  type: 'model_switch' | 'caching' | 'batching' | 'prompt_optimization';
  description: string;
  potential_savings: number;
  implementation_effort: 'low' | 'medium' | 'high';
  status: 'pending' | 'implemented' | 'rejected';
}

export default function CostOptimizerPage() {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('7d');

  useEffect(() => {
    fetchData();
  }, [selectedPeriod]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [costRes, suggestionsRes] = await Promise.all([
        api.get(`/api/ai/cost-optimizer/costs?period=${selectedPeriod}`),
        api.get('/api/ai/cost-optimizer/suggestions')
      ]);
      setCostData(costRes.data);
      setSuggestions(suggestionsRes.data.suggestions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleImplementSuggestion = async (id: string) => {
    try {
      await api.post(`/api/ai/cost-optimizer/suggestions/${id}/implement`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '实施建议失败');
    }
  };

  const handleRejectSuggestion = async (id: string) => {
    try {
      await api.post(`/api/ai/cost-optimizer/suggestions/${id}/reject`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '拒绝建议失败');
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
        <h1 className="text-3xl font-bold text-gray-900">成本优化器</h1>
        <div className="flex gap-2">
          {['1d', '7d', '30d'].map((period) => (
            <Button
              key={period}
              variant={selectedPeriod === period ? 'default' : 'outline'}
              onClick={() => setSelectedPeriod(period)}
            >
              {period === '1d' ? '1天' : period === '7d' ? '7天' : '30天'}
            </Button>
          ))}
          <Button onClick={fetchData}>刷新</Button>
        </div>
      </div>

      {/* 成本概览 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>总成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${costData?.total_cost.toFixed(2) || '0.00'}</div>
            <div className="text-sm text-gray-600 mt-1">周期: {selectedPeriod}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {costData?.by_model.reduce((sum, m) => sum + m.requests, 0).toLocaleString() || '0'}
            </div>
            <div className="text-sm text-gray-600 mt-1">所有模型</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>平均成本/请求</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              ${costData ? (costData.total_cost / costData.by_model.reduce((sum, m) => sum + m.requests, 0)).toFixed(4) : '0.0000'}
            </div>
            <div className="text-sm text-gray-600 mt-1">每请求</div>
          </CardContent>
        </Card>
      </div>

      {/* 按模型分成本 */}
      <Card>
        <CardHeader>
          <CardTitle>按模型分成本</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {costData?.by_model.map((item) => (
              <div key={item.model} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{item.model}</h3>
                  <Badge variant="outline">${item.cost.toFixed(2)}</Badge>
                </div>
                <div className="text-sm text-gray-600">请求数: {item.requests.toLocaleString()}</div>
                <div className="text-sm text-gray-600">平均成本: ${(item.cost / item.requests).toFixed(4)}/请求</div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{ width: `${(item.cost / costData.total_cost) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 按服务分成本 */}
      <Card>
        <CardHeader>
          <CardTitle>按服务分成本</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {costData?.by_service.map((item) => (
              <div key={item.service} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{item.service}</h3>
                  <Badge variant="outline">${item.cost.toFixed(2)}</Badge>
                </div>
                <div className="text-sm text-gray-600">请求数: {item.requests.toLocaleString()}</div>
                <div className="text-sm text-gray-600">平均成本: ${(item.cost / item.requests).toFixed(4)}/请求</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 优化建议 */}
      <Card>
        <CardHeader>
          <CardTitle>优化建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{suggestion.description}</h3>
                    <Badge variant="outline">{suggestion.type}</Badge>
                    <Badge variant={suggestion.status === 'implemented' ? 'default' : 'secondary'}>
                      {suggestion.status === 'implemented' ? '已实施' : suggestion.status === 'rejected' ? '已拒绝' : '待处理'}
                    </Badge>
                  </div>
                  <Badge variant="outline" className="text-green-600">
                    节省: ${suggestion.potential_savings.toFixed(2)}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600">实施难度: {suggestion.implementation_effort}</div>
                {suggestion.status === 'pending' && (
                  <div className="flex gap-2 mt-3">
                    <Button
                      size="sm"
                      onClick={() => handleImplementSuggestion(suggestion.id)}
                    >
                      实施
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRejectSuggestion(suggestion.id)}
                    >
                      拒绝
                    </Button>
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
