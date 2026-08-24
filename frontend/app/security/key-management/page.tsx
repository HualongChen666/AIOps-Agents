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

interface Key {
  id: string;
  name: string;
  type: 'api_key' | 'secret_key' | 'jwt' | 'ssh' | 'certificate';
  algorithm: string;
  keySize: number;
  status: 'active' | 'inactive' | 'expired' | 'revoked';
  createdAt: string;
  expiresAt: string;
  lastRotated: string;
  lastUsed: string;
  usage: string[];
}

interface KeyRotation {
  id: string;
  keyId: string;
  keyName: string;
  scheduledAt: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  completedAt?: string;
}

interface KeyAccess {
  id: string;
  keyId: string;
  keyName: string;
  userId: string;
  userName: string;
  action: 'create' | 'read' | 'update' | 'delete' | 'rotate';
  timestamp: string;
  ipAddress: string;
  success: boolean;
}

export default function KeyManagementPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [keys, setKeys] = useState<Key[]>([]);
  const [rotations, setRotations] = useState<KeyRotation[]>([]);
  const [accessLogs, setAccessLogs] = useState<KeyAccess[]>([]);
  const [activeTab, setActiveTab] = useState<'keys' | 'rotations' | 'access'>('keys');

  const loadKeyManagementData = async () => {
    setLoading(true);
    try {
      const [keysRes, rotationsRes, accessRes] = await Promise.all([
        api.get('/api/v1/security/key-management/keys'),
        api.get('/api/v1/security/key-management/rotations'),
        api.get('/api/v1/security/key-management/access'),
      ]);

      const keysData = keysRes.data?.keys || [];
      const rotationsData = rotationsRes.data?.rotations || [];
      const accessData = accessRes.data?.access || [];

      setKeys(keysData);
      setRotations(rotationsData);
      setAccessLogs(accessData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleRotateKey = async (keyId: string) => {
    try {
      await api.post(`/api/v1/security/key-management/keys/${keyId}/rotate`);
      success('密钥轮换已启动');
      loadKeyManagementData();
    } catch (err) {
      showError('密钥轮换失败');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      await api.post(`/api/v1/security/key-management/keys/${keyId}/revoke`);
      success('密钥已撤销');
      loadKeyManagementData();
    } catch (err) {
      showError('密钥撤销失败');
    }
  };

  const handleScheduleRotation = async (keyId: string, scheduledAt: string) => {
    try {
      await api.post(`/api/v1/security/key-management/keys/${keyId}/schedule-rotation`, {
        scheduledAt,
      });
      success('轮换已调度');
      loadKeyManagementData();
    } catch (err) {
      showError('调度失败');
    }
  };

  useEffect(() => {
    loadKeyManagementData();
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'expired':
      case 'failed':
      case 'revoked':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'api_key':
        return 'bg-blue-100 text-blue-800';
      case 'secret_key':
        return 'bg-purple-100 text-purple-800';
      case 'jwt':
        return 'bg-green-100 text-green-800';
      case 'ssh':
        return 'bg-orange-100 text-orange-800';
      case 'certificate':
        return 'bg-pink-100 text-pink-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'keys' as const, label: '密钥列表' },
    { key: 'rotations' as const, label: '轮换记录' },
    { key: 'access' as const, label: '访问日志' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">密钥管理</h1>
        <Button onClick={loadKeyManagementData}>刷新数据</Button>
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

      {/* 密钥列表 */}
      {activeTab === 'keys' && (
        <Card>
          <CardHeader>
            <CardTitle>密钥列表</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>算法</TableHead>
                  <TableHead>密钥大小</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead>过期时间</TableHead>
                  <TableHead>最后轮换</TableHead>
                  <TableHead>最后使用</TableHead>
                  <TableHead>用途</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.length > 0 ? keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <Badge className={getTypeColor(key.type)}>{key.type}</Badge>
                    </TableCell>
                    <TableCell>{key.algorithm}</TableCell>
                    <TableCell>{key.keySize} bits</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(key.status)}>{key.status}</Badge>
                    </TableCell>
                    <TableCell>{new Date(key.createdAt).toLocaleString()}</TableCell>
                    <TableCell>{new Date(key.expiresAt).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(key.lastRotated).toLocaleString()}</TableCell>
                    <TableCell>{key.lastUsed ? new Date(key.lastUsed).toLocaleString() : '-'}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {key.usage.slice(0, 2).map((use, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{use}</Badge>
                        ))}
                        {key.usage.length > 2 && (
                          <Badge variant="outline" className="text-xs">+{key.usage.length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {key.status === 'active' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRotateKey(key.id)}
                          >
                            轮换
                          </Button>
                        )}
                        {key.status === 'active' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRevokeKey(key.id)}
                          >
                            撤销
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-gray-500">
                      No keys found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 轮换记录 */}
      {activeTab === 'rotations' && (
        <Card>
          <CardHeader>
            <CardTitle>轮换记录</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>密钥</TableHead>
                  <TableHead>调度时间</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>完成时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rotations.length > 0 ? rotations.map((rotation) => (
                  <TableRow key={rotation.id}>
                    <TableCell className="font-medium">{rotation.keyName}</TableCell>
                    <TableCell>{new Date(rotation.scheduledAt).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(rotation.status)}>{rotation.status}</Badge>
                    </TableCell>
                    <TableCell>{rotation.completedAt ? new Date(rotation.completedAt).toLocaleString() : '-'}</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-gray-500">
                      No rotation records found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 访问日志 */}
      {activeTab === 'access' && (
        <Card>
          <CardHeader>
            <CardTitle>访问日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>密钥</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>成功</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accessLogs.length > 0 ? accessLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{log.userName}</TableCell>
                    <TableCell>{log.keyName}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{log.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                        {log.success ? '成功' : '失败'}
                      </Badge>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-gray-500">
                      No access logs found
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
