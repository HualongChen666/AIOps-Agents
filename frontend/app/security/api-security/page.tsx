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

interface ApiEndpoint {
  id: string;
  path: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  authRequired: boolean;
  authType: 'bearer' | 'basic' | 'api_key' | 'oauth2' | 'none';
  rateLimit: number;
  enabled: boolean;
  description: string;
  lastAccessed: string;
}

interface ApiSecurityEvent {
  id: string;
  timestamp: string;
  endpoint: string;
  method: string;
  userId: string;
  ipAddress: string;
  userAgent: string;
  status: 'allowed' | 'blocked' | 'rate_limited' | 'unauthorized';
  reason: string;
  responseTime: number;
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  userId: string;
  permissions: string[];
  enabled: boolean;
  expiresAt: string;
  lastUsed: string;
  createdAt: string;
}

export default function ApiSecurityPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [endpoints, setEndpoints] = useState<ApiEndpoint[]>([]);
  const [events, setEvents] = useState<ApiSecurityEvent[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [activeTab, setActiveTab] = useState<'endpoints' | 'events' | 'keys'>('endpoints');
  const [showAddEndpointModal, setShowAddEndpointModal] = useState(false);
  const [showAddKeyModal, setShowAddKeyModal] = useState(false);
  const [newEndpoint, setNewEndpoint] = useState({
    path: '',
    method: 'GET' as const,
    authRequired: true,
    authType: 'bearer' as const,
    rateLimit: 1000,
    description: '',
  });
  const [newKey, setNewKey] = useState({
    name: '',
    userId: '',
    permissions: [] as string[],
    expiresIn: 30,
  });

  const loadApiSecurityData = async () => {
    setLoading(true);
    try {
      const [endpointsRes, eventsRes, keysRes] = await Promise.all([
        api.get('/api/v1/security/api-security/endpoints'),
        api.get('/api/v1/security/api-security/events'),
        api.get('/api/v1/security/api-security/keys'),
      ]);

      const endpointsData = endpointsRes.data?.endpoints || [];
      const eventsData = eventsRes.data?.events || [];
      const keysData = keysRes.data?.keys || [];

      setEndpoints(endpointsData);
      setEvents(eventsData);
      setApiKeys(keysData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddEndpoint = async () => {
    try {
      await api.post('/api/v1/security/api-security/endpoints', newEndpoint);
      success('API端点添加成功');
      setShowAddEndpointModal(false);
      setNewEndpoint({
        path: '',
        method: 'GET',
        authRequired: true,
        authType: 'bearer',
        rateLimit: 1000,
        description: '',
      });
      loadApiSecurityData();
    } catch (err) {
      showError('端点添加失败');
    }
  };

  const handleToggleEndpoint = async (endpointId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/api-security/endpoints/${endpointId}`, { enabled });
      success('端点状态更新成功');
      loadApiSecurityData();
    } catch (err) {
      showError('端点状态更新失败');
    }
  };

  const handleGenerateKey = async () => {
    try {
      await api.post('/api/v1/security/api-security/keys', newKey);
      success('API密钥生成成功');
      setShowAddKeyModal(false);
      setNewKey({ name: '', userId: '', permissions: [], expiresIn: 30 });
      loadApiSecurityData();
    } catch (err) {
      showError('密钥生成失败');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      await api.delete(`/api/v1/security/api-security/keys/${keyId}`);
      success('API密钥已撤销');
      loadApiSecurityData();
    } catch (err) {
      showError('密钥撤销失败');
    }
  };

  useEffect(() => {
    loadApiSecurityData();
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

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET':
        return 'bg-green-100 text-green-800';
      case 'POST':
        return 'bg-blue-100 text-blue-800';
      case 'PUT':
        return 'bg-yellow-100 text-yellow-800';
      case 'DELETE':
        return 'bg-red-100 text-red-800';
      case 'PATCH':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'allowed':
        return 'bg-green-100 text-green-800';
      case 'blocked':
        return 'bg-red-100 text-red-800';
      case 'rate_limited':
        return 'bg-yellow-100 text-yellow-800';
      case 'unauthorized':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'endpoints' as const, label: 'API端点' },
    { key: 'events' as const, label: '安全事件' },
    { key: 'keys' as const, label: 'API密钥' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">API安全</h1>
        <div className="flex gap-2">
          <Button onClick={loadApiSecurityData}>刷新数据</Button>
          <Button onClick={() => setShowAddEndpointModal(true)}>添加端点</Button>
          <Button onClick={() => setShowAddKeyModal(true)}>生成密钥</Button>
        </div>
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

      {/* API端点 */}
      {activeTab === 'endpoints' && (
        <Card>
          <CardHeader>
            <CardTitle>API端点</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>路径</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>认证</TableHead>
                  <TableHead>认证类型</TableHead>
                  <TableHead>速率限制</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后访问</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {endpoints.length > 0 ? endpoints.map((endpoint) => (
                  <TableRow key={endpoint.id}>
                    <TableCell className="font-mono text-sm">{endpoint.path}</TableCell>
                    <TableCell>
                      <Badge className={getMethodColor(endpoint.method)}>{endpoint.method}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={endpoint.authRequired ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}>
                        {endpoint.authRequired ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>{endpoint.authType}</TableCell>
                    <TableCell>{endpoint.rateLimit}/min</TableCell>
                    <TableCell>
                      <Badge className={endpoint.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {endpoint.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(endpoint.lastAccessed).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleEndpoint(endpoint.id, !endpoint.enabled)}
                      >
                        {endpoint.enabled ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No API endpoints found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 安全事件 */}
      {activeTab === 'events' && (
        <Card>
          <CardHeader>
            <CardTitle>安全事件</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>端点</TableHead>
                  <TableHead>方法</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>原因</TableHead>
                  <TableHead>响应时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.length > 0 ? events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                    <TableCell className="font-mono text-sm">{event.endpoint}</TableCell>
                    <TableCell>
                      <Badge className={getMethodColor(event.method)}>{event.method}</Badge>
                    </TableCell>
                    <TableCell>{event.userId}</TableCell>
                    <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(event.status)}>{event.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm max-w-xs truncate">{event.reason}</TableCell>
                    <TableCell>{event.responseTime}ms</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No security events found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* API密钥 */}
      {activeTab === 'keys' && (
        <Card>
          <CardHeader>
            <CardTitle>API密钥</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>密钥</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>权限</TableHead>
                  <TableHead>过期时间</TableHead>
                  <TableHead>最后使用</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.length > 0 ? apiKeys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell className="font-mono text-sm">{key.key.substring(0, 20)}...</TableCell>
                    <TableCell>{key.userId}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {key.permissions.map((perm, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{perm}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>{new Date(key.expiresAt).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(key.lastUsed).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={key.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {key.enabled ? '启用' : '禁用'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRevokeKey(key.id)}
                      >
                        撤销
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No API keys found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加端点模态框 */}
      {showAddEndpointModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加API端点</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">路径</label>
                <Input
                  value={newEndpoint.path}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, path: e.target.value })}
                  placeholder="/api/v1/resource"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">方法</label>
                <Select
                  value={newEndpoint.method}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, method: e.target.value as any })}
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                  <option value="PATCH">PATCH</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">认证类型</label>
                <Select
                  value={newEndpoint.authType}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, authType: e.target.value as any })}
                >
                  <option value="bearer">Bearer Token</option>
                  <option value="basic">Basic Auth</option>
                  <option value="api_key">API Key</option>
                  <option value="oauth2">OAuth2</option>
                  <option value="none">None</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">速率限制 (请求/分钟)</label>
                <Input
                  type="number"
                  value={newEndpoint.rateLimit}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, rateLimit: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">描述</label>
                <Input
                  value={newEndpoint.description}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, description: e.target.value })}
                  placeholder="端点描述"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newEndpoint.authRequired}
                  onChange={(e) => setNewEndpoint({ ...newEndpoint, authRequired: e.target.checked })}
                />
                <label className="text-sm">需要认证</label>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddEndpointModal(false)}>取消</Button>
                <Button onClick={handleAddEndpoint}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 生成密钥模态框 */}
      {showAddKeyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>生成API密钥</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">名称</label>
                <Input
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                  placeholder="密钥名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">用户ID</label>
                <Input
                  value={newKey.userId}
                  onChange={(e) => setNewKey({ ...newKey, userId: e.target.value })}
                  placeholder="用户ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">过期时间 (天)</label>
                <Input
                  type="number"
                  value={newKey.expiresIn}
                  onChange={(e) => setNewKey({ ...newKey, expiresIn: parseInt(e.target.value) })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">权限 (逗号分隔)</label>
                <Input
                  value={newKey.permissions.join(',')}
                  onChange={(e) => setNewKey({ ...newKey, permissions: e.target.value.split(',').filter(p => p.trim()) })}
                  placeholder="read,write,admin"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddKeyModal(false)}>取消</Button>
                <Button onClick={handleGenerateKey}>生成</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
