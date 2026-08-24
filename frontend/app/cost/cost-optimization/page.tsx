'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface OptimizationSuggestion {
  id: string;
  resource: string;
  type: 'resize' | 'delete' | 'schedule' | 'reserved';
  current_cost: number;
  projected_savings: number;
  effort: 'low' | 'medium' | 'high';
  impact: 'low' | 'medium' | 'high';
  description: string;
  status: 'pending' | 'applied' | 'dismissed';
}

export default function CostOptimizationPage() {
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSuggestions();
  }, []);

  const fetchSuggestions = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/cost-optimization');
      setSuggestions(res.data.suggestions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载优化建议失败');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (id: string) => {
    try {
      await api.post(`/api/cost/cost-optimization/${id}/apply`);
      fetchSuggestions();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '应用失败');
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await api.post(`/api/cost/cost-optimization/${id}/dismiss`);
      fetchSuggestions();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '忽略失败');
    }
  };

  const totalSavings = suggestions
    .filter(s => s.status === 'pending')
    .reduce((sum, s) => sum + s.projected_savings, 0);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchSuggestions} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">成本优化</h1>
        <Button onClick={fetchSuggestions}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>优化概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">${totalSavings.toFixed(2)}</div>
              <div className="text-sm text-gray-500">预计月度节省</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold">
                {suggestions.filter(s => s.status === 'pending').length}
              </div>
              <div className="text-sm text-gray-500">待处理建议</div>
            </div>
            <div className="p-4 border rounded-lg">
              <div className="text-2xl font-bold">
                {suggestions.filter(s => s.status === 'applied').length}
              </div>
              <div className="text-sm text-gray-500">已应用</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {suggestions.map((suggestion) => (
          <Card key={suggestion.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{suggestion.resource}</CardTitle>
                  <div className="text-sm text-gray-500">{suggestion.description}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{suggestion.type}</Badge>
                  <Badge variant={suggestion.status === 'pending' ? 'default' : 'secondary'}>
                    {suggestion.status === 'pending' ? '待处理' : suggestion.status === 'applied' ? '已应用' : '已忽略'}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4 mb-4">
                <div>
                  <div className="text-sm text-gray-500">当前成本</div>
                  <div className="font-semibold">${suggestion.current_cost.toFixed(2)}/月</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">预计节省</div>
                  <div className="font-semibold text-green-600">${suggestion.projected_savings.toFixed(2)}/月</div>
                </div>
                <div>
                  <div className="text-sm text-gray-500">实施难度</div>
                  <Badge variant={suggestion.effort === 'low' ? 'default' : suggestion.effort === 'medium' ? 'secondary' : 'destructive'}>
                    {suggestion.effort}
                  </Badge>
                </div>
                <div>
                  <div className="text-sm text-gray-500">影响程度</div>
                  <Badge variant={suggestion.impact === 'high' ? 'default' : suggestion.impact === 'medium' ? 'secondary' : 'outline'}>
                    {suggestion.impact}
                  </Badge>
                </div>
              </div>
              {suggestion.status === 'pending' && (
                <div className="flex gap-2">
                  <Button onClick={() => handleApply(suggestion.id)}>应用</Button>
                  <Button variant="outline" onClick={() => handleDismiss(suggestion.id)}>忽略</Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
