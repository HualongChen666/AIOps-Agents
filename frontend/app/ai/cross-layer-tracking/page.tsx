'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface CrossLayerTrace {
  id: string;
  trace_id: string;
  layers: Array<{
    name: string;
    timestamp: string;
    duration: number;
    status: 'success' | 'error' | 'warning';
    metadata: Record<string, any>;
  }>;
  total_duration: number;
  created_at: string;
}

interface TrackingConfig {
  id: string;
  name: string;
  enabled_layers: string[];
  sampling_rate: number;
}

export default function CrossLayerTrackingPage() {
  const [traces, setTraces] = useState<CrossLayerTrace[]>([]);
  const [configs, setConfigs] = useState<TrackingConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [traceId, setTraceId] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tracesRes, configsRes] = await Promise.all([
        api.get('/api/ai/cross-layer-tracking/traces'),
        api.get('/api/ai/cross-layer-tracking/configs')
      ]);
      setTraces(tracesRes.data.traces || []);
      setConfigs(configsRes.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchTrace = async () => {
    if (!traceId.trim()) return;
    try {
      const res = await api.get(`/api/ai/cross-layer-tracking/traces/${traceId}`);
      setTraces([res.data]);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '搜索失败');
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
        <h1 className="text-3xl font-bold text-gray-900">跨层追踪</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 搜索追踪 */}
      <Card>
        <CardHeader>
          <CardTitle>搜索追踪</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder="输入追踪ID..."
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearchTrace()}
            />
            <Button onClick={handleSearchTrace}>搜索</Button>
          </div>
        </CardContent>
      </Card>

      {/* 追踪配置 */}
      <Card>
        <CardHeader>
          <CardTitle>追踪配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {configs.map((config) => (
              <div key={config.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{config.name}</h3>
                  <Badge variant="outline">采样率: {(config.sampling_rate * 100).toFixed(1)}%</Badge>
                </div>
                <div className="text-sm text-gray-600">
                  启用层级: {config.enabled_layers.join(', ')}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 追踪列表 */}
      <Card>
        <CardHeader>
          <CardTitle>追踪列表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {traces.map((trace) => (
              <div key={trace.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold">追踪ID: {trace.trace_id}</h3>
                    <Badge variant="outline">总耗时: {trace.total_duration}ms</Badge>
                  </div>
                  <span className="text-sm text-gray-500">
                    {new Date(trace.created_at).toLocaleString()}
                  </span>
                </div>

                <div className="space-y-2">
                  {trace.layers.map((layer, idx) => (
                    <div key={idx} className="border-l-2 pl-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={
                          layer.status === 'success' ? 'default' :
                          layer.status === 'error' ? 'destructive' : 'secondary'
                        }>
                          {layer.status}
                        </Badge>
                        <span className="font-medium">{layer.name}</span>
                        <span className="text-sm text-gray-500">{layer.duration}ms</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(layer.timestamp).toLocaleString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
