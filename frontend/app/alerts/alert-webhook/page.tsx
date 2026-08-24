'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import api from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast, useDebounce } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';
import { Webhook, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw, Copy } from 'lucide-react';

interface WebhookConfig {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  url: string;
  method: 'POST' | 'GET' | 'PUT' | 'DELETE';
  headers: Record<string, string>;
  body_template: string;
  timeout: number;
  retry_count: number;
  retry_interval: number;
  secret_token?: string;
  created_at: string;
  updated_at: string;
}

interface WebhookLog {
  id: string;
  webhook_id: string;
  webhook_name: string;
  status: 'success' | 'failed' | 'pending';
  response_code?: number;
  response_body?: string;
  error_message?: string;
  duration: number;
  timestamp: string;
}

export default function AlertWebhookPage() {
  const [selectedWebhook, setSelectedWebhook] = useState<WebhookConfig | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'webhooks' | 'logs'>('webhooks');
  const [filters, setFilters] = useState({
    enabled: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<WebhookConfig>>({
    name: '',
    description: '',
    enabled: true,
    url: '',
    method: 'POST',
    headers: {},
    body_template: '',
    timeout: 30,
    retry_count: 3,
    retry_interval: 5,
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: webhooksData, isLoading: webhooksLoading, error: webhooksError, refetch: refetchWebhooks } = useQuery<WebhookConfig[]>({
    queryKey: ['alert-webhooks'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/webhook/configs');
      return resp.data.webhooks || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery<WebhookLog[]>({
    queryKey: ['webhook-logs'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/webhook/logs?limit=50');
      return resp.data.logs || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createWebhookMutation = useMutation({
    mutationFn: async (data: Partial<WebhookConfig>) => {
      const resp = await api.post('/api/v1/alerts/webhook/configs', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Webhook配置创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['alert-webhooks'] });
    },
    onError: () => showError('创建Webhook配置失败'),
  });

  const updateWebhookMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<WebhookConfig> }) => {
      const resp = await api.put(`/api/v1/alerts/webhook/configs/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Webhook配置更新成功');
      setShowDialog(false);
      setSelectedWebhook(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['alert-webhooks'] });
    },
    onError: () => showError('更新Webhook配置失败'),
  });

  const deleteWebhookMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/webhook/configs/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('Webhook配置删除成功');
      queryClient.invalidateQueries({ queryKey: ['alert-webhooks'] });
    },
    onError: () => showError('删除Webhook配置失败'),
  });

  useEffect(() => {
    if (webhooksError) showError('Failed to load webhook configs');
  }, [webhooksError, showError]);

  const filteredWebhooks = (webhooksData || []).filter((webhook) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !webhook.enabled : webhook.enabled)) return false;
    if (debouncedSearch && !webhook.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      description: '',
      enabled: true,
      url: '',
      method: 'POST',
      headers: {},
      body_template: '',
      timeout: 30,
      retry_count: 3,
      retry_interval: 5,
    });
    setShowDialog(true);
  };

  const handleEdit = (webhook: WebhookConfig) => {
    setIsEditing(true);
    setSelectedWebhook(webhook);
    setFormData(webhook);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此Webhook配置吗？')) return;
    deleteWebhookMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedWebhook) {
      updateWebhookMutation.mutate({ id: selectedWebhook.id, data: formData });
    } else {
      createWebhookMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (webhook: WebhookConfig) => {
    updateWebhookMutation.mutate({ id: webhook.id, data: { enabled: !webhook.enabled } });
  };

  const handleTestWebhook = async (id: string) => {
    try {
      await api.post(`/api/v1/alerts/webhook/configs/${id}/test`);
      showSuccess('Webhook测试成功');
    } catch (error) {
      showError('Webhook测试失败');
    }
  };

  if (webhooksLoading || logsLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Webhook className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警Webhook</h1>
            <p className="text-sm text-gray-500">配置告警Webhook以发送告警到外部系统</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建Webhook
          </Button>
          <Button onClick={() => { refetchWebhooks(); refetchLogs(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('webhooks')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'webhooks' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Webhook配置
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'logs' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              调用日志 ({logsData?.length || 0})
            </button>
          </div>
        </CardContent>
      </Card>

      {activeTab === 'webhooks' && (
        <>
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                  <Select
                    value={filters.enabled}
                    onChange={(e) => setFilters({ ...filters, enabled: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="enabled">已启用</option>
                    <option value="disabled">已禁用</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <Input
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    placeholder="搜索Webhook名称"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Webhook配置 ({filteredWebhooks.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>URL</TableHead>
                    <TableHead>方法</TableHead>
                    <TableHead>超时</TableHead>
                    <TableHead>重试次数</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredWebhooks.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <EmptyState
                          title="没有Webhook配置"
                          description="当前没有Webhook配置"
                          action={<Button onClick={handleCreate}>创建第一个Webhook</Button>}
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredWebhooks.map((webhook) => (
                      <TableRow key={webhook.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell className="font-medium">{webhook.name}</TableCell>
                        <TableCell>
                          <Badge className={webhook.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {webhook.enabled ? '已启用' : '已禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500 truncate max-w-xs">{webhook.url}</TableCell>
                        <TableCell className="text-sm font-mono">{webhook.method}</TableCell>
                        <TableCell className="text-sm">{webhook.timeout}s</TableCell>
                        <TableCell className="text-sm">{webhook.retry_count}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleTestWebhook(webhook.id)}>
                              测试
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleToggleEnabled(webhook)}>
                              {webhook.enabled ? '禁用' : '启用'}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(webhook)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(webhook.id)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>调用日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Webhook名称</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>响应码</TableHead>
                  <TableHead>耗时</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!logsData || logsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <EmptyState title="没有日志" description="当前没有Webhook调用日志" />
                    </TableCell>
                  </TableRow>
                ) : (
                  logsData.map((log) => (
                    <TableRow key={log.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{log.webhook_name}</TableCell>
                      <TableCell>
                        <Badge className={log.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {log.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{log.response_code || '-'}</TableCell>
                      <TableCell className="text-sm">{log.duration}ms</TableCell>
                      <TableCell className="text-sm text-gray-500 truncate max-w-xs">{log.error_message || '-'}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(log.timestamp).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isEditing ? '编辑Webhook' : '创建Webhook'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入Webhook名称"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="输入Webhook描述"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
                <Input
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="https://example.com/webhook"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">方法</label>
                <Select
                  value={formData.method}
                  onChange={(e) => setFormData({ ...formData, method: e.target.value as any })}
                >
                  <option value="POST">POST</option>
                  <option value="GET">GET</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">超时(秒)</label>
                <Input
                  type="number"
                  value={formData.timeout}
                  onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 30 })}
                  placeholder="30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">重试次数</label>
                <Input
                  type="number"
                  value={formData.retry_count}
                  onChange={(e) => setFormData({ ...formData, retry_count: parseInt(e.target.value) || 3 })}
                  placeholder="3"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">重试间隔(秒)</label>
                <Input
                  type="number"
                  value={formData.retry_interval}
                  onChange={(e) => setFormData({ ...formData, retry_interval: parseInt(e.target.value) || 5 })}
                  placeholder="5"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Body模板</label>
              <Input
                value={formData.body_template}
                onChange={(e) => setFormData({ ...formData, body_template: e.target.value })}
                placeholder='{"alert": "{{.title}}", "severity": "{{.severity}}"}'
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">启用</label>
              <Select
                value={formData.enabled ? 'true' : 'false'}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.value === 'true' })}
              >
                <option value="true">是</option>
                <option value="false">否</option>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>取消</Button>
            <Button onClick={handleSave} disabled={createWebhookMutation.isPending || updateWebhookMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
