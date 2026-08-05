'use client'

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Metric {
  id: string;
  name: string;
  category: string;
  unit: string;
  currentValue: number;
  trend: 'up' | 'down' | 'stable';
  description: string;
}

interface ChartConfig {
  type: 'line' | 'bar' | 'area' | 'pie';
  title: string;
  metrics: string[];
  timeRange: string;
}

interface Snapshot {
  timestamp?: string;
  cpu?: { usage_percent?: number };
  memory?: { usage_percent?: number };
  disk?: any;
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  summary?: { total_alerts?: number; heal_rate?: number | string };
}

interface History {
  cpu?: number[];
  memory?: number[];
  net_in?: number[];
  timestamps?: string[];
  _meta?: { size?: number; maxlen?: number };
}

export default function MetricsExplorerPage() {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [chartType, setChartType] = useState<'line' | 'bar' | 'area' | 'pie'>('line');
  const [timeRange, setTimeRange] = useState('1h');

  useEffect(() => {
    let cancelled = false;

    async function loadMetrics() {
      try {
        const [snapshotRes, historyRes] = await Promise.all([
          api.get<Snapshot>('/api/v1/metrics/snapshot'),
          api.get<History>('/api/v1/metrics/history'),
        ]);

        if (cancelled) return;

        const snapshot = snapshotRes.data;
        const history = historyRes.data;

        function trend(series?: number[]): 'up' | 'down' | 'stable' {
          if (!series || series.length < 2) return 'stable';
          const last = series[series.length - 1];
          const prev = series[series.length - 2];
          if (last > prev + 0.01) return 'up';
          if (last < prev - 0.01) return 'down';
          return 'stable';
        }

        const diskItem = Array.isArray(snapshot.disk) ? snapshot.disk[0] : snapshot.disk;
        const diskUsage = typeof diskItem?.usage_percent === 'number' ? diskItem.usage_percent : 0;

        const derived: Metric[] = [
          {
            id: 'cpu',
            name: 'cpu_usage',
            category: '性能',
            unit: '%',
            currentValue: typeof snapshot.cpu?.usage_percent === 'number' ? snapshot.cpu.usage_percent : 0,
            trend: trend(history.cpu),
            description: 'CPU使用率',
          },
          {
            id: 'memory',
            name: 'memory_usage',
            category: '性能',
            unit: '%',
            currentValue: typeof snapshot.memory?.usage_percent === 'number' ? snapshot.memory.usage_percent : 0,
            trend: trend(history.memory),
            description: '内存使用率',
          },
          {
            id: 'disk',
            name: 'disk_usage',
            category: '存储',
            unit: '%',
            currentValue: diskUsage,
            trend: 'stable',
            description: '磁盘使用率',
          },
          {
            id: 'network_in',
            name: 'network_in',
            category: '网络',
            unit: 'MB/s',
            currentValue: typeof snapshot.network?.recv_speed_mb === 'number' ? snapshot.network.recv_speed_mb : 0,
            trend: trend(history.net_in),
            description: '网络入流量',
          },
          {
            id: 'network_out',
            name: 'network_out',
            category: '网络',
            unit: 'MB/s',
            currentValue: typeof snapshot.network?.sent_speed_mb === 'number' ? snapshot.network.sent_speed_mb : 0,
            trend: 'stable',
            description: '网络出流量',
          },
        ];

        setMetrics(derived);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err.message || '指标加载失败');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadMetrics();
    return () => {
      cancelled = true;
    };
  }, []);

  const categories = Array.from(new Set(metrics.map((m) => m.category)));

  const handleMetricToggle = (metricId: string) => {
    setSelectedMetrics((prev) =>
      prev.includes(metricId) ? prev.filter((id) => id !== metricId) : [...prev, metricId]
    );
  };

  const handleAddAll = () => {
    setSelectedMetrics(metrics.map((m) => m.id));
  };

  const handleClearAll = () => {
    setSelectedMetrics([]);
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '↑';
      case 'down':
        return '↓';
      case 'stable':
        return '→';
      default:
        return '-';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up':
        return 'text-red-600';
      case 'down':
        return 'text-green-600';
      case 'stable':
        return 'text-gray-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">指标探索器</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleAddAll}>
            全选
          </Button>
          <Button variant="outline" onClick={handleClearAll}>
            清空
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 指标浏览器 */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>指标浏览器</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-gray-500">加载中...</div>
            ) : error ? (
              <div className="text-red-600">{error}</div>
            ) : (
              <div className="space-y-4">
                {categories.map((category) => (
                  <div key={category}>
                    <h4 className="font-medium text-sm mb-2">{category}</h4>
                    <div className="space-y-2">
                      {metrics
                        .filter((m) => m.category === category)
                        .map((metric) => (
                          <div
                            key={metric.id}
                            className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 transition ${selectedMetrics.includes(metric.id) ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                              }`}
                            onClick={() => handleMetricToggle(metric.id)}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium text-sm">{metric.name}</span>
                              <span className={`text-xs ${getTrendColor(metric.trend)}`}>
                                {getTrendIcon(metric.trend)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-xs text-gray-500">
                              <span>{metric.currentValue} {metric.unit}</span>
                              <span>{metric.description}</span>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 图表区域 */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>指标对比图表</CardTitle>
              <div className="flex gap-2">
                <select
                  value={chartType}
                  onChange={(e) => setChartType(e.target.value as any)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="line">折线图</option>
                  <option value="bar">柱状图</option>
                  <option value="area">面积图</option>
                  <option value="pie">饼图</option>
                </select>
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="5m">5分钟</option>
                  <option value="1h">1小时</option>
                  <option value="6h">6小时</option>
                  <option value="24h">24小时</option>
                  <option value="7d">7天</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {selectedMetrics.length === 0 ? (
              <div className="h-96 flex items-center justify-center text-gray-400">
                请选择要对比的指标
              </div>
            ) : (
              <div className="space-y-4">
                <div className="h-96 bg-gray-50 rounded-lg flex items-center justify-center">
                  <p className="text-gray-500">
                    {chartType === 'line' ? '折线图' : chartType === 'bar' ? '柱状图' : chartType === 'area' ? '面积图' : '饼图'}区域
                    (使用ECharts渲染)
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedMetrics.map((id) => {
                    const metric = metrics.find((m) => m.id === id);
                    return (
                      <Badge key={id} variant="outline" className="cursor-pointer">
                        {metric?.name}
                      </Badge>
                    );
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 自定义图表配置 */}
      <Card>
        <CardHeader>
          <CardTitle>自定义图表</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">CPU vs 内存</h4>
              <p className="text-sm text-gray-600 mb-3">对比CPU和内存使用率</p>
              <Button variant="outline" size="sm" className="w-full">
                创建图表
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">网络流量概览</h4>
              <p className="text-sm text-gray-600 mb-3">网络入流量和出流量对比</p>
              <Button variant="outline" size="sm" className="w-full">
                创建图表
              </Button>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <h4 className="font-medium mb-2">业务性能指标</h4>
              <p className="text-sm text-gray-600 mb-3">请求速率、错误率和响应时间</p>
              <Button variant="outline" size="sm" className="w-full">
                创建图表
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 指标详情 */}
      {selectedMetrics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>指标详情</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {selectedMetrics.map((id) => {
                const metric = metrics.find((m) => m.id === id);
                if (!metric) return null;
                return (
                  <div key={id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h4 className="font-medium">{metric.name}</h4>
                        <p className="text-sm text-gray-500">{metric.description}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold">
                          {metric.currentValue} {metric.unit}
                        </p>
                        <p className={`text-sm ${getTrendColor(metric.trend)}`}>
                          {getTrendIcon(metric.trend)} {metric.trend === 'up' ? '上升' : metric.trend === 'down' ? '下降' : '稳定'}
                        </p>
                      </div>
                    </div>
                    <div className="h-32 bg-gray-50 rounded flex items-center justify-center">
                      <p className="text-xs text-gray-400">迷你图表</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
