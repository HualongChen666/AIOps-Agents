'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface VMMetric {
  name?: string;
  value?: number;
  timestamp?: string;
  labels?: Record<string, string>;
  [key: string]: any;
}

interface VictoriaMetricsData {
  vm_url?: string;
  vm_version?: string;
  total_metrics?: number;
  series_count?: number;
  data_size_gb?: number;
  retention_days?: number;
  metrics?: VMMetric[];
  query?: string;
  [key: string]: any;
}

export default function VictoriaMetricsPage() {
  const [query, setQuery] = useState('up');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: vmData, refetch } = useQuery<VictoriaMetricsData>({
    queryKey: ['monitoring-victoriametrics', query],
    queryFn: async () => {
      if (!query.trim()) return { metrics: [] };
      const resp = await api.get('/api/v1/monitoring/victoriametrics', {
        params: { query }
      });
      return resp.data;
    },
    enabled: query.length > 0,
    refetchInterval: false,
  });

  const handleQuery = async () => {
    setIsQuerying(true);
    await refetch();
    setIsQuerying(false);
  };

  if (!vmData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">VictoriaMetrics</h1>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>MetricsQL查询</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="输入MetricsQL查询..."
                  className="flex-1"
                  onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
                />
                <Button onClick={handleQuery} disabled={isQuerying}>
                  {isQuerying ? '查询中...' : '查询'}
                </Button>
              </div>
              <div className="text-sm text-gray-500">
                示例查询: up, rate(http_requests_total[5m]), cpu_usage_percent
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">VictoriaMetrics</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>VictoriaMetrics信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">URL:</span>
              <span className="font-medium">{vmData?.vm_url || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">版本:</span>
              <span className="font-medium">{vmData?.vm_version || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">总指标数:</span>
              <span className="font-medium">{vmData?.total_metrics?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">时间序列数:</span>
              <span className="font-medium">{vmData?.series_count?.toLocaleString() || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">数据大小:</span>
              <span className="font-medium">{vmData?.data_size_gb?.toFixed(2) || '-'} GB</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">保留期:</span>
              <span className="font-medium">{vmData?.retention_days || '-'} 天</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>MetricsQL查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入MetricsQL查询..."
                className="flex-1"
                onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              />
              <Button onClick={handleQuery} disabled={isQuerying}>
                {isQuerying ? '查询中...' : '查询'}
              </Button>
            </div>
            <div className="text-sm text-gray-500">
              示例查询: up, rate(http_requests_total[5m]), cpu_usage_percent
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>查询结果</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">指标名称</th>
                  <th className="px-4 py-2 text-left">标签</th>
                  <th className="px-4 py-2 text-left">值</th>
                  <th className="px-4 py-2 text-left">时间</th>
                </tr>
              </thead>
              <tbody>
                {vmData?.metrics?.map((metric, i) => (
                  <tr key={i} className="border-t">
                    <td className="px-4 py-2">{metric.name}</td>
                    <td className="px-4 py-2">
                      <div className="flex flex-wrap gap-1">
                        {metric.labels && Object.entries(metric.labels).map(([key, value], j) => (
                          <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                            {key}={value}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-2">{metric.value?.toFixed(4)}</td>
                    <td className="px-4 py-2">
                      {metric.timestamp ? new Date(metric.timestamp * 1000).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
