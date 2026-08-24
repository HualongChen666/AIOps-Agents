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

interface EncryptionKey {
  id: string;
  name: string;
  type: 'aes' | 'rsa' | 'ecdsa' | 'chacha';
  algorithm: string;
  keySize: number;
  status: 'active' | 'inactive' | 'expired' | 'revoked';
  createdAt: string;
  expiresAt: string;
  lastRotated: string;
  usage: string[];
}

interface EncryptionPolicy {
  id: string;
  name: string;
  scope: string;
  algorithm: string;
  keyRotationDays: number;
  enforceEncryption: boolean;
  allowedAlgorithms: string[];
  createdAt: string;
  status: 'active' | 'inactive';
}

interface EncryptionEvent {
  id: string;
  timestamp: string;
  operation: 'encrypt' | 'decrypt' | 'key_rotation' | 'key_generation';
  keyId: string;
  keyName: string;
  userId: string;
  ipAddress: string;
  status: 'success' | 'failure';
  dataSize: number;
}

export default function DataEncryptionPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [keys, setKeys] = useState<EncryptionKey[]>([]);
  const [policies, setPolicies] = useState<EncryptionPolicy[]>([]);
  const [events, setEvents] = useState<EncryptionEvent[]>([]);
  const [activeTab, setActiveTab] = useState<'keys' | 'policies' | 'events'>('keys');
  const [showGenerateKeyModal, setShowGenerateKeyModal] = useState(false);
  const [newKey, setNewKey] = useState({
    name: '',
    type: 'aes' as const,
    algorithm: 'AES-256-GCM',
    keySize: 256,
    expiresIn: 365,
    usage: [] as string[],
  });

  const loadEncryptionData = async () => {
    setLoading(true);
    try {
      const [keysRes, policiesRes, eventsRes] = await Promise.all([
        api.get('/api/v1/security/data-encryption/keys'),
        api.get('/api/v1/security/data-encryption/policies'),
        api.get('/api/v1/security/data-encryption/events'),
      ]);

      const keysData = keysRes.data?.keys || [];
      const policiesData = policiesRes.data?.policies || [];
      const eventsData = eventsRes.data?.events || [];

      setKeys(keysData);
      setPolicies(policiesData);
      setEvents(eventsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleGenerateKey = async () => {
    try {
      await api.post('/api/v1/security/data-encryption/keys/generate', newKey);
      success('密钥生成成功');
      setShowGenerateKeyModal(false);
      setNewKey({ name: '', type: 'aes', algorithm: 'AES-256-GCM', keySize: 256, expiresIn: 365, usage: [] });
      loadEncryptionData();
    } catch (err) {
      showError('密钥生成失败');
    }
  };

  const handleRotateKey = async (keyId: string) => {
    try {
      await api.post(`/api/v1/security/data-encryption/keys/${keyId}/rotate`);
      success('密钥轮换成功');
      loadEncryptionData();
    } catch (err) {
      showError('密钥轮换失败');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    try {
      await api.post(`/api/v1/security/data-encryption/keys/${keyId}/revoke`);
      success('密钥已撤销');
      loadEncryptionData();
    } catch (err) {
      showError('密钥撤销失败');
    }
  };

  const handleTogglePolicy = async (policyId: string, status: string) => {
    try {
      await api.patch(`/api/v1/security/data-encryption/policies/${policyId}`, { status });
      success('策略状态更新成功');
      loadEncryptionData();
    } catch (err) {
      showError('策略状态更新失败');
    }
  };

  useEffect(() => {
    loadEncryptionData();
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
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'expired':
      case 'failure':
        return 'bg-red-100 text-red-800';
      case 'revoked':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'keys' as const, label: '加密密钥' },
    { key: 'policies' as const, label: '加密策略' },
    { key: 'events' as const, label: '加密事件' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据加密</h1>
        <div className="flex gap-2">
          <Button onClick={loadEncryptionData}>刷新数据</Button>
          <Button onClick={() => setShowGenerateKeyModal(true)}>生成密钥</Button>
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

      {/* 加密密钥 */}
      {activeTab === 'keys' && (
        <Card>
          <CardHeader>
            <CardTitle>加密密钥</CardTitle>
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
                  <TableHead>用途</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.length > 0 ? keys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{key.type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>{key.algorithm}</TableCell>
                    <TableCell>{key.keySize} bits</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(key.status)}>{key.status}</Badge>
                    </TableCell>
                    <TableCell>{new Date(key.createdAt).toLocaleString()}</TableCell>
                    <TableCell>{new Date(key.expiresAt).toLocaleDateString()}</TableCell>
                    <TableCell>{new Date(key.lastRotated).toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {key.usage.map((use, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{use}</Badge>
                        ))}
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
                    <TableCell colSpan={10} className="text-center text-gray-500">
                      No encryption keys found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 加密策略 */}
      {activeTab === 'policies' && (
        <Card>
          <CardHeader>
            <CardTitle>加密策略</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>范围</TableHead>
                  <TableHead>算法</TableHead>
                  <TableHead>密钥轮换周期</TableHead>
                  <TableHead>强制加密</TableHead>
                  <TableHead>允许算法</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies.length > 0 ? policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell className="font-medium">{policy.name}</TableCell>
                    <TableCell>{policy.scope}</TableCell>
                    <TableCell>{policy.algorithm}</TableCell>
                    <TableCell>{policy.keyRotationDays} 天</TableCell>
                    <TableCell>
                      <Badge className={policy.enforceEncryption ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {policy.enforceEncryption ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {policy.allowedAlgorithms.map((algo, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{algo}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(policy.status)}>{policy.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTogglePolicy(policy.id, policy.status === 'active' ? 'inactive' : 'active')}
                      >
                        {policy.status === 'active' ? '禁用' : '启用'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No encryption policies found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 加密事件 */}
      {activeTab === 'events' && (
        <Card>
          <CardHeader>
            <CardTitle>加密事件</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>密钥</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>数据大小</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.length > 0 ? events.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.timestamp).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{event.operation}</Badge>
                    </TableCell>
                    <TableCell>{event.keyName}</TableCell>
                    <TableCell>{event.userId}</TableCell>
                    <TableCell className="font-mono text-sm">{event.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(event.status)}>{event.status}</Badge>
                    </TableCell>
                    <TableCell>{(event.dataSize / 1024).toFixed(2)} KB</TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No encryption events found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 生成密钥模态框 */}
      {showGenerateKeyModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>生成加密密钥</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">密钥名称</label>
                <Input
                  value={newKey.name}
                  onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                  placeholder="输入密钥名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">类型</label>
                <Select
                  value={newKey.type}
                  onChange={(e) => setNewKey({ ...newKey, type: e.target.value as any })}
                >
                  <option value="aes">AES</option>
                  <option value="rsa">RSA</option>
                  <option value="ecdsa">ECDSA</option>
                  <option value="chacha">ChaCha</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">算法</label>
                <Input
                  value={newKey.algorithm}
                  onChange={(e) => setNewKey({ ...newKey, algorithm: e.target.value })}
                  placeholder="例如: AES-256-GCM"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">密钥大小 (bits)</label>
                <Input
                  type="number"
                  value={newKey.keySize}
                  onChange={(e) => setNewKey({ ...newKey, keySize: parseInt(e.target.value) })}
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
                <label className="block text-sm font-medium mb-1">用途 (逗号分隔)</label>
                <Input
                  value={newKey.usage.join(',')}
                  onChange={(e) => setNewKey({ ...newKey, usage: e.target.value.split(',').filter(u => u.trim()) })}
                  placeholder="data-at-rest,transit"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowGenerateKeyModal(false)}>取消</Button>
                <Button onClick={handleGenerateKey}>生成</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
