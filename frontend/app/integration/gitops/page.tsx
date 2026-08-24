'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { GitMerge, RefreshCw, TestTube, Settings, GitCommit, Sync } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface GitOpsConfig {
  config_id: string;
  name: string;
  gitops_type: 'argocd' | 'flux' | 'jenkins-x';
  url: string;
  token: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface GitOpsApplication {
  app_id: string;
  name: string;
  namespace: string;
  repo_url: string;
  path: string;
  sync_status: 'synced' | 'out_of_sync' | 'unknown';
  health_status: 'healthy' | 'degraded' | 'progressing' | 'suspended';
  last_sync: string;
}

interface GitOpsSync {
  sync_id: string;
  application: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  revision: string;
}

export default function GitOpsPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    gitops_type: 'argocd' as const,
    url: '',
    token: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: GitOpsConfig[] }>({
    queryKey: ['gitops-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/gitops/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: appData, refetch: refetchApps } = useQuery<{ applications: GitOpsApplication[] }>({
    queryKey: ['gitops-applications'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/gitops/applications');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: syncData, refetch: refetchSyncs } = useQuery<{ syncs: GitOpsSync[] }>({
    queryKey: ['gitops-syncs'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/gitops/syncs');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/gitops/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gitops-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', gitops_type: 'argocd', url: '', token: '', enabled: true });
      showSuccess('GitOps配置成功');
    },
    onError: () => {
      showError('GitOps配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/gitops/test/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('连接测试成功');
      refetchConfig();
    },
    onError: () => {
      showError('连接测试失败');
    },
  });

  const syncMutation = useMutation({
    mutationFn: async (appId: string) => {
      const resp = await api.post(`/api/v1/integration/gitops/sync/${appId}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('同步触发成功');
      refetchApps();
      refetchSyncs();
    },
    onError: () => {
      showError('同步触发失败');
    },
  });

  useEffect(() => {
    if (error) {
      showError('Failed to load GitOps data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const applications = appData?.applications || [];
  const syncs = syncData?.syncs || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'gitops_type' as const, label: '类型' },
    { key: 'url' as const, label: 'URL' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
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
          description="无法加载GitOps数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchApps(); refetchSyncs(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchApps(); refetchSyncs(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitMerge className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">GitOps集成</h1>
            <p className="text-sm text-gray-500">管理ArgoCD、Flux等GitOps工具集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchApps(); refetchSyncs(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowConfigModal(true)}>
            <Settings className="h-4 w-4 mr-2" />
            添加配置
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">配置数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{configs.length}</p>
            <p className="text-sm text-gray-500 mt-1">GitOps配置</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃连接</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {configs.filter(c => c.status === 'connected').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">已连接</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">应用总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{applications.length}</p>
            <p className="text-sm text-gray-500 mt-1">GitOps应用</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            配置列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <EmptyState
              title="暂无配置"
              description="还没有配置GitOps集成"
              action={<Button onClick={() => setShowConfigModal(true)}>添加配置</Button>}
            />
          ) : (
            <DataTable
              data={configs}
              columns={configColumns}
              pageSize={10}
              emptyMessage="暂无配置"
              onRowClick={(config) => (
                <Button 
                  size="sm" 
                  onClick={() => testMutation.mutate(config.config_id)}
                  disabled={testMutation.isPending}
                >
                  <TestTube className="h-4 w-4 mr-1" />
                  测试连接
                </Button>
              )}
            />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCommit className="h-5 w-5" />
            应用列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {applications.length === 0 ? (
            <EmptyState
              title="暂无应用"
              description="还没有获取到GitOps应用"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {applications.map((app) => (
                <div key={app.app_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">{app.name}</h3>
                    <div className="flex gap-1">
                      <span className={`px-2 py-1 rounded text-xs ${
                        app.sync_status === 'synced' ? 'bg-green-100 text-green-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {app.sync_status}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        app.health_status === 'healthy' ? 'bg-green-100 text-green-800' :
                        app.health_status === 'degraded' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {app.health_status}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>命名空间: {app.namespace}</p>
                    <p>仓库: {app.repo_url}</p>
                    <p>路径: {app.path}</p>
                    <p>最后同步: {new Date(app.last_sync).toLocaleString()}</p>
                  </div>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="w-full mt-3"
                    onClick={() => syncMutation.mutate(app.app_id)}
                    disabled={syncMutation.isPending}
                  >
                    <Sync className="h-4 w-4 mr-1" />
                    同步
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sync className="h-5 w-5" />
            同步历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {syncs.length === 0 ? (
            <EmptyState
              title="暂无同步记录"
              description="还没有同步历史记录"
            />
          ) : (
            <div className="space-y-2">
              {syncs.slice(0, 10).map((sync) => (
                <div key={sync.sync_id} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">{sync.application}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      sync.status === 'successful' ? 'bg-green-100 text-green-800' :
                      sync.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {sync.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>版本: {sync.revision}</p>
                    <p>开始时间: {new Date(sync.started_at).toLocaleString()}</p>
                    {sync.completed_at && (
                      <p>完成时间: {new Date(sync.completed_at).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
