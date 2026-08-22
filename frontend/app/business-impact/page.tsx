'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { KpiCard } from '@/components/ui/KpiCard';
import { GaugeChart } from '@/components/charts/GaugeChart';
import { TrendChart } from '@/components/charts/TrendChart';
import { TrendingUp, RefreshCw, Search, AlertTriangle, Users, DollarSign, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface BusinessImpactService {
  id: string;
  name: string;
  category: string;
  impactScore: number;
  status: string;
}

interface UXMetric {
  id: string;
  name: string;
  value: number;
  change: number;
  status: string;
}

interface BusinessImpactAssessment {
  name: string;
  impactScore: number;
  status: string;
  affectedUsers: number;
  revenueImpact: number;
  currentConversion: number;
  baselineConversion: number;
  conversionRateChange: number;
}

export default function BusinessImpactPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedService, setSelectedService] = useState<string | null>(null);

  // 🔧 获取业务影响服务列表
  const { data: servicesData, isLoading: servicesLoading, error: servicesError, refetch: refetchServices } = useQuery<{ status: string; data: BusinessImpactService[] }>({
    queryKey: ['business-impact-services'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/business-impact/services');
      return resp.data;
    },
    refetchInterval: 60000, // 60秒刷新
  });

  // 🔧 获取用户体验指标
  const { data: uxMetricsData, isLoading: uxLoading, error: uxError, refetch: refetchUX } = useQuery<{ status: string; data: UXMetric[] }>({
    queryKey: ['business-impact-ux'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/business-impact/ux-metrics');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  // 🔧 获取业务影响评估
  const { data: assessmentData, isLoading: assessmentLoading, error: assessmentError, refetch: refetchAssessment } = useQuery<{ status: string; data: BusinessImpactAssessment }>({
    queryKey: ['business-impact-assessment', selectedService],
    queryFn: async () => {
      const resp = await api.get(`/api/v1/business-impact/assess/${selectedService}`);
      return resp.data;
    },
    enabled: !!selectedService,
    refetchInterval: 60000,
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(servicesLoading || uxLoading || assessmentLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (servicesError) {
      showError('Failed to load business impact services');
      setPageError(servicesError as Error);
    }
    if (uxError) {
      showError('Failed to load UX metrics');
      setPageError(uxError as Error);
    }
    if (assessmentError) {
      showError('Failed to load business impact assessment');
      setPageError(assessmentError as Error);
    }
  }, [servicesError, uxError, assessmentError, showError, setPageError]);

  const services = servicesData?.data || [];
  const uxMetrics = uxMetricsData?.data || [];
  const assessment = assessmentData?.data || null;

  const filteredServices = services.filter((service) => {
    if (searchQuery && !service.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !service.category.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const serviceColumns = [
    { key: 'name' as const, label: '服务名称' },
    { key: 'category' as const, label: '类别' },
    { key: 'impactScore' as const, label: '影响分数', render: (value: number) => value.toFixed(1) },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'healthy' ? 'success' : value === 'degraded' ? 'warning' : 'error'} text={value} />
      )
    },
  ];

  const uxColumns = [
    { key: 'name' as const, label: '指标名称' },
    { key: 'value' as const, label: '当前值', render: (value: number) => value.toFixed(2) },
    {
      key: 'change' as const, label: '变化', render: (value: number) => (
        <span className={value < 0 ? 'text-green-600' : 'text-red-600'}>
          {value > 0 ? '+' : ''}{value.toFixed(1)}%
        </span>
      )
    },
    {
      key: 'status' as const, label: '状态', render: (value: string) => (
        <StatusBadge status={value === 'good' ? 'success' : 'warning'} text={value} />
      )
    },
  ];

  const handleServiceClick = (serviceName: string) => {
    setSelectedService(serviceName);
  };

  const handleRefresh = () => {
    refetchServices();
    refetchUX();
    if (selectedService) refetchAssessment();
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
          description="无法加载业务影响数据，请稍后重试"
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

  const totalServices = services.length;
  const downServices = services.filter((s) => s.status === 'down').length;
  const totalRevenueImpact = services.reduce((sum, s) => {
    if (s.status === 'down') {
      return sum + (s.impactScore * 10000);
    }
    return sum;
  }, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">业务影响分析</h1>
            <p className="text-sm text-gray-500">服务故障对业务的影响评估</p>
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
        <KpiCard
          title="总服务数"
          value={totalServices}
          icon={Activity}
          level="normal"
          description="业务影响服务总数"
        />
        <KpiCard
          title="故障服务"
          value={downServices}
          icon={AlertTriangle}
          level={downServices > 0 ? 'critical' : 'normal'}
          description="当前故障的服务"
        />
        <KpiCard
          title="预估收入影响"
          value={totalRevenueImpact}
          unit="$"
          icon={DollarSign}
          level={totalRevenueImpact > 100000 ? 'critical' : totalRevenueImpact > 50000 ? 'warning' : 'normal'}
          description="故障导致的收入损失"
        />
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索服务名称或类别"
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Services List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            业务影响服务 ({filteredServices.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filteredServices.length === 0 ? (
            <EmptyState
              title="暂无服务数据"
              description="当前没有可用的业务影响服务"
            />
          ) : (
            <DataTable
              data={filteredServices}
              columns={serviceColumns}
              pageSize={15}
              emptyMessage="暂无服务数据"
              onRowClick={(service) => handleServiceClick(service.name)}
            />
          )}
        </CardContent>
      </Card>

      {/* UX Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            用户体验指标
          </CardTitle>
        </CardHeader>
        <CardContent>
          {uxMetrics.length === 0 ? (
            <EmptyState
              title="暂无UX指标"
              description="当前没有可用的用户体验指标"
            />
          ) : (
            <DataTable
              data={uxMetrics}
              columns={uxColumns}
              pageSize={10}
              emptyMessage="暂无UX指标"
            />
          )}
        </CardContent>
      </Card>

      {/* Business Impact Assessment */}
      {assessment && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              业务影响评估 - {assessment.name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">影响分数</label>
                  <p className="text-2xl font-bold text-gray-900">{assessment.impactScore.toFixed(1)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">状态</label>
                  <p className="text-2xl font-bold text-gray-900">{assessment.status}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">受影响用户</label>
                  <p className="text-2xl font-bold text-red-600">{assessment.affectedUsers.toLocaleString()}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">收入影响</label>
                  <p className="text-2xl font-bold text-red-600">${assessment.revenueImpact.toLocaleString()}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">当前转化率</label>
                  <p className="text-2xl font-bold text-gray-900">{assessment.currentConversion.toFixed(2)}%</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">基准转化率</label>
                  <p className="text-2xl font-bold text-gray-900">{assessment.baselineConversion.toFixed(2)}%</p>
                </div>
              </div>

              <GaugeChart
                value={assessment.impactScore * 10}
                min={0}
                max={100}
                title="业务影响分数"
                color={assessment.impactScore > 7 ? '#ef4444' : assessment.impactScore > 4 ? '#f59e0b' : '#10b981'}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}