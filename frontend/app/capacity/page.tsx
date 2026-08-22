'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { KpiCard } from '@/components/ui/KpiCard';
import { DataTable } from '@/components/ui/DataTable';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { TrendingUp, RefreshCw, AlertTriangle, Cpu, HardDrive, Network, Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface CapacityForecast {
  metric: string;
  currentValue: number;
  forecast7d: number;
  forecast30d: number;
  threshold: number;
  unit: string;
}

interface ScalingRecommendation {
  id: string;
  service: string;
  action: string;
  reason: string;
  priority: string;
  estimatedCost: number;
}

export default function CapacityPage() {
  // 🔧 获取容量预测
  const { data: forecastData, isLoading: forecastLoading, error: forecastError, refetch: refetchForecast } = useQuery<{ data: CapacityForecast[] }>({
    queryKey: ['capacity-forecast'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/forecast');
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 获取扩容建议
  const { data: recommendationsData, isLoading: recommendationsLoading, error: recommendationsError, refetch: refetchRecommendations } = useQuery<{ data: ScalingRecommendation[] }>({
    queryKey: ['capacity-recommendations'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/capacity/recommendations');
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(forecastLoading || recommendationsLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (forecastError) {
      showError('Failed to load capacity forecast');
      setPageError(forecastError as Error);
    }
    if (recommendationsError) {
      showError('Failed to load scaling recommendations');
      setPageError(recommendationsError as Error);
    }
  }, [forecastError, recommendationsError, showError, setPageError]);

  const forecasts = forecastData?.data || [];
  const recommendations = recommendationsData?.data || [];

  const recommendationColumns = [
    { key: 'id' as const, label: 'ID' },
    { key: 'service' as const, label: '服务' },
    { key: 'action' as const, label: '操作' },
    {
      key: 'reason' as const, label: '原因', render: (value: string) => (
        <div className="max-w-md truncate" title={value}>{value}</div>
      )
    },
    {
      key: 'priority' as const, label: '优先级', render: (value: string) => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${value === 'high' ? 'bg-red-100 text-red-800' : value === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
          }`}>
          {value}
        </span>
      )
    },
    { key: 'estimatedCost' as const, label: '预估成本', render: (value: number) => `$${value.toFixed(2)}` },
  ];

  const handleRefresh = () => {
    refetchForecast();
    refetchRecommendations();
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
          description="无法加载容量规划数据，请稍后重试"
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={handleRefresh}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const highPriorityCount = recommendations.filter((r) => r.priority === 'high').length;
  const totalEstimatedCost = recommendations.reduce((sum, r) => sum + r.estimatedCost, 0);
  const criticalMetrics = forecasts.filter((f) => f.forecast30d > f.threshold).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">容量规划</h1>
            <p className="text-sm text-gray-500">容量预测和扩容建议</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">高优先级建议</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{highPriorityCount}</p>
            <p className="text-sm text-gray-500 mt-1">需要立即处理</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">预估总成本</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">${totalEstimatedCost.toFixed(2)}</p>
            <p className="text-sm text-gray-500 mt-1">扩容预估成本</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">临界指标</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{criticalMetrics}</p>
            <p className="text-sm text-gray-500 mt-1">30天内将超阈值</p>
          </CardContent>
        </Card>
      </div>

      {/* Capacity Forecasts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            容量预测
          </CardTitle>
        </CardHeader>
        <CardContent>
          {forecasts.length === 0 ? (
            <EmptyState
              title="暂无预测数据"
              description="当前没有可用的容量预测数据"
            />
          ) : (
            <div className="space-y-6">
              {forecasts.map((forecast) => {
                const icon = forecast.metric.includes('CPU') ? Cpu : forecast.metric.includes('内存') ? Zap : forecast.metric.includes('磁盘') ? HardDrive : Network;
                const isCritical = forecast.forecast30d > forecast.threshold;
                return (
                  <div key={forecast.metric} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="h-5 w-5 text-gray-600">
                          {forecast.metric.includes('CPU') ? <Cpu /> : forecast.metric.includes('内存') ? <Zap /> : forecast.metric.includes('磁盘') ? <HardDrive /> : <Network />}
                        </div>
                        <h3 className="text-lg font-semibold">{forecast.metric}</h3>
                        {isCritical && <AlertTriangle className="h-5 w-5 text-red-600" />}
                      </div>
                      <div className="text-sm text-gray-500">
                        阈值: {forecast.threshold}{forecast.unit}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div>
                        <label className="text-sm text-gray-600">当前值</label>
                        <p className="text-2xl font-bold text-gray-900">{forecast.currentValue.toFixed(1)}{forecast.unit}</p>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">7天预测</label>
                        <p className="text-2xl font-bold text-blue-600">{forecast.forecast7d.toFixed(1)}{forecast.unit}</p>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">30天预测</label>
                        <p className={`text-2xl font-bold ${isCritical ? 'text-red-600' : 'text-green-600'}`}>
                          {forecast.forecast30d.toFixed(1)}{forecast.unit}
                        </p>
                      </div>
                    </div>
                    <GaugeChart
                      value={forecast.forecast30d}
                      min={0}
                      max={100}
                      title="30天预测"
                      color={isCritical ? '#ef4444' : forecast.forecast30d > forecast.threshold * 0.8 ? '#f59e0b' : '#10b981'}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scaling Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            扩容建议
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recommendations.length === 0 ? (
            <EmptyState
              title="暂无扩容建议"
              description="当前没有扩容建议"
            />
          ) : (
            <DataTable
              data={recommendations}
              columns={recommendationColumns}
              pageSize={10}
              emptyMessage="暂无扩容建议"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}