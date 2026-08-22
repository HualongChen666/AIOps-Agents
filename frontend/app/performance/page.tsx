'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useQuery } from '@tanstack/react-query';
import { useRealtimeData } from '@/hooks/useWebSocket';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Activity, Cpu, HardDrive, MemoryStick, RefreshCw, Wifi, WifiOff, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCard {
  key: string;
  label: string;
  value: string;
  unit: string;
  level: 'normal' | 'warning' | 'critical';
  history: number[];
  icon: React.ReactNode;
}

interface MetricsSnapshot {
  cpu?: { usage_percent: number };
  memory?: { usage_percent: number };
  disk?: { usage_percent: number };
}

interface MetricsHistory {
  cpu?: number[];
  memory?: number[];
  disk?: number[];
}

export default function PerformancePage() {
  // 🔧 获取性能快照
  const { data: snapshotData, isLoading: snapshotLoading, error: snapshotError, refetch: refetchSnapshot } = useQuery<MetricsSnapshot>({
    queryKey: ['metrics-snapshot'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/snapshot');
      return resp.data;
    },
    refetchInterval: 5000, // 5秒刷新
  });

  // 🔧 获取性能历史
  const { data: historyData, isLoading: historyLoading, error: historyError, refetch: refetchHistory } = useQuery<MetricsHistory>({
    queryKey: ['metrics-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/metrics/history');
      return resp.data;
    },
    refetchInterval: 10000, // 10秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(snapshotLoading || historyLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const [metrics, setMetrics] = useState<MetricCard[]>([]);

  // 🔧 Week 7: 实时数据优化 - SSE实时性能监控
  const { isConnected: sseConnected, data: realtimeMetrics } = useRealtimeData<MetricsSnapshot>('/api/v1/sse/events', {
    enabled: true,
    reconnectInterval: 5000,
    maxReconnectAttempts: 5,
    onEvent: (event) => {
      if (event.type === 'message' && event.data) {
        // 实时更新性能数据
        updateMetricsFromSnapshot(event.data, historyData);
      }
    },
  });

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (snapshotError) {
      showError('Failed to load metrics snapshot');
      setPageError(snapshotError as Error);
    }
    if (historyError) {
      showError('Failed to load metrics history');
      setPageError(historyError as Error);
    }
  }, [snapshotError, historyError, showError, setPageError]);

  const updateMetricsFromSnapshot = (snapshot: MetricsSnapshot | null, history: MetricsHistory | null | undefined) => {
    if (!snapshot) return;

    const getLevel = (value: number | null): MetricCard['level'] => {
      if (value === null) return 'normal';
      if (value >= 90) return 'critical';
      if (value >= 70) return 'warning';
      return 'normal';
    };

    const getValue = (value: number | null): string => {
      if (value === null || Number.isNaN(value)) return '--';
      return value.toFixed(1);
    };

    const getHistory = (key: string): number[] => {
      const raw = history?.[key as keyof MetricsHistory];
      if (!Array.isArray(raw)) return [];
      return raw.slice(-20).map((v) => Number(v) || 0);
    };

    const cpu = typeof snapshot.cpu?.usage_percent === 'number' ? snapshot.cpu.usage_percent : null;
    const memory = typeof snapshot.memory?.usage_percent === 'number' ? snapshot.memory.usage_percent : null;
    const disk = typeof snapshot.disk?.usage_percent === 'number' ? snapshot.disk.usage_percent : null;

    setMetrics([
      {
        key: 'cpu',
        label: 'CPU 使用率',
        value: getValue(cpu),
        unit: '%',
        level: getLevel(cpu),
        history: getHistory('cpu'),
        icon: <Cpu className="h-5 w-5" />,
      },
      {
        key: 'memory',
        label: '内存使用率',
        value: getValue(memory),
        unit: '%',
        level: getLevel(memory),
        history: getHistory('memory'),
        icon: <MemoryStick className="h-5 w-5" />,
      },
      {
        key: 'disk',
        label: '磁盘使用率',
        value: getValue(disk),
        unit: '%',
        level: getLevel(disk),
        history: getHistory('disk'),
        icon: <HardDrive className="h-5 w-5" />,
      },
    ]);
  };

  useEffect(() => {
    updateMetricsFromSnapshot(snapshotData || null, historyData || null);
  }, [snapshotData, historyData]);

  const getLevelText = (level: string) => {
    switch (level) {
      case 'critical': return '严重';
      case 'warning': return '警告';
      case 'normal': return '正常';
      default: return level;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'normal': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const renderTrend = (history: number[]) => {
    if (history.length === 0) {
      return <p className="text-xs text-gray-400 mt-2">暂无历史趋势数据</p>;
    }
    const max = Math.max(1, ...history);
    const last = history[history.length - 1];
    const prev = history[history.length - 2] || last;
    const trend = last > prev ? 'up' : last < prev ? 'down' : 'stable';

    return (
      <div className="space-y-2 mt-3">
        <div className="flex items-center gap-2 text-xs">
          {trend === 'up' ? (
            <TrendingUp className="h-3 w-3 text-red-500" />
          ) : trend === 'down' ? (
            <TrendingDown className="h-3 w-3 text-green-500" />
          ) : null}
          <span className="text-gray-500">
            {trend === 'up' ? '上升' : trend === 'down' ? '下降' : '稳定'}
          </span>
        </div>
        <div className="flex items-end h-16 gap-1">
          {history.map((value, index) => (
            <div
              key={index}
              className="flex-1 bg-blue-400 rounded-sm opacity-80 hover:opacity-100 transition"
              style={{ height: `${Math.round((value / max) * 100)}%` }}
              title={`${value.toFixed(1)}%`}
            />
          ))}
        </div>
      </div>
    );
  };

  // 🔧 P1 Integration: Use enhanced loading and empty states
  if (pageLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (pageError) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载性能数据，请稍后重试"
          action={<Button onClick={() => { refetchSnapshot(); refetchHistory(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchSnapshot(); refetchHistory(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">性能监控</h1>
            <p className="text-sm text-gray-500">实时监控系统性能指标</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-sm">
            {sseConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span className="text-green-600">实时连接</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-gray-400" />
                <span className="text-gray-500">离线</span>
              </>
            )}
          </div>
          <Button onClick={() => { refetchSnapshot(); refetchHistory(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {metrics.length === 0 ? (
        <EmptyState
          title="暂无性能指标"
          description="当前没有可用的性能数据"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {metrics.map((m) => (
            <Card key={m.key} className="hover:shadow-md transition">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {m.icon}
                    <CardTitle className="text-sm">{m.label}</CardTitle>
                  </div>
                  <Badge className={getLevelColor(m.level)}>
                    {getLevelText(m.level)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className={`text-3xl font-bold ${m.level === 'critical' ? 'text-red-600' : m.level === 'warning' ? 'text-yellow-600' : 'text-green-600'}`}>
                  {m.value}
                  <span className="text-sm font-normal text-gray-500 ml-1">{m.unit}</span>
                </p>
                <p className="text-xs text-gray-500 mt-1">实时快照 / 历史趋势</p>
                {renderTrend(m.history)}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
