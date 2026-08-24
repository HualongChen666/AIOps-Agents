'use client'

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useLoadingState, useToast } from '@/hooks/useEnhancements';
import api from '@/lib/api';

interface MfaMethod {
  id: string;
  type: 'totp' | 'sms' | 'email' | 'hardware_token' | 'biometric';
  name: string;
  description: string;
  enabled: boolean;
  required: boolean;
  priority: number;
}

interface UserMfa {
  id: string;
  userId: string;
  userName: string;
  method: string;
  methodName: string;
  enabled: boolean;
  verified: boolean;
  lastUsed: string;
  enrolledAt: string;
}

interface MfaEvent {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  method: string;
  action: 'enroll' | 'verify' | 'disable' | 'failed';
  ipAddress: string;
  userAgent: string;
  success: boolean;
  reason?: string;
}

export default function MfaPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [methods, setMethods] = useState<MfaMethod[]>([]);
  const [userMfas, setUserMfas] = useState<UserMfa[]>([]);
  const [events, setEvents] = useState<MfaEvent[]>([]);
  const [activeTab, setActiveTab] = useState<'methods' | 'users' | 'events'>('methods');

  const loadMfaData = async () => {
    setLoading(true);
    try {
      const [methodsRes, usersRes, eventsRes] = await Promise.all([
        api.get('/api/v1/security/mfa/methods'),
        api.get('/api/v1/security/mfa/users'),
        api.get('/api/v1/security/mfa/events'),
      ]);

      const methodsData = methodsRes.data?.methods || [];
      const usersData = usersRes.data?.users || [];
      const eventsData = eventsRes.data?.events || [];

      setMethods(methodsData);
      setUserMfas(usersData);
      setEvents(eventsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleToggleMethod = async (methodId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/mfa/methods/${methodId}`, { enabled });
      success('方法状态更新成功');
      loadMfaData();
    } catch (err) {
      showError('方法状态更新失败');
    }
  };

  const handleToggleRequired = async (methodId: string, required: boolean) => {
    try {
      await api.patch(`/api/v1/security/mfa/methods/${methodId}`, { required });
      success('必需设置更新成功');
      loadMfaData();
    } catch (err) {
      showError('必需设置更新失败');
    }
  };

  const handleDisableUserMfa = async (userMfaId: string) => {
    try {
      await api.post(`/api/v1/security/mfa/users/${userMfaId}/disable`);
      success('用户MFA已禁用');
      loadMfaData();
    } catch (err) {
      showError('禁用失败');
    }
  };

  useEffect(() => {
    loadMfaData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-600 dark:text-red-400">Error: {error.message}</div>
      </div>
    );
  }

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'totp':
        return 'bg-blue-100 text-blue-800';
      case 'sms':
        return 'bg-green-100 text-green-800';
      case 'email':
        return 'bg-purple-100 text-purple-800';
      case 'hardware_token':
        return 'bg-orange-100 text-orange-800';
      case 'biometric':
        return 'bg-pink-100 text-pink-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'enroll':
        return 'bg-blue-100 text-blue-800';
      case 'verify':
        return 'bg-green-100 text-green-800';
      case 'disable':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'methods' as const, label: '认证方法' },
    { key: 'users' as const, label: '用户MFA' },
    { key: 'events' as const, label: '认证事件' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">多因子认证 (MFA)</h1>
        <Button onClick={loadMfaData}>刷新数据</Button>
      </div>

      {/* 标签页 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg font-medium transition ${activeTab === tab.key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 认证方法 */}
      {activeTab === 'methods' && (
        <Card>
          <CardHeader>
            <CardTitle>认证方法</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead>优先级</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>必需</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {methods.length > 0 ? methods.map((method) => (
                  <TableRow key={method.id}>
                    <TableCell className="font-medium">{method.name}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(method.type)}>{method.type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{method.description}</TableCell>
                    <TableCell>{method.priority}</TableCell>
                    <TableCell>
                      <Badge className={method.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {method.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={method.required ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}>
                        {method.required ? '必需' : '可选'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleMethod(method.id, !method.enabled)}
                        >
                          {method.enabled ? '禁用' : '启用'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleRequired(method.id, !method.required)}
                        >
                          {method.required ? '设为可选' : '设为必需'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No MFA methods found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 用户MFA */}
      {activeTab === 'users' && (
        <Card>
          <CardHeader>
            <CardTitle>用户MFA</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>方法名称</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>已验证</TableHead>
                  <TableHead>最后使用</TableHead>
                  <TableHead>注册时间</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userMfas.length > 0 ? userMfas.map((userMfa) => (
                  <TableRow key={userMfa.id}>
                    <TableCell className="font-medium">{userMfa.userName}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(userMfa.method as any)}>{userMfa.method.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{userMfa.methodName}</TableCell>
                    <TableCell>
                      <Badge className={userMfa.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {userMfa.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={userMfa.verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}>
                        {userMfa.verified ? '已验证' : '未验证'}
                      </Badge>
                    </TableCell>
                    <TableCell>{userMfa.lastUsed ? new Date(userMfa.lastUsed).toLocaleString() : '-'}</TableCell>
                    <TableCell>{new Date(userMfa.enrolledAt).toLocaleString()}</TableCell>
                    <TableCell>
                      {userMfa.enabled && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDisableUserMfa(userMfa.id)}
                        >
                          禁用
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No user MFA found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 认证事件 */}
      {activeTab === 'events' && (
        <Card>
          <CardHeader>
            <CardTitle>认证事件</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>成功</TableHead>
                  <TableHead>原因</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.length > 0 ? events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{event.userName}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(event.method as any)}>{event.method.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getActionColor(event.action)}>{event.action}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={event.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {event.success ? '成功' : '失败'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{event.reason || '-'}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No MFA events found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
