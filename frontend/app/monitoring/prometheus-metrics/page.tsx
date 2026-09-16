'use client'

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

// The backend returns one entry per PromQL series: `metric` holds the label
// set and either a single `value` (`[ts, "val"]`) for instant queries or a
// `values` matrix (`[[ts, "val"], ...]`) for range queries.
interface PrometheusSeries {
  metric?: Record<string, string>;
  value?: [number, string];
  values?: Array<[number, string]>;
  [key: string]: any;
}

interface PrometheusMetricsData {
  prometheus_url?: string;
  query?: string;
  metrics?: PrometheusSeries[];
  [key: string]: any;
}

function seriesName(sample: PrometheusSeries, fallback: string): string {
  const labels = sample.metric || {};
  return labels.__name__ || fallback;
}

function seriesPoint(sample: PrometheusSeries): { timestamp: number | null; value: number | null } {
  const raw = sample.value ?? (sample.values && sample.values[sample.values.length - 1]);
  if (!raw || raw.length < 2) return { timestamp: null, value: null };
  const ts = Number(raw[0]);
  const value = Number(raw[1]);
  return {
    timestamp: Number.isFinite(ts) ? ts : null,
    value: Number.isFinite(value) ? value : null,
  };
}

export default function PrometheusMetricsPage() {
  const [query, setQuery] = useState('up');
  const [isQuerying, setIsQuerying] = useState(false);

  const { data: prometheusData, refetch } = useQuery<PrometheusMetricsData>({
    queryKey: ['monitoring-prometheus-metrics', query],
    queryFn: async () => {
      if (!query.trim()) return { metrics: [] };
      const resp = await api.get('/api/v1/monitoring/prometheus-metrics', {
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

  const queryForm = (
    <Card>
      <CardHeader>
        <CardTitle>PromQL查询</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入PromQL查询..."
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
  );

  if (!prometheusData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Prometheus指标</h1>
        </div>
        {queryForm}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Prometheus指标</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Prometheus信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex justify-between">
              <span className="text-gray-500">Prometheus URL:</span>
              <span className="font-medium">{prometheusData?.prometheus_url || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">查询:</span>
              <span className="font-medium">{prometheusData?.query || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">返回序列数:</span>
              <span className="font-medium">{prometheusData?.metrics?.length ?? '-'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {queryForm}

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
                {prometheusData?.metrics?.length ? (
                  prometheusData.metrics.map((sample, i) => {
                    const { timestamp, value } = seriesPoint(sample);
                    const labels = Object.entries(sample.metric || {});
                    return (
                      <tr key={i} className="border-t">
                        <td className="px-4 py-2">{seriesName(sample, prometheusData.query || '-')}</td>
                        <td className="px-4 py-2">
                          <div className="flex flex-wrap gap-1">
                            {labels.map(([key, valueText], j) => (
                              <span key={j} className="px-2 py-1 bg-gray-100 rounded text-xs">
                                {key}={valueText}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-4 py-2">{value !== null ? value.toFixed(4) : '-'}</td>
                        <td className="px-4 py-2">
                          {timestamp !== null ? new Date(timestamp * 1000).toLocaleString() : '-'}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr className="border-t">
                    <td colSpan={4} className="px-4 py-4 text-center text-gray-500">无查询结果</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
