'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

interface Metric {
  name: string;
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
}

export default function MetricsPage() {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['cpu_usage', 'memory_usage']);
  const [timeRange, setTimeRange] = useState('1h');
  const [searchQuery, setSearchQuery] = useState('');

  // 🔧 修复: 使用真实 API 获取指标快照
  const { data: snapshotData, isLoading, error } = useQuery({
    queryKey: ['metrics-snapshot'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/snapshot');
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  const [availableMetrics, setAvailableMetrics] = useState([
    { name: 'cpu_usage', label: 'CPU使用率', category: '系统' },
    { name: 'memory_usage', label: '内存使用率', category: '系统' },
    { name: 'disk_usage', label: '磁盘使用率', category: '系统' },
    { name: 'network_in', label: '网络入流量', category: '网络' },
    { name: 'network_out', label: '网络出流量', category: '网络' },
    { name: 'request_rate', label: '请求速率', category: '应用' },
    { name: 'response_time', label: '响应时间', category: '应用' },
    { name: 'error_rate', label: '错误率', category: '应用' },
  ]);

  // 🔧 修复: 从 API 数据转换当前指标
  const [currentMetrics, setCurrentMetrics] = useState<Metric[]>([
    { name: 'CPU使用率', value: 65, unit: '%', trend: 'up' },
    { name: '内存使用率', value: 55, unit: '%', trend: 'stable' },
  ]);

  // 同步 API 数据
  useEffect(() => {
    if (snapshotData && snapshotData.metrics) {
      const metrics: Metric[] = snapshotData.metrics.map((m: any) => ({
        name: m.name || m.key || '未知指标',
        value: m.value || 0,
        unit: m.unit || '',
        trend: m.trend || 'stable',
      }));
      setCurrentMetrics(metrics);
    }
  }, [snapshotData]);

  const filteredMetrics = availableMetrics.filter(m =>
    m.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleMetric = (metricName: string) => {
    setSelectedMetrics(prev =>
      prev.includes(metricName)
        ? prev.filter(m => m !== metricName)
        : [...prev, metricName]
    );
  };

  if (isLoading) return <div className="text-center text-gray-500">加载中...</div>;
  if (error) return <div className="text-center text-red-500">加载失败</div>;

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
          <Button>刷新</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 指标选择器 */}
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
              {filteredMetrics.map((metric) => (
                <div
                  key={metric.name}
                  className={`p-3 rounded-lg cursor-pointer transition ${
                    selectedMetrics.includes(metric.name)
                      ? 'bg-blue-100 border-2 border-blue-500'
                      : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                  }`}
                  onClick={() => toggleMetric(metric.name)}
                >
                  <div className="font-medium">{metric.label}</div>
                  <div className="text-xs text-gray-500">{metric.category}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 指标图表 */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>指标对比</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
              <p className="text-gray-500">指标对比图表 (使用ECharts渲染)</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 当前指标值 */}
      <Card>
        <CardHeader>
          <CardTitle>当前指标值</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {currentMetrics.map((metric) => (
              <div key={metric.name} className="p-4 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-1">{metric.name}</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold">{metric.value}</span>
                  <span className="text-sm text-gray-500">{metric.unit}</span>
                </div>
                <div className="text-sm mt-1">
                  {metric.trend === 'up' ? '📈 上升' : metric.trend === 'down' ? '📉 下降' : '➡️ 稳定'}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 指标统计 */}
      <Card>
        <CardHeader>
          <CardTitle>指标统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">平均值</div>
              <div className="text-2xl font-bold">60.5</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">最大值</div>
              <div className="text-2xl font-bold">85.2</div>
            </div>
            <div className="p-4 border border-gray-200 rounded-lg">
              <div className="text-sm text-gray-500 mb-1">最小值</div>
              <div className="text-2xl font-bold">42.3</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
