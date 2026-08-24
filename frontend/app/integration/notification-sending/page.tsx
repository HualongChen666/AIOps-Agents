'use client';

import { useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { EnhancedModal } from '@/components/ui/EnhancedModal';
import { Send, RefreshCw, CheckCircle, XCircle, Bell } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/useEnhancements';
import { LoadingSpinner, EmptyState } from '@/components/CommonUI';

interface Notification {
  notification_id: string;
  channel: string;
  recipient: string;
  subject: string;
  message: string;
  status: 'pending' | 'sent' | 'failed';
  sent_at: string | null;
  error: string | null;
}

interface NotificationChannel {
  channel_id: string;
  name: string;
  type: string;
  enabled: boolean;
}

export default function NotificationSendingPage() {
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    channel: '',
    recipient: '',
    subject: '',
    message: '',
  });

  const queryClient = useQueryClient();
  const toast = useToast();
  const showSuccess = toast.success;
  const showError = toast.error;

  const { data: channelsData, isLoading: channelsLoading } = useQuery<{ channels: NotificationChannel[] }>({
    queryKey: ['notification-channels'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/notification/channels');
      return resp.data;
    },
  });

  const { data: historyData, refetch } = useQuery<{ notifications: Notification[] }>({
    queryKey: ['notification-history'],
    queryFn: async () => {
      const resp = await api.get('/api/v1/integration/notification/history');
      return resp.data;
    },
    refetchInterval: 30000,
  });

  const sendMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const resp = await api.post('/api/v1/integration/notification/send', data);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-history'] });
      setShowModal(false);
      setFormData({ channel: '', recipient: '', subject: '', message: '' });
      showSuccess('通知发送成功');
    },
    onError: (error: any) => {
      showError(error.response?.data?.message || '通知发送失败');
    },
  });

  const handleSend = () => {
    if (!formData.channel || !formData.recipient || !formData.message) {
      showError('请填写必填字段');
      return;
    }
    sendMutation.mutate(formData);
  };

  const channels = channelsData?.channels || [];
  const notifications = historyData?.notifications || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Send className="h-8 w-8 text-[var(--accent-cyan)]" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">通知发送</h1>
            <p className="text-sm text-gray-500">发送通知到各种渠道</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => refetch()} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            刷新
          </Button>
          <Button onClick={() => setShowModal(true)}>
            <Send className="h-4 w-4 mr-2" />
            发送通知
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">可用渠道</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-900">{channels.length}</p>
            <p className="text-sm text-gray-500 mt-1">通知渠道</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">已发送</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {notifications.filter(n => n.status === 'sent').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">成功发送</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">发送失败</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">
              {notifications.filter(n => n.status === 'failed').length}
            </p>
            <p className="text-sm text-gray-500 mt-1">失败的通知</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            发送历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {channelsLoading ? (
            <LoadingSpinner size="md" />
          ) : notifications.length === 0 ? (
            <EmptyState
              title="暂无发送记录"
              description="还没有发送过通知"
            />
          ) : (
            <div className="space-y-3">
              {notifications.slice(0, 10).map((notification) => (
                <div
                  key={notification.notification_id}
                  className="p-4 border rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{notification.subject}</span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        notification.status === 'sent' ? 'bg-green-100 text-green-800' :
                        notification.status === 'failed' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {notification.status}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">
                      {notification.sent_at ? new Date(notification.sent_at).toLocaleString() : '-'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>渠道: {notification.channel}</p>
                    <p>收件人: {notification.recipient}</p>
                    {notification.error && (
                      <p className="text-red-600 mt-1">错误: {notification.error}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <EnhancedModal
        open={showModal}
        onOpenChange={setShowModal}
        title="发送通知"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">通知渠道</label>
            <select
              value={formData.channel}
              onChange={(e) => setFormData({ ...formData, channel: e.target.value })}
              className="w-full px-3 py-2 border rounded-md bg-white"
            >
              <option value="">选择渠道</option>
              {channels.map((channel) => (
                <option key={channel.channel_id} value={channel.channel_id}>
                  {channel.name} ({channel.type})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">收件人</label>
            <Input
              value={formData.recipient}
              onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
              placeholder="email@example.com 或 #channel"
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
            <label className="block text-sm font-medium text-gray-700 mb-1">消息内容</label>
            <textarea
              value={formData.message}
              onChange={(e) => setFormData({ ...formData, message: e.target.value })}
              placeholder="通知消息内容"
              rows={4}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowModal(false)}>
              取消
            </Button>
            <Button 
              onClick={handleSend} 
              disabled={sendMutation.isPending}
            >
              {sendMutation.isPending ? '发送中...' : '发送'}
            </Button>
          </div>
        </div>
      </EnhancedModal>
    </div>
  );
}
