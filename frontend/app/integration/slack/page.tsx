'use client';

import { useState, useEffect } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DataTable } from '@/components/ui/DataTable';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { MessageSquare, RefreshCw, TestTube, Settings, Send } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState, ErrorBoundary } from '@/components/CommonUI';

interface SlackConfig {
  config_id: string;
  name: string;
  workspace: string;
  bot_token: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  last_sync: string | null;
  channel_count: number;
}

interface SlackChannel {
  channel_id: string;
  name: string;
  is_private: boolean;
  member_count: number;
}

interface SlackMessage {
  channel: string;
  message_id: string;
  text: string;
  user: string;
  timestamp: string;
}

export default function SlackPage() {
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    workspace: '',
    bot_token: '',
    enabled: true,
  });
  const [messageData, setMessageData] = useState({
    channel: '',
    text: '',
  });

  const { isLoading, error, setError } = useLoadingState();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;
  const queryClient = useQueryClient();

  const { data: configData, refetch: refetchConfig } = useQuery<{ configs: SlackConfig[] }>({
    queryKey: ['slack-config'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/slack/config');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: channelData, refetch: refetchChannels } = useQuery<{ channels: SlackChannel[] }>({
    queryKey: ['slack-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/slack/channels');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const { data: messageHistoryData, refetch: refetchMessages } = useQuery<{ messages: SlackMessage[] }>({
    queryKey: ['slack-messages'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/slack/messages');
      return resp.data;
    },
    refetchInterval: 60000,
  });

  const configMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/slack/config', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack-config'] });
      setShowConfigModal(false);
      setFormData({ name: '', workspace: '', bot_token: '', enabled: true });
      showSuccess('Slack配置成功');
    },
    onError: () => {
      showError('Slack配置失败');
    },
  });

  const sendMutation = useMutation({
    mutationFn: async (data: typeof messageData) => {
      const resp = await api.post('/api/v1/integration/slack/send', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack-messages'] });
      setShowMessageModal(false);
      setMessageData({ channel: '', text: '' });
      showSuccess('消息发送成功');
    },
    onError: () => {
      showError('消息发送失败');
    },
  });

  const testMutation = useMutation({
    mutationFn: async (id: string) => {
      const resp = await api.post(`/api/v1/integration/slack/test/${id}`);
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
      showError('Failed to load Slack data');
    }
  }, [error, showError]);

  const configs = configData?.configs || [];
  const channels = channelData?.channels || [];
  const messages = messageHistoryData?.messages || [];

  const configColumns = [
    { key: 'name' as const, label: '名称' },
    { key: 'workspace' as const, label: '工作区' },
    { key: 'status' as const, label: '状态', render: (value: string) => (
      <StatusBadge 
        status={value === 'connected' ? 'success' : value === 'error' ? 'error' : 'warning'} 
        text={value} 
      />
    )},
    { key: 'enabled' as const, label: '启用', render: (value: boolean) => (value ? '是' : '否') },
    { key: 'channel_count' as const, label: '频道数' },
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
          description="无法加载Slack数据，请稍后重试"
          action={<Button onClick={() => { refetchConfig(); refetchChannels(); refetchMessages(); }}>重试</Button>}
        />
      }>
        <EmptyState
          title="加载失败"
          description={error.message}
          action={<Button onClick={() => { refetchConfig(); refetchChannels(); refetchMessages(); }}>重试</Button>}
        />
      </ErrorBoundary>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageSquare className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Slack集成</h1>
            <p className="text-sm text-gray-500">管理Slack团队沟通集成</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => { refetchConfig(); refetchChannels(); refetchMessages(); }} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowConfigModal(true)}>
            <Settings className="h-4 w-4 mr-2" />
            添加配置
          </Button>
          <Button onClick={() => setShowMessageModal(true)}>
            <Send className="h-4 w-4 mr-2" />
            发送消息
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
            <p className="text-sm text-gray-500 mt-1">Slack配置</p>
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
            <CardTitle className="text-sm">频道总数</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{channels.length}</p>
            <p className="text-sm text-gray-500 mt-1">Slack频道</p>
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
              description="还没有配置Slack集成"
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
            <MessageSquare className="h-5 w-5" />
            频道列表
          </CardTitle>
        </CardHeader>
        <CardContent>
          {channels.length === 0 ? (
            <EmptyState
              title="暂无频道"
              description="还没有获取到Slack频道"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {channels.map((channel) => (
                <div key={channel.channel_id} className="p-4 border rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium">#{channel.name}</span>
                    {channel.is_private && (
                      <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">私有</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">成员数: {channel.member_count}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            消息历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {messages.length === 0 ? (
            <EmptyState
              title="暂无消息"
              description="还没有获取到消息历史"
            />
          ) : (
            <div className="space-y-2">
              {messages.slice(0, 10).map((msg) => (
                <div key={msg.message_id} className="p-3 border rounded hover:bg-gray-50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">#{msg.channel}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(msg.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{msg.text}</p>
                  <p className="text-xs text-gray-500 mt-1">用户: {msg.user}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
