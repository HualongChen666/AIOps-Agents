'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { KpiCard } from '@/components/ui/KpiCard';
import { TrendChart } from '@/components/charts/TrendChart';
import { DataTable } from '@/components/ui/DataTable';
import { DollarSign, TrendingUp, TrendingDown, AlertTriangle, Download, Calendar } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface CostItem {
  date: string;
  amount: number;
  service?: string;
  category?: string;
}

interface BudgetStatus {
  budget?: number;
  used?: number;
  remaining?: number;
  status?: string;
  forecast?: number;
}

interface ForecastItem {
  date: string;
  predicted_amount: number;
}

export default function CostPage() {
  const [forecastDays, setForecastDays] = useState(30);

  // 🔧 获取成本数据
  const { data: costData, isLoading: costLoading, error: costError, refetch: refetchCost } = useQuery<{ costs: CostItem[] }>({
    queryKey: ['cost-collect'],
    queryFn: async () => {
      const resp = await api.get('/api/cost/collect');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取预算状态
  const { data: budgetData, isLoading: budgetLoading, error: budgetError, refetch: refetchBudget } = useQuery<BudgetStatus>({
    queryKey: ['cost-budget'],
    queryFn: async () => {
      const resp = await api.get('/api/cost/budget');
      return resp.data;
    },
    refetchInterval: 120000, // 120秒刷新
  });

  // 🔧 获取费用预测
  const { data: forecastData, isLoading: forecastLoading, refetch: refetchForecast } = useQuery<{ days: number; forecast: ForecastItem[] }>({
    queryKey: ['cost-forecast', forecastDays],
    queryFn: async () => {
      const resp = await api.get(`/api/cost/forecast?days=${forecastDays}`);
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(costLoading || budgetLoading || forecastLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (costError) {
      showError('Failed to load cost data');
      setPageError(costError as Error);
    }
    if (budgetError) {
      showError('Failed to load budget data');
      setPageError(budgetError as Error);
    }
  }, [costError, budgetError, showError, setPageError]);

  const costs = costData?.costs || [];
  const budget = budgetData || {};
  const forecast = forecastData?.forecast || [];

  const total = costs.reduce((s, c) => s + (c.amount || 0), 0);
  const remaining = budget.remaining || 0;
  const cap = budget.budget || 0;
  const budgetUsage = cap > 0 ? (total / cap) * 100 : 0;

  const costColumns = [
    { key: 'date' as const, label: '日期' },
    { key: 'service' as const, label: '服务' },
    { key: 'category' as const, label: '类别' },
    { key: 'amount' as const, label: '金额', render: (value: number) => `$${value.toFixed(2)}` },
  ];

  const forecastColumns = [
    { key: 'date' as const, label: '日期' },
    { key: 'predicted_amount' as const, label: '预测金额', render: (value: number) => `$${value.toFixed(2)}` },
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
          description="无法加载成本数据，请稍后重试"
          action={<Button onClick={() => { refetchCost(); refetchBudget(); refetchForecast(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => { refetchCost(); refetchBudget(); refetchForecast(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DollarSign className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">成本管理</h1>
            <p className="text-sm text-gray-500">监控和管理云资源成本</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchCost(); refetchBudget(); refetchForecast(); }} variant="outline">
            刷新
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            导出报告
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KpiCard
          title="累计成本"
          value={total.toFixed(2)}
          unit="$"
          icon={DollarSign}
          level={budgetUsage > 90 ? 'critical' : budgetUsage > 70 ? 'warning' : 'normal'}
          description="本月累计费用"
        />
        <KpiCard
          title="预算上限"
          value={cap.toFixed(2)}
          unit="$"
          icon={Calendar}
          level="normal"
          description="月度预算上限"
        />
        <KpiCard
          title="剩余预算"
          value={remaining.toFixed(2)}
          unit="$"
          icon={TrendingUp}
          level={remaining < cap * 0.1 ? 'critical' : remaining < cap * 0.3 ? 'warning' : 'normal'}
          description={`已使用 ${budgetUsage.toFixed(1)}%`}
        />
      </div>

      {/* Cost Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            成本趋势
          </CardTitle>
        </CardHeader>
        <CardContent>
          <TrendChart
            data={costs.map((c) => c.amount)}
            labels={costs.map((c) => c.date)}
            color="#10b981"
            height={200}
          />
        </CardContent>
      </Card>

      {/* Forecast Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              费用预测
            </CardTitle>
            <div className="flex items-center gap-2">
              <select
                value={String(forecastDays)}
                onChange={(e) => setForecastDays(Number(e.target.value))}
                className="px-3 py-2 border rounded-md bg-white"
              >
                <option value="7">7天</option>
                <option value="30">30天</option>
                <option value="90">90天</option>
              </select>
              <Button size="sm" onClick={() => refetchForecast()}>
                刷新预测
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {forecast.length === 0 ? (
            <EmptyState
              title="暂无预测数据"
              description="当前没有可用的费用预测数据"
            />
          ) : (
            <DataTable
              data={forecast}
              columns={forecastColumns}
              pageSize={10}
              emptyMessage="暂无预测数据"
            />
          )}
        </CardContent>
      </Card>

      {/* Cost Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            成本明细
          </CardTitle>
        </CardHeader>
        <CardContent>
          {costs.length === 0 ? (
            <EmptyState
              title="暂无成本数据"
              description="当前没有可用的成本数据"
            />
          ) : (
            <DataTable
              data={costs}
              columns={costColumns}
              pageSize={15}
              emptyMessage="暂无成本数据"
            />
          )}
        </CardContent>
      </Card>

      {/* Budget Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            预算状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">预算状态</span>
              <span className={`text-sm font-medium ${budget.status === 'critical' ? 'text-red-600' : budget.status === 'warning' ? 'text-yellow-600' : 'text-green-600'
                }`}>
                {budget.status || '正常'}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all ${budgetUsage > 90 ? 'bg-red-500' : budgetUsage > 70 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                style={{ width: `${Math.min(budgetUsage, 100)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>已使用 {budgetUsage.toFixed(1)}%</span>
              <span>剩余 {remaining.toFixed(2)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}