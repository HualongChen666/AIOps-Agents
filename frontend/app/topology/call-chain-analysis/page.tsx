'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CallChain {
  id: string;
  trace_id: string;
  start_time: string;
  duration: number;
  services: string[];
  status: 'success' | 'error' | 'timeout';
  error_count: number;
}

export default function CallChainAnalysisPage() {
  const [chains, setChains] = useState<CallChain[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [traceId, setTraceId] = useState('');

  useEffect(() => {
    fetchChains();
  }, []);

  const fetchChains = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/topology/call-chain-analysis');
      setChains(res.data.chains || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载调用链失败');
    } finally {
      setLoading(false);
    }
  };

  const analyzeTrace = async () => {
    if (!traceId) return;
    try {
      setLoading(true);
      const res = await api.post('/api/topology/call-chain-analysis/analyze', { trace_id: traceId });
      setChains([res.data]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '分析失败');
    } finally {
      setLoading(false);
    }
  };

  if (loading && chains.length === 0) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchChains} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">调用链分析</h1>
        <Button onClick={fetchChains}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>分析特定追踪</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="输入Trace ID"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
            />
            <Button onClick={analyzeTrace}>分析</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>调用链列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {chains.map((chain) => (
              <div key={chain.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-semibold">{chain.trace_id}</h3>
                    <div className="text-sm text-gray-500">{new Date(chain.start_time).toLocaleString()}</div>
                  </div>
                  <Badge variant={chain.status === 'success' ? 'default' : 'destructive'}>
                    {chain.status}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <div className="text-sm text-gray-500">持续时间</div>
                    <div className="text-lg font-semibold">{chain.duration}ms</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">服务数</div>
                    <div className="text-lg font-semibold">{chain.services.length}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">错误数</div>
                    <div className="text-lg font-semibold text-red-600">{chain.error_count}</div>
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-2">调用路径</div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {chain.services.map((svc, idx) => (
                      <div key={idx} className="flex items-center">
                        <Badge variant="outline">{svc}</Badge>
                        {idx < chain.services.length - 1 && <span className="text-gray-400">→</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
