'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface KPIConfig {
  id: string;
  kpi_id: string;
  kpi_name: string;
  data_source: string;
  query: string;
  aggregation: 'sum' | 'avg' | 'max' | 'min' | 'count';
  interval: string;
  alert_threshold: number;
  alert_enabled: boolean;
}

export default function KPIConfigPage() {
  const [configs, setConfigs] = useState<KPIConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/slo/kpi-config');
      setConfigs(res.data.configs || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id: string, config: Partial<KPIConfig>) => {
    try {
      await api.put(`/api/slo/kpi-config/${id}`, config);
      fetchConfigs();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新配置失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchConfigs} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">KPI配置</h1>
        <Button onClick={fetchConfigs}>刷新</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {configs.map((config) => (
          <Card key={config.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{config.kpi_name}</CardTitle>
                <Badge variant={config.alert_enabled ? 'default' : 'secondary'}>
                  {config.alert_enabled ? '告警启用' : '告警禁用'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">数据源</label>
                  <Input
                    value={config.data_source}
                    onChange={(e) => handleUpdate(config.id, { data_source: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">查询</label>
                  <Input
                    value={config.query}
                    onChange={(e) => handleUpdate(config.id, { query: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">聚合方式</label>
                    <Badge variant="outline">{config.aggregation}</Badge>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">间隔</label>
                    <span>{config.interval}</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">告警阈值</label>
                  <Input
                    type="number"
                    value={config.alert_threshold}
                    onChange={(e) => handleUpdate(config.id, { alert_threshold: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <Button
                  variant="outline"
                  onClick={() => handleUpdate(config.id, { alert_enabled: !config.alert_enabled })}
                >
                  {config.alert_enabled ? '禁用告警' : '启用告警'}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
