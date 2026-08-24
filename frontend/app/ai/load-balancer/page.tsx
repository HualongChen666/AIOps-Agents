'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';

interface LoadBalancerConfig {
  id: string;
  name: string;
  strategy: 'round_robin' | 'least_connections' | 'weighted' | 'latency_based';
  targets: Array<{
    id: string;
    endpoint: string;
    weight: number;
    current_connections: number;
    health: 'healthy' | 'unhealthy' | 'draining';
  }>;
  health_check_interval: number;
  enabled: boolean;
}

interface LoadMetrics {
  total_requests: number;
  requests_per_second: number;
  avg_response_time: number;
  error_rate: number;
}

export default function LoadBalancerPage() {
  const [configs, setConfigs] = useState<LoadBalancerConfig[]>([]);
  const [metrics, setMetrics] = useState<LoadMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({ name: '', strategy: 'round_robin' as const });

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [configsRes, metricsRes] = await Promise.all([
        api.get('/api/ai/load-balancer/configs'),
        api.get('/api/ai/load-balancer/metrics')
      ]);
      setConfigs(configsRes.data.configs || []);
      setMetrics(metricsRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConfig = async () => {
    try {
      await api.post('/api/ai/load-balancer/configs', newConfig);
      setNewConfig({ name: '', strategy: 'round_robin' });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '创建配置失败');
    }
  };

  const handleToggleConfig = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/api/ai/load-balancer/configs/${id}`, { enabled: !enabled });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新配置失败');
    }
  };

  const handleDrainTarget = async (configId: string, targetId: string) => {
    try {
      await api.post(`/api/ai/load-balancer/configs/${configId}/targets/${targetId}/drain`);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '排空目标失败');
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
        <h1 className="text-3xl font-bold text-gray-900">负载均衡器</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 负载指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>总请求数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics?.total_requests.toLocaleString() || '0'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>请求/秒</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics?.requests_per_second.toFixed(2) || '0.00'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>平均响应时间</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{metrics?.avg_response_time.toFixed(2) || '0.00'}ms</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>错误率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{((metrics?.error_rate || 0) * 100).toFixed(2)}%</div>
          </CardContent>
        </Card>
      </div>

      {/* 负载均衡配置 */}
      <Card>
        <CardHeader>
          <CardTitle>负载均衡配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {configs.map((config) => (
              <div key={config.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{config.name}</h3>
                    <Badge variant="outline">{config.strategy}</Badge>
                    <Badge variant={config.enabled ? 'default' : 'secondary'}>
                      {config.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleConfig(config.id, config.enabled)}
                  >
                    {config.enabled ? '禁用' : '启用'}
                  </Button>
                </div>
                <div className="text-sm text-gray-600 mb-3">
                  健康检查间隔: {config.health_check_interval}s
                </div>
                <div className="space-y-2">
                  <h4 className="font-semibold text-sm">目标端点</h4>
                  {config.targets.map((target) => (
                    <div key={target.id} className="flex items-center justify-between border rounded p-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Badge variant={target.health === 'healthy' ? 'default' : 'destructive'}>
                          {target.health}
                        </Badge>
                        <span>{target.endpoint}</span>
                        <Badge variant="outline">权重: {target.weight}</Badge>
                        <span className="text-gray-600">连接: {target.current_connections}</span>
                      </div>
                      {target.health === 'healthy' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDrainTarget(config.id, target.id)}
                        >
                          排空
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* 创建新配置 */}
          <div className="mt-6 pt-6 border-t">
            <h3 className="font-semibold mb-4">创建负载均衡配置</h3>
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
                <option value="round_robin">轮询</option>
                <option value="least_connections">最少连接</option>
                <option value="weighted">加权</option>
                <option value="latency_based">基于延迟</option>
              </select>
            </div>
            <Button onClick={handleCreateConfig} className="mt-4">创建配置</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
