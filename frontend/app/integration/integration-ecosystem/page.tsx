'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Globe, RefreshCw, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface IntegrationSystem {
  system_id: string;
  system_name: string;
  system_type: string;
  version: string;
  status: 'active' | 'inactive' | 'error';
  last_sync: string | null;
  health_score: number;
  connection_count: number;
}

export default function IntegrationEcosystemPage() {
  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const { data: ecosystemData, refetch } = useQuery<{ systems: IntegrationSystem[] }>({
    queryKey: ['integration-ecosystem'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/ecosystem');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (error) {
      showError('Failed to load ecosystem data');
    }
  }, [error, showError]);

  const systems = ecosystemData?.systems || [];

  const columns = [
    { key: 'system_name' as const, label: '系统名称' },
    { key: 'system_type' as const, label: '系统类型' },
    { key: 'version' as const, label: '版本' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'active' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'health_score' as const, label: '健康分数', render: (value: number) => (
      <span className={value >= 80 ? 'text-green-600' : value >= 60 ? 'text-yellow-600' : 'text-red-600'}>
        {value}%
      </span>
    )},
    { key: 'connection_count' as const, label: '连接数' },
    { key: 'last_sync' as const, label: '最后同步', render: (value: string | null) => 
      value ? new Date(value).toLocaleString() : '-' 
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorBoundary fallback={
        <EmptyState
          title="加载失败"
          description="无法加载集成生态数据，请稍后重试"
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => refetch()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const activeSystems = systems.filter(s => s.status === 'active').length;
  const avgHealthScore = systems.length > 0 
    ? Math.round(systems.reduce((sum, s) => sum + s.health_score, 0) / systems.length)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Globe className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">集成生态</h1>
            <p className="text-sm text-gray-500">查看和管理整个集成生态系统</p>
          </div>
        </div>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总系统数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{systems.length}</p>
            <p className="text-sm text-gray-500 mt-1">已集成的系统</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃系统</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{activeSystems}</p>
            <p className="text-sm text-gray-500 mt-1">正常运行中</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">平均健康分数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{avgHealthScore}%</p>
            <p className="text-sm text-gray-500 mt-1">整体健康度</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            集成系统列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {systems.length === 0 ? (
            <EmptyState
              title="暂无集成系统"
              description="当前没有集成的外部系统"
            />
          ) : (
            <DataTable
              data={systems}
              columns={columns}
              pageSize={10}
              emptyMessage="暂无集成系统"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
