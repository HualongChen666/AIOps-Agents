'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { List, Search, RefreshCw, Trash2, TestTube, Edit } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface Integration {
  integration_id: string;
  integration_type: string;
  name: string;
  enabled: boolean;
  status: string;
  last_tested: string | null;
  last_error: string | null;
  created_at: string;
}

export default function IntegrationListPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: integrationData, refetch } = useQuery<{ integrations: Integration[] }>({
    queryKey: ['integration-list'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/list');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/integration/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-list'] });
      showSuccess('集成删除成功');
    },
    onError: () => {
      showError('集成删除失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/test/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('集成测试成功');
      refetch();
    },
    onError: () => {
      showError('集成测试失败');
    },
  });

  useEffect(() => {
    if (error) {
      showError('Failed to load integration list');
    }
  }, [error, showError]);

  const integrations = integrationData?.integrations || [];
  const filteredIntegrations = integrations.filter(integration =>
    integration.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    integration.integration_type.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    { key: 'name' as const, label: '名称' },
    { key: 'integration_type' as const, label: '类型' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'active' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'last_tested' as const, label: '最后测试', render: (value: string | null) => 
      value ? new Date(value).toLocaleString() : '-' 
    },
    { key: 'created_at' as const, label: '创建时间', render: (value: string) => 
      new Date(value).toLocaleString() 
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
          description="无法加载集成列表，请稍后重试"
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

  const activeIntegrations = integrations.filter(i => i.enabled).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <List className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">集成列表</h1>
            <p className="text-sm text-gray-500">查看和管理所有已注册的集成</p>
          </div>
        </div>
        <Button onClick={() => refetch()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总集成数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{integrations.length}</p>
            <p className="text-sm text-gray-500 mt-1">已注册的集成</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃集成</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{activeIntegrations}</p>
            <p className="text-sm text-gray-500 mt-1">已启用的集成</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <List className="h-5 w-5" />
            集成列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="搜索集成名称或类型..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
          {filteredIntegrations.length === 0 ? (
            <EmptyState
              title="暂无集成"
              description={searchTerm ? "没有找到匹配的集成" : "当前没有注册的集成"}
            />
          ) : (
            <DataTable
              data={filteredIntegrations}
              columns={columns}
              pageSize={10}
              emptyMessage="暂无集成"
              onRowClick={(integration) => (
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    onClick={() => testMutation.mutate(integration.integration_id)}
                    disabled={testMutation.isPending}
                  >
                    <TestTube className="h-4 w-4 mr-1" />
                    测试
                  </Button>
                  <Button 
                    size="sm" 
                    variant="destructive" 
                    onClick={() => {
                      if (confirm('确定要删除这个集成吗？')) {
                        deleteMutation.mutate(integration.integration_id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    删除
                  </Button>
                </div>
              )}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
