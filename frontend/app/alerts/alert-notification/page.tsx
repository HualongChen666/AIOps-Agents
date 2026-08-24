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
import { Bell, Plus, Edit, Trash2, CheckCircle, XCircle, RefreshCw, Send } from 'lucide-react';

interface NotificationChannel {
  id: string;
  name: string;
  type: 'email' | 'slack' | 'pagerduty' | 'sms' | 'webhook' | 'teams';
  enabled: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface NotificationLog {
  id: string;
  channel_id: string;
  channel_name: string;
  alert_id: string;
  alert_title: string;
  status: 'sent' | 'failed' | 'pending';
  error_message?: string;
  sent_at: string;
}

export default function AlertNotificationPage() {
  const [selectedChannel, setSelectedChannel] = useState<NotificationChannel | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState<'channels' | 'logs'>('channels');
  const [filters, setFilters] = useState({
    enabled: 'all',
    type: 'all',
    search: '',
  });
  const [showDialog, setShowDialog] = useState(false);
  const [formData, setFormData] = useState<Partial<NotificationChannel>>({
    name: '',
    type: 'email',
    enabled: true,
    config: {},
  });

  const debouncedSearch = useDebounce(filters.search, 300);
  const { isLoading, error, refetch } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: channelsData, isLoading: channelsLoading, error: channelsError, refetch: refetchChannels } = useQuery<NotificationChannel[]>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/notification/channels');
      return resp.data.channels || resp.data || [];
    },
    refetchInterval: 30000,
  });

  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery<NotificationLog[]>({
    queryKey: ['notification-logs'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/alerts/notification/logs?limit=50');
      return resp.data.logs || resp.data || [];
    },
    refetchInterval: 15000,
  });

  const createChannelMutation = useMutation({
    mutationFn: async (data: Partial<NotificationChannel>) => {
      const resp = await api.post('/api/v1/alerts/notification/channels', data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('通知通道创建成功');
      setShowDialog(false);
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
    },
    onError: () => showError('创建通知通道失败'),
  });

  const updateChannelMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<NotificationChannel> }) => {
      const resp = await api.put(`/api/v1/alerts/notification/channels/${id}`, data);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('通知通道更新成功');
      setShowDialog(false);
      setSelectedChannel(null);
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
    },
    onError: () => showError('更新通知通道失败'),
  });

  const deleteChannelMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.delete(`/api/v1/alerts/notification/channels/${id}`);
      return resp.data;
    },
    onSuccess: () => {
      showSuccess('通知通道删除成功');
      queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
    },
    onError: () => showError('删除通知通道失败'),
  });

  useEffect(() => {
    if (channelsError) showError('Failed to load notification channels');
  }, [channelsError, showError]);

  const filteredChannels = (channelsData || []).filter((channel) => {
    if (filters.enabled !== 'all' && (filters.enabled === 'enabled' ? !channel.enabled : channel.enabled)) return false;
    if (filters.type !== 'all' && channel.type !== filters.type) return false;
    if (debouncedSearch && !channel.name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
    return true;
  });

  const handleCreate = () => {
    setIsEditing(false);
    setFormData({
      name: '',
      type: 'email',
      enabled: true,
      config: {},
    });
    setShowDialog(true);
  };

  const handleEdit = (channel: NotificationChannel) => {
    setIsEditing(true);
    setSelectedChannel(channel);
    setFormData(channel);
    setShowDialog(true);
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定要删除此通知通道吗？')) return;
    deleteChannelMutation.mutate(id);
  };

  const handleSave = () => {
    if (isEditing && selectedChannel) {
      updateChannelMutation.mutate({ id: selectedChannel.id, data: formData });
    } else {
      createChannelMutation.mutate(formData);
    }
  };

  const handleToggleEnabled = async (channel: NotificationChannel) => {
    updateChannelMutation.mutate({ id: channel.id, data: { enabled: !channel.enabled } });
  };

  const handleTestNotification = async (id: string) => {
    try {
      await api.post(`/api/v1/alerts/notification/channels/${id}/test`);
      showSuccess('测试通知已发送');
    } catch (error) {
      showError('发送测试通知失败');
    }
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      email: 'bg-blue-100 text-blue-800',
      slack: 'bg-purple-100 text-purple-800',
      pagerduty: 'bg-red-100 text-red-800',
      sms: 'bg-green-100 text-green-800',
      webhook: 'bg-orange-100 text-orange-800',
      teams: 'bg-cyan-100 text-cyan-800',
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (channelsLoading || logsLoading) {
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
          <Bell className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">告警通知</h1>
            <p className="text-sm text-gray-500">配置告警通知通道和查看通知记录</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" />
            创建通知通道
          </Button>
          <Button onClick={() => { refetchChannels(); refetchLogs(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('channels')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'channels' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              通知通道
            </button>
            <button
              onClick={() => setActiveTab('logs')}
              className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === 'logs' ? 'bg-[var(--accent-blue)] text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              通知日志 ({logsData?.length || 0})
            </button>
          </div>
        </CardContent>
      </Card>

      {activeTab === 'channels' && (
        <>
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                  <Select
                    value={filters.type}
                    onChange={(e) => setFilters({ ...filters, type: e.target.value })}
                  >
                    <option value="all">全部</option>
                    <option value="email">邮件</option>
                    <option value="slack">Slack</option>
                    <option value="pagerduty">PagerDuty</option>
                    <option value="sms">短信</option>
                    <option value="webhook">Webhook</option>
                    <option value="teams">Teams</option>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">搜索</label>
                  <Input
                    value={filters.search}
                    onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                    placeholder="搜索通道名称"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>通知通道 ({filteredChannels.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>配置</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredChannels.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <EmptyState
                          title="没有通知通道"
                          description="当前没有通知通道"
                          action={<Button onClick={handleCreate}>创建第一个通知通道</Button>}
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredChannels.map((channel) => (
                      <TableRow key={channel.id} className="cursor-pointer hover:bg-gray-50">
                        <TableCell className="font-medium">{channel.name}</TableCell>
                        <TableCell>
                          <Badge className={channel.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {channel.enabled ? '已启用' : '已禁用'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={getTypeColor(channel.type)}>
                            {channel.type}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-500">{Object.keys(channel.config).length} 项</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleTestNotification(channel.id)}>
                              <Send className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleToggleEnabled(channel)}>
                              {channel.enabled ? '禁用' : '启用'}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(channel)}>
                              <Edit className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(channel.id)}>
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
            <CardTitle>通知日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>通道名称</TableHead>
                  <TableHead>告警标题</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>发送时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(!logsData || logsData.length === 0) ? (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <EmptyState title="没有通知日志" description="当前没有通知日志" />
                    </TableCell>
                  </TableRow>
                ) : (
                  logsData.map((log) => (
                    <TableRow key={log.id} className="cursor-pointer hover:bg-gray-50">
                      <TableCell className="font-medium">{log.channel_name}</TableCell>
                      <TableCell className="text-sm">{log.alert_title}</TableCell>
                      <TableCell>
                        <Badge className={log.status === 'sent' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                          {log.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-500 truncate max-w-xs">{log.error_message || '-'}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(log.sent_at).toLocaleString()}
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
            <DialogTitle>{isEditing ? '编辑通知通道' : '创建通知通道'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入通道名称"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">类型</label>
                <Select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                >
                  <option value="email">邮件</option>
                  <option value="slack">Slack</option>
                  <option value="pagerduty">PagerDuty</option>
                  <option value="sms">短信</option>
                  <option value="webhook">Webhook</option>
                  <option value="teams">Teams</option>
                </Select>
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDialog(false)}>取消</Button>
            <Button onClick={handleSave} disabled={createChannelMutation.isPending || updateChannelMutation.isPending}>
              {isEditing ? '更新' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
