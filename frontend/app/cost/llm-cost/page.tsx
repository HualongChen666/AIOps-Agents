'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import api from '@/lib/api';

interface LLMCost {
  model: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  total_cost: number;
  requests: number;
  avg_cost_per_request: number;
  period: string;
}

export default function LLMCostPage() {
  const [costs, setCosts] = useState<LLMCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCosts();
  }, []);

  const fetchCosts = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/cost/llm-cost');
      setCosts(res.data.costs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载LLM成本失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchCosts} className="mt-2">重试</Button></div>;
  }

  const totalCost = costs.reduce((sum, c) => sum + c.total_cost, 0);
  const totalTokens = costs.reduce((sum, c) => sum + c.input_tokens + c.output_tokens, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">LLM成本监控</h1>
        <Button onClick={fetchCosts}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总成本</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalCost.toFixed(2)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总Token数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTokens.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{costs.reduce((sum, c) => sum + c.requests, 0).toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均成本/请求</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${costs.length > 0 ? (totalCost / costs.reduce((sum, c) => sum + c.requests, 0)).toFixed(4) : 0}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>模型成本详情</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>模型</TableHead>
                <TableHead>提供商</TableHead>
                <TableHead>输入Token</TableHead>
                <TableHead>输出Token</TableHead>
                <TableHead>请求数</TableHead>
                <TableHead>总成本</TableHead>
                <TableHead>平均成本</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {costs.map((cost, idx) => (
                <TableRow key={idx}>
                  <TableCell className="font-medium">{cost.model}</TableCell>
                  <TableCell><Badge variant="outline">{cost.provider}</Badge></TableCell>
                  <TableCell>{cost.input_tokens.toLocaleString()}</TableCell>
                  <TableCell>{cost.output_tokens.toLocaleString()}</TableCell>
                  <TableCell>{cost.requests.toLocaleString()}</TableCell>
                  <TableCell className="font-semibold">${cost.total_cost.toFixed(2)}</TableCell>
                  <TableCell>${cost.avg_cost_per_request.toFixed(4)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
