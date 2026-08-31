'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import api from '@/lib/api';

interface Notification {
  id: string;
  title: string;
  message: string;
  level: string;
  status: string;
  created_at: string;
  read: boolean;
}

interface NotificationChannel {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  config: Record<string, any>;
}

export default function NotifyPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'notifications' | 'channels'>('notifications');

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'notifications') {
        await fetchNotifications();
      } else {
        await fetchChannels();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchNotifications = async () => {
    // Mock data for basic notify page
    const mockNotifications: Notification[] = [
      {
        id: '1',
        title: '系统告警',
        message: 'CPU使用率超过90%',
        level: 'critical',
        status: 'active',
        created_at: new Date().toISOString(),
        read: false,
      },
      {
        id: '2',
        title: '服务重启',
        message: 'API服务已成功重启',
        level: 'info',
        status: 'resolved',
        created_at: new Date(Date.now() - 3600000).toISOString(),
        read: true,
      },
      {
        id: '3',
        title: '磁盘空间警告',
        message: '/var分区使用率超过80%',
        level: 'warning',
        status: 'active',
        created_at: new Date(Date.now() - 7200000).toISOString(),
        read: false,
      },
    ];
    setNotifications(mockNotifications);
  };

  const fetchChannels = async () => {
    try {
      const res = await api.get('/api/v1/notify/channels');
      setChannels(res.data || []);
    } catch (err) {
      // Fallback to mock data if API fails
      const mockChannels: NotificationChannel[] = [
        {
          id: '1',
          name: '邮件通知',
          type: 'email',
          enabled: true,
          config: { smtp_host: 'smtp.example.com' },
        },
        {
          id: '2',
          name: 'Slack通知',
          type: 'slack',
          enabled: true,
          config: { webhook_url: 'https://hooks.slack.com/services/xxx' },
        },
        {
          id: '3',
          name: '短信通知',
          type: 'sms',
          enabled: false,
          config: {},
        },
      ];
      setChannels(mockChannels);
    }
  };

  const markAsRead = async (id: string) => {
    setNotifications(notifications.map(n => 
      n.id === id ? { ...n, read: true } : n
    ));
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-500';
      case 'warning':
        return 'bg-yellow-500';
      case 'info':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading && !notifications.length && !channels.length) {
    return <div className="flex items-center justify-center h-64"><div className="text-gray-500">加载中...</div></div>;
  }

  if (error) {
    return <div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800">{error}</div><Button onClick={fetchData} className="mt-2">重试</Button></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">通知系统</h1>
        <Button onClick={fetchData}>刷新</Button>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        <button
          onClick={() => setActiveTab('notifications')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'notifications'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          通知
        </button>
        <button
          onClick={() => setActiveTab('channels')}
          className={`px-4 py-2 font-medium ${
            activeTab === 'channels'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          通知渠道
        </button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            {activeTab === 'notifications' ? '通知列表' : '通知渠道'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : (
            <div className="space-y-4">
              {activeTab === 'notifications' && notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`border rounded-lg p-4 ${!notification.read ? 'bg-blue-50' : ''}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className={`w-3 h-3 rounded-full ${getLevelColor(notification.level)}`} />
                        <h3 className="font-semibold">{notification.title}</h3>
                        {!notification.read && <Badge variant="default">未读</Badge>}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                      <div className="text-xs text-gray-500 mt-2">
                        {new Date(notification.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={notification.status === 'active' ? 'default' : 'secondary'}>
                        {notification.status}
                      </Badge>
                      {!notification.read && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => markAsRead(notification.id)}
                        >
                          标记已读
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {activeTab === 'channels' && channels.map((channel) => (
                <div key={channel.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold">{channel.name}</h3>
                      <div className="text-sm text-gray-500">类型: {channel.type}</div>
                      <div className="text-sm text-gray-500">
                        配置: {Object.keys(channel.config).length} 项
                      </div>
                    </div>
                    <Badge variant={channel.enabled ? 'default' : 'secondary'}>
                      {channel.enabled ? '启用' : '禁用'}
                    </Badge>
                  </div>
                </div>
              ))}

              {activeTab === 'notifications' && notifications.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无通知</div>
              )}
              {activeTab === 'channels' && channels.length === 0 && (
                <div className="text-center py-8 text-gray-500">暂无通知渠道</div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
