'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface SLODefinition {
  id: string;
  name: string;
  description: string;
  metric_type: 'availability' | 'latency' | 'error_rate' | 'throughput';
  threshold: number;
  operator: 'gte' | 'lte' | 'gt' | 'lt';
  window: string;
  alerting: boolean;
}

export default function SLODefinitionPage() {
  const [definitions, setDefinitions] = useState<SLODefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newDef, setNewDef] = useState({
    name: '',
    description: '',
    metric_type: 'availability' as const,
    threshold: 99.9,
    operator: 'gte' as const,
    window: '30d',
    alerting: true
  });

  useEffect(() => {
    fetchDefinitions();
  }, []);

  const fetchDefinitions = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/definition');
      setDefinitions(res.data.definitions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载SLO定义失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/api/slo/definition', newDef);
      setNewDef({
        name: '',
        description: '',
        metric_type: 'availability',
        threshold: 99.9,
        operator: 'gte',
        window: '30d',
        alerting: true
      });
      fetchDefinitions();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建定义失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchDefinitions} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">SLO定义</h1>
        <Button onClick={fetchDefinitions}>刷新</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>创建SLO定义</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Input
              placeholder="名称"
              value={newDef.name}
              onChange={(e) => setNewDef({ ...newDef, name: e.target.value })}
            />
            <Input
              placeholder="描述"
              value={newDef.description}
              onChange={(e) => setNewDef({ ...newDef, description: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-4">
              <Input
                type="number"
                placeholder="阈值"
                value={newDef.threshold}
                onChange={(e) => setNewDef({ ...newDef, threshold: parseFloat(e.target.value) || 99.9 })}
              />
              <Input
                placeholder="时间窗口"
                value={newDef.window}
                onChange={(e) => setNewDef({ ...newDef, window: e.target.value })}
              />
            </div>
            <Button onClick={handleCreate}>创建</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {definitions.map((def) => (
          <Card key={def.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{def.name}</CardTitle>
                <Badge variant={def.alerting ? 'default' : 'secondary'}>
                  {def.alerting ? '告警启用' : '告警禁用'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">{def.description}</p>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">指标类型</span>
                  <Badge variant="outline">{def.metric_type}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">阈值</span>
                  <span className="font-semibold">{def.threshold}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">操作符</span>
                  <span className="font-mono">{def.operator}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-500">窗口</span>
                  <span>{def.window}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
