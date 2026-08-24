'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Ticket, RefreshCw, TestTube, Settings, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface ServiceNowConfig {
  config_id: string;
  name: string;
  instance_url: string;
  username: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface ServiceNowIncident {
  incident_id: string;
  number: string;
  short_description: string;
  state: string;
  priority: string;
  assigned_to: string;
  created_at: string;
}

export default function ServiceNowPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    instance_url: '',
    username: '',
    password: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: ServiceNowConfig[] }>({
    queryKey: ['servicenow-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/servicenow/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: incidentData, refetch: refetchIncidents } = useQuery<{ incidents: ServiceNowIncident[] }>({
    queryKey: ['servicenow-incidents'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/servicenow/incidents');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/servicenow/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['servicenow-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', instance_url: '', username: '', password: '', enabled: true });
      showSuccess('ServiceNow配置成功');
    },
    onError: () => {
      showError('ServiceNow配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/servicenow/test/${id}`);
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
      showError('Failed to load ServiceNow data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const incidents = incidentData?.incidents || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'instance_url' as const, label: '实例URL' },
    { key: 'username' as const, label: '用户名' },
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
          description="无法加载ServiceNow数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchIncidents(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchIncidents(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Ticket className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">ServiceNow集成</h1>
            <p className="text-sm text-gray-500">管理ServiceNow ITSM集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchIncidents(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">ServiceNow配置</p>
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
            <CardTitle className="text-sm">活跃事件</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {incidents.filter(i => i.state === 'Active').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">活跃事件</p>
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
              description="还没有配置ServiceNow集成"
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
            <AlertCircle className="h-5 w-5" />
            事件列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {incidents.length === 0 ? (
            <EmptyState
              title="暂无事件"
              description="还没有获取到ServiceNow事件"
            />
          ) : (
            <div className="space-y-3">
              {incidents.slice(0, 10).map((incident) => (
                <div key={incident.incident_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{incident.number}</span>
                    <div className="flex gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        incident.state === 'Active' ? 'bg-red-100 text-red-800' :
                        incident.state === 'Resolved' ? 'bg-green-100 text-green-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {incident.state}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        incident.priority === '1 - Critical' ? 'bg-red-100 text-red-800' :
                        incident.priority === '2 - High' ? 'bg-orange-100 text-orange-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {incident.priority}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{incident.short_description}</p>
                  <div className="text-sm text-gray-600">
                    <p>分配给: {incident.assigned_to || '未分配'}</p>
                    <p>创建时间: {new Date(incident.created_at).toLocaleString()}</p>
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
