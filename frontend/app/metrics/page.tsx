'use client'

import { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

const METRIC_LABELS: Record<string, string> = {
  cpu: 'CPU使用率',
  memory: '内存使用率',
  net_in: '网络入流量',
};

const METRIC_UNITS: Record<string, string> = {
  cpu: '%',
  memory: '%',
  net_in: 'MB/s',
};

const CHART_COLORS = ['#2563eb', '#dc2626', '#16a34a'];

interface SnapshotData {
  cpu?: { usage_percent?: number };
  memory?: { usage_percent?: number };
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  [key: string]: any;
}

interface HistoryData {
  cpu?: number[];
  memory?: number[];
  net_in?: number[];
  timestamps?: string[];
  _meta?: any;
  [key: string]: any;
}

export default function MetricsPage() {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['cpu', 'memory']);
  const [timeRange, setTimeRange] = useState('1h');
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data: snapshotData,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useQuery<SnapshotData>({
    queryKey: ['metrics-snapshot'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/snapshot');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const {
    data: historyData,
    isLoading: historyLoading,
    error: historyError,
  } = useQuery<HistoryData>({
    queryKey: ['metrics-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/history');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const availableMetrics = useMemo(() => {
    if (!historyData) return [] as string[];
    return Object.keys(historyData).filter((k) => k !== '_meta' && k !== 'timestamps');
  }, [historyData]);

  const getMetricValue = (metric: string): number | null => {
    if (!snapshotData) return null;
    if (metric === 'cpu') return snapshotData.cpu?.usage_percent ?? null;
    if (metric === 'memory') return snapshotData.memory?.usage_percent ?? null;
    if (metric === 'net_in') return snapshotData.network?.recv_speed_mb ?? null;
    if (metric === 'network_out') return snapshotData.network?.sent_speed_mb ?? null;
    return null;
  };

  const getTrend = (metric: string): 'up' | 'down' | 'stable' => {
    const series = historyData?.[metric];
    if (!Array.isArray(series) || series.length < 2) return 'stable';
    const diff = series[series.length - 1] - series[series.length - 2];
    if (diff > 1e-6) return 'up';
    if (diff < -1e-6) return 'down';
    return 'stable';
  };

  const filteredMetrics = availableMetrics.filter(
    (m) =>
      (METRIC_LABELS[m] || m).toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleMetric = (metricName: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricName)
        ? prev.filter((m) => m !== metricName)
        : [...prev, metricName]
    );
  };

  const selectedForChart = selectedMetrics.filter((m) => availableMetrics.includes(m));

  const chartStats = useMemo(() => {
    const allValues: number[] = [];
    selectedForChart.forEach((m) => {
      const series = historyData?.[m];
      if (Array.isArray(series)) {
        series.forEach((v) => {
          if (typeof v === 'number') allValues.push(v);
        });
      }
    });
    if (allValues.length === 0) return { avg: null, max: null, min: null };
    const sum = allValues.reduce((a, b) => a + b, 0);
    return {
      avg: (sum / allValues.length).toFixed(2),
      max: Math.max(...allValues).toFixed(2),
      min: Math.min(...allValues).toFixed(2),
    };
  }, [historyData, selectedForChart]);

  const isLoading = snapshotLoading || historyLoading;
  const error = snapshotError || historyError;

  if (isLoading) return <div className="text-center text-gray-500">加载中...</div>;
  if (error) return <div className="text-center text-red-500">加载失败</div>;

  const renderChart = () => {
    if (selectedForChart.length === 0 || !historyData) {
      return <p className="text-gray-500">请选择至少一个指标</p>;
    }

    const width = 800;
    const height = 300;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    let allValues: number[] = [];
    selectedForChart.forEach((m) => {
      const series = historyData[m];
      if (Array.isArray(series)) allValues = allValues.concat(series);
    });
    if (allValues.length === 0) return <p className="text-gray-500">暂无历史数据</p>;

    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const range = max - min || 1;

    const points = (metric: string) => {
      const series = historyData[metric];
      if (!Array.isArray(series) || series.length === 0) return '';
      const stepX = chartWidth / (series.length - 1 || 1);
      return series
        .map((v, i) => {
          const x = padding + i * stepX;
          const y = padding + chartHeight - ((v - min) / range) * chartHeight;
          return `${x},${y}`;
        })
        .join(' ');
    };

    return (
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-80" preserveAspectRatio="xMidYMid meet">
          <rect x={padding} y={padding} width={chartWidth} height={chartHeight} fill="#f9fafb" />
          <line x1={padding} y1={padding + chartHeight} x2={padding + chartWidth} y2={padding + chartHeight} stroke="#d1d5db" />
          <line x1={padding} y1={padding} x2={padding} y2={padding + chartHeight} stroke="#d1d5db" />
          {selectedForChart.map((m, i) => (
            <polyline
              key={m}
              fill="none"
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              points={points(m)}
            />
          ))}
        </svg>
        <div className="flex flex-wrap gap-4 mt-2">
          {selectedForChart.map((m, i) => (
            <div key={m} className="flex items-center gap-2 text-sm">
              <span
                className="inline-block w-3 h-3 rounded-full"
                style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
              />
              <span>{METRIC_LABELS[m] || m}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">指标探索器</h1>
        <div className="flex gap-2">
          <Select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </Select>
          <Button onClick={() => window.location.reload()}>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-sm">指标选择</CardTitle>
          </CardHeader>
          <CardContent>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索指标..."
              className="mb-4"
            />
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {filteredMetrics.length === 0 ? (
                <p className="text-sm text-gray-500">暂无指标</p>
              ) : (
                filteredMetrics.map((metric) => (
                  <div
                    key={metric}
                    className={`p-3 rounded-lg cursor-pointer transition ${selectedMetrics.includes(metric)
                        ? 'bg-blue-100 border-2 border-blue-500'
                        : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                      }`}
                    onClick={() => toggleMetric(metric)}
                  >
                    <div className="font-medium">{METRIC_LABELS[metric] || metric}</div>
                    <div className="text-xs text-gray-500">{METRIC_UNITS[metric] || ''}</div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>指标对比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
              {renderChart()}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>当前指标值</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {availableMetrics.length === 0 ? (
              <p className="text-sm text-gray-500">暂无指标数据</p>
            ) : (
              availableMetrics.map((metric) => {
                const value = getMetricValue(metric);
                const trend = getTrend(metric);
                return (
                  <div key={metric} className="p-4 border border-gray-200 rounded-lg">
                    <div className="text-sm text-gray-500 mb-1">{METRIC_LABELS[metric] || metric}</div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-2xl font-bold">{value ?? '-'}</span>
                      <span className="text-sm text-gray-500">{METRIC_UNITS[metric] || ''}</span>
                    </div>
                    <div className="text-sm mt-1">
                      {trend === 'up' ? '上升' : trend === 'down' ? '下降' : '稳定'}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>指标统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">平均值</div>
              <div className="text-2xl font-bold">{chartStats.avg ?? '-'}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">最大值</div>
              <div className="text-2xl font-bold">{chartStats.max ?? '-'}</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">最小值</div>
              <div className="text-2xl font-bold">{chartStats.min ?? '-'}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
