'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface AdvancedFeature {
  id: string;
  name: string;
  description: string;
  category: 'nlp' | 'vision' | 'multimodal' | 'reasoning';
  status: 'available' | 'experimental' | 'deprecated';
  enabled: boolean;
  performance_metrics: {
    accuracy?: number;
    latency?: number;
    throughput?: number;
  };
}

interface AIExperiment {
  id: string;
  name: string;
  feature_id: string;
  status: 'running' | 'completed' | 'failed';
  results: Record<string, any>;
  created_at: string;
}

export default function AdvancedAIPage() {
  const [features, setFeatures] = useState<AdvancedFeature[]>([]);
  const [experiments, setExperiments] = useState<AIExperiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [featuresRes, experimentsRes] = await Promise.all([
        api.get('/api/ai/advanced-ai/features'),
        api.get('/api/ai/advanced-ai/experiments')
      ]);
      setFeatures(featuresRes.data.features || []);
      setExperiments(experimentsRes.data.experiments || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleFeature = async (id: string, enabled: boolean) => {
    try {
      await api.patch(`/api/ai/advanced-ai/features/${id}`, { enabled: !enabled });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '更新功能失败');
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
        <h1 className="text-3xl font-bold text-gray-900">高级AI功能</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* 高级功能列表 */}
      <Card>
        <CardHeader>
          <CardTitle>高级功能</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((feature) => (
              <div key={feature.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{feature.name}</h3>
                  <Badge variant={
                    feature.status === 'available' ? 'default' :
                    feature.status === 'experimental' ? 'secondary' : 'destructive'
                  }>
                    {feature.status}
                  </Badge>
                </div>
                <Badge variant="outline" className="mb-2">{feature.category}</Badge>
                <p className="text-sm text-gray-600 mb-3">{feature.description}</p>
                <div className="space-y-1 text-xs text-gray-500 mb-3">
                  {feature.performance_metrics.accuracy && (
                    <div>准确率: {(feature.performance_metrics.accuracy * 100).toFixed(1)}%</div>
                  )}
                  {feature.performance_metrics.latency && (
                    <div>延迟: {feature.performance_metrics.latency}ms</div>
                  )}
                  {feature.performance_metrics.throughput && (
                    <div>吞吐量: {feature.performance_metrics.throughput}/s</div>
                  )}
                </div>
                <Button
                  variant={feature.enabled ? 'default' : 'outline'}
                  size="sm"
                  className="w-full"
                  onClick={() => handleToggleFeature(feature.id, feature.enabled)}
                >
                  {feature.enabled ? '已启用' : '启用'}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 实验记录 */}
      <Card>
        <CardHeader>
          <CardTitle>实验记录</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {experiments.map((experiment) => (
              <div key={experiment.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold">{experiment.name}</h3>
                  <Badge variant={
                    experiment.status === 'completed' ? 'default' :
                    experiment.status === 'running' ? 'secondary' : 'destructive'
                  }>
                    {experiment.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600 mb-2">功能ID: {experiment.feature_id}</div>
                {Object.keys(experiment.results).length > 0 && (
                  <div className="text-xs text-gray-500">
                    结果: {JSON.stringify(experiment.results)}
                  </div>
                )}
                <div className="text-xs text-gray-500 mt-1">
                  创建于: {new Date(experiment.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
