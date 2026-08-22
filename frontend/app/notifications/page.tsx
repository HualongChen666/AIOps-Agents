'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Bell, RefreshCw, Send, MessageSquare, Mail, CheckCircle, XCircle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface NotificationChannel {
  name: string;
  type: string;
  enabled: boolean;
  config?: Record<string, any>;
}

interface NotificationHistory {
  id: string;
  channel: string;
  recipient: string;
  subject: string;
  status: string;
  sent_at: string;
}

export default function NotificationPage() {
  const [showSendModal, setShowSendModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'channels' | 'history' | 'slack'>('channels');
  const [formData, setFormData] = useState({
    channel: 'slack',
    recipient: '',
    subject: '',
    body: '',
  });
  const [slackFormData, setSlackFormData] = useState({
    text: '',
    channel: '',
  });

  const queryClient = useQueryClient();

  // 🔧 获取通知渠道（从integration_router）
  const { data: channelsData, isLoading: channelsLoading, error: channelsError, refetch: refetchChannels } = useQuery<{ channels: NotificationChannel[] }>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/notification/channels');
      return resp.data;
    },
    refetchInterval: 120000, // 2分钟刷新
  });

  // 🔧 获取Slack健康状态
  const { data: slackHealthData, isLoading: slackHealthLoading, refetch: refetchSlackHealth } = useQuery<{ status: string; default_channel: string }>({
    queryKey: ['slack-health'],
    queryFn: async () => {
      const resp = await api.get('/api/slack/health');
      return resp.data;
    },
    refetchInterval: 300000, // 5分钟刷新
  });

  // 🔧 发送通知
  const sendNotificationMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/notification/send', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-history'] });
      setShowSendModal(false);
      showSuccess('通知发送成功');
    },
    onError: () => {
      showError('通知发送失败');
    },
  });

  // 🔧 发送Slack消息
  const sendSlackMessageMutation = useMutation({
    mutationFn: async (data: typeof slackFormData) => {
      const resp = await api.post('/api/slack/message', data);
      return resp.data;
    },
    onSuccess: () => {
      setSlackFormData({ text: '', channel: '' });
      showSuccess('Slack消息发送成功');
    },
    onError: () => {
      showError('Slack消息发送失败');
    },
  });

  // 🔧 P1 Integration: Use enhanced loading state
  const { isLoading: pageLoading, error: pageError, setError: setPageError } = useLoadingState(channelsLoading || slackHealthLoading);

  // 🔧 P1 Integration: Use toast notifications
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  // 🔧 P1 Integration: Handle errors with toast
  useEffect(() => {
    if (channelsError) {
      showError('Failed to load notification channels');
      setPageError(channelsError as Error);
    }
  }, [channelsError, showError, setPageError]);

  const channels = channelsData?.channels || [];
  const slackHealth = slackHealthData || { status: 'not_configured', default_channel: '' };

  const channelColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'type' as const, label: '类型' },
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
  ];

  const handleSendNotification = () => {
    sendNotificationMutation.mutate(formData);
  };

  const handleSendSlackMessage = () => {
    sendSlackMessageMutation.mutate(slackFormData);
  };

  const handleRefresh = () => {
    refetchChannels();
    refetchSlackHealth();
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
          description="无法加载通知数据，请稍后重试"
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

  const activeChannels = channels.filter((c) => c.enabled).length;
  const totalChannels = channels.length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">通知管理</h1>
            <p className="text-sm text-gray-500">多渠道通知和Slack集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowSendModal(true)}>
            <Send className="h-4 w-4 mr-2" />
            发送通知
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">总渠道数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{totalChannels}</p>
            <p className="text-sm text-gray-500 mt-1">通知渠道总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">活跃渠道</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{activeChannels}</p>
            <p className="text-sm text-gray-500 mt-1">已启用的渠道</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Slack状态</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${slackHealth.status === 'healthy' ? 'text-green-600' : 'text-gray-600'}`}>
              {slackHealth.status === 'healthy' ? '正常' : '未配置'}
            </p>
            <p className="text-sm text-gray-500 mt-1">Slack集成状态</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <Button
          variant={activeTab === 'channels' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('channels')}
        >
          <Bell className="h-4 w-4 mr-2" />
          通知渠道
        </Button>
        <Button
          variant={activeTab === 'slack' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('slack')}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          Slack集成
        </Button>
      </div>

      {/* Channels Tab */}
      {activeTab === 'channels' && (
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

      {/* Slack Tab */}
      {activeTab === 'slack' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Slack集成状态
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">集成状态</span>
                  <span className={`text-sm font-medium ${
                    slackHealth.status === 'healthy' ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {slackHealth.status === 'healthy' ? '正常' : '未配置'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">默认频道</span>
                  <span className="text-sm font-medium text-gray-900">{slackHealth.default_channel || '-'}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>发送Slack消息</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">消息内容</label>
                  <textarea
                    value={slackFormData.text}
                    onChange={(e) => setSlackFormData({ ...slackFormData, text: e.target.value })}
                    placeholder="输入Slack消息..."
                    className="w-full px-3 py-2 border rounded-md bg-white min-h-[100px]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">频道（可选）</label>
                  <Input
                    value={slackFormData.channel}
                    onChange={(e) => setSlackFormData({ ...slackFormData, channel: e.target.value })}
                    placeholder="频道ID或名称"
                  />
                </div>
                <Button onClick={handleSendSlackMessage} disabled={sendSlackMessageMutation.isPending}>
                  <Send className="h-4 w-4 mr-2" />
                  {sendSlackMessageMutation.isPending ? '发送中...' : '发送'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Send Notification Modal */}
      <EnhancedModal
        open={showSendModal}
        onOpenChange={setShowSendModal}
        title="发送通知"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">渠道</label>
            <select
              value={formData.channel}
              onChange={(e) => setFormData({ ...formData, channel: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="slack">Slack</option>
              <option value="email">Email</option>
              <option value="teams">Teams</option>
              <option value="dingtalk">钉钉</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">接收者</label>
            <Input
              value={formData.recipient}
              onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
              placeholder="接收者地址"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">主题</label>
            <Input
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              placeholder="通知主题"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">内容</label>
            <textarea
              value={formData.body}
              onChange={(e) => setFormData({ ...formData, body: e.target.value })}
              placeholder="通知内容"
              className="w-full px-3 py-2 border rounded-md bg-white min-h-[150px]"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowSendModal(false)}>
              取消
            </Button>
            <Button onClick={handleSendNotification} disabled={sendNotificationMutation.isPending}>
              {sendNotificationMutation.isPending ? '发送中...' : '发送'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}