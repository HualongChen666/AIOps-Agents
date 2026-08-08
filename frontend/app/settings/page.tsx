'use client'

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface User {
  id: string;
  username: string;
  name: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  disabled: boolean;
  status: 'active' | 'inactive';
  lastLogin: string;
}

interface AuditLog {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  details: string;
  ip: string;
}

interface Settings {
  system_name?: string;
  timezone?: string;
  language?: string;
  data_retention?: string;
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'users' | 'audit'>('general');

  const [settings, setSettings] = useState<Settings>({});
  const [users, setUsers] = useState<User[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);

  const mapUser = (u: any): User => ({
    id: String(u.id),
    username: String(u.username),
    name: u.full_name || u.username,
    email: u.email || '',
    role: u.role === 'admin' ? 'admin' : u.role === 'operator' ? 'operator' : 'viewer',
    disabled: !!u.disabled,
    status: u.disabled ? 'inactive' : 'active',
    lastLogin: u.last_login_at || u.created_at || new Date().toISOString(),
  });

  const mapAuditLog = (l: any): AuditLog => ({
    id: String(l.id),
    timestamp: l.created_at || new Date().toISOString(),
    user: l.username || 'system',
    action: l.action || '',
    resource: `${l.resource_type || ''}${l.resource_id ? `/${l.resource_id}` : ''}`,
    details: l.details || '',
    ip: l.ip_address || '',
  });

  useEffect(() => {
    let mounted = true;
    const loadData = async () => {
      setLoading(true);
      try {
        const [settingsRes, usersRes, auditRes] = await Promise.all([
          api.get('/api/settings/'),
          api.get('/api/v1/users/'),
          api.get('/api/v1/users/audit-logs'),
        ]);
        if (!mounted) return;
        setSettings(settingsRes.data?.settings || {});
        setUsers((usersRes.data || []).map(mapUser));
        setAuditLogs((auditRes.data || []).map(mapAuditLog));
      } catch {
        // api interceptor shows errors via toast
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadData();
    return () => { mounted = false; };
  }, []);

  const handleSaveSettings = async () => {
    try {
      await api.put('/api/settings/', settings);
    } catch {
      // api interceptor handles errors
    }
  };

  const handleToggleStatus = async (user: User) => {
    const newDisabled = !user.disabled;
    try {
      await api.put(`/api/v1/users/${user.username}`, { disabled: newDisabled });
      setUsers((prev) =>
        prev.map((u) =>
          u.id === user.id ? { ...u, disabled: newDisabled, status: newDisabled ? 'inactive' : 'active' } : u
        )
      );
    } catch {
      // api interceptor handles errors
    }
  };

  const handleDeleteUser = async (user: User) => {
    if (!window.confirm('确定要删除该用户吗？')) return;
    try {
      await api.delete(`/api/v1/users/${user.username}`);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch {
      // api interceptor handles errors
    }
  };

  const tabs = [
    { key: 'general' as const, label: '通用设置' },
    { key: 'users' as const, label: '用户管理' },
    { key: 'audit' as const, label: '审计日志' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">设置</h1>

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

      {activeTab === 'general' && (
        <Card>
          <CardHeader>
            <CardTitle>通用设置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">系统名称</label>
                <Input
                  value={settings.system_name || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, system_name: e.target.value }))}
                  placeholder="AIOps Agent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">时区</label>
                <Select
                  value={settings.timezone || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, timezone: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="Asia/Shanghai">Asia/Shanghai</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">语言</label>
                <Select
                  value={settings.language || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, language: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="zh-CN">简体中文</option>
                  <option value="en-US">English</option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数据保留期</label>
                <Select
                  value={settings.data_retention || ''}
                  onChange={(e) => setSettings((s) => ({ ...s, data_retention: e.target.value }))}
                >
                  <option value="">请选择</option>
                  <option value="7d">7天</option>
                  <option value="30d">30天</option>
                  <option value="90d">90天</option>
                  <option value="1y">1年</option>
                </Select>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleSaveSettings} disabled={loading}>
                  保存设置
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'users' && (
        <Card>
          <CardHeader>
            <CardTitle>用户权限管理</CardTitle>
          </CardHeader>
          <CardContent>
            {users.length === 0 ? (
              <p className="text-sm text-gray-500">暂无用户数据</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>姓名</TableHead>
                    <TableHead>邮箱</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>最后登录</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-mono text-sm">{user.id}</TableCell>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Badge className={user.role === 'admin' ? 'bg-purple-100 text-purple-800' : user.role === 'operator' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}>
                          {user.role === 'admin' ? '管理员' : user.role === 'operator' ? '运维' : '查看者'}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={`cursor-pointer ${user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
                          onClick={() => handleToggleStatus(user)}
                        >
                          {user.status === 'active' ? '活跃' : '未激活'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{new Date(user.lastLogin).toLocaleString()}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm">
                            编辑
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => handleDeleteUser(user)}>
                            删除
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'audit' && (
        <Card>
          <CardHeader>
            <CardTitle>审计日志</CardTitle>
          </CardHeader>
          <CardContent>
            {auditLogs.length === 0 ? (
              <p className="text-sm text-gray-500">暂无审计日志</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>时间</TableHead>
                    <TableHead>用户</TableHead>
                    <TableHead>操作</TableHead>
                    <TableHead>资源</TableHead>
                    <TableHead>详情</TableHead>
                    <TableHead>IP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-sm">{log.id}</TableCell>
                      <TableCell className="text-sm">{new Date(log.timestamp).toLocaleString()}</TableCell>
                      <TableCell>{log.user}</TableCell>
                      <TableCell>{log.action}</TableCell>
                      <TableCell>{log.resource}</TableCell>
                      <TableCell>{log.details}</TableCell>
                      <TableCell>{log.ip}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
