'use client'

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import api from '@/lib/api';

interface Snapshot {
  timestamp?: string;
  cpu?: { usage_percent?: number; cores?: number };
  memory?: { usage_percent?: number; total_gb?: number };
  network?: { recv_speed_mb?: number; sent_speed_mb?: number };
  disk?: any;
}

interface History {
  cpu?: number[];
  memory?: number[];
  net_in?: number[];
  timestamps?: string[];
  _meta?: { size?: number; maxlen?: number };
}

interface TrendPoint {
  t: string;
  v: number;
}

const chartTypes = [
  { id: 'line', name: '折线图' },
  { id: 'area', name: '面积图' },
  { id: 'bar', name: '柱状图' },
];

function buildSeries(values: number[] = [], timestamps: string[] = []): TrendPoint[] {
  return values.map((v, i) => ({
    t: timestamps[i] || '',
    v: typeof v === 'number' ? v : 0,
  }));
}

function MetricTrendChart({
  data,
  color,
  type,
  label,
  unit,
}: {
  data: TrendPoint[];
  color: string;
  type: string;
  label: string;
  unit: string;
}) {
  if (data.length === 0) {
    return (
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-700 mb-2">{label}</div>
        <div className="text-center text-gray-500 py-12">暂无数据</div>
      </div>
    );
  }

  const current = data[data.length - 1].v;
  const values = data.map((d) => d.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const width = 600;
  const height = 200;
  const pad = 30;

  const points = data.map((d, i) => {
    const x = pad + (width - 2 * pad) * (i / Math.max(1, data.length - 1));
    const y = height - pad - ((d.v - min) / range) * (height - 2 * pad);
    return `${x},${y}`;
  });

  const linePath = `M ${points.join(' L ')}`;
  const areaPath = `${linePath} L ${width - pad} ${height - pad} L ${pad} ${height - pad} Z`;
  const barWidth = (width - 2 * pad) / data.length;

  return (
    <div className="mb-6">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm text-gray-600">
          当前: {current.toFixed(1)} {unit}
        </span>
      </div>
      <div className="w-full h-64">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full"
          preserveAspectRatio="none"
        >
          <rect x="0" y="0" width={width} height={height} fill="#ffffff" />
          {Array.from({ length: 5 }).map((_, i) => {
            const y = pad + (height - 2 * pad) * (i / 4);
            return (
              <line
                key={`grid-${i}`}
                x1={pad}
                y1={y}
                x2={width - pad}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth={1}
              />
            );
          })}
          {type !== 'bar' && type === 'area' && (
            <path d={areaPath} fill={color} fillOpacity={0.2} stroke="none" />
          )}
          {type !== 'bar' && (
            <path d={linePath} fill="none" stroke={color} strokeWidth={2} />
          )}
          {type === 'bar' &&
            data.map((d, i) => {
              const h = ((d.v - min) / range) * (height - 2 * pad);
              const x = pad + i * barWidth;
              const y = height - pad - h;
              return (
                <rect
                  key={`bar-${i}`}
                  x={x + 1}
                  y={y}
                  width={Math.max(1, barWidth - 2)}
                  height={h}
                  fill={color}
                />
              );
            })}
        </svg>
      </div>
      <div className="text-xs text-gray-500 mt-2 flex justify-between">
        <span>最低: {min.toFixed(1)} {unit}</span>
        <span>最高: {max.toFixed(1)} {unit}</span>
      </div>
    </div>
  );
}

export default function AdvancedChartsPage() {
  const [activeChart, setActiveChart] = useState('line');
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [snapRes, histRes] = await Promise.all([
        api.get<Snapshot>('/api/v1/metrics/snapshot'),
        api.get<History>('/api/v1/metrics/history?hours=24'),
      ]);
      setSnapshot(snapRes.data);
      setHistory(histRes.data);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || '数据加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const cpu = useMemo(
    () => buildSeries(history?.cpu, history?.timestamps),
    [history]
  );
  const memory = useMemo(
    () => buildSeries(history?.memory, history?.timestamps),
    [history]
  );
  const netIn = useMemo(
    () => buildSeries(history?.net_in, history?.timestamps),
    [history]
  );

  const current = {
    cpu:
      typeof snapshot?.cpu?.usage_percent === 'number'
        ? snapshot.cpu.usage_percent
        : cpu[cpu.length - 1]?.v ?? 0,
    memory:
      typeof snapshot?.memory?.usage_percent === 'number'
        ? snapshot.memory.usage_percent
        : memory[memory.length - 1]?.v ?? 0,
    netIn:
      typeof snapshot?.network?.recv_speed_mb === 'number'
        ? snapshot.network.recv_speed_mb
        : netIn[netIn.length - 1]?.v ?? 0,
    netOut:
      typeof snapshot?.network?.sent_speed_mb === 'number'
        ? snapshot.network.sent_speed_mb
        : 0,
  };

  const metricCards = [
    { id: 'cpu', name: 'CPU 使用率', unit: '%', value: current.cpu },
    { id: 'memory', name: '内存使用率', unit: '%', value: current.memory },
    { id: 'network', name: '网络入流量', unit: 'MB/s', value: current.netIn },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">指标趋势看板</h1>
        <div className="flex items-center gap-2">
          <Select
            value={activeChart}
            onChange={(e) => setActiveChart(e.target.value)}
          >
            {chartTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </Select>
          <Button onClick={loadData} disabled={loading}>
            刷新
          </Button>
        </div>
      </div>

      {loading && <div className="text-center text-gray-500">加载中…</div>}
      {error && <div className="text-center text-red-500">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metricCards.map((metric) => (
          <Card key={metric.id}>
            <CardHeader>
              <CardTitle className="text-sm">{metric.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900">
                {metric.value.toFixed(1)}
                <span className="text-sm font-normal text-gray-500 ml-1">
                  {metric.unit}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>指标说明</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm text-gray-600">
              <p>
                <strong>CPU 使用率:</strong> 系统 CPU 平均使用百分比。
              </p>
              <p>
                <strong>内存使用率:</strong> 物理内存使用百分比。
              </p>
              <p>
                <strong>网络入流量:</strong> 每秒接收流量(MB/s)。
              </p>
              <p>
                数据来源:{' '}
                <code className="bg-gray-100 px-1 rounded">
                  /api/v1/metrics/snapshot
                </code>{' '}
                与{' '}
                <code className="bg-gray-100 px-1 rounded">
                  /api/v1/metrics/history?hours=24
                </code>
                。
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>实时趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <MetricTrendChart
              label="CPU 使用率"
              unit="%"
              data={cpu}
              color="#3b82f6"
              type={activeChart}
            />
            <MetricTrendChart
              label="内存使用率"
              unit="%"
              data={memory}
              color="#10b981"
              type={activeChart}
            />
            <MetricTrendChart
              label="网络入流量"
              unit="MB/s"
              data={netIn}
              color="#f59e0b"
              type={activeChart}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
