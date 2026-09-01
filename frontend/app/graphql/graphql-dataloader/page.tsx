'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface DataLoaderConfig {
  max_batch_size: number;
  cache_enabled: boolean;
  batch_strategy: string;
}

interface BatchLoadStats {
  total_batches: number;
  total_items_loaded: number;
  average_batch_size: number;
  max_batch_size_used: number;
  cache_hit_rate: number;
}

interface PerformanceMetrics {
  total_load_time_ms: number;
  average_load_time_ms: number;
  p50_load_time_ms: number;
  p95_load_time_ms: number;
  p99_load_time_ms: number;
}

interface DataLoaderStatus {
  config: DataLoaderConfig;
  batch_stats: BatchLoadStats;
  performance: PerformanceMetrics;
  active_loaders: string[];
  enabled: boolean;
}

export default function GraphqlDataloaderPage() {
  const [status, setStatus] = useState<DataLoaderStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/graphql/graphql-dataloader');
      setStatus(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const clearCache = async (loaderType?: string) => {
    try {
      await api.post('/api/graphql/graphql-dataloader/clear-cache', null, {
        params: loaderType ? { loader_type: loaderType } : {}
      });
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '清除缓存失败');
    }
  };

  const runTest = async () => {
    try {
      await api.get('/api/graphql/graphql-dataloader/test');
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '测试失败');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  if (!status) {
    return <div className="text-gray-500">无数据</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">GraphQL DataLoader</h1>
        <div className="space-x-2">
          <Button onClick={fetchData}>刷新</Button>
          <Button onClick={runTest} variant="outline">运行测试</Button>
          <Button onClick={() => clearCache()} variant="outline">清除所有缓存</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>配置信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">启用状态:</span>
              <Badge variant={status.enabled ? 'default' : 'secondary'}>
                {status.enabled ? '已启用' : '已禁用'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">最大批次大小:</span>
              <span className="font-medium">{status.config.max_batch_size}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">缓存启用:</span>
              <Badge variant={status.config.cache_enabled ? 'default' : 'secondary'}>
                {status.config.cache_enabled ? '是' : '否'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">批次策略:</span>
              <span className="font-medium">{status.config.batch_strategy}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>批量加载统计</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">总批次数:</span>
              <span className="font-medium">{status.batch_stats.total_batches}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">总加载项数:</span>
              <span className="font-medium">{status.batch_stats.total_items_loaded}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">平均批次大小:</span>
              <span className="font-medium">{status.batch_stats.average_batch_size}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">最大批次大小:</span>
              <span className="font-medium">{status.batch_stats.max_batch_size_used}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">缓存命中率:</span>
              <span className="font-medium">{status.batch_stats.cache_hit_rate}%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>性能指标</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">总加载时间:</span>
              <span className="font-medium">{status.performance.total_load_time_ms.toFixed(3)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">平均加载时间:</span>
              <span className="font-medium">{status.performance.average_load_time_ms.toFixed(3)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">P50 延迟:</span>
              <span className="font-medium">{status.performance.p50_load_time_ms.toFixed(3)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">P95 延迟:</span>
              <span className="font-medium">{status.performance.p95_load_time_ms.toFixed(3)} ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">P99 延迟:</span>
              <span className="font-medium">{status.performance.p99_load_time_ms.toFixed(3)} ms</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>活跃加载器</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {status.active_loaders.length > 0 ? (
                status.active_loaders.map((loader) => (
                  <Badge key={loader} variant="default">
                    {loader}
                  </Badge>
                ))
              ) : (
                <span className="text-gray-500">无活跃加载器</span>
              )}
            </div>
            <div className="mt-4 space-x-2">
              <Button onClick={() => clearCache('alert')} size="sm" variant="outline">清除Alert缓存</Button>
              <Button onClick={() => clearCache('repair')} size="sm" variant="outline">清除Repair缓存</Button>
              <Button onClick={() => clearCache('metrics')} size="sm" variant="outline">清除Metrics缓存</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
