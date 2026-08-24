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

interface DatabaseInstance {
  id: string;
  name: string;
  type: 'postgresql' | 'mysql' | 'mongodb' | 'redis' | 'elasticsearch';
  host: string;
  port: number;
  status: 'online' | 'offline' | 'maintenance';
  encryptionEnabled: boolean;
  sslEnabled: boolean;
  backupEnabled: boolean;
  lastBackup: string;
  version: string;
}

interface DatabaseUser {
  id: string;
  databaseId: string;
  username: string;
  role: string;
  permissions: string[];
  lastLogin: string;
  status: 'active' | 'inactive' | 'locked';
}

interface DatabaseAudit {
  id: string;
  timestamp: string;
  databaseId: string;
  databaseName: string;
  userId: string;
  action: string;
  query: string;
  ipAddress: string;
  result: 'success' | 'failure';
  riskLevel: 'low' | 'medium' | 'high';
}

export default function DatabaseSecurityPage() {
  const { isLoading, error, setLoading, setError } = useLoadingState(false);
  const { success, error: showError } = useToast();
  const [instances, setInstances] = useState<DatabaseInstance[]>([]);
  const [users, setUsers] = useState<DatabaseUser[]>([]);
  const [audits, setAudits] = useState<DatabaseAudit[]>([]);
  const [activeTab, setActiveTab] = useState<'instances' | 'users' | 'audits'>('instances');
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUser, setNewUser] = useState({
    databaseId: '',
    username: '',
    role: 'read',
    permissions: [] as string[],
  });

  const loadDatabaseSecurityData = async () => {
    setLoading(true);
    try {
      const [instancesRes, usersRes, auditsRes] = await Promise.all([
        api.get('/api/v1/security/database-security/instances'),
        api.get('/api/v1/security/database-security/users'),
        api.get('/api/v1/security/database-security/audits'),
      ]);

      const instancesData = instancesRes.data?.instances || [];
      const usersData = usersRes.data?.users || [];
      const auditsData = auditsRes.data?.audits || [];

      setInstances(instancesData);
      setUsers(usersData);
      setAudits(auditsData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  };

  const handleAddUser = async () => {
    try {
      await api.post('/api/v1/security/database-security/users', newUser);
      success('数据库用户添加成功');
      setShowAddUserModal(false);
      setNewUser({ databaseId: '', username: '', role: 'read', permissions: [] });
      loadDatabaseSecurityData();
    } catch (err) {
      showError('用户添加失败');
    }
  };

  const handleToggleEncryption = async (instanceId: string, enabled: boolean) => {
    try {
      await api.patch(`/api/v1/security/database-security/instances/${instanceId}`, {
        encryptionEnabled: enabled,
      });
      success('加密状态更新成功');
      loadDatabaseSecurityData();
    } catch (err) {
      showError('加密状态更新失败');
    }
  };

  const handleLockUser = async (userId: string, locked: boolean) => {
    try {
      await api.patch(`/api/v1/security/database-security/users/${userId}`, {
        status: locked ? 'locked' : 'active',
      });
      success('用户状态更新成功');
      loadDatabaseSecurityData();
    } catch (err) {
      showError('用户状态更新失败');
    }
  };

  useEffect(() => {
    loadDatabaseSecurityData();
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
      case 'online':
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'offline':
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'maintenance':
        return 'bg-yellow-100 text-yellow-800';
      case 'locked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'bg-red-100 text-red-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'low':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getResultColor = (result: string) => {
    switch (result) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'failure':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const tabs = [
    { key: 'instances' as const, label: '数据库实例' },
    { key: 'users' as const, label: '用户管理' },
    { key: 'audits' as const, label: '审计日志' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">数据库安全</h1>
        <div className="flex gap-2">
          <Button onClick={loadDatabaseSecurityData}>刷新数据</Button>
          <Button onClick={() => setShowAddUserModal(true)}>添加用户</Button>
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

      {/* 数据库实例 */}
      {activeTab === 'instances' && (
        <Card>
          <CardHeader>
            <CardTitle>数据库实例</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>主机</TableHead>
                  <TableHead>端口</TableHead>
                  <TableHead>版本</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>加密</TableHead>
                  <TableHead>SSL</TableHead>
                  <TableHead>备份</TableHead>
                  <TableHead>最后备份</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {instances.length > 0 ? instances.map((instance) => (
                  <TableRow key={instance.id}>
                    <TableCell className="font-medium">{instance.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{instance.type}</Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{instance.host}</TableCell>
                    <TableCell>{instance.port}</TableCell>
                    <TableCell>{instance.version}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(instance.status)}>{instance.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={instance.encryptionEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {instance.encryptionEnabled ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={instance.sslEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {instance.sslEnabled ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={instance.backupEnabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                        {instance.backupEnabled ? '是' : '否'}
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(instance.lastBackup).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleEncryption(instance.id, !instance.encryptionEnabled)}
                      >
                        {instance.encryptionEnabled ? '禁用加密' : '启用加密'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={11} className="text-center text-gray-500">
                      No database instances found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 用户管理 */}
      {activeTab === 'users' && (
        <Card>
          <CardHeader>
            <CardTitle>用户管理</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>用户名</TableHead>
                  <TableHead>数据库</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>权限</TableHead>
                  <TableHead>最后登录</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length > 0 ? users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.username}</TableCell>
                    <TableCell>{user.databaseId}</TableCell>
                    <TableCell>{user.role}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.permissions.map((perm, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">{perm}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>{new Date(user.lastLogin).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(user.status)}>{user.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleLockUser(user.id, user.status !== 'locked')}
                      >
                        {user.status === 'locked' ? '解锁' : '锁定'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500">
                      No database users found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 审计日志 */}
      {activeTab === 'audits' && (
        <Card>
          <CardHeader>
            <CardTitle>审计日志</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>数据库</TableHead>
                  <TableHead>用户</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>查询</TableHead>
                  <TableHead>IP地址</TableHead>
                  <TableHead>结果</TableHead>
                  <TableHead>风险</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {audits.length > 0 ? audits.map((audit) => (
                  <TableRow key={audit.id}>
                    <TableCell>{new Date(audit.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{audit.databaseName}</TableCell>
                    <TableCell>{audit.userId}</TableCell>
                    <TableCell>{audit.action}</TableCell>
                    <TableCell className="font-mono text-sm max-w-xs truncate">{audit.query}</TableCell>
                    <TableCell className="font-mono text-sm">{audit.ipAddress}</TableCell>
                    <TableCell>
                      <Badge className={getResultColor(audit.result)}>{audit.result}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getRiskColor(audit.riskLevel)}>{audit.riskLevel}</Badge>
                    </TableCell>
                  </TableRow>
                )) : (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-gray-500">
                      No audit logs found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* 添加用户模态框 */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>添加数据库用户</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">数据库ID</label>
                <Select
                  value={newUser.databaseId}
                  onChange={(e) => setNewUser({ ...newUser, databaseId: e.target.value })}
                >
                  <option value="">选择数据库</option>
                  {instances.map((inst) => (
                    <option key={inst.id} value={inst.id}>{inst.name}</option>
                  ))}
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">用户名</label>
                <Input
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  placeholder="输入用户名"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">角色</label>
                <Select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                >
                  <option value="read">只读</option>
                  <option value="write">读写</option>
                  <option value="admin">管理员</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">权限 (逗号分隔)</label>
                <Input
                  value={newUser.permissions.join(',')}
                  onChange={(e) => setNewUser({ ...newUser, permissions: e.target.value.split(',').filter(p => p.trim()) })}
                  placeholder="SELECT,INSERT,UPDATE,DELETE"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowAddUserModal(false)}>取消</Button>
                <Button onClick={handleAddUser}>添加</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
