'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Phone, RefreshCw, TestTube, Settings, AlertCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface OncallConfig {
  config_id: string;
  name: string;
  provider: 'pagerduty' | 'opsgenie';
  api_key: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
}

interface OncallSchedule {
  schedule_id: string;
  name: string;
  current_oncall: string;
  next_oncall: string;
  timezone: string;
}

interface OncallIncident {
  incident_id: string;
  title: string;
  severity: string;
  status: string;
  assigned_to: string;
  created_at: string;
}

export default function OncallPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    provider: 'pagerduty' as const,
    api_key: '',
    enabled: true,
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: OncallConfig[] }>({
    queryKey: ['oncall-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/oncall/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: scheduleData, refetch: refetchSchedules } = useQuery<{ schedules: OncallSchedule[] }>({
    queryKey: ['oncall-schedules'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/oncall/schedules');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: incidentData, refetch: refetchIncidents } = useQuery<{ incidents: OncallIncident[] }>({
    queryKey: ['oncall-incidents'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/oncall/incidents');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/oncall/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['oncall-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', provider: 'pagerduty', api_key: '', enabled: true });
      showSuccess('Oncall配置成功');
    },
    onError: () => {
      showError('Oncall配置失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/oncall/test/${id}`);
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
      showError('Failed to load Oncall data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const schedules = scheduleData?.schedules || [];
  const incidents = incidentData?.incidents || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'provider' as const, label: '提供商' },
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
          description="无法加载Oncall数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchSchedules(); refetchIncidents(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchSchedules(); refetchIncidents(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Phone className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Oncall集成</h1>
            <p className="text-sm text-gray-500">管理PagerDuty、OpsGenie等值班集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchSchedules(); refetchIncidents(); }} variant="outline">
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
            <p className="text-sm text-gray-500 mt-1">Oncall配置</p>
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
              {incidents.filter(i => i.status === 'active').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">当前事件</p>
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
              description="还没有配置Oncall集成"
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
            <Phone className="h-5 w-5" />
            值班表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {schedules.length === 0 ? (
            <EmptyState
              title="暂无值班表"
              description="还没有获取到值班表信息"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {schedules.map((schedule) => (
                <div key={schedule.schedule_id} className="p-4 border rounded-lg">
                  <h3 className="font-medium mb-2">{schedule.name}</h3>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p>当前值班: {schedule.current_oncall}</p>
                    <p>下次值班: {schedule.next_oncall}</p>
                    <p>时区: {schedule.timezone}</p>
                  </div>
                </div>
              ))}
            </div>
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
              description="还没有获取到值班事件"
            />
          ) : (
            <div className="space-y-3">
              {incidents.slice(0, 10).map((incident) => (
                <div key={incident.incident_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{incident.title}</span>
                    <div className="flex gap-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        incident.status === 'active' ? 'bg-red-100 text-red-800' :
                        incident.status === 'resolved' ? 'bg-green-100 text-green-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {incident.status}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        incident.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        incident.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {incident.severity}
                      </span>
                    </div>
                  </div>
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
