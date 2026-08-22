'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { KpiCard } from '@/components/ui/KpiCard';
import { DataTable } from '@/components/ui/DataTable';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { Activity, RefreshCw, Zap, Cpu, HardDrive, Network, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface APMetrics {
  request_count: number;
  error_rate: number;
  slow_request_rate: number;
  throughput: number;
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
}

interface APMHealth {
  application: string;
  version: string;
  health_status: {
    status: string;
    checks: Record<string, any>;
  };
  timestamp: string;
}

interface APMTrace {
  trace_id: string;
  endpoint: string;
  duration_ms: number;
  status: string;
  timestamp: string;
}

export default function APMPage() {
  const [timeRange, setTimeRange] = useState('1h');

  // 🔧 获取APM指标
  const { data: apmMetricsData, isLoading: metricsLoading, error: metricsError, refetch: refetchMetrics } = useQuery<APMetrics>({
    queryKey: ['apm-metrics', timeRange],
    queryFn: async () => {
      const resp = await api.get('/api/v1/apm/metrics');
      return resp.data.apm_metrics;
    },
    refetchInterval: 10000, // 10秒刷新
  });

  // 🔧 获取APM健康状态
  const { data: apmHealthData, isLoading: healthLoading, error: healthError, refetch: refetchHealth } = useQuery<APMHealth>({
    queryKey: ['apm-health'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/apm/health');
      return resp.data;
    },
    refetchInterval: 30000, // 30秒刷新
  });

  // 🔧 获取APM追踪
  const { data: apmTracesData, isLoading: tracesLoading, error: tracesError, refetch: refetchTraces } = useQuery<{ traces: APMTrace[] }>({
    queryKey: ['apm-traces'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/apm/traces?limit=20');
      return resp.data;
    },
    refetchInterval: 15000, // 15秒刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(metricsLoading || healthLoading || tracesLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (metricsError) {
      showError('Failed to load APM metrics');
      setPageError(metricsError as Error);
    }
    if (healthError) {
      showError('Failed to load APM health data');
      setPageError(healthError as Error);
    }
    if (tracesError) {
      showError('Failed to load APM traces');
      setPageError(tracesError as Error);
    }
  }, [metricsError, healthError, tracesError, showError, setPageError]);

  const apmMetrics: APMetrics = apmMetricsData || {
    request_count: 0,
    error_rate: 0,
    slow_request_rate: 0,
    throughput: 0,
    latency_p50: 0,
    latency_p95: 0,
    latency_p99: 0,
  };
  const apmHealth = apmHealthData || { application: '', version: '', health_status: { status: '', checks: {} }, timestamp: '' };
  const apmTraces = apmTracesData?.traces || [];

  const traceColumns = [
    { key: 'trace_id' as const, label: '追踪ID' },
    { key: 'endpoint' as const, label: '端点' },
    { key: 'duration_ms' as const, label: '持续时间', render: (value: number) => `${value.toFixed(2)}ms` },
    { key: 'status' as const, label: '状态' },
    { key: 'timestamp' as const, label: '时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

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
          description="无法加载APM数据，请稍后重试"
          action={<Button onClick={() => { refetchMetrics(); refetchHealth(); refetchTraces(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchMetrics(); refetchHealth(); refetchTraces(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const throughput = apmMetrics.throughput || 0;
  const errorRate = apmMetrics.error_rate || 0;
  const latencyP95 = apmMetrics.latency_p95 || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">APM监控</h1>
            <p className="text-sm text-gray-500">应用性能监控和实时分析</p>
          </div>
        </div>
        <div className="flex gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border rounded-md bg-white"
          >
            <option value="5m">5分钟</option>
            <option value="1h">1小时</option>
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
          </select>
          <Button onClick={() => { refetchMetrics(); refetchHealth(); refetchTraces(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <KpiCard
          title="吞吐量"
          value={throughput.toFixed(0)}
          unit="req/s"
          icon={Zap}
          level="normal"
          description="每秒请求数"
        />
        <KpiCard
          title="错误率"
          value={errorRate.toFixed(2)}
          unit="%"
          icon={AlertTriangle}
          level={errorRate > 5 ? 'critical' : errorRate > 1 ? 'warning' : 'normal'}
          description="请求错误率"
        />
        <KpiCard
          title="P95延迟"
          value={latencyP95.toFixed(0)}
          unit="ms"
          icon={Clock}
          level={latencyP95 > 500 ? 'critical' : latencyP95 > 200 ? 'warning' : 'normal'}
          description="95分位延迟"
        />
        <KpiCard
          title="慢请求率"
          value={(apmMetrics.slow_request_rate || 0).toFixed(2)}
          unit="%"
          icon={Activity}
          level={apmMetrics.slow_request_rate > 10 ? 'critical' : apmMetrics.slow_request_rate > 5 ? 'warning' : 'normal'}
          description="慢请求占比"
        />
      </div>

      {/* Latency Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GaugeChart
          value={apmMetrics.latency_p50 || 0}
          min={0}
          max={1000}
          title="P50延迟"
          color={apmMetrics.latency_p50 > 500 ? '#ef4444' : apmMetrics.latency_p50 > 200 ? '#f59e0b' : '#10b981'}
        />
        <GaugeChart
          value={apmMetrics.latency_p95 || 0}
          min={0}
          max={1000}
          title="P95延迟"
          color={apmMetrics.latency_p95 > 500 ? '#ef4444' : apmMetrics.latency_p95 > 200 ? '#f59e0b' : '#10b981'}
        />
        <GaugeChart
          value={apmMetrics.latency_p99 || 0}
          min={0}
          max={1000}
          title="P99延迟"
          color={apmMetrics.latency_p99 > 500 ? '#ef4444' : apmMetrics.latency_p99 > 200 ? '#f59e0b' : '#10b981'}
        />
      </div>

      {/* Application Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5" />
            应用健康状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">应用名称</span>
              <span className="text-sm font-medium text-gray-900">{apmHealth.application || 'aiops-agent'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">版本</span>
              <span className="text-sm font-medium text-gray-900">{apmHealth.version || '1.0.0'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">健康状态</span>
              <span className={`text-sm font-medium ${apmHealth.health_status?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                }`}>
                {apmHealth.health_status?.status || 'unknown'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">最后更新</span>
              <span className="text-sm text-gray-500">
                {apmHealth.timestamp ? new Date(apmHealth.timestamp).toLocaleString() : '-'}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Health Checks */}
      <Card>
        <CardHeader>
          <CardTitle>健康检查</CardTitle>
        </CardHeader>
        <CardContent>
          {apmHealth.health_status?.checks ? (
            <div className="space-y-2">
              {Object.entries(apmHealth.health_status.checks).map(([checkName, checkResult]: [string, any]) => (
                <div key={checkName} className="flex items-center justify-between p-3 border rounded">
                  <span className="text-sm font-medium text-gray-700">{checkName}</span>
                  <span className={`text-sm ${checkResult?.status === 'healthy' ? 'text-green-600' : 'text-red-600'
                    }`}>
                    {checkResult?.status || 'unknown'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="暂无健康检查数据"
              description="当前没有可用的健康检查信息"
            />
          )}
        </CardContent>
      </Card>

      {/* Traces */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            性能追踪
          </CardTitle>
        </CardHeader>
        <CardContent>
          {apmTraces.length === 0 ? (
            <EmptyState
              title="暂无追踪数据"
              description="当前没有可用的性能追踪数据"
            />
          ) : (
            <DataTable
              data={apmTraces}
              columns={traceColumns}
              pageSize={10}
              emptyMessage="暂无追踪数据"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}