'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Plug, Plus, RefreshCw, Trash2, TestTube, Webhook, Bell, Settings, CheckCircle, XCircle } from 'lucide-react';
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
}

interface Webhook {
  webhook_id: string;
  source: string;
  event_type: string;
  endpoint: string;
  enabled: boolean;
  created_at: string;
}

interface NotificationChannel {
  name: string;
  type: string;
  enabled: boolean;
}

export default function IntegrationPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showWebhookModal, setShowWebhookModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'integrations' | 'webhooks' | 'notifications'>('integrations');
  const [formData, setFormData] = useState({
    integration_type: 'prometheus',
    name: '',
    config: {},
    enabled: true,
  });
  const [webhookData, setWebhookData] = useState({
    source: '',
    event_type: '',
    endpoint: '',
    secret: '',
  });

  const queryClient = useQueryClient();

  // 🔧 获取集成列表
  const { data: integrationData, isLoading: integrationLoading, error: integrationError, refetch: refetchIntegrations } = useQuery<{ total_integrations: number; integrations: Integration[] }>({
    queryKey: ['integration-list'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/list');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取Webhook列表
  const { data: webhookListData, isLoading: webhookLoading, refetch: refetchWebhooks } = useQuery<{ webhooks: Webhook[] }>({
    queryKey: ['webhook-list'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/webhooks');
      return resp.data;
    },
    refetchInterval: 120000,
  });

  // 🔧 获取通知渠道
  const { data: channelData, refetch: refetchChannels } = useQuery<{ channels: NotificationChannel[] }>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/notification/channels');
      return resp.data;
    },
    refetchInterval: 120000,
  });

  // 🔧 注册集成
  const createIntegrationMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/register', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['integration-list'] });
      setShowCreateModal(false);
      showSuccess('集成注册成功');
    },
    onError: () => {
      showError('集成注册失败');
    },
  });

  // 🔧 测试集成
  const testIntegrationMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/test/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('集成测试成功');
      refetchIntegrations();
    },
    onError: () => {
      showError('集成测试失败');
    },
  });

  // 🔧 删除集成
  const deleteIntegrationMutation = useMutation({
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

  // 🔧 注册Webhook
  const createWebhookMutation = useMutation({
    mutationFn: async (data: typeof webhookData) => {
      const resp = await api.post('/api/v1/integration/webhook/register', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-list'] });
      setShowWebhookModal(false);
      showSuccess('Webhook注册成功');
    },
    onError: () => {
      showError('Webhook注册失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(integrationLoading || webhookLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (integrationError) {
      showError('Failed to load integration data');
      setPageError(integrationError as Error);
    }
  }, [integrationError, showError, setPageError]);

  const integrations = integrationData?.integrations || [];
  const webhooks = webhookListData?.webhooks || [];
  const channels = channelData?.channels || [];

  const integrationColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'integration_type' as const, label: '类型' },
    { key: 'status' as const, label: '状态', render: (value: string) => <StatusBadge status={value === 'active' ? 'success' : 'error'} text={value} /> },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'last_tested' as const, label: '最后测试', render: (value: string | null) => value ? new Date(value).toLocaleString() : '-' },
  ];

  const webhookColumns = [
    { key: 'source' as const, label: '来源' },
    { key: 'event_type' as const, label: '事件类型' },
    { key: 'endpoint' as const, label: '端点' },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'created_at' as const, label: '创建时间', render: (value: string) => new Date(value).toLocaleString() },
  ];

  const channelColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'type' as const, label: '类型' },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
  ];

  const handleCreateIntegration = () => {
    createIntegrationMutation.mutate(formData);
  };

  const handleTestIntegration = (id: string) => {
    testIntegrationMutation.mutate(id);
  };

  const handleDeleteIntegration = (id: string) => {
    if (confirm('确定要删除这个集成吗？')) {
      deleteIntegrationMutation.mutate(id);
    }
  };

  const handleCreateWebhook = () => {
    createWebhookMutation.mutate(webhookData);
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
          description="无法加载集成数据，请稍后重试"
          action={<Button onClick={() => refetchIntegrations()}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={pageError.message}
          action={<Button onClick={() => refetchIntegrations()}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  const activeIntegrations = integrations.filter((i) => i.enabled).length;
  const totalIntegrations = integrations.length;
  const activeWebhooks = webhooks.filter((w) => w.enabled).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Plug className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">集成中心</h1>
            <p className="text-sm text-gray-500">管理外部系统集成和Webhook配置</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchIntegrations(); refetchWebhooks(); refetchChannels(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          {activeTab === 'integrations' && (
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              注册集成
            </Button>
          )}
          {activeTab === 'webhooks' && (
            <Button onClick={() => setShowWebhookModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              注册Webhook
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总集成数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalIntegrations}</p>
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
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Webhook</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{activeWebhooks}</p>
            <p className="text-sm text-gray-500 mt-1">活跃的Webhook</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'integrations' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('integrations')}
        >
          <Settings className="h-4 w-4 mr-2" />
          集成管理
        </Button>
        <Button
          variant={activeTab === 'webhooks' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('webhooks')}
        >
          <Webhook className="h-4 w-4 mr-2" />
          Webhook
        </Button>
        <Button
          variant={activeTab === 'notifications' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('notifications')}
        >
          <Bell className="h-4 w-4 mr-2" />
          通知渠道
        </Button>
      </div>

      {/* Integrations Tab */}
      {activeTab === 'integrations' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              集成列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {integrations.length === 0 ? (
              <EmptyState
                title="暂无集成"
                description="当前没有注册的外部集成"
                action={<Button onClick={() => setShowCreateModal(true)}>注册第一个集成</Button>}
              />
            ) : (
              <DataTable
                data={integrations}
                columns={integrationColumns}
                pageSize={10}
                emptyMessage="暂无集成"
                onRowClick={(integration) => (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => handleTestIntegration(integration.integration_id)}>
                      <TestTube className="h-4 w-4 mr-1" />
                      测试
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => handleDeleteIntegration(integration.integration_id)}>
                      <Trash2 className="h-4 w-4 mr-1" />
                      删除
                    </Button>
                  </div>
                )}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Webhooks Tab */}
      {activeTab === 'webhooks' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Webhook className="h-5 w-5" />
              Webhook列表
            </CardTitle>
          </CardHeader>
          <CardContent>
            {webhooks.length === 0 ? (
              <EmptyState
                title="暂无Webhook"
                description="当前没有注册的Webhook"
                action={<Button onClick={() => setShowWebhookModal(true)}>注册第一个Webhook</Button>}
              />
            ) : (
              <DataTable
                data={webhooks}
                columns={webhookColumns}
                pageSize={10}
                emptyMessage="暂无Webhook"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              通知渠道
            </CardTitle>
          </CardHeader>
          <CardContent>
            {channels.length === 0 ? (
              <EmptyState
                title="暂无通知渠道"
                description="当前没有配置的通知渠道"
              />
            ) : (
              <DataTable
                data={channels}
                columns={channelColumns}
                pageSize={10}
                emptyMessage="暂无通知渠道"
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Integration Modal */}
      <EnhancedModal
        open={showCreateModal}
        onOpenChange={setShowCreateModal}
        title="注册集成"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">集成类型</label>
            <select
              value={formData.integration_type}
              onChange={(e) => setFormData({ ...formData, integration_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="prometheus">Prometheus</option>
              <option value="grafana">Grafana</option>
              <option value="elk">ELK</option>
              <option value="jenkins">Jenkins</option>
              <option value="jira">Jira</option>
              <option value="servicenow">ServiceNow</option>
              <option value="slack">Slack</option>
              <option value="teams">Teams</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="集成名称"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateIntegration} disabled={createIntegrationMutation.isPending}>
              {createIntegrationMutation.isPending ? '注册中...' : '注册'}
            </Button>
          </div>
        </div>
      </EnhancedModal>

      {/* Create Webhook Modal */}
      <EnhancedModal
        open={showWebhookModal}
        onOpenChange={setShowWebhookModal}
        title="注册Webhook"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">来源</label>
            <Input
              value={webhookData.source}
              onChange={(e) => setWebhookData({ ...webhookData, source: e.target.value })}
              placeholder="来源系统"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">事件类型</label>
            <Input
              value={webhookData.event_type}
              onChange={(e) => setWebhookData({ ...webhookData, event_type: e.target.value })}
              placeholder="事件类型"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">端点URL</label>
            <Input
              value={webhookData.endpoint}
              onChange={(e) => setWebhookData({ ...webhookData, endpoint: e.target.value })}
              placeholder="https://example.com/webhook"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密钥（可选）</label>
            <Input
              type="password"
              value={webhookData.secret}
              onChange={(e) => setWebhookData({ ...webhookData, secret: e.target.value })}
              placeholder="Webhook密钥"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowWebhookModal(false)}>
              取消
            </Button>
            <Button onClick={handleCreateWebhook} disabled={createWebhookMutation.isPending}>
              {createWebhookMutation.isPending ? '注册中...' : '注册'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}