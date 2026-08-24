'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Dog, RefreshCw, TestTube, Settings, AlertTriangle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface DatadogConfig {
  config_id: string;
  name: string;
  api_key: string;
  app_key: string;
  site: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface DatadogAlert {
  alert_id: string;
  title: string;
  status: string;
  severity: string;
  created_at: string;
}

export default function DatadogPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    api_key: '',
    app_key: '',
    site: 'datadoghq.com',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: DatadogConfig[] }>({
    queryKey: ['datadog-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/datadog/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: alertData, refetch: refetchAlerts } = useQuery<{ alerts: DatadogAlert[] }>({
    queryKey: ['datadog-alerts'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/datadog/alerts');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/datadog/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datadog-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', api_key: '', app_key: '', site: 'datadoghq.com', enabled: true });
      showSuccess('Datadog配置成功');
    },
    onError: () => {
      showError('Datadog配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/datadog/test/${id}`);
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

  useEffect(() => {
    if (error) {
      showError('Failed to load Datadog data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const alerts = alertData?.alerts || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'site' as const, label: '站点' },
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
          description="无法加载Datadog数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchAlerts(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchAlerts(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Dog className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Datadog集成</h1>
            <p className="text-sm text-gray-500">管理Datadog监控集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchAlerts(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">Datadog配置</p>
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
            <CardTitle className="text-sm">活跃告警</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {alerts.filter(a => a.status === 'active').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">当前告警</p>
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
              description="还没有配置Datadog集成"
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
            <AlertTriangle className="h-5 w-5" />
            最新告警
          </CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <EmptyState
              title="暂无告警"
              description="还没有获取到Datadog告警"
            />
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 10).map((alert) => (
                <div key={alert.alert_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{alert.title}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      alert.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {alert.severity}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>状态: {alert.status}</p>
                    <p>时间: {new Date(alert.created_at).toLocaleString()}</p>
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
